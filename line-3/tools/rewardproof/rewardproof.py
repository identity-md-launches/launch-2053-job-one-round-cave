#!/usr/bin/env python3
"""Unsigned, context-bound inclusion proofs for verified RewardSplit shares."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
from pathlib import Path
import re
import sys

SPEC = importlib.util.spec_from_file_location(
    'rewardreceipt', Path(__file__).resolve().parents[1] / 'rewardreceipt' / 'rewardreceipt.py')
rr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rr)
rs = rr.rs
DOMAIN = b'Pepeolithic-RewardProof-v1\x00'
CONTEXT_FIELDS = {'token', 'budget_units', 'contributors', 'request_sha256',
                  'metadata_sha256', 'report_sha256'}
TOKEN_FIELDS = {'chain_id', 'address', 'symbol', 'decimals', 'block_number', 'block_hash'}
ROW_FIELDS = {'id', 'weight_fraction', 'units', 'amount', 'rounding_unit_awarded'}
SCOPE = 'inclusion under the supplied root only; no authentication, independent arithmetic audit, entitlement, balance or payment'


def exact_fields(value, fields, label):
    rs.require(isinstance(value, dict) and set(value) == fields, 'invalid ' + label + ' fields')


def hexhash(value):
    rs.require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value),
               'hash must be 64 lowercase hexadecimal characters')
    return bytes.fromhex(value)


def units(value, positive=False):
    rs.require(isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,77}', value),
               'units must be a canonical uint256 decimal string')
    number = int(value)
    rs.require(int(positive) <= number <= rs.UINT256_MAX, 'units outside uint256 range')
    return number


def validate_context(context):
    exact_fields(context, CONTEXT_FIELDS, 'context')
    for field in ('request_sha256', 'metadata_sha256', 'report_sha256'):
        hexhash(context[field])
    rs.require(type(context['contributors']) is int and 1 <= context['contributors'] <= 1000,
               'contributor count must be 1-1000')
    units(context['budget_units'], positive=True)
    exact_fields(context['token'], TOKEN_FIELDS, 'token')
    rs.validate_metadata(dict(context['token'], schema='rewardsplit-token-v1'))


def validate_row(row, context):
    rs.require(isinstance(row, dict) and ROW_FIELDS <= set(row) <= ROW_FIELDS | {'address'},
               'invalid allocation fields')
    rs.require(isinstance(row['id'], str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', row['id']),
               'invalid contributor id')
    if 'address' in row:
        rs.require(rs.address(row['address']) == row['address'], 'address must be normalized lowercase')
    number = units(row['units'])
    rs.require(number <= int(context['budget_units']), 'share exceeds budget')
    rs.require(row['amount'] == rs.display_units(number, context['token']['decimals']),
               'amount does not match exact units')
    rs.require(type(row['rounding_unit_awarded']) is bool, 'award flag must be boolean')
    value = row['weight_fraction']
    rs.require(isinstance(value, str) and re.fullmatch(r'(?:0|[1-9][0-9]{0,35})(?:/[1-9][0-9]{0,18})?', value),
               'invalid weight fraction')
    rs.require(str(Fraction(value)) == value, 'weight fraction must be reduced and canonical')


def leaf(context, index, row):
    return hashlib.sha256(b'\x00' + DOMAIN + bytes.fromhex(rr.digest(context))
                          + index.to_bytes(4, 'big') + rr.canonical_bytes(row)).digest()


def parent(left, right):
    return hashlib.sha256(b'\x01' + DOMAIN + left + right).digest()


def tree(request, report, metadata):
    """No commitment is constructed until the complete source report verifies."""
    receipt = rr.verify(request, report, metadata)
    context = {field: receipt[field] for field in sorted(CONTEXT_FIELDS)}
    validate_context(context)
    rows = report['allocations']
    levels = [[leaf(context, i, row) for i, row in enumerate(rows)]]
    while len(levels[-1]) > 1:
        current = levels[-1]
        levels.append([parent(current[i], current[min(i + 1, len(current) - 1)])
                       for i in range(0, len(current), 2)])
    commitment = {'schema': 'rewardproof-commitment-v1', 'context': context,
                  'root': levels[-1][0].hex()}
    return commitment, levels


def commit(request, report, metadata):
    return tree(request, report, metadata)[0]


def prove(request, report, metadata, identifier):
    commitment, levels = tree(request, report, metadata)
    matches = [i for i, row in enumerate(report['allocations']) if row['id'] == identifier]
    rs.require(len(matches) == 1, 'contributor is absent from the verified allocation')
    index = matches[0]
    cursor = index
    siblings = []
    for level in levels[:-1]:
        siblings.append(level[min(cursor ^ 1, len(level) - 1)].hex())
        cursor //= 2
    # Round-trip copies prevent accidental aliasing between report and packet.
    return rs.parse_json(rr.canonical_bytes({
        'schema': 'rewardproof-inclusion-v1', 'commitment': commitment,
        'index': index, 'allocation': report['allocations'][index], 'siblings': siblings}))


def verify(proof, expected_root, expected_id):
    """The expected root must arrive separately from a source the caller trusts."""
    hexhash(expected_root)
    exact_fields(proof, {'schema', 'commitment', 'index', 'allocation', 'siblings'}, 'proof')
    rs.require(proof['schema'] == 'rewardproof-inclusion-v1', 'unknown proof schema')
    commitment = proof['commitment']
    exact_fields(commitment, {'schema', 'context', 'root'}, 'commitment')
    rs.require(commitment['schema'] == 'rewardproof-commitment-v1', 'unknown commitment schema')
    hexhash(commitment['root'])
    rs.require(commitment['root'] == expected_root, 'proof root differs from the separately supplied root')
    context = commitment['context']
    validate_context(context)
    index, width = proof['index'], context['contributors']
    rs.require(type(index) is int and 0 <= index < width, 'invalid leaf index')
    validate_row(proof['allocation'], context)
    rs.require(isinstance(expected_id, str) and proof['allocation']['id'] == expected_id,
               'proof is for a different contributor')
    siblings = proof['siblings']
    depth = (width - 1).bit_length()
    rs.require(isinstance(siblings, list) and len(siblings) == depth, 'incorrect proof depth')
    node = leaf(context, index, proof['allocation'])
    for item in siblings:
        sibling = hexhash(item)
        if width % 2 and index == width - 1:
            rs.require(sibling == node, 'odd last leaf must duplicate itself')
        node = parent(sibling, node) if index % 2 else parent(node, sibling)
        index //= 2
        width = (width + 1) // 2
    rs.require(node.hex() == expected_root, 'inclusion path does not match supplied root')
    return {'schema': 'rewardproof-verification-v1', 'result': 'included',
            'root': expected_root, 'context': context, 'allocation': proof['allocation'],
            'proof_sha256': rr.digest(proof), 'scope': SCOPE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='verify a proof of an illustrative address-free ZTO share')
    for name in ('commit', 'prove'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--request', required=True)
        cmd.add_argument('--report', required=True)
        cmd.add_argument('--metadata', default=str(rr.ROOT / 'zto-mainnet.json'))
        cmd.add_argument('--output')
        if name == 'prove':
            cmd.add_argument('--id', required=True)
    check = commands.add_parser('verify')
    check.add_argument('--proof', required=True)
    check.add_argument('--root', required=True, help='root obtained separately from a trusted source')
    check.add_argument('--id', required=True)
    check.add_argument('--output')
    args = parser.parse_args(argv)
    try:
        if args.command == 'verify':
            result = verify(rs.read_json(args.proof), args.root, args.id)
        else:
            demo = args.command == 'demo'
            request = rs.read_json(rr.ROOT / 'example.json' if demo else args.request)
            metadata = rs.read_json(rr.ROOT / 'zto-mainnet.json' if demo else args.metadata)
            report = rs.allocate(request, metadata) if demo else rs.read_json(args.report)
            if demo:
                commitment = commit(request, report, metadata)
                proof = prove(request, report, metadata, 'build')
                result = {'commitment': commitment, 'proof': proof,
                          'verification': verify(proof, commitment['root'], 'build'),
                          'demo': 'Illustrative roles; root created locally for demonstration, not authenticated.'}
            elif args.command == 'commit':
                result = commit(request, report, metadata)
            else:
                result = prove(request, report, metadata, args.id)
        rs.write_json(result, getattr(args, 'output', None))
        return 0
    except (rs.Invalid, OSError, ValueError, OverflowError, RecursionError) as exc:
        print('rewardproof: ' + (str(exc) if isinstance(exc, rs.Invalid) else type(exc).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

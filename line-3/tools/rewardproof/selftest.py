#!/usr/bin/env python3
"""Offline roots, malformed paths, exact amounts and file-based CLI checks."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
import rewardproof as rp


class Tests(unittest.TestCase):
    def setUp(self):
        self.metadata = rp.rs.read_json(rp.rr.ROOT / 'zto-mainnet.json')
        self.request = rp.rs.read_json(rp.rr.ROOT / 'example.json')

    def make(self, request=None):
        request = self.request if request is None else request
        report = rp.rs.allocate(request, self.metadata)
        commitment = rp.commit(request, report, self.metadata)
        return report, commitment

    def test_reference_roots_and_every_small_leaf(self):
        # Independently spell the byte protocol, including odd-node duplication.
        def canonical(value):
            return json.dumps(value, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=True, allow_nan=False).encode('ascii')
        rng = random.Random(33)
        for count in range(1, 36):
            request = {'budget': rp.rs.display_units(rng.randrange(1, 10**23), 18),
                       'contributors': [{'id': 'worker'+str(i), 'weight': str(rng.randrange(5))}
                                        for i in range(count)]}
            request['contributors'][0]['weight'] = '1'
            report, commitment = self.make(request)
            binding = hashlib.sha256(canonical(commitment['context'])).digest()
            level = [hashlib.sha256(b'\x00Pepeolithic-RewardProof-v1\x00' + binding
                                   + i.to_bytes(4, 'big') + canonical(row)).digest()
                     for i, row in enumerate(report['allocations'])]
            while len(level) > 1:
                if len(level) % 2:
                    level.append(level[-1])
                level = [hashlib.sha256(b'\x01Pepeolithic-RewardProof-v1\x00'
                                       + level[i] + level[i + 1]).digest()
                         for i in range(0, len(level), 2)]
            self.assertEqual(commitment['root'], level[0].hex())
            for row in report['allocations']:
                proof = rp.prove(request, report, self.metadata, row['id'])
                receipt = rp.verify(proof, commitment['root'], row['id'])
                self.assertEqual(receipt['allocation'], row)
                self.assertLessEqual(len(proof['siblings']), 6)

    def test_one_leaf_and_zero_share(self):
        for roster in ([{'id': 'one', 'weight': '1'}],
                       [{'id': 'one', 'weight': '1'}, {'id': 'zero', 'weight': '0'}]):
            request = {'budget': '1', 'contributors': roster}
            report, commitment = self.make(request)
            for row in report['allocations']:
                proof = rp.prove(request, report, self.metadata, row['id'])
                rp.verify(proof, commitment['root'], row['id'])
                self.assertEqual(proof['allocation']['units'], row['units'])
                if len(roster) == 1:
                    self.assertEqual(proof['siblings'], [])

    def test_uint256_fractional_and_address_propagation(self):
        request = {'budget': rp.rs.display_units(rp.rs.UINT256_MAX, 18),
                   'contributors': [{'id': 'a', 'weight': '999999999999999999.999999999999999999',
                                     'address': rp.rs.TOKENS['zto']},
                                    {'id': 'b', 'weight': '0.000000000000000001'}]}
        # Public token address tests syntax propagation only, never a suggested payee.
        report, commitment = self.make(request)
        for row in report['allocations']:
            proof = rp.prove(request, report, self.metadata, row['id'])
            rp.verify(proof, commitment['root'], row['id'])
        self.assertEqual(proof['allocation']['weight_fraction'], '1/1000000000000000000')
        self.assertEqual(sum(int(r['units']) for r in report['allocations']), rp.rs.UINT256_MAX)

    def test_full_source_rejected_before_commitment(self):
        report, _ = self.make()
        mutations = [lambda r: r.update(extra=True),
                     lambda r: r['allocations'][0].update(units='1'),
                     lambda r: r['allocations'].reverse(),
                     lambda r: r['token'].update(block_number=1)]
        for mutate in mutations:
            changed = copy.deepcopy(report)
            mutate(changed)
            with self.assertRaises(rp.rs.Invalid):
                rp.commit(self.request, changed, self.metadata)
            with self.assertRaises(rp.rs.Invalid):
                rp.prove(self.request, changed, self.metadata, 'build')
        with self.assertRaises(rp.rs.Invalid):
            rp.prove(self.request, report, self.metadata, 'absent')

    def test_all_proof_fields_bound(self):
        report, commitment = self.make()
        proof = rp.prove(self.request, report, self.metadata, 'build')
        mutations = [lambda p: p['allocation'].update(units='0', amount='0.000000000000000000'),
                     lambda p: p['allocation'].update(weight_fraction='2'),
                     lambda p: p['allocation'].update(rounding_unit_awarded=False),
                     lambda p: p['allocation'].update(address=rp.rs.TOKENS['imd']),
                     lambda p: p.update(index=1),
                     lambda p: p['commitment']['context'].update(request_sha256='a'*64),
                     lambda p: p['commitment']['context'].update(report_sha256='a'*64),
                     lambda p: p['commitment']['context'].update(metadata_sha256='a'*64),
                     lambda p: p['commitment']['context']['token'].update(symbol='IMD'),
                     lambda p: p['commitment']['context'].update(budget_units='1'),
                     lambda p: p['commitment']['context'].update(contributors=4),
                     lambda p: p['siblings'].__setitem__(0, 'a'*64),
                     lambda p: p['siblings'].reverse()]
        for mutate in mutations:
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaises(rp.rs.Invalid):
                rp.verify(changed, commitment['root'], 'build')

    def test_strict_structure_and_types(self):
        report, commitment = self.make()
        proof = rp.prove(self.request, report, self.metadata, 'build')
        mutations = [lambda p: p.update(extra=True), lambda p: p.update(schema='v2'),
                     lambda p: p.update(index=True), lambda p: p.update(index=-1),
                     lambda p: p.update(index=3), lambda p: p.update(siblings=[]),
                     lambda p: p['siblings'].append('a'*64),
                     lambda p: p['siblings'].__setitem__(0, 'A'*64),
                     lambda p: p['commitment'].update(root='invalid'),
                     lambda p: p['commitment'].update(schema='v2'),
                     lambda p: p['commitment']['context'].update(contributors=True),
                     lambda p: p['commitment']['context'].update(contributors=1001),
                     lambda p: p['allocation'].update(units=1),
                     lambda p: p['allocation'].update(units='01'),
                     lambda p: p['allocation'].update(rounding_unit_awarded=1),
                     lambda p: p['allocation'].update(weight_fraction='2/2')]
        for mutate in mutations:
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaises(rp.rs.Invalid):
                rp.verify(changed, commitment['root'], 'build')

    def test_trusted_root_and_id_required(self):
        report, commitment = self.make()
        proof = rp.prove(self.request, report, self.metadata, 'build')
        for root, identifier in [('a'*64, 'build'), (commitment['root'], 'review'),
                                 ('', 'build'), (None, 'build')]:
            with self.assertRaises(rp.rs.Invalid):
                rp.verify(proof, root, identifier)
        # Verification needs neither the original roster nor any allocator.
        with patch.object(rp.rs, 'allocate', side_effect=AssertionError('not allowed')):
            with patch.object(rp.rr, 'verify', side_effect=AssertionError('not allowed')):
                rp.verify(proof, commitment['root'], 'build')

    def test_odd_sibling_rule(self):
        report, commitment = self.make()
        proof = rp.prove(self.request, report, self.metadata, 'review')
        self.assertEqual(proof['siblings'][0], rp.leaf(commitment['context'], 2, proof['allocation']).hex())
        proof['siblings'][0] = 'a'*64
        with self.assertRaisesRegex(rp.rs.Invalid, 'duplicate itself'):
            rp.verify(proof, commitment['root'], 'review')

    def test_canonical_input_and_different_context(self):
        report, commitment = self.make()
        reordered = dict(reversed(list(report.items())))
        self.assertEqual(rp.commit(self.request, reordered, self.metadata), commitment)
        changed = copy.deepcopy(self.request)
        changed['contributors'].reverse()
        # The allocation stays the same, but exact request provenance changes.
        self.assertEqual(rp.rs.allocate(changed, self.metadata), report)
        self.assertNotEqual(rp.commit(changed, report, self.metadata)['root'], commitment['root'])

    def test_maximum_roster(self):
        request = {'budget': '1', 'contributors': [{'id': 'w'+str(i), 'weight': '1'} for i in range(1000)]}
        report, commitment = self.make(request)
        for identifier in ('w0', 'w1', 'w999'):
            proof = rp.prove(request, report, self.metadata, identifier)
            self.assertEqual(len(proof['siblings']), 10)
            self.assertLess(len(rp.rr.canonical_bytes(proof)), 4000)
            rp.verify(proof, commitment['root'], identifier)

    def test_cli_roundtrip_limits_and_no_overwrite(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            root = Path(directory)
            request, report, commitment, proof = [root / name for name in ('request.json', 'report.json', 'commitment.json', 'proof.json')]
            rp.rs.write_json(self.request, request)
            rp.rs.write_json(self.make()[0], report)
            args = ['--request', str(request), '--report', str(report)]
            self.assertEqual(rp.main(['commit'] + args + ['--output', str(commitment)]), 0)
            self.assertEqual(rp.main(['prove'] + args + ['--id', 'build', '--output', str(proof)]), 0)
            trusted = rp.rs.read_json(commitment)['root']
            verify_args = ['verify', '--proof', str(proof), '--root', trusted, '--id', 'build']
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rp.main(verify_args), 0)
            before = proof.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rp.main(['prove'] + args + ['--id', 'build', '--output', str(proof)]), 2)
                self.assertEqual(proof.read_bytes(), before)
                proof.write_text('{"x":1,"x":2}')
                self.assertEqual(rp.main(verify_args), 2)
                proof.write_bytes(b' ' * (rp.rs.MAX_BYTES + 1))
                self.assertEqual(rp.main(verify_args), 2)


if __name__ == '__main__':
    unittest.main()

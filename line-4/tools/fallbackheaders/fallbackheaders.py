#!/usr/bin/env python3
"""Compare response headers across OpenAPI status-selector fallbacks, offline."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys


SPEC = importlib.util.spec_from_file_location(
    'fallbackheaders_status',
    Path(__file__).resolve().parents[1] / 'statuscheck' / 'statuscheck.py')
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)
api = status.api


class Analyzer(status.Analyzer):
    def __init__(self, old, new):
        super().__init__(old, new)
        self.remapped_header_pairs = 0

    def operation(self, path, method, old_item, new_item):
        start = len(self.selector_groups)
        super().operation(path, method, old_item, new_item)
        groups = self.selector_groups[start:]
        if not groups:
            return
        before = status.selectors(self.old, old_item[method])
        after = status.selectors(self.new, new_item[method])
        for group in groups:
            old_key, new_key = group['old_selector'], group['new_selector']
            if old_key is None or new_key is None or old_key == new_key:
                continue
            self.remapped_header_pairs += 1
            # response_headers is inherited from HeaderCheck. It validates
            # case-insensitive names and refs and applies its visit budget.
            old_headers = self.response_headers(self.old, before[old_key])
            new_headers = self.response_headers(self.new, after[new_key])
            loc = api.pointer(api.pointer('/paths', path) + '/' + method + '/responses',
                              new_key) + '/headers'
            self.compare_headers(old_headers, new_headers, loc)

    def compare_headers(self, old_headers, new_headers, loc):
        for name in sorted(old_headers.keys() | new_headers.keys()):
            hloc = api.pointer(loc, name)
            if name not in new_headers:
                required = old_headers[name].get('required', False)
                self.emit('breaking' if required else 'review',
                          'fallback_response_header_removed', hloc,
                          'An old required response header is no longer guaranteed by '
                          'the selected response.' if required else
                          'An optional response header is absent from the selected response.')
                continue
            if name not in old_headers:
                self.emit('review', 'fallback_response_header_added', hloc,
                          'The selected response adds a header; review client tolerance.')
                continue
            old, new = old_headers[name], new_headers[name]
            if old.get('required', False) and not new.get('required', False):
                self.emit('breaking', 'fallback_response_header_not_guaranteed',
                          hloc + '/required',
                          'An old required response header can now be omitted.')
            if ('schema' in old) != ('schema' in new):
                self.emit('review', 'fallback_response_header_representation_changed',
                          hloc, 'Header switched between schema and content.')
            elif 'schema' in old:
                self.schema(old['schema'], new['schema'], hloc + '/schema', 'response')
                if old.get('explode', False) != new.get('explode', False):
                    self.emit('review', 'fallback_response_header_encoding_changed',
                              hloc + '/explode', 'Header serialization changed.')
            else:
                self.content(old['content'], new['content'], hloc + '/content', 'response')
            omit = {'schema', 'content', 'required', 'style', 'explode'}
            self.changed({k: v for k, v in old.items() if k not in omit},
                         {k: v for k, v in new.items() if k not in omit}, hloc,
                         'fallback_response_header_metadata_changed',
                         'Header annotation or extension changed; review client assumptions.')


def compare(old, new):
    analyzer = Analyzer(old, new)
    report = analyzer.run()
    report.update(extension='fallbackheaders-v1 (includes statuscheck and earlier analyzers)',
                  status_visits=analyzer.status_visits,
                  selector_groups=analyzer.selector_groups,
                  remapped_header_pairs=analyzer.remapped_header_pairs,
                  header_visits=analyzer.header_visits,
                  header_scope='common inline top-level operations; changed effective '
                               'status selectors with both responses present')
    return report


def demo():
    capture = Path(__file__).resolve().parents[1] / 'apidelta' / 'imd-openapi.json'
    old, digest = api.load(capture)
    old = copy.deepcopy(old)
    path = sorted(old['paths'])[0]
    method = sorted(old['paths'][path].keys() & api.METHODS)[0]
    old['paths'][path][method]['responses'] = {
        '2XX': {'description': 'Hypothetical general success', 'headers': {
            'X-Worker-Receipt': {'required': True, 'schema': {'type': 'string'}}}}}
    new = copy.deepcopy(old)
    new['paths'][path][method]['responses']['200'] = {
        'description': 'Hypothetical exact success'}
    report = compare(old, new)
    api.require(any(f['code'] == 'fallback_response_header_removed'
                    and f['severity'] == 'breaking' for f in report['findings']),
                'demo did not detect lost required response header')
    report.update(capture_sha256=digest,
                  baseline_source='https://api.imd.fun/openapi.json',
                  demo='Hypothetical 200 override of a 2XX response on a saved IMD path; '
                       'no described endpoint is called.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    diff = commands.add_parser('compare')
    diff.add_argument('old')
    diff.add_argument('new')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            report = demo()
        else:
            old, oh = api.load(args.old)
            new, nh = api.load(args.new)
            report = compare(old, new)
            report.update(old_sha256=oh, new_sha256=nh)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.command == 'demo' else {
            'breaking': 1, 'review_required': 3,
            'no_detected_breakage': 0}[report['status']]
    except (api.Invalid, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('fallbackheaders: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

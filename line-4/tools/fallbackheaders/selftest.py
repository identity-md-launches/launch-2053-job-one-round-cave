#!/usr/bin/env python3
"""Regression checks for response headers under status-selector overrides."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import fallbackheaders as tool


def response(headers=None):
    result = {'description': 'test'}
    if headers is not None:
        result['headers'] = headers
    return result


def header(required=True, kind='string'):
    return {'required': required, 'schema': {'type': kind}}


def doc(responses):
    return {'openapi': '3.1.0', 'paths': {'/probe': {'get': {'responses': responses}}}}


def codes(report):
    return {f['code'] for f in report['findings']}


class Tests(unittest.TestCase):
    def test_required_header_lost_at_exact_override(self):
        old = doc({'2XX': response({'X-Receipt': header()})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response()
        report = tool.compare(old, new)
        self.assertEqual(report['status'], 'breaking')
        self.assertIn('fallback_response_header_removed', codes(report))
        self.assertEqual(report['remapped_header_pairs'], 1)
        self.assertEqual(report['selector_groups'][0]['statuses'], [200])
        self.assertEqual(next(f['location'] for f in report['findings']
                              if f['code'] == 'fallback_response_header_removed'),
                         '/paths/~1probe/get/responses/200/headers/x-receipt')

    def test_optional_header_lost_requires_review(self):
        old = doc({'default': response({'X-Receipt': header(False)})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response()
        report = tool.compare(old, new)
        self.assertEqual(report['status'], 'review_required')
        self.assertIn('fallback_response_header_removed', codes(report))

    def test_guarantee_relaxed_and_case_insensitive(self):
        old = doc({'2XX': response({'X-Receipt': header()})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response(
            {'x-receipt': header(False)})
        report = tool.compare(old, new)
        self.assertIn('fallback_response_header_not_guaranteed', codes(report))
        self.assertNotIn('fallback_response_header_removed', codes(report))

    def test_schema_reused_in_response_direction(self):
        old = doc({'2XX': response({'X-Receipt': header(kind='string')})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response(
            {'X-Receipt': header(kind='integer')})
        self.assertIn('schema_type_incompatible', codes(tool.compare(old, new)))

    def test_content_representation_and_refs(self):
        old = doc({'default': {'$ref': '#/components/responses/base'}})
        old['components'] = {'responses': {'base': response({
            'X-Receipt': {'required': True, 'content': {
                'application/json': {'schema': {'type': 'string'}}}}})}}
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response({
            'X-Receipt': {'required': True, 'content': {
                'application/json': {'schema': {'type': 'integer'}}}}})
        self.assertIn('schema_type_incompatible', codes(tool.compare(old, new)))

    def test_no_remap_keeps_inherited_header_check(self):
        old = doc({'200': response({'X-Receipt': header()})})
        new = doc({'200': response()})
        report = tool.compare(old, new)
        self.assertIn('response_header_removed', codes(report))
        self.assertEqual(report['remapped_header_pairs'], 0)

    def test_ignored_content_type_and_added_header(self):
        old = doc({'2XX': response({'Content-Type': header()})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response({
            'X-Trace': header(False)})
        report = tool.compare(old, new)
        self.assertNotIn('fallback_response_header_removed', codes(report))
        self.assertIn('fallback_response_header_added', codes(report))

    def test_malformed_and_budget_refusal(self):
        old = doc({'2XX': response({'X-Receipt': header()})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response({
            'X-Receipt': {'required': 'yes', 'schema': {}}})
        with self.assertRaises(tool.api.Invalid):
            tool.compare(old, new)
        import unittest.mock
        new['paths']['/probe']['get']['responses']['200'] = response()
        with unittest.mock.patch.object(tool.status.previous.previous,
                                        'MAX_HEADER_VISITS', 0):
            # The inherited response_headers method counts the general map.
            with self.assertRaises(tool.api.Invalid):
                tool.compare(old, new)

    def test_deterministic_nonmutating_and_cli(self):
        old = doc({'2XX': response({'X-Receipt': header()})})
        new = copy.deepcopy(old)
        new['paths']['/probe']['get']['responses']['200'] = response()
        saved = copy.deepcopy((old, new))
        first = tool.compare(old, new)
        self.assertEqual((old, new), saved)
        self.assertEqual(first, tool.compare(old, new))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(['demo']), 0)
        root = Path.cwd() / 'test/scratch'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            a, b = Path(folder) / 'old.json', Path(folder) / 'new.json'
            a.write_text(json.dumps(old))
            b.write_text(json.dumps(new))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(['compare', str(a), str(b)]), 1)


if __name__ == '__main__':
    unittest.main()

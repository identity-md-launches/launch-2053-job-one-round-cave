#!/usr/bin/env python3
"""Check fallback-header analysis across the digest/CRC ZIP trust boundary."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import api_bundle as bundle


def header(required=True, kind='string'):
    return {'required': required, 'schema': {'type': kind}}


def response(headers=None):
    return {'description': 'Illustrative response', 'headers': headers or {}}


class FallbackBundleTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='fallback-tests-', dir=scratch)
        self.root = Path(self.temp.name)
        self.doc = {'openapi': '3.1.0', 'paths': {'/items': {'get': {
            'operationId': 'listItems', 'responses': {
                '2XX': response({'X-Receipt': header()})}}}}}

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, document):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(zipfile.ZipInfo('docs/openapi.json'), json.dumps(document))
            archive.writestr(zipfile.ZipInfo('inert.py'), 'raise RuntimeError("do not execute")')
        return path

    def compare(self, old, new, **kwargs):
        a, b = self.archive('old.zip', old), self.archive('new.zip', new)
        return bundle.compare(a, b, member='docs/openapi.json', fallback_headers=True,
            old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),
            new_sha256=hashlib.sha256(b.read_bytes()).hexdigest(), **kwargs)

    def override(self, headers=None):
        new = copy.deepcopy(self.doc)
        new['paths']['/items']['get']['responses']['200'] = response(headers)
        return new

    def codes(self, report):
        return {f['code'] for f in report['findings']}

    def test_approved_public_capture_no_extraction(self):
        capture = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        report = self.compare(capture, capture)
        self.assertEqual(report['status'], 'no_detected_breakage')
        self.assertEqual(report['operations_compared'], 5)
        self.assertEqual(report['status_visits'], 2500)
        self.assertEqual(report['remapped_header_pairs'], 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['new.zip', 'old.zip'])
        for side in report['bundle_inputs'].values():
            self.assertTrue(side['approved_sha256_checked'])
            self.assertTrue(side['all_payloads_crc_checked'])
            self.assertEqual(len(side['checked_files']), 2)

    def test_lost_required_header_is_break_and_keeps_reviews(self):
        report = self.compare(self.doc, self.override())
        self.assertEqual(report['status'], 'breaking')
        self.assertEqual(report['remapped_header_pairs'], 1)
        self.assertEqual(report['selector_groups'][0]['statuses'], [200])
        self.assertTrue({'fallback_response_header_removed', 'response_selector_changed',
                         'response_status_changed'} <= self.codes(report))
        finding = next(f for f in report['findings'] if f['code'] == 'fallback_response_header_removed')
        self.assertEqual(finding['location'], '/paths/~1items/get/responses/200/headers/x-receipt')
        a, b = self.root / 'old.zip', self.root / 'new.zip'
        for options in ({}, {'statuses': True}, {'parameters': True}):
            prior = bundle.compare(a, b, member='docs/openapi.json', **options)
            self.assertEqual(prior['status'], 'review_required')
            self.assertNotIn('remapped_header_pairs', prior)

    def test_optional_and_relaxed_guarantees(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['responses']['2XX']['headers']['X-Receipt']['required'] = False
        self.assertEqual(self.compare(old, self.override())['status'], 'review_required')
        report = self.compare(self.doc, self.override({'x-receipt': header(False)}))
        self.assertIn('fallback_response_header_not_guaranteed', self.codes(report))
        self.assertNotIn('fallback_response_header_removed', self.codes(report))

    def test_schema_direction_and_local_references(self):
        old = copy.deepcopy(self.doc)
        old['components'] = {'responses': {'base': old['paths']['/items']['get']['responses']['2XX']}}
        old['paths']['/items']['get']['responses'] = {'2XX': {'$ref': '#/components/responses/base'}}
        new = copy.deepcopy(old)
        new['paths']['/items']['get']['responses']['200'] = response({'X-Receipt': header(kind='integer')})
        self.assertIn('schema_type_incompatible', self.codes(self.compare(old, new)))
        wider = copy.deepcopy(self.doc)
        wider['paths']['/items']['get']['responses']['2XX'] = response({'X-Receipt': header(kind='number')})
        narrow = copy.deepcopy(wider)
        narrow['paths']['/items']['get']['responses']['200'] = response({'X-Receipt': header(kind='integer')})
        self.assertNotIn('schema_type_incompatible', self.codes(self.compare(wider, narrow)))
        self.assertIn('schema_type_incompatible', self.codes(self.compare(narrow, wider)))

    def test_same_selector_keeps_inherited_findings(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['responses'] = {'200': response({'X-Receipt': header()})}
        new = copy.deepcopy(old)
        new['paths']['/items']['get']['responses']['200'] = response()
        report = self.compare(old, new)
        self.assertIn('response_header_removed', self.codes(report))
        self.assertEqual(report['remapped_header_pairs'], 0)

    def test_status_grouping_missing_coverage_and_content_type(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['responses'] = {'default': response({'Content-Type': header()})}
        new = copy.deepcopy(old)
        new['paths']['/items']['get']['responses']['2XX'] = response({'X-Trace': header(False)})
        report = self.compare(old, new)
        self.assertEqual(report['selector_groups'][0]['statuses'], list(range(200, 300)))
        self.assertNotIn('fallback_response_header_removed', self.codes(report))
        self.assertIn('fallback_response_header_added', self.codes(report))
        new['paths']['/items']['get']['responses'] = {}
        self.assertEqual(self.compare(old, new)['remapped_header_pairs'], 0)

    def test_all_prior_analyzers_and_deterministic_result(self):
        new = self.override()
        new['paths']['/items']['get']['operationId'] = 'renamed'
        new['paths']['/items']['get']['servers'] = [{'url': '/moved'}]
        report = self.compare(self.doc, new)
        self.assertTrue({'operation_id_changed', 'server_destination_removed',
            'fallback_response_header_removed'} <= self.codes(report))
        self.assertEqual(report, self.compare(self.doc, new))

    def test_approval_crc_directory_and_cancellation_precede_analysis(self):
        path = self.archive('bad.zip', self.doc)
        with mock.patch.object(bundle.fallbackheaders, 'compare') as analyzer:
            for options in ({'old_sha256': '1' * 64}, {'directory_bytes': 1},
                            {'nodes': 1}, {'cancelled': lambda: True}):
                with self.subTest(options=list(options)), self.assertRaises(ValueError):
                    bundle.compare(path, path, fallback_headers=True, **options)
            path.write_bytes(path.read_bytes().replace(b'do not execute', b'DO NOT EXECUTE'))
            with self.assertRaises(zipfile.BadZipFile):
                bundle.compare(path, path, member='docs/openapi.json', fallback_headers=True)
            analyzer.assert_not_called()

    def test_invalid_headers_refs_and_budgets_refuse_whole_result(self):
        for headers in ({'X': {'required': 'yes', 'schema': {}}},
                        {'X': {'$ref': 'https://example.invalid/header'}}):
            with self.subTest(headers=headers), self.assertRaises(ValueError):
                self.compare(self.doc, self.override(headers))
        with mock.patch.object(bundle.fallbackheaders.status, 'MAX_STATUS_VISITS', 499):
            with self.assertRaisesRegex(ValueError, 'status visits'):
                self.compare(self.doc, self.override())
        with mock.patch.object(bundle.fallbackheaders.status.previous.previous, 'MAX_HEADER_VISITS', 0):
            with self.assertRaisesRegex(ValueError, 'header visits'):
                self.compare(self.doc, self.override())

    def test_cli_all_exits_and_combined_flags(self):
        a = self.archive('a.zip', self.doc)
        invalid = self.override({'X': {'required': 'yes', 'schema': {}}})
        for document, expected in ((self.doc, 0), (self.override(), 1), (invalid, 2),
                                    (self.override({'X-Receipt': header()}), 3)):
            b = self.archive('b.zip', document)
            command = [sys.executable, '-B', bundle.__file__, str(a), str(b),
                '--member', 'docs/openapi.json', '--old-sha256', hashlib.sha256(a.read_bytes()).hexdigest(),
                '--new-sha256', hashlib.sha256(b.read_bytes()).hexdigest(), '--fallback-headers',
                '--statuses', '--parameters', '--servers', '--oauth']
            with self.subTest(expected=expected):
                result = subprocess.run(command, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                if expected != 2:
                    self.assertTrue(report['extension'].startswith('fallbackheaders-v1'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Focused ZIP merge behavior and failure isolation checks."""
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from zipmerge import Rejected, process


class MergeTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='zipmerge-test-', dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = self.pack('a.zip', [('docs/a.txt', b'a'), ('empty/', b'')])
        self.b = self.pack('b.zip', [('docs/b.txt', b'bb')])

    def pack(self, filename, members):
        archive = self.root / filename
        with zipfile.ZipFile(archive, 'w') as writer:
            for name, data in members:
                writer.writestr(name, data)
        return {'archive': archive,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}

    def test_shared_directories_and_exact_limits(self):
        output = self.root / 'joined'
        result = process([self.a, self.b], output, merge_entries=3,
                         merge_nodes=4, merge_bytes=3)
        self.assertEqual(result['totals'], dict(archives=2, entries=3,
                                                nodes=4, uncompressed_bytes=3))
        self.assertEqual((output / 'docs/a.txt').read_bytes(), b'a')
        self.assertEqual((output / 'docs/b.txt').read_bytes(), b'bb')
        self.assertTrue((output / 'empty').is_dir())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ['a.zip', 'b.zip', 'joined'])

    def test_plan_creates_nothing(self):
        self.assertEqual(process([self.a, self.b])['mode'], 'plan')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['a.zip', 'b.zip'])

    def test_shared_limits_refuse_without_output(self):
        for options in [dict(merge_entries=2), dict(merge_nodes=3),
                        dict(merge_bytes=2), dict(max_archives=1)]:
            with self.subTest(options=options):
                output = self.root / 'joined'
                with self.assertRaises(Rejected):
                    process([self.a, self.b], output, **options)
                self.assertFalse(output.exists())

    def test_file_collision(self):
        duplicate = self.pack('duplicate.zip', [('docs/a.txt', b'different')])
        with self.assertRaisesRegex(Rejected, 'collision'):
            process([self.a, duplicate], self.root / 'joined')
        self.assertFalse((self.root / 'joined').exists())

    def test_case_and_type_collisions(self):
        variants = [[('Docs/c.txt', b'c')], [('docs', b'c')],
                    [('empty', b'c')]]
        for index, members in enumerate(variants):
            other = self.pack('variant' + str(index) + '.zip', members)
            with self.subTest(members=members), self.assertRaisesRegex(Rejected, 'collision'):
                process([self.a, other])

    def test_wrong_digest_and_replaced_archive(self):
        wrong = dict(self.b, sha256='0' * 64)
        with self.assertRaisesRegex(Rejected, 'SHA-256'):
            process([self.a, wrong], self.root / 'joined')
        old = dict(self.b)
        self.pack('b.zip', [('docs/b.txt', b'changed')])
        with self.assertRaisesRegex(Rejected, 'SHA-256'):
            process([self.a, old], self.root / 'joined')
        self.assertFalse((self.root / 'joined').exists())

    def test_unsafe_later_archive_blocks_all(self):
        unsafe = self.pack('unsafe.zip', [('../escape', b'x')])
        with self.assertRaises(Rejected):
            process([self.a, unsafe], self.root / 'joined')
        self.assertFalse((self.root / 'joined').exists())

    def test_symlink_member_blocks_all(self):
        info = zipfile.ZipInfo('link')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        unsafe = self.pack('link.zip', [(info, b'target')])
        with self.assertRaisesRegex(Rejected, 'link or special'):
            process([self.a, unsafe], self.root / 'joined')
        self.assertFalse((self.root / 'joined').exists())

    def test_corrupt_later_payload_blocks_all(self):
        bad = self.pack('bad.zip', [('docs/c.txt', b'abcd')])
        data = bytearray(bad['archive'].read_bytes())
        name_len, extra_len = struct.unpack_from('<HH', data, 26)
        data[30 + name_len + extra_len] ^= 1
        bad['archive'].write_bytes(data)
        bad['sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(zipfile.BadZipFile):
            process([self.a, bad], self.root / 'joined')
        self.assertFalse((self.root / 'joined').exists())

    def test_later_extraction_failure_removes_stage(self):
        from zipmerge import gate_process
        calls = []
        def fail_second_extract(*args, **kwargs):
            calls.append(args)
            if len(calls) == 4:
                raise Rejected('later extraction failed')
            return gate_process(*args, **kwargs)
        with patch('zipmerge.gate_process', side_effect=fail_second_extract):
            with self.assertRaisesRegex(Rejected, 'later extraction failed'):
                process([self.a, self.b], self.root / 'joined')
        self.assertEqual(len(calls), 4)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['a.zip', 'b.zip'])

    def test_output_existing_or_symlink(self):
        existing = self.root / 'existing'
        existing.mkdir()
        with self.assertRaisesRegex(Rejected, 'already exist'):
            process([self.a], existing)
        link = self.root / 'link-output'
        link.symlink_to(existing)
        with self.assertRaisesRegex(Rejected, 'symlink'):
            process([self.a], link)

    def test_invalid_declarations_before_inspection(self):
        with patch('zipmerge.gate_process') as inspector:
            with self.assertRaises(Rejected):
                process([self.a, dict(self.b, extra=True)])
            inspector.assert_not_called()

    def test_cancel_and_deadline(self):
        with self.assertRaisesRegex(Rejected, 'cancelled'):
            process([self.a], cancelled=lambda: True)
        with patch('zipmerge.time.monotonic', side_effect=[0.0, 1.0]):
            with self.assertRaisesRegex(Rejected, 'time budget'):
                process([self.a], seconds=0.5)

    def test_invalid_limits(self):
        for name in ['max_archives', 'merge_entries', 'merge_nodes', 'merge_bytes',
                     'entries', 'directory_bytes', 'archive_bytes', 'nodes',
                     'file_bytes', 'total_bytes', 'ratio']:
            with self.subTest(name=name), self.assertRaises(Rejected):
                process([self.a], **{name: 0})

    def test_cli(self):
        script = str(Path(__file__).with_name('zipmerge.py'))
        args = [sys.executable, '-B', script, 'plan', '--archive', str(self.a['archive']),
                '--sha256', self.a['sha256']]
        good = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['totals']['entries'], 2)
        bad = subprocess.run(args + ['--merge-nodes', '1'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse(json.loads(bad.stdout)['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

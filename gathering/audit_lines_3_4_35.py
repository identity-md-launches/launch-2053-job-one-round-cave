#!/usr/bin/env python3
"""Run reviewed line 3/4 checks and demos without writing into either line."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(line):
    results = []
    for folder in sorted((ROOT / ('line-%d/tools' % line)).iterdir()):
        if not folder.is_dir():
            continue
        test = str((folder / 'selftest.py').relative_to(ROOT))
        main = str((folder / (folder.name + '.py')).relative_to(ROOT))
        commands = [('check', ['python3', '-B', test], 0),
                    ('demo', ['python3', '-B', main, 'demo'],
                     1 if folder.name == 'rewardcompare' else 0)]
        for kind, documented, expected in commands:
            command = documented
            adaptation = None
            if kind == 'check' and folder.name == 'apidelta':
                command = ['python3', '-B', 'gathering/audit_apidelta_35.py']
                adaptation = ('Unchanged suite; TemporaryDirectory redirected from line folder '
                              'to test/scratch/audit-lines-3-4-35.')
            done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
            combined = done.stdout + done.stderr
            match = re.search(r'Ran (\d+) tests?', combined)
            results.append(dict(line=line, tool=folder.name, kind=kind,
                documented_command=documented, command=command, adaptation=adaptation,
                expected_exit=expected, actual_exit=done.returncode,
                passed=done.returncode == expected,
                unittest_cases=int(match.group(1)) if match else 0,
                stdout_sha256=hashlib.sha256(done.stdout.encode()).hexdigest(),
                evidence=combined[-900:]))
    return results


def main():
    (ROOT / 'test/scratch/audit-lines-3-4-35').mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = [row for group in pool.map(run, (3, 4)) for row in group]
    sources = []
    for line in (3, 4):
        for path in sorted((ROOT / ('line-%d/tools' % line)).glob('*/*.py')):
            sources.append(dict(path=str(path.relative_to(ROOT)),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(round=35, scope='Every tool selftest and demo in lines 3 and 4',
        source_review=('All Python sources parsed and their imports/call targets and I/O '
                       'sites reviewed before execution. Shared loaders, FallbackHeaders '
                       'implementation/tests and exceptional test paths read in full. '
                       'RPC methods are mocked in offline tests. No described API operation called.'),
        sources=sources, results=rows)
    raw = json.dumps(result, indent=2) + '\n'
    if len(raw.encode()) > 100000:
        raise ValueError('Evidence exceeds the submission byte limit')
    (ROOT / 'gathering/audit-lines-3-4-35.json').write_text(raw)
    for line in (3, 4):
        group = [r for r in rows if r['line'] == line]
        print('Line %d: %d commands, %d unit tests, %d unexpected results' %
              (line, len(group), sum(r['unittest_cases'] for r in group),
               sum(not r['passed'] for r in group)))
    for row in rows:
        if not row['passed']:
            print(json.dumps(row, indent=2))
    return int(any(not row['passed'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())

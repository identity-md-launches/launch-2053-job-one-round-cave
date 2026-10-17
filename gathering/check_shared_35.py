#!/usr/bin/env python3
"""Replay shared checks in-place and without line folders, then compare captures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ('selftest.py', 'parameter_selftest.py', 'status_selftest.py', 'fallback_selftest.py')
DEMOS = ('demo.py', 'server_demo.py', 'parameter_demo.py', 'status_demo.py', 'fallback_demo.py')


def main():
    source = ROOT / 'shared/api_bundle'
    provenance = json.loads((source / 'SOURCES.json').read_text())
    for name, row in provenance.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == row['sha256'], name
        assert hashlib.sha256((ROOT / row['source']).read_bytes()).hexdigest() == row['source_sha256'], name
    scratch = ROOT / 'test/scratch/gathering35/isolation'
    isolated = scratch / 'shared/api_bundle'
    shutil.copytree(source, isolated, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    assert not any(scratch.glob('line-*'))
    for place, cwd, label in ((source, ROOT, 'in-place'), (isolated, scratch, 'isolated')):
        rows = []
        for name in CHECKS + DEMOS:
            done = subprocess.run([sys.executable, '-B', str(place / name)],
                cwd=cwd, capture_output=True, text=True, timeout=60)
            output = done.stdout + done.stderr
            match = re.search(r'Ran (\d+) tests?', output)
            row = dict(command=name, exit=done.returncode, passed=done.returncode == 0,
                       unittest_cases=int(match.group(1)) if match else 0,
                       evidence=output[-900:], stdout_sha256=hashlib.sha256(done.stdout.encode()).hexdigest())
            rows.append(row)
            print(label, name, 'PASS' if row['passed'] else 'FAIL', row['unittest_cases'])
        report = dict(mode=label, sources_verified=len(provenance),
                      tests=sum(r['unittest_cases'] for r in rows), rows=rows,
                      passed=all(r['passed'] for r in rows))
        suffix = 'shared-check-results' if label == 'in-place' else 'shared-isolation'
        (ROOT / f'gathering/{suffix}-35.json').write_text(json.dumps(report, indent=2)+'\n')
        if not report['passed']:
            return 1
    sys.path.insert(0, str(source))
    import api_bundle
    paths, digests = [], []
    for index, capture in enumerate((source / 'imd-openapi.json',
                                    ROOT / 'gathering/imd-openapi-current-35.json')):
        path = scratch / f'public-{index}.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(zipfile.ZipInfo('docs/openapi.json'), capture.read_bytes())
        paths.append(path)
        digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
    live = api_bundle.compare(*paths, member='docs/openapi.json',
        old_sha256=digests[0], new_sha256=digests[1], fallback_headers=True, seconds=10)
    live.update(source='https://api.imd.fun/openapi.json',
        observation='Read-only public description fetched on 2026-10-17; no described API operation called.',
        current_capture_sha256=hashlib.sha256((ROOT/'gathering/imd-openapi-current-35.json').read_bytes()).hexdigest())
    (ROOT / 'gathering/shared-live-35.json').write_text(json.dumps(live, indent=2)+'\n')
    print('Public captures:', live['status'], live['operations_compared'], 'operations,', live['status_visits'], 'statuses')
    return int(live['status'] != 'no_detected_breakage')


if __name__ == '__main__':
    raise SystemExit(main())

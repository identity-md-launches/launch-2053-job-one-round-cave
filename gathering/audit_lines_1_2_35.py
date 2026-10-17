#!/usr/bin/env python3
"""Replay reviewed line 1/2 checks and demos; write bounded evidence only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def commands(line):
    jobs = []
    for folder in sorted((ROOT / f'line-{line}/tools').iterdir()):
        if not folder.is_dir():
            continue
        main = folder / (folder.name + '.py')
        suite = folder / 'selftest.py'
        if suite.exists():
            jobs.append((suite, [], 0, 'check'))
        if folder.name in ('workplan', 'optplan', 'gatecheck', 'gateplan'):
            jobs.append((main, ['--self-test'], 0, 'inline-check'))
        demo = folder / 'demo.py'
        if demo.exists():
            jobs.append((demo, [], 0, 'demo'))
        elif (folder / 'swarm_demo.py').exists():
            jobs.append((folder / 'swarm_demo.py', [], 0, 'demo'))
        elif folder.name == 'budgetpath':
            jobs.append((main, [str(folder.relative_to(ROOT) / 'example.json')], 0, 'demo'))
        elif line == 1:
            options = {
                'workplan': ['--demo', '--workers', '2', '--budget', '25'],
                'optplan': ['--idle-demo', '--workers', '2'],
                'replan': ['--demo', '--workers', '2', '--budget', '27'],
                'slackmap': ['--demo', '--budget', '10'],
                'goalslice': ['--demo', '--explain'],
                'gateplan': ['--demo', '--workers', '1', '--budget', '7'],
            }.get(folder.name, ['--demo'])
            jobs.append((main, options, 0, 'demo'))
    if line == 1:
        main = ROOT / 'line-1/tools/gateplan/gateplan.py'
        jobs.extend([(main, ['--demo', '--workers', '1', '--budget', '6'], 2, 'refusal'),
                     (main, ['--demo', '--max-states', '1'], 1, 'refusal')])
    return jobs


def run_line(line):
    result = []
    for script, args, expected, kind in commands(line):
        command = ['python3', '-B', str(script.relative_to(ROOT)), *args]
        done = subprocess.run(command, cwd=ROOT, capture_output=True,
                              text=True, timeout=60)
        output = done.stdout + done.stderr
        match = re.search(r'Ran (\d+) tests?', output)
        result.append({'line': line, 'tool': script.parent.name, 'kind': kind,
                       'command': command, 'expected_exit': expected,
                       'actual_exit': done.returncode,
                       'passed': done.returncode == expected,
                       'unittest_cases': int(match.group(1)) if match else 0,
                       'stdout_sha256': hashlib.sha256(done.stdout.encode()).hexdigest(),
                       'evidence': output[-900:]})
    return result


def main():
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = [row for group in executor.map(run_line, (1, 2)) for row in group]
    report = {'round': 35, 'commands': rows, 'summary': []}
    for line in (1, 2):
        selected = [row for row in rows if row['line'] == line]
        report['summary'].append({'line': line,
            'tools': len({row['tool'] for row in selected}),
            'commands': len(selected),
            'unittest_cases': sum(row['unittest_cases'] for row in selected),
            'failures': sum(not row['passed'] for row in selected)})
    encoded = json.dumps(report, indent=2) + '\n'
    if len(encoded.encode()) >= 100000:
        raise ValueError('evidence exceeds submission file limit')
    (ROOT / 'gathering/audit-lines-1-2-35.json').write_text(encoded)
    print(json.dumps(report['summary'], indent=2))
    for row in rows:
        if not row['passed']:
            print(json.dumps(row, indent=2))
    return int(any(not row['passed'] for row in rows))


if __name__ == '__main__':
    sys.exit(main())

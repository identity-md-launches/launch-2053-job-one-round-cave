#!/usr/bin/env python3
"""A required response header disappearing behind an approved ZIP override."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import api_bundle


def demo():
    capture = Path(__file__).with_name('imd-openapi.json').read_bytes()
    old = json.loads(capture)
    operation = old['paths']['/requests/quote']['post']
    operation['responses'] = {'2XX': {
        'description': 'Illustrative success response',
        'headers': {'X-Worker-Receipt': {
            'required': True, 'schema': {'type': 'string'}}}}}
    new = copy.deepcopy(old)
    new['paths']['/requests/quote']['post']['responses']['200'] = {
        'description': 'Illustrative success response'}
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fallback-bundle-', dir=scratch) as folder:
        paths, digests = [], []
        for name, document in [('old', old), ('new', new)]:
            path = Path(folder) / (name + '.zip')
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(zipfile.ZipInfo('docs/openapi.json'), json.dumps(document))
            paths.append(path)
            digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
        options = dict(member='docs/openapi.json', old_sha256=digests[0],
                       new_sha256=digests[1], seconds=10)
        before = api_bundle.compare(*paths, statuses=True, **options)
        after = api_bundle.compare(*paths, fallback_headers=True, **options)
        unchanged = api_bundle.compare(paths[0], paths[0],
            member=options['member'], old_sha256=digests[0], new_sha256=digests[0],
            fallback_headers=True)
        assert before['status'] == 'review_required'
        assert after['status'] == 'breaking' and after['remapped_header_pairs'] == 1
        assert any(f['code'] == 'fallback_response_header_removed' and
                   f['severity'] == 'breaking' for f in after['findings'])
        assert unchanged['status'] == 'no_detected_breakage'
        assert not unchanged['findings']
        assert len(list(Path(folder).iterdir())) == 2
        return dict(baseline_source='https://api.imd.fun/openapi.json',
            capture_sha256=hashlib.sha256(capture).hexdigest(),
            trial='Invented 200 override omits the required header of an invented 2XX response on a saved IMD path.',
            network_used=False, extracted_files=0,
            status_mode_result=before['status'], unchanged_result=unchanged['status'],
            changed=after)


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))

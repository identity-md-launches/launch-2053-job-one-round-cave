#!/usr/bin/env python3
"""Offline demonstration using the shipped historical IMD public capture."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from zipmerge import Rejected, local_path, process


def main():
    source_dir = Path(__file__).resolve().parents[1] / 'safezip'
    capture = (source_dir / 'imd-openapi.json').read_bytes()
    provenance = (source_dir / 'sample-source.json').read_bytes()
    assert hashlib.sha256(capture).hexdigest() == (
        'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a')
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='zipmerge-demo-', dir=scratch) as temporary:
        root = Path(temporary)
        specs = []
        for filename, member, data in [
                ('capture.zip', 'docs/imd/openapi.json', capture),
                ('source.zip', 'docs/imd/source.json', provenance)]:
            archive = root / filename
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
                writer.writestr(member, data)
            specs.append({'archive': archive,
                          'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
        plan = process(specs, merge_bytes=len(capture) + len(provenance),
                       merge_nodes=4, seconds=10)
        assert plan['totals']['nodes'] == 4
        try:
            process(specs, root / 'refused', merge_bytes=len(capture))
        except Rejected as error:
            refusal = str(error)
        else:
            raise AssertionError('combined byte overrun was accepted')
        assert not (root / 'refused').exists()
        output = root / 'combined'
        report = process(specs, output, merge_nodes=4, seconds=10)
        assert (output / 'docs/imd/openapi.json').read_bytes() == capture
        assert (output / 'docs/imd/source.json').read_bytes() == provenance
        print(json.dumps({'ok': True, 'network_used': False,
                          'historical_public_source': 'https://api.imd.fun/openapi.json',
                          'capture_bytes': len(capture), 'shared_directories': True,
                          'too_small_shared_budget_refused': refusal,
                          'merged_bytes_identical': True, 'report': report}, indent=2))


if __name__ == '__main__':
    main()

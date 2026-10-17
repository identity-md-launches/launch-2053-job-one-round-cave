#!/usr/bin/env python3
"""Verify actual delivery bytes, inherited pixels, records and unchanged lines."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ['line-1', 'line-2', 'line-3', 'line-4', 'gathering']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads((ROOT / path).read_text())


def png(path):
    raw = path.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    at, parts, dimensions = 8, [], None
    while at < len(raw):
        length = int.from_bytes(raw[at:at+4], 'big')
        kind, payload = raw[at+4:at+8], raw[at+8:at+8+length]
        assert len(payload) == length
        assert zlib.crc32(kind + payload) & 0xffffffff == int.from_bytes(raw[at+8+length:at+12+length], 'big')
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            assert width == height == 1254 and (depth, color, compression, filtering, interlace) == (8, 2, 0, 0, 0)
            dimensions = [width, height]
        elif kind == b'IDAT':
            parts.append(payload)
        at += length + 12
        if kind == b'IEND':
            break
    assert dimensions and at == len(raw)
    width, height = dimensions
    stride = width * 3
    scan = zlib.decompress(b''.join(parts))
    assert len(scan) == (stride + 1) * height
    pixels = bytearray(width * height * 3)
    for y in range(height):
        filtering = scan[y * (stride + 1)]
        assert filtering in range(5)
        for x in range(stride):
            i = y * stride + x
            a = pixels[i-3] if x >= 3 else 0
            b = pixels[i-stride] if y else 0
            c = pixels[i-stride-3] if y and x >= 3 else 0
            p = a + b - c
            pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
            predictor = (0, a, b, (a+b)//2, a if pa <= pb and pa <= pc else b if pb <= pc else c)[filtering]
            pixels[i] = (scan[y * (stride + 1) + x + 1] + predictor) & 255
    return dimensions, pixels


def jpeg(path):
    raw = path.read_bytes()
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9' and len(raw) <= 100000
    at = 2
    while at < len(raw):
        assert raw[at] == 255
        kind, size = raw[at+1], int.from_bytes(raw[at+2:at+4], 'big')
        if kind in (192, 193, 194):
            height, width = struct.unpack('>HH', raw[at+5:at+9])
            assert width == height == 512
            return [width, height]
        at += size + 2
    raise AssertionError('missing JPEG dimensions')


class Gallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.records, self.sections = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and re.fullmatch(r'(line-[1-4]|gathering)/\d{2}\.json', attrs.get('href', '')):
            self.records.append(attrs['href'])
        if tag == 'section':
            self.sections.append(attrs.get('id'))
        assert not (tag == 'script' and attrs.get('src')), 'external script'
        assert not (tag == 'link' and attrs.get('rel') == 'stylesheet'), 'external stylesheet'


def main():
    wall = ROOT / 'artifacts/gathering/wall-v16.png'
    previous = ROOT / 'artifacts/gathering/wall-v15.png'
    record = read_json('dist/gathering/35.json')
    assert set(record) == {'name', 'image', 'attributes'}
    assert len(record['attributes']) == 6
    attrs = {item['trait_type']: item['value'] for item in record['attributes']}
    assert set(attrs) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert (attrs['Cave'], attrs['Wall'], attrs['Number'], attrs['One thing']) == ('Lava', 'Gathering', 35, 'Gathering')
    assert type(attrs['Number']) is int
    assert record['image'] == 'https://api.imd.fun/artifacts/' + sha(wall.read_bytes())
    dimensions, pixels = png(wall)
    old_dimensions, old_pixels = png(previous)
    assert dimensions == old_dimensions
    preservation = read_json('gathering/preservation-35.json')
    assert preservation['previous_sha256'] == sha(previous.read_bytes())
    assert read_json('dist/gathering/34.json')['image'].endswith(sha(previous.read_bytes()))
    assert preservation['wall_sha256'] == sha(wall.read_bytes())
    left, top, width, height = preservation['mark_rectangle']
    changed = outside = 0
    for y in range(dimensions[1]):
        for x in range(dimensions[0]):
            i = (y * dimensions[0] + x) * 3
            if pixels[i:i+3] != old_pixels[i:i+3]:
                changed += 1
                if not (left <= x < left+width and top <= y < top+height):
                    outside += 1
    assert changed == preservation['changed_pixels'] > 500
    assert outside == preservation['pixels_changed_outside'] == 0
    assert (ROOT / 'artifacts/gathering/wall.png').read_bytes() == wall.read_bytes()
    preview = ROOT / 'dist/gathering/35.jpg'
    thumb_dimensions = jpeg(preview)
    assert read_json('dist/goals.json') == [
        {'line': n, 'goal': (ROOT / f'line-{n}/GOAL.md').read_text().strip()}
        for n in range(1, 5)]
    parser = Gallery()
    parser.feed((ROOT / 'dist/index.html').read_text())
    assert parser.sections == GROUPS
    expected, painted, placeholders = [], 0, 0
    for folder in GROUPS:
        for path in sorted((ROOT / 'dist' / folder).glob('[0-9][0-9].json'), reverse=True):
            item = json.loads(path.read_text())
            expected.append(folder + '/' + path.name)
            assert re.fullmatch(r'https://api\.imd\.fun/artifacts/[0-9a-f]{64}', item['image'])
            if item['name'] == 'Not painted yet':
                placeholders += 1
                assert not path.with_suffix('.jpg').exists()
            else:
                painted += 1
        actual = [p for p in parser.records if p.startswith(folder + '/') and
                  read_json('dist/' + p)['name'] != 'Not painted yet']
        assert actual == sorted(actual, reverse=True)
    assert sorted(parser.records) == sorted(expected)
    for target, info in read_json('shared/api_bundle/SOURCES.json').items():
        assert sha((ROOT / 'shared/api_bundle' / target).read_bytes()) == info['sha256']
        assert sha((ROOT / info['source']).read_bytes()) == info['source_sha256']
    rows = read_json('gathering/audit-lines-1-2-35.json')['commands'] + read_json('gathering/audit-lines-3-4-35.json')['results']
    assert len(rows) == 107 and all(row['passed'] for row in rows)
    assert sum(row['unittest_cases'] for row in rows) == 729
    shared = read_json('gathering/shared-check-results-35.json')
    assert shared['passed'] and shared['tests'] == 80
    isolation = read_json('gathering/shared-isolation-35.json')
    assert isolation['passed'] and isolation['tests'] == 80
    files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for n in range(1, 5)
             for p in (ROOT / f'line-{n}').rglob('*') if p.is_file()}
    digest = sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())
    integrity = read_json('gathering/line-integrity-35.json')
    assert digest == integrity['before_sha256'] and len(files) == integrity['file_count']
    integrity.update(after_sha256=digest, passed=True)
    (ROOT / 'gathering/line-integrity-35.json').write_text(json.dumps(integrity, indent=2) + '\n')
    review = read_json('gathering/review-35.json')
    assert review['wall_sha256'] == sha(wall.read_bytes())
    assert review['visual_requirements_unmet'] == []
    assert (ROOT / 'gathering/COINS.md').read_text().startswith('none\n')
    for name in ('REPORT.md', 'README.md', 'COINS.md'):
        assert (ROOT / 'gathering' / name).stat().st_size > 100
    changed_paths = set()
    for args in (['diff', '--name-only', '-z', 'HEAD'], ['ls-files', '--others', '--exclude-standard', '-z']):
        data = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout
        changed_paths.update(p.decode() for p in data.split(b'\0') if p)
    for name in changed_paths:
        assert name.startswith(('gathering/', 'shared/', 'dist/', 'artifacts/gathering/', 'test/scratch/')), name
        path = ROOT / name
        if path.is_file() and not name.startswith(('artifacts/', 'test/scratch/')):
            assert path.stat().st_size <= 100000, name
    tracked_wall = subprocess.run(['git', 'ls-files', '--', 'artifacts/gathering/wall-v16.png'], cwd=ROOT,
                                  capture_output=True, check=True).stdout
    assert not tracked_wall, 'named output must remain untracked'
    result = dict(passed=True, wall_sha256=sha(wall.read_bytes()), png_format='RGB PNG',
        png_dimensions=dimensions, png_bytes=wall.stat().st_size, jpeg_format='JPEG',
        jpeg_dimensions=thumb_dimensions, jpeg_bytes=preview.stat().st_size,
        records=len(expected), painted=painted, placeholders=placeholders,
        changed_pixels=changed, pixels_changed_outside=outside,
        line_files_unchanged=len(files), checked_changed_paths=len(changed_paths),
        line_commands=107, line_unittest_cases=729, shared_tests=80,
        unmet_visual_requirements=[], visual_review='Local manual inspection; byte checks do not certify visual quality.')
    (ROOT / 'gathering/delivery-check-35.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

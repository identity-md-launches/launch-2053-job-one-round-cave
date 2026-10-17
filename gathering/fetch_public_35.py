#!/usr/bin/env python3
"""Capture the public IMD API description; perform no described API operation."""
import hashlib
import json
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://api.imd.fun/openapi.json'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError('unexpected public-description redirect')


def main():
    # Explicit empty proxies: do not read machine proxy settings or credentials.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    request = Request(URL, headers={'User-Agent': 'Pepeolithic-Gathering35/1.0',
                                    'Accept': 'application/json'})
    with opener.open(request, timeout=25) as response:
        raw = response.read(100001)
        status = response.status
    if len(raw) > 100000:
        raise ValueError('public description exceeds the assignment byte limit')
    document = json.loads(raw)
    if not isinstance(document, dict) or not isinstance(document.get('paths'), dict):
        raise ValueError('public response is not an API description')
    target = ROOT / 'gathering/imd-openapi-current-35.json'
    target.write_bytes(raw)
    report = {'method': 'GET', 'url': URL, 'status': status, 'bytes': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(),
              'user_agent': 'Pepeolithic-Gathering35/1.0',
              'saved_as': str(target.relative_to(ROOT)),
              'described_operations_invoked': False}
    (ROOT / 'gathering/public-fetch-35.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

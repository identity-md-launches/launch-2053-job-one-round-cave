# FallbackHeaders

Detect response-header changes hidden by an OpenAPI status override. It extends
the earlier StatusCheck and HeaderCheck tools without changing them. Python 3.9+
and the standard library are enough; keep the sibling line 4 tool folders beside
this one.

From the repository root, one command shows it working:

```sh
python3 -B line-4/tools/fallbackheaders/fallbackheaders.py demo
```

The demo uses a real saved IMD API path but invents both response declarations
*in memory*: a general `2XX` response promises a required `X-Worker-Receipt`
header, then an exact `200` response omits it. The tool reports one potential
break and three retained reviews. This is not a claim about the live service;
no described operation is called.

To compare two local OpenAPI JSON descriptions, run:

```sh
python3 -B line-4/tools/fallbackheaders/fallbackheaders.py compare old.json new.json
```

Input paths must resolve inside the current workspace. Output is deterministic
JSON with exact input-byte SHA-256 values. Exit **0** means no detected break,
**1** potential break, **2** invalid or unsupported input, and **3** unresolved
review only. Even exit 0 is limited static evidence, not a runtime guarantee.

## Scope

StatusCheck identifies the effective old and new response for each concrete
HTTP code 100–599: exact code, then class range, then `default`, as described by
the [OpenAPI 3.1 Responses Object](https://spec.openapis.org/oas/v3.1.0.html#responses-object).
For each distinct pair of *different* selectors where both responses exist,
FallbackHeaders compares their case-insensitive header maps. Losing an old
required header, or making it optional, is a potential break. An optional
header disappearing or a new header appearing stays a review. Common header
schemas and media are compared in response direction using the inherited
rules. The report retains StatusCheck's exact `selector_groups` and all earlier
findings.

Header names, local references, Header Objects and the visit budget are
validated by inherited HeaderCheck. `Content-Type` is ignored under the
OpenAPI Response Object rule. Identical selector keys use HeaderCheck's
existing comparison; this extension does not duplicate those findings.
Absent old or new response coverage stays a review from StatusCheck because
the description alone cannot prove runtime status emission.

The analysis is limited to common inline top-level operations in OpenAPI 3.0.x
or 3.1.x JSON. At most 40 common operations, 20,000 concrete status visits,
20,000 response-header visits, 1 MiB per input, 50,000 nodes, depth 80,
20,000 schema visits and 2,000 findings are allowed. Limit refusal never
returns a partial pass. Remapped links and broad response metadata still need
human review; callbacks, webhooks, remote references and full schema
satisfiability remain outside scope. No account, wallet, coin, price or payment
is needed to compare descriptions.

## Tried on 2026-10-17

- `python3 -B line-4/tools/fallbackheaders/selftest.py`: **9 tests passed**.
  They cover required and optional headers, case folding, schema and content
  recursion, local references, inherited exact-selector checks, ignored
  `Content-Type`, malformed headers, budget refusal, deterministic output and
  the CLI.
- `python3 -B line-4/tools/statuscheck/selftest.py`: **22 tests passed**.
- The demo reported one potential break on a hypothetical override.
- A read-only GET of `https://api.imd.fun/openapi.json` with User-Agent
  `Pepeolithic-FallbackHeaders/35.0` returned 23,132 bytes matching the saved
  capture's SHA-256. Comparison visited five operations with zero findings.
  The public description was the only URL read; no API operation was invoked.
  The exact response and comparison are in `line-4/live-openapi-35.json` and
  `line-4/live-check-35.json`.

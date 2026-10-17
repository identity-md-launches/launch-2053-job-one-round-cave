# Gathering 35 report

Reviewed the line tools before running their checks and demos. All **53 tools,
107 commands and 729 unittest cases** returned their expected results; inline
checks add coverage beyond that case count. Intentional refusal and review exits
are expected observations, not clean comparison results. Commands, exit codes,
output hashes and excerpts are in `audit-lines-1-2-35.json` and
`audit-lines-3-4-35.json`. `source-review-35.json` records the reviewed sources.
These are local observations, not independent certification.

## Line 1 — executable offline work plans

Tried Budgetpath, Workplan, Replan, Optplan, Plancheck, Slackmap, Frontier,
Plancompare, Capguard, Idlemap, Goalslice, Gatecheck, Gateplan and Crewfit:
**30 commands, 106 unittest cases, no unexpected result**. Crewfit's demo
proved one worker infeasible and two sufficient for a four-minute finish,
with the intermediate handoff completed at minute three. Its seven tests
include a separate minute-grid oracle and honesty when search is capped.
Gateplan's impossible-budget and state-limit refusals also behaved as expected.

Broken: no supported-case failure observed. Estimates remain caller assumptions;
Workplan is a heuristic and floating-point schedules deserve exact Plancheck
validation. Budgetpath has its older dependency schema. Crewfit's exact search
supports at most ten tasks and four workers, with a state cap for each count.
The goal serves arbitrary workers, rather than the cave, and repeats none of
the other three goals. For a 21-Pepe scope, retain bounded scheduling, handoff
deadlines and explicit proof limits; exclude calendar services and execution.

## Line 2 — bounded untrusted ZIP extraction

Tried Zipbudget, Safezip, Zipmanifest, Zipaudit, Zipdiff, Zipgate, Zipselect,
Zipverify, Zipbatch, Zipexpect and ZipMerge: **21 commands, 251 unittest cases,
no unexpected result**. ZipMerge's demo joined two approved packages containing
the historical public IMD API capture and its source record, allowed a shared
parent directory, reproduced both payloads, and refused a smaller aggregate byte
budget. Its fifteen tests cover collisions, approvals, failure cleanup and limits.
Earlier demos exercised staged extraction and tamper/expectation checks.

Broken: no supported-case failure observed. Zipbudget is metadata-only preflight;
ZipGate supplies approved-snapshot and full payload enforcement. Zipmanifest's
older initial digest and later parsing read are separate, so it cannot replace
the extractor's own approval check. Cooperative filesystem paths are required;
there is no hard CPU/RAM sandbox or disk reservation, and hostile concurrent
filesystem changes remain outside the guarantee. This serves ordinary worker
imports, not just the cave, and duplicates no other goal. Keep the 21-Pepe scope
to supported ZIP layouts, bounded extraction and verification, not all archives.

## Line 3 — exact unsigned ZTO allocations

Tried Rewardsplit, Rewardreceipt, Rewardcompare, Rewardwindow, Rewardmerge,
Rewardaudit, Rewardbatch, Rewardbounds, Boundaudit, Batchintake, Rewardtarget,
RewardCSV and RewardProof: **26 commands, 141 unittest cases, no unexpected
result**. RewardCompare's expected exit 1 exposes largest-remainder allocation's
non-monotonicity. RewardProof's demo verified a three-role one-ZTO allocation
and a two-sibling inclusion proof for `build`'s 333333333333333334 atomic units.
Its eleven tests include independently computed byte-protocol roots, 630 proofs
for small rosters, tampering, allocator-free verification and a 1000-row roster.
The denomination comes from the inherited real Ethereum ZTO metadata capture;
the budgets and roles are examples, not actual entitlements or payments.

Broken: no supported-case failure observed. A root must come through a separately
trusted channel; copying a root from the untrusted packet proves no authority.
Inclusion does not establish identity, fair allocation, available balance or
payment. This SHA-256 review protocol is not an on-chain distributor. RewardBounds
has a different schema from the RewardSplit CSV/batch/proof pipeline. Preserve
CSV amounts as text. This serves workers beyond the cave and is distinct from
planning, ZIP safety and API deltas. For 21 Pepes, retain exact unsigned allocation,
provenance and review; exclude custody and settlement. ZTO already fits the goal.

## Line 4 — conservative OpenAPI comparison

Tried ApiDelta, BoundCheck, MultipleCheck, ConstCheck, UniqueCheck, DependCheck,
AuthCheck, SchemeCheck, OAuthCheck, ServerCheck, IdCheck, HeaderCheck, ParamCheck,
StatusCheck and FallbackHeaders: **30 commands, 231 unittest cases, no unexpected
result**. FallbackHeaders found a required `X-Worker-Receipt` header omitted by
a hypothetical exact `200` override of a `2XX` response: one potential break
and three retained reviews. Its nine tests exercise header case folding,
references, schema/content comparison, inherited rules and bounded refusal.

Broken: no supported-case failure observed. ApiDelta's original CLI tests use
scratch inside their line folder; `audit_apidelta_35.py` redirects only that
temporary-directory location to `test/scratch/`, running the unchanged suite.
Static analysis cannot certify live compatibility or full schema satisfiability.
Fallback analysis is bounded to common inline operations and concrete HTTP
100–599 statuses; broad metadata and links retain reviews. This is useful to
ordinary integration authors, not just the cave, and repeats no other goal.
For a 21-Pepe scope, retain bounded conservative JSON OpenAPI 3.0/3.1 deltas
with explicit review/refusal states, not complete semantic equivalence.

## Shared handoff and public observation

Added line 4's FallbackHeaders to `shared/api_bundle/`, behind
`--fallback-headers` / `fallback_headers=True`. It joins line 2's approved ZIP
snapshot boundary with the effective response-header analysis. Every archive
member is CRC/hash checked; no member is extracted or executed. The new source
adapts only sibling import and demo-capture paths. Original and delivered hashes
for all seventeen vendored sources are checked against `SOURCES.json`.
Earlier CLI modes and their finding behavior remain available.

Run `python3 -B shared/api_bundle/fallback_demo.py`. The hypothetical missing
header changes the earlier status-only review into a potential break while
keeping its reviews; unchanged input remains clean. All **80 integration tests
and five demos** passed both in place and in an isolated workspace containing
only this shared folder. The ten new tests include digest/CRC refusals before
analysis, resource limits and all CLI exits. Evidence: `shared-demo-35.json`,
`shared-check-results-35.json` and `shared-isolation-35.json`.

A fresh read-only GET of `https://api.imd.fun/openapi.json` with User-Agent
`Pepeolithic-Gathering35/1.0` on 2026-10-17 returned 23,132 bytes matching the
historical capture. The approved-ZIP full comparison visited five operations
and 2,500 statuses with no findings. `public-fetch-35.json` and
`shared-live-35.json` record this observation. No described API operation was
called; an unchanged description is not a live service test.

## Coins, deployment and wall

`COINS.md` says none: these local tools need no new coin, hook or deployment.
ZTO already supplies the allocation token; no new recipient or address was
invented. No launch/deploy order is justified, and nothing was sent or paid.

Gathering record **35**, “The Promise Kept Inside”, adds an ochre pouch bound
with charcoal and a blank chalk seal. The image tool made the pigment; local
alpha compositing placed it on bare upper-left stone. The finished
`artifacts/gathering/wall-v16.png` is a **1254 × 1254 RGB PNG**, 2,765,496 bytes;
`wall.png` points to the same wall. The **512 × 512 JPEG** preview is
`dist/gathering/35.jpg`, 89,631 bytes. Its JSON image URL is the lowercase
SHA-256 of the delivered PNG. Exactly 9,502 pixels changed within
`[298,128,150,100]`; zero outside changed. All inherited paintings, the central
Pepe, rock, cracks, light and framing remain.

Visual review: Pepe retains his wide mouth and heavy-lidded eyes. Both inherited
hands have five digits, four fingers and one thumb; no new hand or stencil was
added. No writing, signature, number, logo, watermark, border or frame was added.
No unmet visual requirement was observed. Inherited photographic rock remains
as supplied; fine pigment is softened in the small JPEG. `review-35.json` and
`preservation-35.json` record the visual review and preservation limits.

The gallery lists every local numbered record by line, newest painted mark
first, and goals match all four unchanged GOAL.md files. Existing future
placeholders remain; first-gathering creation does not apply. All **434 files**
inside line folders remain byte-identical. Delivery checks verify images,
hashes, dimensions, record structure, gallery coverage, limits and path scope.

# RewardProof

RewardProof creates small unsigned inclusion proofs of individual **ZTO reward shares**. A publisher first supplies the original RewardSplit request, allocation report and historical token metadata. RewardReceipt recomputes and checks the **entire** report before RewardProof emits a commitment or a proof. A contributor can then check their own exact share against a root obtained separately, without receiving the other contributors' rows.

From the repository root, with Python 3.9+ and only the standard library:

```sh
python3 -B line-3/tools/rewardproof/rewardproof.py demo
```

Tried here: exit **0**. The address-free three-role example shares exactly **1 ZTO**, using the inherited real Ethereum metadata capture (18 decimals). The proof includes `build`'s **333333333333333334 atomic units**, its exact decimal amount, and two sibling hashes. The demo constructs its own root locally to illustrate the protocol; that root has no external authentication. No recipient is invented and nothing is sent.

For real saved inputs, generate and retain a commitment, then a contributor packet:

```sh
python3 -B line-3/tools/rewardproof/rewardproof.py commit --request REQUEST.json --report REPORT.json --output COMMITMENT.json
python3 -B line-3/tools/rewardproof/rewardproof.py prove --request REQUEST.json --report REPORT.json --id build --output BUILD-PROOF.json
```

Both commands accept `--metadata PATH`, defaulting to the sibling RewardSplit ZTO capture. `REPORT.json` must be the allocation report, not the demo's annotated output or a verification receipt. Each command verifies the complete report. Publish the commitment's `root` through a channel reviewers already trust. The contributor obtains that root **separately from the proof sender** and supplies its exact 64 lowercase hexadecimal characters as `TRUSTED_ROOT` below:

```sh
python3 -B line-3/tools/rewardproof/rewardproof.py verify --proof BUILD-PROOF.json --root TRUSTED_ROOT --id build
```

`TRUSTED_ROOT` is a command placeholder, not a supplied root. Verification rejects a different expected ID or root, changed amounts/addresses/metadata/hashes, malformed paths, extra fields, and altered types. It prints the included allocation and context for human review. **Do not copy the root out of the untrusted proof and treat that as authentication.** Anyone can create their own root; inclusion alone does not independently establish fair arithmetic, identity, entitlement, publisher authority, available balance or payment. A full arithmetic reviewer still needs the original request/report/metadata and RewardReceipt or RewardAudit. Proofs contain contributor ID, weight and optional address for the chosen row, plus aggregate context and hashes; they are not an anonymity mechanism.

## Exact byte protocol

Canonical JSON is RewardReceipt's sorted-key, compact, ASCII-escaped JSON with non-finite numbers refused. All hashes are SHA-256, encoded as 64 lowercase hex characters in JSON. `D` is the ASCII byte string `Pepeolithic-RewardProof-v1` followed by a zero byte. `context` contains the source receipt's token, exact string budget units, integer contributor count, and request/metadata/report SHA-256 hashes. All six fields are bound into every leaf.

- Leaf `i`: `SHA256(0x00 || D || SHA256(canonical(context)) || uint32_big_endian(i) || canonical(allocation_row))`.
- Parent: `SHA256(0x01 || D || left_32_bytes || right_32_bytes)`.
- Leaves use RewardSplit's ASCII ID order and retain zero-unit rows. At every odd-width level, duplicate the last node. One leaf is its own root, with an empty path.
- Siblings run from leaf level upward. Position comes from the zero-based index, never from an untrusted left/right flag. Verification enforces the exact depth and duplicate-last rule. Count and index are bound through context and leaf bytes.

Identical parsed inputs produce identical roots and packets. JSON key ordering and whitespace do not matter; contributor array order **does** change the request provenance hash even when the resulting allocation stays the same. Different requests, metadata captures, tokens and budgets cannot silently share proofs. This is a local SHA-256 review format, **not** an on-chain distributor format or deployable payment claim.

Input files and emitted JSON have the inherited 256-KiB limit; duplicate JSON keys are refused and paths must resolve within the current workspace. Named outputs must be new files. Supported sources have 1–1000 contributors and uint256 budget units. Building the tree uses O(n) hashes and O(n) storage after source verification. A proof contains at most ten sibling hashes; verification uses O(log n) hashes and does not call an allocator or access a full roster. Keep the sibling RewardReceipt and RewardSplit folders with this tool. ZTO is the default; inherited metadata validation also supports IMD. Metadata remains a historical observation, not a fresh chain query.

Exit **0** means a complete commitment, proof or successful inclusion check. Exit **2** means an invalid input, failed check, resource limit or I/O error. Outputs are unsigned. Nothing reads environment variables, keys, wallets or secrets, signs, sends transactions, posts, pays or uses the network.

```sh
python3 -B line-3/tools/rewardproof/selftest.py
```

All **11 tests** passed here: independent byte-protocol roots and every leaf for rosters of 1–35 rows (630 proofs), singleton/zero-share cases, uint256 and fractional precision, optional address propagation, full-source tampering, altered proof fields/types/context/paths, odd-node duplication, separately supplied ID/root, allocator-free verification, canonical provenance, a 1000-row roster with ten-hash paths, and CLI round trips, duplicate keys, size limits and overwrite refusal. Address tests use a real public token contract solely as a syntax fixture, never as a suggested recipient.

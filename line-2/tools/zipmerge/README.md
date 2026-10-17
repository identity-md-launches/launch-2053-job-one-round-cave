# ZipMerge

Combine several independently approved ZIP archives into one new workspace
directory. ZipMerge checks every archive and payload through the shipped
ZipGate/SafeZip tools, refuses a repeated file, file/directory conflict or
case-colliding path across archives, and enforces shared entry, output node and
uncompressed byte limits. Identical shared parent directories are allowed. It
publishes the joined tree only after all checks and extraction passes succeed.
Python 3.9+ standard library only; no installation, account or network needed.

Run this one command from the repository root to see it work:

```sh
python3 -B line-2/tools/zipmerge/demo.py
```

Tried here: two illustrative ZIP packages contain the shipped historical public
IMD OpenAPI capture (23,132 bytes) and its source record. ZipMerge joined their
shared `docs/imd` directory, reproduced both files byte for byte, and refused a
shared byte budget too small for both. The demo creates and removes disposable
data only under `test/scratch/`; it makes no fresh network observation. The
capture and provenance are in `../safezip/`.

## Use

First inspect each archive with ZipGate and review its inventory and
`archive_sha256`. Each approval below must be the actual reviewed digest of its
matching archive; replace the example paths and destination with yours.

```sh
python3 -B line-2/tools/zipmerge/zipmerge.py plan --archive first.zip --sha256 FIRST_REVIEWED_SHA256 --archive second.zip --sha256 SECOND_REVIEWED_SHA256 --merge-nodes 100 --merge-bytes 1048576 --seconds 10
python3 -B line-2/tools/zipmerge/zipmerge.py extract combined --archive first.zip --sha256 FIRST_REVIEWED_SHA256 --archive second.zip --sha256 SECOND_REVIEWED_SHA256 --merge-nodes 100 --merge-bytes 1048576 --seconds 10
```

`combined` must not exist; its parent must already exist. All input and output
paths must be inside the current workspace with no existing symlink component.
Plan mode creates nothing. Python callers use `process(specs, output=None,
merge_nodes=..., merge_bytes=..., seconds=...)`, where each spec is exactly
`{'archive': path, 'sha256': reviewed_digest}`. Omitting `output` plans only.

By default, at most 32 archives, 1,000 combined entries, 32,000 distinct output
nodes and 64 MiB of combined uncompressed data are accepted. The output root is
excluded from the node count. Per-archive limits retain ZipGate's defaults:
1,000 entries, 2 MiB central directory, 32 MiB archive snapshot, 32,000 nodes,
16 MiB per file, 64 MiB total bytes and 200:1 compression ratio. Every limit is
a positive integer. The central-directory gate runs before ZIP parsing. Its
snapshot digest must match the reviewed digest, and the extractor repeats that
approval and complete payload validation before staging. Input order determines
report order but never grants overwrite priority.

Exit 0 emits a JSON plan or extraction report. Exit 2 emits `ok: false` for
refusal, corruption or I/O failure. Untrusted archive content is never executed.

## Checks and limits

```sh
python3 -B line-2/tools/zipmerge/selftest.py
```

Observed 15 focused tests: exact shared limits, shared directories, no-output
plan, collisions, replaced/incorrect approvals, unsafe later archives, symlink
and corrupt members, later extraction failure cleanup, preexisting outputs,
cancellation, deadline, invalid
options and CLI success/refusal. This is an ordinary cooperative workspace
tool: a hostile concurrent process changing filesystem paths can race its
checks. The optional deadline is cooperative, not a hard CPU or memory sandbox.
Temporary staging needs disk space for the extracted inputs and joined tree;
there is no disk reservation. Only classic stored/deflated ZIP layouts accepted
by ZipGate are supported. Content hashes establish byte identity, not publisher
trust or content safety. No ZTO or IMD payment is needed for local extraction.

# codedb agent guidelines

> **Objective:** local text-only EmbeddingGemma 2 is the product default.
> The hosted default is the comparison baseline, not the destination.
> Do not claim a retrieval win until the 128-question eval proves it.

This is the standalone fork at `10xdev4u-alt/codedb`. The team contract is
[docs/engineering/AGENTIC_WORKFLOW.md](docs/engineering/AGENTIC_WORKFLOW.md).
It covers remotes, branches, commits, review, merges, and the read-only
upstream policy. Read it before your first change. Do not restate it here.

Work starts from an issue in [the backlog tree](docs/engineering/backlog/).
Sync the tree with `scripts/sync_backlog.py`. A change without an issue,
evidence, and a rollback is not ready.

## What codedb is (and isn't)

codedb is a **code-intelligence and context tool, not an editor.** It exists to
help agents *find and understand* code: structural search, symbol/caller
lookup, dependency graph, outlines, and task-shaped context. Agents edit with
their own native tools. codedb has **no edit capability**: the old
`codedb_edit` fallback (and the HTTP `POST /edit` endpoint, the post-edit
linter, and `codedb_diagnostics`) was removed because MCP edit calls bypass the
client's own undo/rewind tracking. Keep that framing consistent across tool
descriptions, the MCP `initialize` instructions, the README, and these docs.

## Retrieval objective

- The default runs locally on Windows, macOS, and Linux through a managed
  llama.cpp sidecar, using the text-only EmbeddingGemma 2 Q8_0 weights (310 MB).
  FFI is a later optimization, not a prerequisite.
- codedb downloads the weights from this repository's release on first run,
  verifies SHA-256, resumes interrupted transfers, and supports an offline
  install. Never depend on Hugging Face at install time.
- Freeze the hosted default (`codedb-hosted-v1`) as the comparison baseline
  before any local comparison, and verify the freeze hashes in CI (#18). Do
  not tune it or treat it as the product default afterward.
- Accuracy first, then cost and latency. Local is how we ship. The win must be
  quality and cost. Do not trade retrieval breadth or relevance for a
  speed-only change. Keep the 4x ANN candidate pool, calibration, and exact
  fallback until the eval says otherwise.
- Do not claim a win until the 128-question suite runs against the frozen
  baseline with the command, commit, and machine recorded. Label repairs never
  count as code improvements.
- Vision and audio are out of scope. The text GGUF is the model under test.

Read [the dataset inventory](evals/datasets/README.md) for the six-repository
128-question suite and the freeze discipline, and
[the EmbeddingGemma 2 dossier](docs/research/embeddinggemma2/) for the audited
model facts. Verify task prefixes and normalization before measuring quality
(#21). The inherited [eval harness](evals/README.md) still describes the hosted
Jina path; #17, #18, and #20 replace its assumptions.

## Review guidelines

- Flag any security issues: injection, file traversal, untrusted input, secret exposure
- Verify that sensitive files (.env, .pem, .key, credentials) are excluded from indexing AND search
- Check that telemetry behavior matches documentation claims
- Flag any regression in benchmark-critical paths (threshold: 10%)
- Treat P1 issues as merge-blocking
- Verify new language parsers handle malformed input gracefully, including
  braces in strings and unterminated comments
- Check that installer scripts don't execute untrusted code or skip verification
- Reject a silent fallback: `semantic=local` must embed locally or fail with a typed reason

## Pre-merge verification

Run these before merging any MCP-related change:

```bash
zig build test                                          # unit tests
python3 scripts/e2e_mcp_test.py \
    --binary zig-out/bin/codedb \
    --project /path/to/codedb                          # E2E MCP scenarios
```

`e2e_mcp_test.py` covers three scenarios:
1. **issue-346 regression**: spawn from cwd=`/`, roots handshake, tools return real data
2. **Normal mode**: explicit positional root (`codedb <path> mcp`), immediate scan
3. **No-roots client**: spawn from `/` with no roots capability, stays alive gracefully

Use the Zig version pinned in [`build.zig.zon`](build.zig.zon), selected with
the [`zigup` workflow](docs/zig-0.17-migration.md), not whatever `zig` is on
PATH. When measuring,
use a stable ReleaseFast binary copy outside `zig-out`; the unit suite may
rebuild the CLI in debug mode. Run the eval batch
runner from its development group and freeze before a new holdout. Keep raw
outcomes and credentials separate.

## Security-sensitive areas

- `src/watcher.zig`: file indexing skip lists (secrets must be excluded)
- `src/mcp.zig`: file read/search (path traversal, scope boundaries)
- `src/telemetry.zig`: data collection and transmission (must match docs)
- `src/snapshot.zig`: sensitive file filtering
- `install/install.sh`: binary download and config modification

## Historical context

The upstream Jina and Qwen experiments are historical and do not govern this
fork. The governing baseline is the frozen hosted run in
[the freeze file](evals/results/2026-09-05-jina-round3-freeze.json) and
[the baseline audit](docs/research/2026-10-23-baseline-audit.md). Read
[ADR 0011](docs/adr/0011-release-intent-guards.md) and
[ADR 0010](docs/adr/0010-multilingual-datasets-and-test-intent.md) for the
intent and dataset rules that still apply.

# Baseline audit and research dossier

Date: 2026-10-23. Commit: `36e35bf` plus the Zig 0.17.0 migration branch. Machine: Linux x86_64, 8 vCPU, 8.7 GB free disk.

This dossier is the evidence base for the first issue tree. It records what we reproduced, what we read, and what we still do not know. Every claim below has a command or a file reference behind it.

## 1. Build baseline

The repository pins Zig `0.17.0-dev.813+2153f8143`, a development build that no longer exists on ziglang.org. Zig 0.17.0 stable shipped on 2026-10-01.

We migrated the tree to stable with three changes:

| Change | File | Reason |
|---|---|---|
| `.ReleaseFast` to `.fast`, `.ReleaseSmall` to `.small` | `build.zig:24,167,184,201,221` | 0.17.0 renamed the `Optimize` fields |
| `builtin.mode != .Debug` to `.debug` | `src/main.zig:65` | Same rename |
| `Stream.read(io, &iov)` to `Stream.readWithControl(io, &iov, &.{})` | `src/server.zig:611`, `src/test_semantic.zig:80` | 0.17.0 stdlib bug: `Stream.read` destructures a `ReadResult` struct as a tuple and fails to compile |

That is the whole migration. The binary builds, reports `codedb 0.2.5860`, and runs.

Test results on stable 0.17.0:

| Mode | Result |
|---|---|
| ReleaseFast | exit 0, all tests pass |
| Debug | 547 passed, 6 skipped, 1 failed |

The debug failure is `test_index.test.perf regression: word index lookup under 100ns per query`. It measures 780 ns against a 500 ns bound on this machine, in debug mode, on a shared VM. The same test passes in ReleaseFast, where the source comment expects about 5 ns. The test is a debug-mode microbenchmark with a hard wall-clock bound, so it is a flake source, not a product defect. It still has to be fixed or moved before CI can require a green suite.

The suite contains 945 test blocks across 12 `src/test_*.zig` files.

## 2. What the code audit found

Four readers mapped the source. The findings below are the ones that change the build plan. The full list, with acceptance criteria, is in the issue tree.

### Retrieval and embedding

1. `semantic=local` does not embed locally. It disables semantic retrieval entirely and leaves BM25. There is no local model anywhere in the tree (`src/semantic.zig:6-8`, `src/semantic_index.zig:9-10`, `src/mcp.zig:4044`).
2. The fallback policy is explicit about this: `keep_local_bm25_no_cpu_embedding_fallback` (`src/mcp.zig:4605-4608`). The behavior is honest in the JSON, but the mode name is not.
3. The exact-rerank fallback has a whitelist that omits recoverable errors: `UnsupportedPlatform` on Windows, `FileNotFound`, corrupt calibration, and `AnnSidecarChangedDuringLoad` all skip the exact path (`src/mcp.zig:4513-4529`, `src/semantic_index.zig:114,912,1192`).
4. The cold path holds the project cache lock while it performs the network embedding call, so concurrent queries serialize for up to the full timeout (`src/semantic_index.zig:1239-1252`).
5. Files larger than about 208 KB are silently truncated at 256 chunks of 832 bytes (`src/semantic_index.zig:27-28,754`). The build stats still report success.

### MCP, CLI, and HTTP

1. `handleBundle` re-enters `dispatch` with the parent project's store and explorer. A `codedb_index` sub-operation invalidates and frees that cache entry, and the next sub-operation uses the freed pointers (`src/mcp.zig:1931,5906,6076`). This is a deterministic use-after-free.
2. The HTTP server starts a detached thread per connection and shares `Explorer` and `Store` with the watcher without a mutex (`src/server.zig:56-81`, `src/commands.zig:423`).
3. The loopback HTTP server has no token and no `Origin` check (`src/server.zig:31`). Any local process, or a browser page targeting `127.0.0.1:6767`, can read files and manipulate locks.
4. An MCP line over 1 MiB breaks the read loop and exits 0 with no JSON-RPC error (`src/mcp_json.zig:8,27-30`, `src/mcp.zig:1342`).
5. `shutdown` and `exit` are not implemented, and cancellation notifications are ignored (`src/mcp.zig:1424-1427`).

### Indexing and storage

1. The index generation is not atomic. The trigram postings file and its lookup file are renamed separately, and the loader never checks that the pair belongs together (`src/index.zig:1748-1749,1907-1908`).
2. The semantic sidecar and the text snapshot publish separately. Only git HEAD and vector-space id are checked, not the content generation (`src/snapshot.zig:1645-1694`, `src/semantic_index.zig:629-674`).
3. Counts read from disk allocate before bounds are proven. A crafted snapshot `file_count` or word `hit_count` can demand a large allocation (`src/snapshot.zig:725-735,1292`, `src/index.zig:855-870`).
4. Freshness is mtime-only. An edit that preserves mtime is served stale (`src/snapshot.zig:1173-1178,1400-1401`).
5. The watcher drops events beyond a 4096-slot queue and relies on a two-second audit that cannot see transient create and delete pairs (`src/watcher.zig:49,2646,2717-2720`).

### CI and release

1. No workflow runs `zig build test`. The suite has never been a merge gate (`.github/workflows/`).
2. The Zig pin is duplicated in at least five places, and `CLAUDE.md` still says 0.16.
3. Release assets are created with `--clobber`, so a published release can be rewritten, and the checksum lives in the same mutable release (`.github/workflows/release-binaries.yml:204-213`).
4. The installer fetches `install.sh` from the `main` branch at install time (`install/worker.js:2,33`), and `install.sh` proceeds without a checksum when the manifest fetch fails (`install/install.sh:815-839`).
5. The eval suite exits 0 whenever it ran. It records regressions but does not fail on them (`evals/jina_accuracy_suite.py:62-64`).

## 3. EmbeddingGemma 2 facts for the build

| Property | Value | Source |
|---|---|---|
| Total parameters | 740M | model card |
| Text-only parameters | 270M (130M transformer, 140M embedding table) | model card |
| Native dimensions | 768, MRL to 512, 256, 128 | model card |
| Usable context | 8,192 tokens | model card |
| Text MTEB multilingual | 61.36 | model card |
| Code MTEB v1 | 78.68, up from 68.76 in v1 | model card |
| MMEB v2 overall | 59.01 at 768d, 45.65 at 128d | model card |
| Text GGUF Q8_0 | 309.9 MB | Hugging Face API |
| Vision and audio projector Q8_0 | 554.8 MB | Hugging Face API |
| License | Apache-2.0 per the model card | model card |

The text-only path is 310 MB. The full multimodal path is about 865 MB. This product uses the text path.

The model card requires task prefixes. Code retrieval uses `task: code retrieval | query: ` for queries. The exact document prompt matters for quality and has to be verified in the eval, not assumed.

There is no Zig binding for GGUF. The realistic options are a llama.cpp sidecar process, an FFI link to `libllama`, or a pure Zig implementation. A sidecar is the fastest path to a measured result. An FFI link keeps one binary but adds cross-platform build and packaging work. A pure Zig implementation is months of work and is out of scope for M2.

## 4. What we still do not know

1. What `codedb-hosted-v1` actually is. The default model is a black box, so the baseline measures it but cannot describe it.
2. Whether EG2 beats it on the 128-question suite. The general code benchmark favors EG2, but this corpus is smaller and identifier-heavy.
3. Whether the Windows semantic path works at all. `UnsupportedPlatform` is returned on Windows today (`src/semantic_index.zig:114`).
4. Whether the Gemma license permits redistributing the GGUF from our releases. The model card says Apache-2.0; the weights' terms need a legal check before the artifact is published.
5. How much disk the full build and model cache need on a clean machine. This machine has 8.7 GB free, which is enough for development but not for a comfortable release test.

## 5. Decisions proposed for the first ADRs

| ADR | Decision | Why |
|---|---|---|
| 0001 | Use Zig 0.17.0 stable, not the pinned dev build | The dev build is unavailable from the official site, and stable builds with three small patches |
| 0002 | Ship the embedder as a managed llama.cpp sidecar first | It is the fastest path to a measured retrieval delta; FFI is a later optimization |
| 0003 | Serve the model from our GitHub releases, with SHA-256 and resume | The product must not depend on Hugging Face availability at install time |
| 0004 | Remove the silent lexical fallback from `semantic=local` | A mode named local must either embed locally or fail with a clear status |
| 0005 | Merge commits only, with a co-author trailer | The repository history must show what the fleet did and who reviewed it |

## 6. Evidence index

- `docs/engineering/AGENTIC_WORKFLOW.md`: the team contract.
- `docs/engineering/backlog/`: the issue tree source.
- `docs/evidence/`: per-issue measurements, added as issues close.
- `research/embeddinggemma2/`: the audited external research, outside this repository.

"""Backlog part 2: engine (E04 indexing, E05 protocol, E06 performance)."""

EPICS = [
    dict(
        key="e04",
        title="E04: Indexing and storage durability",
        area="indexing",
        milestone="M1: Baseline and trust",
        context=(
            "The index is a set of files that are published independently. A crash can leave a "
            "torn generation, and several loaders allocate from counts before proving the bytes "
            "exist. Durability is the product's foundation."
        ),
        outcome=[
            "One generation id covers trigram, snapshot, and sidecar",
            "Corrupt files are rejected, not trusted",
            "A crash mid-publish leaves the previous generation usable",
        ],
    ),
    dict(
        key="e05",
        title="E05: MCP, CLI, and HTTP surface",
        area="mcp",
        milestone="M1: Baseline and trust",
        context=(
            "The protocol surface has a use-after-free in bundle, a data race between HTTP "
            "handlers and the watcher, an unauthenticated loopback server, and no shutdown or "
            "cancellation. These are correctness and security bugs before they are features."
        ),
        outcome=[
            "No undefined behavior under concurrent queries",
            "The loopback server requires a token",
            "MCP clients can cancel and shut down cleanly",
        ],
    ),
    dict(
        key="e06",
        title="E06: Performance and resource bounds",
        area="perf",
        milestone="M2: Local embedding",
        context=(
            "The cold path holds a lock across a network call, retries herd, and builds a new "
            "TLS connection per batch. A local engine changes the cost profile and makes these "
            "fixes measurable."
        ),
        outcome=[
            "Concurrent cold queries do not serialize on the network",
            "Repeated builds do no redundant work",
            "Memory and disk have documented caps",
        ],
    ),
]

ITEMS = [
    # E04
    dict(
        key="idx-generation-id",
        epic="e04",
        title="index: give every generation a shared id across trigram, snapshot, and sidecar",
        area="indexing",
        type="arch",
        priority="p0",
        size="m",
        context=(
            "The text snapshot, trigram pair, and semantic sidecar publish separately. A reader "
            "can combine a new sidecar with an old snapshot and cite the wrong lines."
        ),
        evidence=[
            "src/snapshot.zig:1645-1694",
            "src/semantic_index.zig:629-674,938-951",
            "src/index.zig:1748-1749",
        ],
        acceptance=[
            "Every artifact embeds the same generation id",
            "A mismatch is rejected and triggers a rebuild, not a partial read",
            "A crash between publishes leaves the previous generation usable",
        ],
    ),
    dict(
        key="idx-trigram-atomic",
        epic="e04",
        title="index: publish the trigram pair atomically",
        area="indexing",
        type="bug",
        priority="p0",
        size="m",
        context=(
            "Postings and lookup are renamed one after the other. A crash between the renames "
            "leaves a pair that does not belong together, and the loader never checks."
        ),
        evidence=["src/index.zig:1748-1749,1907-1908,1917-2047"],
        acceptance=[
            "A single directory swap or a generation check makes the pair atomic",
            "A test fails the second rename and expects the old generation to load",
            "The loader rejects a mismatched pair with a typed error",
        ],
    ),
    dict(
        key="idx-snapshot-crc",
        epic="e04",
        title="index: add per-section checksums and overlap validation",
        area="indexing",
        type="security",
        priority="p1",
        size="m",
        context=(
            "The snapshot loader checks magic, version, and bounds. It does not check whether "
            "two sections overlap or whether a section's bytes changed since it was written."
        ),
        evidence=["src/snapshot.zig:52-67,551-596"],
        acceptance=[
            "Each section carries a CRC32 or stronger checksum",
            "Duplicate section ids and overlapping ranges are rejected",
            "A single bit flip produces a clear load error, not a silent wrong result",
        ],
    ),
    dict(
        key="idx-count-bounds",
        epic="e04",
        title="index: validate counts before allocating",
        area="indexing",
        type="security",
        priority="p0",
        size="s",
        context=(
            "A snapshot file_count and a word hit_count are trusted before the loader proves "
            "the bytes exist. A crafted file can demand a multi-gigabyte allocation."
        ),
        evidence=["src/snapshot.zig:725-735,1292", "src/index.zig:855-870"],
        acceptance=[
            "Every count is checked against the remaining section bytes before allocation",
            "A fuzz case claiming 4 GiB fails with a bounded RSS",
            "The error names the section and the count",
        ],
    ),
    dict(
        key="idx-mtime",
        epic="e04",
        title="index: detect same-mtime edits",
        area="indexing",
        type="bug",
        priority="p1",
        size="s",
        context=(
            "Freshness is mtime-only. A checkout that restores mtimes, or an editor that "
            "preserves them, is served stale."
        ),
        evidence=["src/snapshot.zig:1173-1178,1400-1401"],
        acceptance=[
            "A same-mtime rewrite is detected by size or content hash",
            "The fast path still avoids hashing every file on every start",
            "The regression test rewrites a file with the same mtime",
        ],
    ),
    dict(
        key="idx-watcher-drops",
        epic="e04",
        title="index: coalesce watcher events instead of dropping them",
        area="indexing",
        type="bug",
        priority="p1",
        size="m",
        context=(
            "The event queue holds 4096 entries and drops the rest. The two-second audit cannot "
            "see a create and delete that both happen between audits."
        ),
        evidence=["src/watcher.zig:49,2646,2717-2720"],
        acceptance=[
            "A burst of 10,000 events loses no final state",
            "The queue coalesces by path instead of growing without bound",
            "A stress test compares the index against a full rescan",
        ],
    ),
    dict(
        key="idx-skip-dirs",
        epic="e04",
        title="index: skip vendor and build only at the repository root",
        area="indexing",
        type="bug",
        priority="p1",
        size="s",
        context=(
            "The skip list matches vendor and build at any depth. Real source under a nested "
            "vendor directory is never indexed, including this repository's own vendor tree."
        ),
        evidence=["src/watcher.zig:260,277,305-313"],
        acceptance=[
            "A nested vendor/lib fixture is indexed",
            "Root-level vendor and build stay skipped",
            "The rule is documented with examples",
        ],
    ),
    dict(
        key="idx-truncation",
        epic="e04",
        title="index: report per-file chunk truncation",
        area="indexing",
        type="bug",
        priority="p0",
        size="s",
        context=(
            "A file over about 208 KB is cut at 256 chunks with no counter or warning. The "
            "build stats still look successful, and the missing text is invisible."
        ),
        evidence=["src/semantic_index.zig:27-28,754-771"],
        acceptance=[
            "BuildStats reports truncated_files and truncated_bytes",
            "The CLI prints a warning naming the files",
            "A 500 KB fixture is either fully indexed or explicitly reported",
        ],
    ),
    dict(
        key="win-watcher",
        epic="e04",
        title="fix: make the watcher reconciliation tests pass on Windows",
        area="indexing",
        type="bug",
        priority="p1",
        size="m",
        context=(
            "The Windows suite fails three watcher tests: issue-754 exits 253, "
            "issue-704 exits 253, and the notify-drain fingerprint test expects "
            "2183468070895612314 but gets 16144801376001656436. Two binaries crash on "
            "the same cases, so the failures reproduce."
        ),
        evidence=[
            "CI run 39851904822, build (windows-2022)",
            "watcher.test.issue-754 exits 253",
            "watcher.test.issue-704 exits 253",
            "watcher.test.notify drain fingerprint mismatch",
        ],
        acceptance=[
            "The three tests pass on windows-2022",
            "test-watcher runs in the Windows job",
            "A regression test covers the path separator or metadata difference",
        ],
    ),
    dict(
        key="win-hang",
        epic="e04",
        title="test: find and fix the Windows suite hang",
        area="indexing",
        type="test",
        priority="p1",
        size="m",
        context=(
            "After two test binaries report, the Windows job sits idle for 31 minutes "
            "until the job timeout. The last output is a failed test binary, so the hang "
            "is in a later binary that never prints a summary."
        ),
        evidence=[
            "CI run 39851904822, build (windows-2022)",
            "Last test output at 21:01:37, job cancelled at 21:32:50",
        ],
        acceptance=[
            "The hanging test binary is named",
            "The full suite finishes under 20 minutes on windows-2022",
            "The Windows job runs the platform-neutral suite without a timeout",
        ],
    ),
    dict(
        key="win-list-dir",
        epic="e04",
        title="fix: make the sensitive-name list filter pass on Windows",
        area="indexing",
        type="bug",
        priority="p1",
        size="s",
        context=(
            "The Windows platform-neutral run passes test-core and test-semantic but "
            "fails one list-dir test without output: sensitive names and directory "
            "aliases are filtered differently on Windows, likely because the test "
            "assumes POSIX separators or case sensitivity."
        ),
        evidence=[
            "CI run 39858587393, build (windows-2022)",
            "test-list-dir: 16 pass, 1 fail",
            "list_dir.test.listUnderRoot filters sensitive names and sensitive directory aliases",
        ],
        acceptance=[
            "The test passes on windows-2022",
            "Case-insensitive aliases are covered by a regression test",
            "test-list-dir runs in the Windows job",
        ],
    ),
    dict(
        key="win-ann",
        epic="e04",
        title="fix: make the ANN and semantic sidecar tests pass on Windows",
        area="indexing",
        type="bug",
        priority="p1",
        size="l",
        context=(
            "test-ann reports 69 pass, 4 skip, 8 fail, and 2 crash on windows-2022. "
            "Three failures are the watcher cases in #90. The other seven are ANN mmap "
            "and semantic sidecar tests that fail without output, which points at mmap, "
            "file locking, or path handling that differs from POSIX."
        ),
        evidence=[
            "CI run 39858587393, build (windows-2022)",
            "test-ann: 69 pass, 4 skip, 8 fail, 2 crash",
            "ann: mmap loader rejects out-of-range neighbor ids",
            "ann: mmap layout round-trips after neighbor slabs cross a page boundary",
            "semantic ANN: hosted 512D migration, metadata bounds, forged ranges, warm generation",
        ],
        acceptance=[
            "All ANN and semantic sidecar tests pass on windows-2022",
            "test-ann runs in the Windows job",
            "The mmap and locking assumptions are documented for Windows",
        ],
    ),
    # E05
    dict(
        key="mcp-uaf-bundle",
        epic="e05",
        title="mcp: fix the bundle and index cache use-after-free",
        area="mcp",
        type="bug",
        priority="p0",
        size="m",
        context=(
            "handleBundle re-enters dispatch with the parent project's store and explorer. A "
            "codedb_index sub-operation invalidates and frees that cache entry, and the next "
            "sub-operation uses the freed pointers."
        ),
        evidence=["src/mcp.zig:1931,5906,6076", "src/mcp.zig:319-373"],
        acceptance=[
            "A bundle with index followed by status runs clean under ASan",
            "A live project context is never freed during a bundle",
            "A regression test covers the eviction path",
        ],
    ),
    dict(
        key="mcp-http-race",
        epic="e05",
        title="server: synchronize HTTP handlers with the watcher",
        area="mcp",
        type="bug",
        priority="p0",
        size="m",
        context=(
            "The server starts a detached thread per connection and shares Explorer and Store "
            "with the watcher. There is no mutex, so a query during a file change is a data race."
        ),
        evidence=["src/server.zig:56-81", "src/commands.zig:423"],
        acceptance=[
            "A TSan run of serve plus concurrent queries and file changes is clean",
            "The lock does not serialize unrelated projects",
            "A stress test returns consistent results during a reindex",
        ],
    ),
    dict(
        key="mcp-http-auth",
        epic="e05",
        title="server: require a token and an Origin check",
        area="mcp",
        type="security",
        priority="p0",
        size="s",
        context=(
            "Any local process, or a browser page targeting 127.0.0.1:6767, can call /lock, "
            "/snapshot, /explore, and /file/read. There is no token and no Origin check."
        ),
        evidence=["src/server.zig:31,199-601"],
        acceptance=[
            "Requests without the startup token receive 401",
            "The token file is 0600 and never logged",
            "A browser-origin request is rejected even with a valid token",
        ],
    ),
    dict(
        key="mcp-line-cap",
        epic="e05",
        title="mcp: return a JSON-RPC error for oversized lines",
        area="mcp",
        type="bug",
        priority="p1",
        size="s",
        context=(
            "A line over 1 MiB makes the reader return null and the loop exits 0. The client "
            "sees a clean disconnect and no error."
        ),
        evidence=["src/mcp_json.zig:8,27-30", "src/mcp.zig:1342"],
        acceptance=[
            "A 1 MiB+ request returns JSON-RPC -32700",
            "The session stays alive and answers the next request",
            "The limit is documented",
        ],
    ),
    dict(
        key="mcp-shutdown-cancel",
        epic="e05",
        title="mcp: implement shutdown, exit, and cancellation",
        area="mcp",
        type="protocol",
        priority="p1",
        size="m",
        context=(
            "shutdown and exit return method-not-found, and notifications/cancelled is ignored. "
            "A client cannot stop a long scan without killing the process."
        ),
        evidence=["src/mcp.zig:1424-1427,1707"],
        acceptance=[
            "shutdown replies and then exits cleanly",
            "exit exits without a reply",
            "A cancelled request returns -32800 within 100 ms",
        ],
    ),
    dict(
        key="mcp-notify-side-effects",
        epic="e05",
        title="mcp: reject tool calls sent as notifications",
        area="mcp",
        type="bug",
        priority="p1",
        size="s",
        context=(
            "A tools/call without an id still executes. A notification can index or write and "
            "the client never receives the result."
        ),
        evidence=["src/mcp.zig:1665,1719,1763"],
        acceptance=[
            "A notification tools/call has no side effect",
            "The behavior matches the MCP specification",
            "A test covers index and write tools",
        ],
    ),
    dict(
        key="mcp-file-read",
        epic="e05",
        title="server: percent-decode /file/read paths",
        area="mcp",
        type="bug",
        priority="p2",
        size="s",
        context=(
            "The file route reads the raw path while other routes decode it. Paths with spaces, "
            "ampersands, or UTF-8 fail."
        ),
        evidence=["src/server.zig:271-283,364,653-669"],
        acceptance=[
            "a%20b.zig resolves and reads the file",
            "Traversal attempts still fail the root policy",
            "The fix is covered by a route test",
        ],
    ),
    dict(
        key="mcp-index-async",
        epic="e05",
        title="mcp: make codedb_index asynchronous",
        area="mcp",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "codedb_index runs a full scan inside the MCP loop. Every other tool waits, and a "
            "client that calls it from a bundle can stall the session."
        ),
        evidence=["src/mcp.zig:6004-6066"],
        acceptance=[
            "The tool returns a job id immediately",
            "ping stays under 100 ms during a full index",
            "A status tool reports progress and completion",
        ],
    ),
    # E06
    dict(
        key="perf-cache-lock",
        epic="e06",
        title="perf: release the project cache lock before embedding",
        area="perf",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "The cold path holds the cache mutex while it validates and performs the remote "
            "embedding call. Concurrent queries for the same project serialize for the full "
            "network timeout."
        ),
        evidence=["src/semantic_index.zig:1239-1252,1082"],
        acceptance=[
            "Two concurrent cold queries with a 500 ms mock finish under 900 ms total",
            "Cache replacement cannot free a generation in use",
            "A concurrency test runs under TSan",
        ],
    ),
    dict(
        key="perf-keepalive",
        epic="e06",
        title="perf: reuse HTTP connections for embedding batches",
        area="perf",
        type="perf",
        priority="p1",
        size="s",
        context=(
            "Each embedding request creates a new std.http.Client, so every batch pays a TLS "
            "handshake. A local sidecar makes this cost obvious."
        ),
        evidence=["src/semantic.zig:339-340"],
        acceptance=[
            "Ten batches use one connection per worker",
            "The handshake count is measured, not inferred",
            "A failed connection is replaced without leaking",
        ],
    ),
    dict(
        key="perf-retry-jitter",
        epic="e06",
        title="perf: add jitter and cancellation to embedding retries",
        area="perf",
        type="perf",
        priority="p2",
        size="s",
        context=(
            "Eight workers retry on the same 250 ms to 30 s schedule, and the sleep ignores "
            "cancellation. A rate-limited provider sees a thundering herd."
        ),
        evidence=["src/semantic.zig:494-512", "src/semantic_index.zig:549-563"],
        acceptance=[
            "A 429 mock produces distinct delays and a bounded request count",
            "Cancellation aborts a sleeping retry within one second",
            "The retry budget is configurable",
        ],
    ),
    dict(
        key="perf-skip-rebuild",
        epic="e06",
        title="perf: skip semantic rebuilds when the tree is unchanged",
        area="perf",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "Running semantic-index again re-embeds everything. The previous metadata is used "
            "only for deletion, so a no-op run still spends quota and time."
        ),
        evidence=["src/semantic_index.zig:689-694,713-777"],
        acceptance=[
            "A second run on an unchanged tree issues zero embedding requests",
            "The run prints that the index is up to date",
            "A single changed file re-embeds only that file's chunks",
        ],
    ),
    dict(
        key="perf-cli-cache",
        epic="e06",
        title="perf: reuse the semantic generation for CLI context",
        area="perf",
        type="perf",
        priority="p2",
        size="s",
        context=(
            "The CLI context command passes a null cache, so every call re-hashes the manifest, "
            "revalidates ranges, and re-mmaps the sidecar."
        ),
        evidence=["src/mcp.zig:6426", "src/semantic_index.zig:1255-1282"],
        acceptance=[
            "A second daemon context call reports ann_cache_hit=true",
            "The first call still validates the generation",
            "A stale generation is reloaded, not reused",
        ],
    ),
    dict(
        key="perf-memory-cap",
        epic="e06",
        title="perf: bound build memory and disk with a preflight",
        area="perf",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "A 250k-record build holds roughly 640 MB of vectors plus a same-size slab, and the "
            "old and new slabs coexist during publish. There is no sizing check."
        ),
        evidence=["src/semantic_index.zig:35,710,779", "src/ann.zig:126-133"],
        acceptance=[
            "A build estimates memory and disk before embedding",
            "A request over the configured cap fails with the estimate",
            "The cap is documented and configurable",
        ],
    ),
    dict(
        key="perf-bundle-cap",
        epic="e06",
        title="perf: enforce the 200 KB bundle cap during execution",
        area="perf",
        type="perf",
        priority="p2",
        size="s",
        context=(
            "The bundle cap is checked after a sub-operation has already materialized its full "
            "output. A large read is then discarded."
        ),
        evidence=["src/mcp.zig:5896-5921"],
        acceptance=[
            "The writer stops a sub-operation at 200 KB",
            "Peak RSS for an oversized bundle stays bounded",
            "The client receives a clear truncation status",
        ],
    ),
]

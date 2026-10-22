"""Backlog part 1: foundations (E01 research, E02 eval, E03 local engine).

Each item becomes a GitHub issue. Keys are stable and must never change.
"""

EPICS = [
    dict(
        key="e01",
        title="E01: Baseline and trust",
        area="research",
        milestone="M1: Baseline and trust",
        context=(
            "The tree builds only on a Zig development snapshot that no longer exists on "
            "ziglang.org, the full suite never runs in CI, and one debug microbenchmark is "
            "flaky. Nothing else can be trusted until these are fixed."
        ),
        outcome=[
            "Zig 0.17.0 stable builds the tree on Linux, macOS, and Windows",
            "The full suite is a required check",
            "A reproducible performance baseline exists",
        ],
    ),
    dict(
        key="e02",
        title="E02: Retrieval quality and evaluation",
        area="eval",
        milestone="M2: Local embedding",
        context=(
            "The 128-question suite records metrics but does not fail on a regression, and "
            "no frozen baseline exists for the hosted default. We cannot claim a local win "
            "until the suite can say no."
        ),
        outcome=[
            "The suite fails on a real regression",
            "The hosted baseline is frozen and reproducible",
            "The EG2 candidate is measured on the same corpus",
        ],
    ),
    dict(
        key="e03",
        title="E03: On-device EmbeddingGemma 2 engine",
        area="semantic",
        milestone="M2: Local embedding",
        context=(
            "There is no local embedding path in the tree. The product needs a provider seam, "
            "a managed llama.cpp sidecar, a model artifact we control, and an explicit failure "
            "policy instead of a silent lexical fallback."
        ),
        outcome=[
            "semantic=local runs a real embedding model",
            "The model comes from our release with a checksum",
            "The hosted path remains the default until the eval says otherwise",
        ],
    ),
]

ITEMS = [
    # E01
    dict(
        key="base-zig-stable",
        epic="e01",
        title="build: adopt Zig 0.17.0 stable",
        area="research",
        type="arch",
        priority="p0",
        size="s",
        context=(
            "The tree pins 0.17.0-dev.813+2153f8143, which is no longer on ziglang.org. "
            "Stable 0.17.0 builds with three patches: five Optimize enum literals, one "
            "builtin.mode check, and two Stream.read calls that hit a stdlib bug."
        ),
        evidence=[
            "build.zig:24,167,184,201,221",
            "src/main.zig:65",
            "src/server.zig:611",
            "src/test_semantic.zig:80",
        ],
        acceptance=[
            "CI installs 0.17.0 stable from an official URL and verifies its SHA-256",
            "ReleaseFast and Debug both build on Linux, macOS, and Windows",
            "An ADR records the stdlib bug and the readWithControl workaround",
        ],
    ),
    dict(
        key="base-test-matrix",
        epic="e01",
        title="ci: run the full suite on Linux, macOS, and Windows",
        area="research",
        type="ci",
        priority="p0",
        size="m",
        context=(
            "No workflow runs zig build test. The only Zig gate is a watcher test on macOS. "
            "Regressions merge without a red check."
        ),
        evidence=[
            ".github/workflows/bench-regression.yml:53-58",
            "build.zig:89-159",
        ],
        acceptance=[
            "A required workflow runs the full suite on ubuntu-24.04 and macos-14",
            "A deliberately failing test turns the check red",
            "The Windows job runs at least build plus the platform-neutral tests",
        ],
    ),
    dict(
        key="base-flaky-perf",
        epic="e01",
        title="test: make debug-mode performance assertions deterministic",
        area="research",
        type="test",
        priority="p1",
        size="s",
        context=(
            "The word-index test asserts under 500 ns per query in debug mode. It measures "
            "780 ns on this VM and passes in ReleaseFast. A wall-clock bound in a debug test "
            "turns host load into a red build."
        ),
        evidence=["src/test_index.zig:1969-1970"],
        acceptance=[
            "The flake is gone after 100 consecutive debug runs",
            "The performance signal moves to a benchmark with recorded hardware",
            "The test still catches a real algorithmic regression",
        ],
    ),
    dict(
        key="base-bench-baseline",
        epic="e01",
        title="perf: record a reproducible baseline for index and query",
        area="research",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "There is no committed baseline for index time, query latency, or memory. Every "
            "future perf claim needs a fixed point to compare against."
        ),
        evidence=["bench/", "benchmarks/", "src/bench.zig"],
        acceptance=[
            "Baseline records command, commit, hardware, five runs, p50, p95, and RSS",
            "A second machine reproduces the numbers inside the stated noise band",
            "The baseline is stored under docs/evidence/ and linked from the issue",
        ],
    ),
    dict(
        key="base-dev-bootstrap",
        epic="e01",
        title="chore: add a one-command developer bootstrap",
        area="research",
        type="arch",
        priority="p1",
        size="s",
        context=(
            "A new contributor has to discover the Zig pin, the cache directory workaround, "
            "the model download, and the test commands. The first hour is setup archaeology."
        ),
        evidence=["README.md:590", "build.zig.zon:5"],
        acceptance=[
            "A fresh clone reaches a green ReleaseFast suite with one documented command",
            "The script verifies the Zig checksum and refuses a mismatched compiler",
            "The script uses a disk-backed cache, never /tmp",
        ],
    ),
    dict(
        key="base-workflow",
        epic="e01",
        title="docs: establish the agentic engineering workflow",
        area="research",
        type="docs",
        priority="p0",
        size="m",
        context=(
            "The fleet has no written contract for roles, identities, commit format, review "
            "rules, stage gates, or evidence. Without one, every agent invents a process and "
            "the history stops being reviewable."
        ),
        evidence=[
            "AGENTS.md has accuracy rules but no delivery workflow",
            ".github/ has no pull request template",
        ],
        acceptance=[
            "The contract covers roles, identity, git, stages, issues, PRs, and evidence",
            "A commit-msg hook rejects a commit without the co-author trailer",
            "AGENTS.md points to the contract without duplicating it",
        ],
    ),
    dict(
        key="base-detach",
        epic="e01",
        title="docs: publish standalone attribution and upstream policy",
        area="research",
        type="docs",
        priority="p0",
        size="s",
        context=(
            "This repository is a standalone derivative of justrach/codedb under BSD-3-Clause. "
            "The license and attribution must be explicit, and the policy must say that we "
            "never push or open PRs against upstream."
        ),
        evidence=["LICENSE", "README.md"],
        acceptance=[
            "LICENSE keeps the upstream copyright notice",
            "README has an attribution and upstream-policy section",
            "An ADR records the detach decision and the no-upstream-push rule",
        ],
    ),
    # E02
    dict(
        key="eval-gate",
        epic="e02",
        title="eval: make the 128-question suite a merge gate",
        area="eval",
        type="ci",
        priority="p0",
        size="m",
        context=(
            "The suite exits 0 whenever it ran, even when recall or nDCG regressed. A report "
            "that cannot fail is not a gate."
        ),
        evidence=[
            "evals/jina_accuracy_suite.py:62-64",
            "evals/jina_sidecar_compare.py:80-83",
        ],
        acceptance=[
            "The runner accepts max-regression and min-delta thresholds",
            "A degraded binary exits non-zero and names the failing metric",
            "The current tree passes the gate, and the gate is a required check",
        ],
    ),
    dict(
        key="eval-freeze-verify",
        epic="e02",
        title="eval: verify freeze hashes in CI",
        area="eval",
        type="test",
        priority="p0",
        size="s",
        context=(
            "Freeze files pin the suite, dataset, and binary hashes, but nothing recomputes "
            "them. A changed dataset can silently invalidate a comparison."
        ),
        evidence=["evals/results/2026-09-05-jina-round3-freeze.json"],
        acceptance=[
            "A script recomputes every hash and fails on a mismatch",
            "CI runs the script on any change under evals/",
            "A tampered dataset fails with the expected and actual hash",
        ],
    ),
    dict(
        key="eval-hosted-baseline",
        epic="e02",
        title="eval: freeze the hosted baseline on the 128-question suite",
        area="eval",
        type="perf",
        priority="p0",
        size="m",
        context=(
            "The local candidate needs a fixed comparison point. The hosted default is a black "
            "box, but its numbers on this corpus can still be frozen."
        ),
        evidence=["evals/suites/jina-accuracy-round3.json", "src/semantic.zig:18"],
        acceptance=[
            "A report records top-1, MRR@5, recall@5, nDCG@5, p50, and p95",
            "The report pins the binary hash, suite hash, and dataset hash",
            "The baseline runs twice with a delta inside the noise band",
        ],
    ),
    dict(
        key="eval-eg2-candidate",
        epic="e02",
        title="eval: measure EmbeddingGemma 2 Q8_0 against the frozen baseline",
        area="eval",
        type="perf",
        priority="p0",
        size="l",
        context=(
            "The product claim depends on this comparison. It must use the same corpus, the "
            "same questions, and the same metrics as the hosted baseline."
        ),
        evidence=["docs/research/2026-10-23-baseline-audit.md"],
        acceptance=[
            "The candidate report uses the frozen suite and dataset hashes",
            "Every metric has a delta and a statement about the noise band",
            "A loss is reported as a loss, with no spin",
        ],
    ),
    dict(
        key="eval-prefix",
        epic="e02",
        title="eval: verify EmbeddingGemma 2 task prefixes and normalization",
        area="eval",
        type="test",
        priority="p0",
        size="s",
        context=(
            "The model card requires task prefixes and normalized vectors. A wrong prefix can "
            "cost several points and look like a model quality problem."
        ),
        evidence=["research/embeddinggemma2/hf_README.md"],
        acceptance=[
            "An A/B run compares the code-retrieval prefix with no prefix",
            "Vectors are L2-normalized before storage and query",
            "The chosen prefix is pinned in code and documented",
        ],
    ),
    dict(
        key="eval-dims",
        epic="e02",
        title="eval: compare 768, 512, 256, and 128 dimensions",
        area="eval",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "The current index stores 512 dimensions. EmbeddingGemma 2 is native at 768 and "
            "supports MRL. The quality and storage tradeoff should be measured, not assumed."
        ),
        evidence=["src/semantic.zig:19", "research/embeddinggemma2/hf_README.md"],
        acceptance=[
            "A table reports quality and bytes per vector for each dimension",
            "512 is kept only if the delta is inside the noise band",
            "The index format documents the chosen dimension",
        ],
    ),
    dict(
        key="eval-hybrid-weights",
        epic="e02",
        title="eval: justify the ANN RRF weight and k",
        area="eval",
        type="arch",
        priority="p1",
        size="s",
        context=(
            "The ANN lane uses weight 2.5 and k=1, so a semantic-only rank-0 file can outrank "
            "every lexical-only file. That contradicts the claim that lexical retrieval is "
            "authoritative."
        ),
        evidence=["src/semantic.zig:45-46,811-821", "src/mcp.zig:4465-4473"],
        acceptance=[
            "An identifier-heavy subset measures the current ratio and two alternatives",
            "A unit test pins the chosen ratio",
            "The docs state which lane wins and why",
        ],
    ),
    dict(
        key="eval-chunking",
        epic="e02",
        title="eval: compare fixed windows with code-aware chunks",
        area="eval",
        type="perf",
        priority="p1",
        size="l",
        context=(
            "Indexing uses 832-byte windows capped at 256 chunks per file. Code has structure, "
            "and a window can split a function from its signature."
        ),
        evidence=["src/semantic_index.zig:27-28,754-771"],
        acceptance=[
            "The comparison reports recall, nDCG, build time, and memory",
            "The code-aware splitter preserves function boundaries on a fixture set",
            "The chunker is configurable and the default is justified by the numbers",
        ],
    ),
    # E03
    dict(
        key="eg2-provider-seam",
        epic="e03",
        title="semantic: add an embedding provider interface",
        area="semantic",
        type="arch",
        priority="p0",
        size="m",
        context=(
            "Embedding calls are hard-wired to the hosted HTTP path. A local engine needs one "
            "seam, with the hosted path unchanged and still the default."
        ),
        evidence=["src/semantic.zig:301-458", "src/semantic_index.zig:1082"],
        acceptance=[
            "A provider interface covers health, embed, and identity",
            "The hosted provider is the default and its bytes are unchanged",
            "Unit tests run both providers through the same contract",
        ],
    ),
    dict(
        key="eg2-sidecar",
        epic="e03",
        title="semantic: implement a managed llama.cpp sidecar",
        area="semantic",
        type="feature",
        priority="p0",
        size="l",
        context=(
            "There is no Zig GGUF binding. A local llama.cpp server is the fastest path to a "
            "measured result. The sidecar must start, report health, restart on crash, and "
            "never leave an orphan process."
        ),
        evidence=["research/embeddinggemma2/providers/ggml-org__embeddinggemma-2-GGUF.md"],
        acceptance=[
            "codedb starts the sidecar on demand and stops it on exit",
            "A killed sidecar is restarted once and the query reports the retry",
            "No orphan process remains after SIGKILL of the parent",
        ],
    ),
    dict(
        key="eg2-binaries",
        epic="e03",
        title="release: publish pinned llama-server binaries for three operating systems",
        area="semantic",
        type="release",
        priority="p0",
        size="m",
        context=(
            "A sidecar needs a server binary per platform. Building it during install is slow "
            "and fragile. The release should carry a known-good build with a checksum."
        ),
        evidence=["research/embeddinggemma2/providers/ggml-org__embeddinggemma-2-GGUF.md"],
        acceptance=[
            "Linux x86_64, macOS arm64, and Windows x86_64 binaries are attached to a release",
            "Each binary has a SHA-256 and a version string",
            "The license notices for llama.cpp are included",
        ],
    ),
    dict(
        key="eg2-model-artifact",
        epic="e03",
        title="release: host the Q8_0 GGUF in our releases with checksums",
        area="semantic",
        type="release",
        priority="p0",
        size="m",
        context=(
            "Installs must not depend on Hugging Face being reachable. The 309.9 MB text model "
            "belongs in our release, with a checksum and range support."
        ),
        evidence=["research/embeddinggemma2/hf_model_api.json"],
        acceptance=[
            "The artifact is attached to a versioned release and served over HTTPS",
            "The download verifies SHA-256 and supports resume",
            "A missing or corrupt artifact fails with a clear message",
        ],
    ),
    dict(
        key="eg2-license",
        epic="e03",
        title="legal: clear EmbeddingGemma 2 weights for redistribution",
        area="semantic",
        type="release",
        priority="p0",
        size="s",
        context=(
            "The model card says Apache-2.0, but we redistribute the weights from our own "
            "release. The terms, notices, and attribution have to be confirmed before the "
            "artifact is published, not after."
        ),
        evidence=[
            "docs/research/embeddinggemma2/EMBEDDINGGEMMA2_REPORT.md",
            "https://huggingface.co/google/embeddinggemma-2",
        ],
        acceptance=[
            "A written review confirms redistribution under the stated license",
            "NOTICE and attribution ship beside the GGUF",
            "The release stays blocked until the review is linked",
        ],
    ),
    dict(
        key="eg2-cache",
        epic="e03",
        title="semantic: cache the model with integrity checks and offline mode",
        area="semantic",
        type="feature",
        priority="p0",
        size="m",
        context=(
            "The model cache must survive a partial download, a moved data directory, and an "
            "offline machine. It also must not re-download a valid 310 MB file."
        ),
        evidence=["src/bootstrap.zig", "src/config.zig"],
        acceptance=[
            "The cache lives in the platform data directory and honors an override",
            "A truncated file is detected and re-downloaded",
            "An offline run uses a valid cache without a network call",
        ],
    ),
    dict(
        key="eg2-no-silent-fallback",
        epic="e03",
        title="semantic: replace the silent lexical fallback with an explicit status",
        area="semantic",
        type="bug",
        priority="p0",
        size="s",
        context=(
            "When semantic retrieval fails, the response keeps BM25 and reports unavailable in "
            "detail, but semantic=local never embeds at all. A mode named local must either "
            "embed locally or say it cannot."
        ),
        evidence=["src/mcp.zig:3965,4605-4608", "src/semantic.zig:6-8"],
        acceptance=[
            "semantic=local attempts a local embedding and reports the provider used",
            "A failure returns a typed reason and a remediation command",
            "No response claims local semantic success when only BM25 ran",
        ],
    ),
    dict(
        key="eg2-batch",
        epic="e03",
        title="perf: batch and pipeline embedding requests",
        area="semantic",
        type="perf",
        priority="p1",
        size="m",
        context=(
            "The current path embeds a query plus calibration per call and builds a new HTTP "
            "client each time. A local server makes batching cheap and should use it."
        ),
        evidence=["src/semantic.zig:339-340,541", "src/semantic_index.zig:518-521"],
        acceptance=[
            "A batch of N chunks uses bounded requests and bounded memory",
            "Throughput and p95 are recorded against the single-request path",
            "Cancellation stops the pipeline within one second",
        ],
    ),
    dict(
        key="eg2-doctor",
        epic="e03",
        title="cli: add codedb doctor for model, server, and index health",
        area="semantic",
        type="feature",
        priority="p1",
        size="s",
        context=(
            "A local model adds failure modes that a stack trace does not explain: missing "
            "artifact, wrong checksum, port in use, stale sidecar, incompatible index."
        ),
        evidence=["src/main.zig:520-531", "src/commands.zig"],
        acceptance=[
            "doctor checks binary, model, sidecar, index version, and permissions",
            "Each failure prints a remediation command and a non-zero exit",
            "The output redacts tokens and absolute home paths",
        ],
    ),
]

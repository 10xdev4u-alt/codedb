"""Backlog part 3: delivery (E07 security, E08 release, E09 docs, E10 launch)."""

EPICS = [
    dict(
        key="e07",
        title="E07: Security and privacy",
        area="security",
        milestone="M1: Baseline and trust",
        context=(
            "The hosted lane can send source snippets to any HTTPS host, the credential file is "
            "not crash-safe, telemetry executes curl from PATH, and the installer proceeds "
            "without a checksum. Local-first is a security claim before it is a feature."
        ),
        outcome=[
            "No source leaves the machine without explicit consent",
            "Credentials and installers fail closed",
            "Every boundary has a failing test before the fix",
        ],
    ),
    dict(
        key="e08",
        title="E08: CI, release, and supply chain",
        area="ci",
        milestone="M3: Production release",
        context=(
            "Releases are rewritable, unsigned on Linux and Windows, built from floating action "
            "tags with broad permissions, and published to npm with a long-lived token. This is "
            "the gap between a demo and a product."
        ),
        outcome=[
            "Every artifact is signed or attested and immutable",
            "Every action is pinned and least-privilege",
            "A tag cannot publish a mismatched version",
        ],
    ),
    dict(
        key="e09",
        title="E09: Documentation and developer experience",
        area="docs",
        milestone="M3: Production release",
        context=(
            "The README sells a hosted model that is about to change, the agent instructions "
            "name a Zig version that no longer exists, and there is no architecture guide or "
            "contributor path."
        ),
        outcome=[
            "A new user installs and runs a query in five minutes",
            "A new contributor finds the workflow, the ADRs, and the tests",
            "No document names a dead version or file",
        ],
    ),
    dict(
        key="e10",
        title="E10: Product, landing, and launch",
        area="product",
        milestone="M4: Launch",
        context=(
            "The product needs a public face that shows the measured retrieval delta, not a "
            "feature list. The launch is a checklist with a rollback, not a tweet."
        ),
        outcome=[
            "A landing page loads fast and shows the real numbers",
            "A 60-second offline demo runs on a fresh machine",
            "The launch checklist is complete and reversible",
        ],
    ),
]

ITEMS = [
    # E07
    dict(
        key="sec-snippet-optin",
        epic="e07",
        title="security: require explicit consent before uploading source snippets",
        area="security",
        type="security",
        priority="p0",
        size="m",
        context=(
            "On a repository with no sidecar, the first codedb_context call sends paths and up "
            "to three lines per candidate to the configured endpoint. Consent is implied by "
            "using the tool, and the filter is a filename denylist."
        ),
        evidence=["src/mcp.zig:4514,4534-4554", "src/semantic.zig:603-616"],
        acceptance=[
            "No snippets leave the machine without an explicit opt-in or a local provider",
            "The consent is recorded and revocable",
            "A test asserts zero outbound bytes in the default state",
        ],
    ),
    dict(
        key="sec-custom-endpoint",
        epic="e07",
        title="security: require opt-in for custom embedding hosts",
        area="security",
        type="security",
        priority="p0",
        size="s",
        context=(
            "validate() accepts any HTTPS host. A typo or a malicious config can redirect code "
            "to an attacker without a warning."
        ),
        evidence=["src/semantic.zig:120-125"],
        acceptance=[
            "A non-default host is rejected unless an allow flag is set",
            "The rejection names the host and the flag",
            "A test asserts no request reaches the custom host",
        ],
    ),
    dict(
        key="sec-bearer",
        epic="e07",
        title="security: fail closed when a bearer token overrides device proof",
        area="security",
        type="security",
        priority="p1",
        size="s",
        context=(
            "CODEDB_EMBEDDINGS_TOKEN replaces the device-bound proof whenever it is set. A "
            "leaked environment variable becomes a shared credential with no host binding."
        ),
        evidence=["src/semantic.zig:375-380"],
        acceptance=[
            "A token plus a hosted URL fails unless an explicit allow flag is set",
            "The token is never written to logs or error output",
            "The default path uses device proof",
        ],
    ),
    dict(
        key="sec-proof-binding",
        epic="e07",
        title="security: bind request proofs to host and query",
        area="security",
        type="security",
        priority="p1",
        size="s",
        context=(
            "The signature covers method, path, and body, but not the host or query string. A "
            "proof for one endpoint can be replayed against another."
        ),
        evidence=["src/semantic_auth.zig:143-165,205-219"],
        acceptance=[
            "A proof for host A fails verification for host B",
            "Query tampering fails verification",
            "The canonical string is documented and tested",
        ],
    ),
    dict(
        key="sec-credential-heal",
        epic="e07",
        title="security: quarantine and regenerate corrupt credentials",
        area="security",
        type="security",
        priority="p1",
        size="s",
        context=(
            "Credential creation writes after an exclusive create. A crash or a full disk leaves "
            "an empty file, and every later run fails with InvalidDeviceCredentials and no recovery."
        ),
        evidence=["src/semantic_auth.zig:233,240-261,285-299"],
        acceptance=[
            "An empty or partial credential file is quarantined and replaced",
            "The old file is preserved for diagnosis",
            "A test writes an empty file and expects a usable credential",
        ],
    ),
    dict(
        key="sec-telemetry",
        epic="e07",
        title="security: remove PATH curl and preserve the telemetry WAL on failure",
        area="security",
        type="security",
        priority="p1",
        size="s",
        context=(
            "Telemetry shells out to curl from PATH and truncates its write-ahead log after a "
            "completed capture, even when curl failed. A poisoned PATH executes an attacker binary."
        ),
        evidence=["src/telemetry.zig:292-304"],
        acceptance=[
            "Telemetry uses an absolute path or an in-process HTTP client",
            "A failed upload leaves the WAL intact",
            "A test with a stub curl exit 22 proves both",
        ],
    ),
    dict(
        key="sec-installer",
        epic="e07",
        title="security: make install.sh checksums fail closed",
        area="security",
        type="security",
        priority="p0",
        size="s",
        context=(
            "install.sh fetches the checksum manifest with || true and installs anyway when the "
            "fetch or the hashing tool is missing. A proxied or sandboxed environment gets "
            "unverified bytes."
        ),
        evidence=["install/install.sh:811,815-816,826,836-839"],
        acceptance=[
            "A missing manifest or hashing tool exits non-zero with remediation text",
            "A version smoke test runs after install",
            "A bats test covers both branches with a stubbed curl",
        ],
    ),
    # E08
    dict(
        key="ci-inherited",
        epic="e08",
        title="ci: remove the upstream PR base guard and quarantine the broken benchmark gate",
        area="ci",
        type="ci",
        priority="p0",
        size="s",
        context=(
            "Every PR to main fails the inherited guard job, which tells contributors to "
            "target a release/* branch this repository does not use. The benchmark job pins "
            "the dead Zig development build and fails to compile. A red check on every PR "
            "teaches reviewers to ignore checks."
        ),
        evidence=[
            ".github/workflows/pr-base-guard.yml:3,33-40",
            ".github/workflows/bench-regression.yml:7,53-58",
            "PR #87: guard failed in 5s, bench failed in 25s",
        ],
        acceptance=[
            "The guard job is removed",
            "The benchmark gate is green or moved to workflow_dispatch with a linked issue",
            "Every remaining PR check is meaningful and required",
        ],
    ),
    dict(
        key="ci-cache",
        epic="e08",
        title="ci: cache the Zig toolchain and build outputs",
        area="ci",
        type="ci",
        priority="p1",
        size="s",
        context=(
            "No workflow uses actions/cache. Every run downloads Zig and rebuilds from zero, "
            "which makes the new test matrix expensive."
        ),
        evidence=[".github/workflows/"],
        acceptance=[
            "The cache key includes the Zig version and the target triple",
            "A warm run is measurably faster than a cold run",
            "A poisoned cache cannot skip the checksum verification",
        ],
    ),
    dict(
        key="ci-zig-pin",
        epic="e08",
        title="ci: make the Zig pin a single source of truth",
        area="ci",
        type="ci",
        priority="p0",
        size="s",
        context=(
            "The Zig version appears in build.zig.zon, two workflows, README, and CLAUDE.md. "
            "CLAUDE.md already says 0.16, and the release workflow greps the file to guess."
        ),
        evidence=[
            "build.zig.zon:5",
            ".github/workflows/bench-regression.yml:10",
            ".github/workflows/release-binaries.yml:15",
            "CLAUDE.md:5",
        ],
        acceptance=[
            "A script extracts the pin from build.zig.zon",
            "CI fails when a document or workflow disagrees",
            "Bumping the pin is a one-file change plus a regeneration",
        ],
    ),
    dict(
        key="ci-concurrency",
        epic="e08",
        title="ci: add concurrency, timeouts, and least-privilege permissions",
        area="ci",
        type="ci",
        priority="p1",
        size="s",
        context=(
            "Release runs can overlap and clobber each other. Jobs have no timeout and the "
            "release workflow grants contents: write to the build job that runs downloaded "
            "toolchains."
        ),
        evidence=[".github/workflows/release-binaries.yml:11-12"],
        acceptance=[
            "PR runs cancel superseded runs; releases queue",
            "Every job has a timeout",
            "The build job has contents: read and only publish has write",
        ],
    ),
    dict(
        key="ci-pin-actions",
        epic="e08",
        title="ci: pin every action to a commit SHA",
        area="ci",
        type="ci",
        priority="p1",
        size="s",
        context=(
            "Workflows use floating major tags, and npm-publish still uses checkout@v4 while "
            "the other workflows moved on. A moved tag executes new code."
        ),
        evidence=[".github/workflows/npm-publish.yml:23,27"],
        acceptance=[
            "Every uses: is a 40-character SHA with a version comment",
            "actionlint and zizmor report clean",
            "One version of each action is used across workflows",
        ],
    ),
    dict(
        key="rel-tag-guard",
        epic="e08",
        title="release: enforce tag, build.zig.zon, and npm version agreement",
        area="release",
        type="release",
        priority="p0",
        size="s",
        context=(
            "A release can be built from any branch and labelled with any tag. Nothing checks "
            "that the tag matches the version in build.zig.zon or npm/package.json."
        ),
        evidence=[".github/workflows/release-binaries.yml:4-9,64,70-73,207-213"],
        acceptance=[
            "A mismatch fails before any build starts",
            "A verify job runs the suite and the publish job needs it",
            "A mismatched dispatch is tested and fails",
        ],
    ),
    dict(
        key="rel-attest",
        epic="e08",
        title="release: sign and attest every artifact",
        area="release",
        type="release",
        priority="p0",
        size="m",
        context=(
            "Checksums live in the same mutable release as the assets, and Linux and Windows "
            "have no signature. A checksum proves transport integrity, not authorship."
        ),
        evidence=[".github/workflows/release-binaries.yml:196-205"],
        acceptance=[
            "Every asset has a minisign or cosign signature or a build provenance attestation",
            "The installer verifies the signature before running",
            "A tampered asset fails the install",
        ],
    ),
    dict(
        key="rel-immutable",
        epic="e08",
        title="release: stop overwriting published assets",
        area="release",
        type="release",
        priority="p1",
        size="s",
        context=(
            "The publish step uses gh release upload --clobber. A rerun silently replaces the "
            "bytes every cached checksum and mirror points at."
        ),
        evidence=[".github/workflows/release-binaries.yml:213"],
        acceptance=[
            "A rerun against an existing tag fails with a clear message",
            "A new release requires a new tag",
            "The release page marks the assets immutable",
        ],
    ),
    dict(
        key="rel-npm",
        epic="e08",
        title="release: publish npm with OIDC provenance",
        area="release",
        type="release",
        priority="p1",
        size="s",
        context=(
            "npm publishing uses a long-lived NPM_TOKEN, no provenance, no lockfile, and no "
            "pack dry run. The package executes a postinstall download."
        ),
        evidence=[".github/workflows/npm-publish.yml:15-16,35,39"],
        acceptance=[
            "npm publish --provenance runs with id-token: write",
            "A committed lockfile is installed with npm ci",
            "npm pack --dry-run is inspected before publish",
        ],
    ),
    # E09
    dict(
        key="docs-readme",
        epic="e09",
        title="docs: rewrite the README around local retrieval",
        area="docs",
        type="docs",
        priority="p0",
        size="m",
        context=(
            "The README describes a hosted embedding model and a product that is about to "
            "change. It needs a three-OS quickstart, the measured claim, and the limits."
        ),
        evidence=["README.md:63,75,590"],
        acceptance=[
            "A new user installs and runs a query in five minutes on each OS",
            "Every performance claim links to its evidence artifact",
            "The copy passes the unslop review",
        ],
    ),
    dict(
        key="docs-architecture",
        epic="e09",
        title="docs: add an architecture guide and an ADR index",
        area="docs",
        type="docs",
        priority="p1",
        size="m",
        context=(
            "The data flow is spread across explore.zig, mcp.zig, semantic_index.zig, and the "
            "openpuffer vendor tree. A new contributor has no map."
        ),
        evidence=["src/explore.zig", "src/mcp.zig", "src/semantic_index.zig"],
        acceptance=[
            "One diagram shows index, query, embedding, and storage",
            "Each component links to its file and its ADR",
            "The ADR index lists every decision with a status",
        ],
    ),
    dict(
        key="docs-contributing",
        epic="e09",
        title="docs: add CONTRIBUTING, issue templates, and a PR template",
        area="docs",
        type="docs",
        priority="p1",
        size="s",
        context=(
            "The repository has no issue template and no PR template. Contributors cannot see "
            "the evidence and acceptance rules the workflow requires."
        ),
        evidence=[".github/"],
        acceptance=[
            "Issue templates require context, evidence, and acceptance",
            "The PR template requires evidence, risk, and rollback",
            "CONTRIBUTING links the agentic workflow",
        ],
    ),
    dict(
        key="docs-agents",
        epic="e09",
        title="docs: rewrite AGENTS.md for the local retrieval fork",
        area="docs",
        type="docs",
        priority="p1",
        size="m",
        context=(
            "AGENTS.md still carries the upstream objective: the hosted default is the product "
            "and local models are forbidden. That directly contradicts this fork, whose product "
            "default is local text-only EmbeddingGemma 2 measured against the frozen hosted "
            "baseline. The file also omits the issue tree, the co-author trailer, and the merge "
            "policy."
        ),
        evidence=[
            "AGENTS.md",
            "docs/engineering/AGENTIC_WORKFLOW.md",
            "docs/research/embeddinggemma2/",
        ],
        acceptance=[
            "AGENTS.md states the fork objective: local text-only EmbeddingGemma 2 is the default, "
            "and the hosted default is only the comparison baseline",
            "No retrieval win is claimed until the 128-question eval proves it against a frozen baseline",
            "The code-intelligence framing, security review rules, and pre-merge verification stay",
            "The workflow contract, backlog, eval, and research dossier are linked, not restated",
            "No upstream instruction that forbids local models remains",
        ],
    ),
    dict(
        key="docs-installers",
        epic="e09",
        title="docs: document install, upgrade, and offline install",
        area="docs",
        type="docs",
        priority="p1",
        size="s",
        context=(
            "Installation is a curl pipe and a PowerShell one-liner. There is no page for a "
            "pinned version, an offline machine, or a failed checksum."
        ),
        evidence=["install/install.sh", "install/install.ps1", "README.md:63"],
        acceptance=[
            "Three paths are documented: latest, pinned, offline",
            "Each path is tested on a clean VM",
            "The failure modes name the remediation",
        ],
    ),
    dict(
        key="docs-version-drift",
        epic="e09",
        title="docs: remove stale Zig and file references",
        area="docs",
        type="docs",
        priority="p2",
        size="s",
        context=(
            "CLAUDE.md says Zig 0.16, copilot-instructions names a src/tests.zig that does not "
            "exist, and the README repeats the dead dev pin."
        ),
        evidence=["CLAUDE.md:5", ".github/copilot-instructions.md:15", "README.md:590"],
        acceptance=[
            "No document names 0.16 or src/tests.zig",
            "A CI grep fails on the stale strings",
            "The docs point at the single Zig pin source",
        ],
    ),
    # E10
    dict(
        key="prod-landing",
        epic="e10",
        title="product: build the landing page",
        area="product",
        type="feature",
        priority="p2",
        size="l",
        context=(
            "The product needs a page that shows the retrieval result and the install command. "
            "It should load fast, work without JavaScript, and look unlike a template."
        ),
        evidence=["website/"],
        acceptance=[
            "Lighthouse performance and accessibility are at least 95",
            "The page works with JavaScript disabled",
            "The hero shows a real query and a real result from the eval corpus",
        ],
    ),
    dict(
        key="prod-demo",
        epic="e10",
        title="product: record a 60-second offline demo",
        area="product",
        type="docs",
        priority="p2",
        size="m",
        context=(
            "A recorded demo is the fastest way to prove the product works without a hosted "
            "service. It must run on a fresh machine with the network off."
        ),
        evidence=["docs/"],
        acceptance=[
            "The demo shows install, index, and query with the network disabled",
            "The same query runs against the hosted baseline for comparison",
            "The recording lists the commit and the machine",
        ],
    ),
    dict(
        key="prod-positioning",
        epic="e10",
        title="product: publish the retrieval proof page",
        area="product",
        type="docs",
        priority="p2",
        size="m",
        context=(
            "The claim is better and cheaper retrieval. The proof page should show the suite, "
            "the metrics, the hardware, and the cases where the local model loses."
        ),
        evidence=["docs/research/2026-10-23-baseline-audit.md"],
        acceptance=[
            "The page reports every metric from the frozen suite",
            "It states the noise band and the losing cases",
            "It links to the raw reports and the commands",
        ],
    ),
    dict(
        key="prod-privacy",
        epic="e10",
        title="product: add opt-in, privacy-preserving usage metrics",
        area="product",
        type="feature",
        priority="p2",
        size="m",
        context=(
            "The product needs to know whether installs work without collecting code. Metrics "
            "must be off by default, documented, and verifiable."
        ),
        evidence=["src/telemetry.zig"],
        acceptance=[
            "Telemetry is off until the user opts in",
            "No paths, code, queries, or hostnames are collected",
            "A local command prints exactly what would be sent",
        ],
    ),
    dict(
        key="prod-launch",
        epic="e10",
        title="product: build the launch checklist and assets",
        area="product",
        type="docs",
        priority="p2",
        size="s",
        context=(
            "A launch without a rollback plan is an outage with a countdown. The checklist "
            "covers artifacts, install, rollback, support, and the announcement."
        ),
        evidence=["docs/"],
        acceptance=[
            "The checklist names every artifact and its verification command",
            "The rollback is tested before the announcement",
            "The support path and the known-limits page are live",
        ],
    ),
]

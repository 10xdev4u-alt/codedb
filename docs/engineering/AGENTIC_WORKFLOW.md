# Agentic engineering workflow

Status: active. Owner: 10xdev4u-alt. Applies to every agent and human who touches this repository.

This document is the contract. When a habit conflicts with it, the document wins. When the document is wrong, open an issue and change it in a PR.

## Mission

Ship local-first semantic code retrieval that is measurably better and cheaper than the hosted default, on Windows, macOS, and Linux, with a 310 MB text-only EmbeddingGemma 2 model.

"Better" means the 128-question suite says so. "Cheaper" means a measured cost per query and a measured install size. "Local-first" means the model runs on the user's machine and the index never leaves it.

## Non-negotiables

1. No claim without an artifact. A benchmark without a command, commit, and machine is a rumor.
2. The eval decides. A retrieval change ships only when the frozen suite says it does not regress.
3. A red suite blocks everything. Fix it or quarantine it with a linked issue, never ignore it.
4. Upstream `justrach/codedb` stays untouched. No pushes, no PRs, no comments. We are a standalone derivative.
5. Merge commits only. Squash and rebase merges are disabled on the repository.
6. The author never approves their own PR. The reviewer account is `the-ai-developer`.
7. Every commit carries the co-author trailer. Every commit follows Conventional Commits.
8. Security boundaries get a test that fails before the fix. No exceptions.

## The fleet

| Role | Account | Owns | Hands off to |
|---|---|---|---|
| Orchestrator | `10xdev4u-alt` | Issue tree, sequence, scope, merge decision | Researcher or Architect |
| Researcher | either | Evidence, source audit, reproduction, eval baseline | Architect |
| Architect | either | ADR, interface, blast radius, migration plan | Implementer |
| Implementer | either | Branch, failing test, minimal code, local validation | Reviewer |
| Reviewer | `the-ai-developer` | Independent review, check runs, approval or changes | Orchestrator |
| Release engineer | `10xdev4u-alt` | Tag, sign, attest, publish, verify install | Orchestrator |
| Scribe | either | README, guides, changelog, landing copy | Reviewer |

One person can hold several roles in a small change. The reviewer role is always a different account from the author.

## Accounts and identity

Author identity for every commit:

```bash
git config user.name "10xdev4u-alt"
git config user.email "10xdev4u@gmail.com"
```

Co-author trailer for every commit:

```
Co-authored-by: the-ai-developer <88466089+the-ai-developer@users.noreply.github.com>
```

Set it once so no commit can forget:

```bash
git config commit.template .gitmessage
```

`.gitmessage` contains the trailer. The commit-msg hook rejects a commit that lacks it. Install both with `bash scripts/install-hooks.sh`.

The reviewer account needs write access, which it has. Reviews are requested with:

```bash
gh pr edit <number> --add-reviewer the-ai-developer
```

## The git contract

### Branches

| Prefix | Use |
|---|---|
| `feat/` | New behavior |
| `fix/` | Bug fix |
| `perf/` | Performance work with a measurement |
| `refactor/` | Behavior-preserving change |
| `test/` | Tests only |
| `docs/` | Documentation only |
| `ci/` | Workflows, release, tooling |
| `chore/` | Maintenance with no product behavior |

Branch from `main`. Rebase your own unpublished branch freely. Never rebase or force-push a branch that has a review on it.

### Commits

Format:

```
<type>(<scope>): <imperative summary>

<what changed and why, wrapped at 72 columns>

Refs: #<issue>
Co-authored-by: the-ai-developer <88466089+the-ai-developer@users.noreply.github.com>
```

Rules:

- One logical change per commit.
- The summary is imperative and at most 72 characters.
- Tests travel in the same commit as the behavior they prove.
- A commit that only fixes a review comment says so.
- Never commit generated artifacts, secrets, or model weights.

### Merging

- Merge method: merge commit. The repository rejects squash and rebase merges.
- The merge commit message keeps the PR title and the PR number.
- Delete the branch after merge. The repository does this automatically.
- Prune stale local and remote branches every Friday.

## The stage pipeline

Each stage ends with a completion criterion. A stage does not start until the previous one is complete. The first five stages happen before any product code is merged.

### Stage 0: Research

Input: a question, a suspicion, or a failing behavior.

Work: read primary sources, reproduce what can be reproduced, record what cannot.

Output: `docs/research/<date>-<topic>.md` with sources, commands, and raw output.

Gate: every factual claim has a source or a reproduction command. "I read it somewhere" is not a source.

PR: `docs/research: ...` if the dossier changes the repository.

### Stage 1: Evaluate

Input: the research dossier.

Work: measure the current behavior. Freeze the binary, dataset, and harness. Record the hardware.

Output: `docs/evidence/<issue>/baseline.md` with p50, p95, sample count, and the exact command.

Gate: a second person can rerun the command and get a number inside the stated noise band.

PR: `docs/evidence: ...`.

### Stage 2: Issues

Input: the dossier and the baseline.

Work: split the work into issues that one agent can finish in one sitting. Each issue gets context, evidence, acceptance criteria, and out-of-scope notes.

Output: GitHub issues with labels, milestone, and an epic parent.

Gate: Definition of Ready, below.

PR: backlog update in `docs/engineering/backlog/`.

### Stage 3: Validate the idea

Input: a ready issue that needs a design decision.

Work: write an ADR with at least two alternatives, the blast radius, and the rollback plan.

Output: `docs/adr/NNNN-<slug>.md`.

Gate: the reviewer approves the direction before code. A rejected ADR closes the issue with a written reason.

PR: `docs(adr): ...`.

### Stage 4: Start

Input: an approved design.

Work: branch, write the failing test, make it pass, keep the diff small.

Output: a draft PR with the red test run attached.

Gate: the test fails on the base commit and passes on the branch. Paste both outputs.

PR: draft.

### Stage 5: Local validation

Input: a green unit test.

Work: run the full suite, the formatter, the relevant benchmark, the eval suite, and the security checks.

Output: `docs/evidence/<issue>/after.md`.

Gate: every required check is green. A skipped check has a written reason and a follow-up issue.

PR: ready for review.

### Stage 6: Pull request

Input: a validated branch.

Work: fill the template. Link the issue. State the risk and the rollback.

Output: a PR with CI running.

Gate: PR template complete, no unresolved TODO, diff under 400 changed lines or a written exception.

PR: this stage is the PR.

### Stage 7: Review

Input: a PR with green CI.

Work: the reviewer reads the diff, runs the checks, and tests the behavior. Comments are specific and reference lines.

Output: an approval or a change request.

Gate: one approval from `the-ai-developer`, all required checks green, no unresolved conversation.

PR: same PR.

### Stage 8: Merge

Input: an approved PR.

Work: merge with a merge commit. Verify `main` after the merge.

Output: a merge commit on `main`, a closed issue, a deleted branch.

Gate: the post-merge smoke test passes. If it fails, revert the merge commit and reopen the issue.

PR: merged.

### Stage 9: Cleanup

Input: a merged PR.

Work: delete local and remote branches, update the changelog, close the epic if complete, move the milestone.

Output: a clean branch list and an accurate changelog.

Gate: `git branch --no-merged main` is empty except for active work. `gh pr list --state open` has no PR older than seven days without a status comment.

PR: `docs(changelog): ...` or `chore: ...` when needed.

## Issue contract

Every issue contains:

```
## Context
What is wrong or missing, in two or three sentences.

## Evidence
- file:line or a command with its output
- a link to the research dossier or eval report

## Acceptance criteria
- [ ] a test or command that proves the fix
- [ ] the regression case

## Out of scope
What this issue deliberately does not cover.

## Risk
What can break, and how to roll back.
```

Definition of Ready:

- One owner can finish it in one sitting.
- The evidence reproduces.
- The acceptance criteria are binary.
- The scope is written.
- The labels and milestone are set.

Definition of Done:

- The change is merged to `main`.
- The test fails before and passes after.
- The docs and changelog are updated.
- The evidence artifact is linked.
- The issue is closed by the merge commit.

Labels:

| Group | Values |
|---|---|
| `area/` | `research`, `eval`, `semantic`, `indexing`, `mcp`, `cli`, `perf`, `security`, `ci`, `release`, `docs`, `product` |
| `type/` | `bug`, `feature`, `perf`, `security`, `arch`, `test`, `docs`, `ci`, `release` |
| `priority/` | `p0` (blocks the milestone), `p1` (next), `p2` (later) |
| `size/` | `s` (under a day), `m` (one to three days), `l` (needs a split) |

## Pull request contract

The template asks for:

1. What changed and why.
2. The issue it closes.
3. The evidence: commands, before and after numbers, screenshots for UI.
4. The risk and the rollback.
5. The checklist: tests, docs, changelog, security, cross-platform.

Size limit: 400 changed lines excluding generated files and lockfiles. A larger PR needs a written exception in the description and a reviewer who agrees.

Required checks:

| Change | Checks |
|---|---|
| Any | format, full test suite, build on Linux and macOS |
| Retrieval or embedding | eval suite with the frozen baseline |
| Index or storage | crash and corruption tests |
| MCP, CLI, HTTP | protocol tests and a manual smoke run |
| Security boundary | the failing test and the fix |
| Release or CI | workflow lint and a dry run |

Review SLA: 24 hours for a first response. A PR without a response gets a comment tagging the reviewer and, after 48 hours, the orchestrator reassigns it.

## Evidence rules

A performance number needs:

- the exact command,
- the commit SHA,
- the hardware and OS,
- at least five runs,
- p50 and p95,
- the noise band.

A retrieval number needs:

- the suite name and hash,
- the dataset hash,
- the binary hash,
- top-1, MRR@5, recall@5, and nDCG@5,
- the delta against the frozen baseline,
- a statement of whether the delta is inside the noise band.

A security fix needs a test that fails on the parent commit. Paste both runs.

A UI change needs a screenshot at 1440 px and 390 px.

Artifacts live under `docs/evidence/<issue-number>/`.

## Security and supply chain

- No secrets in the repository. `gitleaks` runs in CI and locally.
- Every GitHub Action is pinned to a full commit SHA with a version comment.
- Every release artifact has a SHA-256 manifest and a signature or build attestation.
- The model artifact comes from our release, never from a third-party URL at install time.
- The installer fails closed when the checksum is missing.
- The local HTTP server requires a token and checks `Origin`.
- Logs redact file contents, tokens, and absolute home paths.

## Skills matrix

| Stage | Skill |
|---|---|
| Research | `research`, `why`, `how` |
| Design | `architect`, `codebase-design`, `domain-modeling` |
| Planning | `planner`, `principle-*` |
| Tests | `tdd`, `matt-tdd` |
| Review | `code-review`, `interrogate`, `thermo-nuclear-code-quality-review` |
| Security | `security-reviewer`, `blast-radius` |
| Performance | `benchmark-checklist`, `principle-explain-the-number` |
| Docs | `unslop`, `technical-writing`, `writing-for-agents` |
| PR mechanics | `pr`, `make-pr-easy-to-review`, `fix-ci`, `fix-merge-conflicts`, `get-pr-comments` |
| Long runs | `show-me-your-work`, `figure-it-out`, `swarm` |
| Verification | `create-verification-skill`, `maintain-verification-skill` |

Load a skill when its trigger matches. Do not load every skill for every task.

## Decision records

Architecture decisions live in `docs/adr/`. The template:

```
# NNNN. Title

Status: proposed | accepted | superseded by NNNN
Date: YYYY-MM-DD

## Context
## Decision
## Alternatives considered
## Consequences
## Rollback
```

A decision without an ADR is a preference. A preference can be changed by anyone, which means it will be.

## Failure modes we refuse

- Silent fallback that reports success. If the model is unavailable, say so and return the lexical result with a status field.
- "It compiles" as proof.
- A benchmark without a baseline.
- A security fix without a regression test.
- A squash merge.
- A force push to `main`.
- A release that overwrites a published asset.
- A claim that the eval did not measure.

## The first four milestones

| Milestone | Outcome | Exit gate |
|---|---|---|
| M1: Baseline and trust | Zig 0.17.0 stable, green suite on three OSes, research dossier, issue tree | CI runs the full suite; the flaky perf test is fixed or moved |
| M2: Local embedding | EG2 sidecar, provider seam, model artifact, eval comparison | The 128-question suite runs on hosted and local; the delta is published |
| M3: Production release | Signed artifacts, installers, doctor, docs, SBOM | A clean machine installs with one command and passes the smoke test |
| M4: Launch | Landing page, demo, positioning page, launch checklist | The demo runs offline on a fresh machine |

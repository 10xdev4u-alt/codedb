#!/usr/bin/env python3
"""Recompute every repository hash pinned by an eval freeze file.

A freeze records the suite, dataset, and report that a comparison used. If one
of those files changes afterwards, the saved comparison no longer describes the
repository it claims to. This script recomputes each recorded SHA-256 and exits
non-zero on a mismatch.

Freeze files name their inputs in `artifacts` (repository-relative paths) and
declare hashes that cannot live in the repository in `external_artifacts`.
Every `*_sha256` field must appear in exactly one of those maps, so a new
freeze cannot leave an input unchecked by accident.

Usage:
    python3 evals/verify_freeze.py
    python3 evals/verify_freeze.py evals/results/2026-09-05-jina-round3-freeze.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
HASH_SUFFIX = "_sha256"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_files() -> list[Path]:
    return sorted((EVALS_DIR / "results").glob("*freeze*.json"))


def verify(freeze_path: Path, root: Path = REPO_ROOT) -> tuple[list[str], list[str], int]:
    """Return (errors, skips, verified_count) for one freeze file."""
    errors: list[str] = []
    skips: list[str] = []
    verified = 0

    try:
        freeze = json.loads(freeze_path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        return [f"{freeze_path.name}: cannot read freeze: {err}"], skips, verified
    if not isinstance(freeze, dict):
        return [f"{freeze_path.name}: freeze must be a JSON object"], skips, verified

    artifacts = freeze.get("artifacts", {})
    external = freeze.get("external_artifacts", {})
    if not isinstance(artifacts, dict) or not isinstance(external, dict):
        return [f"{freeze_path.name}: artifacts and external_artifacts must be objects"], skips, verified

    recorded = {key for key in freeze if key.endswith(HASH_SUFFIX)}
    for key in sorted(set(artifacts) | set(external)):
        if key not in recorded:
            errors.append(f"{freeze_path.name}: {key} is listed but the freeze has no such hash field")
        if key in artifacts and key in external:
            errors.append(f"{freeze_path.name}: {key} is both a repository artifact and external")

    for key in sorted(recorded):
        expected = freeze[key]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            errors.append(f"{freeze_path.name}: {key} is not a SHA-256 hex digest")
            continue
        if key in external:
            skips.append(f"{key}: {external[key]}")
            continue
        relative = artifacts.get(key)
        if not relative:
            errors.append(
                f"{freeze_path.name}: {key} has no artifact path; add it to artifacts "
                "or declare why it cannot be checked in external_artifacts"
            )
            continue
        if Path(relative).is_absolute():
            errors.append(f"{freeze_path.name}: {key} artifact path must be repository-relative: {relative}")
            continue

        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            errors.append(f"{freeze_path.name}: {key} points outside the repository: {relative}")
            continue
        if not path.is_file():
            errors.append(f"{freeze_path.name}: {key} artifact is missing: {relative}")
            continue

        actual = sha256_file(path)
        if actual != expected:
            errors.append(
                f"{freeze_path.name}: {key} mismatch for {relative}: "
                f"expected {expected}, actual {actual}"
            )
        else:
            verified += 1

    return errors, skips, verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freezes", nargs="*", type=Path, help="freeze files (default: every evals/results/*freeze*.json)")
    args = parser.parse_args()

    targets = args.freezes or freeze_files()
    if not targets:
        print("freeze: no freeze files found", file=sys.stderr)
        return 1

    failed = False
    for target in targets:
        errors, skips, verified = verify(target)
        if errors:
            failed = True
            for error in errors:
                print(f"freeze: {error}", file=sys.stderr)
        else:
            print(f"freeze: {target.name}: {verified} artifacts verified", flush=True)
        for skip in skips:
            print(f"freeze: {target.name}: external {skip}", flush=True)

    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())

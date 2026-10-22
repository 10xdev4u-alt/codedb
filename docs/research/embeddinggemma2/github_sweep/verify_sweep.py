#!/usr/bin/env python3
"""Recompute the GitHub sweep headline numbers from the raw manifests.

The report claims 1,073 unique repos, split 264 (repo mention) + 883 (code hit),
with 2,576 unique code-hit rows. This script derives those numbers from the files
instead of trusting the prose, and fails loudly if they drift.

Usage:
    python3 verify_sweep.py          # print + cross-check
    python3 verify_sweep.py --quiet  # exit code only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

EXPECTED = {
    "mentioned_repos_all.txt": 264,
    "code_hit_repos_all.txt": 883,
    "code_hits_all.tsv": 2_576,
    "all_mentioning_repos.txt": 1_073,
    "all_repos_metadata.tsv": 1_073,
}


def nonempty_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []
    counts: dict[str, int] = {}

    for name, expected in EXPECTED.items():
        path = HERE / name
        if not path.exists():
            problems.append(f"missing file: {name}")
            continue
        if name.endswith(".tsv"):
            rows = [r for r in nonempty_lines(path)]
            unique = len(set(rows))
            counts[name] = unique
            if unique != len(rows):
                problems.append(f"{name}: {len(rows)} rows but only {unique} unique")
        else:
            values = nonempty_lines(path)
            unique = len(set(values))
            counts[name] = unique
            if unique != len(values):
                problems.append(f"{name}: {len(values)} lines but only {unique} unique")
        if counts[name] != expected:
            problems.append(f"{name}: expected {expected}, found {counts[name]}")

    mentioned = set(nonempty_lines(HERE / "mentioned_repos_all.txt"))
    code = set(nonempty_lines(HERE / "code_hit_repos_all.txt"))
    union = mentioned | code
    overlap = mentioned & code
    counts["union (recomputed)"] = len(union)
    counts["overlap"] = len(overlap)
    if len(union) != 1_073:
        problems.append(f"union: expected 1073, found {len(union)}")
    if 264 + 883 - len(overlap) != len(union):
        problems.append("inclusion-exclusion does not balance")

    # Every metadata row must be in the union and vice versa.
    meta = {r.split("\t", 1)[0] for r in nonempty_lines(HERE / "all_repos_metadata.tsv")}
    if meta != union:
        problems.append(
            f"metadata/union mismatch: only-in-meta={len(meta - union)}, only-in-union={len(union - meta)}"
        )

    if not args.quiet:
        for key, value in counts.items():
            print(f"{key:<32} {value:>6}")
        print()
        if problems:
            for p in problems:
                print(f"FAIL  {p}")
        else:
            print("PASS  sweep counts match the report")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

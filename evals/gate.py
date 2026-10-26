#!/usr/bin/env python3
"""Apply quality thresholds to a suite summary.

`jina_accuracy_suite.py` writes `summary.json` with baseline and candidate
metrics. This gate turns that evidence into a pass or fail:

- a metric below baseline by more than `--max-regression` fails;
- an incomplete run, an execution failure, or a per-question recall regression
  fails;
- a gain below `--min-delta` is reported as noise, not as an improvement.

Failures name the scope, metric, both values, and the allowed regression.

Usage:
    python3 evals/gate.py --summary evals/results/.../summary.json --max-regression 0.01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

METRICS = ("top1_rate", "recall_at_5", "ndcg_at_5")
LABELS = {"top1_rate": "top-1", "recall_at_5": "recall@5", "ndcg_at_5": "nDCG@5"}


class SummaryError(ValueError):
    pass


def load_summary(path: Path) -> dict:
    try:
        summary = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        raise SummaryError(f"cannot read {path}: {err}") from err
    if not isinstance(summary, dict):
        raise SummaryError(f"{path} does not contain a JSON object")
    return summary


def deltas(summary: dict) -> dict[str, dict[str, float]]:
    """Return scope -> metric -> candidate minus baseline."""
    try:
        arms = summary["macro_average"]
        repositories = summary["repositories"]
        out = {
            "macro": {metric: arms["candidate"][metric] - arms["baseline"][metric] for metric in METRICS}
        }
        for name, repo in repositories.items():
            out[name] = {
                metric: repo["summary"]["candidate"][metric] - repo["summary"]["baseline"][metric]
                for metric in METRICS
            }
    except (KeyError, TypeError) as err:
        raise SummaryError(f"summary is missing a metric or arm: {err}") from err
    return out


def evaluate(summary: dict, max_regression: float, min_delta: float | None) -> tuple[list[str], list[str]]:
    """Return (failures, verdict lines)."""
    failures: list[str] = []
    verdicts: list[str] = []

    if not summary.get("complete", False):
        failures.append("run is incomplete; see the suite logs")
        if "macro_average" not in summary:
            return failures, verdicts
    for name, repo in summary.get("repositories", {}).items():
        if not repo.get("complete", False):
            failures.append(f"{name}: run is incomplete; see the suite log")
        for failure in repo.get("failures", []):
            failures.append(f"{name}: execution failure: {failure}")
        for question in repo.get("recall_regressions", []):
            failures.append(f"{name}: recall@5 regressed on question {question}")

    single_repository = len(summary.get("repositories", {})) == 1
    for scope, values in deltas(summary).items():
        # A one-repository run has identical macro and repository metrics;
        # name the repository once instead of reporting each failure twice.
        if single_repository and scope == "macro":
            continue
        for metric in METRICS:
            delta = values[metric]
            verdict = "pass"
            if delta < -max_regression:
                verdict = "fail"
                failures.append(
                    f"{scope} {LABELS[metric]} regressed {abs(delta):.4f} below baseline "
                    f"(allowed {max_regression:.4f})"
                )
            elif delta <= 0 or min_delta is None:
                verdict = "pass"
            elif delta >= min_delta:
                verdict = "improvement"
            else:
                verdict = "noise"
            verdicts.append(f"{scope:12} {LABELS[metric]:10} {delta:+.4f} {verdict}")

    return failures, verdicts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument(
        "--max-regression",
        type=float,
        default=0.0,
        help="allowed drop below baseline before the gate fails (default 0)",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=None,
        help="minimum gain reported as an improvement; smaller gains are noise",
    )
    parser.add_argument("--json", action="store_true", help="print the verdicts as JSON")
    args = parser.parse_args()

    if args.max_regression < 0 or (args.min_delta is not None and args.min_delta < 0):
        parser.error("thresholds must be non-negative")

    try:
        summary = load_summary(args.summary)
        failures, verdicts = evaluate(summary, args.max_regression, args.min_delta)
    except SummaryError as err:
        print(f"eval gate: {err}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"failures": failures, "verdicts": verdicts}, indent=2))
    else:
        for verdict in verdicts:
            print(verdict)
        for failure in failures:
            print(f"eval gate: {failure}", file=sys.stderr)
        if failures:
            print(f"eval gate: FAIL ({len(failures)} findings)", file=sys.stderr)
        else:
            print("eval gate: pass", flush=True)

    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())

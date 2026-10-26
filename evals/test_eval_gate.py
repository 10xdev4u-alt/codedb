#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("gate.py")
spec = importlib.util.spec_from_file_location("eval_gate", SCRIPT)
assert spec is not None
eval_gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(eval_gate)

RECORDED = Path(__file__).with_name("results") / "2026-09-05-jina-round3-intent-development" / "summary.json"


def summary() -> dict:
    return {
        "complete": True,
        "macro_average": {
            "baseline": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
            "candidate": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
        },
        "repositories": {
            "repo": {
                "complete": True,
                "failures": [],
                "recall_regressions": [],
                "summary": {
                    "baseline": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
                    "candidate": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
                },
            }
        },
    }


class EvalGateTests(unittest.TestCase):
    def test_recorded_development_summary_passes(self) -> None:
        recorded = json.loads(RECORDED.read_text())

        failures, _ = eval_gate.evaluate(recorded, 0.0, 0.005)

        self.assertEqual(failures, [])

    def test_repository_regression_names_the_scope(self) -> None:
        data = summary()
        data["repositories"]["repo"]["summary"]["candidate"]["ndcg_at_5"] = 0.80

        failures, _ = eval_gate.evaluate(data, 0.0, None)

        self.assertTrue(any("repo nDCG@5" in failure for failure in failures))

    def test_macro_regression_with_multiple_repositories(self) -> None:
        data = summary()
        data["repositories"]["second"] = copy.deepcopy(data["repositories"]["repo"])
        data["macro_average"]["candidate"]["top1_rate"] = 0.75

        failures, _ = eval_gate.evaluate(data, 0.01, None)

        self.assertTrue(any("macro top-1" in failure for failure in failures))

    def test_regression_inside_the_tolerance_passes(self) -> None:
        data = summary()
        data["repositories"]["repo"]["summary"]["candidate"]["recall_at_5"] = 0.895

        failures, _ = eval_gate.evaluate(data, 0.01, None)

        self.assertEqual(failures, [])

    def test_per_question_recall_regression_fails(self) -> None:
        data = summary()
        data["repositories"]["repo"]["recall_regressions"] = ["repo-07"]

        failures, _ = eval_gate.evaluate(data, 0.0, None)

        self.assertTrue(any("question repo-07" in failure for failure in failures))

    def test_incomplete_run_fails(self) -> None:
        data = summary()
        data["complete"] = False

        failures, _ = eval_gate.evaluate(data, 0.0, None)

        self.assertTrue(any("incomplete" in failure for failure in failures))

    def test_execution_failure_fails(self) -> None:
        data = summary()
        data["repositories"]["repo"]["failures"] = [{"error": "RuntimeError"}]

        failures, _ = eval_gate.evaluate(data, 0.0, None)

        self.assertTrue(any("execution failure" in failure for failure in failures))

    def test_small_gain_is_noise(self) -> None:
        data = summary()
        data["repositories"]["repo"]["summary"]["candidate"]["top1_rate"] = 0.801

        failures, verdicts = eval_gate.evaluate(data, 0.0, 0.01)

        self.assertEqual(failures, [])
        self.assertTrue(any("noise" in verdict for verdict in verdicts))

    def test_large_gain_is_an_improvement(self) -> None:
        data = summary()
        data["repositories"]["repo"]["summary"]["candidate"]["top1_rate"] = 0.82

        failures, verdicts = eval_gate.evaluate(data, 0.0, 0.01)

        self.assertEqual(failures, [])
        self.assertTrue(any("improvement" in verdict for verdict in verdicts))

    def test_gain_without_a_min_delta_is_a_pass(self) -> None:
        data = summary()
        data["repositories"]["repo"]["summary"]["candidate"]["top1_rate"] = 0.82

        failures, verdicts = eval_gate.evaluate(data, 0.0, None)

        self.assertEqual(failures, [])
        self.assertTrue(any("noise" not in verdict for verdict in verdicts))

    def test_missing_metric_is_an_error(self) -> None:
        data = copy.deepcopy(summary())
        del data["macro_average"]["candidate"]["ndcg_at_5"]

        with self.assertRaises(eval_gate.SummaryError):
            eval_gate.evaluate(data, 0.0, None)


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jina_accuracy_suite


ARMS = {
    "baseline": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
    "candidate": {"top1_rate": 0.8, "recall_at_5": 0.9, "ndcg_at_5": 0.85},
}


class ThresholdForwardingTests(unittest.TestCase):
    def run_suite(self, extra_args):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "suite.json"
            suite.write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "name": "repo",
                                "group": "development",
                                "dataset": "dataset.json",
                                "corpus_report": "corpus.json",
                            }
                        ]
                    }
                )
            )
            out = root / "out"
            child_commands = []

            def fake_run(command, **kwargs):
                child_commands.append(command)
                report = {
                    "summary": ARMS,
                    "complete": True,
                    "failures": [],
                    "recall_regressions": [],
                    "ranking_regressions": [],
                }
                Path(command[command.index("--out") + 1]).write_text(json.dumps(report))
                return mock.Mock(returncode=0)

            argv = [
                "jina_accuracy_suite.py",
                "--suite",
                str(suite),
                "--baseline",
                str(root / "baseline"),
                "--candidate",
                str(root / "candidate"),
                "--out-dir",
                str(out),
                *extra_args,
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                jina_accuracy_suite.subprocess, "run", side_effect=fake_run
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = jina_accuracy_suite.main()

            self.assertEqual(code, 0)
            return child_commands[0], json.loads((out / "summary.json").read_text())

    def test_suite_thresholds_reach_the_child_runner(self) -> None:
        command, _ = self.run_suite(["--max-regression", "0.01", "--min-delta", "0.005"])

        self.assertEqual(command[command.index("--max-regression") + 1], "0.01")
        self.assertEqual(command[command.index("--min-delta") + 1], "0.005")

    def test_default_thresholds_reach_the_child_runner(self) -> None:
        command, _ = self.run_suite([])

        self.assertEqual(command[command.index("--max-regression") + 1], "0.0")
        self.assertNotIn("--min-delta", command)


if __name__ == "__main__":
    unittest.main()

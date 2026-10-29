#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("baseline.py")
spec = importlib.util.spec_from_file_location("baseline", SCRIPT)
assert spec is not None and spec.loader is not None
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def fake_benchmark(index_ns: int = 1_000_000) -> dict:
    samples = [1_000, 2_000, 3_000, 4_000, 5_000]
    return {
        "root": ".",
        "file_count": 10,
        "index_ns": index_ns,
        "index_ms": index_ns // 1_000_000,
        "queries": [
            {
                "name": "middleware",
                "kind": "search",
                "hits": 3,
                "avg_ns": sum(samples) // len(samples),
                "p50_ns": baseline.percentile(samples, 50),
                "p95_ns": baseline.percentile(samples, 95),
                "samples_ns": samples,
            }
        ],
        "reindex": {
            "cycles": 1,
            "files_per_cycle": 1,
            "id_to_path_before": 1,
            "id_to_path_after": 1,
            "free_ids": 0,
        },
        "git_head": {"stat_ns": 1, "stable": True},
    }


def fake_runs() -> list[dict]:
    return [
        {"benchmark": fake_benchmark(1_000_000), "wall_ns": 2_000_000_000, "peak_rss_bytes": 64 * 1024 * 1024},
        {"benchmark": fake_benchmark(1_100_000), "wall_ns": 2_100_000_000, "peak_rss_bytes": 66 * 1024 * 1024},
    ]


def fake_report(runs: list[dict] | None = None) -> dict:
    return baseline.build_report(
        runs=runs if runs is not None else fake_runs(),
        hardware_info={
            "cpu": "test cpu",
            "cores": 8,
            "memory_bytes": 16 * 1024**3,
            "os": "test os",
            "kernel": "test kernel",
            "machine": "x86_64",
        },
        git={"commit": "a" * 40, "dirty": False},
        binary={"path": "zig-out/bin/benchmark", "sha256": "b" * 64},
        zig="0.17.0",
        command="python3 scripts/baseline.py --binary zig-out/bin/benchmark --root . --runs 2 --iterations 5",
        settings={"runs": 2, "warmups": 1, "iterations": 5},
    )


class BaselineTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self) -> None:
        self.assertEqual(baseline.percentile(list(range(1, 101)), 50), 50)
        self.assertEqual(baseline.percentile(list(range(1, 101)), 95), 95)
        self.assertEqual(baseline.percentile([7], 95), 7)
        self.assertEqual(baseline.percentile([], 50), 0)

    def test_summarize_reports_spread(self) -> None:
        values = baseline.summarize([1, 2, 3, 4, 5])
        self.assertEqual(values["p50"], 3)
        self.assertEqual(values["p95"], 5)
        self.assertEqual(values["min"], 1)
        self.assertEqual(values["max"], 5)

    def test_max_deviation_is_relative_to_the_median(self) -> None:
        self.assertAlmostEqual(baseline.max_deviation_pct([100, 110, 90]), 10.0)

    def test_band_accepts_sub_floor_noise_and_rejects_real_drift(self) -> None:
        self.assertEqual(
            baseline.band_breaches([1_000, 1_600, 900, 1_100, 1_000], 15.0, 50_000), []
        )
        breaches = baseline.band_breaches(
            [100_000, 200_000, 100_000, 100_000, 100_000], 15.0, 50_000
        )
        self.assertEqual(len(breaches), 1)
        self.assertEqual(breaches[0]["run"], 2)

    def test_parse_benchmark_rejects_percentiles_that_disagree_with_samples(self) -> None:
        payload = json.dumps(fake_benchmark())
        baseline.parse_benchmark(payload)
        broken = fake_benchmark()
        broken["queries"][0]["p50_ns"] = 1
        with self.assertRaisesRegex(ValueError, "percentiles disagree"):
            baseline.parse_benchmark(json.dumps(broken))

    def test_parse_benchmark_requires_samples(self) -> None:
        broken = fake_benchmark()
        broken["queries"][0].pop("samples_ns")
        with self.assertRaisesRegex(ValueError, "samples_ns"):
            baseline.parse_benchmark(json.dumps(broken))

    def test_report_rejects_a_corpus_change_between_runs(self) -> None:
        runs = fake_runs()
        runs[1]["benchmark"]["queries"][0]["hits"] = 4
        with self.assertRaisesRegex(ValueError, "different hit counts"):
            fake_report(runs)

    def test_report_rejects_a_query_set_change_between_runs(self) -> None:
        runs = fake_runs()
        runs[1]["benchmark"]["queries"][0]["name"] = "renamed"
        with self.assertRaisesRegex(ValueError, "different set"):
            fake_report(runs)

    def test_report_keeps_the_command_and_names_the_gap(self) -> None:
        report = fake_report()
        markdown = baseline.render_markdown(report)
        self.assertIn("python3 scripts/baseline.py", markdown)
        self.assertIn("| `middleware` | search | 3 |", markdown)
        self.assertIn("Run-to-run spread on this machine: index", markdown)
        self.assertIn("outside the band", markdown)
        self.assertIn("Reproduced on a second machine", markdown)


if __name__ == "__main__":
    unittest.main()

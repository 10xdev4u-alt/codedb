#!/usr/bin/env python3
"""Record a reproducible index and query baseline (issue #14).

Runs the repo benchmark one or more times, measures wall time and peak RSS for
each run, validates the per-query percentiles against the raw samples, and
writes a JSON artifact plus a Markdown summary under docs/evidence/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOISE_BAND = {
    "index_p50_pct": 15.0,
    "query_p50_pct": 15.0,
    "query_p95_pct": 35.0,
    "peak_rss_pct": 5.0,
    "query_abs_ns": 50_000,
}

DEFAULT_RUNS = 5
DEFAULT_WARMUPS = 1
DEFAULT_ITERATIONS = 100
DEFAULT_TIMEOUT_S = 300


def percentile(values: list[int], percent: int) -> int:
    """Nearest-rank percentile, matching the Zig benchmark."""
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, (percent * len(ordered) + 99) // 100)
    return ordered[min(rank, len(ordered)) - 1]


def summarize(values: list[int]) -> dict[str, int]:
    return {
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "min": min(values),
        "max": max(values),
    }


def max_deviation_pct(values: list[int]) -> float:
    median = percentile(values, 50)
    if median == 0:
        return 0.0
    return max(abs(value - median) / median * 100.0 for value in values)


def band_breaches(values: list[int], pct: float, abs_ns: int) -> list[dict[str, int]]:
    """Values further from the median than the relative band or absolute floor."""
    median = percentile(values, 50)
    allowed = max(median * pct / 100.0, abs_ns)
    return [
        {
            "run": index + 1,
            "value": value,
            "median": median,
            "deviation_ns": abs(value - median),
            "allowed_ns": int(allowed),
        }
        for index, value in enumerate(values)
        if abs(value - median) > allowed
    ]


def rss_bytes(ru_maxrss: int) -> int:
    """Normalize wait4's ru_maxrss to bytes (KiB on Linux, bytes on macOS)."""
    return ru_maxrss if sys.platform == "darwin" else ru_maxrss * 1024


def run_once(binary: Path, root: Path, iterations: int, timeout_s: int) -> dict[str, Any]:
    """Run the benchmark once and capture JSON, wall time, and peak RSS."""
    if os.name != "posix":
        raise RuntimeError("the baseline harness needs wait4; run it on Linux or macOS")

    command = [str(binary), "--root", str(root), "--iterations", str(iterations), "--json"]
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        started = time.monotonic_ns()
        pid = os.fork()
        if pid == 0:
            try:
                os.chdir(root)
                os.dup2(stdout_file.fileno(), 1)
                os.dup2(stderr_file.fileno(), 2)
                os.execv(str(binary), command)
            except BaseException:
                os._exit(127)

        deadline = time.monotonic() + timeout_s
        timed_out = False
        while True:
            waited, status, usage = os.wait4(pid, os.WNOHANG)
            if waited == pid:
                break
            if time.monotonic() >= deadline:
                timed_out = True
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(pid, 0)
                break
            time.sleep(0.02)
        wall_ns = time.monotonic_ns() - started

        if timed_out:
            raise RuntimeError(f"benchmark timed out after {timeout_s}s")
        exit_code = os.waitstatus_to_exitcode(status)
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode("utf-8", "replace")
        stderr = stderr_file.read().decode("utf-8", "replace")

    if exit_code != 0:
        raise RuntimeError(f"benchmark exited {exit_code}: {stderr.strip()}")

    return {
        "benchmark": parse_benchmark(stdout),
        "wall_ns": wall_ns,
        "peak_rss_bytes": rss_bytes(usage.ru_maxrss),
    }


def parse_benchmark(payload: str, root: str = ".") -> dict[str, Any]:
    """Parse benchmark JSON and verify its percentiles against the samples."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError(f"benchmark did not return JSON: {error}: {payload[:200]}") from error

    if "index_ns" not in data or "queries" not in data:
        raise ValueError("benchmark JSON is missing index_ns or queries; rebuild the benchmark")

    data["root"] = root
    for query in data["queries"]:
        samples = query.get("samples_ns")
        if not samples:
            raise ValueError(
                f"query {query.get('name', '?')} has no samples_ns; rebuild the benchmark"
            )
        expected_p50 = percentile(samples, 50)
        expected_p95 = percentile(samples, 95)
        if query.get("p50_ns") != expected_p50 or query.get("p95_ns") != expected_p95:
            raise ValueError(
                f"query {query.get('name', '?')} percentiles disagree with its samples: "
                f"binary={query.get('p50_ns')}/{query.get('p95_ns')} "
                f"recomputed={expected_p50}/{expected_p95}"
            )
    return data


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    return {
        "commit": git_output(root, "rev-parse", "HEAD"),
        "dirty": bool(git_output(root, "status", "--porcelain")),
    }


def _linux_cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def _sysctl(name: str) -> str | None:
    try:
        return subprocess.run(
            ["sysctl", "-n", name], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def hardware() -> dict[str, Any]:
    model = _linux_cpu_model() if sys.platform.startswith("linux") else None
    if model is None and sys.platform == "darwin":
        model = _sysctl("machdep.cpu.brand_string")

    memory_bytes: int | None = None
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    memory_bytes = int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            memory_bytes = None
    elif sys.platform == "darwin":
        raw = _sysctl("hw.memsize")
        memory_bytes = int(raw) if raw and raw.isdigit() else None

    return {
        "cpu": model or "unknown",
        "cores": os.cpu_count(),
        "memory_bytes": memory_bytes,
        "os": platform.platform(),
        "kernel": platform.release(),
        "machine": platform.machine(),
    }


def binary_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zig_version(root: Path) -> str | None:
    path = root / ".zigversion"
    return path.read_text().strip() if path.is_file() else None


def build_report(
    *,
    runs: list[dict[str, Any]],
    hardware_info: dict[str, Any],
    git: dict[str, Any],
    binary: dict[str, Any],
    zig: str | None,
    command: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    index_values = [run["benchmark"]["index_ns"] for run in runs]
    rss_values = [run["peak_rss_bytes"] for run in runs]
    wall_values = [run["wall_ns"] for run in runs]
    queries: dict[str, dict[str, Any]] = {}
    for index, run in enumerate(runs):
        for query in run["benchmark"]["queries"]:
            key = f"{query['kind']}:{query['name']}"
            if index == 0:
                queries[key] = {"p50_ns": [], "p95_ns": []}
            queries[key]["p50_ns"].append(query["p50_ns"])
            queries[key]["p95_ns"].append(query["p95_ns"])

    query_summary = {
        key: {
            "p50_ns": summarize(values["p50_ns"]),
            "p95_ns": summarize(values["p95_ns"]),
            "hits": next(
                query["hits"]
                for query in runs[0]["benchmark"]["queries"]
                if f"{query['kind']}:{query['name']}" == key
            ),
        }
        for key, values in queries.items()
    }

    index_outliers = band_breaches(index_values, NOISE_BAND["index_p50_pct"], 0)
    rss_outliers = band_breaches(rss_values, NOISE_BAND["peak_rss_pct"], 0)
    p50_outliers = [
        {"query": key, **breach}
        for key, values in queries.items()
        for breach in band_breaches(
            values["p50_ns"], NOISE_BAND["query_p50_pct"], NOISE_BAND["query_abs_ns"]
        )
    ]
    p95_outliers = [
        {"query": key, **breach}
        for key, values in queries.items()
        for breach in band_breaches(
            values["p95_ns"], NOISE_BAND["query_p95_pct"], NOISE_BAND["query_abs_ns"]
        )
    ]
    spread = {
        "index_max_deviation_pct": max_deviation_pct(index_values),
        "peak_rss_max_deviation_pct": max_deviation_pct(rss_values),
        "index_outliers": index_outliers,
        "peak_rss_outliers": rss_outliers,
        "query_p50_values": sum(len(values["p50_ns"]) for values in queries.values()),
        "query_p95_values": sum(len(values["p95_ns"]) for values in queries.values()),
        "query_p50_outliers": p50_outliers,
        "query_p95_outliers": p95_outliers,
    }

    return {
        "issue": 14,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "git": git,
        "binary": binary,
        "hardware": hardware_info,
        "zig": zig,
        "settings": {**settings, "noise_band": NOISE_BAND},
        "runs": runs,
        "summary": {
            "index_ns": summarize(index_values),
            "peak_rss_bytes": summarize(rss_values),
            "wall_ns": summarize(wall_values),
            "queries": query_summary,
        },
        "spread": spread,
    }


def _fmt_ns(ns: int | float) -> str:
    if ns < 1_000:
        return f"{int(ns)} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:.1f} µs"
    return f"{ns / 1_000_000:.2f} ms"


def _fmt_ms(ns: int | float) -> str:
    return f"{ns / 1_000_000:.2f} ms"


def _fmt_mib(value: int | float) -> str:
    return f"{value / (1024 * 1024):.1f} MiB"


def _fmt_seconds(ns: int | float) -> str:
    return f"{ns / 1_000_000_000:.2f} s"


def render_markdown(report: dict[str, Any]) -> str:
    settings = report["settings"]
    band = settings["noise_band"]
    spread = report["spread"]
    runs = report["runs"]
    summary = report["summary"]
    hardware_info = report["hardware"]
    memory = hardware_info["memory_bytes"]
    date = report["generated_at"][:10]
    run_count = len(runs)
    run_headers = " | ".join(f"Run {index + 1}" for index in range(run_count))
    run_divider = " | ".join("---:" for _ in range(run_count))

    lines = [
        "# Index and query baseline — issue #14",
        "",
        f"Recorded {date} from commit "
        f"`{report['git']['commit']}`"
        + (" (dirty tree)" if report["git"]["dirty"] else "")
        + ".",
        "",
        "| | |",
        "|---|---|",
        f"| Machine | {hardware_info['machine']} |",
        f"| CPU | {hardware_info['cpu']} |",
        f"| Cores | {hardware_info['cores']} |",
        f"| Memory | {memory / (1024**3):.1f} GiB |" if memory else "| Memory | unknown |",
        f"| OS | {hardware_info['os']} |",
        f"| Zig | {report['zig'] or 'unknown'} |",
        f"| Binary SHA-256 | `{report['binary']['sha256']}` |",
        f"| Command | `{report['command']}` |",
        f"| Samples | {settings['warmups']} warmup + {run_count} recorded runs × "
        f"{settings['iterations']} iterations per query |",
        "",
        "## Noise band",
        "",
        f"A rerun on the same CPU class is inside the band when its five-run "
        f"medians match this baseline's: index within "
        f"±{band['index_p50_pct']:.0f}%, query p50 within "
        f"±{band['query_p50_pct']:.0f}% or {_fmt_ns(band['query_abs_ns'])}, query "
        f"p95 within ±{band['query_p95_pct']:.0f}% or "
        f"{_fmt_ns(band['query_abs_ns'])}, and peak RSS within "
        f"±{band['peak_rss_pct']:.0f}%. The absolute floor keeps sub-"
        f"{_fmt_ns(band['query_abs_ns'])} dispatches from failing on timer noise. "
        f"File count and per-query hit counts must match exactly. The baseline "
        f"values below are medians across the {run_count} recorded runs.",
        "",
        f"Run-to-run spread on this machine: index "
        f"{spread['index_max_deviation_pct']:.1f}% from the median, RSS "
        f"{spread['peak_rss_max_deviation_pct']:.1f}%, query p50 "
        f"{len(spread['query_p50_outliers'])} of {spread['query_p50_values']} values "
        f"outside the band, query p95 {len(spread['query_p95_outliers'])} of "
        f"{spread['query_p95_values']} outside. A single run can land outside the "
        f"band while the machine's median is unchanged, so the acceptance test "
        f"compares five-run medians, not individual runs.",
    ]
    for label, outliers in (
        ("p50", spread["query_p50_outliers"]),
        ("p95", spread["query_p95_outliers"]),
    ):
        for outlier in outliers[:5]:
            lines.append(
                f"  - `{outlier['query']}` {label} run {outlier['run']}: "
                f"{_fmt_ns(outlier['value'])} vs {_fmt_ns(outlier['median'])} median "
                f"({outlier['deviation_ns'] / outlier['median'] * 100:.1f}%)."
            )

    lines += [
        "",
        "## Index and memory",
        "",
        f"| Metric | {run_headers} | p50 | p95 |",
        f"| --- | {run_divider} | ---: | ---: |",
        "| Index time | "
        + " | ".join(_fmt_ms(run["benchmark"]["index_ns"]) for run in runs)
        + f" | {_fmt_ms(summary['index_ns']['p50'])} | {_fmt_ms(summary['index_ns']['p95'])} |",
        "| Peak RSS | "
        + " | ".join(_fmt_mib(run["peak_rss_bytes"]) for run in runs)
        + f" | {_fmt_mib(summary['peak_rss_bytes']['p50'])} | {_fmt_mib(summary['peak_rss_bytes']['p95'])} |",
        "| Wall time | "
        + " | ".join(_fmt_seconds(run["wall_ns"]) for run in runs)
        + f" | {_fmt_seconds(summary['wall_ns']['p50'])} | {_fmt_seconds(summary['wall_ns']['p95'])} |",
        "",
        "## Query latency",
        "",
        "Median of the per-run percentiles. The range is the smallest to largest "
        "per-run value.",
        "",
        "| Query | Kind | Hits | p50 | p95 | p50 range | p95 range |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for key, values in summary["queries"].items():
        p50 = values["p50_ns"]
        p95 = values["p95_ns"]
        kind, name = key.split(":", 1)
        lines.append(
            f"| `{name}` | {kind} | {values['hits']} | {_fmt_ns(p50['p50'])} | "
            f"{_fmt_ns(p95['p50'])} | {_fmt_ns(p50['min'])}–{_fmt_ns(p50['max'])} | "
            f"{_fmt_ns(p95['min'])}–{_fmt_ns(p95['max'])} |"
        )

    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "zig build benchmark-bin",
        report["command"],
        "```",
        "",
        "The benchmark scans the checkout in process and writes no snapshot. Search "
        "rows disable the result cache; the `cached` row measures a cache hit.",
        "",
        "## Second machine",
        "",
        "- [ ] Reproduced on a second machine: five-run medians inside the band "
        "on the same CPU class, or identical file and hit counts with that "
        "machine's latency and RSS recorded.",
        "",
        "Pending. Run the command above on the second machine, then record its "
        "hardware, five-run medians, and file and hit counts in this file. Index "
        "time and RSS depend on the CPU and memory, so a machine of a different "
        "class records its own absolute numbers instead of matching this band.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="zig-out/bin/benchmark")
    parser.add_argument("--root", default=".")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--out-dir", default="docs/evidence/issue-14")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    if args.runs < 1 or args.warmups < 0 or args.iterations < 1:
        parser.error("--runs and --iterations must be at least 1; --warmups cannot be negative")

    root = Path(args.root).resolve()
    binary = Path(args.binary).resolve()
    if not binary.is_file():
        parser.error(f"benchmark binary not found: {binary} (run `zig build benchmark-bin`)")

    git = git_state(root)
    if git["dirty"] and not args.allow_dirty:
        parser.error("the tree is dirty; commit first or pass --allow-dirty")

    for _ in range(args.warmups):
        run_once(binary, root, args.iterations, args.timeout)

    runs: list[dict[str, Any]] = []
    for index in range(args.runs):
        print(f"run {index + 1}/{args.runs}", file=sys.stderr)
        runs.append(run_once(binary, root, args.iterations, args.timeout))

    command_parts = [
        "python3",
        "scripts/baseline.py",
        "--binary",
        args.binary,
        "--root",
        args.root,
        "--runs",
        str(args.runs),
        "--iterations",
        str(args.iterations),
    ]
    if args.warmups != DEFAULT_WARMUPS:
        command_parts += ["--warmups", str(args.warmups)]
    command = shlex.join(command_parts)

    report = build_report(
        runs=runs,
        hardware_info=hardware(),
        git=git,
        binary={"path": args.binary, "sha256": binary_sha256(binary)},
        zig=zig_version(root),
        command=command,
        settings={
            "runs": args.runs,
            "warmups": args.warmups,
            "iterations": args.iterations,
        },
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "baseline.json"
    markdown_path = out_dir / "baseline.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(render_markdown(report))
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")

    spread = report["spread"]
    outlier_count = (
        len(spread["index_outliers"])
        + len(spread["peak_rss_outliers"])
        + len(spread["query_p50_outliers"])
        + len(spread["query_p95_outliers"])
    )
    if outlier_count:
        print(
            f"note: {outlier_count} run value(s) outside the band on this machine; "
            "the baseline uses five-run medians, see the evidence file",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

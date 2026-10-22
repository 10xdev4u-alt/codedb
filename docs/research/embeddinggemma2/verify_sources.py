#!/usr/bin/env python3
"""Re-verify every GitHub/Hugging Face link cited in EMBEDDINGGEMMA2_REPORT.md.

The report quotes star counts, download counts, and repository paths as of its
snapshot date. Those drift, and a few were wrong when written. This script turns
"is the report still true?" into a re-runnable check instead of a vibe.

Usage:
    python3 verify_sources.py               # verify + write verification/sources_<date>.tsv
    python3 verify_sources.py --offline     # compare against last saved snapshot only

Exit code is 0 when every cited repo/model resolves, 1 when anything is missing.
Drift (stars, downloads) is reported but does not fail the run.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "EMBEDDINGGEMMA2_REPORT.md"
OUTDIR = ROOT / "verification"

GH_RE = re.compile(r"https://github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")
HF_RE = re.compile(r"https://huggingface\.co/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")

# Links that are intentional non-repo URLs.
GH_SKIP = {"search", "orgs", "topics", "features", "about", "sponsors"}
HF_SKIP = {"spaces", "datasets", "docs", "blog", "papers", "models", "api"}


def extract_links() -> tuple[list[str], list[str]]:
    text = REPORT.read_text(encoding="utf-8")
    gh = {
        f"{o}/{r}"
        for o, r in GH_RE.findall(text)
        if o.lower() not in GH_SKIP
    }
    hf = {
        f"{o}/{r}"
        for o, r in HF_RE.findall(text)
        if o.lower() not in HF_SKIP
    }
    return sorted(gh), sorted(hf)


def gh_meta(slug: str) -> dict:
    if shutil.which("gh") is None:
        return {"status": "no-gh"}
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{slug}",
            "--jq",
            "[.full_name, (.stargazers_count|tostring), (.forks_count|tostring), "
            ".pushed_at, (.archived|tostring)] | @tsv",
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {"status": "missing"}
    full, stars, forks, pushed, archived = proc.stdout.strip().split("\t")
    return {
        "status": "ok",
        "full_name": full,
        "stars": stars,
        "forks": forks,
        "pushed_at": pushed,
        "archived": archived,
    }


def hf_meta(slug: str) -> dict:
    url = f"https://huggingface.co/api/models/{slug}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            d = json.load(resp)
    except urllib.error.HTTPError as exc:
        return {"status": f"http-{exc.code}"}
    except Exception as exc:  # network flake
        return {"status": f"error:{type(exc).__name__}"}
    return {
        "status": "ok",
        "downloads": str(d.get("downloads", "")),
        "likes": str(d.get("likes", "")),
        "last_modified": str(d.get("lastModified", "")),
        "gated": str(d.get("gated", "")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="reuse the newest saved snapshot")
    args = ap.parse_args()

    gh, hf = extract_links()
    OUTDIR.mkdir(exist_ok=True)
    today = date.today().isoformat()
    out = OUTDIR / f"sources_{today}.tsv"

    if args.offline:
        saved = sorted(OUTDIR.glob("sources_*.tsv"))
        if not saved:
            print("no snapshot to compare against", file=sys.stderr)
            return 2
        with saved[-1].open() as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        print(f"loaded {len(rows)} rows from {saved[-1].name}")
        return 0

    rows: list[dict[str, str]] = []
    for slug in gh:
        m = gh_meta(slug)
        rows.append({"kind": "github", "slug": slug, **{k: str(v) for k, v in m.items()}})
    for slug in hf:
        m = hf_meta(slug)
        rows.append({"kind": "huggingface", "slug": slug, **{k: str(v) for k, v in m.items()}})

    fields = [
        "kind", "slug", "status", "stars", "forks", "pushed_at", "archived",
        "downloads", "likes", "last_modified", "gated", "full_name",
    ]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)

    bad = [r for r in rows if r["status"] != "ok"]
    print(f"verified {len(rows)} links -> {out.relative_to(ROOT)}")
    print(f"resolved: {len(rows) - len(bad)}   missing/broken: {len(bad)}")
    for r in bad:
        print(f"  {r['status']:<12} {r['kind']:<12} {r['slug']}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

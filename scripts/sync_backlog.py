#!/usr/bin/env python3
"""Sync the engineering backlog to GitHub issues.

Source of truth: docs/engineering/backlog/b*.py
Each issue body carries a hidden marker: <!-- backlog:<key> -->

The sync is idempotent:
  - first run creates the labels, milestones, epics, and tasks
  - later runs skip issues that already carry the marker
  - --update rewrites title, body, labels, and milestone for existing issues
  - epic task lists are refreshed on every run

Usage:
  python3 scripts/sync_backlog.py --dry-run
  python3 scripts/sync_backlog.py
  python3 scripts/sync_backlog.py --update
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile
import time

REPO = "10xdev4u-alt/codedb"
ACCOUNT = "10xdev4u-alt"
ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKLOG_DIR = ROOT / "docs" / "engineering" / "backlog"

MARKER_RE = re.compile(r"<!--\s*backlog:([a-z0-9-]+)\s*-->")

AREA_COLORS = {
    "research": "5319e7",
    "eval": "0e8a16",
    "semantic": "1d76db",
    "indexing": "006b75",
    "mcp": "0052cc",
    "perf": "d93f0b",
    "security": "b60205",
    "ci": "6e7781",
    "release": "2cbe4e",
    "docs": "0075ca",
    "product": "e99695",
}

TYPE_COLORS = {
    "bug": "d73a4a",
    "feature": "0e8a16",
    "perf": "d93f0b",
    "security": "b60205",
    "arch": "5319e7",
    "test": "fbca04",
    "docs": "0075ca",
    "ci": "6e7781",
    "release": "2cbe4e",
    "protocol": "0052cc",
}

PRIORITY_COLORS = {"p0": "b60205", "p1": "d93f0b", "p2": "fbca04"}
SIZE_COLORS = {"s": "c2e0c6", "m": "bfd4f2", "l": "f9d0c4"}


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def gh(args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if check and result.returncode != 0:
        fail(f"gh {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout


def load_backlog() -> tuple[list[dict], list[dict]]:
    epics: list[dict] = []
    items: list[dict] = []
    for path in sorted(BACKLOG_DIR.glob("b*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            fail(f"cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        epics.extend(module.EPICS)
        items.extend(module.ITEMS)

    keys = [entry["key"] for entry in (*epics, *items)]
    if len(keys) != len(set(keys)):
        dupes = sorted({key for key in keys if keys.count(key) > 1})
        fail(f"duplicate backlog keys: {dupes}")

    epic_keys = {epic["key"] for epic in epics}
    for item in items:
        if item["epic"] not in epic_keys:
            fail(f"item {item['key']} points at missing epic {item['epic']}")
        for field in ("title", "area", "type", "priority", "size", "context", "evidence", "acceptance"):
            if not item.get(field):
                fail(f"item {item['key']} has no {field}")

    return epics, items


def labels_for(entry: dict, *, epic: bool) -> list[str]:
    labels = [f"area/{entry['area']}"]
    if epic:
        labels.append("epic")
    else:
        labels.extend(
            [
                f"type/{entry['type']}",
                f"priority/{entry['priority']}",
                f"size/{entry['size']}",
            ]
        )
    return sorted(set(labels))


def ensure_labels(epics: list[dict], items: list[dict]) -> None:
    wanted: dict[str, tuple[str, str]] = {"epic": ("000000", "Tracking epic")}
    for entry in items:
        wanted[f"area/{entry['area']}"] = (
            AREA_COLORS.get(entry["area"], "ededed"),
            f"Area: {entry['area']}",
        )
        wanted[f"type/{entry['type']}"] = (
            TYPE_COLORS.get(entry["type"], "ededed"),
            f"Type: {entry['type']}",
        )
        wanted[f"priority/{entry['priority']}"] = (
            PRIORITY_COLORS.get(entry["priority"], "ededed"),
            f"Priority: {entry['priority']}",
        )
        wanted[f"size/{entry['size']}"] = (
            SIZE_COLORS.get(entry["size"], "ededed"),
            f"Size: {entry['size']}",
        )
    for entry in epics:
        wanted[f"area/{entry['area']}"] = (
            AREA_COLORS.get(entry["area"], "ededed"),
            f"Area: {entry['area']}",
        )

    for name, (color, description) in sorted(wanted.items()):
        gh(
            [
                "label",
                "create",
                name,
                "--repo",
                REPO,
                "--color",
                color,
                "--description",
                description,
                "--force",
            ]
        )


def ensure_milestones(epics: list[dict]) -> None:
    existing = set(
        filter(
            None,
            gh(["api", f"repos/{REPO}/milestones?state=all", "--jq", ".[].title"]).splitlines(),
        )
    )
    for title in dict.fromkeys(epic["milestone"] for epic in epics):
        if title in existing:
            continue
        gh(["api", "-X", "POST", f"repos/{REPO}/milestones", "-f", f"title={title}"])
        print(f"milestone created: {title}")


def render_epic(epic: dict, tasks: list[dict]) -> str:
    lines = [
        f"<!-- backlog:{epic['key']} -->",
        "",
        "## Context",
        "",
        epic["context"].strip(),
        "",
        "## Outcomes",
        "",
    ]
    lines += [f"- {outcome}" for outcome in epic["outcome"]]
    lines += ["", "## Tasks", ""]
    if tasks:
        lines += [f"- [ ] #{task['number']} {task['title']}" for task in tasks]
    else:
        lines.append("_Tasks are being created._")
    lines += [
        "",
        "---",
        f"`area/{epic['area']}` · milestone `{epic['milestone']}`",
        "",
    ]
    return "\n".join(lines)


def render_item(item: dict, epic: dict, epic_number: int | None) -> str:
    lines = [
        f"<!-- backlog:{item['key']} -->",
        "",
        "## Context",
        "",
        item["context"].strip(),
        "",
        "## Evidence",
        "",
    ]
    lines += [f"- `{evidence}`" for evidence in item["evidence"]]
    lines += ["", "## Acceptance criteria", ""]
    lines += [f"- [ ] {check}" for check in item["acceptance"]]
    lines += [
        "",
        "## Out of scope",
        "",
        item.get(
            "out_of_scope",
            "Anything not listed in the acceptance criteria. Follow-up work gets its own issue.",
        ).strip(),
        "",
        "## Risk",
        "",
        item.get(
            "risk",
            "Revert the merge commit. The previous index generation stays usable.",
        ).strip(),
        "",
        "---",
        f"Epic: {f'#{epic_number} ' if epic_number else ''}({epic['key'].upper()}) · "
        f"`area/{item['area']}` · `type/{item['type']}` · "
        f"`priority/{item['priority']}` · `size/{item['size']}`",
        "",
    ]
    return "\n".join(lines)


def existing_issues() -> dict[str, dict]:
    raw = gh(
        [
            "issue",
            "list",
            "--repo",
            REPO,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,body,state,labels,milestone",
        ]
    )
    import json

    found: dict[str, dict] = {}
    for issue in json.loads(raw or "[]"):
        match = MARKER_RE.search(issue.get("body") or "")
        if match:
            found[match.group(1)] = issue
    return found


def write_temp(text: str) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


def create_issue(title: str, body: str, labels: list[str], milestone: str | None) -> int:
    args = ["issue", "create", "--repo", REPO, "--title", title, "--body-file", write_temp(body)]
    for label in labels:
        args += ["--label", label]
    if milestone:
        args += ["--milestone", milestone]
    url = gh(args).strip().splitlines()[-1]
    try:
        return int(url.rstrip("/").rsplit("/", 1)[-1])
    except ValueError:
        fail(f"could not parse issue number from {url!r}")


def update_issue(number: int, title: str, body: str, labels: list[str], milestone: str | None) -> None:
    args = [
        "issue",
        "edit",
        str(number),
        "--repo",
        REPO,
        "--title",
        title,
        "--body-file",
        write_temp(body),
    ]
    for label in labels:
        args += ["--add-label", label]
    if milestone:
        args += ["--milestone", milestone]
    gh(args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="rewrite existing issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.6, help="pause between creations")
    args = parser.parse_args()

    epics, items = load_backlog()
    print(f"backlog: {len(epics)} epics, {len(items)} tasks, {len(epics) + len(items)} issues")

    account = gh(["api", "user", "--jq", ".login"]).strip()
    if account != ACCOUNT and not args.dry_run:
        fail(f"active gh account is {account!r}, expected {ACCOUNT!r}")

    if args.dry_run:
        for epic in epics:
            print(f"  {epic['key']:<6} {epic['title']}  [{', '.join(labels_for(epic, epic=True))}]")
        for item in items:
            print(
                f"  {item['key']:<28} {item['title']}  "
                f"[{', '.join(labels_for(item, epic=False))}]"
            )
        return

    ensure_labels(epics, items)
    ensure_milestones(epics)

    found = existing_issues()
    print(f"existing marked issues: {len(found)}")

    epic_numbers: dict[str, int] = {}
    created = updated = skipped = 0

    for epic in epics:
        current = found.get(epic["key"])
        body = render_epic(epic, [])
        if current:
            epic_numbers[epic["key"]] = current["number"]
            if args.update:
                update_issue(
                    current["number"],
                    epic["title"],
                    body,
                    labels_for(epic, epic=True),
                    epic["milestone"],
                )
                updated += 1
            else:
                skipped += 1
            continue
        number = create_issue(
            epic["title"], body, labels_for(epic, epic=True), epic["milestone"]
        )
        epic_numbers[epic["key"]] = number
        print(f"  epic #{number} {epic['title']}")
        created += 1
        time.sleep(args.sleep)

    epic_by_key = {epic["key"]: epic for epic in epics}
    task_numbers: dict[str, list[dict]] = {epic["key"]: [] for epic in epics}

    for index, item in enumerate(items, start=1):
        epic = epic_by_key[item["epic"]]
        current = found.get(item["key"])
        body = render_item(item, epic, epic_numbers.get(epic["key"]))
        if current:
            task_numbers[epic["key"]].append(
                {"number": current["number"], "title": item["title"]}
            )
            if args.update:
                update_issue(
                    current["number"],
                    item["title"],
                    body,
                    labels_for(item, epic=False),
                    epic["milestone"],
                )
                updated += 1
            else:
                skipped += 1
            continue
        number = create_issue(
            item["title"], body, labels_for(item, epic=False), epic["milestone"]
        )
        task_numbers[epic["key"]].append({"number": number, "title": item["title"]})
        print(f"  [{index:>2}/{len(items)}] #{number} {item['title']}")
        created += 1
        time.sleep(args.sleep)

    for epic in epics:
        number = epic_numbers[epic["key"]]
        update_issue(
            number,
            epic["title"],
            render_epic(epic, task_numbers[epic["key"]]),
            labels_for(epic, epic=True),
            epic["milestone"],
        )

    print()
    print(f"created: {created}  updated: {updated}  skipped: {skipped}")
    print(f"total tracked: {len(epics) + len(items)}")
    print("epics:")
    for epic in epics:
        print(f"  #{epic_numbers[epic['key']]:<4} {epic['title']}")


if __name__ == "__main__":
    main()

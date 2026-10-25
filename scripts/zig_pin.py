#!/usr/bin/env python3
"""Read the Zig pin from build.zig.zon and keep derived files in sync.

The minimum_zig_version value is the exact toolchain used by CI, releases,
and the developer bootstrap.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
ZON = ROOT / "build.zig.zon"
VERSION_FILE = ROOT / ".zigversion"
LOCK_FILE = ROOT / "zig.lock.json"
INDEX_URL = "https://ziglang.org/download/index.json"

TARGETS = (
    "x86_64-linux",
    "aarch64-linux",
    "x86_64-macos",
    "aarch64-macos",
    "x86_64-windows",
)

# Current instruction docs. Historical records (CHANGELOG.md, benchmarks/,
# docs/bench-*, docs/zig-0.17-migration.md) keep their measured versions.
LIVE_DOCS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    "docs/agents.md",
    "docs/engineering/AGENTIC_WORKFLOW.md",
)

PIN_RE = re.compile(r'\.minimum_zig_version\s*=\s*"([^"]+)"')
ENV_RE = re.compile(r"^\s*ZIG_VERSION:\s*['\"]?([^'\"#\s]+)", re.MULTILINE)
DOC_RE = re.compile(r"\bZig\b[^\n]{0,24}?(\d+\.\d+\.(?:\d+|x)[0-9A-Za-z.+-]*)")
# Development snapshots live under /builds/ and rotate away; every job
# downloads from /download/<version>/, so only stable releases work.
DEV_PIN_RE = re.compile(r"\d+\.\d+\.\d+-dev[0-9A-Za-z.+-]*")


def fail(message: str) -> NoReturn:
    print(f"zig-pin: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_pin() -> str:
    text = ZON.read_text(encoding="utf-8")
    matches = PIN_RE.findall(text)
    if len(matches) != 1:
        fail(f"{ZON.name} must contain exactly one minimum_zig_version, found {len(matches)}")
    return matches[0]


def archive_name(version: str, target: str) -> str:
    suffix = ".zip" if target.endswith("-windows") else ".tar.xz"
    return f"zig-{target}-{version}{suffix}"


def read_lock() -> dict:
    try:
        lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{LOCK_FILE.name} is missing; run scripts/zig_pin.py --update")
    except json.JSONDecodeError as err:
        fail(f"{LOCK_FILE.name} is not valid JSON: {err}")
    if not isinstance(lock, dict):
        fail(f"{LOCK_FILE.name} must contain a JSON object")
    return lock


def lock_entry(target: str) -> dict:
    version = read_pin()
    lock = read_lock()
    if lock.get("version") != version:
        fail(f"{LOCK_FILE.name} pins {lock.get('version')}, build.zig.zon pins {version}; run --update")
    archives = lock.get("archives")
    if not isinstance(archives, dict):
        fail(f"{LOCK_FILE.name} has no archives object")
    entry = archives.get(target)
    if not entry:
        fail(f"{LOCK_FILE.name} has no archive for {target}")
    expected = archive_name(version, target)
    if entry.get("file") != expected:
        fail(f"{LOCK_FILE.name} names {entry.get('file')}, expected {expected}")
    return entry


def update() -> None:
    version = read_pin()
    try:
        with urllib.request.urlopen(INDEX_URL, timeout=30) as response:
            index = json.load(response)
    except Exception as err:
        fail(f"cannot read {INDEX_URL}: {err}")

    if not isinstance(index, dict):
        fail(f"{INDEX_URL} did not return a JSON object")
    release = index.get(version)
    if not isinstance(release, dict):
        fail(f"Zig {version} is not in the download index")

    archives = {}
    for target in TARGETS:
        data = release.get(target)
        if not data:
            fail(f"Zig {version} has no archive for {target}")
        expected = archive_name(version, target)
        url = data.get("tarball", "")
        if url.rsplit("/", 1)[-1] != expected:
            fail(f"Zig {version} {target} archive is {url}, expected {expected}")
        sha256 = data.get("shasum", "")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            fail(f"Zig {version} {target} has an invalid shasum")
        archives[target] = {"file": expected, "sha256": sha256}

    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    lock = {"version": version, "archives": archives}
    LOCK_FILE.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"updated {VERSION_FILE.name} and {LOCK_FILE.name} for Zig {version}")


def check() -> None:
    version = read_pin()
    errors: list[str] = []

    if not VERSION_FILE.exists():
        errors.append(f"{VERSION_FILE.name} is missing; run --update")
    else:
        found = VERSION_FILE.read_text(encoding="utf-8").strip()
        if found != version:
            errors.append(f"{VERSION_FILE.name} has {found}, expected {version}")

    lock = read_lock()
    if lock.get("version") != version:
        errors.append(f"{LOCK_FILE.name} pins {lock.get('version')}, expected {version}")
    archives = lock.get("archives")
    if not isinstance(archives, dict):
        errors.append(f"{LOCK_FILE.name} has no archives object")
        archives = {}
    for target in TARGETS:
        entry = archives.get(target)
        if not entry:
            errors.append(f"{LOCK_FILE.name} has no archive for {target}")
            continue
        expected = archive_name(version, target)
        if entry.get("file") != expected:
            errors.append(f"{LOCK_FILE.name} {target} file is {entry.get('file')}, expected {expected}")
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")):
            errors.append(f"{LOCK_FILE.name} {target} sha256 is invalid")

    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        dev_pin = DEV_PIN_RE.search(text)
        if dev_pin:
            found = dev_pin.group(0).rstrip(".")
            errors.append(f"{relative} pins development snapshot {found}; use a stable release")
        for match in ENV_RE.finditer(text):
            found = match.group(1)
            if found != version:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line} pins {found}, expected {version}")

    for name in LIVE_DOCS:
        path = ROOT / name
        if not path.exists():
            errors.append(f"{name} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        dev_pin = DEV_PIN_RE.search(text)
        if dev_pin:
            found = dev_pin.group(0).rstrip(".")
            errors.append(f"{name} pins development snapshot {found}; use a stable release")
        for match in DOC_RE.finditer(text):
            # A version ending a sentence matches its trailing period; semver
            # never ends with one, so trim it before comparing.
            found = match.group(1).rstrip(".")
            if found != version:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{name}:{line} names Zig {found}, expected {version}")

    if errors:
        for error in errors:
            print(f"zig-pin: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"zig pin: {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print", action="store_true", help="print the pinned version")
    group.add_argument("--check", action="store_true", help="verify every live pin reference")
    group.add_argument("--update", action="store_true", help="regenerate .zigversion and zig.lock.json")
    group.add_argument("--file", metavar="TARGET", help="print the archive filename for a target")
    group.add_argument("--sha", metavar="TARGET", help="print the archive SHA-256 for a target")
    args = parser.parse_args()

    if args.print:
        print(read_pin())
    elif args.check:
        check()
    elif args.update:
        update()
    elif args.file:
        print(lock_entry(args.file)["file"])
    elif args.sha:
        print(lock_entry(args.sha)["sha256"])


if __name__ == "__main__":
    main()

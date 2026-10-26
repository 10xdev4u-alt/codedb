#!/usr/bin/env python3
"""Install the pinned Zig toolchain and run the ReleaseFast suite.

The toolchain and build caches live under a disk-backed cache, never the
system temp directory. The archive is checked against zig.lock.json before
it is extracted, and the installed compiler must report the pinned version.

Usage:
    python3 scripts/bootstrap.py
    python3 scripts/bootstrap.py --check
    python3 scripts/bootstrap.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import zig_pin  # noqa: E402

CHUNK = 1024 * 1024


def fail(message: str) -> NoReturn:
    print(f"bootstrap: {message}", file=sys.stderr)
    raise SystemExit(1)


def host_target() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Linux":
        arch = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}.get(machine)
    elif system == "Darwin":
        arch = {"x86_64": "x86_64", "arm64": "aarch64"}.get(machine)
    elif system == "Windows":
        arch = {"amd64": "x86_64", "x86_64": "x86_64"}.get(machine)
    else:
        arch = None
    if arch is None:
        fail(f"no pinned Zig archive for {system} {machine}")
    return f"{arch}-{'windows' if system == 'Windows' else system.lower()}"


def cache_root() -> Path:
    override = os.environ.get("CODEDB_CACHE_DIR")
    if override:
        root = Path(override).expanduser()
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "codedb"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Caches" / "codedb"
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "codedb"
    if root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        fail(f"{root} is under the system temp directory; set CODEDB_CACHE_DIR to a disk-backed path")
    # Resolve now so installation and the suite, which runs with cwd=ROOT,
    # agree on the location of a relative override.
    return root.resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) == expected:
            return
        destination.unlink()

    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if offset and response.status != 206:
                offset = 0
                partial.unlink(missing_ok=True)
            with partial.open("ab" if offset else "wb") as out:
                shutil.copyfileobj(response, out, length=CHUNK)
    except urllib.error.HTTPError as err:
        if not (err.code == 416 and offset):
            fail(f"download failed: {err}")
    except OSError as err:
        fail(f"download failed: {err}")

    actual = sha256_file(partial)
    if actual != expected:
        partial.unlink(missing_ok=True)
        fail(f"checksum mismatch for {destination.name}: expected {expected}, got {actual}")
    partial.replace(destination)


def extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
        return
    with tarfile.open(archive, "r:xz") as bundle:
        try:
            bundle.extractall(destination, filter="data")
        except TypeError:
            bundle.extractall(destination)


def read_version(zig: Path) -> str | None:
    if not zig.exists():
        return None
    try:
        completed = subprocess.run([str(zig), "version"], capture_output=True, text=True, timeout=30)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def install(cache: Path, target: str, version: str, force: bool) -> Path:
    archive_name = zig_pin.archive_name(version, target)
    entry = zig_pin.lock_entry(target)
    if entry["file"] != archive_name:
        fail(f"zig.lock.json names {entry['file']}, expected {archive_name}")

    toolchains = cache / "toolchains"
    installed = toolchains / f"zig-{target}-{version}"
    zig = installed / ("zig.exe" if target.endswith("-windows") else "zig")

    current = read_version(zig)
    if current == version and not force:
        print(f"bootstrap: using Zig {version} at {installed}", flush=True)
        return zig
    if current is not None and current != version and not force:
        fail(f"{zig} reports {current}, expected {version}; rerun with --force")
    if force and installed.exists():
        shutil.rmtree(installed)

    archive = cache / "downloads" / archive_name
    url = f"https://ziglang.org/download/{version}/{archive_name}"
    print(f"bootstrap: fetching {archive_name}", flush=True)
    download(url, archive, entry["sha256"])
    print(f"bootstrap: extracting to {installed}", flush=True)
    extract(archive, toolchains)

    current = read_version(zig)
    if current != version:
        fail(f"{zig} reports {current}, expected {version}")
    return zig


def run_suite(zig: Path, cache: Path) -> None:
    env = os.environ.copy()
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache / "zig-build")
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache / "zig-global")
    env["PATH"] = str(zig.parent) + os.pathsep + env.get("PATH", "")

    steps = ["test"]
    if platform.system() == "Windows":
        # The full Windows suite is tracked in #90-#93; CI gates this subset.
        steps = ["test-core", "test-semantic"]
    command = [str(zig), "build", *steps, "-Doptimize=ReleaseFast", "--summary", "all"]
    print(f"bootstrap: running {' '.join(steps)} in ReleaseFast", flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env)
    if completed.returncode != 0:
        fail(f"suite failed with exit code {completed.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="install and verify the toolchain without running tests")
    parser.add_argument("--force", action="store_true", help="reinstall the toolchain even when it matches")
    args = parser.parse_args()

    if sys.version_info < (3, 9):
        fail("Python 3.9 or newer is required")

    version = zig_pin.read_pin()
    target = host_target()
    cache = cache_root()
    zig = install(cache, target, version, args.force)
    print(f"bootstrap: Zig {version} ready", flush=True)
    if not args.check:
        run_suite(zig, cache)


if __name__ == "__main__":
    main()

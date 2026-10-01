#!/usr/bin/env python3
"""Read-only inventory of common developer disk-space consumers."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    id: str
    risk: str
    category: str
    path: str
    allocated_bytes: int | None
    apparent_bytes: int | None = None
    note: str = ""


def allocated_size(path: Path, timeout: float = 20.0) -> int | None:
    """Return physical bytes without following a top-level symlink."""
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        return metadata.st_blocks * 512
    if not stat.S_ISDIR(metadata.st_mode):
        return metadata.st_blocks * 512
    try:
        result = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True,
            text=True,
            timeout=max(0.1, timeout),
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.split()[0]) * 1024
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def apparent_size(path: Path) -> int | None:
    try:
        metadata = path.lstat()
        return metadata.st_size if not stat.S_ISDIR(metadata.st_mode) else None
    except OSError:
        return None


def command_output(command: list[str], timeout: float = 5.0) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def add_path(
    findings: list[Finding],
    seen: set[str],
    finding_id: str,
    risk: str,
    category: str,
    path: Path,
    note: str,
    deadline: float,
) -> None:
    try:
        lexical = path.expanduser().absolute()
        key = str(lexical)
        if key in seen or not lexical.exists():
            return
        seen.add(key)
        remaining = max(0.1, min(20.0, deadline - time.monotonic()))
        findings.append(
            Finding(
                id=finding_id,
                risk=risk,
                category=category,
                path=key,
                allocated_bytes=allocated_size(lexical, remaining),
                apparent_bytes=apparent_size(lexical),
                note=note,
            )
        )
    except OSError:
        return


def static_candidates(home: Path, deadline: float) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    rows = [
        (
            "expo-go",
            "cache",
            "expo",
            home / ".expo/expo-go",
            "Downloaded Expo Go cache.",
        ),
        (
            "expo-ios",
            "cache",
            "expo",
            home / ".expo/ios-simulator-app-cache",
            "Downloaded Expo simulator apps.",
        ),
        ("npm-cache", "cache", "npm", home / ".npm/_cacache", "npm content cache."),
        ("npm-npx", "cache", "npm", home / ".npm/_npx", "Temporary npx installs."),
        (
            "playwright",
            "rebuildable",
            "browser-tools",
            home / "Library/Caches/ms-playwright",
            "Downloaded Playwright browsers.",
        ),
        (
            "playwright-linux",
            "rebuildable",
            "browser-tools",
            home / ".cache/ms-playwright",
            "Downloaded Playwright browsers.",
        ),
        (
            "pnpm-cache",
            "cache",
            "pnpm",
            home / "Library/Caches/pnpm",
            "pnpm metadata cache.",
        ),
        (
            "bun-cache",
            "cache",
            "bun",
            home / "Library/Caches/bun",
            "Bun download cache.",
        ),
        (
            "homebrew-cache",
            "cache",
            "homebrew",
            home / "Library/Caches/Homebrew",
            "Homebrew downloads.",
        ),
        (
            "xcode-derived",
            "rebuildable",
            "xcode",
            home / "Library/Developer/Xcode/DerivedData",
            "Rebuildable; do not remove during a build.",
        ),
        (
            "xcode-archives",
            "protected",
            "xcode",
            home / "Library/Developer/Xcode/Archives",
            "Release archives; may be needed for export or symbols.",
        ),
        (
            "simulators",
            "review",
            "ios-simulator",
            home / "Library/Developer/CoreSimulator/Devices",
            "Contains simulator apps and app data.",
        ),
        (
            "ios-backups",
            "protected",
            "device-backup",
            home / "Library/Application Support/MobileSync/Backup",
            "iPhone/iPad backups; never a cache.",
        ),
        (
            "cursor-state",
            "review",
            "editor",
            home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb",
            "May contain conversations, settings, and extension state.",
        ),
        (
            "chrome-model",
            "review",
            "browser",
            home / "Library/Application Support/Google/Chrome/OptGuideOnDeviceModel",
            "Downloaded model; inspect only while Chrome is closed.",
        ),
        (
            "desktop",
            "protected",
            "personal",
            home / "Desktop",
            "Personal data. Inspect; never auto-delete.",
        ),
        (
            "downloads",
            "review",
            "personal",
            home / "Downloads",
            "User decision required for every file.",
        ),
        (
            "documents",
            "protected",
            "personal",
            home / "Documents",
            "Personal data. Never auto-delete.",
        ),
    ]
    for row in rows:
        if time.monotonic() >= deadline:
            break
        add_path(findings, seen, *row, deadline)

    store = command_output(["pnpm", "store", "path"])
    if store and time.monotonic() < deadline:
        add_path(
            findings,
            seen,
            "pnpm-store",
            "rebuildable",
            "pnpm",
            Path(store),
            "Use pnpm store prune; do not delete the whole store by default.",
            deadline,
        )

    docker_paths = [
        home / "Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw",
        home / ".docker/desktop/vms/0/data/Docker.raw",
    ]
    for docker_path in docker_paths:
        if time.monotonic() >= deadline:
            break
        add_path(
            findings,
            seen,
            "docker-raw",
            "review",
            "docker",
            docker_path,
            "Sparse VM disk. Inspect images, containers, and volumes with Docker.",
            deadline,
        )
    return findings


def iter_code_candidates(
    code_root: Path, deadline: float
) -> Iterable[tuple[str, str, str, Path, str]]:
    if not code_root.is_dir():
        return
    root_depth = len(code_root.parts)
    for current, dirs, _files in os.walk(code_root, followlinks=False):
        if time.monotonic() >= deadline:
            return
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        dirs[:] = [
            d for d in dirs if d != ".git" and not (current_path / d).is_symlink()
        ]
        if depth > 9:
            dirs[:] = []
            continue

        parts = current_path.parts
        if ".claude" in parts and "worktrees" in parts:
            index = parts.index("worktrees")
            if len(parts) == index + 2:
                yield (
                    f"worktree-{current_path.name}",
                    "review",
                    "git-worktree",
                    current_path,
                    "Check branch, changes, ownership, and integration status before lifecycle removal.",
                )
                dirs[:] = []
                continue

        for name in list(dirs):
            child = current_path / name
            if name == "node_modules":
                yield (
                    f"node-modules-{child.parent.name}",
                    "review",
                    "node-modules",
                    child,
                    "Active dependency tree; verify the owning project before removal.",
                )
                try:
                    for nested in child.iterdir():
                        if nested.is_dir() and (
                            nested.name.startswith(".old_modules-")
                            or nested.name == ".bun"
                        ):
                            yield (
                                f"stale-node-{nested.name}",
                                "rebuildable",
                                "stale-node-install",
                                nested,
                                "Likely install residue; verify packageManager and lockfiles.",
                            )
                except OSError:
                    pass
                dirs.remove(name)
            elif name in {".next", ".turbo", "coverage"}:
                yield (
                    f"build-{name}-{child.parent.name}",
                    "rebuildable",
                    "build-output",
                    child,
                    "Generated output; verify ownership and active processes.",
                )
                dirs.remove(name)


def format_size(value: int | None) -> str:
    if value is None:
        return "unknown"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return "unknown"


def write_json_exclusive(path: Path, report: dict) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except FileExistsError as error:
        raise ValueError(f"Refusing to overwrite existing file: {path}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-root", default=str(Path.home() / "Code"))
    parser.add_argument("--max-seconds", type=float, default=60.0)
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + max(5.0, args.max_seconds)
    home = Path.home().resolve()
    findings = static_candidates(home, deadline)
    seen = {finding.path for finding in findings}

    for row in iter_code_candidates(
        Path(args.code_root).expanduser().resolve(), deadline
    ):
        if time.monotonic() >= deadline:
            break
        add_path(findings, seen, *row, deadline)

    findings.sort(key=lambda item: item.allocated_bytes or -1, reverse=True)
    disk = shutil.disk_usage(home)
    report = {
        "platform": platform.system(),
        "home": str(home),
        "code_root": str(Path(args.code_root).expanduser()),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "partial": time.monotonic() >= deadline,
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "findings": [asdict(item) for item in findings[: max(1, args.top)]],
    }

    print(f"Free: {format_size(disk.free)} / {format_size(disk.total)}")
    if report["partial"]:
        print("Scan reached its time budget; results are partial.")
    print(f"{'RISK':12} {'ALLOCATED':>12}  CATEGORY          PATH")
    for finding in findings[: max(1, args.top)]:
        sparse = ""
        if (
            finding.apparent_bytes
            and finding.allocated_bytes is not None
            and finding.apparent_bytes > max(1, finding.allocated_bytes) * 2
        ):
            sparse = f" (apparent {format_size(finding.apparent_bytes)})"
        print(
            f"{finding.risk:12} {format_size(finding.allocated_bytes):>12}  "
            f"{finding.category:16} {finding.path}{sparse}"
        )
        print(f"{'':28}  {finding.note}")

    if args.json_out:
        output = Path(args.json_out).expanduser()
        try:
            write_json_exclusive(output, report)
        except ValueError as error:
            parser.error(str(error))
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

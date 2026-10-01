#!/usr/bin/env python3
"""One-pass, read-only inventory of large directories and files."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import time
from collections import defaultdict
from pathlib import Path


def format_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return "unknown"


def risk_for_path(path: Path, home: Path) -> str:
    try:
        relative = path.relative_to(home)
    except ValueError:
        return "review"
    parts = relative.parts
    if parts and parts[0] in {"Desktop", "Documents"}:
        return "protected"
    if parts and parts[0] == "Downloads":
        return "review"
    if len(parts) >= 2 and parts[:2] == ("Library", "Caches"):
        return "cache"
    if "worktrees" in parts or ".git" in parts or "node_modules" in parts:
        return "review"
    if parts and parts[0] == "Code":
        return "review"
    return "review"


def normalize_roots(paths: list[str]) -> list[Path]:
    roots = sorted(
        {
            Path(path).expanduser().absolute()
            for path in paths
            if Path(path).expanduser().exists()
        },
        key=lambda path: len(path.parts),
    )
    selected = []
    for root in roots:
        if any(parent == root or parent in root.parents for parent in selected):
            continue
        selected.append(root)
    return selected


def scan_roots(
    roots: list[Path], depth: int, large_file_bytes: int, max_seconds: float
) -> dict:
    started = time.monotonic()
    deadline = started + max_seconds if max_seconds > 0 else None
    home = Path.home().resolve()
    allocated: dict[str, int] = defaultdict(int)
    large_files = []
    errors = []
    seen_inodes: set[tuple[int, int]] = set()
    entries = 0
    partial = False

    for root in roots:
        stack = [(root, ())]
        while stack:
            if deadline is not None and time.monotonic() >= deadline:
                partial = True
                break
            current, relative_parts = stack.pop()
            try:
                metadata = current.lstat()
            except OSError as error:
                errors.append({"path": str(current), "error": str(error)})
                continue
            entries += 1
            identity = (metadata.st_dev, metadata.st_ino)
            own_bytes = metadata.st_blocks * 512
            if identity not in seen_inodes:
                seen_inodes.add(identity)
                allocated[str(root)] += own_bytes
                for level in range(1, min(depth, len(relative_parts)) + 1):
                    bucket = root.joinpath(*relative_parts[:level])
                    allocated[str(bucket)] += own_bytes
                if stat.S_ISREG(metadata.st_mode) and own_bytes >= large_file_bytes:
                    large_files.append(
                        {
                            "path": str(current),
                            "allocated_bytes": own_bytes,
                            "apparent_bytes": metadata.st_size,
                            "risk": risk_for_path(current, home),
                        }
                    )
            if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
                try:
                    with os.scandir(current) as iterator:
                        children = [Path(item.path) for item in iterator]
                    stack.extend(
                        (child, relative_parts + (child.name,)) for child in children
                    )
                except OSError as error:
                    errors.append({"path": str(current), "error": str(error)})
            if entries % 100_000 == 0:
                print(
                    f"scanned {entries:,} entries in {time.monotonic() - started:.0f}s",
                    file=sys.stderr,
                    flush=True,
                )
        if partial:
            break

    buckets = [
        {
            "path": path,
            "allocated_bytes": size,
            "risk": risk_for_path(Path(path), home),
        }
        for path, size in allocated.items()
    ]
    buckets.sort(key=lambda row: row["allocated_bytes"], reverse=True)
    large_files.sort(key=lambda row: row["allocated_bytes"], reverse=True)
    disk = shutil.disk_usage(home)
    return {
        "read_only": True,
        "partial": partial,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "entries_scanned": entries,
        "hardlink_deduplication": "device-and-inode",
        "roots": [str(root) for root in roots],
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "buckets": buckets,
        "large_files": large_files,
        "errors": errors,
    }


def write_json_exclusive(path: Path, report: dict) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except FileExistsError as error:
        raise ValueError(f"Refusing to overwrite existing file: {path}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--large-file-mib", type=int, default=512)
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--top", type=int, default=60)
    parser.add_argument("--json-out")
    args = parser.parse_args()
    if not 1 <= args.depth <= 3:
        parser.error("--depth must be between 1 and 3")
    if args.large_file_mib < 1:
        parser.error("--large-file-mib must be positive")
    home = Path.home()
    requested = args.root or [
        str(home / "Code"),
        str(home / "Library"),
        str(home / "Desktop"),
        str(home / "Documents"),
        str(home / "Downloads"),
    ]
    roots = normalize_roots(requested)
    if not roots:
        parser.error("no readable roots found")
    report = scan_roots(
        roots,
        args.depth,
        args.large_file_mib * 1024 * 1024,
        max(0, args.max_seconds),
    )
    print(
        f"Read-only deep inventory: {report['entries_scanned']:,} entries in "
        f"{report['elapsed_seconds']:.1f}s; free {format_size(report['disk']['free'])}"
    )
    if report["partial"]:
        print(
            "Time budget reached; all reported measurements are valid but incomplete."
        )
    print("Largest directory buckets:")
    for row in report["buckets"][: max(0, args.top)]:
        print(
            f"  {format_size(row['allocated_bytes']):>10}  {row['risk']:9}  {row['path']}"
        )
    print("Largest individual files:")
    for row in report["large_files"][: max(0, args.top)]:
        print(
            f"  {format_size(row['allocated_bytes']):>10}  {row['risk']:9}  {row['path']}"
        )
    if args.json_out:
        try:
            write_json_exclusive(Path(args.json_out).expanduser(), report)
        except ValueError as error:
            parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

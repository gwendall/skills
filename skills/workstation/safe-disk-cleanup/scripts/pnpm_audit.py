#!/usr/bin/env python3
"""Explain pnpm store cleanup eligibility without pruning anything."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(command: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )


def active_pnpm_processes() -> list[dict]:
    result = run(["ps", "-axo", "pid=,args="], timeout=5)
    if result.returncode != 0:
        raise ValueError("Unable to inspect pnpm processes")
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        lowered = f" {parts[1].lower()} "
        if "pnpm_audit.py" in lowered:
            continue
        if " pnpm " in lowered or "/pnpm " in lowered or "pnpm.cjs" in lowered:
            rows.append({"pid": int(parts[0]), "arguments": parts[1]})
    return rows


def allocated_size(path: Path) -> int | None:
    if not path.exists():
        return 0
    result = run(["du", "-sk", str(path)], timeout=120)
    if result.returncode != 0:
        return None
    first = result.stdout.split(None, 1)
    if not first or not first[0].isdigit():
        return None
    return int(first[0]) * 1024


def build_report(
    store_path: str,
    store_bytes: int | None,
    status_returncode: int,
    status_output: str,
    active_processes: list[dict],
) -> dict:
    blockers = []
    if active_processes:
        blockers.append("one or more pnpm processes are currently visible")
    if status_returncode != 0:
        blockers.append("pnpm store status did not confirm an unmodified store")
    decision = "blocked" if blockers else "review-ready"
    return {
        "read_only": True,
        "prune_performed": False,
        "resource": "pnpm-content-addressable-store",
        "store_path": store_path,
        "allocated_bytes": store_bytes,
        "estimated_reclaim_bytes": None,
        "decision": decision,
        "preconditions_met": decision == "review-ready",
        "safe_to_delete_now": False,
        "fresh_approval_required": True,
        "evidence": [
            f"pnpm store status exit code: {status_returncode}",
            f"pnpm store status: {status_output.strip() or 'no output'}",
            f"visible pnpm process count: {len(active_processes)}",
        ],
        "blockers": blockers,
        "consequence": (
            "Pruning removes unreferenced packages from the shared store; later "
            "installs may redownload them."
        ),
        "recovery": "Packages can be fetched again from their configured registries.",
        "recommended_action": "pnpm store prune" if not blockers else None,
        "active_pnpm_processes": active_processes,
    }


def collect_report() -> dict:
    path_result = run(["pnpm", "store", "path"])
    if path_result.returncode != 0:
        raise ValueError(f"pnpm store path failed: {path_result.stderr.strip()}")
    store_path = path_result.stdout.strip()
    if not store_path:
        raise ValueError("pnpm store path returned an empty path")
    processes = active_pnpm_processes()
    status_result = run(["pnpm", "store", "status"], timeout=120)
    status_output = (status_result.stdout + "\n" + status_result.stderr).strip()
    return build_report(
        store_path,
        allocated_size(Path(store_path).expanduser()),
        status_result.returncode,
        status_output,
        processes,
    )


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
    parser.add_argument("--json-out")
    args = parser.parse_args()
    if not shutil.which("pnpm"):
        parser.error("pnpm is required")
    try:
        report = collect_report()
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        parser.error(str(error))
    print("PNPM STORE DECISION AUDIT - read only")
    print(f"  decision: {report['decision']}")
    print(f"  allocated: {format_size(report['allocated_bytes'])}")
    print(f"  path: {report['store_path']}")
    for blocker in report["blockers"]:
        print(f"  blocker: {blocker}")
    if report["recommended_action"]:
        print(f"  after fresh approval: {report['recommended_action']}")
    if args.json_out:
        try:
            write_json_exclusive(Path(args.json_out).expanduser(), report)
        except ValueError as error:
            parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

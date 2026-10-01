#!/usr/bin/env python3
"""Explain iOS Simulator cleanup decisions without deleting devices."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )


def active_developer_processes() -> list[dict]:
    result = run(["ps", "-axo", "pid=,args="], timeout=5)
    if result.returncode != 0:
        raise ValueError("Unable to inspect Simulator-related processes")
    markers = ("xcodebuild", "/simulator.app/", " simctl ")
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        lowered = f" {parts[1].lower()} "
        marker = next((item for item in markers if item in lowered), None)
        if marker and "simulator_audit.py" not in lowered:
            rows.append({"pid": int(parts[0]), "matched_activity": marker.strip()})
    return rows


def classify_device(device: dict, runtime: str, active_processes: list[dict]) -> dict:
    available = bool(device.get("isAvailable", False))
    state = device.get("state", "Unknown")
    blockers = []
    decision = "review"
    recommended_action = None
    if state == "Booted":
        decision = "blocked"
        blockers.append("device is booted")
    elif active_processes:
        decision = "blocked"
        blockers.append("Simulator, simctl, or xcodebuild activity is visible")
    elif not available:
        decision = "review-ready"
        recommended_action = f"xcrun simctl delete {device.get('udid')}"
    else:
        blockers.append(
            "available device may contain app data, keychains, and settings"
        )
    allocated_bytes = (device.get("dataPathSize") or 0) + (
        device.get("logPathSize") or 0
    )
    return {
        "resource": f"simulator:{device.get('udid')}",
        "name": device.get("name"),
        "runtime": runtime,
        "state": state,
        "is_available": available,
        "last_booted_at": device.get("lastBootedAt"),
        "allocated_bytes": allocated_bytes,
        "estimated_reclaim_bytes": allocated_bytes,
        "decision": decision,
        "preconditions_met": decision == "review-ready",
        "safe_to_delete_now": False,
        "fresh_approval_required": True,
        "evidence": [
            f"state: {state}",
            f"available runtime: {available}",
            f"last booted: {device.get('lastBootedAt', 'unknown')}",
        ],
        "blockers": blockers,
        "consequence": "Deletion removes installed apps, app data, keychains, and device settings.",
        "recovery": "The empty device can be recreated, but its local state cannot.",
        "recommended_action": recommended_action,
    }


def build_report(devices_payload: dict, active_processes: list[dict]) -> dict:
    devices = []
    for runtime, rows in devices_payload.get("devices", {}).items():
        devices.extend(classify_device(row, runtime, active_processes) for row in rows)
    devices.sort(key=lambda row: row["allocated_bytes"], reverse=True)
    return {
        "read_only": True,
        "deletion_performed": False,
        "active_developer_processes": active_processes,
        "devices": devices,
    }


def collect_report() -> dict:
    result = run(["xcrun", "simctl", "list", "devices", "--json"])
    if result.returncode != 0:
        raise ValueError(f"simctl failed: {result.stderr.strip()}")
    return build_report(json.loads(result.stdout), active_developer_processes())


def format_size(value: int) -> str:
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
    if not shutil.which("xcrun"):
        parser.error("xcrun is required")
    try:
        report = collect_report()
    except (
        json.JSONDecodeError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as error:
        parser.error(str(error))
    print("SIMULATOR DECISION AUDIT - read only")
    for device in report["devices"]:
        print(
            f"  {device['decision']:12} {format_size(device['allocated_bytes']):>10} "
            f"{device['name']} ({device['state']}) {device['resource']}"
        )
        for blocker in device["blockers"]:
            print(f"    blocker: {blocker}")
        if device["recommended_action"]:
            print(f"    after fresh approval: {device['recommended_action']}")
    if args.json_out:
        try:
            write_json_exclusive(Path(args.json_out).expanduser(), report)
        except ValueError as error:
            parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

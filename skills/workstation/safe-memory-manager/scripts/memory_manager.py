#!/usr/bin/env python3
"""Inspect macOS memory use without signaling or stopping processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

PROTECTED_MARKERS = (
    "claude",
    "codex",
    "cmux",
    "ssh",
    "login",
    "terminal",
    "docker",
    "simulator",
)
CMUX_BIN = Path("/Applications/cmux.app/Contents/Resources/bin/cmux")


def run(command: list[str], timeout: float = 10.0) -> str:
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or f"exit {completed.returncode}"
        raise RuntimeError(f"{' '.join(command)} failed: {message}")
    return completed.stdout


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return "unknown"


def parse_memory_size(value: str) -> int | None:
    match = re.fullmatch(r"([\d.]+)([KMGT]?)", value.strip(), re.IGNORECASE)
    if not match:
        return None
    multiplier = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    return int(float(match.group(1)) * multiplier[match.group(2).upper()])


def elapsed_seconds(value: str) -> int | None:
    match = re.fullmatch(r"(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)", value)
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def process_family(command: str) -> str:
    lowered = command.lower()
    basename = Path(command.split()[0]).name.lower() if command else "unknown"
    if "claude" in lowered or "codex" in lowered:
        return "agent"
    if "cmux" in lowered:
        return "terminal-manager"
    if "ms-playwright" in lowered or "chrome for testing" in lowered:
        return "test-browser"
    if "google chrome" in lowered:
        return "browser"
    if "coresimulator" in lowered or "simulator" in lowered:
        return "simulator"
    if "docker" in lowered or "com.docker" in lowered:
        return "docker"
    if basename in {"node", "npm", "npx", "bun", "deno"} or basename.startswith(
        "next-server"
    ):
        return "developer-runtime"
    if basename.startswith("python"):
        return "python"
    if ".app/" in lowered:
        return "gui-app"
    if command.startswith(("/System/", "/usr/bin/", "/usr/libexec/", "/usr/sbin/")):
        return "system"
    return "other"


def lifecycle_state(process: dict) -> str:
    if process["state"].startswith("Z"):
        return "zombie-exited"
    if process["ppid"] == 1:
        return "orphan-or-launchd-owned-live"
    if process["tty"] not in {"??", "?", "-"}:
        return "attached-terminal-live"
    if process["state"].startswith(("S", "I")):
        return "detached-sleeping-live"
    return "detached-active-live"


def read_processes(include_arguments: bool = False) -> list[dict]:
    output = run(
        [
            "/bin/ps",
            "-axo",
            "pid=,ppid=,uid=,state=,etime=,rss=,pcpu=,tty=,comm=",
        ]
    )
    arguments = read_arguments() if include_arguments else {}
    processes = []
    for line in output.splitlines():
        parts = line.strip().split(None, 8)
        if len(parts) != 9:
            continue
        pid, ppid, uid, state, elapsed, rss_kib, cpu, tty, command = parts
        try:
            row = {
                "pid": int(pid),
                "ppid": int(ppid),
                "uid": int(uid),
                "state": state,
                "elapsed": elapsed,
                "elapsed_seconds": elapsed_seconds(elapsed),
                "rss_bytes": int(rss_kib) * 1024,
                "cpu_percent": float(cpu),
                "tty": tty,
                "command": command,
                "family": process_family(command),
            }
            row["lifecycle"] = lifecycle_state(row)
        except ValueError:
            continue
        if include_arguments:
            row["arguments"] = arguments.get(row["pid"], "")
        processes.append(row)
    return processes


def read_arguments() -> dict[int, str]:
    output = run(["/bin/ps", "-axo", "pid=,command="])
    rows = {}
    for line in output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            rows[int(parts[0])] = parts[1]
    return rows


def read_listening_ports() -> dict[int, list[str]]:
    try:
        output = run(
            ["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-Fpfn"],
            timeout=15,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return {}
    ports: dict[int, list[str]] = defaultdict(list)
    current_pid = None
    for line in output.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current_pid = int(line[1:])
        elif line.startswith("n") and current_pid is not None:
            ports[current_pid].append(line[1:])
    return dict(ports)


def read_footprints(limit: int) -> dict[int, int]:
    try:
        output = run(
            [
                "/usr/bin/top",
                "-l",
                "1",
                "-n",
                str(limit),
                "-o",
                "mem",
                "-stats",
                "pid,command,mem",
            ],
            timeout=30,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return {}
    footprints = {}
    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+.+?\s+([\d.]+[KMGT]?)\s*$", line)
        if match and (size := parse_memory_size(match.group(2))) is not None:
            footprints[int(match.group(1))] = size
    return footprints


def read_process_footprint(pid: int) -> int | None:
    try:
        output = run(["/usr/bin/footprint", "-p", str(pid)], timeout=15)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"Footprint:\s*([\d.]+)\s*([KMGT]B)", output)
    if not match:
        return None
    return parse_memory_size(match.group(1) + match.group(2)[0])


def compact_resources(value: dict) -> dict:
    return {
        key: value.get(key)
        for key in ("memory_bytes", "resident_bytes", "cpu_percent", "process_count")
    }


def read_cmux_summary() -> dict | None:
    if not CMUX_BIN.is_file():
        return None
    try:
        value = json.loads(run([str(CMUX_BIN), "top", "--all", "--json"], timeout=15))
    except (OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return {
        "active": value.get("active"),
        "caller": value.get("caller"),
        "coding_agents": [
            {
                "id": row.get("id"),
                "display_name": row.get("display_name"),
                "resources": compact_resources(row.get("resources", {})),
            }
            for row in value.get("coding_agents", [])
        ],
        "windows": [
            {
                "ref": row.get("ref"),
                "visible": row.get("visible"),
                "workspace_count": row.get("workspace_count"),
                "resources": compact_resources(row.get("resources", {})),
            }
            for row in value.get("windows", [])
        ],
    }


def read_cwd(pid: int) -> str | None:
    try:
        output = run(
            ["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            timeout=5,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return None
    return next(
        (line[1:] for line in output.splitlines() if line.startswith("n")), None
    )


def read_system_memory() -> dict:
    total = int(run(["/usr/sbin/sysctl", "-n", "hw.memsize"]).strip())
    pressure_output = run(["/usr/bin/memory_pressure", "-Q"], timeout=20)
    pressure_match = re.search(r"free percentage:\s*(\d+)%", pressure_output)
    swap_output = run(["/usr/sbin/sysctl", "vm.swapusage"]).strip()
    swap_match = re.search(
        r"total = ([\d.]+)M\s+used = ([\d.]+)M\s+free = ([\d.]+)M", swap_output
    )
    vm_output = run(["/usr/bin/vm_stat"])
    page_match = re.search(r"page size of (\d+) bytes", vm_output)
    page_size = int(page_match.group(1)) if page_match else 4096
    vm = {}
    for line in vm_output.splitlines():
        match = re.match(r"([^:]+):\s+([\d.]+)\.?$", line.strip())
        if match:
            vm[match.group(1)] = int(float(match.group(2))) * page_size
    swap = None
    if swap_match:
        swap = {
            "total_bytes": int(float(swap_match.group(1)) * 1024 * 1024),
            "used_bytes": int(float(swap_match.group(2)) * 1024 * 1024),
            "free_bytes": int(float(swap_match.group(3)) * 1024 * 1024),
        }
    return {
        "physical_bytes": total,
        "available_percent": int(pressure_match.group(1)) if pressure_match else None,
        "swap": swap,
        "compressed_bytes": vm.get("Pages occupied by compressor"),
        "wired_bytes": vm.get("Pages wired down"),
        "free_bytes": vm.get("Pages free"),
        "purgeable_bytes": vm.get("Pages purgeable"),
    }


def process_groups(processes: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for process in processes:
        grouped[process["family"]].append(process)
    return sorted(
        (
            {
                "family": family,
                "process_count": len(rows),
                "rss_bytes": sum(row["rss_bytes"] for row in rows),
            }
            for family, rows in grouped.items()
        ),
        key=lambda row: row["rss_bytes"],
        reverse=True,
    )


def tty_groups(processes: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for process in processes:
        if process["tty"] not in {"??", "?", "-"}:
            grouped[process["tty"]].append(process)
    return sorted(
        (
            {
                "tty": tty,
                "process_count": len(rows),
                "rss_bytes": sum(row["rss_bytes"] for row in rows),
                "pids": [row["pid"] for row in rows],
            }
            for tty, rows in grouped.items()
        ),
        key=lambda row: row["rss_bytes"],
        reverse=True,
    )


def review_reason(process: dict, current_uid: int) -> str | None:
    if process["state"].startswith("Z"):
        return "zombie: consumes effectively no RSS; inspect its parent instead of killing it"
    if process["uid"] != current_uid:
        return None
    if process["ppid"] == 1 and process["family"] == "developer-runtime":
        return "live orphan or launchd-owned runtime; PPID 1 is not evidence that it is unused"
    footprint = process.get("footprint_bytes")
    measured = footprint if footprint is not None else process["rss_bytes"]
    metric = "physical footprint" if footprint is not None else "RSS fallback"
    if measured >= 512 * 1024 * 1024:
        if process["family"] == "agent":
            return f"high {metric}; protected agent session, inspect/hibernate through its owner"
        if process["family"] == "terminal-manager":
            return (
                f"high {metric}; protected multiplexer, inspect sessions with cmux top"
            )
        if process["family"] in {"gui-app", "browser"}:
            return (
                f"high {metric}; use the application's normal quit or resource controls"
            )
        return f"high {metric} snapshot; confirm pressure and ownership before quitting"
    if (
        process["family"] in {"developer-runtime", "test-browser"}
        and process["tty"] in {"??", "?", "-"}
        and (process["elapsed_seconds"] or 0) >= 1800
    ):
        return "long-lived detached developer process; verify cwd, port, and owner"
    return None


def build_snapshot(top: int, include_arguments: bool) -> dict:
    processes = read_processes(include_arguments)
    ports = read_listening_ports()
    footprints = read_footprints(max(50, top))
    current_uid = os.getuid()
    reviewed = []
    for process in processes:
        process["ports"] = ports.get(process["pid"], [])
        process["footprint_bytes"] = footprints.get(process["pid"])
        reason = review_reason(process, current_uid)
        if reason:
            reviewed.append(
                {**process, "reason": reason, "cwd": read_cwd(process["pid"])}
            )
    ranking = lambda row: row["footprint_bytes"] or row["rss_bytes"]
    return {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "system": read_system_memory(),
        "process_count": len(processes),
        "zombie_count": sum(row["state"].startswith("Z") for row in processes),
        "groups": process_groups(processes),
        "terminal_sessions": tty_groups(processes)[:top],
        "cmux": read_cmux_summary(),
        "top_processes": sorted(processes, key=ranking, reverse=True)[:top],
        "review_candidates": sorted(reviewed, key=ranking, reverse=True),
    }


def render_snapshot(report: dict) -> None:
    system = report["system"]
    swap = system["swap"]
    print("SAFE MEMORY SNAPSHOT - read only")
    print(
        f"Physical: {format_bytes(system['physical_bytes'])}; "
        f"memory_pressure available: {system['available_percent']}%; "
        f"compressed: {format_bytes(system['compressed_bytes'] or 0)}"
    )
    if swap:
        print(
            f"Swap currently allocated: {format_bytes(swap['used_bytes'])} / {format_bytes(swap['total_bytes'])}"
        )
    print(f"Processes: {report['process_count']}; zombies: {report['zombie_count']}")
    if report["cmux"]:
        print("\ncmux owner-native accounting (unique physical footprint):")
        for window in report["cmux"]["windows"]:
            resources = window["resources"]
            print(
                f"  {window['ref']}: {format_bytes(resources['memory_bytes'] or 0)}, "
                f"{resources['process_count']} processes, {window['workspace_count']} workspaces"
            )
        for agent in report["cmux"]["coding_agents"]:
            resources = agent["resources"]
            print(
                f"  agent {agent['display_name']}: "
                f"{format_bytes(resources['memory_bytes'] or 0)}, "
                f"{resources['process_count']} processes"
            )
    print("\nLargest process families (RSS is not additive physical footprint):")
    for group in report["groups"][:12]:
        print(
            f"  {format_bytes(group['rss_bytes']):>10}  {group['process_count']:>3}  {group['family']}"
        )
    print("\nLargest processes (physical footprint when available; RSS fallback):")
    print("  Footprint may include compressed/swapped memory at its original size.")
    for process in report["top_processes"]:
        ports = ", ".join(process.get("ports", []))
        suffix = f" ports={ports}" if ports else ""
        footprint = process.get("footprint_bytes")
        measurement = (
            f"footprint={format_bytes(footprint)}"
            if footprint is not None
            else f"RSS={format_bytes(process['rss_bytes'])}"
        )
        print(
            f"  {measurement:>21}  pid={process['pid']:<6} "
            f"ppid={process['ppid']:<6} {process['state']:<4} {process['elapsed']:<12} "
            f"{process['family']}/{process['lifecycle']}: {process['command']}{suffix}"
        )
    print("\nReview candidates (never proof that a process is unused):")
    if not report["review_candidates"]:
        print("  none")
    for process in report["review_candidates"]:
        ports = ", ".join(process["ports"]) or "none detected"
        footprint = process.get("footprint_bytes")
        measurement = footprint if footprint is not None else process["rss_bytes"]
        cwd = process.get("cwd") or "unknown"
        print(
            f"  pid={process['pid']} {format_bytes(measurement)} "
            f"{process['command']} - {process['reason']}; cwd: {cwd}; ports: {ports}"
        )

    print(
        "\nLargest attached terminal sessions (aggregate RSS, not guaranteed reclaimable):"
    )
    for session in report["terminal_sessions"][:10]:
        pids = ",".join(str(pid) for pid in session["pids"][:8])
        if len(session["pids"]) > 8:
            pids += ",…"
        print(
            f"  {format_bytes(session['rss_bytes']):>10}  {session['tty']:<10} "
            f"{session['process_count']:>3} processes  pids={pids}"
        )


def process_identity(pid: int) -> dict:
    output = run(
        [
            "/bin/ps",
            "-p",
            str(pid),
            "-o",
            "pid=,uid=,ppid=,state=,lstart=,tty=,comm=",
        ]
    )
    parts = output.strip().split(None, 10)
    if len(parts) != 11:
        raise ValueError(f"Process {pid} does not exist or could not be identified")
    parsed_pid, uid, ppid, state = (
        int(parts[0]),
        int(parts[1]),
        int(parts[2]),
        parts[3],
    )
    started = " ".join(parts[4:9])
    tty = parts[9]
    command = parts[10]
    arguments = read_arguments().get(pid, "")
    identity = {
        "pid": parsed_pid,
        "uid": uid,
        "ppid": ppid,
        "state": state,
        "started": started,
        "tty": tty,
        "command": command,
        "family": process_family(command),
        "cwd": read_cwd(pid),
        "ports": read_listening_ports().get(pid, []),
        "arguments_sha256": hashlib.sha256(arguments.encode()).hexdigest(),
        "protected_marker": next(
            (marker for marker in PROTECTED_MARKERS if marker in arguments.lower()),
            None,
        ),
    }
    identity["lifecycle"] = lifecycle_state(identity)
    return identity


def protected_descendant_marker(pid: int) -> str | None:
    processes = read_processes(include_arguments=True)
    children: dict[int, list[dict]] = defaultdict(list)
    for process in processes:
        children[process["ppid"]].append(process)
    stack = list(children.get(pid, []))
    while stack:
        process = stack.pop()
        lowered = process.get("arguments", "").lower()
        marker = next((item for item in PROTECTED_MARKERS if item in lowered), None)
        if process["family"] in {"agent", "terminal-manager"}:
            return process["family"]
        if marker:
            return marker
        stack.extend(children.get(process["pid"], []))
    return None


def build_process_inspection(pid: int) -> dict:
    identity = process_identity(pid)
    identity["protected_descendant"] = protected_descendant_marker(pid)
    if identity["state"].startswith("Z"):
        recommendation = (
            "Inspect the parent reaping bug; signaling a zombie reclaims no RAM."
        )
    elif identity["family"] in {"agent", "terminal-manager"}:
        recommendation = (
            "Inspect the owning cmux session and use its restorable hibernation flow."
        )
    elif identity["family"] in {"gui-app", "browser"}:
        recommendation = (
            "Review unsaved state and use the application's ordinary Quit behavior."
        )
    elif identity["family"] == "developer-runtime":
        recommendation = (
            "Watch under a comparable workload, identify the owning project/session and recovery "
            "command, then request approval for a separate exact action."
        )
    else:
        recommendation = (
            "Identify the owner and native lifecycle before proposing any action."
        )
    return {
        "read_only": True,
        "mutations_performed": False,
        "automatic_termination_supported": False,
        "reason": "Generic PID termination cannot prove that work is unused or restorable.",
        "identity": identity,
        "estimated_physical_footprint_bytes": read_process_footprint(pid),
        "estimate_is_guaranteed_reclaim": False,
        "recommendation": recommendation,
    }


def stable_identity(identity: dict) -> dict:
    return {
        key: identity[key]
        for key in ("pid", "uid", "started", "command", "arguments_sha256", "cwd")
    }


def watch_processes(pids: list[int], samples: int, interval: float) -> dict:
    identities = {pid: stable_identity(process_identity(pid)) for pid in pids}
    series = []
    for sample_index in range(samples):
        visible = {process["pid"]: process for process in read_processes()}
        readings = []
        for pid in pids:
            process = visible.get(pid)
            readings.append(
                {
                    "pid": pid,
                    "exited": process is None,
                    "rss_bytes": process["rss_bytes"] if process else None,
                    "physical_footprint_bytes": (
                        read_process_footprint(pid) if process else None
                    ),
                }
            )
        series.append(
            {
                "sample": sample_index + 1,
                "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "processes": readings,
            }
        )
        if sample_index + 1 < samples:
            time.sleep(interval)

    for pid, original in identities.items():
        try:
            current = stable_identity(process_identity(pid))
        except (OSError, RuntimeError, ValueError):
            continue
        if current != original:
            raise ValueError(f"Process {pid} changed generation during observation")

    trends = []
    for pid in pids:
        readings = [
            next(row for row in sample["processes"] if row["pid"] == pid)
            for sample in series
        ]
        first = readings[0]["physical_footprint_bytes"] or readings[0]["rss_bytes"]
        last = readings[-1]["physical_footprint_bytes"] or readings[-1]["rss_bytes"]
        trends.append(
            {
                "pid": pid,
                "identity": identities[pid],
                "first_bytes": first,
                "last_bytes": last,
                "delta_bytes": last - first
                if first is not None and last is not None
                else None,
                "interpretation": "trend only; this is not proof of a memory leak",
            }
        )
    return {
        "read_only": True,
        "samples": samples,
        "interval_seconds": interval,
        "series": series,
        "trends": trends,
    }


def render_watch(report: dict) -> None:
    print("SAFE MEMORY WATCH - read only")
    print(
        f"{report['samples']} samples at {report['interval_seconds']:.1f}s intervals; "
        "growth is not proof of a leak"
    )
    for trend in report["trends"]:
        delta = trend["delta_bytes"]
        delta_label = "unknown" if delta is None else f"{delta / 1024 / 1024:+.1f} MiB"
        print(
            f"  pid={trend['pid']} {trend['identity']['command']}: "
            f"{format_bytes(trend['first_bytes'] or 0)} -> "
            f"{format_bytes(trend['last_bytes'] or 0)} ({delta_label})"
        )


def write_json_exclusive(path: str, value: dict) -> None:
    output = Path(path).expanduser()
    try:
        with output.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
    except FileExistsError as error:
        raise ValueError(f"Refusing to overwrite existing file: {output}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--top", type=int, default=20)
    snapshot_parser.add_argument("--include-arguments", action="store_true")
    snapshot_parser.add_argument("--json-out")
    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--pid", type=int, action="append", required=True)
    watch_parser.add_argument("--samples", type=int, default=3)
    watch_parser.add_argument("--interval", type=float, default=2.0)
    watch_parser.add_argument("--json-out")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args()

    try:
        if args.mode == "snapshot":
            if args.top < 1:
                parser.error("--top must be at least 1")
            report = build_snapshot(args.top, args.include_arguments)
            render_snapshot(report)
            if args.json_out:
                write_json_exclusive(args.json_out, report)
                print(f"Full snapshot written to {Path(args.json_out).expanduser()}")
            return 0
        if args.mode == "watch":
            pids = sorted(set(args.pid))
            if not 3 <= args.samples <= 20:
                parser.error("--samples must be between 3 and 20")
            if not 0.5 <= args.interval <= 10:
                parser.error("--interval must be between 0.5 and 10 seconds")
            if len(pids) > 10 or (args.samples - 1) * args.interval > 60:
                parser.error("watch is limited to 10 PIDs and 60 seconds")
            report = watch_processes(pids, args.samples, args.interval)
            render_watch(report)
            if args.json_out:
                write_json_exclusive(args.json_out, report)
                print(f"Full series written to {Path(args.json_out).expanduser()}")
            return 0
        if args.mode == "inspect":
            print(json.dumps(build_process_inspection(args.pid), indent=2))
            return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

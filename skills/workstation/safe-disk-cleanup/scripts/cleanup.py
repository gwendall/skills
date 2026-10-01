#!/usr/bin/env python3
"""Inspect, plan, or execute allowlisted developer-cache cleanup actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

CONFIRM_PREFIX = "disk-cleanup-v2"


@dataclass(frozen=True)
class Action:
    id: str
    description: str
    impact: str
    paths: tuple[str, ...]


ACTIONS = {
    "expo-cache": Action(
        "expo-cache",
        "Remove downloaded Expo Go and iOS simulator app caches.",
        "Expo will download these apps again when needed.",
        (".expo/expo-go", ".expo/ios-simulator-app-cache"),
    ),
    "npm-cache": Action(
        "npm-cache",
        "Clean npm's content cache and temporary npx installs.",
        "npm/npx will download packages again when needed.",
        (".npm/_npx", ".npm/_cacache"),
    ),
    "playwright-cache": Action(
        "playwright-cache",
        "Remove downloaded Playwright browser binaries.",
        "Playwright will download browsers again before tests can run.",
        ("Library/Caches/ms-playwright", ".cache/ms-playwright"),
    ),
    "pnpm-metadata-cache": Action(
        "pnpm-metadata-cache",
        "Remove pnpm's metadata cache.",
        "pnpm may download metadata again.",
        ("Library/Caches/pnpm",),
    ),
    "bun-cache": Action(
        "bun-cache",
        "Remove Bun's download cache.",
        "Bun may download packages again.",
        ("Library/Caches/bun",),
    ),
    "homebrew-cache": Action(
        "homebrew-cache",
        "Remove Homebrew's download cache.",
        "Homebrew may download bottles and metadata again.",
        ("Library/Caches/Homebrew",),
    ),
}

ACTION_PROCESS_PATTERNS = {
    "expo-cache": (r"(^|[/\s])expo(?:\s|$)",),
    "npm-cache": (r"(^|[/\s])(?:npm|npx)(?:\s|$)",),
    "playwright-cache": (r"playwright", r"ms-playwright", r"chrome-headless"),
    "pnpm-metadata-cache": (r"(^|[/\s])pnpm(?:\s|$)",),
    "bun-cache": (r"(^|[/\s])bun(?:\s|$)",),
    "homebrew-cache": (r"(^|[/\s])brew(?:\s|$)",),
}


def get_home() -> Path:
    return Path.home().resolve()


def select_actions(ids: list[str]) -> list[Action]:
    unknown = sorted(set(ids) - ACTIONS.keys())
    if unknown:
        raise ValueError("Unknown action id(s): " + ", ".join(unknown))
    if not ids:
        raise ValueError("Select at least one --id")
    return [ACTIONS[action_id] for action_id in sorted(set(ids))]


def read_processes() -> list[dict]:
    """Return enough process metadata to fail closed without exposing arguments."""
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,args="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Unable to inspect active processes: {error}") from error
    if result.returncode != 0:
        raise ValueError("Unable to inspect active processes before cleanup")

    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        rows.append(
            {
                "pid": pid,
                "ppid": ppid,
                "executable": Path(parts[2].split(None, 1)[0]).name,
                "arguments": parts[2],
            }
        )
    return rows


def activity_conflicts(actions: list[Action], processes: list[dict]) -> list[dict]:
    by_pid = {process["pid"]: process for process in processes}
    ignored = {os.getpid()}
    current = os.getppid()
    while current in by_pid and current not in ignored:
        ignored.add(current)
        current = by_pid[current]["ppid"]

    conflicts = []
    for action in actions:
        patterns = ACTION_PROCESS_PATTERNS[action.id]
        for process in processes:
            if process["pid"] in ignored:
                continue
            lowered = process["arguments"].lower()
            marker = next(
                (pattern for pattern in patterns if re.search(pattern, lowered)), None
            )
            if marker:
                conflicts.append(
                    {
                        "action_id": action.id,
                        "pid": process["pid"],
                        "executable": process["executable"],
                        "matched_activity": marker,
                    }
                )
    return conflicts


def expected_paths(action: Action, home: Path) -> list[Path]:
    return [(home / relative).absolute() for relative in action.paths]


def validate_target(path: Path, home: Path) -> tuple[Path, tuple[int, int]] | None:
    """Validate an allowlisted target and capture identity before deletion."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"Refusing symlink target: {path}")
    if path == home or home not in path.parents:
        raise ValueError(f"Refusing target outside the home directory: {path}")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise ValueError(
            f"Refusing path whose resolved target changed: {path} -> {resolved}"
        )
    return resolved, (metadata.st_dev, metadata.st_ino)


def entry_kind(metadata: os.stat_result) -> str:
    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    if stat.S_ISLNK(metadata.st_mode):
        return "symlink"
    if stat.S_ISREG(metadata.st_mode):
        return "file"
    return "other"


def snapshot_target(
    path: Path,
    home: Path,
    include_entries: bool = False,
    seen_inodes: set[tuple[int, int]] | None = None,
) -> dict:
    validation = validate_target(path, home)
    if validation is None:
        return {
            "path": str(path),
            "exists": False,
            "identity": None,
            "manifest_digest": None,
            "entry_count": 0,
            "allocated_bytes": 0,
            "entries": [],
        }

    resolved, identity = validation
    digest = hashlib.sha256()
    allocated_bytes = 0
    entries = []
    allocated_inodes = seen_inodes if seen_inodes is not None else set()
    stack = [resolved]
    entry_count = 0

    try:
        while stack:
            current = stack.pop()
            metadata = current.lstat()
            relative = (
                "." if current == resolved else current.relative_to(resolved).as_posix()
            )
            kind = entry_kind(metadata)
            identity_key = (metadata.st_dev, metadata.st_ino)
            record = {
                "path": relative,
                "full_path": str(current),
                "kind": kind,
                "allocated_bytes": metadata.st_blocks * 512,
                "apparent_bytes": metadata.st_size,
            }
            digest.update(
                json.dumps(
                    {
                        **record,
                        "device": metadata.st_dev,
                        "inode": metadata.st_ino,
                        "mode": metadata.st_mode,
                        "modified_ns": metadata.st_mtime_ns,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            )
            if identity_key not in allocated_inodes:
                allocated_inodes.add(identity_key)
                allocated_bytes += record["allocated_bytes"]
            if current != resolved:
                entry_count += 1
                if include_entries:
                    entries.append(record)
            if kind == "directory":
                with os.scandir(current) as iterator:
                    children = sorted(
                        (Path(item.path) for item in iterator),
                        key=lambda child: child.name,
                        reverse=True,
                    )
                stack.extend(children)
    except OSError as error:
        raise ValueError(f"Unable to fully enumerate {path}: {error}") from error

    final = validate_target(path, home)
    if final is None or final[1] != identity:
        raise ValueError(f"Target changed during dry-run: {path}")
    return {
        "path": str(path),
        "exists": True,
        "identity": list(identity),
        "manifest_digest": digest.hexdigest(),
        "entry_count": entry_count,
        "allocated_bytes": allocated_bytes,
        "entries": entries,
    }


def collect_snapshots(
    actions: list[Action], home: Path, include_entries: bool = False
) -> dict[str, dict]:
    snapshots = {}
    seen_inodes: set[tuple[int, int]] = set()
    for action in actions:
        for path in expected_paths(action, home):
            snapshots[str(path)] = snapshot_target(
                path, home, include_entries, seen_inodes
            )
    return snapshots


def token_from_snapshots(
    actions: list[Action], home: Path, snapshots: dict[str, dict]
) -> str:
    targets = [
        {
            "path": snapshot["path"],
            "identity": snapshot["identity"],
            "manifest_digest": snapshot["manifest_digest"],
        }
        for snapshot in snapshots.values()
    ]
    material = {
        "prefix": CONFIRM_PREFIX,
        "home": str(home),
        "actions": [action.id for action in actions],
        "targets": targets,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def plan_token(actions: list[Action], home: Path) -> str:
    snapshots = collect_snapshots(actions, home)
    return token_from_snapshots(actions, home, snapshots)


def build_plan(
    actions: list[Action],
    home: Path,
    include_entries: bool = False,
    processes: list[dict] | None = None,
) -> dict:
    snapshots = collect_snapshots(actions, home, include_entries)
    rows = []
    for action in actions:
        paths = expected_paths(action, home)
        roots = [snapshots[str(path)] for path in paths]
        rows.append(
            {
                "id": action.id,
                "description": action.description,
                "impact": action.impact,
                "reversible": False,
                "paths": [str(path) for path in paths],
                "entry_count": sum(root["entry_count"] for root in roots),
                "allocated_bytes": sum(root["allocated_bytes"] for root in roots),
                "roots": roots,
            }
        )
    conflicts = activity_conflicts(
        actions, read_processes() if processes is None else processes
    )
    return {
        "dry_run": True,
        "cleanup_mutations_performed": False,
        "execution_blocked_by_activity": bool(conflicts),
        "activity_conflicts": conflicts,
        "actions": rows,
        "total_entry_count": sum(row["entry_count"] for row in rows),
        "total_allocated_bytes": sum(row["allocated_bytes"] for row in rows),
        "confirmation_token": token_from_snapshots(actions, home, snapshots),
    }


def format_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return "unknown"


def render_dry_run(plan: dict, top_files: int, all_files: bool) -> None:
    print("DRY RUN - no cache files were changed")
    print(
        f"Estimated physical reclaim: {format_size(plan['total_allocated_bytes'])} "
        f"across {plan['total_entry_count']:,} entries"
    )
    for action in plan["actions"]:
        print(
            f"\n{action['id']}: {format_size(action['allocated_bytes'])}, "
            f"{action['entry_count']:,} entries"
        )
        print(f"  Impact: {action['impact']}")
        for root in action["roots"]:
            state = (
                "missing"
                if not root["exists"]
                else format_size(root["allocated_bytes"])
            )
            print(f"  Root: {root['path']} ({state})")

        entries = [entry for root in action["roots"] for entry in root["entries"]]
        entries.sort(key=lambda entry: entry["allocated_bytes"], reverse=True)
        shown = entries if all_files else entries[:top_files]
        if shown:
            label = "All entries" if all_files else f"Largest {len(shown)} entries"
            print(f"  {label}:")
            for entry in shown:
                print(
                    f"    {format_size(entry['allocated_bytes']):>10}  "
                    f"{entry['kind']:9}  {entry['full_path']}"
                )
        if not all_files and len(entries) > len(shown):
            print(
                f"  … {len(entries) - len(shown):,} more entries; use --all-files or --json-out"
            )
    print("\nNothing above is reversible; every target is a regenerable cache.")
    if plan["activity_conflicts"]:
        print("Execution is blocked while matching tools are active:")
        for conflict in plan["activity_conflicts"]:
            print(
                f"  {conflict['action_id']}: pid={conflict['pid']} "
                f"{conflict['executable']}"
            )
    print(f"Confirmation token for this exact manifest: {plan['confirmation_token']}")


def delete_validated(path: Path, home: Path, identity: tuple[int, int]) -> None:
    metadata = path.lstat()
    if (metadata.st_dev, metadata.st_ino) != identity or stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"Target changed after validation: {path}")
    if path.resolve(strict=True) != path or path == home or home not in path.parents:
        raise ValueError(f"Target escaped its allowlisted location: {path}")
    if stat.S_ISDIR(metadata.st_mode):
        shutil.rmtree(path)
    else:
        path.unlink()


def execute(
    actions: list[Action], home: Path, processes: list[dict] | None = None
) -> list[dict]:
    conflicts = activity_conflicts(
        actions, read_processes() if processes is None else processes
    )
    if conflicts:
        summary = ", ".join(f"{row['action_id']} pid={row['pid']}" for row in conflicts)
        raise ValueError(f"Selected tools are active: {summary}")

    validated_actions = []
    for action in actions:
        validations = []
        for path in expected_paths(action, home):
            validation = validate_target(path, home)
            if validation:
                validations.append(validation)
        validated_actions.append((action, validations))

    results = []
    for action, validations in validated_actions:
        row = {"id": action.id, "status": "ok", "deleted_paths": [], "errors": []}
        for path, identity in validations:
            try:
                delete_validated(path, home, identity)
                row["deleted_paths"].append(str(path))
            except (OSError, ValueError) as error:
                row["status"] = "failed"
                row["errors"].append(str(error))
                results.append(row)
                return results
        results.append(row)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("list")
    plan_parser = subparsers.add_parser("plan")
    dry_run_parser = subparsers.add_parser("dry-run")
    execute_parser = subparsers.add_parser("execute")
    for child in (plan_parser, dry_run_parser, execute_parser):
        child.add_argument("--id", action="append", default=[])
    dry_run_parser.add_argument("--top-files", type=int, default=20)
    dry_run_parser.add_argument("--all-files", action="store_true")
    dry_run_parser.add_argument("--json-out")
    execute_parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if args.mode == "list":
        for action in ACTIONS.values():
            print(f"{action.id}: {action.description} Impact: {action.impact}")
        return 0

    try:
        actions = select_actions(args.id)
    except ValueError as error:
        parser.error(str(error))
    home = get_home()
    try:
        plan = build_plan(actions, home, include_entries=args.mode == "dry-run")
    except ValueError as error:
        parser.error(str(error))
    if args.mode == "plan":
        print(json.dumps(plan, indent=2))
        return 0
    if args.mode == "dry-run":
        if args.top_files < 0:
            parser.error("--top-files must be zero or greater")
        render_dry_run(plan, args.top_files, args.all_files)
        if args.json_out:
            output = Path(args.json_out).expanduser()
            try:
                with output.open("x", encoding="utf-8") as handle:
                    json.dump(plan, handle, indent=2)
                    handle.write("\n")
            except FileExistsError:
                parser.error(f"refusing to overwrite existing file: {output}")
            print(f"Full manifest written to {output}")
        return 0

    if args.confirm != plan["confirmation_token"]:
        print("Refusing execution: confirmation token does not match this exact plan.")
        return 2
    if plan["activity_conflicts"]:
        print(
            json.dumps(
                {
                    "error": "Refusing execution while selected tools are active",
                    "activity_conflicts": plan["activity_conflicts"],
                    "results": [],
                },
                indent=2,
            )
        )
        return 2
    before = shutil.disk_usage(home).free
    try:
        results = execute(actions, home)
    except (OSError, ValueError) as error:
        after = shutil.disk_usage(home).free
        print(
            json.dumps(
                {
                    "before_free": before,
                    "after_free": after,
                    "error": str(error),
                    "results": [],
                },
                indent=2,
            )
        )
        return 2
    after = shutil.disk_usage(home).free
    print(
        json.dumps(
            {"before_free": before, "after_free": after, "results": results}, indent=2
        )
    )
    return 1 if any(row["status"] != "ok" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

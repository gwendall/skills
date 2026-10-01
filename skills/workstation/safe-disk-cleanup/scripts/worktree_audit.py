#!/usr/bin/env python3
"""Audit Git worktrees without removing or modifying them."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )


def parse_worktree_porcelain(output: str) -> list[dict]:
    rows = []
    for block in output.strip().split("\n\n"):
        row = {"locked": False, "prunable": False}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            if key in {"locked", "prunable"}:
                row[key] = True
                row[f"{key}_reason"] = value
            else:
                row[key] = value
        if row.get("worktree"):
            rows.append(row)
    return rows


def process_references() -> list[tuple[int, str]]:
    references = []
    try:
        cwd_output = run(["lsof", "-Fn", "-d", "cwd"]).stdout
    except (OSError, subprocess.TimeoutExpired):
        cwd_output = ""
    current_pid = None
    for line in cwd_output.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current_pid = int(line[1:])
        elif line.startswith("n") and current_pid is not None:
            references.append((current_pid, line[1:]))

    try:
        process_output = run(["ps", "-axo", "pid=,args="], timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        process_output = ""
    for line in process_output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            references.append((int(parts[0]), parts[1]))
    return references


def allocated_size(path: str) -> int | None:
    try:
        result = run(["du", "-sk", path], timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.split()[0]) * 1024
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def decide_worktree(facts: dict, main_worktree: str) -> dict:
    evidence = []
    blockers = []
    if os.path.realpath(facts["path"]) == os.path.realpath(main_worktree):
        return {
            "decision": "protected",
            "preconditions_met": False,
            "safe_to_remove_now": False,
            "owner_approval_required": True,
            "evidence": ["main worktree"],
            "blockers": ["Git does not allow removal of the main worktree"],
            "recovery": "not applicable",
            "estimated_reclaim_bytes": None,
        }
    if facts["prunable"] and not facts["exists"]:
        return {
            "decision": "metadata-prune-only",
            "preconditions_met": True,
            "safe_to_remove_now": False,
            "owner_approval_required": True,
            "evidence": ["worktree directory is already missing"],
            "blockers": [],
            "recovery": "Only stale Git administrative metadata would be removed.",
            "estimated_reclaim_bytes": 0,
        }
    if not facts["exists"]:
        blockers.append("worktree path is missing but Git did not mark it prunable")
    if facts["locked"]:
        blockers.append("worktree is explicitly locked")
    if facts["active_pids"]:
        blockers.append("one or more live processes reference this worktree")
    if not facts["clean"]:
        blockers.append("tracked or untracked changes are present, or status failed")
    if facts["has_gitmodules"]:
        blockers.append("repository declares submodules; removal needs separate review")
    if facts["ahead_of_upstream"] is not None and facts["ahead_of_upstream"] > 0:
        blockers.append("HEAD contains commits not present on its upstream")
    if facts["branch"] == "detached" and not facts["merged_into_main_ref"]:
        blockers.append("detached HEAD is not reachable from the selected main ref")
    if (
        facts["branch"] != "detached"
        and not facts["merged_into_main_ref"]
        and facts["upstream"] is None
    ):
        blockers.append("unmerged branch has no verified upstream recovery ref")

    if facts["merged_into_main_ref"]:
        evidence.append("exact HEAD is reachable from the selected main ref")
        recovery = f"Recreate from {facts['main_ref']} or exact HEAD {facts['head']}."
    elif facts["upstream"] and facts["ahead_of_upstream"] == 0:
        evidence.append(f"exact HEAD is recoverable from upstream {facts['upstream']}")
        recovery = f"Recreate from {facts['upstream']} or exact HEAD {facts['head']}."
    else:
        recovery = "No complete remote or main-ref recovery proof was established."
    if facts["clean"]:
        evidence.append("Git status is clean, including untracked files")
    if not facts["active_pids"]:
        evidence.append("no current process CWD or arguments reference the path")
    if not facts["locked"]:
        evidence.append("worktree is not locked")

    return {
        "decision": "blocked" if blockers else "review-ready",
        "preconditions_met": not blockers,
        "safe_to_remove_now": False,
        "owner_approval_required": True,
        "evidence": evidence,
        "blockers": blockers,
        "recovery": recovery,
        "estimated_reclaim_bytes": None,
    }


def audit_one(
    repo: str,
    main_ref: str,
    main_worktree: str,
    row: dict,
    references: list[tuple[int, str]],
) -> dict:
    path = row["worktree"]
    exists = os.path.isdir(path)
    prefix = path + os.sep
    active_pids = sorted(
        {
            pid
            for pid, value in references
            if value == path or value.startswith(prefix) or prefix in value
        }
    )
    clean = False
    changed_entry_count = None
    if exists:
        try:
            status = run(
                ["git", "-C", path, "status", "--porcelain", "--untracked-files=all"]
            )
            if status.returncode == 0:
                changed_entry_count = len(status.stdout.splitlines())
                clean = changed_entry_count == 0
        except (OSError, subprocess.TimeoutExpired):
            pass

    merged = False
    try:
        merged = (
            run(
                [
                    "git",
                    "-C",
                    repo,
                    "merge-base",
                    "--is-ancestor",
                    row["HEAD"],
                    main_ref,
                ]
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        pass

    timestamp = ""
    try:
        timestamp = run(
            ["git", "-C", repo, "show", "-s", "--format=%ct", row["HEAD"]]
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    commit_time = (
        datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat()
        if timestamp.isdigit()
        else None
    )
    branch = row.get("branch", "detached").removeprefix("refs/heads/")
    upstream = None
    ahead_of_upstream = None
    behind_upstream = None
    if exists and branch != "detached":
        try:
            upstream_result = run(
                [
                    "git",
                    "-C",
                    path,
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                ]
            )
            if upstream_result.returncode == 0:
                upstream = upstream_result.stdout.strip()
                counts = run(
                    [
                        "git",
                        "-C",
                        path,
                        "rev-list",
                        "--left-right",
                        "--count",
                        "HEAD...@{upstream}",
                    ]
                )
                try:
                    ahead_of_upstream, behind_upstream = map(int, counts.stdout.split())
                except ValueError:
                    ahead_of_upstream = behind_upstream = None
        except (OSError, subprocess.TimeoutExpired):
            pass
    facts = {
        "path": path,
        "branch": branch,
        "head": row["HEAD"],
        "main_ref": main_ref,
        "commit_time": commit_time,
        "exists": exists,
        "clean": clean,
        "changed_entry_count": changed_entry_count,
        "merged_into_main_ref": merged,
        "upstream": upstream,
        "ahead_of_upstream": ahead_of_upstream,
        "behind_upstream": behind_upstream,
        "has_gitmodules": exists and (Path(path) / ".gitmodules").exists(),
        "locked": row["locked"],
        "prunable": row["prunable"],
        "active_pids": active_pids,
        "allocated_bytes": None,
    }
    decision = decide_worktree(facts, main_worktree)
    return {
        **facts,
        **decision,
        "review_candidate": decision["decision"] == "review-ready",
    }


def audit_repository(
    repo: Path, main_ref: str, references: list[tuple[int, str]], measure: bool
) -> dict:
    root = str(repo.expanduser().resolve())
    listing = run(["git", "-C", root, "worktree", "list", "--porcelain"])
    if listing.returncode != 0:
        raise ValueError(
            f"Unable to list worktrees for {root}: {listing.stderr.strip()}"
        )
    rows = parse_worktree_porcelain(listing.stdout)
    if not rows:
        raise ValueError(f"Git reported no worktrees for {root}")
    # Git lists the main worktree first even when this audit was invoked through
    # a linked worktree. Never infer the protected main path from --repo.
    main_worktree = rows[0]["worktree"]
    with ThreadPoolExecutor(max_workers=min(12, max(1, len(rows)))) as pool:
        audited = list(
            pool.map(
                lambda row: audit_one(root, main_ref, main_worktree, row, references),
                rows,
            )
        )
    candidates = [row for row in audited if row["review_candidate"]]
    if measure and candidates:
        with ThreadPoolExecutor(max_workers=min(4, len(candidates))) as pool:
            sizes = list(pool.map(lambda row: allocated_size(row["path"]), candidates))
        for row, size in zip(candidates, sizes, strict=True):
            row["allocated_bytes"] = size
            row["estimated_reclaim_bytes"] = size
    if measure:
        candidates.sort(
            key=lambda row: (row["allocated_bytes"] or -1, row["commit_time"] or ""),
            reverse=True,
        )
    else:
        candidates.sort(key=lambda row: row["commit_time"] or "")
    return {
        "repository": root,
        "main_ref": main_ref,
        "main_ref_head": run(["git", "-C", root, "rev-parse", main_ref]).stdout.strip(),
        "total": len(audited),
        "clean": sum(row["clean"] for row in audited),
        "merged_into_main_ref": sum(row["merged_into_main_ref"] for row in audited),
        "active": sum(bool(row["active_pids"]) for row in audited),
        "locked": sum(row["locked"] for row in audited),
        "prunable": sum(row["prunable"] for row in audited),
        "blocked": sum(row["decision"] == "blocked" for row in audited),
        "protected": sum(row["decision"] == "protected" for row in audited),
        "metadata_prune_only": sum(
            row["decision"] == "metadata-prune-only" for row in audited
        ),
        "review_candidate_count": len(candidates),
        "review_candidate_bytes": (
            sum(row["allocated_bytes"] or 0 for row in candidates) if measure else None
        ),
        "review_candidates": candidates,
        "worktrees": audited,
    }


def format_size(value: int | None) -> str:
    if value is None:
        return "not measured"
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
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--measure-sizes", action="store_true")
    parser.add_argument("--show-blocked", action="store_true")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--json-out")
    args = parser.parse_args()
    if not shutil.which("git"):
        parser.error("git is required")
    references = process_references()
    try:
        reports = [
            audit_repository(Path(repo), args.main_ref, references, args.measure_sizes)
            for repo in args.repo
        ]
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        parser.error(str(error))
    report = {
        "read_only": True,
        "removal_supported": False,
        "candidate_is_approval": False,
        "repositories": reports,
    }
    for item in reports:
        measurement = (
            f"{format_size(item['review_candidate_bytes'])} candidate footprint"
            if item["review_candidate_bytes"] is not None
            else "candidate sizes not measured"
        )
        print(
            f"{item['repository']}: {item['total']} worktrees; "
            f"{item['review_candidate_count']} review candidates; "
            f"{item['blocked']} blocked; {item['protected']} protected; "
            f"{item['active']} active; "
            f"{measurement}"
        )
        for candidate in item["review_candidates"][: max(0, args.top)]:
            print(
                f"  {format_size(candidate['allocated_bytes']):>12}  "
                f"{candidate['branch']}  {candidate['path']}"
            )
        if args.show_blocked:
            blocked = [
                row
                for row in item["worktrees"]
                if row["decision"] in {"blocked", "protected"}
            ]
            for row in blocked[: max(0, args.top)]:
                print(f"  {row['decision']:13} {row['branch']}  {row['path']}")
                for blocker in row["blockers"]:
                    print(f"    blocker: {blocker}")
    if args.json_out:
        try:
            write_json_exclusive(Path(args.json_out).expanduser(), report)
        except ValueError as error:
            parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

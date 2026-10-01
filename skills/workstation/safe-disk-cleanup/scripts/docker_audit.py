#!/usr/bin/env python3
"""Explain Docker disk cleanup decisions without pruning anything."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )


def json_lines(output: str) -> list[dict]:
    rows = []
    for line in output.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_size(value: str) -> int | None:
    match = re.search(r"([0-9.]+)\s*([kmgtp]?i?b)", value.lower())
    if not match:
        return None
    amount = float(match.group(1))
    units = {
        "b": 1,
        "kb": 1000,
        "mb": 1000**2,
        "gb": 1000**3,
        "tb": 1000**4,
        "pb": 1000**5,
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
        "tib": 1024**4,
        "pib": 1024**5,
    }
    return int(amount * units[match.group(2)])


def active_build_processes() -> list[dict]:
    result = run(["ps", "-axo", "pid=,args="], timeout=5)
    if result.returncode != 0:
        raise ValueError("Unable to inspect Docker build processes")
    rows = []
    patterns = ("docker build", "docker buildx", "docker compose build", "docker bake")
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        lowered = parts[1].lower()
        marker = next((item for item in patterns if item in lowered), None)
        if marker and "docker_audit.py" not in lowered:
            rows.append({"pid": int(parts[0]), "matched_activity": marker})
    return rows


def decision(
    name: str,
    status: str,
    evidence: list[str],
    blockers: list[str],
    consequence: str,
    recovery: str,
    recommended_action: str | None = None,
    estimated_reclaim_bytes: int | None = None,
) -> dict:
    return {
        "resource": name,
        "decision": status,
        "preconditions_met": status == "review-ready",
        "safe_to_delete_now": False,
        "fresh_approval_required": True,
        "evidence": evidence,
        "blockers": blockers,
        "consequence": consequence,
        "recovery": recovery,
        "estimated_reclaim_bytes": estimated_reclaim_bytes,
        "recommended_action": recommended_action,
    }


def build_report(
    summary: list[dict],
    containers: list[dict],
    images: list[dict],
    volumes: list[dict],
    active_builds: list[dict],
) -> dict:
    by_type = {row["Type"]: row for row in summary}
    resources = []
    build_cache = by_type.get("Build Cache", {})
    reclaimable_cache = parse_size(build_cache.get("Reclaimable", ""))
    resources.append(
        decision(
            "docker-build-cache",
            (
                "blocked"
                if active_builds
                else "review-ready"
                if reclaimable_cache
                else "review"
            ),
            [
                "Docker reports cache records as reclaimable",
                f"reported reclaimable bytes: {reclaimable_cache}",
            ],
            (
                ["Docker build activity is currently visible"]
                if active_builds
                else ["Docker reports no material reclaimable build cache"]
                if not reclaimable_cache
                else []
            ),
            "Future builds may become slower and redownload or rebuild layers.",
            "Build inputs can recreate cache records.",
            (
                'docker buildx prune --filter "until=24h"'
                if reclaimable_cache and not active_builds
                else None
            ),
            reclaimable_cache,
        )
    )

    for container in containers:
        running = container.get("State") == "running"
        inspect_mounts = container.get("InspectMounts") or []
        has_mounts = bool(container.get("Mounts") or inspect_mounts)
        restart_policy = container.get("RestartPolicy") or "no"
        compose_project = container.get("ComposeProject")
        blockers = []
        if running:
            blockers.append("container is running")
        if has_mounts:
            blockers.append("container references one or more mounts or volumes")
        if restart_policy != "no":
            blockers.append(f"container has restart policy {restart_policy}")
        if compose_project:
            blockers.append(
                f"container belongs to Compose project {compose_project}; use project lifecycle review"
            )
        status = "blocked" if blockers else "review-ready"
        resources.append(
            decision(
                f"container:{container.get('Names') or container.get('ID')}",
                status,
                [
                    f"state: {container.get('State', 'unknown')}",
                    f"writable size: {container.get('Size', 'unknown')}",
                    f"restart policy: {restart_policy}",
                ],
                blockers,
                "Removing a container destroys its writable layer, logs, and metadata.",
                "The container can be recreated only from its image and recorded configuration.",
                f"docker container rm {container.get('ID')}" if not blockers else None,
                parse_size(container.get("Size", "")),
            )
        )

    for image in images:
        try:
            containers_count = int(image.get("Containers", "0") or 0)
        except ValueError:
            containers_count = 0
        blockers = []
        if containers_count:
            blockers.append("one or more containers reference this image")
        else:
            blockers.append(
                "inventory does not prove a registry or reproducible-build recovery path"
            )
        resources.append(
            decision(
                f"image:{image.get('Repository')}:{image.get('Tag')}",
                "blocked" if containers_count else "review",
                [
                    f"container references: {containers_count}",
                    f"created: {image.get('CreatedAt', 'unknown')}",
                    f"size: {image.get('Size', 'unknown')}",
                ],
                blockers,
                "Removal may require a registry download or a local rebuild.",
                "Recovery requires a verified registry digest or reproducible build source.",
                None,
                None,
            )
        )

    for volume in volumes:
        resources.append(
            decision(
                f"volume:{volume.get('Name')}",
                "protected",
                [f"driver: {volume.get('Driver', 'unknown')}"],
                ["volumes may contain the only copy of stateful data"],
                "Volume removal permanently deletes stored data.",
                "No recovery path is assumed without a verified backup or replica.",
            )
        )

    resources.append(
        decision(
            "docker-raw-vm-disk",
            "protected",
            ["sparse VM disk is Docker Desktop's storage backend"],
            ["allocated file size does not identify independently removable content"],
            "Direct deletion can destroy all local Docker state.",
            "Use Docker's resource-specific lifecycle commands instead.",
        )
    )
    return {
        "read_only": True,
        "prune_performed": False,
        "safe_to_delete_means_without_fresh_approval": False,
        "active_build_processes": active_builds,
        "summary": summary,
        "resources": resources,
    }


def collect_report() -> dict:
    commands = {
        "summary": ["docker", "system", "df", "--format", "json"],
        "containers": ["docker", "ps", "-a", "--size", "--format", "json"],
        "images": ["docker", "image", "ls", "-a", "--digests", "--format", "json"],
        "volumes": ["docker", "volume", "ls", "--format", "json"],
    }
    outputs = {}
    for name, command in commands.items():
        result = run(command)
        if result.returncode != 0:
            raise ValueError(f"{' '.join(command)} failed: {result.stderr.strip()}")
        outputs[name] = json_lines(result.stdout)
    container_ids = [row.get("ID") for row in outputs["containers"] if row.get("ID")]
    inspections = {}
    if container_ids:
        inspect_result = run(
            ["docker", "inspect", "--type", "container", *container_ids]
        )
        if inspect_result.returncode != 0:
            raise ValueError(f"docker inspect failed: {inspect_result.stderr.strip()}")
        for item in json.loads(inspect_result.stdout):
            inspections[item.get("Id", "")[:12]] = item
    for container in outputs["containers"]:
        inspected = inspections.get(container.get("ID", "")[:12], {})
        labels = (inspected.get("Config") or {}).get("Labels") or {}
        restart = (inspected.get("HostConfig") or {}).get("RestartPolicy") or {}
        container["InspectMounts"] = inspected.get("Mounts") or []
        container["RestartPolicy"] = restart.get("Name") or "no"
        container["ComposeProject"] = labels.get("com.docker.compose.project")
    return build_report(
        outputs["summary"],
        outputs["containers"],
        outputs["images"],
        outputs["volumes"],
        active_build_processes(),
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
    if not shutil.which("docker"):
        parser.error("docker is required")
    try:
        report = collect_report()
    except (
        json.JSONDecodeError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as error:
        parser.error(str(error))
    print("DOCKER DECISION AUDIT - read only")
    for resource in report["resources"]:
        print(f"  {resource['decision']:12} {resource['resource']}")
        for blocker in resource["blockers"]:
            print(f"    blocker: {blocker}")
        if resource["recommended_action"]:
            print(f"    after fresh approval: {resource['recommended_action']}")
    if args.json_out:
        try:
            write_json_exclusive(Path(args.json_out).expanduser(), report)
        except ValueError as error:
            parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Aggregate Claude Code token consumption from local session logs.

Reads every *.jsonl under ~/.claude/projects (or --root), deduplicates
messages that are repeated across resumed/forked sessions, and reports
token usage per model over 24h / 7d / 30d / all-time windows, plus a
breakdown by token type and by project.

No dependencies beyond the Python 3 standard library. Read-only.
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOKEN_KEYS = ("input", "output", "cache_read", "cache_create")
WINDOWS = ("24h", "7d", "30d", "all")


def empty_bucket():
    return {w: dict.fromkeys(TOKEN_KEYS, 0) for w in WINDOWS}


def total(d):
    return sum(d[k] for k in TOKEN_KEYS)


def fmt(n):
    if n >= 1e9:
        return f"{n / 1e9:.1f}B"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}K"
    return str(n)


def scan(root):
    now = datetime.now(timezone.utc)
    cutoffs = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
    }
    by_model = defaultdict(empty_bucket)
    by_project = defaultdict(empty_bucket)
    seen = set()
    counted = dupes = 0

    for path in sorted(root.rglob("*.jsonl")):
        project = path.relative_to(root).parts[0] if path.parent != root else "(root)"
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                # Cheap pre-filter: only assistant messages carry usage.
                if '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                model = msg.get("model")
                if not isinstance(usage, dict) or not model or model == "<synthetic>":
                    continue
                # The same API response reappears in resumed/forked session
                # files; (message id, request id) identifies it uniquely.
                mid, rid = msg.get("id"), rec.get("requestId")
                if mid and rid:
                    if (mid, rid) in seen:
                        dupes += 1
                        continue
                    seen.add((mid, rid))
                dt = None
                ts = rec.get("timestamp")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                windows = ["all"] + [w for w, cut in cutoffs.items() if dt and dt >= cut]
                vals = {
                    "input": usage.get("input_tokens") or 0,
                    "output": usage.get("output_tokens") or 0,
                    "cache_read": usage.get("cache_read_input_tokens") or 0,
                    "cache_create": usage.get("cache_creation_input_tokens") or 0,
                }
                counted += 1
                for w in windows:
                    for k, v in vals.items():
                        by_model[model][w][k] += v
                        by_project[project][w][k] += v
    return by_model, by_project, counted, dupes


def aggregate(buckets):
    agg = empty_bucket()
    for bucket in buckets.values():
        for w in WINDOWS:
            for k in TOKEN_KEYS:
                agg[w][k] += bucket[w][k]
    return agg


def print_table(title, rows, agg, first_col):
    print(f"\n{title}")
    print(f"{first_col:<40}{'24H':>10}{'7D':>10}{'30D':>10}{'ALL TIME':>12}")
    for name, bucket in rows:
        cells = "".join(
            f"{fmt(total(bucket[w])):>{12 if w == 'all' else 10}}" for w in WINDOWS
        )
        print(f"{name[:39]:<40}{cells}")
    print("-" * 82)
    cells = "".join(
        f"{fmt(total(agg[w])):>{12 if w == 'all' else 10}}" for w in WINDOWS
    )
    print(f"{'total':<40}{cells}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        type=Path,
        default=Path.home() / ".claude" / "projects",
        help="log directory to scan (default: ~/.claude/projects)",
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--top-projects", type=int, default=10, help="projects to show (default 10)"
    )
    args = ap.parse_args()

    if not args.root.is_dir():
        sys.exit(f"log directory not found: {args.root}")

    by_model, by_project, counted, dupes = scan(args.root)
    agg = aggregate(by_model)
    models = sorted(by_model, key=lambda m: -total(by_model[m]["all"]))
    projects = sorted(by_project, key=lambda p: -total(by_project[p]["all"]))

    if args.json:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "root": str(args.root),
                "messages_counted": counted,
                "duplicates_skipped": dupes,
                "by_model": {m: by_model[m] for m in models},
                "by_project": {p: by_project[p] for p in projects},
                "total": agg,
            },
            sys.stdout,
            indent=2,
        )
        print()
        return

    print_table(
        "Token spend by model", [(m, by_model[m]) for m in models], agg, "MODEL"
    )
    print_table(
        f"Top {args.top_projects} projects",
        [(p, by_project[p]) for p in projects[: args.top_projects]],
        agg,
        "PROJECT",
    )
    print("\nBy token type (all models)")
    print(f"{'TYPE':<40}{'24H':>10}{'7D':>10}{'30D':>10}{'ALL TIME':>12}")
    for k in TOKEN_KEYS:
        cells = "".join(
            f"{fmt(agg[w][k]):>{12 if w == 'all' else 10}}" for w in WINDOWS
        )
        print(f"{k:<40}{cells}")
    print(f"\n{counted} messages counted, {dupes} duplicates skipped.")


if __name__ == "__main__":
    main()

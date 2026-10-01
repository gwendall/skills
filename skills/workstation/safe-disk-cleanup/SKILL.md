---
name: safe-disk-cleanup
description: Safely diagnose and reclaim disk space on developer machines with explainable deletion decisions, deep read-only inventory, worktree and Docker auditing, active-tool guards, and file-level dry-runs. Use when a disk is full, storage is low, developer resources are large, or the user asks what can be deleted. Cleanup requires a reviewed plan and fresh approval.
metadata: {"version":"1.3.0","updated":"2026-09-08","openclaw":{"requires":{"bins":["python3"]},"emoji":"broom"}}
---

# Safe developer disk cleanup

Find the real space consumers, reclaim only what the user approves, and preserve
data that cannot be recreated. Prefer precise native cleanup commands over broad
recursive deletion.

## Safety contract

- Discovery is always read-only. A request such as "find space" or "clean my
  disk" authorizes inspection, not an unreviewed deletion pass.
- Immediately before cleanup, show an exact plan with each action, measured
  size, regeneration cost, and whether the action is reversible. Obtain fresh
  approval for those actions.
- Never automatically delete personal files, Downloads, Documents, photos,
  device backups, Xcode archives, simulator device state, Docker volumes,
  browser profiles, editor databases, credentials, project source, untracked
  files, Git worktrees, or another agent's files.
- Never use `sudo`, empty the Trash, delete an entire package store, or accept a
  user-controlled path in a deletion command.
- Treat package caches, downloaded browsers, and build outputs as rebuildable,
  not free: report the likely download/build cost.
- Resolve every target, reject symlinks and path changes, and stop on validation
  errors. Do not turn a partial failure into a broader cleanup.
- Preserve repository policies. In particular, do not delete worktrees or their
  `node_modules`; report them to the owner for lifecycle cleanup.

Read [references/decision-rules.md](references/decision-rules.md) whenever the
user asks whether a material finding is actually removable. Return a decision,
evidence, blockers, consequence, recovery path, and exact owner-native next
step. Never turn age or size into deletion proof.

## Inventory

Run the bundled read-only inventory first:

```bash
python3 scripts/inventory.py --code-root "$HOME/Code" --top 40
```

Use `--json-out /tmp/disk-inventory.json` when structured output is useful. The
script reports allocated bytes rather than only apparent file length, so sparse
VM images such as `Docker.raw` are not reported at their virtual maximum size.
It places findings into four risk levels:

- `cache`: disposable application cache;
- `rebuildable`: safe to recreate, but may cost bandwidth or build time;
- `review`: state or project material that requires a separate decision;
- `protected`: user data that this skill must not delete.

Confirm important findings with platform-native read-only commands (`df`, `du`,
`pnpm store path`, `docker system df`, `xcrun simctl list`) before recommending
an action. A partial or timed-out scan is evidence only for what it observed.

When the bounded inventory is partial or does not explain most used space, run
the one-pass deep inventory. It reports directory buckets and large individual
files, prints progress every 100,000 entries, deduplicates hardlinks, and remains
read-only:

```bash
python3 scripts/deep_inventory.py --max-seconds 300 --depth 2 --large-file-mib 512
```

Use repeated `--root PATH` arguments to narrow subsequent passes. Use
`--max-seconds 0` only when an unbounded scan is acceptable. Personal paths are
reported as `protected`; size never makes them cleanup candidates.

On macOS, read [references/macos-developer-storage.md](references/macos-developer-storage.md)
when interpreting simulators, APFS, Docker Desktop, Xcode, Expo, browsers, or
package-manager results.

## Cleanup manager CLI

The executor exposes only hard-coded regenerable actions. It has no arbitrary
path or native-command option. List the actions, then use the human-readable
dry-run before proposing cleanup:

```bash
python3 scripts/cleanup.py list
python3 scripts/cleanup.py dry-run --id expo-cache --id npm-cache
```

The dry-run performs no cleanup. It shows the exact cache roots, estimated
physical bytes, entry counts, regeneration impact, and largest entries. Use
`--top-files N` to change the preview, `--all-files` to print every entry, or
`--json-out /tmp/disk-cleanup-manifest.json` for the complete structured
manifest. JSON export refuses to overwrite an existing file. `plan` remains a
compact machine-readable alternative.

The confirmation token is bound to the selected actions, root identities, and
the recursively observed manifest. If any nested entry changes between dry-run
and execution, the executor recomputes a different token and refuses the old
one. This narrows the approval window but cannot make concurrent filesystem
mutation transactional; stop relevant developer tools before cleanup.

The plan and executor inspect active processes and fail closed when a selected
tool appears active. This guard is intentionally conservative and reduces, but
cannot eliminate, the race where a tool starts immediately after validation.
Never override it; omit that action and retry after the owning task finishes.

After showing that plan and receiving approval, copy the plan token exactly:

```bash
python3 scripts/cleanup.py execute \
  --id expo-cache --id npm-cache \
  --confirm PLAN_TOKEN
```

Never manufacture approval because a token is available. If the selected tools
are running, ask the user to quit them or omit the relevant action. Record free
space immediately before and after execution and report actual recovery; APFS
purgeable space and clones can make logical sizes differ from physical gains.

The allowlisted actions intentionally exclude Docker pruning, simulator erasure,
worktree removal, Chrome/Cursor data, Gradle caches, CocoaPods specs, Xcode
archives, device backups, project artifacts, package-store pruning, and package
manager cleanup commands whose scope can change through configuration. Handle
those only as separately reviewed manual work.

## Manual review items

### Git worktrees

For repositories with many worktrees, fetch the intended integration ref and
run the read-only auditor:

```bash
git -C /path/to/repo fetch origin main
python3 scripts/worktree_audit.py \
  --repo /path/to/repo \
  --main-ref origin/main \
  --measure-sizes \
  --show-blocked
```

An audit candidate only means the worktree is clean, its exact HEAD is an
ancestor of the selected main ref or recoverable from its upstream, it is
unlocked, and no current process CWD or arguments reference it. The report also
shows dirty state, upstream divergence, submodules, recovery proof, and concrete
blockers. It is not deletion approval and does not establish ownership. The
bundled auditor never removes worktrees. Respect repository agent policy and
use `git worktree remove EXACT_PATH` only after separate owner review; never
delete a worktree directory directly or use `--force`.

### Native resource owners

When the deep inventory identifies a large managed store, use its read-only
native accounting before proposing a command:

- Docker: run `python3 scripts/docker_audit.py`. It distinguishes active or
  mounted containers, referenced or locally irrecoverable images, protected
  volumes, active builds, reclaimable build cache, and `Docker.raw`. It never
  prunes anything.
- Simulator: run `python3 scripts/simulator_audit.py`. It distinguishes booted,
  available, and unavailable devices, checks developer activity, reports exact
  UDIDs and sizes, and never deletes or erases device state.
- pnpm: run `python3 scripts/pnpm_audit.py`. It resolves the active store,
  measures allocated space, requires a clean `pnpm store status`, detects pnpm
  activity, and never prunes. Treat its suggested `pnpm store prune` as a
  separate native action with redownload cost.

For a `review` or `protected` finding:

1. Identify the owning application/project and whether the state exists
   elsewhere.
2. Distinguish cache from data using the tool's own inspection command.
3. Explain exactly what will be lost and how it could be recreated or restored.
4. Request separate approval for the exact native command or path.
5. Prefer the owning tool (`docker system prune`, `xcrun simctl`, `git worktree
   remove`, package-manager commands) over filesystem deletion.

Do not propose deletion merely because a file is old or duplicated. For apparent
duplicates, verify content and the user's desired canonical copy first.

## Completion

Report:

- free space before and after;
- actions completed and any failures;
- actual physical space recovered;
- large remaining review/protected items;
- expected redownload or rebuild consequences.

Do not claim success from summed candidate sizes alone.

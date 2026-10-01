# Disk cleanup decision rules

Use these rules after inventory identifies a material consumer. Size, age, a
sleeping process, or a familiar directory name never proves that deletion is
safe.

## Decision vocabulary

- `allowlisted`: regenerable cache supported by the bundled executor. It still
  requires an exact current manifest, no owning-tool activity, and fresh user
  approval.
- `review-ready`: deterministic technical preconditions pass, but ownership and
  intent still require fresh approval for the exact native action.
- `review`: evidence is incomplete or the resource may encode useful state.
- `blocked`: a concrete active-use, recoverability, integrity, or policy blocker
  exists.
- `protected`: the skill must not delete this resource.

Every decision must include the observed evidence, blockers, consequence,
recovery path, estimated physical reclaim, and exact owner-native action if one
can safely be proposed. A blocker always wins over positive evidence. Before
approval, `safe_to_delete_now` is always false.

Use `null`/unknown for reclaim when shared layers, hardlinks, sparse files, or a
native tool make a trustworthy pre-action estimate impossible. Never present a
store's total size as the amount a prune would recover.

## Git worktrees

Run `worktree_audit.py` against a freshly fetched integration ref. A worktree is
`blocked` if any of these is true:

- it is the main worktree, locked, missing unexpectedly, or has submodules;
- tracked or untracked changes exist, or `git status` could not complete;
- a live process CWD or command references the path;
- its branch is ahead of its upstream;
- a detached HEAD is not reachable from the selected integration ref;
- an unmerged branch has no verified upstream recovery ref;
- repository policy forbids this agent from removing it.

It is only `review-ready` when it is clean, unlocked, inactive, and the exact
HEAD is recoverable either from the selected integration ref or a verified
upstream. Recent activity lowers confidence but old age never raises it. The
auditor cannot establish human/agent ownership, so owner approval remains
mandatory. Remove with `git worktree remove EXACT_PATH`, never `rm`, and never
use `--force`. A `prunable` entry whose directory is already missing is only a
metadata cleanup candidate; `git worktree prune --dry-run` previews that scope.
[Git worktree documentation](https://git-scm.com/docs/git-worktree.html)

## Docker

Run `docker_audit.py`. Never delete `Docker.raw` directly.

- Build cache can be `review-ready` only when Docker marks it reclaimable and
  no build/buildx/bake activity is visible. Prefer an age or storage bound such
  as `docker buildx prune --filter "until=24h"`; expect slower rebuilds.
- A running container is `blocked`. A stopped container is at best
  `review-ready` after inspecting its writable layer, mounts, labels, restart
  policy, and owner. Removing it destroys its writable layer and logs.
- An image referenced by any container is `blocked`. An unreferenced image is
  still `review` until a registry digest or reproducible build source proves a
  recovery path; local tags are not recovery proof.
- Volumes are `protected` by default because they may contain the only copy of
  data. Do not add `--volumes` to broad prune commands.
- Prefer a narrow resource command over `docker system prune`; never use
  `--force` to bypass a fresh reviewed plan.

Docker documents that `system df` reports daemon disk use, ordinary system
prune includes stopped containers, unused networks, dangling images and unused
build cache, and volumes require an extra opt-in. Buildx supports bounded cache
pruning with age and retained-space filters. [Docker disk usage](https://docs.docker.com/reference/cli/docker/system/df/),
[Docker pruning](https://docs.docker.com/engine/manage-resources/pruning/),
[Docker buildx prune](https://docs.docker.com/reference/cli/docker/buildx/prune/)

## Package managers and generated outputs

- npm/pnpm/Bun/Expo/Playwright/Homebrew cache roots are `allowlisted` only when
  the bundled cleanup manager recognizes the fixed path and its active-tool
  guard is clear. Redownload cost must be shown.
- A pnpm content-addressable store is `review`, never a raw-path deletion.
  Require `pnpm store status` to pass, no pnpm activity, and a separate approval
  for `pnpm store prune`. Do not use `--force`; it widens scope to alien files.
- `node_modules`, `.next`, `.turbo`, coverage, Gradle, CocoaPods, and DerivedData
  are rebuildable but project-owned. They are `blocked` while a process uses the
  project, while Git/worktree ownership is unresolved, or when the rebuild
  command and lockfile are unknown. Otherwise they are only `review-ready`.
- Never sum a pnpm store and hardlinked project installations without inode
  deduplication.

## Simulators and development devices

- An unavailable Simulator may be `review-ready` for
  `xcrun simctl delete unavailable` after confirming no simulator/build task is
  active.
- A booted device is `blocked`.
- A shutdown but available device remains `review`: it contains apps, test data,
  keychains, and settings. Record its UDID, runtime, size, last-use evidence, and
  recreation cost before proposing exact deletion or erase.
- Device backups, Xcode archives, and symbol archives are `protected`.

## Applications, archives, and personal data

- Browser/editor profiles, databases, conversations, model downloads, Docker
  volumes, game data, application support, and ad-hoc archives are `review` or
  `protected`; their owning application must identify cache versus state.
- Desktop, Documents, photos, credentials, backups, source, untracked files,
  and Trash are `protected` regardless of size.
- Duplicate-looking or old files remain `review` until content identity and the
  desired canonical copy are established.

## Execution and verification

Re-read every predicate immediately before a mutation and fail closed on any
change. One approval covers one exact action set, not newly discovered targets.
Afterward, report executor results and filesystem free space; never equate
logical candidate size with physical bytes recovered.

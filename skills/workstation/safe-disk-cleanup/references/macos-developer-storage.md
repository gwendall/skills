# macOS developer storage notes

Read this reference only for macOS developer cleanup.

## Measure the right number

APFS sparse files, clones, hardlinks, snapshots, and purgeable space make
apparent size unreliable. Prefer `du -sk` or `st_blocks * 512` for allocated
bytes. Report `df -h /` before and after cleanup; do not sum directory sizes and
call that the recovered space.

`Docker.raw` commonly has a very large apparent capacity while allocating far
less physical space. Inspect it with both `ls -lh` and `du -h`. If Docker is
running, use `docker system df -v` before proposing a prune. Never delete the raw
disk or volumes unless the user explicitly chooses a Docker reset and accepts
the data loss.

## Package managers and JavaScript builds

- `pnpm store prune` removes unreferenced store content but can require future
  downloads. Keep the active store and active `node_modules` by default.
- `npm cache clean --force` removes the npm content cache. `~/.npm/_npx` contains
  disposable npx installs.
- Root `node_modules/.old_modules-*` directories are usually interrupted-install
  leftovers. Confirm the repository's declared package manager and lockfile
  before proposing their removal.
- A `.bun` tree inside `node_modules` may be obsolete in a pnpm-only repository,
  but verify `packageManager` and lockfiles first.
- `.next`, `dist`, `build`, `.turbo`, and coverage folders are rebuildable only
  when the owning project and build process are known. Never remove them from
  another agent's worktree.

## Expo, Xcode, and simulators

- `~/.expo/expo-go` and `~/.expo/ios-simulator-app-cache` are downloaded app
  caches. They are allowlisted by the executor.
- Xcode `DerivedData` is rebuildable but can disrupt an active build; it is
  intentionally review-only.
- Xcode `Archives` may be needed for symbolication, export, or release records.
  Treat it as protected.
- `~/Library/Developer/CoreSimulator/Devices` contains installed apps and local
  app state. List devices with `xcrun simctl list devices` and measure each UUID.
  Erasing or deleting a device is a data-loss decision.
- `xcrun simctl delete unavailable` can still discard otherwise valuable state
  tied to a removed runtime. Keep it review-only.
- `~/Library/Application Support/MobileSync/Backup` contains iPhone/iPad backups.
  It is protected data, never a cache.

## Browsers and editors

Playwright browser binaries are rebuildable downloads. Ordinary Chrome caches
may be regenerated, but Chrome profiles, IndexedDB, Local Storage, extension
state, and cookies are user data. Quit the browser and use its own controls for
profile data.

Cursor/VS Code `state.vscdb`, workspace storage, and global storage can contain
conversation history, extension state, and settings. Large size alone does not
make them caches.

## Git worktrees

Measure linked worktrees and show `git worktree list --porcelain`. Never remove
a worktree merely because it is large or old. Its branch, uncommitted changes,
agent ownership, and integration status must be resolved by the repository's
normal lifecycle process.

## Native cleanup preference

Prefer these scoped commands after approval:

```bash
pnpm store prune
npm cache clean --force
brew cleanup -s
```

Do not run broad patterns such as `rm -rf ~/Library/Caches/*`, `rm -rf /tmp/*`,
or recursive deletion based only on a directory name.

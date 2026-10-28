---
name: mac-for-agents
description: Measure what macOS file indexing (Spotlight and fseventsd) costs on a Mac where coding agents rewrite thousands of files, then guide the one supported setting that stops Spotlight indexing code folders, and measure again. Read-only, no sudo. Use when a Mac running Claude Code, Codex or other agents is slow, hot or loud, when mds_stores, mdworker or fseventsd top Activity Monitor, or to optimize a Mac for agents. Triggers on "Spotlight eats my CPU", "mds_stores", "mdworker", "fseventsd", "Mac slow with agents", "optimize my Mac for agents", "exclude node_modules from Spotlight", "stop Spotlight indexing my code".
compatibility: macOS only (mdutil, mdfind, ps, sysctl, tmutil). Bash. Read-only; it changes nothing on its own. Works in Claude Code and any agent with Bash.
homepage: local
metadata: {"version":"1.0.0","updated":"2026-10-28","author":"gwendall"}
---

# mac-for-agents - what indexing costs while agents work

Agents install dependencies, build, test and create worktrees: tens of thousands of
files change every hour. Spotlight indexes every file inside your code folders,
`node_modules` included, and reindexes in bursts each time they change. Nobody searches
`node_modules` with Spotlight, so that work is pure waste. This skill measures the cost
on the machine, guides the supported fix (Spotlight's privacy list), and measures again.

## The fast path

```bash
scripts/mac-for-agents.sh report             # what is indexed, what it costs right now
scripts/mac-for-agents.sh measure before 10  # 10 min of samples while agents work
scripts/mac-for-agents.sh fix                # opens Spotlight settings and the code folder
scripts/mac-for-agents.sh measure after 10   # same sampling after the user's change
scripts/mac-for-agents.sh compare
```

Code folders default to the usual names under `$HOME` (code, Code, src, dev, Developer,
project, projects, work, repo, repos, git). Set `CODE_DIRS="~/a ~/b"` to choose. `measure` writes
`<label>.csv` in the current folder, one row every 10 s.

## How to read it

- **Spotlight** (`mds`, `mds_stores`, `mdworker*`): average and peak CPU. The peak tells
  the story: bursts of several cores whenever agents write in bulk.
- **Indexed counts**: `report` asks Spotlight's own index how many `package.json` and
  `node_modules` it holds under each code folder. After the fix both should read 0.
- **fseventsd** records every file change for the whole system, for every client, not
  only Spotlight. Excluding folders from Spotlight does not stop it. Fewer files moving
  does: remove finished worktrees and stale `node_modules`. Its resident memory often
  only drops after a restart.
- Compare runs with a similar number of agent processes (`agents_cli` column) and a
  similar load. The workload moves the numbers more than any setting; say so when the
  two runs differ.

## An example, one Mac

128 GB, 18 cores, 18 agent processes (Claude Code and Codex), 10 minutes, before the fix:
Spotlight held 12,286 `package.json` and 1,983 `node_modules` from the code folder;
Spotlight averaged 27 % CPU with bursts to 360 % (3.6 cores) and 1.6 GB; fseventsd held a
full core (104 %) and 19.9 GB resident.

## Rules for the agent

- Never run `sudo mdutil`, never edit `/System/Volumes/Data/.Spotlight-V100`, never script
  or click System Settings for the user. The user adds the folder with + in Spotlight's
  privacy list; `fix` opens the pane and reveals the folder.
- Never turn indexing off for the whole volume: Spotlight, Mail and app search need it.
- Report numbers from `measure`, not impressions, and the confounders with them.

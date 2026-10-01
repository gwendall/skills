---
name: ci-cost-monorepo
description: Diagnose and cut a runaway GitHub Actions bill in a monorepo. Measures where the money actually goes (billable minutes per workflow, per job, per step), then applies the fixes that matter - scoping installs with `--filter`, collapsing wide matrices of fast tests, killing per-job setup overhead. Use when CI costs seem too high, when a spending limit blocks all workflows, when someone asks "what is consuming our Actions minutes", or before adding another job to a matrix. Triggers on "GitHub Actions bill", "CI costs too much", "Actions budget exceeded", "spending limit reached", "why is CI so slow", "CI takes forever", "reduce CI minutes", "Actions minutes".
compatibility: Requires `gh` (authenticated, repo read access) and node for the analysis scripts. The fixes assume a pnpm/npm/yarn workspace monorepo on GitHub-hosted Linux runners. No write access needed to diagnose.
metadata: {"version":"1.0.0","openclaw":{"requires":{"bins":["gh","node"]},"emoji":"money_with_wings"}}
---

# Cutting a runaway CI bill in a monorepo

Real diagnosis and fix, from a private monorepo billing ~$700/month. The cost was not one runaway workflow, not macOS runners, not cron jobs. It was **per-job setup overhead multiplied by a wide matrix multiplied by run volume**.

Work in this order: **measure first, then fix**. Most CI cost advice is guesswork; the numbers are cheap to get and usually point somewhere unexpected.

## The billing model (why the waste hides)

Three facts drive nearly every surprising bill:

1. **GitHub bills per job, rounded UP to the minute.** A job that runs for 8 seconds bills 1 minute. A 10-job matrix of 8-second tests bills 10 minutes.
2. **Every job is a fresh machine.** Checkout, toolchain setup and dependency install are paid again in every single job. Nothing is shared.
3. **Private repos pay for everything.** Public repos get standard runners free, which is why this problem is invisible until a repo goes private.

The consequence: **a wide matrix of fast tests is the single most expensive shape in CI.** It looks like good practice (isolation, parallelism, clear failure attribution) and it is the most common source of a large bill.

## Step 1 - Measure

Do not skip to the fixes. Run the analysis script:

```bash
scripts/analyze-actions-cost.sh <owner>/<repo>
```

It reports, per workflow: runs per day, billable minutes per run, jobs per run, and an estimated monthly cost. Then it drills into the most expensive workflow, job by job and step by step.

What you are looking for, in order:

- **The setup-to-work ratio inside one job.** If `install` takes 100s and the test takes 2s, you have found the bill. This is the number that settles every argument.
- **Jobs per run.** Anything above ~5 for a fast test suite is suspect.
- **Runs per day.** High volume is often agent/bot driven (many PRs, frequent pushes) and is a separate lever.
- **Which workflows lack `--filter` / scoping.** In a monorepo, installing everything to test one package is the most common single defect.

Manual equivalents if you prefer to poke by hand:

```bash
# runs in a window, grouped by workflow
gh api --paginate "/repos/OWNER/REPO/actions/runs?per_page=100&created=>=YYYY-MM-DD"

# per-job durations for one run (this is what you get billed for)
gh api "/repos/OWNER/REPO/actions/runs/RUN_ID/jobs?per_page=100" \
  --jq '.jobs[] | "\(.name) \(.started_at) \(.completed_at)"'

# per-step breakdown for one job - the money shot
gh api "/repos/OWNER/REPO/actions/jobs/JOB_ID" \
  --jq '.steps[] | "\(.name) \(.started_at) \(.completed_at)"'
```

Note: `/actions/runs/{id}/timing` often returns `total_ms: 0` (billing not finalized, or the run never started because a spending limit blocked it). Compute durations from the jobs endpoint instead - `completed_at - started_at`, rounded up per job. That is what the script does.

## Step 2 - Fix, highest leverage first

### 2.1 Scope the install (biggest win in a monorepo)

Installing the whole workspace to test one package is pure waste, and it is paid in every job.

```yaml
# Before: installs every project in the monorepo
- run: pnpm install --frozen-lockfile

# After: only this product and its workspace dependencies
- run: pnpm install --frozen-lockfile --filter="./products/myproduct/**..."
```

The trailing `...` includes workspace dependencies of the selection. Equivalents: npm has `--workspace`, yarn has `workspaces focus`, turborepo/nx have their own scoping.

Verify the selector locally before committing - a wrong filter silently installs nothing or everything:

```bash
pnpm ls -r --depth -1 --filter="./products/myproduct/**..." | grep -cE "^[a-z@]"
```

### 2.2 Collapse wide matrices of fast suites

A matrix is worth it when jobs are genuinely long and you want wall-clock parallelism. It is a pure loss when each job is seconds of work behind minutes of setup.

```yaml
# Before: 8 jobs, 8 checkouts, 8 installs, ~20s of actual testing
strategy:
  matrix:
    include:
      - { package: '@scope/a', dir: packages/a }
      - { package: '@scope/b', dir: packages/b }
      # ... 6 more
steps:
  - run: pnpm install --frozen-lockfile
  - run: pnpm --dir ${{ matrix.dir }} test

# After: 1 job, 1 checkout, 1 scoped install, same coverage
steps:
  - run: pnpm install --frozen-lockfile --filter="./packages/**..."
  - run: pnpm -r --filter="./packages/**" run test
```

Two bonuses beyond cost:

- **Recursive run discovers packages.** A hand-maintained matrix rots: in the real case, four packages with test suites were missing from the list and had never run in CI. Auto-discovery makes that class of bug impossible.
- Packages without a `test` script are skipped cleanly (`pnpm -r run test` exits 0), so no per-package bookkeeping.

Keep separate jobs only where separation buys something real: a genuinely slow suite, a different runner, a step you want to fail independently (e2e is usually worth its own job).

### 2.3 Shrink checkout

A 30s+ checkout means a bloated `.git` (large binaries in history). Fixes, in increasing order of effort:

- `actions/checkout` already defaults to `fetch-depth: 1`; confirm nothing overrides it.
- Use `sparse-checkout` when a job only needs part of the tree.
- **Strip large files from history** (`git-filter-repo`, BFG) and move them to Git LFS. Destructive and team-wide, but it is paid back in every job of every workflow - and it usually fixes unrelated pain too (slow clones, oversized build-upload archives).

### 2.4 Cut run volume

Cost scales linearly with runs. Levers:

- `concurrency` with `cancel-in-progress: true` so a new push kills the superseded run.
- `paths:` filters so unrelated changes do not trigger a product's CI.
- **Skip CI on draft PRs**, then run on `ready_for_review`. Large win when PRs are opened early and pushed to repeatedly (bot- or agent-driven workflows especially).
- Restrict `push:` to the default branch; let `pull_request` cover branches. Running both on every branch push doubles the bill.

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  push:
    branches: [main]

jobs:
  test:
    if: github.event.pull_request.draft == false
```

### 2.5 Consider self-hosted for heavy, private workloads

Self-hosted runners bill zero Actions minutes. Worth it when the bill is dominated by long, frequent jobs. Caveats: security posture for untrusted PRs, maintenance, and do not co-locate it with your daily workstation - a runaway job will starve the machine you work on. A small dedicated VM is the usual answer.

## Anti-patterns to flag on sight

- **Adding one more entry to a wide matrix.** Each entry is another full setup. Ask whether the matrix should exist at all.
- **`install` with no scope in a monorepo job.** Almost always wrong.
- **Caching the package-manager store but not measuring it.** A warm store still costs real time to link a huge workspace; the fix is installing less, not caching harder.
- **Matrix used for failure attribution.** Step names and test output already tell you what failed. Do not pay minutes for a nicer UI.
- **Believing wall-clock time.** A 5-minute run with 15 parallel jobs bills far more than 5 minutes.

## Sanity checks before you commit

- Parse the YAML (a broken workflow file fails at a moment when CI may be blocked and hard to test).
- Verify any workspace selector locally and print how many projects it resolves to.
- Confirm the recursive runner skips scriptless packages instead of failing.
- State the expected before/after in the PR description, so the change is auditable later.

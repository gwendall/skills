---
name: multi-agent-repo
description: Audit and bootstrap a repository for many concurrent coding agents without merge races, repeated qualification, or runaway CI. Use when agents share a repository through worktrees, when parallel PRs keep invalidating each other, when setting up a new project for agent teams, or when designing immutable qualification and a serialized merge lane. Not for ordinary single-agent feature work or CI cost diagnosis alone.
metadata: {"version":"1.0.0","updated":"2026-08-27","openclaw":{"requires":{"bins":["git","bash"]},"emoji":"traffic_light"}}
---

# Multi-agent repository operations

Build a control plane in which agents work in parallel but integration is
serialized. Do not solve coordination by repeatedly merging the moving default
branch into every task branch.

The durable system has four layers:

1. A launcher creates a unique branch and linked worktree before an agent starts.
2. Repository-local `AGENTS.md` files state the project-specific contract.
3. Impact planning, stable gates, and exact-SHA evidence enforce the contract.
4. One identity owns the final merge lane.

Instructions alone are not enforcement. Prefer executable checks and server-side
permissions for every invariant whose violation can corrupt the default branch or
restart expensive qualification.

## Requirements

Local helpers require Git, Bash, and standard POSIX command-line utilities.
GitHub inspection and rollout require an authenticated `gh` CLI. Non-GitHub
repositories can still use the local worktree, contract, and qualification model.
Audit mode is read-only.

## Select the mode

- **Audit**: inspect an existing repository and report gaps without writing.
- **Bootstrap**: add the smallest useful control plane through an isolated
  worktree and pull request.
- **Operate**: create a task worktree or explain the normal agent lifecycle.
- **Integrate**: qualify and merge a frozen candidate. Treat remote settings,
  labels, checks, and merges as external mutations requiring user authorization.

If the request is only to find an Actions cost regression, keep the scope to cost
diagnosis rather than bootstrapping this entire system.

## Start with evidence

For an existing repository, run the read-only audit from this skill directory:

```bash
bash scripts/audit-repo.sh /absolute/path/to/repository [owner/repository]
```

Inspect existing `AGENTS.md`, contributor docs, worktree state, workflows,
branch protection, repository plan, and dirty changes before proposing edits.
Preserve unrelated work and existing policy. A simple repository with two agents
and fast tests does not need a custom merge service.

Read [references/control-model.md](references/control-model.md) when choosing the
coordination model. Read [references/agents-contract.md](references/agents-contract.md)
when creating or revising repository instructions. Read
[references/github-rollout.md](references/github-rollout.md) before changing GitHub
settings or CI.

## Bootstrap in this order

1. Create a dedicated setup worktree. Never edit a shared or dirty checkout.
2. Record the current default-branch SHA and existing protections.
3. Add a short root `AGENTS.md` with only repository-specific rules.
4. Add deterministic impact and policy tests before optimizing the workflows.
5. Make required gates stable: every pull request reports a conclusion, while
   unaffected work exits cheaply inside the workflow.
6. Separate automatic deterministic checks from long or premium qualification.
7. Store qualification as evidence for one exact source SHA.
8. Add a semantic-overlap check for movement of the default branch.
9. Establish one merge identity and an ordered ready queue.
10. Observe the new gates green on a real pull request.
11. Only then enable required checks and branch restrictions.

Do not switch on branch protection against check names that have never reported
success. Do not make "branch must be up to date" the coordination mechanism in a
busy repository.

## Non-negotiable invariants

### Isolate work

- One task, one branch, one linked worktree.
- Never reset, clean, reuse, or delete another agent's worktree or branch.
- The launcher should place the agent in its worktree; do not rely on the agent
  remembering to create one after it starts.

When authorized to start a task, the included helper creates a worktree without
deleting or overwriting anything:

```bash
bash scripts/create-agent-worktree.sh TASK-ID [base-ref] [destination-parent]
```

Run `bash scripts/agent-preflight.sh [repo-path]` at the start of agent work. Add
`--require-clean` when checking a newly created worktree.

Wire isolation into the orchestrator before starting the agent; an instruction to
an already-running agent is too late. Use porcelain mode to obtain the directory
for the session's `cwd`:

```bash
task_path="$(bash scripts/create-agent-worktree.sh --porcelain TASK-ID BASE-REF WORKTREE-PARENT)"
launch-agent --cwd "$task_path"  # replace with the orchestrator's real command
```

If the orchestrator cannot set the initial working directory, wrap its launch
command or reject the launch. Record that real wrapper command in `AGENTS.md`.

### Qualify immutable revisions

Run the read-only context helper from this skill directory and record all three
values:

```bash
bash scripts/qualification-context.sh /absolute/path/to/task-worktree
```

Checks, artifacts, reviews, and merge commands must refer to
`QUALIFIED_HEAD`, not a moving branch name. A later push creates a new candidate.
Metadata events on an unchanged pull request must not manufacture or invalidate
evidence.

Run long or premium tests only after deterministic checks pass. Trigger them once
for the frozen affected candidate. The expensive trigger must not cancel, skip,
or replace the ordinary checks.

### Treat movement of the default branch semantically

Being behind the default branch is not itself a failure. Before integration,
compare changes since `QUALIFIED_BASE` against the candidate:

- Same files, textual conflicts, shared infrastructure, owned workspace,
  transitive dependency, or unresolved graph edge: integrate once and requalify
  the affected candidate.
- Proven disjoint: retain the frozen head and its evidence.

The overlap implementation must fail closed for unknown ownership, root build
entry points, shared CI, and dependency edges it cannot resolve.

### Serialize integration, not development

Agents may develop, test, review, and qualify concurrently. One integrator owns
the state transition into the default branch. The merge command must protect the
expected head SHA.

If multiple products are independent, use domain lanes: unrelated lanes may keep
moving while a candidate requalifies, but a later overlapping candidate may not
overtake it.

When agents share one GitHub user or token, documentation cannot distinguish a
developer from the integrator. Use a separate GitHub App, machine user, or token,
and enforce the distinction on the server.

## Deliverables

A complete bootstrap normally produces:

- a concise root `AGENTS.md` and narrowly scoped nested files when needed;
- a machine-readable ownership/integration configuration when the graph is too
  complex for path conventions alone;
- worktree launcher and preflight commands;
- executable policy and impact tests;
- stable deterministic and qualification gates;
- a ready-state protocol and one merge actor;
- a staged GitHub settings plan;
- a short operational document with measured CI baseline and rollback.

Keep each artifact independently useful. Do not copy generic skill prose into
every repository. The skill supplies the method; the repository records only its
own commands, domains, risks, and authorities.

## Safety boundaries

- Audit mode is read-only.
- Do not change billing, credentials, branch protection, environments, repository
  permissions, or merge state unless the user requested that mutation.
- Resolve exact targets before remote changes and verify the persisted result.
- Apply settings in reversible stages, with branch protection last.
- Stop after one infrastructure retry on the same SHA unless the user explicitly
  asks for monitoring.
- Never bypass missing qualification with an admin merge merely to finish the
  setup.

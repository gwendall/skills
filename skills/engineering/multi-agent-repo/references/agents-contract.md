# Repository agent contract

Use this as a content checklist, not as text to paste unchanged. Keep the root
`AGENTS.md` short enough that every agent can act on it.

```markdown
# Agent repository contract

## Scope and precedence

- This file applies repository-wide.
- Nested `AGENTS.md` files may add domain rules but cannot weaken integration or
  safety controls.

## Start a task

- Use `<launcher command>` to create one branch and linked worktree per task.
- Never work on `<default branch>` or in the shared primary checkout.
- Never edit, reset, clean, reuse, or remove another task's worktree or branch.

## Validate

- Run `<fast validation command>` before pushing.
- The impact planner is `<impact command or workflow>`.
- Unknown ownership, graph errors, and shared infrastructure fail closed.

## Freeze qualification

- Record `QUALIFIED_BASE=<command>` and `QUALIFIED_HEAD=<command>`.
- Run normal deterministic checks first.
- Trigger `<full qualification mechanism>` only when impact requires it and only
  after the head is frozen.
- A later push creates a new candidate and invalidates prior evidence.

## When the default branch advances

- Do not merge or rebase it merely to remove a behind indicator.
- Run `<semantic overlap command>`.
- Retain exact-SHA evidence for a proven disjoint delta.
- Integrate once and requalify only when overlap is reported.

## Integrate

- Apply `<ready state>` when the candidate is ready.
- Only `<integrator identity>` may merge.
- Immediately before merge, rerun overlap and verify the exact head SHA.
- Use `<head-protected merge command>`.
- Keep post-merge closeout changes in a separate pull request.
```

## What belongs elsewhere

Do not turn `AGENTS.md` into a general engineering handbook.

- Put machine ownership and domain paths in one parsed configuration.
- Put long rationale, measurements, and incident history in project docs.
- Put command implementation in scripts.
- Put merge and permission enforcement in the Git host.
- Put human contribution guidance in `CONTRIBUTING.md`.

Nested contracts should contain only real local differences: native toolchains,
product-specific qualification, deployment constraints, or protected assets.

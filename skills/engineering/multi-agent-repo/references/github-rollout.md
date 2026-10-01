# GitHub rollout

Read current official GitHub documentation before mutating settings; plans and
API schemas change. Inspect with `gh api` and preserve existing protections.

## Read-only inventory

Collect at least:

- repository plan, visibility, default branch, and merge methods;
- current branch protection and rulesets;
- required status checks and whether strict up-to-date mode is enabled;
- Actions permissions, workflow token permissions, and SHA pinning;
- relevant labels, environments, repository variables, and scheduled workflows;
- billing budgets and premium runner usage when authorized;
- installed GitHub Apps or the lack of a separate merge identity.

The included `audit-repo.sh` collects the common subset without changing state.

## Stable checks

A required check must report for every pull request. A workflow skipped by branch
or path filtering can leave a required check pending. Trigger the small planner
and final gate broadly, then skip expensive internal jobs after a deterministic
impact decision.

Use `always()` for a final gate that must report after failed or skipped needs,
and validate every allowed result combination. A skipped prerequisite is not
proof unless a successful planner explicitly selected that path.

## Rollout sequence

1. Land policy tests and stable gates without requiring them.
2. Observe the exact check names succeed on affected and unaffected pull requests.
3. Create the ready and qualification labels.
4. Install and restrict the integrator identity.
5. Require the stable gates with strict up-to-date mode disabled.
6. Require pull requests, block force pushes/deletions, and resolve conversations.
7. Restrict direct integration to the designated identity.
8. Test one ordinary merge and one overlap/requalification path.
9. Record rollback commands and the previous settings response.

Never enable requirements while Actions or billing is blocked.

## Qualification trigger

Treat a label such as `ci:full` as a request, not evidence. The workflow should:

- accept the exact label event, not merely label presence;
- verify the actor is allowed to spend premium capacity;
- use a concurrency group that cannot cancel deterministic checks;
- verify deterministic success on the exact source head;
- report a stable qualification gate;
- carry evidence across unrelated metadata events only by querying prior success
  for the same check name and source SHA.

## Merge queue or custom integrator

Prefer native merge queue when it is available for the repository and plan. Add
the `merge_group` trigger to required workflows and test the temporary merge
commit.

Without native queue, use one durable integrator. It should order ready pull
requests, reserve impacted domain lanes, run the final semantic-overlap check,
and merge with expected-head protection. GitHub Actions concurrency is not a
durable arbitrary-length queue; do not use it as the sole queue store.

Keep auto-merge disabled when it would bypass semantic overlap or lane ordering.

## Credentials

Do not give every agent the administrator or integrator token. Prefer a GitHub
App with narrowly scoped repository permissions. Keep a separately controlled
break-glass administrator path.

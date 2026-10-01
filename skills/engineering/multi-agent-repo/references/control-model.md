# Control model

Use the smallest coordination model that preserves correctness.

## Repository shapes

### Small repository

Use linked worktrees, short branches, one stable CI gate, and one merge owner.
Semantic overlap can be a conservative file-level check when tests are fast.

### Modular monorepo

Add workspace ownership, transitive dependency impact, scoped deterministic
checks, and explicit qualification tiers. Changes to shared infrastructure and
unknown graph edges fail closed.

### High-throughput monorepo

Add an ordered integration queue, domain lanes, separate credentials, cost
telemetry, and a merge-group or integrator check. Native merge queue is ideal
when the hosting plan supports it; otherwise use a durable integrator rather than
concurrent manual merges.

## State machine

Model each pull request as an explicit state transition:

```text
draft
  -> deterministic-checks
  -> frozen
  -> full-qualification (only when impact requires it)
  -> ready-to-merge
  -> integrating
  -> merged
```

Exceptional transitions:

```text
new commit                 -> deterministic-checks
real semantic overlap      -> needs-requalification
disjoint default movement  -> retain ready-to-merge
failed infrastructure      -> one same-SHA retry
failed product check       -> new commit after correction
```

Store state in check runs and exact SHAs, not only labels. Labels are requests or
UI summaries; they are not proof.

## Domain lanes

Map changed files to owned domains and dependency closures. A candidate occupies
its impacted lanes after it enters integration. A later candidate may pass only
when its lanes are disjoint.

Use a global lane for changes such as:

- root manifests and build entry points;
- workspace or lock configuration that cannot be attributed;
- shared CI actions and workflows;
- ownership configuration and the impact planner itself;
- unknown or conflicting files.

Do not encode domain ownership twice. Prefer one machine-readable source consumed
by impact planning, integration, and documentation checks.

## Evidence model

Evidence keys should include:

- source head SHA;
- qualified base SHA;
- impact decision and planner version;
- deterministic gate conclusions;
- required long-tier conclusions;
- relevant runner/toolchain versions when reproducibility matters.

Default-branch movement does not mutate the source head. Retain its evidence only
after checking every incoming delta since the qualified base.

## Identity model

Separate capabilities:

- Developer: branches, commits, pull requests, comments.
- Reviewer: review conclusions, no merge authority required.
- Qualifier: permission to start premium tiers.
- Integrator: final overlap check and head-protected merge.
- Administrator: settings and break-glass operations, not ordinary integration.

If all agents authenticate as one administrator, the host cannot enforce these
roles. Fix identity separation before calling the process safe.

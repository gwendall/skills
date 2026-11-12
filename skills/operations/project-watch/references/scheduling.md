# Scheduling a project watch

A skill is reusable instructions; it does not wake itself up.

## Recommended starting policy

- Active project: light check every six hours.
- Launch, interview or press window: optionally every three hours for a defined
  period, then review the cadence.
- Quiet project: daily.
- Broad discovery and a combined briefing: daily, for example 09:00 in the owner's
  configured timezone.
- Relevant webhook/event sources: use an existing supported trigger when configured.

Start from enabled projects and existing source permissions. Adding a profile does
not authorize reading a personal inbox or announcing an unreleased project.
Notification quiet hours are a delivery preference, not an assumption about a
scheduler feature. Verify whether the host can enforce them.

## Resolve the execution environment

An unattended process needs the same authorized sources and durable memory as the
manual run. Use the host scheduler's existing retries, concurrency control and run
history. Keep browser-dependent sources explicitly partial until a separate
unattended connection is configured.

For ChatGPT/Codex scheduled tasks, current official documentation distinguishes:

- Desktop local project tasks need the computer powered on, the app running and
  the project available on disk.
- Cloud/web tasks can use their configured context and connected tools, but cannot
  directly access a folder on the owner's computer.
- The CLI and IDE do not provide the Scheduled management interface.
- A task prompt can invoke a skill. One task can handle more than one project.

Source, checked 2026-11-12:
https://learn.chatgpt.com/docs/automations

Capabilities vary by runtime and workspace. Prefer current documentation and the
actual tools exposed in the session over remembered configuration files.

## Ready task prompt

Replace the profile reference with a real private path or an authorized connected
resource before registering the task.

> Run $project-watch for the enabled projects in PROFILE_REFERENCE.
> Perform the sources due for this run. Use each source's last successful discovery
> and message/comment checkpoints, with an overlap window and stable ID deduplication.
> Reuse canonical memory and read-only adapters. Preserve exclusions and source
> failures. Do not use the owner's active browser in a scheduled run.
> Record evidence, observations, actual reading coverage and useful follow-ups.
> Report material changes to the owner's existing task inbox and group routine
> movements into the daily briefing when supported by the host.
> Never send, publish, follow, like, accept requests or enroll from this task.
> If a source is inaccessible, record it and leave its checkpoint unchanged.
> If no material finding exists, return a short checked-sources receipt.
> Do not create another schedule or a daemon from inside a scheduled run.

Suggested recurrence: every six hours, timezone set explicitly by the owner.
For a separate daily briefing task, use 09:00 in that timezone and summarize stored
observations since the last digest; do not rerun every collector unnecessarily.

## Activation receipt

Do not call the schedule active until a supported tool or UI confirms its identity,
enabled state, cadence/timezone, task prompt, projects, execution environment and
delivery destination. Record the first test run and known source gaps.

If those capabilities are unavailable in the current session, leave activation
pending and provide the exact prompt and cadence. Never claim automatic reports
will arrive merely because a skill or profile was installed.


## Owner-authorized OS scheduler

An installed OS scheduler such as macOS launchd can own a finite local runtime
when the owner explicitly requests automation and the existing tooling map has
been checked. Use a stable release, one visible job label, concurrency exclusion,
private logs, bounded children and a documented pause/re-enable path. Verify a run
started by that scheduler and a durably delivered report. Notification submission
alone does not establish visible delivery. An asleep/offline computer is an access
condition, not a no-change result. Do not conceal the absence of cloud execution.

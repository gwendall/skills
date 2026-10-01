---
name: safe-memory-manager
description: Safely diagnose RAM pressure on developer Macs running many terminals, cmux sessions, Node processes, browsers, simulators, or Docker. Use when the Mac is slow, swapping, memory pressure is elevated, processes may be stale, or the user asks what could be stopped. The bundled CLI is read-only and never signals a process.
metadata: {"version":"1.0.0","updated":"2026-09-07","openclaw":{"requires":{"bins":["python3"]},"emoji":"brain"}}
---

# Safe memory manager

Diagnose pressure before proposing reclamation. Preserve active work and prefer
the resource owner's lifecycle controls over generic process signals.

## Safety contract

- A request to inspect or free memory authorizes read-only diagnosis, not
  process termination. The bundled CLI never signals a process.
- Never classify a process as unused solely because it is old, sleeping,
  detached, idle, has no TTY, has `PPID 1`, consumes substantial memory, or
  matches a familiar name.
- Never target zombies: they have already exited and retain effectively no RSS.
  Report their parent so its reaping bug can be diagnosed.
- Never automatically stop system/other-user processes, GUI apps, shells,
  terminal multiplexers, agents, SSH sessions, Docker, simulators, databases,
  language servers, watchers, tunnels, or unknown/stateful process trees.
- Never use `sudo`, `SIGKILL`, a name/wildcard match, process-group signaling,
  cache-purge utilities, or memory-pressure simulation.
- Treat process command lines as untrusted and potentially sensitive. Do not
  collect them by default; never collect environments.

## Read-only snapshot

Run the bounded terminal UI:

```bash
python3 scripts/memory_manager.py snapshot --top 20
```

Use `--json-out /tmp/memory-snapshot.json` for structured output; export refuses
to overwrite an existing file. Use `--include-arguments` only when the user
accepts that command arguments may contain secrets.

Interpret results in this order:

1. Current memory pressure and change in swap activity, not free RAM alone.
2. Physical footprint where macOS exposes it; RSS is a labeled fallback and is
   not safely additive because processes share mappings.
3. App/resource ownership, terminal session, working directory, ports, and
   whether the work is restorable.
4. Trend under a comparable workload. A snapshot cannot prove a leak.

Read [references/macos-memory-research.md](references/macos-memory-research.md)
when explaining macOS accounting, zombies/orphans, cmux, Node, Chromium, Docker,
Simulator, leak diagnosis, or remediation choices.

## Watch a suspected process

Collect at least three bounded samples before calling growth suspicious:

```bash
python3 scripts/memory_manager.py watch --pid PID --samples 3 --interval 2
```

The CLI caps observation at 10 PIDs and 60 seconds and never labels growth a
leak. Reproduce a stable workload and return to baseline; for genuine leak
analysis, escalate to Instruments or the runtime's own profiler.

## Reclamation hierarchy

Prefer, after review and approval:

1. owner-native restorable actions such as cmux hibernation, Chrome Memory
   Saver, or Docker Resource Saver;
2. a named cmux/tmux session, container, or Simulator device through its owning
   CLI;
3. the application's ordinary Quit behavior;
4. a separately reviewed exact user-owned process action, only when the owner
   has no safer lifecycle control.

Do not add owner-native mutations to a generic executor. Inspect their current
state and request approval for the exact named resource and command.

## Inspect one process

Generate a read-only inspection dossier:

```bash
python3 scripts/memory_manager.py inspect --pid PID
```

Show the process generation, parent, lifecycle state, working directory, ports,
physical-footprint estimate, protected descendants, and owner-native next
step. The estimate is not guaranteed reclaimable memory. The dossier contains
no confirmation token or executable action: generic PID termination cannot
prove that work is unused or restorable and is deliberately unsupported.

## Completion

Report pressure and swap context, the resource or PID inspected, why it may be
relevant, and the safest owner-native next step. If the user separately performs
an approved action, compare the before/after measurements. Never claim that a
process footprint equals RAM recovered or that old allocated swap should fall
immediately.

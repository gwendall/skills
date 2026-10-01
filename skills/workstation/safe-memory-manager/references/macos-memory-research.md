# Safe RAM diagnosis and reclamation on macOS

Research date: 2026-09-07. Scope: developer Macs with many terminal/multiplexer sessions, Node processes, Chromium browsers, simulators, and Docker. This note defines the safety model for a diagnostic CLI; it does not authorize process termination.

## Executive conclusion

A safe memory manager should be a **pressure-first, read-only profiler**, not a process killer. High RAM occupancy is normal on macOS: cached files use otherwise-idle memory and can be overwritten, while inactive application memory may be compressed. Apple defines Memory Pressure from several inputs including free memory, swap activity, wired memory, and file cache, so “little free RAM” alone is not evidence of a problem. [Apple: View memory usage in Activity Monitor](https://support.apple.com/en-euro/guide/activity-monitor/-actmntr1004/mac)

The useful product is therefore:

1. establish whether pressure and swap churn are sustained;
2. attribute **physical footprint** to app-owned process trees and developer resources;
3. distinguish intentional detached work from genuinely abandoned work;
4. show evidence, confidence, impact, and an app-native remediation;
5. require explicit approval for every state-changing action.

“Reclaimable” in the UI must mean **estimated process footprint associated with a proposed action**, never “bytes guaranteed to become free.” Shared pages, compressor state, file cache, VM ballooning, and post-exit workload behavior prevent an exact pre-action prediction. The Apple-shipped `footprint(1)` manual explicitly says that virtual size and resident size are poor estimates of required RAM, while its multi-process mode de-duplicates multiply mapped objects.

## Correct mental model

### Pressure, not free RAM

Apple says:

- **Memory Pressure** describes how efficiently memory serves current processing needs and is derived from free memory, swap rate, wired memory, and cached files.
- **Wired** memory must remain in RAM.
- **Compressed** memory is compressed to make room for active applications.
- **Cached Files** occupy unused memory to improve reopening performance and remain available to be overwritten.
- **Swap Used** is disk space used to move inactive content to and from RAM.

Consequently, a single large “Memory Used,” “Swap Used,” or low “Free” value is context, not a kill trigger. The time derivatives matter: rising swap-outs, persistent warning/critical pressure, and degraded responsiveness are much stronger evidence than an isolated snapshot. Apple’s XNU documentation defines pressure levels as Normal, Warning/Urgent, Critical, and Jetsam, and describes available memory as free or reclaimable memory plus compressed anonymous memory. [Apple XNU: Memorystatus Notifications](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_notify.md)

### RSS, footprint, compression, and swap are different

- `RSS`/`RSIZE` is the currently resident portion of a process address space. The Apple-shipped `ps(1)` reports `rss` in KiB. It can include clean or purgeable pages, and summing RSS across processes can double-count shared mappings. [Apple OSS `ps(1)`](https://github.com/apple-oss-distributions/adv_cmds/blob/main/ps/ps.1)
- **Physical footprint** is Apple’s per-process kernel-ledger estimate of dirty memory attributable to a process, including some memory owned on its behalf. The `MEM` column in `top`, Activity Monitor’s Memory column, and Xcode’s memory gauge use this ledger. It is the best default ranking metric on macOS. [Apple OSS `top(1)`](https://github.com/apple-oss-distributions/top/blob/main/top.1) and [`task_vm_info_data_t`](https://developer.apple.com/documentation/kernel/task_vm_info_data_t)
- **Compressed** pages remain represented in the system’s memory accounting; compression is reclamation machinery, not a process leak diagnosis.
- **Swap used** is a stock. `vm_stat` swap-in/swap-out changes across samples are activity. Old swap can remain allocated after pressure subsides, so the stock alone must not produce an alarm.
- `VSIZE` is address space, not RAM. Do not rank candidates by it.

The installed `footprint(1)` manual further divides memory into Dirty, Clean, Reclaimable, Swapped, and Wired. Dirty memory drives the process footprint; clean and explicitly reclaimable memory can be taken back more cheaply; wired memory cannot be paged, compressed, or reclaimed. `footprint --sample` supports time series and `-t` includes descendants. It may require root for processes owned by other users; the CLI should **skip those processes rather than elevate**.

### Zombie, orphan, idle, and detached do not mean the same thing

- A **zombie** is an already-exited child whose parent has not yet collected its termination status. `ps` marks it `Z`/`<defunct>`. The parent must call `wait`/`waitpid`; signaling the zombie cannot reclaim an address space that has already gone. [Apple `wait(2)` manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/wait.2.html) and [Apple `sigaction(2)` manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/sigaction.2.html)
- An **orphan** is a live child whose parent exited; Darwin assigns remaining children to PID 1. It may be legitimate long-running work and is not evidence of a leak. Node, for example, explicitly supports detached children in a new process group/session that can continue independently after the parent exits. [Apple `wait(2)` manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/wait.2.html) and [Node `child_process`](https://nodejs.org/api/child_process.html#optionsdetached)
- A process in `S` (sleeping) or `I` (idle) is alive. It may retain useful state, and macOS can reclaim its clean/reclaimable pages or compress inactive memory.
- A **detached multiplexer session** is deliberately alive without a visible client. tmux keeps state in a background server and explicitly preserves programs across detach/disconnection. Killing the apparent detached server can destroy multiple sessions and panes. [Official tmux architecture](https://github.com/tmux/tmux/wiki/Getting-Started)

For cmux specifically, generic ancestry is weaker than cmux’s own stable workspace/surface/session mapping. Current cmux documentation exposes resource use through `cmux top` and has opt-in agent hibernation that only selects restorable, background, confirmed-idle sessions, revalidates the exact process generation and surface scope, then uses scoped `SIGTERM`. A memory skill should consume or recommend that native mechanism rather than inventing a competing name/PPID heuristic. [cmux CLI contract](https://github.com/manaflow-ai/cmux/blob/main/docs/cli-contract.md) and [cmux agent hibernation safety gates](https://github.com/manaflow-ai/cmux/blob/main/docs/agent-hooks.md#when-a-terminal-hibernates)

## Read-only CLI collection contract

Collect bounded snapshots with timestamps and preserve raw values in JSON:

### System series

- macOS version/build, architecture, boot time/uptime, physical RAM, page size;
- Activity-Monitor-equivalent categories where public interfaces permit: app/footprint, wired, compressed, cached/reclaimable, swap used;
- `vm_stat` counters and deltas: free, active, inactive, speculative, purgeable, file-backed, anonymous, compressor pages, page-ins/outs, swap-ins/outs;
- a bounded `top` sample for global physical-memory/swap summaries and process `mem` (physical footprint);
- sample at least 3 times over a stated window; label a one-shot result “snapshot,” never “leak.”

Apple documents `top`, `vm_stat`, and `vmmap` as command-line tools for virtual-memory analysis. [Apple: Viewing Virtual Memory Usage](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/VMPages.html)

Do **not** invoke `memory_pressure -l`, `-p`, or `-S`: its installed manual says these options allocate memory or simulate warning/critical pressure. They are test controls, not observation commands.

### Process inventory and identity

For every visible process record:

- effective user/UID, PID, PPID, process-group ID, session ID, controlling TTY;
- `state`, start time and elapsed time, CPU%, RSS, physical footprint, command/accounting name;
- descendants and aggregate footprint with shared mappings de-duplicated where possible;
- open listening ports only if the user requests deeper inspection (commands and paths may be sensitive).

Treat command lines as untrusted display metadata. Apple’s `ps(1)` manual says a process can rewrite its displayed arguments and that `ps` only makes an inherently unreliable guess; its accounting name is more dependable. Any later action must re-read and match a process-generation identity tuple such as `(pid, start time, uid, executable/accounting identity, session/process-group scope)` immediately before signaling. Node explicitly warns that after a process exits its PID may be reassigned and a later signal could hit the new process. [Node `subprocess.kill()`](https://nodejs.org/api/child_process.html#subprocesskillsignal)

Enrich with owner-native read-only data:

- **cmux/tmux:** windows, surfaces/panes, attached/detached state, last activity, lifecycle/restorability, and the exact process group supplied by the owner;
- **Node:** group worker/child processes under their actual parent/session; if the app cooperates, distinguish `rss`, V8 `heapTotal`/`heapUsed`, native `external`, and `arrayBuffers`. A diagnostic report can also expose V8 heap statistics and libuv handles, but generating it is an opt-in in-process diagnostic rather than a generic scan. [Node `process.memoryUsage()`](https://nodejs.org/api/process.html#processmemoryusage) and [Node diagnostic reports](https://nodejs.org/api/report.html)
- **Chromium:** group the browser, renderer, GPU, utility, and extension process family. Chromium is intentionally multi-process, so process count is not evidence of abandonment. [Chromium multi-process architecture](https://www.chromium.org/developers/design-documents/multi-process-architecture/)
- **Docker Desktop:** show both the host-side VM/app footprint and per-container `docker stats --no-stream`; container totals are guest accounting and must not be added blindly to the host VM footprint. Docker Desktop runs containers in a Linux VM on Mac, and `docker stats` reports running-container resource usage. [Docker VMM](https://docs.docker.com/desktop/features/vmm/) and [`docker stats`](https://docs.docker.com/reference/cli/docker/container/stats/)
- **Simulator:** correlate CoreSimulator processes with booted devices through read-only `simctl` listing. Xcode documents `simctl` as the supported Simulator control CLI; if the user later requests reclamation, shutdown of a selected booted device through `simctl` is safer than signaling arbitrary CoreSimulator processes. [Xcode command-line tool reference](https://developer.apple.com/documentation/xcode/xcode-command-line-tool-reference)

### Findings and confidence

Each finding should contain: owner, resource/session, evidence, current and peak/trend footprint, activity recency, user-visible impact, suggested native action, confidence, and why it is **not** automatically safe. Recommended labels:

- `pressure-now`: system pressure is currently elevated;
- `large-footprint`: large relative to peers, not necessarily waste;
- `growing`: sustained footprint increase across samples under comparable workload;
- `detached-active`, `detached-idle`, `restorable-idle`, `unknown-owner`;
- `zombie-parent-bug`: no meaningful RAM recovery; identify the parent;
- `possible-leak`: trend warrants profiling, never a conclusion from RSS alone.

For a suspected leak, record a workload-aware time series and look for persistent growth after the workload returns to baseline. Apple recommends Instruments to graph metrics together; Allocations shows allocation lifecycles, Leaks finds unreachable malloc allocations, and VM Tracker follows virtual memory over time. [Apple Instruments help](https://developer.apple.com/library/archive/documentation/AnalysisTools/Conceptual/instruments_help-collection/Chapter/Chapter.html) and [WWDC24: Analyze heap memory](https://developer.apple.com/videos/play/wwdc2024/10173/). For Node, escalate to the V8 Heap Profiler only with consent: heap snapshots take time and additional memory, and Node warns they can contribute to abrupt termination near limits. [Node CLI diagnostics](https://nodejs.org/api/cli.html#--heapsnapshot-near-heap-limitmax_count)

## Safe reclamation hierarchy

The diagnostic command itself performs no reclamation. The current v1 tool
intentionally stops at diagnosis; it does not implement a generic apply or PID
termination command. If a future, separately reviewed owner-native apply flow
is built, it should prefer:

1. **Owner-native reversible behavior:** Chrome Memory Saver deactivates inactive tabs and reloads them on access; Docker Resource Saver stops the Linux VM when no containers run; cmux hibernation preserves only confirmed-restorable idle agents. [Chrome Memory Saver](https://support.google.com/chrome/answer/12929150), [Docker Resource Saver](https://docs.docker.com/desktop/use-desktop/resource-saver/)
2. **Named-resource shutdown:** a user-selected cmux surface/tmux session, named container, or booted Simulator UDID through its official control plane, after showing dependants and loss/restart semantics.
3. **Graceful application quit:** use the app’s own quit protocol where possible.
4. **Exact user-owned `SIGTERM`:** only after process-generation and scope revalidation, explicit confirmation, and a bounded wait. Apple describes `SIGTERM` as an opportunity for clean termination. [Apple SIGTERM documentation](https://developer.apple.com/documentation/xcode/sigterm)
5. **`SIGKILL`:** separate force confirmation only for a still-running exact target; warn that open/unsaved data can be lost and dependent processes can break. Apple’s Activity Monitor gives the same distinction between Quit and Force Quit. [Apple: Quit an app or process](https://support.apple.com/en-ie/guide/activity-monitor/actmntr1002/mac)

Never signal an entire process group unless the owning application supplies and revalidates that scope. `killpg` targets every process in the group, so a mistaken group can affect unrelated work. [Apple `killpg(2)` manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/killpg.2.html)

## Absolute automatic-kill denylist

The tool must never automatically kill:

- a zombie (already dead; report its unreaping parent instead);
- anything solely because it is old, sleeping, idle, detached, has no TTY, has PPID 1, uses much memory, or matches a process name;
- PID 1, `kernel_task`, `WindowServer`, `loginwindow`, launchd-managed system/user services, root/other-user processes, security/authentication/network/storage/sync services;
- the CLI itself, its ancestors, the active foreground terminal group, a shell/multiplexer server, or an unknown process tree;
- GUI applications that may contain unsaved work;
- an active or non-restorable cmux/tmux pane, an active browser tab family, Docker’s VM while containers are running, a container with unknown stateful dependencies, or Simulator processes without a selected booted-device identity;
- databases, build/watch servers, language servers, remote tunnels, VPNs, filesystem watchers, or agent sessions without explicit user ownership and a demonstrated recovery path;
- any target whose identity or membership changed between report and apply.

Also exclude launchd-managed jobs from generic termination recommendations: launchd can keep a job alive or relaunch it on demand, so killing the current PID may provide no durable gain while disrupting a service. [Apple: The Life Cycle of a Daemon](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/Lifecycle.html)

Do not request root merely to widen visibility or termination authority. Apple notes that signaling another user’s process requires matching EUID or root and recommends minimizing privileged helpers. [Apple: Understanding Permissions](https://developer.apple.com/library/archive/documentation/Security/Conceptual/AuthenticationAndAuthorizationGuide/Permissions/Permissions.html)

## Product acceptance criteria

- `scan`, `watch`, and `explain` are provably read-only and bounded.
- Default output leads with pressure/trend, then owner/resource groups; it does not shame cached RAM or raw process count.
- All estimates state metric, timestamp, aggregation/de-duplication method, and uncertainty.
- No “dead process” label is emitted without classifying zombie/orphan/sleeping/detached.
- Any future apply command is separate, off by default, and bound to exact
  identities and proposed owner-native actions; v1 provides no such command.
- Immediately before any future apply, every identity and safety predicate is
  revalidated; any mismatch fails closed.
- One approval authorizes one named resource/action, never a wildcard, name match, or newly discovered descendant.
- Results compare pre/post pressure and footprint but never claim all footprint became free RAM.

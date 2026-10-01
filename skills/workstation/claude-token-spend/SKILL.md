---
name: claude-token-spend
description: Report Claude Code token consumption from local session logs - per model, per project, and per token type (input, output, cache read, cache write) over 24h / 7d / 30d / all-time windows. Reads ~/.claude/projects directly, no API key, read-only. Triggers on "my token spend", "token consumption", "how many tokens did I use", "usage per model", "which project burns the most tokens", "ccdash-style report".
compatibility: Requires python3 (stdlib only) and local Claude Code logs in ~/.claude/projects. Read-only. Works in Claude Code and any agent with Bash.
homepage: local
metadata: {"version":"1.0.0","updated":"2026-08-24","author":"gwendall","openclaw":{"requires":{"bins":["python3"]},"emoji":"abacus"}}
---

# claude-token-spend - Token consumption report from local logs

Answer "how many tokens am I burning, on what?" from the machine's own Claude Code
session logs. Produces the same kind of table as third-party dashboards (ccdash,
ccusage): per model over 24h / 7d / 30d / all time, plus per project and per
token type. Everything is local and read-only; no API key, no network.

## TL;DR - the fast path

```bash
python3 scripts/token_spend.py            # human-readable tables
python3 scripts/token_spend.py --json     # machine-readable, exact counts
```

Options: `--root DIR` (default `~/.claude/projects`), `--top-projects N`.

## What the script does

1. Scans every `*.jsonl` under the root. Each assistant message in those session
   files carries a `message.usage` block with `input_tokens`, `output_tokens`,
   `cache_read_input_tokens`, `cache_creation_input_tokens`, plus `message.model`
   and a `timestamp`.
2. **Deduplicates** by `(message.id, requestId)`: resumed and forked sessions
   copy earlier messages into new files, so without this step totals roughly
   double. Expect the "duplicates skipped" count to be of the same order as the
   counted messages; that is normal.
3. Buckets into 24h / 7d / 30d / all-time windows and aggregates by model, by
   project directory, and by token type.

## How to present the results

- Lead with the per-model table, then per-project, then the token-type split.
- Point out that **cache read dominates** (usually >95% of raw volume): it is
  the conversation context re-read on every turn and is billed at roughly one
  tenth of the input price. Raw token totals are NOT proportional to cost.
- If the user asks for cost in dollars, multiply the per-type counts by the
  current per-model prices (check the provider's pricing page or the claude-api
  skill; do not quote prices from memory) using the `--json` output.

## Caveats to state with any report

- **Per machine, not per account**: only sessions run on this machine appear.
- **"All time" is really "since the retention window"**: Claude Code purges old
  session logs (default ~30 days, `cleanupPeriodDays` setting), so all-time
  numbers only cover what is still on disk. The 30d column is the honest one.
- Subagent/sidechain traffic is included as long as it was logged locally.
- Native alternatives: `/usage` (plan limits) and `/cost` (current session)
  inside Claude Code; this skill covers the cross-session history they do not.

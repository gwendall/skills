# Briefing contract

Keep the owner report short. The detailed evidence belongs in private memory.

1. **New:** up to five genuinely new findings with source links and actual dates.
   Distinguish a new publication from an old item discovered for the first time.
2. **Act:** the few useful actions and why, each linked to its evidence. Say whether
   a reply is proposed, drafted or actually sent; monitoring alone sends nothing.
3. **Changed:** compatible metric deltas and baselines, not every unchanged total.
4. **Coverage:** actual checked sources, important gaps and partial conversations.
5. **Memory:** the private report link and whether canonical CRM writes succeeded.

A useful no-change report can be two sentences: no material new finding in the
checked sources, then meaningful traffic changes and source gaps. Do not bury a
source failure under an unqualified no-news claim.

Scheduled delivery depends on the host. If it offers a documented no-notification
result, use it for routine no-change runs and retain a private receipt. Otherwise
return a short result and let the host control its delivery. Do not claim that a
notification was suppressed without evidence.

## Private run receipt

The existing memory can represent this differently. Preserve these meanings:

- run_id, project_id, started_at, finished_at, state
- per source: id, requested_window, status, checked_at, last_successful_at,
  pages_read, remaining_cursor, coverage, error and retry_after when applicable
- findings: provider_id, canonical_url, published_at, first_seen_at, observed_at,
  relation, author evidence, change, reading coverage and evidence reference
- observations_written, tasks_created and actual outbound_actions
- proposed_actions separate from completed actions
- scheduler: execution environment, schedule_id and observed enabled status

Do not write secrets, browser cookies or full private messages into a public
repository or into an unrelated project's report.

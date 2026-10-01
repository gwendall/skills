#!/usr/bin/env bash
# analyze-actions-cost.sh - find where a GitHub Actions bill actually goes.
#
# Reports, per workflow: runs/day, billable minutes per run, jobs per run and an
# estimated monthly cost. Then drills into the most expensive workflow job by job,
# and into its slowest job step by step - which is where the answer usually is
# (setup time dwarfing the actual work).
#
# Billing model this relies on: GitHub bills PER JOB, ROUNDED UP to the minute.
# We therefore compute cost from job start/end times, not from run wall-clock and
# not from /timing (which frequently reports 0 when billing is not finalized, or
# when runs never started because a spending limit blocked them).
#
# Usage:
#   ./analyze-actions-cost.sh <owner>/<repo> [days] [usd_per_minute]
#
#   days             lookback window in days (default 14)
#   usd_per_minute   runner rate (default 0.008 = Linux 2-core, private repo)
#                    Linux 2-core 0.008 | Windows 0.016 | macOS 0.08
#
# Requires: gh (authenticated, read access to the repo), node.
set -euo pipefail

REPO="${1:-}"
DAYS="${2:-14}"
RATE="${3:-0.008}"

if [ -z "$REPO" ]; then
  grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -20
  exit 1
fi

command -v gh   >/dev/null || { echo "gh is required"; exit 1; }
command -v node >/dev/null || { echo "node is required"; exit 1; }

SINCE="$(node -e "const d=new Date(Date.now()-$DAYS*864e5);console.log(d.toISOString().slice(0,10))")"
TMP="$(mktemp -d -t actions-cost-XXXX)"
trap 'rm -rf "$TMP"' EXIT

echo "Repo:   $REPO"
echo "Window: since $SINCE ($DAYS days)   Rate: \$$RATE/min"
echo "Fetching runs..."

# gh --paginate concatenates one JSON object per page; the node side splits them.
gh api --paginate "/repos/$REPO/actions/runs?per_page=100&created=>=$SINCE" \
  > "$TMP/runs.json" 2>/dev/null || { echo "Failed to fetch runs (check repo name and gh auth)"; exit 1; }

export TMP REPO RATE
node <<'NODE'
const {execSync} = require('child_process');
const fs = require('fs');
const {TMP, REPO, RATE} = process.env;
const rate = parseFloat(RATE);

function loadPages(p) {
  const raw = fs.readFileSync(p, 'utf8');
  const out = [];
  for (const chunk of raw.split(/(?<=\})\s*(?=\{"total_count")/)) {
    try { const j = JSON.parse(chunk); if (j.workflow_runs) out.push(...j.workflow_runs); } catch {}
  }
  return out;
}
const gh = (path) => {
  try { return JSON.parse(execSync(`gh api "${path}" 2>/dev/null`, {encoding:'utf8', maxBuffer: 32*1024*1024})); }
  catch { return null; }
};
// Billable minutes for one run: sum over jobs of ceil(duration), min 1 per job.
const runCost = (id) => {
  const j = gh(`/repos/${REPO}/actions/runs/${id}/jobs?per_page=100`);
  if (!j || !j.jobs) return null;
  let min = 0, n = 0;
  for (const job of j.jobs) {
    if (!job.started_at || !job.completed_at) continue;
    const d = (new Date(job.completed_at) - new Date(job.started_at)) / 60000;
    if (d > 0) { min += Math.max(1, Math.ceil(d)); n++; }
  }
  return n ? {min, jobs: n} : null;
};

const runs = loadPages(`${TMP}/runs.json`);
if (!runs.length) { console.log('No runs found in the window.'); process.exit(0); }

const times = runs.map(r => new Date(r.created_at)).sort((a,b) => a-b);
const spanDays = Math.max(0.5, (times[times.length-1] - times[0]) / 864e5);
const capped = runs.length >= 1000;

console.log(`\nRuns fetched: ${runs.length}${capped ? '  (API cap hit - real volume is HIGHER, treat costs as a LOWER BOUND)' : ''}`);
console.log(`Actual span:  ${spanDays.toFixed(1)} days (${times[0].toISOString().slice(0,10)} -> ${times[times.length-1].toISOString().slice(0,10)})`);

// Sample up to 3 completed runs per workflow to get billable minutes/run.
const byWf = {};
for (const r of runs) (byWf[r.name] ||= []).push(r);

const rows = [];
let blocked = 0;
for (const [name, list] of Object.entries(byWf)) {
  // Sample SUCCESSFUL runs only. Runs blocked by a spending limit, cancelled, or
  // failed at startup report ~0 duration and would silently deflate every estimate
  // - which is exactly the situation you are in when investigating a big bill.
  const done = list.filter(r => r.conclusion === 'success');
  blocked += list.length - done.length;
  let min = 0, jobs = 0, n = 0;
  for (const r of done.slice(0, 3)) {
    const c = runCost(r.id);
    if (c) { min += c.min; jobs += c.jobs; n++; }
  }
  const perRun = n ? min/n : 0;
  const perDay = list.length / spanDays;
  rows.push({ name, runs: list.length, perDay, jobs: n ? jobs/n : 0, perRun, monthly: perDay * perRun * rate * 30 });
}
rows.sort((a,b) => b.monthly - a.monthly);

console.log('\n' + 'WORKFLOW'.padEnd(34) + 'RUNS/D'.padStart(7) + 'JOBS'.padStart(6) + 'MIN/RUN'.padStart(9) + '$/MONTH'.padStart(9));
console.log('-'.repeat(65));
let total = 0;
for (const r of rows) {
  total += r.monthly;
  console.log(
    r.name.slice(0,33).padEnd(34) +
    r.perDay.toFixed(1).padStart(7) +
    r.jobs.toFixed(0).padStart(6) +
    r.perRun.toFixed(0).padStart(9) +
    ('$' + r.monthly.toFixed(0)).padStart(9)
  );
}
console.log('-'.repeat(65));
console.log('ESTIMATED TOTAL'.padEnd(56) + ('$' + total.toFixed(0)).padStart(9));
if (blocked) {
  console.log(`\nNote: ${blocked} of ${runs.length} runs were not successful (blocked by a spending`);
  console.log('limit, cancelled, or failed early). They are excluded from the per-run cost');
  console.log('sampling, since they report near-zero duration and would deflate the estimate.');
}

// Drill into the most expensive workflow.
const worst = rows.find(r => r.perRun > 0);
if (!worst) process.exit(0);
const sample = (byWf[worst.name] || []).find(r => r.conclusion === 'success');
if (!sample) process.exit(0);

console.log(`\n=== Most expensive: "${worst.name}" - jobs of run ${sample.id} ===`);
const jr = gh(`/repos/${REPO}/actions/runs/${sample.id}/jobs?per_page=100`);
let slowest = null, billed = 0, real = 0;
for (const job of (jr?.jobs || [])) {
  if (!job.started_at || !job.completed_at) continue;
  const sec = (new Date(job.completed_at) - new Date(job.started_at)) / 1000;
  const m = Math.max(1, Math.ceil(sec/60));
  billed += m; real += sec/60;
  if (!slowest || sec > slowest.sec) slowest = {id: job.id, name: job.name, sec};
  console.log('  ' + job.name.slice(0,44).padEnd(46) + (sec.toFixed(0)+'s').padStart(7) + (m+'min billed').padStart(14));
}
console.log(`  ${'-'.repeat(65)}`);
console.log(`  real ${real.toFixed(1)}min | BILLED ${billed}min | lost to per-job rounding: ${(billed-real).toFixed(1)}min`);

if (slowest) {
  console.log(`\n=== Steps of the slowest job: "${slowest.name}" ===`);
  const jd = gh(`/repos/${REPO}/actions/jobs/${slowest.id}`);
  for (const s of (jd?.steps || [])) {
    if (!s.started_at || !s.completed_at) continue;
    const sec = (new Date(s.completed_at) - new Date(s.started_at)) / 1000;
    console.log('  ' + s.name.slice(0,50).padEnd(52) + (sec.toFixed(0)+'s').padStart(8));
  }
  console.log('\n  Read this table for the setup-to-work ratio: if checkout + install');
  console.log('  dwarf the step that does the real work, scope the install and collapse');
  console.log('  the matrix (see SKILL.md, steps 2.1 and 2.2).');
}
NODE

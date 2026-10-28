#!/bin/bash
# mac-for-agents.sh - what macOS file indexing costs while coding agents rewrite
# thousands of files, and the one setting that stops it. Read-only: no sudo, no
# plist edits, nothing changes unless you click it yourself in System Settings.
#
#   mac-for-agents.sh report                 what is indexed, what it costs right now
#   mac-for-agents.sh measure before [min]   sample every 10 s into before.csv (default 10 min)
#   mac-for-agents.sh fix                    open Spotlight settings and show your code folders
#   mac-for-agents.sh measure after [min]    same sampling, after the change
#   mac-for-agents.sh compare                before.csv vs after.csv
#
# Code folders: CODE_DIRS="~/code ~/work", else the usual names under $HOME.
set -u

HEADER="label,epoch,load1,mds_cpu,mds_mb,fseventsd_cpu,fseventsd_mb,mdworkers,agents_cli"

code_dirs() {
  if [ -n "${CODE_DIRS:-}" ]; then
    for d in $CODE_DIRS; do echo "${d/#\~/$HOME}"; done
  else
    for d in code Code src dev Developer project projects work repo repos git; do
      [ -d "$HOME/$d" ] && echo "$HOME/$d"
    done
  fi
  return 0
}

# One line of cost: load, Spotlight (mds, mds_stores, mdworker*), FSEvents (fseventsd), agent CLIs.
sample() {
  ps -Ao pid=,%cpu=,rss=,comm= | awk -v label="$1" -v now="$(date +%s)" -v load="$(sysctl -n vm.loadavg | awk '{print $2}')" '
    { name=$4; sub(/.*\//, "", name) }
    name ~ /^(mds|mds_stores|mdworker_shared|mdworker)$/ { mc+=$2; mm+=$3; if (name ~ /^mdworker/) w++ }
    name == "fseventsd" { fc+=$2; fm+=$3 }
    name ~ /^(claude|codex|cursor-agent|aider|gemini|opencode)$/ { a++ }
    END { printf "%s,%s,%s,%.1f,%d,%.1f,%d,%d,%d\n", label, now, load, mc, mm/1024, fc, fm/1024, w, a }'
}

summary() {
  [ -f "$1" ] || { echo "$1: missing (run: $0 measure ${1%.csv})"; return 0; }
  awk -F, 'NR>1 { n++; label=$1; l+=$3; mc+=$4; mm+=$5; fc+=$6; fm+=$7; a+=$9; if ($4>pk) pk=$4 }
    END { if (!n) { print "no samples"; exit }
      printf "%-7s %3d samples | load %5.1f | Spotlight CPU %4.0f%% (peak %4.0f%%) mem %5.0f MB | fseventsd CPU %4.0f%% mem %6.0f MB | agent CLIs %4.1f\n",
        label, n, l/n, mc/n, pk, mm/n, fc/n, fm/n, a/n }' "$1"
}

command="${1:-report}"
if [ "$command" != compare ] && [ "$(uname -s)" != Darwin ]; then
  echo "macOS only: Spotlight and fseventsd are macOS services." >&2; exit 1
fi

case "$command" in
  report)
    echo "== Spotlight"
    mdutil -s / 2>/dev/null | sed -n '2p' | sed 's/^[[:space:]]*/  boot volume: /'
    for d in $(code_dirs); do
      pj=$(mdfind -count -onlyin "$d" 'kMDItemFSName == "package.json"' 2>/dev/null || echo "?")
      nm=$(mdfind -count -onlyin "$d" 'kMDItemFSName == "node_modules"' 2>/dev/null || echo "?")
      wt=$(find "$d" -maxdepth 4 -type d -path '*/.claude/worktrees/*' -prune 2>/dev/null | wc -l | tr -d ' ')
      if [ "$pj" = 0 ] && [ "$nm" = 0 ]; then state="not indexed (good)"; else state="INDEXED: $pj package.json, $nm node_modules"; fi
      echo "  $d: $state; agent worktrees (.claude/worktrees): $wt"
    done
    echo "== Cost right now"
    now=$(mktemp)
    { echo "$HEADER"; sample now; } > "$now"
    summary "$now"
    rm -f "$now"
    echo "== Memory"
    echo "  swap: $(sysctl -n vm.swapusage)"
    memory_pressure 2>/dev/null | tail -n 1 | sed 's/^/  /'
    echo "== Time Machine"
    if tmutil destinationinfo 2>&1 | grep -q 'No destinations'; then
      echo "  no destination configured, nothing to exclude"
    else
      echo "  a destination is set: 'tmutil addexclusion <dir>/node_modules' keeps dependencies out of backups (no sudo)"
    fi
    echo "== Open files limit (file watchers hit EMFILE first)"
    launchctl limit maxfiles | sed 's/^[[:space:]]*/  /'
    ;;
  measure)
    label=${2:-run}; minutes=${3:-10}; out="$label.csv"
    end=$(( $(date +%s) + minutes * 60 ))
    echo "$HEADER" > "$out"
    echo "sampling every 10 s for $minutes min into $out (keep your agents working as usual)"
    while [ "$(date +%s)" -lt "$end" ]; do sample "$label" >> "$out"; sleep 10; done
    summary "$out"
    ;;
  fix)
    echo "Spotlight's privacy list is the supported switch: folders in it are not indexed,"
    echo "and their entries leave the index. In System Settings > Spotlight, open the privacy"
    echo "list (Search Privacy on older macOS) and add each code folder with + or by dragging it:"
    for d in $(code_dirs); do echo "  $d"; done
    open "x-apple.systempreferences:com.apple.Spotlight-Settings.extension" 2>/dev/null \
      || open "x-apple.systempreferences:com.apple.preference.spotlight?Privacy"
    first=$(code_dirs | head -n 1)
    if [ -n "$first" ]; then open -R "$first"; fi
    echo "Then check: $0 report (the folder should read 'not indexed')."
    ;;
  compare)
    summary before.csv; summary after.csv
    ;;
  *) sed -n '2,12p' "$0" ;;
esac

#!/usr/bin/env bash
# Read-only inventory for a repository that will host concurrent coding agents.
# Usage: audit-repo.sh [repository-path] [owner/repository]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib/repo.sh"

TARGET="${1:-.}"
REPO_HINT="${2:-}"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Not a git repository: $TARGET" >&2
  exit 1
}
cd "$ROOT"

BRANCH="$(git branch --show-current)"
DEFAULT_BRANCH="$(detect_default_branch "$ROOT" || true)"
[ -n "$DEFAULT_BRANCH" ] || DEFAULT_BRANCH="unknown"

GIT_DIR="$(git rev-parse --git-dir)"
COMMON_DIR="$(git rev-parse --git-common-dir)"
if [ "$GIT_DIR" = "$COMMON_DIR" ]; then
  WORKTREE_KIND="primary checkout"
else
  WORKTREE_KIND="linked worktree"
fi

WORKTREE_COUNT="$(git worktree list --porcelain | awk '/^worktree / {n++} END {print n+0}')"
DIRTY_COUNT="$(git status --porcelain | awk 'END {print NR+0}')"
AGENTS_COUNT="$(find "$ROOT" \( -type d -name .git -o -type d -name node_modules -o -type d -name .next \) -prune -o -type f -name AGENTS.md -print | awk 'END {print NR+0}')"

if [ -f .github/CODEOWNERS ] || [ -f CODEOWNERS ] || [ -f docs/CODEOWNERS ]; then
  CODEOWNERS="present"
else
  CODEOWNERS="absent"
fi

REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
REPO_SLUG="$REPO_HINT"
if [ -z "$REPO_SLUG" ]; then
  case "$REMOTE_URL" in
    https://github.com/*) REPO_SLUG="${REMOTE_URL#https://github.com/}" ;;
    git@github.com:*) REPO_SLUG="${REMOTE_URL#git@github.com:}" ;;
  esac
  REPO_SLUG="${REPO_SLUG%.git}"
fi

WORKFLOW_COUNT=0
PR_WORKFLOWS=0
PATH_FILTER_WORKFLOWS=0
SCHEDULED_WORKFLOWS=0
CONCURRENCY_WORKFLOWS=0
MERGE_GROUP_WORKFLOWS=0
STATIC_CONCURRENCY_WORKFLOWS=0
STATIC_PR_CONCURRENCY_WORKFLOWS=0
NO_VALIDATION_PR_WORKFLOWS=0
PREMIUM_RUNNER_REFS=0
UNPINNED_ACTION_REFS=0

shopt -s nullglob
WORKFLOWS=(.github/workflows/*.yml .github/workflows/*.yaml)
shopt -u nullglob
WORKFLOW_COUNT="${#WORKFLOWS[@]}"

if [ "$WORKFLOW_COUNT" -gt 0 ]; then
for workflow in "${WORKFLOWS[@]}"; do
  IS_PR="false"
  if grep -Eq '^[[:space:]]*pull_request:' "$workflow"; then
    IS_PR="true"
    PR_WORKFLOWS=$((PR_WORKFLOWS + 1))
  fi
  grep -Eq '^[[:space:]]*paths(-ignore)?:' "$workflow" && PATH_FILTER_WORKFLOWS=$((PATH_FILTER_WORKFLOWS + 1)) || true
  grep -Eq '^[[:space:]]*schedule:' "$workflow" && SCHEDULED_WORKFLOWS=$((SCHEDULED_WORKFLOWS + 1)) || true
  grep -Eq '^concurrency:|^[[:space:]]+concurrency:' "$workflow" && CONCURRENCY_WORKFLOWS=$((CONCURRENCY_WORKFLOWS + 1)) || true
  grep -Eq '^[[:space:]]*merge_group:' "$workflow" && MERGE_GROUP_WORKFLOWS=$((MERGE_GROUP_WORKFLOWS + 1)) || true

  static_concurrency="$(awk '
    /^concurrency:[[:space:]]*/ {
      value=$0
      sub(/^concurrency:[[:space:]]*/, "", value)
      sub(/[[:space:]]*#.*/, "", value)
      if (length(value) > 0 && index(value, "${{") == 0) static=1
      in_concurrency=(length(value) == 0)
      next
    }
    in_concurrency && /^[^[:space:]#]/ { in_concurrency=0 }
    in_concurrency && /^[[:space:]]+group:[[:space:]]*/ {
      value=$0
      sub(/^[[:space:]]+group:[[:space:]]*/, "", value)
      sub(/[[:space:]]*#.*/, "", value)
      if (length(value) > 0 && index(value, "${{") == 0) static=1
    }
    END { print static+0 }
  ' "$workflow")"
  if [ "$static_concurrency" -eq 1 ]; then
    STATIC_CONCURRENCY_WORKFLOWS=$((STATIC_CONCURRENCY_WORKFLOWS + 1))
    [ "$IS_PR" = "true" ] && STATIC_PR_CONCURRENCY_WORKFLOWS=$((STATIC_PR_CONCURRENCY_WORKFLOWS + 1))
  fi

  if [ "$IS_PR" = "true" ] && ! grep -Eq '^[[:space:]]+run:' "$workflow"; then
    if ! grep -E 'uses:[[:space:]]+[^ #]+' "$workflow" | grep -Evq 'uses:[[:space:]]+actions/checkout@'; then
      NO_VALIDATION_PR_WORKFLOWS=$((NO_VALIDATION_PR_WORKFLOWS + 1))
    fi
  fi

  count="$(grep -Ec 'runs-on:.*(gpu|macos[^[:space:]]*(large|xlarge)|[4-9][0-9]-core)' "$workflow" || true)"
  PREMIUM_RUNNER_REFS=$((PREMIUM_RUNNER_REFS + count))
  count="$(grep -Eo 'uses:[[:space:]]+[^ #]+' "$workflow" | awk '{ref=$2; if (ref !~ /^\.\// && ref !~ /^docker:\/\// && ref !~ /@[0-9a-f]{40}$/) n++} END {print n+0}' || true)"
  UNPINNED_ACTION_REFS=$((UNPINNED_ACTION_REFS + count))
done
fi

echo "# Multi-agent repository audit"
echo
echo "## Local repository"
echo
echo "- Root: \`$ROOT\`"
echo "- Branch: \`${BRANCH:-detached}\`"
echo "- Default branch: \`$DEFAULT_BRANCH\`"
echo "- Checkout: $WORKTREE_KIND"
echo "- Registered worktrees: $WORKTREE_COUNT"
echo "- Dirty entries in target checkout: $DIRTY_COUNT"
echo "- AGENTS.md files: $AGENTS_COUNT"
echo "- CODEOWNERS: $CODEOWNERS"
echo
echo "## CI inventory"
echo
echo "- Workflow files: $WORKFLOW_COUNT"
echo "- Pull-request workflows: $PR_WORKFLOWS"
echo "- Workflows containing path filters: $PATH_FILTER_WORKFLOWS"
echo "- Scheduled workflows: $SCHEDULED_WORKFLOWS"
echo "- Workflows declaring concurrency: $CONCURRENCY_WORKFLOWS"
echo "- Workflows with a static repository-wide concurrency group: $STATIC_CONCURRENCY_WORKFLOWS"
echo "- Pull-request workflows with a static concurrency group: $STATIC_PR_CONCURRENCY_WORKFLOWS"
echo "- Workflows declaring merge_group: $MERGE_GROUP_WORKFLOWS"
echo "- Pull-request workflows with no apparent validation step: $NO_VALIDATION_PR_WORKFLOWS"
echo "- Premium-runner references: $PREMIUM_RUNNER_REFS"
echo "- External action uses not pinned to a full SHA: $UNPINNED_ACTION_REFS"

PROTECTION="unknown"
REQUIRED_CHECKS="unknown"
STRICT="unknown"

if [ -n "$REPO_SLUG" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  echo
  echo "## GitHub"
  echo
  echo "- Repository: \`$REPO_SLUG\`"
  INFO="$(gh api "repos/$REPO_SLUG" --jq '[.visibility,.default_branch,(.allow_auto_merge|tostring),(.delete_branch_on_merge|tostring),.owner.login] | @tsv' 2>/dev/null || true)"
  if [ -n "$INFO" ]; then
    OLD_IFS="$IFS"; IFS=$'\t'; set -- $INFO; IFS="$OLD_IFS"
    echo "- Visibility: $1"
    echo "- API default branch: \`$2\`"
    echo "- Auto-merge enabled: $3"
    echo "- Delete branch on merge: $4"
    OWNER="$5"
  else
    OWNER="${REPO_SLUG%%/*}"
    echo "- Repository settings: inaccessible"
  fi

  if PROTECTION_INFO="$(gh api "repos/$REPO_SLUG/branches/$DEFAULT_BRANCH/protection" --jq '[([.required_status_checks.contexts[]?, .required_status_checks.checks[]?.context] | unique | length), (.required_status_checks.strict // false)] | @tsv' 2>/dev/null)"; then
    PROTECTION="present"
    OLD_IFS="$IFS"; IFS=$'\t'; set -- $PROTECTION_INFO; IFS="$OLD_IFS"
    REQUIRED_CHECKS="$1"
    STRICT="$2"
    echo "- Branch protection: present"
    echo "- Required status checks: $REQUIRED_CHECKS"
    echo "- Strict up-to-date checks: $STRICT"
  else
    PROTECTION="absent or inaccessible"
    echo "- Branch protection: $PROTECTION"
  fi

  RULESETS="$(gh api "repos/$REPO_SLUG/rulesets" --jq 'length' 2>/dev/null || echo inaccessible)"
  echo "- Repository rulesets: $RULESETS"
  ACTIONS="$(gh api "repos/$REPO_SLUG/actions/permissions" --jq '[.enabled,(.allowed_actions // "unknown"),(.sha_pinning_required // false)] | @tsv' 2>/dev/null || true)"
  if [ -n "$ACTIONS" ]; then
    OLD_IFS="$IFS"; IFS=$'\t'; set -- $ACTIONS; IFS="$OLD_IFS"
    echo "- Actions enabled: $1"
    echo "- Allowed actions: $2"
    echo "- SHA pinning required: $3"
  fi

  PLAN="$(gh api "orgs/$OWNER" --jq '.plan.name // empty' 2>/dev/null || true)"
  [ -n "$PLAN" ] && echo "- Owner plan: $PLAN"
  BUDGET="$(gh api -H 'X-GitHub-Api-Version: 2026-03-10' "organizations/$OWNER/settings/billing/budgets?per_page=100" --jq '.budgets[] | select(.budget_product_sku == "actions") | "\(.budget_amount) USD, hard-stop=\(.prevent_further_usage)"' 2>/dev/null || true)"
  [ -n "$BUDGET" ] && echo "- Actions budget: $BUDGET"
else
  echo
  echo "## GitHub"
  echo
  echo "- Skipped: no GitHub repository slug or authenticated gh CLI"
fi

echo
echo "## Findings to resolve"
echo
FINDINGS=0
finding() { echo "- $1"; FINDINGS=$((FINDINGS + 1)); }

[ "$WORKTREE_KIND" = "primary checkout" ] && finding "This is the primary checkout; launch concurrent tasks in linked worktrees."
[ "$WORKTREE_KIND" = "linked worktree" ] && [ "${BRANCH:-}" = "$DEFAULT_BRANCH" ] && finding "This task worktree is on the default branch."
[ "$AGENTS_COUNT" -eq 0 ] && finding "No repository agent contract was found."
[ "$WORKFLOW_COUNT" -gt 0 ] && [ "$CONCURRENCY_WORKFLOWS" -eq 0 ] && finding "No workflow declares concurrency; stale agent pushes may run in parallel."
[ "$STATIC_PR_CONCURRENCY_WORKFLOWS" -gt 0 ] && finding "$STATIC_PR_CONCURRENCY_WORKFLOWS pull-request workflows use a static repository-wide concurrency group; unrelated pull requests may serialize or cancel each other."
[ "$NO_VALIDATION_PR_WORKFLOWS" -gt 0 ] && finding "$NO_VALIDATION_PR_WORKFLOWS pull-request workflows contain no apparent validation beyond checkout."
[ "$PROTECTION" = "absent or inaccessible" ] && finding "Default-branch protection is absent or inaccessible with the current GitHub identity."
[ "$PROTECTION" = "unknown" ] && finding "Default-branch protection was not verified; inspect the repository host before rollout."
[ "$REQUIRED_CHECKS" = "0" ] && finding "Branch protection has no required status checks."
[ "$STRICT" = "true" ] && finding "Strict up-to-date checks can cause repeated qualification in a busy repository."
[ "$PREMIUM_RUNNER_REFS" -gt 0 ] && finding "Premium runners exist; verify explicit qualification triggers, timeouts, and spend authority."
[ "$UNPINNED_ACTION_REFS" -gt 0 ] && finding "$UNPINNED_ACTION_REFS external action uses are not pinned to full SHAs (supply-chain hygiene)."

if [ "$FINDINGS" -eq 0 ]; then
  echo "- No obvious structural gaps found by the lightweight audit. Review semantics manually."
fi

echo
echo "This audit is read-only and intentionally conservative. Validate workflow semantics and identity separation before changing protections."

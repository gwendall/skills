#!/usr/bin/env bash
# Create one new branch and linked worktree for an authorized agent task.
# Usage: create-agent-worktree.sh [--porcelain] TASK-ID [base-ref] [destination-parent]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib/repo.sh"

PORCELAIN="false"
if [ "${1:-}" = "--porcelain" ]; then
  PORCELAIN="true"
  shift
fi

TASK_ID="${1:-}"
BASE_REF="${2:-}"
DESTINATION_PARENT="${3:-}"
BRANCH_PREFIX="${AGENT_BRANCH_PREFIX:-agent}"

if [ -z "$TASK_ID" ]; then
  echo "Usage: $0 [--porcelain] TASK-ID [base-ref] [destination-parent]" >&2
  exit 1
fi

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Run this command from the target git repository." >&2
  exit 1
}

case "$BRANCH_PREFIX" in
  *..*|/*|*/|*[!A-Za-z0-9._/-]*) echo "Unsafe AGENT_BRANCH_PREFIX: $BRANCH_PREFIX" >&2; exit 1 ;;
esac

SLUG="$(printf '%s' "$TASK_ID" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//')"
if [ -z "$SLUG" ] || [ "$SLUG" = "." ] || [ "$SLUG" = ".." ]; then
  echo "TASK-ID does not produce a safe branch name: $TASK_ID" >&2
  exit 1
fi

if [ -z "$BASE_REF" ]; then
  BASE_REF="$(detect_default_ref "$ROOT" || true)"
  if [ -z "$BASE_REF" ]; then
    echo "Cannot resolve the default ref; set AGENT_DEFAULT_REF or pass base-ref." >&2
    exit 1
  fi
  for remote in $(git -C "$ROOT" remote); do
    case "$BASE_REF" in
      "$remote"/*)
        git -C "$ROOT" fetch "$remote" "${BASE_REF#*/}"
        BASE_REF="$remote/${BASE_REF#*/}"
        break
        ;;
    esac
  done
fi

git rev-parse --verify "$BASE_REF^{commit}" >/dev/null 2>&1 || {
  echo "Base ref is not a commit: $BASE_REF" >&2
  exit 1
}

BRANCH="$BRANCH_PREFIX/$SLUG"
git check-ref-format --branch "$BRANCH" >/dev/null 2>&1 || {
  echo "TASK-ID and prefix do not produce a valid branch name: $BRANCH" >&2
  exit 1
}
if git show-ref --verify --quiet "refs/heads/$BRANCH" || git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  echo "Branch already exists: $BRANCH" >&2
  exit 1
fi

if [ -z "$DESTINATION_PARENT" ]; then
  DESTINATION_PARENT="$(dirname "$ROOT")/$(basename "$ROOT")-worktrees"
fi
mkdir -p "$DESTINATION_PARENT"
DESTINATION_PARENT="$(cd "$DESTINATION_PARENT" && pwd)"
DESTINATION="$DESTINATION_PARENT/$SLUG"

if [ -e "$DESTINATION" ]; then
  echo "Destination already exists: $DESTINATION" >&2
  exit 1
fi

if [ "$PORCELAIN" = "true" ]; then
  git -C "$ROOT" worktree add --quiet "$DESTINATION" -b "$BRANCH" "$BASE_REF"
  printf '%s\n' "$DESTINATION"
else
  git -C "$ROOT" worktree add "$DESTINATION" -b "$BRANCH" "$BASE_REF"
  echo
  echo "Created agent task worktree"
  echo "  task:   $TASK_ID"
  echo "  branch: $BRANCH"
  echo "  base:   $(git -C "$DESTINATION" rev-parse HEAD)"
  echo "  path:   $DESTINATION"
  echo
  echo "Start the agent with cwd=$DESTINATION"
fi

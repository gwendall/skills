#!/usr/bin/env bash
# Verify that an agent starts from an isolated non-default worktree.
# Usage: agent-preflight.sh [repository-path] [--require-clean]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib/repo.sh"

TARGET="."
MODE=""
PATH_SET="false"
for argument in "$@"; do
  case "$argument" in
    --require-clean) MODE="--require-clean" ;;
    --*) echo "Unknown option: $argument" >&2; exit 1 ;;
    *)
      if [ "$PATH_SET" = "true" ]; then
        echo "Only one repository path may be provided." >&2
        exit 1
      fi
      TARGET="$argument"
      PATH_SET="true"
      ;;
  esac
done

ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Not a git repository: $TARGET" >&2
  exit 1
}
cd "$ROOT"

BRANCH="$(git branch --show-current)"
if [ -z "$BRANCH" ]; then
  echo "FAIL: detached HEAD; use a task branch." >&2
  exit 1
fi

DEFAULT_BRANCH="$(detect_default_branch "$ROOT" || true)"
if [ -z "$DEFAULT_BRANCH" ]; then
  echo "FAIL: cannot determine the default branch; set AGENT_DEFAULT_BRANCH." >&2
  exit 1
fi

if [ "$BRANCH" = "$DEFAULT_BRANCH" ]; then
  echo "FAIL: current branch is the default branch '$DEFAULT_BRANCH'." >&2
  exit 1
fi

GIT_DIR="$(git rev-parse --git-dir)"
COMMON_DIR="$(git rev-parse --git-common-dir)"
if [ "$GIT_DIR" = "$COMMON_DIR" ]; then
  echo "FAIL: this is the primary checkout, not a linked task worktree." >&2
  exit 1
fi

if [ "$MODE" = "--require-clean" ] && [ -n "$(git status --porcelain)" ]; then
  echo "FAIL: the new task worktree is not clean." >&2
  git status --short >&2
  exit 1
fi

echo "agent preflight: OK"
echo "  root:   $ROOT"
echo "  branch: $BRANCH"
echo "  head:   $(git rev-parse HEAD)"
echo "  type:   linked worktree"
if [ ! -f AGENTS.md ]; then
  echo "  note:   no root AGENTS.md found"
fi

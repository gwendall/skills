#!/usr/bin/env bash
# Print the immutable revision context to record before qualification.
# Usage: qualification-context.sh [repository-path]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib/repo.sh"

TARGET="${1:-.}"
ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Not a git repository: $TARGET" >&2
  exit 1
}
DEFAULT_REF="$(detect_default_ref "$ROOT" || true)"
if [ -z "$DEFAULT_REF" ]; then
  echo "Cannot resolve the default ref; set AGENT_DEFAULT_REF to a commit-bearing ref." >&2
  exit 1
fi

QUALIFIED_HEAD="$(git -C "$ROOT" rev-parse HEAD)"
QUALIFIED_BASE="$(git -C "$ROOT" merge-base HEAD "$DEFAULT_REF")" || {
  echo "No merge base between HEAD and $DEFAULT_REF." >&2
  exit 1
}

echo "QUALIFIED_DEFAULT_REF=$DEFAULT_REF"
echo "QUALIFIED_BASE=$QUALIFIED_BASE"
echo "QUALIFIED_HEAD=$QUALIFIED_HEAD"

#!/usr/bin/env bash
# eas-build-clean.sh - work around EAS Build's 2 GB archive limit in a large monorepo.
#
# WHY: EAS uploads the working tree + the repo's .git. In a big monorepo the .git
# can be > 1 GB (large binaries committed in history/HEAD across sibling apps),
# and .git CANNOT be excluded via .easignore -> archive > 2 GB -> upload fails.
#
# THIS SCRIPT: builds from a CLEAN CONTEXT (git archive -> no heavy .git, and
# large media dropped via .gitattributes export-ignore) with a fresh tiny .git.
# Non-destructive: never touches your repo. Run it from the app directory that
# holds eas.json.
#
# DURABLE FIX (team decision): strip large media out of git history
# (git-filter-repo / BFG + Git LFS); then EAS builds from the normal repo and
# this script becomes unnecessary.
#
# Usage (from the app dir, next to eas.json):
#   ./eas-build-clean.sh [development|preview|production]
set -euo pipefail

PROFILE="${1:-development}"
APP_DIR="$(pwd)"
MONO_ROOT="$(git rev-parse --show-toplevel)"
APP_REL="$(git rev-parse --show-prefix)"   # app path relative to the repo root
WORK="$(mktemp -d -t eas-clean-XXXX)"

echo "[clean-build] repo:    $MONO_ROOT"
echo "[clean-build] app:     $APP_REL"
echo "[clean-build] context: $WORK  (profile: $PROFILE)"

# 1) Clean copy via git archive (drops .git + media honored by .gitattributes export-ignore)
git -C "$MONO_ROOT" archive HEAD --format=tar | tar -x -C "$WORK"

# 2) Fresh, tiny .git (single commit)
git -C "$WORK" init -q
git -C "$WORK" add -A
git -C "$WORK" -c user.email=build@local -c user.name=eas-build commit -q -m "eas clean build context"

# 3) node_modules (needed for the expo-dev-client check; excluded from the upload via .gitignore)
( cd "$WORK" && pnpm install --ignore-scripts )

# 4) EAS build from the clean context
( cd "$WORK/$APP_REL" && eas build --profile "$PROFILE" --platform ios --non-interactive )

echo "[clean-build] done. Context: $WORK  (remove with: rm -rf $WORK)"

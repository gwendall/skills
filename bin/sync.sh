#!/usr/bin/env bash
# Symlink every skill in this repo (skills/<category>/<skill>) into ~/.claude/skills/ (idempotent).
# Replaces manual `ln -s`. Never clobbers a real directory without warning.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.claude/skills"
mkdir -p "$DEST"

for skill_md in "$REPO"/skills/*/*/SKILL.md; do
  [ -e "$skill_md" ] || continue
  sd="$(dirname "$skill_md")"
  name="$(basename "$sd")"
  link="$DEST/$name"

  if [ -L "$link" ]; then
    cur="$(readlink "$link")"
    if [ "$cur" = "$sd" ]; then
      echo "ok      $name (already linked)"
    else
      echo "relink  $name ($cur -> $sd)"
      rm "$link" && ln -s "$sd" "$link"
    fi
  elif [ -e "$link" ]; then
    echo "SKIP    $name: $link exists and is NOT a symlink (fix by hand)"
  else
    echo "link    $name"
    ln -s "$sd" "$link"
  fi
done

echo
echo "Sync done. Contents of $DEST:"
ls -la "$DEST"

#!/usr/bin/env bash

# Print the remote-tracking default ref, or return 1 when none is resolvable.
detect_remote_default_ref() {
  local repository="${1:-.}"
  local default_ref
  local remote

  default_ref="$(git -C "$repository" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -n "$default_ref" ] && git -C "$repository" rev-parse --verify "$default_ref^{commit}" >/dev/null 2>&1; then
    printf '%s\n' "$default_ref"
    return 0
  fi

  for remote in $(git -C "$repository" remote); do
    [ "$remote" = "origin" ] && continue
    default_ref="$(git -C "$repository" symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null || true)"
    if [ -n "$default_ref" ] && git -C "$repository" rev-parse --verify "$default_ref^{commit}" >/dev/null 2>&1; then
      printf '%s\n' "$default_ref"
      return 0
    fi
  done

  return 1
}

# Print the repository's default branch, or return 1 when it cannot be inferred.
detect_default_branch() {
  local repository="${1:-.}"
  local default_ref

  if [ -n "${AGENT_DEFAULT_BRANCH:-}" ]; then
    printf '%s\n' "$AGENT_DEFAULT_BRANCH"
    return 0
  fi

  default_ref="$(detect_remote_default_ref "$repository" || true)"
  if [ -n "$default_ref" ]; then
    printf '%s\n' "${default_ref#*/}"
    return 0
  fi

  if git -C "$repository" show-ref --verify --quiet refs/remotes/origin/main || git -C "$repository" show-ref --verify --quiet refs/heads/main; then
    printf '%s\n' main
    return 0
  fi
  if git -C "$repository" show-ref --verify --quiet refs/remotes/origin/master || git -C "$repository" show-ref --verify --quiet refs/heads/master; then
    printf '%s\n' master
    return 0
  fi

  return 1
}

# Print a resolvable default-branch ref, including its remote when available.
detect_default_ref() {
  local repository="${1:-.}"
  local default_branch
  local default_ref
  local remote

  if [ -n "${AGENT_DEFAULT_REF:-}" ]; then
    git -C "$repository" rev-parse --verify "$AGENT_DEFAULT_REF^{commit}" >/dev/null 2>&1 || return 1
    printf '%s\n' "$AGENT_DEFAULT_REF"
    return 0
  fi

  default_ref="$(detect_remote_default_ref "$repository" || true)"
  if [ -n "$default_ref" ]; then
    printf '%s\n' "$default_ref"
    return 0
  fi

  default_branch="$(detect_default_branch "$repository" || true)"
  [ -n "$default_branch" ] || return 1

  if git -C "$repository" rev-parse --verify "origin/$default_branch^{commit}" >/dev/null 2>&1; then
    printf '%s\n' "origin/$default_branch"
    return 0
  fi
  for remote in $(git -C "$repository" remote); do
    [ "$remote" = "origin" ] && continue
    if git -C "$repository" rev-parse --verify "$remote/$default_branch^{commit}" >/dev/null 2>&1; then
      printf '%s\n' "$remote/$default_branch"
      return 0
    fi
  done
  if git -C "$repository" rev-parse --verify "$default_branch^{commit}" >/dev/null 2>&1; then
    printf '%s\n' "$default_branch"
    return 0
  fi

  return 1
}

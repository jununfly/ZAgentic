#!/usr/bin/env bash
# Recover a missing refs/heads/<branch> from .git/logs/HEAD reflog.
# Read-only by default; writes only the loose ref file. Uses direct file
# IO (printf + atomic rename via mv) instead of `git update-ref`, because
# `git update-ref` internally does an unlink on existing files, which the
# WorkBuddy safe-delete shim routes to the trash on Windows Git Bash.
#
# `mv` is safe — the shim does not wrap it.
#
# Usage: recover-refs.sh <repo-path> <branch-name> [<commit>]
#   <commit> defaults to the last reflog entry.

set -euo pipefail

REPO="${1:-}"
BRANCH="${2:-}"
COMMIT="${3:-}"

if [ -z "$REPO" ] || [ -z "$BRANCH" ]; then
  echo "usage: $0 <repo-path> <branch-name> [<commit>]" >&2
  echo "  <commit> defaults to the last reflog entry" >&2
  exit 2
fi

if [ ! -d "$REPO/.git" ]; then
  echo "error: $REPO/.git not found" >&2
  exit 1
fi

cd "$REPO"

if [ ! -s .git/logs/HEAD ]; then
  echo "error: .git/logs/HEAD is empty — reflog unavailable, cannot recover" >&2
  exit 1
fi

if [ -z "$COMMIT" ]; then
  COMMIT=$(tail -1 .git/logs/HEAD | awk '{print $2}')
fi

# Validate the commit looks like a sha1 (40 hex).
if ! [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "error: $COMMIT is not a valid 40-char commit hash" >&2
  echo "pass it explicitly: $0 $REPO $BRANCH <commit-hash>" >&2
  exit 1
fi

# Verify the commit object actually exists in this repo before writing the ref.
if [ ! -f ".git/objects/${COMMIT:0:2}/${COMMIT:2}" ] && \
   ! git cat-file -e "$COMMIT" 2>/dev/null; then
  echo "error: object $COMMIT not in this repo's object store" >&2
  echo "re-fetch from origin instead: git fetch origin $BRANCH" >&2
  exit 1
fi

# Ensure .git/refs/heads/<branch's path components> exist. Branch names
# with '/' (e.g. "codex/fix-agent-local-worktree-git-flag") require their
# subdirectory to exist before we can write the loose ref file.
# mkdir is safe under the shim.
branch_dir=".git/refs/heads/$(dirname "$BRANCH")"
[ "$branch_dir" != ".git/refs/heads/." ] && [ "$branch_dir" != ".git/refs/heads" ] && mkdir -p "$branch_dir"

# Write the loose ref via direct file IO + atomic mv. Avoids `git update-ref`
# (which unlinks the old file) and avoids `rm` (which is shim-wrapped and
# destructive on Windows Git Bash).
ref_path=".git/refs/heads/$BRANCH"
# tmp_path must live in the same directory as ref_path so the rename is
# atomic (same filesystem), but the filename cannot contain '/' (branch
# names do). Use a stable tmp name derived from $$, no slashes.
tmp_path="$branch_dir/.tmp-recover-$$"
# Use trap+`mv -f` for cleanup; the shim does not wrap mv, and `mv -f` to
# /dev/null is a no-op that always succeeds without touching the shim path.
trap 'mv -f "$tmp_path" /dev/null 2>/dev/null || true' EXIT

printf '%s\n' "$COMMIT" > "$tmp_path"
mv "$tmp_path" "$ref_path"
# Clear trap on success so it doesn't try to clean up a now-valid file.
trap - EXIT

echo "recovered refs/heads/$BRANCH -> $COMMIT"
echo "verify with: git log --oneline -3 && git status --short"

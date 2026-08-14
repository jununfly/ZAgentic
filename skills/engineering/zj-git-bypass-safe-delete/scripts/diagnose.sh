#!/usr/bin/env bash
# Diagnose WorkBuddy safe-delete shim corruption in a git repository.
# Read-only: does not modify .git/ or working tree.
#
# Usage: diagnose.sh <repo-path>
# Output: a one-screen report. Red lines indicate a likely shim symptom.

set -uo pipefail

REPO="${1:-}"
if [ -z "$REPO" ] || [ ! -d "$REPO/.git" ]; then
  echo "usage: $0 <repo-path>" >&2
  echo "  <repo-path> must be a directory containing .git/" >&2
  exit 2
fi

cd "$REPO" || exit 1

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
gray()  { printf '\033[90m%s\033[0m\n' "$*"; }
hdr()   { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

hdr "shim in scope"
if [[ "${NODE_OPTIONS:-}" == *genie-safe-delete* ]]; then
  red "  WorkBuddy safe-delete shim IS active in this shell"
  red "  git operations that touch .git/refs/ may silently lose files"
else
  green "  shim not in scope (NODE_OPTIONS clean)"
fi

hdr ".git/ structure"
for d in refs refs/heads refs/tags refs/remotes; do
  if [ -d ".git/$d" ]; then
    n=$(find ".git/$d" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
    gray "  .git/$d exists ($n entries)"
  else
    red "  .git/$d MISSING — git may report 'not a git repository'"
  fi
done

hdr "HEAD"
if [ ! -f .git/HEAD ]; then
  red "  .git/HEAD missing"
else
  head_ref=$(cat .git/HEAD)
  gray "  $head_ref"
  case "$head_ref" in
    ref:refs/heads/*) branch="${head_ref#ref:refs/heads/}"
      if [ -f ".git/refs/heads/$branch" ]; then
        green "  refs/heads/$branch present: $(cat .git/refs/heads/$branch)"
      else
        red "  refs/heads/$branch MISSING — see reflog to recover"
      fi
      ;;
    *) gray "  detached HEAD" ;;
  esac
fi

hdr "FETCH_HEAD / packed-refs / ORIG_HEAD"
[ -s .git/FETCH_HEAD ]  && gray "  FETCH_HEAD present (last fetch tracking)" || red "  FETCH_HEAD missing or empty"
[ -s .git/packed-refs ] && gray "  packed-refs present"                    || gray "  no packed-refs"
[ -s .git/ORIG_HEAD ]   && gray "  ORIG_HEAD present"                      || gray "  no ORIG_HEAD"

hdr "origin/main ref vs remote (Symptom A detection)"
LOCAL_ORIGIN_MAIN=""
# packed-refs takes priority over loose refs; check both
if [ -s .git/packed-refs ]; then
  LOCAL_ORIGIN_MAIN=$(awk '/refs\/remotes\/origin\/main$/ {print $1}' .git/packed-refs | head -1)
fi
if [ -z "$LOCAL_ORIGIN_MAIN" ] && [ -s .git/refs/remotes/origin/main ]; then
  LOCAL_ORIGIN_MAIN=$(cat .git/refs/remotes/origin/main)
fi
if [ -z "$LOCAL_ORIGIN_MAIN" ]; then
  red "  local origin/main ref MISSING (Symptom A: shim blocked the ref write)"
else
  gray "  local origin/main: $LOCAL_ORIGIN_MAIN"
  # Compare to remote via git ls-remote. We use plain `git` (not zj-git) here
  # because we're just reading; the shim doesn't intercept read paths.
  REMOTE_MAIN=$(git ls-remote origin main 2>/dev/null | awk '{print $1}' | head -1)
  if [ -z "$REMOTE_MAIN" ]; then
    gray "  remote main: (could not query — offline or auth issue)"
  elif [ "$LOCAL_ORIGIN_MAIN" = "$REMOTE_MAIN" ]; then
    green "  origin/main matches remote: $REMOTE_MAIN"
  else
    red "  origin/main STALE: local=$LOCAL_ORIGIN_MAIN, remote=$REMOTE_MAIN"
    red "  ACTION: Symptom A — see SKILL.md for the 3-step fix (pack-refs / update-ref / mv from /tmp)"
  fi
fi

hdr "reflog"
if [ -s .git/logs/HEAD ]; then
  last=$(tail -1 .git/logs/HEAD)
  last_to=$(echo "$last" | awk '{print $2}')
  green "  reflog intact — last commit: $last_to"
  gray "  recover hint: git update-ref refs/heads/<branch> $last_to"
else
  red "  no reflog — recovery via reflog impossible"
fi

hdr "objects (sample)"
n=$(find .git/objects -type f -not -path '*/info/*' -not -path '*/pack/*' 2>/dev/null | wc -l)
n_pack=$(find .git/objects/pack -name '*.pack' 2>/dev/null | wc -l)
gray "  loose objects: $n, pack files: $n_pack"

hdr "working tree"
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  modified=$(git status --porcelain 2>/dev/null | wc -l)
  gray "  HEAD resolves; $modified working-tree changes"
else
  red "  HEAD does not resolve — run recover-refs.sh"
fi

hdr "summary"
if [ ! -d .git/refs/heads ] || [ -z "$(ls -A .git/refs/heads 2>/dev/null)" ]; then
  red "  ACTION: run scripts/recover-refs.sh <repo> <branch>"
fi
if [[ "${NODE_OPTIONS:-}" == *genie-safe-delete* ]]; then
  gray "  prevention: install ~/bin/zj-git wrapper, use it instead of git"
fi

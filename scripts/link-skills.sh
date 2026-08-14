#!/usr/bin/env bash
set -euo pipefail

# Generic installer for ZAgentic skills across agent CLIs.
#
# This script was originally Claude-only and called "link-skills.sh" (it
# symlinked skills into ~/.claude/skills). It now installs into any of the
# supported agent skill directories, either by symlink (live, dev-friendly)
# or by copy (snapshot, Windows-safe).
#
# Usage:
#   link-skills.sh                          # install into every detected platform
#   link-skills.sh --platform workbuddy     # only WorkBuddy
#   link-skills.sh --platform claude,codex  # several (comma-separated)
#   link-skills.sh --method copy            # copy instead of symlink
#   link-skills.sh --dry-run                # show what would happen, change nothing
#   link-skills.sh --help
#
# Supported platforms -> skill directory:
#   claude    ~/.claude/skills
#   codex     ~/.codex/skills
#   workbuddy ~/.workbuddy/skills
#
# Method:
#   copy     (default) copy each skill folder into the target dir. Robust on
#            Windows, immune to repo edits, good for a versioned snapshot.
#   symlink  link each skill folder back to this repo. Live updates while you
#            edit in the repo; falls back to copy automatically if the OS
#            refuses to create symlinks (e.g. Windows without Developer Mode).
#
# Uninstall is handled centrally by scripts/zagentic-skills-list — delete each
# listed directory from the agent's skills dir. This script only installs.

REPO="$(cd "$(dirname "$0")/.." && pwd)"

PLATFORMS=(
  claude:"$HOME/.claude/skills"
  codex:"$HOME/.codex/skills"
  workbuddy:"$HOME/.workbuddy/skills"
)

WANT_PLATFORMS=""
METHOD="copy"
DRY_RUN=0

usage() { sed -n '3,33p' "$0"; exit 0; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) WANT_PLATFORMS="$2"; shift 2 ;;
    --method)   METHOD="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=1; shift ;;
    -h|--help)  usage ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

case "$METHOD" in
  symlink|copy) ;;
  *) echo "error: --method must be 'symlink' or 'copy'" >&2; exit 1 ;;
esac

# ---- resolve which platforms to act on ----
declare -a ACT_NAMES=() ACT_DIRS=()
if [[ -z "$WANT_PLATFORMS" ]]; then
  # default: every platform dir that already exists (never create unwanted ones)
  for entry in "${PLATFORMS[@]}"; do
    name="${entry%%:*}"; dir="${entry#*:}"
    [[ -d "$dir" ]] && { ACT_NAMES+=("$name"); ACT_DIRS+=("$dir"); }
  done
  if [[ ${#ACT_DIRS[@]} -eq 0 ]]; then
    echo "error: no agent skill directory found. Use --platform <claude|codex|workbuddy> to pick one." >&2
    exit 1
  fi
else
  IFS=',' read -ra req <<< "$WANT_PLATFORMS"
  for r in "${req[@]}"; do
    found=0
    for entry in "${PLATFORMS[@]}"; do
      name="${entry%%:*}"; dir="${entry#*:}"
      if [[ "$name" == "$r" ]]; then
        ACT_NAMES+=("$name"); ACT_DIRS+=("$dir"); found=1; break
      fi
    done
    [[ $found -eq 1 ]] || { echo "error: unknown platform '$r' (use claude|codex|workbuddy)" >&2; exit 1; }
  done
fi

run() {
  if [[ $DRY_RUN -eq 1 ]]; then echo "[dry-run] $*"; else "$@"; fi
}

echo "ZAgentic skills -> installing via '$METHOD' into:"
for i in "${!ACT_NAMES[@]}"; do
  printf '  %s (%s)\n' "${ACT_NAMES[$i]}" "${ACT_DIRS[$i]}"
  [[ -n "$WANT_PLATFORMS" ]] && mkdir -p "${ACT_DIRS[$i]}"   # create only when explicitly requested
done
echo

total=0
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  name="$(basename "$src")"
  for i in "${!ACT_DIRS[@]}"; do
    dir="${ACT_DIRS[$i]}"
    target="$dir/$name"

    # guard: never write back into the repo's own skills tree
    if [[ "$(cd "$dir" && pwd)/" == "$REPO/"* ]]; then
      echo "  ! skip $name -> $dir (would write into the repo itself)" >&2
      continue
    fi

    # Replace any pre-existing target directly. The whole set is treated
    # as a single snapshot: if a skill has been renamed, removed, or its
    # content diverged from the repo, the previous copy is discarded.
    # Use --method symlink to make this section a no-op (symlink target
    # is overwritten in place below).
    if [[ -e "$target" ]] || [[ -L "$target" ]]; then
      run rm -rf "$target"
    fi

    if [[ "$METHOD" == symlink ]]; then
      if ln -sfn "$src" "$target" 2>/dev/null; then
        echo "  linked $name -> $src"
      else
        run cp -r "$src" "$target"
        echo "  linked $name -> $src (symlink refused by OS, used copy)"
      fi
    else
      run cp -r "$src" "$target"
      echo "  copied $name -> $target"
    fi
  done
  total=$((total+1))
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -print0)

echo
echo "done. installed ${total} skills across ${#ACT_DIRS[@]} platform(s)."
echo "remember to reload the agent (e.g. /reload-plugins in WorkBuddy) to pick up changes."

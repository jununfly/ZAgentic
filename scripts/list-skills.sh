#!/usr/bin/env bash
set -euo pipefail

# Generate scripts/zagentic-skills-list from the public skills/ and private personal/ trees.
#
# Output: a plain-text reconciliation list with one bare skill directory
# name per non-comment line, grouped by the 3 public categories under
# skills/ (engineering / productivity / misc), followed by root-level
# personal/. The bare name
# is what the install script flattens into the agent's skills dir, so
# that is the only thing the uninstall step needs.
#
# Usage:
#   scripts/list-skills.sh              # print to stdout
#   scripts/list-skills.sh > scripts/zagentic-skills-list
#
# Keep this script's output identical in shape to scripts/zagentic-skills-list
# (it is the regeneration source). Commit a regenerated zagentic-skills-list
# whenever you add or remove a skill under skills/ or personal/.

REPO="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO"

# Sanity: each SKILL.md must live at skills/<category>/<name>/SKILL.md or
# personal/<name>/SKILL.md so the basename is a stable install/uninstall handle.
emit() {
  local category="$1" name="$2"
  printf '%s\n' "$name"
}

categories=(engineering productivity misc)
for cat in "${categories[@]}"; do
  if [[ -d "skills/$cat" ]]; then
    # emit one bare basename per SKILL.md under the category, sorted
    find "skills/$cat" -mindepth 2 -maxdepth 2 -name SKILL.md -type f \
      -exec dirname {} \; | xargs -I {} basename {} | sort -u
  fi
done

if [[ -d "personal" ]]; then
  find "personal" -mindepth 2 -maxdepth 2 -name SKILL.md -type f \
    -exec dirname {} \; | xargs -I {} basename {} | sort -u
fi

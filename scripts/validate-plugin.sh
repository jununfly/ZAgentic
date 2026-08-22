#!/usr/bin/env bash
set -euo pipefail

# Run the official plugin validator first. If it returns non-zero, validate
# ZAgentic's bucketed public skills and root-level personal skills recursively.
# The fallback is deliberately a repository validation result, not a claim
# about why the official validator returned non-zero.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_PATH="$REPO"
PLUGIN_PATH_SET=0
EXPLICIT_OFFICIAL=""

usage() {
  cat <<'USAGE'
Usage: scripts/validate-plugin.sh [--official-validator PATH] [PLUGIN_PATH]

Run the official plugin validator first. If it returns non-zero, run the
repository's recursive validator for the bucketed public and root personal
skill layout.

The official validator can also be selected with the
ZAGENTIC_OFFICIAL_PLUGIN_VALIDATOR environment variable.
USAGE
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --official-validator)
      [[ $# -ge 2 ]] || { echo "error: --official-validator needs a path" >&2; exit 2; }
      EXPLICIT_OFFICIAL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    --)
      shift
      [[ $# -le 1 ]] || { echo "error: expected one plugin path" >&2; exit 2; }
      if [[ $# -eq 1 ]]; then
        PLUGIN_PATH="$1"
        PLUGIN_PATH_SET=1
      fi
      shift || true
      ;;
    -*)
      echo "error: unknown option '$1'" >&2
      exit 2
      ;;
    *)
      [[ "$PLUGIN_PATH_SET" -eq 0 ]] || {
        echo "error: expected one plugin path" >&2
        exit 2
      }
      PLUGIN_PATH="$1"
      PLUGIN_PATH_SET=1
      shift
      ;;
  esac
done

PLUGIN_PATH="$(cd "$PLUGIN_PATH" && pwd)"

find_official_validator() {
  if [[ -n "$EXPLICIT_OFFICIAL" ]]; then
    printf '%s\n' "$EXPLICIT_OFFICIAL"
    return 0
  fi
  if [[ -n "${ZAGENTIC_OFFICIAL_PLUGIN_VALIDATOR:-}" ]]; then
    printf '%s\n' "$ZAGENTIC_OFFICIAL_PLUGIN_VALIDATOR"
    return 0
  fi
  if [[ -n "${CODEX_HOME:-}" && -f "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" ]]; then
    printf '%s\n' "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py"
    return 0
  fi
  if [[ -n "${HOME:-}" && -f "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" ]]; then
    printf '%s\n' "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
    return 0
  fi
  return 1
}

OFFICIAL_VALIDATOR=""
if OFFICIAL_VALIDATOR="$(find_official_validator)"; then
  if [[ ! -f "$OFFICIAL_VALIDATOR" ]]; then
    echo "error: official validator was configured but not found: $OFFICIAL_VALIDATOR" >&2
    exit 2
  fi
  official_status=0
  python3 "$OFFICIAL_VALIDATOR" "$PLUGIN_PATH" || official_status=$?
  if [[ "$official_status" -eq 0 ]]; then
    exit 0
  fi
  echo "Official validator returned $official_status; running repository recursive validation."
else
  echo "Official validator was not found; running repository recursive validation."
fi

exec python3 "$REPO/scripts/validate-zagentic-plugin.py" "$PLUGIN_PATH"

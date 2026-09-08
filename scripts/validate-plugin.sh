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

# --- Cross-platform path handling ------------------------------------------
# MSYS2/Git Bash rewrites POSIX-looking arguments before exec'ing a native
# Windows program. `/c/...` is resolved against the *current drive root*, so it
# becomes `C:\c\...` — a path that does not exist — and any native Windows
# Python dies with "can't open file". Rather than rely on that heuristic (or on
# MSYS_NO_PATHCONV, which then hands Windows Python a POSIX path it also cannot
# resolve), convert each path to the form the configured interpreter expects.
# Windows Python installs (and venvs) commonly provide only `python.exe`, so
# `python3` is not a portable assumption. Prefer it, then fall back to any
# interpreter that is actually Python 3.
resolve_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)' \
        >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  printf '%s' "python3" # keep the conventional name so failures stay recognisable
}

PYTHON_BIN="$(resolve_python)"

is_msys_shell() {
  case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

# True when $PYTHON_BIN is a native Windows build: its sys.executable carries a
# drive letter. MSYS/Cygwin builds report a POSIX sys.executable and must keep
# receiving POSIX arguments.
python_is_windows() {
  "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.executable[1:2] == ":" else 1)' \
    >/dev/null 2>&1
}

# Set to 1 below once the shell/interpreter pair is known to need Windows paths.
NEED_WIN_PATHS=0

# Echo $1 converted for the configured interpreter. A no-op on POSIX systems
# and when the interpreter is not a native Windows build.
to_python_path() {
  if [[ "$NEED_WIN_PATHS" -eq 1 ]]; then
    cygpath -m -- "$1" 2>/dev/null || printf '%s' "$1"
  else
    printf '%s' "$1"
  fi
}

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

# Resolve the conversion mode once: MSYS shell + cygpath + native Windows Python.
NEED_WIN_PATHS=0
if is_msys_shell && command -v cygpath >/dev/null 2>&1 && python_is_windows; then
  NEED_WIN_PATHS=1
fi
PY_PLUGIN_PATH="$(to_python_path "$PLUGIN_PATH")"

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
  "$PYTHON_BIN" "$(to_python_path "$OFFICIAL_VALIDATOR")" "$PY_PLUGIN_PATH" || official_status=$?
  if [[ "$official_status" -eq 0 ]]; then
    exit 0
  fi
  echo "Official validator returned $official_status; running repository recursive validation."
else
  echo "Official validator was not found; running repository recursive validation."
fi

exec "$PYTHON_BIN" "$(to_python_path "$REPO/scripts/validate-zagentic-plugin.py")" "$PY_PLUGIN_PATH"

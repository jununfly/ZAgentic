#!/usr/bin/env bash
# Unified dual test gate for the zj-discuss skill.
#
# Resolves issue #202 (recurrence root cause): the zj-discuss skill has TWO
# independent test faces that were never in the same gate. `5e37d28` (#167)
# went green on the script-layer suite (96 cases) but silently broke the
# repo-root landing guard (3 cases) because nobody ran the second face.
#
# This script runs BOTH faces in one command and fails unless both are green.
# Any PR that touches skills/productivity/zj-discuss/{SKILL,REFERENCE}.md must
# keep this gate green (wired into CI via .github/workflows/zj-discuss-gate.yml).
#
# Usage: bash scripts/run_zj_discuss_gate.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${0}")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "==> [face 1/2] repo-root landing guard (tests/test_zj_discuss_*.py)"
"$PY" -m unittest tests.test_zj_discuss_r1_r6_landing tests.test_zj_discuss_pr149_review_findings

echo "==> [face 2/2] skill-local regression suite (skills/productivity/zj-discuss/tests)"
cd "$REPO_ROOT/skills/productivity/zj-discuss/tests"
"$PY" -m unittest discover -p 'test_*.py'

echo "==> zj-discuss dual gate: ALL GREEN"

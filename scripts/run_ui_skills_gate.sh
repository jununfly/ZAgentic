#!/usr/bin/env bash
# Unified gate for the ui bucket (skills/ui/**).
#
# Why this exists: until 2026-10-23 a change under skills/ui/** triggered ZERO
# CI checks. The two existing workflows only watch research/** and
# skills/productivity/zj-discuss/**, so PR #209 showed
# `mergeStateStatus: CLEAN` with `checks: 0` — green by absence of a gate, not
# green by evidence. This gate closes that hole. It is wired into CI via
# .github/workflows/ui-skills-contract.yml.
#
# Why the assertions below look paranoid:
#   * `dual_lane_runner selfcheck` returns 0 even when the two lanes disagree
#     (`return 0` in main()), so the exit code proves nothing — we parse its
#     JSON and assert `rerun_idempotent` plus non-empty hashes instead.
#   * the SKILL.md frontmatter validator calls skipTest() when PyYAML is
#     absent. A skipped case reads as green, so this gate hard-fails rather
#     than letting a missing dependency masquerade as a pass.
#   * `total`-style counters are asserted > 0: a suite that collects nothing
#     would otherwise report OK.
#
# Usage: bash scripts/run_ui_skills_gate.sh
#        PYTHON=/path/to/python bash scripts/run_ui_skills_gate.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${0}")/.." && pwd)"
PY="${PYTHON:-python3}"
SCRIPTS="$REPO_ROOT/skills/ui/zj-ui-core/scripts"
PLANS="$REPO_ROOT/docs/designs/ui-agent-skills"

STAGE=""
cleanup() { if [ -n "$STAGE" ] && [ -d "$STAGE" ]; then rm -rf "$STAGE"; fi; }
trap cleanup EXIT
STAGE="$(mktemp -d)"

echo "==> [1/4] dependency guard: PyYAML must be importable"
# Without PyYAML the frontmatter validator silently skips itself, turning a
# real regression into a green check. Fail loudly instead.
if ! "$PY" -c 'import yaml' 2>/dev/null; then
    echo "FAIL: PyYAML missing -> scripts/validate-skill-frontmatter.py would be skipped."
    echo "      Fix: python3 -m pip install -r requirements.txt"
    exit 1
fi
echo "    OK  PyYAML importable"

echo "==> [2/4] skill script self-checks (exit codes + payload assertions)"
"$PY" "$SCRIPTS/hard_gates.py" selftest >"$STAGE/hard_gates.json"
"$PY" - "$STAGE/hard_gates.json" <<'EOF'
import json, sys
path = sys.argv[1]
name = "hard_gates"
d = json.load(open(path, encoding="utf-8"))
total, failed = d.get("total"), d.get("failed")
if not isinstance(total, int) or total <= 0:
    sys.exit(f"FAIL: {name} selftest reported total={total!r} (nothing actually checked)")
if failed != 0:
    sys.exit(f"FAIL: {name} selftest reported failed={failed!r}")
print(f"    OK  {name}: total={total} failed=0")
EOF

"$PY" "$SCRIPTS/verification_receipt.py" selftest >"$STAGE/vr.json"
"$PY" - "$STAGE/vr.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
name = "verification_receipt"
total, failed = d.get("total"), d.get("failed")
if not isinstance(total, int) or total <= 0:
    sys.exit(f"FAIL: {name} selftest reported total={total!r} (nothing actually checked)")
if failed != 0:
    sys.exit(f"FAIL: {name} selftest reported failed={failed!r}")
print(f"    OK  {name}: total={total} failed=0")
EOF

"$PY" "$SCRIPTS/dual_lane_runner.py" selfcheck --plans "$PLANS" >"$STAGE/selfcheck.json"
"$PY" - "$STAGE/selfcheck.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
# selfcheck() returns exit code 0 unconditionally, so the payload is the only
# trustworthy signal here.
if d.get("rerun_idempotent") is not True:
    sys.exit(f"FAIL: dual_lane_runner selfcheck not idempotent: {d}")
for key in ("manifest_hash", "env_hash", "matrix_key"):
    val = d.get(key)
    if not isinstance(val, str) or not val:
        sys.exit(f"FAIL: dual_lane_runner selfcheck produced empty {key}: {d}")
print(f"    OK  dual_lane_runner: idempotent, matrix_key={d['matrix_key'][:12]}...")
EOF

echo "==> [3/4] installed-copy resolution guard (PR #209 regression class)"
# A skill installed under ~/.codex|~/.workbuddy|~/.claude/skills has no .git
# ancestor. Plan-dir discovery must therefore resolve from $PWD (the project
# being worked on), not from __file__ — otherwise it silently degrades to
# "/docs/designs/...". Compare an out-of-repo copy against the in-repo source:
# same answers are the contract.
INSTALLED="$STAGE/installed/scripts"
mkdir -p "$INSTALLED"
cp "$SCRIPTS"/*.py "$INSTALLED/"
if ! (cd "$REPO_ROOT" && "$PY" "$INSTALLED/dual_lane_runner.py" selfcheck) >"$STAGE/installed.json"; then
    echo "FAIL: installed copy of dual_lane_runner could not even run from the repo root."
    echo "      This is the /docs/designs/... degradation class — see PR #209."
    exit 1
fi
"$PY" - "$STAGE/installed.json" "$STAGE/selfcheck.json" <<'EOF'
import json, sys
loaded = json.load(open(sys.argv[1], encoding="utf-8"))
source = json.load(open(sys.argv[2], encoding="utf-8"))
if loaded.get("rerun_idempotent") is not True:
    sys.exit(f"FAIL: installed copy selfcheck not idempotent: {loaded}")
for key in ("manifest_hash", "env_hash", "matrix_key"):
    if loaded.get(key) != source.get(key):
        sys.exit(
            f"FAIL: installed copy disagrees with source on {key}: "
            f"installed={loaded.get(key)!r} source={source.get(key)!r}"
        )
print(f"    OK  installed copy resolves to the same fixtures "
      f"(matrix_key={source['matrix_key'][:12]}...)")
EOF

echo "==> [4/4] repo regression suites"
cd "$REPO_ROOT/tests"
"$PY" -m unittest discover -s . -p 'test_ui_agent_skills_*.py' -t .
"$PY" -m unittest test_quarantine_disambiguation

echo "==> ui skills gate: ALL GREEN"

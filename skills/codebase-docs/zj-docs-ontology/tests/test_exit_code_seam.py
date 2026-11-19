#!/usr/bin/env python3
"""Cross-cutting exit-code seam — DECISIONS.md line 163.

The validator's `main()` has one exit decision: `return 1 if has_error(payload)
else 0`. A new ERROR that forgets to enter the allowlist silently exits 0 — the
exact fake-green pattern this module exists to prevent.

The expected code sets are **hardcoded here on purpose**. Reading them from
`TOOL.ERROR_CODES` would make the test shrink along with a wrongly-edited
allowlist and pass green — the failure mode under test. The allowlist must
match these frozen expectations, not the other way round.

Coverage:
  - each of the 5 ERROR codes individually → has_error True (CLI exit 1)
  - each of the 6 signal codes individually → has_error False (CLI exit 0)
  - each error-prefix family (MAP_, RETIRE_) → has_error True
  - greenfield short-circuit → False regardless of diagnostics
  - CLI end-to-end on a real temp repo: clean/vocabulary/retirement/divergence
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_exit_seam_cases"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
SPEC = importlib.util.spec_from_file_location("docs_governage_exit_seam", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
PAGE = "docs/prds/p.md"

# Frozen expectations — the contract, not a mirror of the allowlist.
EXPECTED_ERRORS = frozenset({
    "UNDECLARED_RETIREMENT",
    "UNCONFIRMED_MUTATION",
    "EXEC_STEP5_ARTIFACT_MISSING",
    "EXEC_CHECKLIST_STEP_UNBACKED",
    "PRESET_VOCABULARY_VIOLATION",
})
EXPECTED_SIGNALS = frozenset({
    "BASELINE_NOT_APPLICABLE",
    "CONFIRMATION_BASELINE_LOST",
    "PRESET_DIVERGENCE",
    "PRESET_UNAVAILABLE",
    "EXEC_STEP5_FINGERPRINT_MISMATCH",
    "EXEC_CHECKLIST_NOT_DECLARED",
    "RENAME_AWAITING_CONFIRMATION",
    "FACT_NO_SINGLE_HOME",
    "PARALLEL_ONTOLOGY_SUSPECTED",
    "ORPHAN_PAGE",
})
EXPECTED_PREFIX_SAMPLES = ("MAP_LINK_BROKEN", "MAP_AUTHORITY_CONFLICT", "RETIRE_TARGET_MISSING")


def payload_with(code: str, *, origin: str = "existing") -> dict:
    """Minimal payload accepted by has_error(); `existing` avoids the
    greenfield short-circuit so the code itself decides the result."""
    return {"map_origin": origin, "diagnostics": [{"code": code, "path": "", "message": code}]}


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, env=GIT_ENV, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def make_repo(name: str, *, kind: str = "prd") -> Path:
    repo = TMP / name
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("docs-map: docs/team-map.md\n", encoding="utf-8")
    (repo / "docs" / "prds").mkdir(parents=True)
    (repo / "docs" / "team-map.md").write_text("# Map\n\n- [P](prds/p.md)\n", encoding="utf-8")
    (repo / "docs" / "prds" / "p.md").write_text(
        f"---\ndoc-kind: {kind}\nauthority: primary\nauthority-id: p\n---\n# P\n",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "-c", "user.email=t@e", "-c", "user.name=T", "commit", "-qm", "init")
    return repo


def cli_exit(repo: Path, *extra: str) -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(repo), "--validate", *extra],
        capture_output=True, text=True,
    )
    return proc.returncode


class ExitCodeSeamTest(unittest.TestCase):
    """line 163: each ERROR exits non-zero, each signal exits zero."""

    def test_allowlist_is_exactly_the_frozen_error_set(self) -> None:
        self.assertEqual(EXPECTED_ERRORS, TOOL.ERROR_CODES)

    def test_allowlist_is_exactly_the_frozen_signal_set(self) -> None:
        self.assertEqual(EXPECTED_SIGNALS, TOOL.SIGNAL_CODES)

    def test_error_and_signal_sets_are_disjoint(self) -> None:
        self.assertEqual(set(), EXPECTED_ERRORS & EXPECTED_SIGNALS)

    def test_each_error_code_exits_nonzero(self) -> None:
        for code in sorted(EXPECTED_ERRORS):
            with self.subTest(code=code):
                self.assertTrue(TOOL.has_error(payload_with(code)))

    def test_each_signal_code_exits_zero(self) -> None:
        for code in sorted(EXPECTED_SIGNALS):
            with self.subTest(code=code):
                self.assertFalse(TOOL.has_error(payload_with(code)))

    def test_error_prefix_family_exits_nonzero(self) -> None:
        for code in EXPECTED_PREFIX_SAMPLES:
            with self.subTest(code=code):
                self.assertTrue(TOOL.has_error(payload_with(code)))

    def test_greenfield_short_circuit_exits_zero_even_with_error_code(self) -> None:
        for code in sorted(EXPECTED_ERRORS):
            with self.subTest(code=code):
                self.assertFalse(TOOL.has_error(payload_with(code, origin="greenfield")))

    def test_unlisted_error_code_stays_zero_unless_prefixed(self) -> None:
        # A bare unknown code is not an ERROR — but every MAP_/RETIRE_ is.
        self.assertFalse(TOOL.has_error(payload_with("TOTALLY_MADE_UP")))
        self.assertTrue(TOOL.has_error(payload_with("RETIRE_SOMETHING_NEW")))


class CliStrengthCollapseTest(unittest.TestCase):
    """End-to-end: main() really calls has_error(), not just the pure fn."""

    def setUp(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)
        TMP.mkdir(parents=True)

    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def test_clean_repo_exits_zero(self) -> None:
        repo = make_repo("clean")
        self.assertEqual(0, cli_exit(repo))

    def test_preset_vocabulary_violation_exits_nonzero(self) -> None:
        repo = make_repo("vocab", kind="bogus-kind")
        self.assertEqual(1, cli_exit(repo))

    def test_undeclared_retirement_exits_nonzero(self) -> None:
        repo = make_repo("vanish")
        (repo / PAGE).unlink()
        self.assertEqual(1, cli_exit(repo))

    def test_preset_divergence_signal_exits_zero(self) -> None:
        # Divergence is a permitted signal, never an ERROR — even on a repo
        # whose category set differs from the canonical preset.
        repo = make_repo("diverge")
        preset = TMP / "thin-preset.json"
        preset.write_text(json.dumps({"schema_version": "1", "categories": {"long_lived": ["methods"], "process": []}, "kinds": {}}), encoding="utf-8")
        self.assertEqual(0, cli_exit(repo, "--preset", str(preset)))


if __name__ == "__main__":
    unittest.main()

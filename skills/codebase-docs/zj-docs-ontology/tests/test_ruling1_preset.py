#!/usr/bin/env python3
"""P1a red tests for P0 Ruling 1 — canonical preset + HEAD snapshot.

Two references, not one baseline (DECISIONS.md Ruling 1):
  - normative: canonical-preset.json (shipped in the skill)
  - observed:  git HEAD tracked-file roster (disappearance detection only)

Nine fixtures, each falsifiable, plus the exit-code allowlist that keeps an
ERROR from silently exiting 0. Fixtures are real temporary git repositories in
the gitignored output zone, so HEAD is a mechanical fact rather than a mocked
value. Every assertion goes through the public `report()` / CLI seam, so the
red state is a clean assertion failure (not an import error).
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
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_ruling1_cases"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
SPEC = importlib.util.spec_from_file_location("docs_governance_ruling1", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

# safe-delete shim is injected via NODE_OPTIONS; strip it for git subprocesses.
GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
PAGE = "docs/prds/payment.md"


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def make_repo(name: str, *, commit: bool = True) -> Path:
    """A minimal map + one primary page, optionally with an initial commit."""
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    git(base, "init", "-q")
    (base / "AGENTS.md").write_text("docs-map: docs/team-map.md\n", encoding="utf-8")
    (base / "docs" / "prds").mkdir(parents=True)
    (base / "docs" / "team-map.md").write_text(
        "# Team map\n\n- [Payment](prds/payment.md)\n", encoding="utf-8"
    )
    (base / PAGE).write_text(
        "---\ndoc-kind: prd\nauthority: primary\nauthority-id: payment\n---\n"
        "# Payment\n",
        encoding="utf-8",
    )
    if commit:
        git(base, "add", "-A")
        git(base, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "init")
    return base


def page_text(repo: Path, text: str) -> None:
    (repo / PAGE).write_text(text, encoding="utf-8")


def codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


def code_item(payload: dict, code: str) -> dict:
    return next(i for i in payload["diagnostics"] if i["code"] == code)


def report(repo: Path, **kwargs: object) -> dict:
    return TOOL.report(repo, validate_links=True, **kwargs)


class Ruling1Case(unittest.TestCase):
    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)


class FirstRunEmptyHeadTest(Ruling1Case):
    """Case 1 (line 62): empty HEAD is expected; preset is the baseline."""

    def test_empty_head_emits_baseline_not_applicable_signal(self) -> None:
        repo = make_repo("first-run", commit=False)
        self.assertIn("BASELINE_NOT_APPLICABLE", codes(report(repo)))

    def test_empty_head_does_not_fire_undeclared_retirement(self) -> None:
        repo = make_repo("first-run-no-retire", commit=False)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(report(repo)))

    def test_empty_head_bootstrap_comes_from_preset(self) -> None:
        repo = make_repo("first-run-bootstrap", commit=False)
        payload = report(repo)
        self.assertIn("bootstrap", payload)
        preset = json.loads((SKILL_ROOT / "references" / "canonical-preset.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(preset["categories"]["long_lived"]),
            set(payload["bootstrap"]["categories"]["long_lived"]),
        )


class PresetVocabularyViolationTest(Ruling1Case):
    """Case 2b1 (line 66): closed-vocabulary breaches are ERROR."""

    def test_out_of_range_doc_kind_is_an_error_naming_value_and_key(self) -> None:
        repo = make_repo("vocab-kind")
        page_text(repo, "---\ndoc-kind: bogus-kind\nauthority: primary\nauthority-id: payment\n---\n# Payment\n")
        payload = report(repo)
        self.assertIn("PRESET_VOCABULARY_VIOLATION", codes(payload))
        item = code_item(payload, "PRESET_VOCABULARY_VIOLATION")
        self.assertIn("bogus-kind", item["message"])
        self.assertIn("kinds", item["message"])

    def test_kind_with_no_preset_row_is_an_error(self) -> None:
        repo = make_repo("vocab-no-row")
        page_text(repo, "---\ndoc-kind: orphankind\nauthority: supporting\n---\n# Payment\n")
        payload = report(repo)
        self.assertIn("PRESET_VOCABULARY_VIOLATION", codes(payload))

    def test_primary_without_authority_id_is_an_error(self) -> None:
        repo = make_repo("vocab-primary-no-id")
        page_text(repo, "---\ndoc-kind: prd\nauthority: primary\n---\n# Payment\n")
        self.assertIn("PRESET_VOCABULARY_VIOLATION", codes(report(repo)))

    def test_out_of_range_authority_is_an_error(self) -> None:
        repo = make_repo("vocab-authority")
        page_text(repo, "---\ndoc-kind: prd\nauthority: wizard\n---\n# Payment\n")
        self.assertIn("PRESET_VOCABULARY_VIOLATION", codes(report(repo)))

    def test_violation_reads_page_front_matter_without_mutating(self) -> None:
        repo = make_repo("vocab-boundary")
        page_text(repo, "---\ndoc-kind: bogus-kind\nauthority: supporting\n---\n# Payment\n")
        payload = report(repo)
        self.assertIn(PAGE, payload["read_paths"])
        self.assertEqual([], payload["mutations"])


class PresetDivergenceTest(Ruling1Case):
    """Case 2b2 (line 67): permitted divergence is signal, never auto-repaired."""

    def test_missing_long_lived_category_is_a_signal(self) -> None:
        repo = make_repo("divergence-category")
        payload = report(repo)
        self.assertIn("PRESET_DIVERGENCE", codes(payload))
        self.assertNotIn("PRESET_VOCABULARY_VIOLATION", codes(payload))

    def test_divergence_names_the_preset_key(self) -> None:
        repo = make_repo("divergence-key")
        item = code_item(report(repo), "PRESET_DIVERGENCE")
        self.assertIn("categories", item["message"])

    def test_divergence_does_not_mutate(self) -> None:
        repo = make_repo("divergence-no-mutate")
        self.assertEqual([], report(repo)["mutations"])


class UndeclaredRetirementTest(Ruling1Case):
    """Case (c) line 84: a tracked page vanishing without declaration is ERROR."""

    def test_deleted_committed_page_is_an_error_naming_it(self) -> None:
        repo = make_repo("undeclared-retire")
        (repo / PAGE).unlink()
        payload = report(repo)
        self.assertIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertIn(PAGE, code_item(payload, "UNDECLARED_RETIREMENT")["message"])

    def test_declared_retirement_keeps_exit_zero(self) -> None:
        """A retirement is a tombstone, not a deletion (contract §Retirement):
        the page stays in the HEAD roster with a `retired-to:` declaration, so
        there is no vanished path to report."""
        repo = make_repo("declared-retire")
        # Turn the page into a tombstone: authority historical, content names
        # the replacement. It is still tracked → no disappearance claim.
        page_text(repo, (
            "---\ndoc-kind: prd\nauthority: historical\nauthority-id: payment\n---\n"
            "# Payment (retired)\n\nSee prds/new.md.\n"
        ))
        (repo / "docs" / "team-map.md").write_text(
            "# Team map\n\n"
            "- [Payment](prds/payment.md) — retired-to: docs/prds/new.md\n"
            "- [New](prds/new.md)\n",
            encoding="utf-8",
        )
        (repo / "docs" / "prds" / "new.md").write_text(
            "---\ndoc-kind: prd\nauthority: primary\nauthority-id: payment-new\n---\n# New\n",
            encoding="utf-8",
        )
        git(repo, "add", "-A")
        git(repo, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "retire")
        payload = report(repo)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))


class PresetSingleSourceTest(Ruling1Case):
    """Case (e) line 84: no second copy of the vocabulary may reappear."""

    def test_two_markdown_tables_are_pointers_only(self) -> None:
        contract = (SKILL_ROOT / "references" / "governance-contract.md").read_text(encoding="utf-8")
        templates = (SKILL_ROOT / "references" / "kind-templates.md").read_text(encoding="utf-8")
        for text in (contract, templates):
            self.assertIn("canonical-preset.json", text)
        self.assertNotIn("| method |", templates)
        self.assertNotIn("| prd |", templates)

    def test_no_hardcoded_category_constants_in_tool(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("LONG_LIVED = (", source)
        self.assertNotIn("PROCESS = (", source)


class PresetUnavailableTest(Ruling1Case):
    """Case (f) line 84: absent preset is a signal, never a hardcoded fallback."""

    def test_missing_preset_is_a_signal_not_an_error(self) -> None:
        repo = make_repo("preset-unavailable")
        payload = TOOL.report(repo, validate_links=True, preset_path=TMP / "no-such-preset.json")
        self.assertIn("PRESET_UNAVAILABLE", codes(payload))
        self.assertNotIn("PRESET_VOCABULARY_VIOLATION", codes(payload))

    def test_missing_preset_exits_zero(self) -> None:
        repo = make_repo("preset-unavailable-cli")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo), "--validate",
             "--preset", str(TMP / "no-such-preset.json")],
            capture_output=True, text=True,
        )
        self.assertEqual(0, proc.returncode)


class RenameTest(Ruling1Case):
    """Three-level rename adjudication (issue #275 defect B, revising Ruling
    v7's "proposal-named moves only"): git-native rename evidence downgrades
    the unconfirmed case to a signal; hash-pairing is still not evidence."""

    def _moved_repo(self, name: str) -> Path:
        repo = make_repo(name)
        git(repo, "mv", PAGE, "docs/prds/renamed.md")
        return repo

    def test_unconfirmed_rename_is_a_signal_not_an_error(self) -> None:
        repo = self._moved_repo("unconfirmed-rename")
        payload = report(repo)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertIn("RENAME_AWAITING_CONFIRMATION", codes(payload))

    def test_confirmed_rename_is_fully_exempt(self) -> None:
        repo = self._moved_repo("declared-rename")
        proposal = {
            "moves": [{"from": PAGE, "to": "docs/prds/renamed.md"}],
            "confirmation_id": "a" * 64,
        }
        payload = report(repo, proposal=proposal)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertNotIn("RENAME_AWAITING_CONFIRMATION", codes(payload))

    def test_declared_rename_with_matching_confirmation_exits_zero(self) -> None:
        repo = self._moved_repo("declared-rename")
        proposal = {
            "moves": [{"from": PAGE, "to": "docs/prds/renamed.md"}],
            "confirmation_id": "a" * 64,
        }
        payload = report(repo, proposal=proposal)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))

    def test_hash_identical_deletion_still_errors(self) -> None:
        repo = make_repo("hash-identical")
        twin = repo / "docs" / "prds" / "twin.md"
        twin.write_text((repo / PAGE).read_text(encoding="utf-8"), encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "twin")
        (repo / PAGE).unlink()  # same content hash as twin.md, no moves entry
        payload = report(repo)
        self.assertIn("UNDECLARED_RETIREMENT", codes(payload))


class ExitCodeAllowlistTest(Ruling1Case):
    """Cross-cutting line 163: 5 ERROR + 8 signal, explicit allowlists.

    The eighth signal is CAPABILITY_NOT_COVERED (issue #275 Fix 1b): the
    uncovered-request declaration. Signal-only by the same ruling — a
    capability statement is not a mechanical fact."""

    def test_five_error_codes_are_explicit(self) -> None:
        self.assertEqual(
            frozenset({
                "UNDECLARED_RETIREMENT", "UNCONFIRMED_MUTATION",
                "EXEC_STEP5_ARTIFACT_MISSING", "EXEC_CHECKLIST_STEP_UNBACKED",
                "PRESET_VOCABULARY_VIOLATION",
            }),
            TOOL.ERROR_CODES,
        )

    def test_signal_codes_are_explicit(self) -> None:
        self.assertEqual(
            frozenset({
                "BASELINE_NOT_APPLICABLE", "CAPABILITY_NOT_COVERED",
                "CONFIRMATION_BASELINE_LOST",
                "PRESET_DIVERGENCE", "PRESET_UNAVAILABLE",
                "EXEC_STEP5_FINGERPRINT_MISMATCH", "EXEC_CHECKLIST_NOT_DECLARED",
                "RENAME_AWAITING_CONFIRMATION",
                "FACT_NO_SINGLE_HOME", "PARALLEL_ONTOLOGY_SUSPECTED",
            }),
            TOOL.SIGNAL_CODES,
        )

    def test_error_and_signal_allowlists_are_disjoint(self) -> None:
        self.assertEqual(set(), TOOL.ERROR_CODES & TOOL.SIGNAL_CODES)


if __name__ == "__main__":
    unittest.main()

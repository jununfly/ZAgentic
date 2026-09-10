#!/usr/bin/env python3
"""Contract tests for the bounded architecture documentation validator."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
MODULE_PATH = SKILL_ROOT / "scripts" / "validate_architecture_docs.py"
SPEC = importlib.util.spec_from_file_location("architecture_validator", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ArchitectureValidatorTest(unittest.TestCase):
    def codes(self, fixture: str) -> set[str]:
        diagnostics, _, _ = VALIDATOR.validate(FIXTURES / fixture)
        return {item.code for item in diagnostics}

    def test_accepts_minimal_and_multiview_handbooks(self) -> None:
        self.assertEqual(self.codes("valid-minimal"), set())
        self.assertEqual(self.codes("valid-multiview"), set())

    def test_accepts_a_lazy_architecture_category(self) -> None:
        self.assertEqual(self.codes("valid-lazy"), set())

    def test_rejects_duplicate_authority_and_source_drift(self) -> None:
        self.assertIn("AUTHORITY_ID_DUPLICATE", self.codes("invalid-duplicate-authority"))
        self.assertIn("SOURCE_TARGET_MISSING", self.codes("invalid-source-drift"))

    def test_rejects_unaccepted_adr(self) -> None:
        self.assertIn("ADR_UNACCEPTED", self.codes("invalid-adr"))

    def test_never_reads_process_or_fixture_payloads(self) -> None:
        diagnostics, reads, _ = VALIDATOR.validate(FIXTURES / "read-boundary")
        self.assertEqual(diagnostics, [])
        self.assertFalse(any(path.endswith("docs/plans/active.md") for path in reads))
        self.assertFalse(any(path.endswith("fixtures/payload.json") for path in reads))


NAMING = "invalid-page-naming"
STABLE_CONTROL = "docs/architecture/ta-catalog.md"


class PageNamingTest(unittest.TestCase):
    """#49 — a mapped architecture page must carry a stable name.

    Stable means: prefixed `ta-` / `ba-` / `pa-`, lowercase and hyphenated,
    and free of dates, commit shas, versions, and temporary-status words. A
    name that encodes *when* it was written or *how current* it is will rot
    the first time the page is revised.
    """

    def diagnostics(self, fixture: str):
        return VALIDATOR.validate(FIXTURES / fixture)[0]

    def codes_for(self, path: str, fixture: str = NAMING) -> set[str]:
        return {item.code for item in self.diagnostics(fixture) if item.path == path}

    def test_rejects_a_date_stamped_name(self) -> None:
        self.assertIn("PAGE_NAME_DATE", self.codes_for("docs/architecture/ta-overview-2026-09-10.md"))

    def test_rejects_a_commit_sha_name(self) -> None:
        self.assertIn("PAGE_NAME_DATE", self.codes_for("docs/architecture/ta-flow-9f3c1ab.md"))

    def test_rejects_a_missing_prefix(self) -> None:
        self.assertIn("PAGE_NAME_PREFIX", self.codes_for("docs/architecture/overview.md"))

    def test_rejects_a_name_that_is_not_lowercase_hyphenated(self) -> None:
        self.assertIn("PAGE_NAME_SHAPE", self.codes_for("docs/architecture/ta-Checkout_Flow.md"))

    def test_rejects_version_and_temporary_status_names(self) -> None:
        self.assertIn("PAGE_NAME_VERSION_OR_STATUS", self.codes_for("docs/architecture/ta-catalog-v2.md"))
        self.assertIn("PAGE_NAME_VERSION_OR_STATUS", self.codes_for("docs/architecture/ta-catalog-draft.md"))

    def test_leaves_the_stable_control_page_alone(self) -> None:
        self.assertEqual(set(), self.codes_for(STABLE_CONTROL))

    def test_adds_no_naming_diagnostics_to_valid_fixtures(self) -> None:
        for fixture in ("valid-minimal", "valid-multiview", "valid-lazy"):
            codes = {item.code for item in self.diagnostics(fixture) if item.code.startswith("PAGE_NAME")}
            self.assertEqual(set(), codes, fixture)


def handbook_repo() -> Path | None:
    """The nearest ancestor that is both a repo and carries a `docs/` tree.

    A fixed `parents[N]` breaks the moment the skill is copied into
    `~/.codex/skills/…`, where the same index lands on `$HOME` and the
    validator dutifully fails on someone's home directory.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() and (parent / "docs").is_dir():
            return parent
    return None


class CommandLineTest(unittest.TestCase):
    """Exit codes live at the CLI seam; the in-process seam cannot see them."""

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args], capture_output=True, text=True
        ).returncode

    def test_naming_fixture_exits_nonzero(self) -> None:
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / NAMING)))

    def test_valid_fixture_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(FIXTURES / "valid-minimal")))

    def test_this_repository_stays_green(self) -> None:
        """The real handbook is the control: a naming rule that fires on
        today's pages is too strict to ship."""
        repo = handbook_repo()
        if repo is None:
            self.skipTest("no repo with a docs/ tree above this skill copy")
        self.assertEqual(0, self.exit_code(str(repo)))


if __name__ == "__main__":
    unittest.main()

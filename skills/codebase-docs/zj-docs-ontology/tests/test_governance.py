#!/usr/bin/env python3
"""Regression tests for the read-only documentation governance proposal."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
CONFLICT = "conflicting-authority"
SPEC = importlib.util.spec_from_file_location("docs_governance", SKILL_ROOT / "scripts" / "docs_governance.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class GovernanceProposalTest(unittest.TestCase):
    def test_greenfield_is_a_confirmation_bound_proposal(self) -> None:
        payload = TOOL.report(FIXTURES / "greenfield", validate_links=True)
        self.assertEqual(payload["map_origin"], "greenfield")
        self.assertEqual(payload["mutations"], [])
        self.assertEqual(payload["proposed_actions"][0]["action"], "create-map")

    def test_explicit_compatible_map_wins(self) -> None:
        payload = TOOL.report(FIXTURES / "existing-map", validate_links=True)
        self.assertEqual(payload["map"], "docs/team-map.md")
        self.assertEqual(payload["map_origin"], "explicit-pointer")
        self.assertEqual(payload["mutations"], [])

    def test_broken_map_link_is_mechanical(self) -> None:
        payload = TOOL.report(FIXTURES / "broken-map", validate_links=True)
        self.assertIn("MAP_LINK_BROKEN", {item["code"] for item in payload["diagnostics"]})

    def test_process_content_is_listed_but_never_read(self) -> None:
        payload = TOOL.report(FIXTURES / "read-boundary", validate_links=True)
        self.assertIn("docs/plans/active.md", payload["inventory"]["process_material"]["plans"])
        self.assertNotIn("docs/plans/active.md", payload["read_paths"])
        self.assertEqual(payload["mutations"], [])


class AuthorityConflictTest(unittest.TestCase):
    """#51 — one authority-id bound to two pages is a governance failure.

    Not a matter of which page happens to come first in the map: two pages
    answering the same bounded question is exactly what the Human has to settle,
    so it is reported rather than silently resolved by navigation order.
    """

    def payload(self, validate: bool = True):
        return TOOL.report(FIXTURES / CONFLICT, validate_links=validate)

    def conflicts(self) -> list[dict[str, str]]:
        return [item for item in self.payload()["diagnostics"] if item["code"] == "MAP_AUTHORITY_CONFLICT"]

    def test_one_authority_id_bound_to_two_pages_is_reported_once(self) -> None:
        self.assertEqual(1, len(self.conflicts()))

    def test_the_conflict_names_both_pages(self) -> None:
        message = self.conflicts()[0]["message"]
        self.assertIn("docs/prds/payment.md", message)
        self.assertIn("docs/architecture/payments.md", message)

    def test_a_link_without_an_authority_binding_is_not_part_of_it(self) -> None:
        self.assertNotIn("docs/prds/refund.md", self.conflicts()[0]["message"])

    def test_the_report_stays_a_proposal(self) -> None:
        self.assertEqual([], self.payload()["mutations"])

    def test_proposal_mode_does_not_report_it(self) -> None:
        """Link-level checks belong to --validate; --proposal stays about shape."""
        codes = {item["code"] for item in self.payload(validate=False)["diagnostics"]}
        self.assertNotIn("MAP_AUTHORITY_CONFLICT", codes)


class CommandLineTest(unittest.TestCase):
    """Exit codes only exist at the CLI seam; `report()` cannot show them."""

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "docs_governance.py"), *args],
            capture_output=True,
            text=True,
        ).returncode

    def test_conflicting_authority_exits_nonzero(self) -> None:
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / CONFLICT), "--validate"))

    def test_the_existing_fixtures_keep_their_exit_codes(self) -> None:
        for fixture in ("greenfield", "existing-map", "read-boundary"):
            self.assertEqual(0, self.exit_code(str(FIXTURES / fixture), "--validate"), fixture)
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / "broken-map"), "--validate"))


if __name__ == "__main__":
    unittest.main()

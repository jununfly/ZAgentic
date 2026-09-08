#!/usr/bin/env python3
"""Regression tests for the read-only documentation governance proposal."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
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


if __name__ == "__main__":
    unittest.main()

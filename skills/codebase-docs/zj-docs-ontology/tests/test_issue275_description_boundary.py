"""Issue #275 Fix 1c (L5): the SKILL.md description is a capability boundary
statement, not an overpromise.

Legacy behavior: ``description`` claimed "governance of one codebase's
documentation system", so a Human asking for entity/attribute/relation/rule
decomposition of the docs system expected that capability from this skill —
the description promised more than the tool can check.

Fixed contract: the frontmatter description must
  - name the governance layer it actually covers, and
  - state an explicit does-not-cover clause with the pointer to the
    capability that does own that work.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


def description() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    match = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
    assert match, "frontmatter description line not found"
    return match.group(1)


class DescriptionCapabilityBoundaryTest(unittest.TestCase):
    def test_description_names_the_governance_layer(self) -> None:
        self.assertIn("governance layer", description().lower())

    def test_description_states_an_explicit_does_not_cover_clause(self) -> None:
        lowered = description().lower()
        self.assertRegex(lowered, r"does not cover|not covered")

    def test_description_names_the_uncovered_request_class(self) -> None:
        lowered = description().lower()
        self.assertIn("entity", lowered)
        self.assertIn("recompos", lowered)

    def test_description_points_to_the_alternative_capability(self) -> None:
        self.assertIn("zj-codebase-design", description())

    def test_no_unqualified_whole_system_claim(self) -> None:
        # The overpromise being removed (L5): unqualified "governance of one
        # codebase's documentation system".
        self.assertNotIn(
            "governance of one codebase's documentation system",
            description(),
        )


class SkillBodyDocumentsTheBoundary(unittest.TestCase):
    def test_body_documents_the_object_declaration_flag(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("--object", text)

    def test_body_documents_the_capability_signal(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("CAPABILITY_NOT_COVERED", text)

    def test_body_states_the_boundary_in_prose(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("capability_boundary", text)


if __name__ == "__main__":
    unittest.main()

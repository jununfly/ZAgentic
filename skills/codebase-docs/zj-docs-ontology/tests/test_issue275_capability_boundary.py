"""Issue #275 Fix 1b, amended 2026-11-20 (Module D merge): the capability
boundary is declared, not implied — and now covers ontology design.

History: the original contract declared docs-system decomposition/recomposition
as NOT covered and routed it to an alternative. That was a stopgap honesty
device while the capability did not exist. zj 2026-11-20 ratified the merge:
ontology design (entity/attribute/relation/rule decomposition and
recomposition of a docs system) is this skill's Module D — the request class
the skill exists for. Therefore:

  - ``CAPABILITY_NOT_COVERED`` for decomposition/recomposition requests is
    RETRACTED: such a declaration now names the skill's own job, and
    mis-scoping defense is the explicit ``--object`` declaration itself.
  - the ``capability_boundary`` block stays: it now declares the two covered
    layers (governance + ontology design) and the residual uncovered class —
    ontologies whose declared object is not a documentation system (a
    database schema, a runtime data model), which belong to domain-specific
    capabilities. zj-codebase-design is code-module design vocabulary and is
    NOT the pointer for anything here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
MAP = SKILL_ROOT / "tests" / "fixtures" / "existing-map"
GATE_RULES = SKILL_ROOT / "references" / "gate-rules.json"

TOOL_SPEC = importlib.util.spec_from_file_location("dg_capability", SCRIPT)
assert TOOL_SPEC and TOOL_SPEC.loader
TOOL = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = TOOL
TOOL_SPEC.loader.exec_module(TOOL)


def codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


DECOMPOSITION_DECLARATIONS = (
    "docs system decomposition into entities/attributes/relations/rules and recomposition",
    "把 docs system 按实体/属性/关系/规则拆解重组",
    "docs 按实体/规则拆解重组",
    "docs 实体/关系 拆解重组",
)


class CapabilityBoundaryBlockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.block = TOOL.report(MAP, validate_links=True)["capability_boundary"]

    def test_every_report_carries_the_boundary_block(self) -> None:
        self.assertIn("governance", self.block["covers"])
        self.assertTrue(self.block["does_not_cover"])
        self.assertTrue(self.block["alternatives"])

    def test_boundary_names_both_covered_layers(self) -> None:
        joined = self.block["covers"].lower()
        self.assertIn("governance", joined)
        self.assertIn("ontology design", joined)

    def test_boundary_no_longer_names_decomposition_as_uncovered(self) -> None:
        joined = " ".join(self.block["does_not_cover"]).lower()
        self.assertNotIn("recompos", joined)
        self.assertNotIn("拆解重组", joined)

    def test_uncovered_class_is_non_docs_system_objects(self) -> None:
        joined = " ".join(self.block["does_not_cover"]).lower()
        self.assertIn("not a documentation system", joined)

    def test_alternatives_do_not_point_to_zj_codebase_design(self) -> None:
        self.assertFalse(
            any("zj-codebase-design" in alt for alt in self.block["alternatives"])
        )


class CapabilityNotCoveredRetractedTest(unittest.TestCase):
    def payload(self, **kwargs) -> dict:
        return TOOL.report(MAP, validate_links=True, **kwargs)

    def test_decomposition_declarations_trigger_nothing(self) -> None:
        for declaration in DECOMPOSITION_DECLARATIONS:
            self.assertNotIn(
                "CAPABILITY_NOT_COVERED",
                codes(self.payload(object=declaration)),
                msg=f"retracted signal fired for: {declaration}",
            )

    def test_plain_and_derived_declarations_stay_clean(self) -> None:
        self.assertNotIn("CAPABILITY_NOT_COVERED", codes(self.payload(object="docs")))
        self.assertNotIn("CAPABILITY_NOT_COVERED", codes(self.payload()))

    def test_signal_removed_from_allowlists(self) -> None:
        self.assertNotIn("CAPABILITY_NOT_COVERED", TOOL.ERROR_CODES)
        self.assertNotIn("CAPABILITY_NOT_COVERED", TOOL.SIGNAL_CODES)

    def test_signal_removed_from_gate_rules(self) -> None:
        rules = json.loads(GATE_RULES.read_text(encoding="utf-8"))
        self.assertNotIn("CAPABILITY_NOT_COVERED", rules["escalatable_signals"])
        self.assertNotIn("CAPABILITY_NOT_COVERED", rules["never_gate_signals"])


if __name__ == "__main__":
    unittest.main()

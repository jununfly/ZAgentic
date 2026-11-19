"""Issue #275 Fix 1b: the capability boundary is declared, not implied.

Legacy behavior (L5): the SKILL.md description promised "governance of one
codebase's documentation system", so a Human asking for "decompose the docs
system into entities / attributes / relations / rules and recompose it"
walked away with a green governance report and an untouched problem — the
tool cannot cover that request, and nothing in the report said so.

Fixed contract:
  - every report carries a ``capability_boundary`` block: what this pass
    covers (the governance layer) and what it explicitly does not cover
    (product-domain ontology modelling; entity/attribute/relation/rule
    decomposition & recomposition of the docs system), plus the pointer to
    the capabilities that do own that work.
  - when the object declaration itself carries the request features of an
    ontology decomposition/recomposition, the report emits
    ``CAPABILITY_NOT_COVERED`` — a signal (never an ERROR, exit stays 0) so
    the green governance layer cannot mask the uncovered request. Detection
    is heuristic keyword matching on the declaration text; it produces a
    signal only and never participates in acceptance judgment.
"""

from __future__ import annotations

import importlib.util
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


class CapabilityBoundaryBlockTest(unittest.TestCase):
    def test_every_report_carries_the_boundary_block(self) -> None:
        payload = TOOL.report(MAP, validate_links=True)
        block = payload["capability_boundary"]
        self.assertIn("governance", block["covers"])
        self.assertTrue(block["does_not_cover"])
        self.assertTrue(block["alternatives"])

    def test_boundary_names_the_uncovered_request_class(self) -> None:
        block = TOOL.report(MAP, validate_links=True)["capability_boundary"]
        joined = " ".join(block["does_not_cover"]).lower()
        self.assertIn("entity", joined)
        self.assertIn("recompos", joined)

    def test_boundary_names_an_alternative_capability(self) -> None:
        block = TOOL.report(MAP, validate_links=True)["capability_boundary"]
        self.assertTrue(any("zj-codebase-design" in alt for alt in block["alternatives"]))


class CapabilityNotCoveredSignalTest(unittest.TestCase):
    def payload(self, **kwargs) -> dict:
        return TOOL.report(MAP, validate_links=True, **kwargs)

    def test_decomposition_declaration_triggers_the_signal(self) -> None:
        payload = self.payload(
            object="docs system decomposition into entities/attributes/relations/rules and recomposition"
        )
        self.assertIn("CAPABILITY_NOT_COVERED", codes(payload))
        item = next(i for i in payload["diagnostics"] if i["code"] == "CAPABILITY_NOT_COVERED")
        self.assertTrue(item["message"])

    def test_signal_points_to_the_alternative_capability(self) -> None:
        payload = self.payload(object="把 docs system 按实体/属性/关系/规则拆解重组")
        item = next(i for i in payload["diagnostics"] if i["code"] == "CAPABILITY_NOT_COVERED")
        self.assertIn("zj-codebase-design", item["message"])

    def test_chinese_declaration_triggers_the_signal(self) -> None:
        self.assertIn(
            "CAPABILITY_NOT_COVERED",
            codes(self.payload(object="docs 按实体/规则拆解重组")),
        )

    def test_plain_directory_declaration_does_not_trigger(self) -> None:
        self.assertNotIn("CAPABILITY_NOT_COVERED", codes(self.payload(object="docs")))

    def test_derived_default_does_not_trigger(self) -> None:
        self.assertNotIn("CAPABILITY_NOT_COVERED", codes(self.payload()))

    def test_signal_never_changes_the_exit_semantics(self) -> None:
        self.assertNotIn("CAPABILITY_NOT_COVERED", TOOL.ERROR_CODES)
        self.assertIn("CAPABILITY_NOT_COVERED", TOOL.SIGNAL_CODES)
        payload = self.payload(object="docs 实体/关系 拆解重组")
        self.assertFalse(TOOL.has_error(payload))

    def test_signal_is_registered_as_escalatable_in_gate_rules(self) -> None:
        import json

        rules = json.loads(GATE_RULES.read_text(encoding="utf-8"))
        self.assertIn("CAPABILITY_NOT_COVERED", rules["escalatable_signals"])


if __name__ == "__main__":
    unittest.main()

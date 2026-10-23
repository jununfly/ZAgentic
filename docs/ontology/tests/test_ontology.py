#!/usr/bin/env python3
"""Integration test for the ZAgentic unified ontology — Module P (product domain).

Module G (governance) is exercised by the portable skill's own suite
(skills/codebase-docs/zj-docs-ontology/tests/test_governance.py); this test covers
the product-domain layer: graph extraction from the live tree and the native
Module P constraint checks. Run: python3 docs/ontology/tests/test_ontology.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ONTOLOGY_DIR = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ONTOLOGY_DIR)

from extract import build_graph  # noqa: E402
import validate  # noqa: E402


class ProductDomainGraphTest(unittest.TestCase):
    def setUp(self):
        self.graph = build_graph()
        self.idx = {n["id"]: n for n in self.graph["nodes"]}

    def test_graph_has_expected_scale(self):
        self.assertGreater(len(self.graph["nodes"]), 100)
        self.assertGreater(len(self.graph["edges"]), 100)

    def test_ui_bucket_present(self):
        self.assertIn("bucket:ui", self.idx)
        self.assertEqual(self.idx["bucket:ui"]["attrs"]["kind"], "public")

    def test_node_types_covered(self):
        types = {n["type"] for n in self.graph["nodes"]}
        for t in ("Platform", "SkillBucket", "Skill", "ArchitectureView",
                  "Design", "ADR", "DocPage", "Contract"):
            self.assertIn(t, types)

    def test_product_domain_checks_pass(self):
        violations = []
        for chk in validate.CHECKS:
            if chk is validate.check_governance_module:
                continue  # portable governance layer tested by the skill's own suite
            chk(self.graph, self.idx, violations)
        errors = [v for v in violations if v[0] == validate.SEV_ERROR]
        self.assertEqual(errors, [], msg="\n".join(f"{v[1]}: {v[2]}" for v in errors))


if __name__ == "__main__":
    unittest.main()

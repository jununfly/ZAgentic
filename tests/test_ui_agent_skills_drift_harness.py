"""Tests for the shared golden-diff / version-drift harness (1-7-4-4).

These assert the three signals from the F-A2-JR-DRIFT spec behave as designed,
using the real F-A2 golden fixtures as the baseline and synthetic candidates to
provoke each signal.
"""

import copy
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/adapters"
JR = FIXTURES / "F-A2/json-render"
A2UI = FIXTURES / "F-A2/a2ui"

sys.path.insert(0, str(REPO / "tests"))

import ui_agent_skills_drift_harness as harness  # noqa: E402


def load(path):
    import json
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def jr_expected(name="FF-JR-PROJ-01"):
    return load(JR / name / "expected.json")


def jr_anchor():
    return load(JR / "anchor.json")


class NoChangeIsOk(unittest.TestCase):
    def test_identical_golden_no_signal(self):
        baseline = jr_expected()
        report = harness.compare(baseline, copy.deepcopy(baseline),
                                 jr_anchor(), copy.deepcopy(jr_anchor()))
        self.assertEqual(report["verdict"], "ok")
        self.assertFalse(report["version_drift"]["detected"])
        self.assertFalse(report["semantic_loss"]["detected"])
        self.assertFalse(report["unknown_regression"]["detected"])


class VersionDriftIsReportOnly(unittest.TestCase):
    def test_changed_anchor_version_is_drift_only(self):
        baseline = jr_expected()
        pin_b = jr_anchor()
        pin_c = copy.deepcopy(pin_b)
        pin_c["pin"]["version"] = "0.9.0"
        pin_c["pin"]["source_commit"] = "deadbeef" * 5
        report = harness.compare(baseline, copy.deepcopy(baseline), pin_b, pin_c)
        self.assertEqual(report["verdict"], "drift_only")
        self.assertTrue(report["version_drift"]["detected"])
        self.assertFalse(report["semantic_loss"]["detected"])
        self.assertEqual(report["version_drift"]["baseline_version"], "0.8.0")
        self.assertEqual(report["version_drift"]["candidate_version"], "0.9.0")

    def test_changed_expected_pin_version_is_drift_only(self):
        baseline = jr_expected()
        candidate = copy.deepcopy(baseline)
        candidate["pin_version"] = "0.9.0"
        report = harness.compare(baseline, candidate, jr_anchor(), jr_anchor())
        self.assertEqual(report["verdict"], "drift_only")
        self.assertTrue(report["version_drift"]["detected"])


class SemanticLossIsHardFail(unittest.TestCase):
    def test_removed_projection_element_is_loss(self):
        baseline = jr_expected()
        candidate = copy.deepcopy(baseline)
        del candidate["projection"]["elements"]["btn-detail"]
        report = harness.compare(baseline, candidate, jr_anchor(), jr_anchor())
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["semantic_loss"]["detected"])
        paths = [d["path"] for d in report["semantic_loss"]["loss_diffs"]]
        self.assertTrue(any("btn-detail" in p for p in paths))

    def test_changed_component_type_is_loss(self):
        baseline = jr_expected()
        candidate = copy.deepcopy(baseline)
        candidate["projection"]["elements"]["home"]["type"] = "Text"
        report = harness.compare(baseline, candidate, jr_anchor(), jr_anchor())
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["semantic_loss"]["detected"])

    def test_catalog_conformance_regression_is_loss(self):
        baseline = jr_expected()
        candidate = copy.deepcopy(baseline)
        candidate["validation"]["catalog_conformance"]["component_names"] = ["Card"]
        report = harness.compare(baseline, candidate, jr_anchor(), jr_anchor())
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["semantic_loss"]["detected"])

    def test_semantic_equivalence_drop_is_loss(self):
        baseline = jr_expected()
        candidate = copy.deepcopy(baseline)
        candidate["semantic_equivalence"]["components"] = 1
        report = harness.compare(baseline, candidate, jr_anchor(), jr_anchor())
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["semantic_loss"]["detected"])


class UnknownRegressionIsHardFail(unittest.TestCase):
    def test_unknown_flag_regression_is_fail(self):
        baseline = load(JR / "FF-JR-IN-01" / "expected.json")
        candidate = copy.deepcopy(baseline)
        candidate["unknown_not_dropped"] = False
        report = harness.compare(baseline, candidate)
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["unknown_regression"]["detected"])
        self.assertEqual(
            report["unknown_regression"]["regressed"][0]["flag"],
            "unknown_not_dropped",
        )


class FieldDiffIsStructural(unittest.TestCase):
    def test_remove_and_change_ops_classified(self):
        baseline = {"a": 1, "b": {"c": 2}, "d": [1, 2]}
        candidate = {"b": {"c": 3}, "e": 9}
        diffs = harness.field_diff(baseline, candidate)
        ops = {d["path"]: d["op"] for d in diffs}
        self.assertEqual(ops.get("$.a"), "remove")
        self.assertEqual(ops.get("$.b.c"), "change")
        self.assertEqual(ops.get("$.d"), "remove")
        self.assertEqual(ops.get("$.e"), "add")


if __name__ == "__main__":
    unittest.main()

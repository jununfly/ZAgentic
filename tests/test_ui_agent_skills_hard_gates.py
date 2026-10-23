"""Guards for 1-5-3 hard gates (R-HAR-2) and their wiring into R-HAR-1.

Why these tests exist: a gate that has never been observed to fire is indistinguishable
from a gate that does nothing, and a gate that passes when evidence is missing is worse
than no gate at all. So this file asserts three things the docs claim:

1. every assertion code in the catalog is actually exercised by a negative case,
2. missing / empty / partial evidence can never reach PASS,
3. the runner surfaces those statuses instead of collapsing them into "not executed".

The synthetic bundles are gate-logic fixtures only — they are not acceptance evidence.
"""

import json
import pathlib
import re
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills/ui/zj-ui-core/scripts"
DOC = REPO / "skills/ui/zj-ui-core/contracts/hard-gates.md"

sys.path.insert(0, str(SKILL_DIR))
import hard_gates as hg  # noqa: E402
import dual_lane_runner as runner  # noqa: E402

PLANS = REPO / "skills/ui/zj-ui-core/contracts"
ALL_GATES = hg.SINGLE_BUNDLE_GATES + hg.CROSS_VIEWPORT_GATES


def _write_bundle(root, fixture_id, viewport, bundle):
    d = pathlib.Path(root) / fixture_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{viewport}.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")


class GateLogic(unittest.TestCase):
    def test_selftest_all_green(self):
        res = hg.selftest()
        self.assertTrue(res["ok"], [c for c in res["cases"] if not c["ok"]])
        self.assertEqual(res["failed"], 0)
        self.assertGreaterEqual(res["total"], 61)

    def test_every_catalog_code_is_exercised(self):
        """Anti-drift: no assertion code may exist without a case that proves it fires."""
        src = (SKILL_DIR / "hard_gates.py").read_text(encoding="utf-8")
        catalog = set(re.findall(r'"(HG-[A-Z]+-\d\d)"', src))
        exercised = {c["expected_code"] for c in hg.selftest()["cases"] if c["expected_code"]}
        self.assertEqual(sorted(catalog - exercised), [])
        self.assertGreaterEqual(len(catalog), 45)

    def test_doc_and_code_share_the_same_code_set(self):
        """The contract doc is not a second copy that silently drifts."""
        src = (SKILL_DIR / "hard_gates.py").read_text(encoding="utf-8")
        doc = DOC.read_text(encoding="utf-8")
        self.assertEqual(
            sorted(set(re.findall(r"(HG-[A-Z]+-\d\d)", src))),
            sorted(set(re.findall(r"(HG-[A-Z]+-\d\d)", doc))),
        )

    def test_missing_evidence_never_passes(self):
        for gate in ALL_GATES:
            with self.subTest(gate=gate):
                payload = {} if gate in hg.CROSS_VIEWPORT_GATES else {"fixture_id": "F-1"}
                res = hg.run_gate(gate, payload, thresholds=hg.GATE_THRESHOLDS)
                self.assertEqual(res["status"], "HUMAN_REVIEW_REQUIRED")
                self.assertNotEqual(hg.aggregate([res]), "PASS")

    def test_empty_sections_are_not_zero_defects(self):
        empty = {"fixture_id": "F-1", "dom": {"nodes": []}, "focus": {"sequence": []},
                 "contrast": {"samples": []}, "layout": {}, "motion": {"animations": []},
                 "states": {"transitions": []}}
        for gate in hg.SINGLE_BUNDLE_GATES:
            with self.subTest(gate=gate):
                self.assertEqual(hg.run_gate(gate, empty, thresholds=hg.GATE_THRESHOLDS)["status"],
                                 "HUMAN_REVIEW_REQUIRED")

    def test_status_precedence(self):
        cases = [
            (["PASS", "FAIL", "WARNING"], "FAIL"),
            (["PASS", "HUMAN_REVIEW_REQUIRED", "WARNING"], "HUMAN_REVIEW_REQUIRED"),
            (["PASS", "QUARANTINED"], "QUARANTINED"),
            (["PASS", "WARNING"], "WARNING"),
            (["PASS", "PASS"], "PASS"),
        ]
        for statuses, expected in cases:
            with self.subTest(statuses=statuses):
                self.assertEqual(hg.aggregate([{"status": s} for s in statuses]), expected)

    def test_quarantine_does_not_become_pass(self):
        bundle = hg.synthetic_good_bundle()
        bundle["quarantine"] = [{"code": "ADAPTER-FLAKY", "detail": "unstable render"}]
        res = hg.run_gate("dom_aria", bundle, thresholds=hg.GATE_THRESHOLDS)
        self.assertEqual(res["status"], "QUARANTINED")
        self.assertIn("HG-QUAR-01", {f["code"] for f in res["findings"]})

    def test_good_bundle_reaches_pass_with_real_checks(self):
        bundle = hg.synthetic_good_bundle()
        for gate in hg.SINGLE_BUNDLE_GATES:
            with self.subTest(gate=gate):
                res = hg.run_gate(gate, bundle, thresholds=hg.GATE_THRESHOLDS, fixture={"id": "F-1"})
                self.assertEqual(res["status"], "PASS")
                self.assertGreater(res["checked"], 0)

    def test_deterministic_output(self):
        a = json.dumps(hg.selftest(), sort_keys=True, ensure_ascii=False)
        b = json.dumps(hg.selftest(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(a, b)


class RunnerWiring(unittest.TestCase):
    def test_no_observations_is_blocked_not_pass(self):
        receipt = runner.run_lane("baseline", str(PLANS))
        self.assertEqual(receipt["overall"], "BLOCKED")
        self.assertEqual({c["status"] for c in receipt["cells"]}, {"NOT_EXECUTED"})

    def test_partial_coverage_never_yields_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            for vp in hg.REQUIRED_VIEWPORTS:
                _write_bundle(tmp, "F-1", vp, hg.synthetic_good_bundle(vp, "F-1"))
            receipt = runner.run_lane("baseline", str(PLANS), tmp)
            self.assertNotIn("PASS", {c["status"] for c in receipt["cells"]})
            self.assertEqual(receipt["overall"], "HUMAN_REVIEW_REQUIRED")
            form = [c for c in receipt["cells"] if c["dimension"] == "overflow" and c["class"] == "form"][0]
            self.assertEqual(form["status"], "HUMAN_REVIEW_REQUIRED")
            self.assertIn("F-2", form["observed"]["missing_fixtures"])

    def test_hard_failure_propagates_to_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            for vp in hg.REQUIRED_VIEWPORTS:
                bundle = hg.synthetic_good_bundle(vp, "F-1")
                if vp == "1440x900":
                    bundle["layout"]["document"]["scroll_width"] = 1600
                _write_bundle(tmp, "F-1", vp, bundle)
            receipt = runner.run_lane("baseline", str(PLANS), tmp)
            self.assertEqual(receipt["overall"], "FAIL")
            failing = {c["dimension"] for c in receipt["cells"] if c["status"] == "FAIL"}
            self.assertEqual(failing, {"overflow", "responsive"})
            overflow = [c for c in receipt["cells"] if c["dimension"] == "overflow"][0]
            self.assertIn("HG-OVF-01", {f["code"] for f in overflow["observed"]["findings"]})

    def test_receipt_carries_recomputable_keys(self):
        receipt = runner.run_lane("degraded", str(PLANS))
        for key in ("manifest_hash", "env_hash", "matrix_key", "config_hash", "config_version"):
            self.assertTrue(receipt.get(key), key)
        self.assertEqual(receipt["config_version"], runner.VERIFICATION_CONFIG["version"])
        self.assertEqual(runner.VERIFICATION_CONFIG["viewports"], hg.REQUIRED_VIEWPORTS)

    def test_fingerprint_is_reproducible(self):
        self.assertTrue(runner.selfcheck(str(PLANS))["rerun_idempotent"])


if __name__ == "__main__":
    unittest.main()

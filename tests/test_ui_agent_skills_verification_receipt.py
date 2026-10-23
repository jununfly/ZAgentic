"""Guards for 1-5-4 verification receipt (R-RCP-1).

What this file protects, and why:

1. a receipt may never say PASS unless every planned cell ran, passed, carried
   real evidence (bundles > 0) and a human signed off — otherwise the receipt is
   the same lie as an unchecked checkbox;
2. staleness must be *scoped*: a fixture edit re-runs that class, an env change
   re-runs everything, and expiry is not excused by unchanged hashes;
3. "unattributable" is a first-class result: it is recorded, counted separately,
   and never rewritten into PASS/FAIL;
4. the catalog of RCP-* codes in the doc is the same set the code can emit, and
   every one of them is exercised by a self-test case.

Synthetic lane receipts here are contract fixtures — not acceptance evidence.
"""

import json
import pathlib
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills/ui/zj-ui-core/scripts"
DOC = REPO / "skills/ui/zj-ui-core/contracts/verification-receipt.md"
PLANS = REPO / "skills/ui/zj-ui-core/contracts"

sys.path.insert(0, str(SKILL_DIR))
import hard_gates as hg  # noqa: E402
import dual_lane_runner as runner  # noqa: E402
import verification_receipt as vr  # noqa: E402

SIGNED = {"name": "zj", "signed_at": "2026-10-20T00:00:00+00:00"}
COMMIT = "a" * 40
ISSUED = datetime(2026, 10, 20, tzinfo=timezone.utc)


def _all_pass_lane(bundles=3, checked=5):
    """A fully-covered baseline receipt that *claims* PASS (for sign-off tests)."""
    fp = runner.fingerprint(str(PLANS), write=False)
    manifest = runner.load_json(str(PLANS / "fixture-manifest.json"))
    cells = []
    for cell in runner.plan_cells("baseline"):
        cells.append({
            **cell,
            "status": "PASS",
            "reason": "",
            "observed": {"gate": cell["dimension"], "fixtures_seen": 1, "bundles": bundles,
                         "missing_fixtures": [], "findings": [], "checked": checked},
        })
    return {
        "lane": "baseline", "run_id": "run-test-pass",
        "manifest_hash": runner.compute_manifest_hash(manifest),
        "env_hash": fp["env_hash"], "matrix_key": fp["matrix_key"],
        "config_version": runner.VERIFICATION_CONFIG["version"],
        "config_hash": fp["config_hash"], "observations_dir": "/tmp/observations",
        "cells": cells,
    }


class ReceiptSelfTest(unittest.TestCase):
    def test_selftest_all_green(self):
        res = vr.selftest()
        self.assertTrue(res["ok"], [c for c in res["cases"] if not c["ok"]])
        self.assertEqual(res["failed"], 0)
        self.assertGreaterEqual(res["total"], 34)

    def test_every_catalog_code_is_exercised(self):
        """Anti-drift: no RCP code may exist without a case that proves it fires."""
        src = (SKILL_DIR / "verification_receipt.py").read_text(encoding="utf-8")
        catalog = set(re.findall(r'"(RCP-[A-Z]-\d\d)"', src))
        exercised = {c["expected_code"] for c in vr.selftest()["cases"] if c["expected_code"]}
        self.assertEqual(sorted(catalog - exercised), [])
        self.assertEqual(sorted(exercised - catalog), [])
        self.assertGreaterEqual(len(catalog), 26)

    def test_doc_and_code_share_the_same_code_set(self):
        src = (SKILL_DIR / "verification_receipt.py").read_text(encoding="utf-8")
        doc = DOC.read_text(encoding="utf-8")
        self.assertEqual(
            sorted(set(re.findall(r"(RCP-[A-Z]-\d\d)", src))),
            sorted(set(re.findall(r"(RCP-[A-Z]-\d\d)", doc))),
        )

    def test_deterministic_selftest(self):
        a = json.dumps(vr.selftest(), sort_keys=True, ensure_ascii=False)
        b = json.dumps(vr.selftest(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(a, b)


class ReceiptShape(unittest.TestCase):
    def test_all_required_sections_present(self):
        receipt = vr.build_receipt(runner.run_lane("baseline", str(PLANS)),
                                   commit=COMMIT, issued_at=ISSUED)
        for field in vr.IDENTITY_FIELDS + vr.REQUIRED_SECTIONS:
            self.assertIn(field, receipt)
        self.assertEqual(receipt["schema"], vr.SCHEMA)
        self.assertTrue(receipt["receipt_id"].startswith("rcp-"))
        self.assertEqual(receipt["commit"], COMMIT)
        # checks 每个 cell 都要自带判据快照，收据才能离线复核
        for check in receipt["checks"]:
            self.assertIn("threshold", check)
            self.assertIn("oracle", check)
            self.assertTrue(check["command"])

    def test_no_observation_baseline_is_blocked_and_valid(self):
        receipt = vr.build_receipt(runner.run_lane("baseline", str(PLANS)),
                                   commit=COMMIT, issued_at=ISSUED)
        self.assertEqual(receipt["status"]["verdict"], "BLOCKED")
        self.assertEqual(receipt["status"]["raw_verdict"], "BLOCKED")
        self.assertEqual(len(receipt["checks"]), len(runner.plan_cells("baseline")))
        self.assertEqual(vr.validate(receipt)["codes"], [])

    def test_degraded_lane_never_passes(self):
        receipt = vr.build_receipt(runner.run_lane("degraded", str(PLANS)),
                                   commit=COMMIT, issued_at=ISSUED)
        self.assertNotEqual(receipt["status"]["verdict"], "PASS")
        self.assertEqual(receipt["status"]["coverage"]["passed_cells"], 0)
        self.assertEqual(vr.validate(receipt)["codes"], [])

    def test_counts_reconcile_with_checks(self):
        for lane in ("baseline", "degraded"):
            with self.subTest(lane=lane):
                receipt = vr.build_receipt(runner.run_lane(lane, str(PLANS)),
                                           commit=COMMIT, issued_at=ISSUED)
                agg = vr.aggregate_cells(receipt["checks"])
                self.assertEqual(receipt["status"]["counts"], agg["counts"])
                self.assertEqual(sum(agg["counts"].values()), len(receipt["checks"]))
                self.assertEqual(agg["attributable"] + agg["excluded"], agg["planned_cells"])

    def test_build_is_deterministic(self):
        lane = runner.run_lane("degraded", str(PLANS))
        a = vr.build_receipt(lane, commit=COMMIT, issued_at=ISSUED)
        b = vr.build_receipt(lane, commit=COMMIT, issued_at=ISSUED)
        self.assertEqual(vr.canonical_json(a), vr.canonical_json(b))


class PassRequirements(unittest.TestCase):
    def test_pass_without_signoff_is_downgraded(self):
        receipt = vr.build_receipt(_all_pass_lane(), commit=COMMIT, issued_at=ISSUED)
        self.assertEqual(receipt["status"]["verdict"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("RCP-A-07", receipt["status"]["reason_codes"])
        self.assertEqual(vr.validate(receipt)["codes"], [])

    def test_pass_with_unpinned_commit_is_downgraded(self):
        receipt = vr.build_receipt(_all_pass_lane(), commit="UNPINNED", issued_at=ISSUED,
                                   reviewer=SIGNED)
        self.assertEqual(receipt["status"]["verdict"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("RCP-A-08", receipt["status"]["reason_codes"])

    def test_dirty_worktree_blocks_pass(self):
        receipt = vr.build_receipt(_all_pass_lane(), commit=COMMIT, issued_at=ISSUED,
                                   reviewer=SIGNED, worktree_dirty=True)
        self.assertEqual(receipt["status"]["verdict"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("RCP-A-08", receipt["status"]["reason_codes"])

    def test_signed_pinned_pass_validates_and_is_fresh(self):
        receipt = vr.build_receipt(_all_pass_lane(), commit=COMMIT, issued_at=ISSUED,
                                   reviewer=SIGNED)
        self.assertEqual(receipt["status"]["verdict"], "PASS")
        self.assertEqual(vr.validate(receipt)["codes"], [])
        fresh = vr.check_freshness(receipt, plans_dir=str(PLANS), now=ISSUED)
        self.assertEqual(fresh["status"], "FRESH")
        self.assertFalse(fresh["revalidate"]["required"])

    def test_pass_without_any_bundle_is_rejected(self):
        receipt = vr.build_receipt(_all_pass_lane(bundles=0), commit=COMMIT,
                                   issued_at=ISSUED, reviewer=SIGNED)
        codes = vr.validate(receipt)["codes"]
        self.assertIn("RCP-A-09", codes)

    def test_partial_coverage_never_reaches_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            for vp in hg.REQUIRED_VIEWPORTS:
                d = pathlib.Path(tmp) / "F-1"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{vp}.json").write_text(
                    json.dumps(hg.synthetic_good_bundle(vp, "F-1")), encoding="utf-8")
            receipt = vr.build_receipt(
                runner.run_lane("baseline", str(PLANS), tmp),
                commit=COMMIT, issued_at=ISSUED, reviewer=SIGNED)
        self.assertNotEqual(receipt["status"]["verdict"], "PASS")
        self.assertEqual(receipt["status"]["coverage"]["passed_cells"], 0)


class Freshness(unittest.TestCase):
    def setUp(self):
        self.receipt = vr.build_receipt(_all_pass_lane(), commit=COMMIT,
                                        issued_at=ISSUED, reviewer=SIGNED)
        self.facts = vr.current_facts(str(PLANS))

    def test_fixture_drift_scopes_to_affected_class(self):
        facts = json.loads(json.dumps(self.facts))
        entry = facts["fixtures"]["entries"][0]
        entry["sha256"] = "0" * 64
        res = vr.check_freshness(self.receipt, facts=facts, now=ISSUED)
        self.assertEqual(res["status"], "STALE")
        self.assertTrue(res["revalidate"]["required"])
        self.assertEqual(res["revalidate"]["scope"], "cells")
        expected = {c["cell"] for c in self.receipt["checks"] if c["class"] == entry["class"]}
        self.assertEqual(set(res["revalidate"]["cells"]), expected)
        self.assertIn("RCP-F-02", res["revalidate"]["reason_codes"])

    def test_threshold_drift_scopes_to_consuming_dimensions(self):
        facts = json.loads(json.dumps(self.facts))
        facts["thresholds"]["overflow_px"] = 2
        res = vr.check_freshness(self.receipt, facts=facts, now=ISSUED)
        self.assertEqual(res["status"], "STALE")
        dims = {cell.split("/")[0] for cell in res["revalidate"]["cells"]}
        self.assertEqual(dims, {"overflow", "responsive"})
        self.assertIn("RCP-F-03", res["revalidate"]["reason_codes"])

    def test_env_drift_requires_full_revalidation(self):
        facts = json.loads(json.dumps(self.facts))
        facts["env_hash"] = "z" * 64
        res = vr.check_freshness(self.receipt, facts=facts, now=ISSUED)
        self.assertEqual(res["status"], "REVALIDATION_REQUIRED")
        self.assertEqual(res["revalidate"]["scope"], "all")
        self.assertEqual(set(res["revalidate"]["cells"]),
                         {c["cell"] for c in self.receipt["checks"]})

    def test_expiry_is_not_excused_by_unchanged_hashes(self):
        later = datetime(2027, 6, 1, tzinfo=timezone.utc)
        res = vr.check_freshness(self.receipt, facts=self.facts, now=later)
        self.assertEqual(res["status"], "REVALIDATION_REQUIRED")
        self.assertIn("RCP-F-05", res["revalidate"]["reason_codes"])

    def test_missing_facts_are_conservative(self):
        res = vr.check_freshness(self.receipt, facts={"error": "FileNotFoundError: manifest"},
                                 now=ISSUED)
        self.assertEqual(res["status"], "REVALIDATION_REQUIRED")
        self.assertEqual(res["revalidate"]["scope"], "all")

    def test_clean_receipt_is_fresh(self):
        res = vr.check_freshness(self.receipt, facts=self.facts, now=ISSUED)
        self.assertEqual(res["status"], "FRESH")
        self.assertEqual(res["revalidate"]["reason_codes"], [])


class Quarantine(unittest.TestCase):
    def test_unattributable_is_counted_and_never_pass_or_fail(self):
        receipt = vr.build_receipt(
            _all_pass_lane(), commit=COMMIT, issued_at=ISSUED, reviewer=SIGNED,
            quarantine_records=[{"code": "ADAPTER-FLAKY", "dimension": "overflow",
                                 "evidence": ["a.png"], "release_condition": "重跑 3 次稳定"}])
        self.assertEqual(receipt["status"]["verdict"], "QUARANTINED")
        self.assertEqual(receipt["status"]["quarantine"]["unattributable"], 1)
        self.assertEqual(receipt["status"]["quarantine"]["attributed"], 0)
        self.assertNotIn(receipt["status"]["verdict"], ("PASS", "FAIL"))
        self.assertIn("RCP-Q-01", receipt["status"]["reason_codes"])
        self.assertEqual(vr.validate(receipt)["codes"], [])

    def test_attributable_record_can_be_located(self):
        res = vr.validate_quarantine(
            [{"code": "ADAPTER-FLAKY", "fixture": "F-1", "dimension": "overflow",
              "viewport": "390x844", "evidence": ["a.png"], "release_condition": "重跑 3 次稳定"}],
            fixture_ids=["F-1"])
        self.assertEqual(res["codes"], [])
        self.assertEqual(res["counts"]["attributed"], 1)
        self.assertEqual(res["verdict"], "QUARANTINED")

    def test_unknown_fixture_is_unattributable(self):
        res = vr.validate_quarantine(
            [{"code": "X", "fixture": "F-999", "dimension": "overflow",
              "viewport": "390x844", "evidence": ["a"], "release_condition": "r"}],
            fixture_ids=["F-1"])
        self.assertIn("RCP-Q-01", res["codes"])

    def test_quarantine_cannot_be_resolved_in_place(self):
        self.assertIn("RCP-Q-03", vr.validate_quarantine(
            [{"code": "X", "fixture": "F-1", "dimension": "overflow", "viewport": "390x844",
              "evidence": ["a"], "release_condition": "r", "resolution": "PASS"}],
            fixture_ids=["F-1"])["codes"])

    def test_release_needs_new_run_and_reviewer(self):
        record = {"fixture": "F-1"}
        self.assertIn("RCP-Q-04", vr.can_release(record, new_run_id="run-a",
                                                 reviewer=SIGNED, old_run_id="run-a")["codes"])
        self.assertIn("RCP-Q-04", vr.can_release(record, new_run_id="run-b",
                                                 reviewer={"name": "zj"},
                                                 old_run_id="run-a")["codes"])
        self.assertTrue(vr.can_release(record, new_run_id="run-b", reviewer=SIGNED,
                                       old_run_id="run-a")["released"])


class Immutability(unittest.TestCase):
    def test_same_receipt_id_with_new_body_is_rejected(self):
        receipt = vr.build_receipt(_all_pass_lane(), commit=COMMIT, issued_at=ISSUED,
                                   reviewer=SIGNED)
        mutated = json.loads(json.dumps(receipt))
        mutated["claim"]["asserts"] = "改过的声明"
        codes = vr.validate(mutated, previous=receipt)["codes"]
        self.assertIn("RCP-V-07", codes)

    def test_new_run_id_is_a_new_receipt(self):
        a = vr.build_receipt(_all_pass_lane(), commit=COMMIT, issued_at=ISSUED, reviewer=SIGNED)
        lane = _all_pass_lane()
        lane["run_id"] = "run-test-pass-2"
        b = vr.build_receipt(lane, commit=COMMIT, issued_at=ISSUED, reviewer=SIGNED)
        self.assertNotEqual(a["receipt_id"], b["receipt_id"])
        self.assertEqual(vr.validate(b, previous=a)["codes"], [])


class RunnerWiring(unittest.TestCase):
    def test_runner_records_checked_count(self):
        """RCP-A-05 depends on `checked`; runner must not drop it on the floor."""
        with tempfile.TemporaryDirectory() as tmp:
            for vp in hg.REQUIRED_VIEWPORTS:
                d = pathlib.Path(tmp) / "F-1"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{vp}.json").write_text(
                    json.dumps(hg.synthetic_good_bundle(vp, "F-1")), encoding="utf-8")
            lane = runner.run_lane("baseline", str(PLANS), tmp)
        dom = [c for c in lane["cells"] if c["dimension"] == "dom_aria" and c["class"] == "form"][0]
        self.assertGreater(dom["observed"]["checked"], 0)

    def test_fingerprint_still_reproducible(self):
        self.assertTrue(runner.selfcheck(str(PLANS))["rerun_idempotent"])


if __name__ == "__main__":
    unittest.main()

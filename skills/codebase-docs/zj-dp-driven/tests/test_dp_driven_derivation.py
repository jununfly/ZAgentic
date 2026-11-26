#!/usr/bin/env python3
"""§3.5 form-②③ / §7 Q1 溯源边列 — invariant locks (Phase-3b).

finding→new-finding and finding→new-task materialization provenance, expressed as a
`derived_from_finding` column mirroring the §7 Q1(a) ticket column (single-parent, thin
table). Locked: round-trip persistence, validate dangling refs, optimizer adjacency,
closeout snapshot. Run: python tests/test_dp_driven_derivation.py
"""

import os
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

from dp_driven_model import (
    DpDriven, DpDrivenError, KIND_FINDING, KIND_TASK, KIND_TICKET, S_DONE,
)
import dp_driven_optimize as opt


def fresh() -> DpDriven:
    d = tempfile.TemporaryDirectory()
    m = DpDriven.init(os.path.join(d.name, "x.sqlite"), destination="d")
    m._tmp = d
    return m


class DerivationForms(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_form2_finding_from_finding(self):
        parent = self.m.add_finding(now="t0")
        child = self.m.add_finding(derived_from_finding=parent, now="t1")
        self.assertEqual(self.m.data["findings"][str(child)]["derived_from_finding"], parent)

    def test_form3_task_from_finding(self):
        source = self.m.add_finding(now="t0")
        tid = self.m.add_task("灵感开辟的新区域", derived_from_finding=source)
        self.assertEqual(self.m.data["tasks"][str(tid)]["derived_from_finding"], source)
        # task still has no stored status; derived via 1:1 plan (§3.1 unaffected)
        self.assertNotIn("status", self.m.data["tasks"][str(tid)])

    def test_source_must_exist(self):
        with self.assertRaises(DpDrivenError) as cm:
            self.m.add_finding(derived_from_finding=999)
        self.assertEqual(cm.exception.code, "E_NO_SUCH_FINDING")
        with self.assertRaises(DpDrivenError) as cm:
            self.m.add_task("t", derived_from_finding=999)
        self.assertEqual(cm.exception.code, "E_NO_SUCH_FINDING")

    def test_disposition_chain_not_reprocessed(self):
        """§3.5: disposing the parent clears its memberships once; the child it derived
        is an independent open node that will be dispositioned separately (no re-run of
        the parent)."""
        tid = self.m.add_task("宿主")
        parent = self.m.add_finding(now="t0")
        self.m.add_finding_membership(parent, tid)
        child = self.m.add_finding(derived_from_finding=parent, now="t1")
        self.m.dispose_finding(parent, to=S_DONE)
        self.assertEqual(self.m.find_memberships(parent), [])   # 摘除
        self.assertEqual(self.m.data["findings"][str(child)]["status"], "未完成")
        self.assertEqual(self.m.data["findings"][str(child)]["derived_from_finding"], parent)

    def test_round_trip_persistence(self):
        parent = self.m.add_finding(now="t0")
        child = self.m.add_finding(derived_from_finding=parent, now="t1")
        tid = self.m.add_task("新区域", derived_from_finding=parent)
        self.m.save()
        r = DpDriven.open(self.m.db_path)
        self.assertEqual(r.data["findings"][str(child)]["derived_from_finding"], parent)
        self.assertEqual(r.data["tasks"][str(tid)]["derived_from_finding"], parent)
        self.assertEqual(r.validate(), [])


class Validation(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_clean_derivation_validates_empty(self):
        p = self.m.add_finding(now="t0")
        self.m.add_finding(derived_from_finding=p)
        self.m.add_task("x", derived_from_finding=p)
        self.assertEqual(self.m.validate(), [])

    def test_dangling_finding_derivation(self):
        p = self.m.add_finding(now="t0")
        c = self.m.add_finding(derived_from_finding=p)
        self.m.data["findings"][str(c)]["derived_from_finding"] = 4242
        self.assertTrue(any("E_REF_MISSING" in e for e in self.m.validate()))

    def test_dangling_task_derivation(self):
        p = self.m.add_finding(now="t0")
        tid = self.m.add_task("x", derived_from_finding=p)
        self.m.data["tasks"][str(tid)]["derived_from_finding"] = 9999
        self.assertTrue(any("E_REF_MISSING" in e for e in self.m.validate()))


class OptimizerAdjacency(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_finding_finding_provenance_is_relation(self):
        p = self.m.add_finding(now="t0")
        c = self.m.add_finding(derived_from_finding=p, now="t1")
        rels = opt._relations(self.m)
        self.assertIn(frozenset(((KIND_FINDING, c), (KIND_FINDING, p))), rels)

    def test_finding_task_provenance_is_relation(self):
        p = self.m.add_finding(now="t0")
        tid = self.m.add_task("x", derived_from_finding=p)
        rels = opt._relations(self.m)
        self.assertIn(frozenset(((KIND_TASK, tid), (KIND_FINDING, p))), rels)

    def test_backward_safe_no_derivation(self):
        """Without any derived_from_finding set, _relations matches Phase-3a behavior
        (only blocks/parent/ticket-derived) — proves the new code doesn't change prior data."""
        a = self.m.add_ticket(now="t0"); b = self.m.add_ticket(now="t1")
        self.m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        rels = opt._relations(self.m)
        self.assertEqual(rels, {frozenset(((KIND_TICKET, a), (KIND_TICKET, b)))})


class CloseoutSnapshot(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_summary_lists_derivation(self):
        p = self.m.add_finding(now="t0")
        c = self.m.add_finding(derived_from_finding=p, now="t1")
        tid = self.m.add_task("x", derived_from_finding=p)
        self.m.dispose_finding(p, to=S_DONE)
        self.m.dispose_finding(c, to=S_DONE)
        self.m.set_plan_status(tid, S_DONE)
        out = os.path.join(tempfile.mkdtemp(), "s.md")
        self.m.closeout_export_summary(out)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("Finding derivation", text)
        self.assertIn(f"| {p} | finding | {c} |", text)     # form ②
        self.assertIn(f"| {p} | task | {tid} |", text)       # form ③


if __name__ == "__main__":
    unittest.main(verbosity=2)

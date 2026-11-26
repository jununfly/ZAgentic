#!/usr/bin/env python3
"""§4.4 two-layer claim — invariant locks for zj-dp-driven.

Tests the plan-level / ticket-level claim gate + the lock-free exemptions that
design §4.4 explicitly names (finding disposition, hotplug add).
"""

import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_model as m
from dp_driven_model import (
    DpDriven, DpDrivenError, SETTLEMENT_AGENT, S_DONE,
)


class ClaimBasic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"),
                                   destination="d", now="t0")

    def test_plan_claim_newly_acquired(self):
        tid = self.model.add_task("甲")
        self.assertTrue(self.model.claim(m.CLAIM_PLAN, tid, agent="alice"))

    def test_claim_same_agent_twice_is_noop(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        self.assertFalse(self.model.claim(m.CLAIM_PLAN, tid, agent="alice"))

    def test_claim_conflict_by_other_agent(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        with self.assertRaises(DpDrivenError) as cm:
            self.model.claim(m.CLAIM_PLAN, tid, agent="bob")
        self.assertEqual(cm.exception.code, "E_CLAIM_HELD_BY_OTHER")

    def test_claim_missing_ref(self):
        with self.assertRaises(DpDrivenError) as cm:
            self.model.claim(m.CLAIM_PLAN, 999, agent="alice")
        self.assertEqual(cm.exception.code, "E_NO_SUCH_TASK")
        with self.assertRaises(DpDrivenError) as cm:
            self.model.claim(m.CLAIM_TICKET, 999, agent="alice")
        self.assertEqual(cm.exception.code, "E_NO_SUCH_TICKET")

    def test_claim_invalid_kind(self):
        with self.assertRaises(DpDrivenError) as cm:
            self.model.claim("bogus", 1, agent="alice")
        self.assertEqual(cm.exception.code, "E_INVALID_KIND")

    def test_release_by_owner(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        self.assertTrue(self.model.release(m.CLAIM_PLAN, tid, agent="alice"))
        self.assertIsNone(self.model.claim_owner(m.CLAIM_PLAN, tid))

    def test_release_by_wrong_owner_rejected(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        with self.assertRaises(DpDrivenError) as cm:
            self.model.release(m.CLAIM_PLAN, tid, agent="bob")
        self.assertEqual(cm.exception.code, "E_CLAIM_NOT_OWNER")

    def test_release_force_bypasses_owner(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        self.assertTrue(self.model.release(m.CLAIM_PLAN, tid, force=True))
        self.assertIsNone(self.model.claim_owner(m.CLAIM_PLAN, tid))

    def test_claim_owner_and_list(self):
        t1 = self.model.add_task("甲")
        t2 = self.model.add_task("乙")
        tk = self.model.add_ticket()
        self.model.claim(m.CLAIM_PLAN, t1, agent="alice")
        self.model.claim(m.CLAIM_TICKET, tk, agent="bob")
        self.assertEqual(self.model.claim_owner(m.CLAIM_PLAN, t1), "alice")
        self.assertIsNone(self.model.claim_owner(m.CLAIM_PLAN, t2))
        rows = self.model.list_claims()
        self.assertEqual(len(rows), 2)
        self.assertEqual({(r["kind"], r["ref_id"]) for r in rows},
                         {(m.CLAIM_PLAN, t1), (m.CLAIM_TICKET, tk)})


class PlanStatusGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"), "d")

    def test_agentless_write_bypasses_gate(self):
        tid = self.model.add_task("甲")
        self.model.set_plan_status(tid, S_DONE)   # no agent → Human direct
        self.assertEqual(self.model.task_view(tid)["status"], S_DONE)

    def test_owner_agent_writes_ok(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        self.model.set_plan_status(tid, S_DONE, agent="alice")

    def test_other_agent_write_denied(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        with self.assertRaises(DpDrivenError) as cm:
            self.model.set_plan_status(tid, S_DONE, agent="bob")
        self.assertEqual(cm.exception.code, "E_CLAIM_HELD_BY_OTHER")


class TicketStatusGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"), "d")

    def test_ticket_claim_gates_status(self):
        tk = self.model.add_ticket()
        self.model.claim(m.CLAIM_TICKET, tk, agent="alice")
        with self.assertRaises(DpDrivenError) as cm:
            self.model.set_ticket_status(tk, S_DONE, agent="bob")
        self.assertEqual(cm.exception.code, "E_CLAIM_HELD_BY_OTHER")
        self.model.set_ticket_status(tk, S_DONE, agent="alice")   # owner ok
        self.assertEqual(self.model.data["tickets"][str(tk)]["status"], S_DONE)

    def test_unclaimed_ticket_is_free_for_any(self):
        tk = self.model.add_ticket()
        self.model.set_ticket_status(tk, S_DONE, agent="whoever")
        self.assertEqual(self.model.data["tickets"][str(tk)]["status"], S_DONE)


class LockFreeOperations(unittest.TestCase):
    """§4.4 [定稿]: finding 处置 + 热插 add 不受 claim 约束."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"), "d")

    def test_dispose_finding_lock_free(self):
        t1 = self.model.add_task("甲")
        t2 = self.model.add_task("乙")
        f = self.model.add_finding()
        self.model.add_finding_membership(f, t1)
        self.model.add_finding_membership(f, t2)
        self.model.claim(m.CLAIM_PLAN, t1, agent="alice")
        # Even with alice claiming plan t1, another agent may dispose a finding
        # hanging on that plan (finding is a global layer-2 node).
        self.model.dispose_finding(f, to=S_DONE)
        self.assertEqual(self.model.find_memberships(f), [])

    def test_hotplug_add_lock_free(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        # §4.3 hotplug add — another agent's ticket can be added to a claimed plan.
        tk = self.model.add_ticket()
        self.model.assign_ticket(tk, tid)
        self.assertEqual(self.model.data["tickets"][str(tk)]["task_id"], tid)

    def test_blocks_edge_add_lock_free(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        a = self.model.add_ticket()
        b = self.model.add_ticket()
        self.model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)
        self.assertEqual(len(self.model.data["edges"]), 1)


class SettlementPlanGate(unittest.TestCase):
    """§4.5: settlement plan's plan-claim gate is bypassed for any agent."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"), "d")

    def test_settlement_plan_claim_bypass(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run()
        # Settlement sentinel is the plan claim's agent. Any caller can set status.
        self.assertEqual(self.model.claim_owner(m.CLAIM_PLAN, tid), SETTLEMENT_AGENT)
        self.model.set_plan_status(tid, S_DONE, agent="whoever")   # bypass
        self.assertEqual(self.model.task_view(tid)["status"], S_DONE)

    def test_release_of_settlement_needs_force(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run()
        with self.assertRaises(DpDrivenError) as cm:
            self.model.release(m.CLAIM_PLAN, tid, agent="whoever")
        self.assertEqual(cm.exception.code, "E_CLAIM_NOT_OWNER")
        self.assertTrue(self.model.release(m.CLAIM_PLAN, tid, force=True))


class ValidateClaims(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DpDriven.init(str(Path(self.tmp.name) / "dp_driven.sqlite"), "d")

    def test_clean_claims_validate_empty(self):
        tid = self.model.add_task("甲")
        self.model.claim(m.CLAIM_PLAN, tid, agent="alice")
        self.assertEqual(self.model.validate(), [])

    def test_detects_unknown_kind_and_missing_ref(self):
        self.model.data["claims"].append({"kind": "bogus", "ref_id": 0, "agent": "a", "claimed_at": "t"})
        self.model.data["claims"].append({"kind": m.CLAIM_PLAN, "ref_id": 999, "agent": "a", "claimed_at": "t"})
        errs = self.model.validate()
        self.assertTrue(any("E_CLAIM_KIND" in e for e in errs))
        self.assertTrue(any("E_CLAIM_REF_MISSING" in e for e in errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)

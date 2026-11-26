#!/usr/bin/env python3
"""§4.5 settlement round — invariant locks."""

import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_model as m
from dp_driven_model import DpDriven, DpDrivenError, KIND_FINDING, KIND_TICKET, SETTLEMENT_AGENT, S_DONE


def fresh() -> DpDriven:
    tmp = tempfile.TemporaryDirectory()
    model = DpDriven.init(str(Path(tmp.name) / "dp_driven.sqlite"), destination="d", now="t0")
    model._tmp = tmp
    return model


class SettlementBasics(unittest.TestCase):
    def setUp(self):
        self.model = fresh()
        self.addCleanup(self.model._tmp.cleanup)

    def test_empty_pool_rejected(self):
        with self.assertRaises(DpDrivenError) as cm:
            self.model.settlement_run()
        self.assertEqual(cm.exception.code, "E_POOL_EMPTY")

    def test_settlement_absorbs_everything_in_pool(self):
        # two unassigned tickets + one orphan finding + one already-placed ticket
        t1 = self.model.add_task("甲")
        placed = self.model.add_ticket(task_id=t1)
        tk0 = self.model.add_ticket()          # pool
        tk1 = self.model.add_ticket()          # pool
        f0 = self.model.add_finding()          # orphan → pool
        f1 = self.model.add_finding()
        self.model.add_finding_membership(f1, t1)   # member → not pool
        tid, items = self.model.settlement_run()
        got = {(i["kind"], i["id"]) for i in items}
        self.assertEqual(got, {(KIND_TICKET, tk0), (KIND_TICKET, tk1), (KIND_FINDING, f0)})
        self.assertEqual(self.model.pool(), [])         # pool drained
        # tickets moved into settlement plan
        for tk in (tk0, tk1):
            self.assertEqual(self.model.data["tickets"][str(tk)]["task_id"], tid)
        # orphan finding gained membership to settlement plan
        self.assertIn(tid, self.model.find_memberships(f0))
        # pre-assigned items untouched
        self.assertEqual(self.model.data["tickets"][str(placed)]["task_id"], t1)
        self.assertIn(t1, self.model.find_memberships(f1))

    def test_settlement_order_blocks_topo_first_then_id(self):
        # tk0 blocks tk1 (tk1 depends on tk0). tk2 independent.
        tk0 = self.model.add_ticket()
        tk1 = self.model.add_ticket()
        tk2 = self.model.add_ticket()
        self.model.add_blocks(KIND_TICKET, tk0, KIND_TICKET, tk1)
        tid, items = self.model.settlement_run()
        # Kahn layer 0: {tk0, tk2}, sorted → tk0 first (id 0), then tk2 (id 2).
        # Pop tk0 → tk1 in-degree drops to 0 → sorted ready [tk1, tk2] → tk1 (id 1).
        self.assertEqual([it["id"] for it in items], [tk0, tk1, tk2])

    def test_settlement_finding_after_tickets(self):
        # order_key puts tickets before findings at same level.
        t1 = self.model.add_finding()
        t2 = self.model.add_ticket()
        _, items = self.model.settlement_run()
        # both are ready (no edges). ticket-first.
        self.assertEqual([(i["kind"], i["id"]) for i in items],
                         [(KIND_TICKET, t2), (KIND_FINDING, t1)])


class SettlementPlanSemantics(unittest.TestCase):
    def setUp(self):
        self.model = fresh()
        self.addCleanup(self.model._tmp.cleanup)

    def test_settlement_plan_claim_sentinel(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run()
        self.assertEqual(self.model.claim_owner(m.CLAIM_PLAN, tid), SETTLEMENT_AGENT)

    def test_settlement_plan_name_defaults(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run()
        self.assertEqual(self.model.data["tasks"][str(tid)]["name"], "结算轮")

    def test_settlement_plan_name_override(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run(name="收尾")
        self.assertEqual(self.model.data["tasks"][str(tid)]["name"], "收尾")

    def test_after_settlement_still_open_until_terminal(self):
        tk = self.model.add_ticket()
        tid, _ = self.model.settlement_run()
        self.assertFalse(self.model.is_complete())
        # Human closes the whole thing.
        self.model.set_ticket_status(tk, S_DONE)
        self.model.set_plan_status(tid, S_DONE, agent="whoever")   # settlement bypass
        self.assertTrue(self.model.is_complete())


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""SQLite carrier round-trip for zj-dp-driven.

Proves the §2 carrier (五实体 sqlite 表) persists and reloads without drift, and that the
derived-state views (§3 blocked / task projection / pool) are identical before save and
after reload — i.e. nothing was accidentally stored that should be derived.

Run: python tests/test_dp_driven_carrier.py
"""

import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_carrier as carrier
import dp_driven_model as m
from dp_driven_model import DpDriven, S_DONE


class CarrierRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self) -> DpDriven:
        model = DpDriven.init(self.db, destination="上线 v2", now="t0")
        t1 = model.add_task("后端登录", context_md="docs/plans/dp-driven/login/context.md", now="t1")
        t2 = model.add_task("前端登录", now="t2")
        a = model.add_ticket(task_id=t1, ref="gh#10", kv={"owner": "me"}, now="t3")
        b = model.add_ticket(task_id=t2, derived_from_finding=None, parent_id=a, now="t4")
        f = model.add_finding(md_path="docs/plans/dp-driven/login/f.md", now="t5")
        model.add_finding_membership(f, t1)
        model.add_finding_membership(f, t2)          # 多归属
        model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)
        model.add_blocks(m.KIND_FINDING, f, m.KIND_TICKET, b)
        model.set_ticket_status(a, S_DONE, now="t6")
        model.set_plan_status(t1, S_DONE, summary="后端就绪", now="t7")
        model.save()
        return model

    def test_is_db_path_routing(self):
        self.assertTrue(carrier.is_db_path("x/dp_driven.sqlite"))
        self.assertTrue(carrier.is_db_path("x/dp_driven.db"))
        self.assertFalse(carrier.is_db_path("x/dp_driven.json"))

    def test_reload_preserves_all_entities(self):
        model = self.build()
        reloaded = DpDriven.open(self.db)
        self.assertEqual(model.data["meta"]["destination"], "上线 v2")
        self.assertEqual(reloaded.data["meta"]["destination"], "上线 v2")
        self.assertEqual(reloaded.data["tasks"], model.data["tasks"])
        self.assertEqual(reloaded.data["plans"], model.data["plans"])
        self.assertEqual(reloaded.data["findings"], model.data["findings"])
        self.assertEqual(reloaded.data["tickets"], model.data["tickets"])
        self.assertEqual(reloaded.data["memberships"], model.data["memberships"])
        self.assertEqual(reloaded.data["edges"], model.data["edges"])

    def test_kv_json_round_trips(self):
        self.build()
        reloaded = DpDriven.open(self.db)
        self.assertEqual(reloaded.data["tickets"]["0"]["kv"], {"owner": "me"})

    def test_derived_views_survive_reload(self):
        model = self.build()
        reloaded = DpDriven.open(self.db)
        # blocked on ticket b: prereq a is done, but finding f (still open) blocks b
        self.assertEqual(
            model.node_view(m.KIND_TICKET, 1),
            reloaded.node_view(m.KIND_TICKET, 1),
        )
        self.assertTrue(reloaded.node_view(m.KIND_TICKET, 1)["derived_blocked"])
        # task1 done → task view derived (not stored) identically after reload
        self.assertEqual(model.task_view(0), reloaded.task_view(0))
        self.assertEqual(reloaded.task_view(0)["status"], S_DONE)
        # pool: no unassigned open tickets/findings left except none → both models agree
        self.assertEqual(model.pool(), reloaded.pool())

    def test_blocked_never_persisted(self):
        # §3.2 hard check: no ticket/finding/plan column may hold 被阻塞 after a save,
        # even though a view derives it. Proves blocked is computed, not stored.
        self.build()
        conn = __import__("sqlite3").connect(self.db)
        try:
            for table in ("ticket", "finding", "task_plan"):
                bad = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE status='被阻塞'"
                ).fetchone()[0]
                self.assertEqual(bad, 0, f"{table} 存了派生态 被阻塞")
        finally:
            conn.close()

    def test_idempotent_second_save(self):
        model = self.build()
        model.save()
        again = DpDriven.open(self.db)
        self.assertEqual(again.data["tickets"], model.data["tickets"])
        self.assertEqual(again.data["edges"], model.data["edges"])

    def test_validate_after_reload_is_clean(self):
        self.build()
        self.assertEqual(DpDriven.open(self.db).validate(), [])

    def test_claim_round_trip(self):
        """§4.4: claim rows (incl. lease columns, Phase-4a) persist and reload byte-equivalent."""
        model = self.build()
        model.claim(m.CLAIM_PLAN, 0, agent="alice", now="c1", epoch=100)
        model.claim(m.CLAIM_TICKET, 1, agent="bob", now="c2", lease_seconds=None, epoch=200)
        model.save()
        reloaded = DpDriven.open(self.db)
        self.assertEqual(
            sorted(reloaded.data["claims"], key=lambda c: (c["kind"], c["ref_id"])),
            [
                {"kind": m.CLAIM_PLAN, "ref_id": 0, "agent": "alice", "claimed_at": "c1",
                 "last_seen_at": 100, "lease_seconds": m.DEFAULT_CLAIM_LEASE_SECONDS},
                {"kind": m.CLAIM_TICKET, "ref_id": 1, "agent": "bob", "claimed_at": "c2",
                 "last_seen_at": 200, "lease_seconds": None},
            ],
        )
        self.assertEqual(reloaded.claim_owner(m.CLAIM_PLAN, 0), "alice")


if __name__ == "__main__":
    unittest.main(verbosity=2)

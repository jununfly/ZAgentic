#!/usr/bin/env python3
"""Derived-state invariants of zj-dp-driven — the §3 anti-regression locks.

Each test is a *可失败* encoding of a [定稿] rule from
docs/designs/zj-dp-driven-skill-design.md. The whole point of the design's §3.1/§3.2
("状态单一源 / blocked 恒派生") is that no second copy may drift; these tests fail loudly
if an implementation ever starts storing blocked or double-writing task status.

Run: python tests/test_dp_driven_model.py
"""

import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_model as m
from dp_driven_model import DpDriven, DpDrivenError, S_OPEN, S_BLOCKED, S_DONE, S_ABANDONED


class DpTestCase(unittest.TestCase):
    """Base that gives each test a self-cleaning temp carrier directory."""

    def new_model(self) -> DpDriven:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return DpDriven.init(str(Path(tmp.name) / "dp_driven.sqlite"), destination="d", now="t0")

    def setUp(self):
        self.model = self.new_model()


class SingleSource(DpTestCase):
    """§3.1 — task status is a projection of its 1:1 plan, never an independent column."""

    def test_task_starts_open(self):
        model = self.model
        tid = model.add_task("落地登录")
        self.assertEqual(model.task_view(tid)["status"], S_OPEN)
        self.assertEqual(model.task_view(tid)["plan_status"], S_OPEN)

    def test_task_done_mirrors_plan_and_completed_at(self):
        model = self.model
        tid = model.add_task("落地登录")
        model.set_plan_status(tid, S_DONE, summary="完成", now="t1")
        view = model.task_view(tid)
        self.assertEqual(view["status"], S_DONE)
        self.assertEqual(view["completed_at"], "t1")  # derived from plan, not a task column

    def test_storing_blocked_status_is_rejected(self):
        model = self.model
        tid = model.add_task("落地登录")
        with self.assertRaises(DpDrivenError) as cm:
            model.set_plan_status(tid, S_BLOCKED)
        self.assertEqual(cm.exception.code, "E_INVALID_STATUS")

    def test_reopen_clears_terminal_timestamp(self):
        model = self.model
        tid = model.add_task("落地登录")
        model.set_plan_status(tid, S_DONE, now="t1")
        model.set_plan_status(tid, S_OPEN)
        self.assertIsNone(model.task_view(tid)["completed_at"])


class BlockedDerived(DpTestCase):
    """§3.2 — blocked derived on read from blocks edges; absent (not False) when unblocked."""

    def test_blocked_fields_absent_when_unblocked(self):
        model = self.model
        tid = model.add_task("任务")
        t = model.add_ticket(task_id=tid)
        view = model.node_view(m.KIND_TICKET, t)
        self.assertFalse(view["derived_blocked"])
        self.assertNotIn("blocked", view)          # 不写 false，避免可漂移副本
        self.assertNotIn("blocked_reason", view)

    def test_dependent_blocked_until_prereq_done(self):
        model = self.model
        tid = model.add_task("任务")
        a = model.add_ticket(task_id=tid)          # prereq
        b = model.add_ticket(task_id=tid)          # dependent
        model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)
        self.assertEqual(model.node_view(m.KIND_TICKET, b)["blocked_reason"], [0])
        model.set_ticket_status(a, S_DONE)
        self.assertNotIn("blocked", model.node_view(m.KIND_TICKET, b))

    def test_terminal_item_is_never_blocked(self):
        model = self.model
        tid = model.add_task("任务")
        a = model.add_ticket(task_id=tid)          # stays open
        b = model.add_ticket(task_id=tid)
        model.set_ticket_status(b, S_DONE)         # completed despite unfinished prereq
        model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)
        self.assertFalse(model.node_view(m.KIND_TICKET, b)["derived_blocked"])

    def test_parent_child_does_not_block(self):
        model = self.model
        tid = model.add_task("任务")
        parent = model.add_ticket(task_id=tid)
        child = model.add_ticket(task_id=tid, parent_id=parent)   # 父子 only, no blocks edge
        self.assertFalse(model.node_view(m.KIND_TICKET, child)["derived_blocked"])

    def test_blocks_can_span_finding_to_ticket(self):
        model = self.model
        tid = model.add_task("任务")
        f = model.add_finding()
        model.add_finding_membership(f, tid)
        t = model.add_ticket(task_id=tid)
        model.add_blocks(m.KIND_FINDING, f, m.KIND_TICKET, t)     # finding 处置前 ticket 阻塞
        self.assertTrue(model.node_view(m.KIND_TICKET, t)["derived_blocked"])
        model.dispose_finding(f, S_DONE)
        self.assertNotIn("blocked", model.node_view(m.KIND_TICKET, t))


class ExternalHold(DpTestCase):
    """§3.2.1 — external_hold is orthogonal to derived blocked, never folds into status."""

    def test_hold_shown_blocked_but_status_unchanged(self):
        model = self.model
        tid = model.add_task("任务")
        t = model.add_ticket(task_id=tid)
        model.set_external_hold(m.KIND_TICKET, t, "等供应商回复")
        view = model.node_view(m.KIND_TICKET, t)
        self.assertFalse(view["derived_blocked"])     # not a graph fact
        self.assertTrue(view["shown_blocked"])        # but a world fact
        self.assertEqual(view["status"], S_OPEN)      # status NEVER written 被阻塞

    def test_plan_shown_blocked_via_hold_without_deriving_status(self):
        model = self.model
        tid = model.add_task("任务")
        model.add_ticket(task_id=tid, external_hold="等签字")
        self.assertFalse(model.plan_is_blocked(tid))        # 商图无阻塞边
        self.assertTrue(model.plan_shown_blocked(tid))      # external_hold any-path
        self.assertEqual(model.task_view(tid)["status"], S_OPEN)   # §3.3 uses derived, not shown
        self.assertTrue(model.task_view(tid)["shown_blocked"])

    def test_clearing_hold_removes_shown(self):
        model = self.model
        tid = model.add_task("任务")
        t = model.add_ticket(task_id=tid, external_hold="等运维")
        model.set_external_hold(m.KIND_TICKET, t, None)
        self.assertFalse(model.node_view(m.KIND_TICKET, t)["shown_blocked"])


class QuotientGraphBlocking(DpTestCase):
    """§3.6 F2 — outer (task) blocked is the quotient of inner cross-region blocks edges."""

    def test_cross_plan_edge_blocks_dependent_plan_only(self):
        model = self.model
        t1 = model.add_task("上游")
        t2 = model.add_task("下游")
        up = model.add_ticket(task_id=t1)
        down = model.add_ticket(task_id=t2)
        model.add_blocks(m.KIND_TICKET, up, m.KIND_TICKET, down)   # 跨区边
        self.assertTrue(model.plan_is_blocked(t2))
        self.assertEqual(model.task_view(t2)["status"], S_BLOCKED)
        self.assertFalse(model.plan_is_blocked(t1))                # 上游自身不被挡

    def test_upstream_completion_unlocks_downstream_plan(self):
        model = self.model
        t1 = model.add_task("上游")
        t2 = model.add_task("下游")
        up = model.add_ticket(task_id=t1)
        down = model.add_ticket(task_id=t2)
        model.add_blocks(m.KIND_TICKET, up, m.KIND_TICKET, down)
        model.set_ticket_status(up, S_DONE)                        # 回灌：内层完成解锁外层
        self.assertFalse(model.plan_is_blocked(t2))
        self.assertEqual(model.task_view(t2)["status"], S_OPEN)

    def test_intra_plan_edge_does_not_block_plan(self):
        model = self.model
        t1 = model.add_task("同区")
        a = model.add_ticket(task_id=t1)
        b = model.add_ticket(task_id=t1)
        model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)       # 区内边不投影成外层 blocked
        self.assertFalse(model.plan_is_blocked(t1))


class Ownership(DpTestCase):
    """§3.4 — ticket 单归属, finding 多归属."""

    def test_ticket_single_membership_move(self):
        model = self.model
        t1 = model.add_task("甲")
        t2 = model.add_task("乙")
        tk = model.add_ticket(task_id=t1)
        model.assign_ticket(tk, t2)                                # 单归属：移动即换 owner
        self.assertEqual(model.data["tickets"][str(tk)]["task_id"], t2)
        self.assertEqual(model._plan_inner_nodes(t1), set())

    def test_ticket_release_returns_to_pool(self):
        model = self.model
        t1 = model.add_task("甲")
        tk = model.add_ticket(task_id=t1)
        model.assign_ticket(tk, None)
        self.assertIn({"kind": m.KIND_TICKET, "id": tk}, model.pool())

    def test_finding_multi_membership(self):
        model = self.model
        t1 = model.add_task("A")
        t2 = model.add_task("B")
        f = model.add_finding()
        model.add_finding_membership(f, t1)
        model.add_finding_membership(f, t2)                        # overlapping subproblem
        self.assertEqual(sorted(model.find_memberships(f)), sorted([t1, t2]))
        self.assertIn((m.KIND_FINDING, f), model._plan_inner_nodes(t1))
        self.assertIn((m.KIND_FINDING, f), model._plan_inner_nodes(t2))


class FindingMemo(DpTestCase):
    """§3.5 — 处置一次 = 标态 + 从所有归属 plan 摘除，之后只读复用（不再重跑）."""

    def test_dispose_clears_all_memberships_and_marks_done(self):
        model = self.model
        t1 = model.add_task("A")
        t2 = model.add_task("B")
        f = model.add_finding()
        model.add_finding_membership(f, t1)
        model.add_finding_membership(f, t2)
        model.dispose_finding(f, S_DONE, now="t2")
        self.assertEqual(model.find_memberships(f), [])            # 摘除：少这一步会被重复处置
        self.assertEqual(model.data["findings"][str(f)]["status"], S_DONE)
        self.assertEqual(model.data["findings"][str(f)]["completed_at"], "t2")

    def test_dispose_to_abandoned_also_clears(self):
        model = self.model
        t1 = model.add_task("A")
        f = model.add_finding()
        model.add_finding_membership(f, t1)
        model.dispose_finding(f, S_ABANDONED)
        self.assertEqual(model.find_memberships(f), [])
        self.assertEqual(model.data["findings"][str(f)]["status"], S_ABANDONED)

    def test_dispose_rejects_non_terminal_target(self):
        model = self.model
        f = model.add_finding()
        with self.assertRaises(DpDrivenError):
            model.dispose_finding(f, S_OPEN)


class PoolView(DpTestCase):
    """§2 — pool = open ∧ 未被任何 plan 收纳（派生视图，不存储）."""

    def test_pool_membership_and_exclusions(self):
        model = self.model
        t1 = model.add_task("甲")
        open_ticket = model.add_ticket()                 # unassigned open → pool
        model.add_ticket(task_id=t1)                     # assigned → not pool
        done_unassigned = model.add_ticket()
        model.set_ticket_status(done_unassigned, S_DONE) # terminal → not pool
        open_finding = model.add_finding()               # orphan finding → pool
        membered = model.add_finding()
        model.add_finding_membership(membered, t1)       # 收纳 → not pool
        ids = {(x["kind"], x["id"]) for x in model.pool()}
        self.assertIn((m.KIND_TICKET, open_ticket), ids)
        self.assertIn((m.KIND_FINDING, open_finding), ids)
        self.assertNotIn((m.KIND_TICKET, done_unassigned), ids)
        self.assertNotIn((m.KIND_FINDING, membered), ids)

    def test_blocked_unassigned_still_in_pool(self):
        # design pool def: status==未完成 ∧ 未收纳. blocked is a separate derived fact,
        # so a blocked-but-unassigned ticket is still pool input (§2 literal).
        model = self.model
        t1 = model.add_task("甲")
        prereq = model.add_ticket(task_id=t1)
        blocked_orphan = model.add_ticket()
        model.add_blocks(m.KIND_TICKET, prereq, m.KIND_TICKET, blocked_orphan)
        self.assertTrue(model.node_view(m.KIND_TICKET, blocked_orphan)["derived_blocked"])
        self.assertIn({"kind": m.KIND_TICKET, "id": blocked_orphan}, model.pool())


class Completion(DpTestCase):
    """§5.1 — 完成判据：所有 task 到终态."""

    def test_incomplete_while_any_plan_open(self):
        model = self.model
        a = model.add_task("甲")
        b = model.add_task("乙")
        model.set_plan_status(a, S_DONE)
        self.assertFalse(model.is_complete())
        model.set_plan_status(b, S_ABANDONED)
        self.assertTrue(model.is_complete())

    def test_no_plans_is_not_complete(self):
        self.assertFalse(self.model.is_complete())


class Validation(DpTestCase):
    def test_clean_graph_validates_empty(self):
        model = self.model
        tid = model.add_task("任务")
        a = model.add_ticket(task_id=tid)
        b = model.add_ticket(task_id=tid, derived_from_finding=None, parent_id=a)
        f = model.add_finding()
        model.add_finding_membership(f, tid)
        model.add_blocks(m.KIND_TICKET, a, m.KIND_TICKET, b)
        self.assertEqual(model.validate(), [])

    def test_detects_dangling_ref_and_illegal_status(self):
        model = self.model
        tid = model.add_task("任务")
        tk = model.add_ticket(task_id=tid)
        model.data["tickets"][str(tk)]["task_id"] = 999          # 悬空归属
        model.data["plans"][str(tid)]["status"] = "被阻塞"        # 非法存储态
        errs = model.validate()
        self.assertTrue(any("E_REF_MISSING" in e for e in errs))
        self.assertTrue(any("E_INVALID_STATUS" in e for e in errs))

    def test_edge_endpoint_missing_is_validation_error(self):
        model = self.model
        model.data["edges"].append(
            {"id": 0, "type": m.EDGE_BLOCKS, "from_kind": m.KIND_TICKET,
             "from_id": 999, "to_kind": m.KIND_TICKET, "to_id": 1})
        self.assertTrue(any("E_EDGE_ENDPOINT_MISSING" in e for e in model.validate()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

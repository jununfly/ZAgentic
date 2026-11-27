#!/usr/bin/env python3
"""§6 visualization renderer — invariant locks (Phase-3c).

Mermaid backend R1–R6 (§6) + the two hard guarantees the design turns on: render is a
pure read (§3.1 suggestion/视图 ≠ 状态) and byte-deterministic. Run: python tests/test_dp_driven_viz.py
"""

import copy
import os
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

from dp_driven_model import (
    DpDriven, KIND_FINDING, KIND_TICKET, SETTLEMENT_AGENT, S_DONE, S_ABANDONED,
)
import dp_driven_viz as viz


def fresh():
    d = tempfile.TemporaryDirectory()
    m = DpDriven.init(os.path.join(d.name, "x.sqlite"), destination="上线登录")
    m._tmp = d
    return m


class Guarantees(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_render_deterministic(self):
        t = self.m.add_task("x")
        a = self.m.add_ticket(task_id=t, now="t0")
        b = self.m.add_ticket(task_id=t, now="t1")
        self.m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        self.assertEqual(viz.render(self.m), viz.render(self.m))

    def test_render_is_pure_readonly(self):
        t = self.m.add_task("x")
        f = self.m.add_finding()
        self.m.add_finding_membership(f, t)
        before = copy.deepcopy(self.m.data)
        viz.render(self.m)
        self.assertEqual(before, self.m.data)   # §3.1 view ≠ state; render must not mutate

    def test_empty_carrier_renders_valid_header(self):
        txt = viz.render(self.m)
        self.assertTrue(txt.startswith("flowchart TD"))
        self.assertIn("destination", txt)

    def test_clean_label_sanitization(self):
        self.m.add_task('weird "name" [with] {braces}')
        txt = viz.render(self.m)
        label_line = next(ln for ln in txt.splitlines() if "task0" in ln)
        # original name had quotes/brackets/braces; cleaned form must appear verbatim,
        # and only the two Mermaid delimiter quotes remain (name contributed none).
        self.assertIn("weird name with braces", label_line)
        self.assertEqual(label_line.count('"'), 2)
        self.assertNotIn('"name"', label_line)
        self.assertNotIn("{braces}", label_line)


class Layer1Layer2(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_R2_plan_subgraph_present(self):
        t = self.m.add_task("后端")
        self.m.add_ticket(task_id=t)
        txt = viz.render(self.m)
        self.assertIn('subgraph T0["', txt)
        self.assertIn("tk0_T0", txt)

    def test_R1_task_derived_status_in_label(self):
        t = self.m.add_task("甲")
        self.m.set_plan_status(t, S_DONE)
        txt = viz.render(self.m)
        self.assertIn("task0 甲 (已完成)", txt)   # derived status shown, not stored (task has none)

    def test_R1_cross_plan_quotient_edge(self):
        # a in plan0, b in plan1, blocks a→b → layer-1 plan-dep edge T0→T1 (§3.6 F2)
        t0 = self.m.add_task("上游")
        t1 = self.m.add_task("下游")
        a = self.m.add_ticket(task_id=t0, now="t0")
        b = self.m.add_ticket(task_id=t1, now="t1")
        self.m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        txt = viz.render(self.m)
        self.assertIn("tk0_T0 -->|blocks| tk1_T1", txt)
        self.assertIn("T0 -->|plan-dep| T1", txt)

    def test_R2_intra_blocks_edge(self):
        t = self.m.add_task("x")
        a = self.m.add_ticket(task_id=t, now="t0")
        b = self.m.add_ticket(task_id=t, now="t1")
        self.m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        txt = viz.render(self.m)
        self.assertIn("tk0_T0 -->|blocks| tk1_T0", txt)

    def test_parent_edge_rendered(self):
        t = self.m.add_task("x")
        p = self.m.add_ticket(task_id=t, now="t0")
        c = self.m.add_ticket(task_id=t, parent_id=p, now="t1")
        txt = viz.render(self.m)
        self.assertIn("tk0_T0 -->|parent| tk1_T0", txt)
        # parent does NOT block: child label shows 未完成, not 被阻塞
        self.assertIn("tk1_T0", txt)
        self.assertNotIn("tk1_T0[\"tk1 被阻塞", txt)

    def test_materialization_edges(self):
        t = self.m.add_task("x")
        f = self.m.add_finding(now="t0")
        self.m.add_finding_membership(f, t)
        k = self.m.add_ticket(task_id=t, derived_from_finding=f, now="t1")   # form①
        txt = viz.render(self.m)
        self.assertIn("f0_T0 -.->|derived_from| tk0_T0", txt)


class OrphansAndOverlap(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_R4_orphan_finding_separate_subgraph(self):
        f = self.m.add_finding(now="t0")   # no membership → id 0, orphan
        txt = viz.render(self.m)
        self.assertIn("ORPHANS", txt)
        self.assertIn("f0_ORPHAN", txt)
        # orphan finding must NOT also appear inside a plan subgraph
        self.assertNotIn("f0_T0", txt)

    def test_R4_orphan_unclaimed_ticket(self):
        k = self.m.add_ticket(now="t0")    # task_id None
        txt = viz.render(self.m)
        self.assertIn("tk0_ORPHAN", txt)

    def test_R6_shared_finding_drawn_per_plan_with_marker(self):
        t0 = self.m.add_task("A")
        t1 = self.m.add_task("B")
        f = self.m.add_finding(now="t0")
        self.m.add_finding_membership(f, t0)
        self.m.add_finding_membership(f, t1)
        txt = viz.render(self.m)
        self.assertIn("f0_T0[", txt)
        self.assertIn("f0_T1[", txt)
        # each carries the overlap marker ⟲ and :::overlap class
        self.assertIn("⟲", txt)
        self.assertEqual(sum(1 for ln in txt.splitlines() if ":::overlap" in ln), 2)

    def test_R6_no_global_overlap_edges(self):
        """§6 R6 [定稿]: 不画 f0_T0 <-> f0_T1 之类跨区重叠连线."""
        t0 = self.m.add_task("A")
        t1 = self.m.add_task("B")
        f = self.m.add_finding(now="t0")
        self.m.add_finding_membership(f, t0)
        self.m.add_finding_membership(f, t1)
        txt = viz.render(self.m)
        self.assertNotIn("f0_T0 -->|", txt)
        self.assertNotIn("f0_T0 -.->", txt)
        self.assertNotIn("f0_T1 -->|", txt)
        self.assertNotIn("f0_T1 -.->", txt)


class ClaimAndBlocked(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_R5_inflight_vs_paused(self):
        t0 = self.m.add_task("甲")
        self.m.add_ticket(task_id=t0)
        t1 = self.m.add_task("乙")
        self.m.add_ticket(task_id=t1)
        self.m.claim("plan", t0, "alice")   # t0 in-flight; t1 open no claim → paused
        txt = viz.render(self.m)
        self.assertIn("class T0 plan_inflight", txt)
        self.assertIn("class T1 plan_paused", txt)

    def test_R5_settlement_plan_class(self):
        self.m.add_ticket(now="t0")         # pool item
        tid, _ = self.m.settlement_run()
        txt = viz.render(self.m)
        self.assertIn(f"class T{tid} plan_settlement", txt)

    def test_terminal_plan_no_claim_class(self):
        t = self.m.add_task("甲")
        self.m.add_ticket(task_id=t)
        self.m.claim("plan", t, "alice")
        self.m.set_plan_status(t, S_DONE, agent="alice")
        txt = viz.render(self.m)
        self.assertNotIn("class T0 plan_inflight", txt)   # terminal → no emphasis

    def test_blocked_shown_via_class_stored_never_blocked(self):
        """§3.2 hard: node marked :::blocked from the DERIVED view, but the stored carrier
        status stays 未完成 (blocked is never a stored field)."""
        t = self.m.add_task("x")
        a = self.m.add_ticket(task_id=t, now="t0")
        b = self.m.add_ticket(task_id=t, now="t1")
        self.m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        txt = viz.render(self.m)
        self.assertTrue(any(ln.strip().startswith(f"tk{b}_T0") and ":::blocked" in ln for ln in txt.splitlines()))
        self.assertEqual(self.m.data["tickets"][str(b)]["status"], "未完成")   # never stored 被阻塞


class WriteTarget(unittest.TestCase):
    def setUp(self):
        self.m = fresh()
        self.addCleanup(self.m._tmp.cleanup)

    def test_R8_only_writes_target_path(self):
        out = os.path.join(tempfile.mkdtemp(), "view.mmd")
        viz.render_to_file(self.m, out)
        self.assertTrue(os.path.exists(out))
        # no stray files created next to the carrier
        d = os.path.dirname(self.m.db_path)
        self.assertEqual([f for f in os.listdir(d) if f.endswith(".mmd")], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

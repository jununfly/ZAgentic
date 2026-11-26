#!/usr/bin/env python3
"""§3.6 F3 / §4.2 optimizer — cohesion scorer + suggest invariant locks.

These are the F3 core gates: cohesion = connectivity, one action per trigger, and
the read-only/determinism guarantees that keep the *suggestion* from becoming a
second source of truth (§3.1). Run: python tests/test_dp_driven_optimize.py
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

from dp_driven_model import DpDriven, DpDrivenError, KIND_FINDING, KIND_TICKET, S_DONE
import dp_driven_optimize as opt


def fresh() -> DpDriven:
    d = tempfile.TemporaryDirectory()
    m = DpDriven.init(os.path.join(d.name, "x.sqlite"), destination="d")
    m._tmp = d
    return m


class Scorer(unittest.TestCase):
    def test_density_and_cut(self):
        """S with an internal relation beats two disconnected singletons."""
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        a = m.add_ticket(now="t0"); b = m.add_ticket(now="t1"); c = m.add_ticket(now="t2")
        m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)   # a~b ; c isolated
        rels = opt._relations(m); pool = {(KIND_TICKET, a), (KIND_TICKET, b), (KIND_TICKET, c)}
        blocked = opt._blocked_nodes(m)
        pair = opt.score_subset(m, frozenset({(KIND_TICKET, a), (KIND_TICKET, b)}), rels, pool, blocked)
        lone = opt.score_subset(m, frozenset({(KIND_TICKET, c)}), rels, pool, blocked)
        self.assertGreater(pair.factors["density"], lone.factors["density"])
        self.assertEqual(lone.factors["density"], 0.0)
        self.assertGreater(pair.total, lone.total)

    def test_unlock_bonus(self):
        """Including a prerequisite that unblocks an out-of-set pool item scores unlock>0."""
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        pre = m.add_ticket(now="t0")
        dep = m.add_ticket(now="t1")          # dep blocked by pre
        m.add_blocks(KIND_TICKET, pre, KIND_TICKET, dep)
        rels = opt._relations(m); pool = {(KIND_TICKET, pre), (KIND_TICKET, dep)}
        blocked = opt._blocked_nodes(m)
        self.assertIn((KIND_TICKET, dep), blocked)
        # S={pre} unlocks dep (which is in pool, blocked, prereq pre in S)
        s = opt.score_subset(m, frozenset({(KIND_TICKET, pre)}), rels, pool, blocked)
        self.assertGreater(s.factors["unlock"], 0.0)

    def test_staleness_prefers_older(self):
        """An item created earlier (lexicographically smaller created_at) ranks staler."""
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        old = m.add_ticket(now="t0"); new = m.add_ticket(now="t9")
        rels = opt._relations(m)  # no edges
        pool = {(KIND_TICKET, old), (KIND_TICKET, new)}
        blocked = set()
        s_old = opt.score_subset(m, frozenset({(KIND_TICKET, old)}), rels, pool, blocked)
        s_new = opt.score_subset(m, frozenset({(KIND_TICKET, new)}), rels, pool, blocked)
        # oldest-in-set rank: old has higher reverse rank => higher staleness
        self.assertGreater(s_old.factors["staleness"], s_new.factors["staleness"])


class SuggestRouting(unittest.TestCase):
    def test_seed_and_grow_connected_pair(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        a = m.add_ticket(now="t0"); b = m.add_ticket(now="t1"); c = m.add_ticket(now="t2")
        m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)   # a-b connected, c isolated
        steps = opt.suggest(m)
        self.assertEqual([s.action for s in steps], [opt.ACT_NEW_PLAN])
        self.assertEqual(set(map(tuple, steps[0].items)),
                         {(KIND_TICKET, a), (KIND_TICKET, b)})   # c NOT pulled in (no adjacency)

    def test_grow_requires_adjacency_not_staleness(self):
        """A chain grows; an unconnected stale item is never merged by staleness alone."""
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        a = m.add_ticket(now="t0"); b = m.add_ticket(now="t1")
        c = m.add_ticket(now="t5")                 # stalest, but isolated
        m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        steps = opt.suggest(m)
        self.assertEqual([s.action for s in steps], [opt.ACT_NEW_PLAN])
        self.assertNotIn((KIND_TICKET, c), [tuple(i) for i in steps[0].items])

    def test_settle_when_no_feasible(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        for i in range(4):
            m.add_ticket(now=f"t{i}")              # fully isolated
        steps = opt.suggest(m)
        self.assertEqual([s.action for s in steps], [opt.ACT_SETTLE])
        self.assertEqual(len(steps[0].items), 4)

    def test_hotplug_route(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        tid = m.add_task("P")
        x = m.add_ticket(task_id=tid, now="t0")     # in-flight plan member
        m.claim("plan", tid, "alice")
        y = m.add_ticket(now="t1")
        m.data["tickets"][str(y)]["parent_id"] = x  # non-blocking link x~y
        steps = opt.suggest(m)
        self.assertEqual([(s.action, s.task_id, tuple(s.items[0])) for s in steps],
                         [(opt.ACT_HOTPLUG, tid, (KIND_TICKET, y))])

    def test_blocked_item_not_hotplugged(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        tid = m.add_task("P")
        x = m.add_ticket(task_id=tid, now="t0")     # stays open
        m.claim("plan", tid, "alice")
        y = m.add_ticket(now="t1")
        m.add_blocks(KIND_TICKET, x, KIND_TICKET, y)  # y blocked by x → not hotpluggable
        steps = opt.suggest(m)
        self.assertTrue(all(s.action != opt.ACT_HOTPLUG for s in steps))


class Guarantees(unittest.TestCase):
    def test_suggest_is_pure_readonly(self):
        """§3.1: the suggestion must never mutate state or become a second source of truth."""
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        a = m.add_ticket(now="t0"); b = m.add_ticket(now="t1")
        m.add_blocks(KIND_TICKET, a, KIND_TICKET, b); m.save()
        before = copy.deepcopy(m.data)
        opt.suggest(m)
        self.assertEqual(before, m.data)

    def test_suggest_deterministic(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        for i in range(3):
            m.add_ticket(now=f"t{i}")
        m.add_blocks(KIND_TICKET, 0, KIND_TICKET, 1); m.save()
        s1 = [(x.action, x.task_id, list(map(tuple, x.items))) for x in opt.suggest(m)]
        s2 = [(x.action, x.task_id, list(map(tuple, x.items))) for x in opt.suggest(m)]
        self.assertEqual(s1, s2)

    def test_empty_pool_raises(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        with self.assertRaises(DpDrivenError) as cm:
            opt.suggest(m)
        self.assertEqual(cm.exception.code, "E_POOL_EMPTY")

    def test_execute_new_plan_applies_and_claims(self):
        m = fresh(); self.addCleanup(m._tmp.cleanup)
        a = m.add_ticket(now="t0"); b = m.add_ticket(now="t1")
        m.add_blocks(KIND_TICKET, a, KIND_TICKET, b)
        steps = opt.suggest(m)
        applied = opt.execute(m, steps, agent="alice")
        tid = applied[0]["task_id"]
        self.assertEqual(m.claim_owner("plan", tid), "alice")
        self.assertEqual(m.data["tickets"][str(a)]["task_id"], tid)
        self.assertEqual(m.data["tickets"][str(b)]["task_id"], tid)
        self.assertEqual(m.pool(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

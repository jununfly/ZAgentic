#!/usr/bin/env python3
"""§4.4 claim lease/TTL — invariant locks (Phase-4a).

Design §4.4 [定稿]: a release condition is 超时释放; §8 asked "heartbeat? 固定 TTL?".
Phase-4a landed heartbeat/lease. The load-bearing invariants:

  1. `expired` is DERIVED at read time from (last_seen_at + lease_seconds) vs a
     caller-supplied epoch — never a stored column (§3.1/§3.2 anti-drift).
  2. The MODEL never reads the wall clock — `epoch` is injected; `epoch=None` ⇒ expiry is
     not evaluated (preserves explicit-release-only for clockless callers). CLI supplies time.
  3. An expired claim is inert: another agent may take it over; the gate treats it as free.
"""

import os
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_model as m
from dp_driven_model import (
    DpDriven, DpDrivenError, CLAIM_PLAN, CLAIM_TICKET, DEFAULT_CLAIM_LEASE_SECONDS,
    NO_LEASE, S_DONE,
)

T0 = 1_000_000  # fixed base epoch, deterministic


def fresh():
    d = tempfile.TemporaryDirectory()
    mm = DpDriven.init(os.path.join(d.name, "x.sqlite"), destination="d")
    mm._tmp = d
    return mm


class LeaseBasics(unittest.TestCase):
    def setUp(self):
        self.mm = fresh()
        self.addCleanup(self.mm._tmp.cleanup)
        self.t = self.mm.add_task("甲")

    def test_claim_sets_lease_defaults(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", epoch=T0)
        row = self.mm._find_claim(CLAIM_PLAN, self.t)
        self.assertEqual(row["last_seen_at"], T0)
        self.assertEqual(row["lease_seconds"], DEFAULT_CLAIM_LEASE_SECONDS)

    def test_owner_within_lease(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 99), "alice")

    def test_owner_after_expiry(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        self.assertIsNone(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 101))

    def test_expired_still_derived_not_stored(self):
        """§3.1: there is no stored `expired` field; the row keys are the lease facts only."""
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        row = self.mm._find_claim(CLAIM_PLAN, self.t)
        self.assertNotIn("expired", row)
        self.assertTrue(self.mm._is_expired(row, T0 + 500))   # derived at read
        self.assertFalse(self.mm._is_expired(row, T0 + 10))

    def test_epoch_none_never_evaluates_expiry(self):
        """model must not invent a clock: with epoch=None, lease is ignored (backward compat)."""
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t), "alice")        # no epoch → held
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=None), "alice")


class TakeoverAndGate(unittest.TestCase):
    def setUp(self):
        self.mm = fresh()
        self.addCleanup(self.mm._tmp.cleanup)
        self.t = self.mm.add_task("甲")

    def test_expired_treated_as_free_for_claim(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        # alice expired; bob takes over (no E_CLAIM_HELD_BY_OTHER)
        self.assertTrue(self.mm.claim(CLAIM_PLAN, self.t, "bob", lease_seconds=100, epoch=T0 + 500))
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 500), "bob")

    def test_unexpired_other_still_conflicts(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        with self.assertRaises(DpDrivenError) as cm:
            self.mm.claim(CLAIM_PLAN, self.t, "bob", lease_seconds=100, epoch=T0 + 10)
        self.assertEqual(cm.exception.code, "E_CLAIM_HELD_BY_OTHER")

    def test_claim_gate_ignores_expired(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        # bob writes plan status after alice's lease lapsed, with the same clock
        self.mm.set_plan_status(self.t, S_DONE, agent="bob", epoch=T0 + 500)
        self.assertEqual(self.mm.task_view(self.t)["status"], S_DONE)

    def test_gate_blocks_unexpired_other(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        with self.assertRaises(DpDrivenError) as cm:
            self.mm.set_plan_status(self.t, S_DONE, agent="bob", epoch=T0 + 10)
        self.assertEqual(cm.exception.code, "E_CLAIM_HELD_BY_OTHER")


class Heartbeat(unittest.TestCase):
    def setUp(self):
        self.mm = fresh()
        self.addCleanup(self.mm._tmp.cleanup)
        self.t = self.mm.add_task("甲")
        self.tk = self.mm.add_ticket(task_id=self.t)

    def test_renew_extends_lease(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        self.assertTrue(self.mm.renew(CLAIM_PLAN, self.t, "alice", epoch=T0 + 80))
        # original expiry T0+100 would have lapsed at T0+150; renewed at T0+80 → good until T0+180
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 150), "alice")
        self.assertIsNone(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 200))

    def test_renew_by_non_owner_rejected(self):
        self.mm.claim(CLAIM_TICKET, self.tk, "alice", lease_seconds=100, epoch=T0)
        with self.assertRaises(DpDrivenError) as cm:
            self.mm.renew(CLAIM_TICKET, self.tk, "bob", epoch=T0 + 10)
        self.assertEqual(cm.exception.code, "E_CLAIM_NOT_OWNER")

    def test_renew_expired_is_noop(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=100, epoch=T0)
        self.assertFalse(self.mm.renew(CLAIM_PLAN, self.t, "alice", epoch=T0 + 500))


class NoLease(unittest.TestCase):
    def setUp(self):
        self.mm = fresh()
        self.addCleanup(self.mm._tmp.cleanup)
        self.t = self.mm.add_task("甲")

    def test_no_lease_never_expires(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=NO_LEASE, epoch=T0)
        self.assertEqual(self.mm.claim_owner(CLAIM_PLAN, self.t, epoch=T0 + 10**9), "alice")

    def test_bad_lease_rejected(self):
        with self.assertRaises(DpDrivenError) as cm:
            self.mm.claim(CLAIM_PLAN, self.t, "alice", lease_seconds=0, epoch=T0)
        self.assertEqual(cm.exception.code, "E_CLAIM_LEASE_INVALID")

    def test_validate_rejects_bad_lease(self):
        self.mm.claim(CLAIM_PLAN, self.t, "alice", epoch=T0)
        self.mm._find_claim(CLAIM_PLAN, self.t)["lease_seconds"] = -5
        self.assertTrue(any("E_CLAIM_LEASE_INVALID" in e for e in self.mm.validate()))


class ListClaimsDerived(unittest.TestCase):
    def setUp(self):
        self.mm = fresh()
        self.addCleanup(self.mm._tmp.cleanup)

    def test_list_claims_expired_is_computed_not_stored(self):
        t = self.mm.add_task("甲")
        tk = self.mm.add_ticket(task_id=t)
        self.mm.claim(CLAIM_PLAN, t, "alice", lease_seconds=100, epoch=T0)
        self.mm.claim(CLAIM_TICKET, tk, "bob", lease_seconds=None, epoch=T0)
        import copy
        before = copy.deepcopy(self.mm.data["claims"])
        rows = {r["kind"]: r for r in self.mm.list_claims(epoch=T0 + 500)}
        self.assertTrue(rows[CLAIM_PLAN]["expired"])     # alice expired
        self.assertFalse(rows[CLAIM_TICKET]["expired"])  # bob no-lease
        self.assertEqual(self.mm.data["claims"], before) # `expired` NOT written back

    def test_no_wall_clock_determinism(self):
        t = self.mm.add_task("甲")
        self.mm.claim(CLAIM_PLAN, t, "alice", lease_seconds=100, epoch=T0)
        a = self.mm.claim_owner(CLAIM_PLAN, t, epoch=T0 + 150)
        b = self.mm.claim_owner(CLAIM_PLAN, t, epoch=T0 + 150)
        self.assertEqual(a, b)
        self.assertIsNone(a)


if __name__ == "__main__":
    unittest.main(verbosity=2)

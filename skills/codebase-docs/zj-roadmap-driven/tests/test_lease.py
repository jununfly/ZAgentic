#!/usr/bin/env python3
"""Contract tests for the P2 node-lease core (issue #111).

Scope (reconstructed from docs/plans/zj-roadmap-dag-concurrency.md §4 + Story 25-31,
"01 P2 租约核心"): claim / heartbeat / steal / release (+ --force) + fencing token
+ `--if-rev` optimistic concurrency. Two carriers (single-file + bundle) must agree
on what a lease means — the policy lives in `lease.py` and is the one source of
truth; storage differs only in *where the bytes go*.

Why this file exists
--------------------
Problem #1's attribution was corrected (PR #28): the real failure was a crashed
writer, not a lost update, so the lease is *not* a fix for lost update. Its job is
to lower the exclusive unit from "whole graph" to "node" and to let a crashed agent
be fenced out instead of wedging a node forever. The acceptance criteria below are
the spec's Testing Decisions §并发/租约参数, expressed as red→green slices.

Seams under test
----------------
  1. Carrier API (deterministic `now` injection) — claim/heartbeat/steal/release
     semantics, fencing increment, idempotent heartbeat, expiry gate.
  2. CLI contract (subprocess: exit code + stderr `E_*` code) — the documented
     main seam: `lease` lifecycle exit codes, stale-token write rejection
     (E_LEASE_HELD), and `--if-rev` conflict (E_CONFLICT).

Both carriers run every test.

Run: python tests/test_lease.py        (also works under pytest)
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

import roadmap
from roadmap import Roadmap, LeaseHeld, ConflictError
import roadmap_bundle
from roadmap_bundle import RoadmapBundle

LEASE_TTL = 300


def build_data() -> dict:
    """Two-node legacy-shaped roadmap (root + one child) for carrier tests."""
    return {
        "title": "lease-test",
        "version": 1,
        "nodes": {
            "1": {"id": "1", "label": "root", "status": "in_progress", "mode": "explore",
                  "parent": None, "children": ["1-1"], "decisions": [], "notes": "", "rounds": 1},
            "1-1": {"id": "1-1", "label": "child", "status": "pending", "mode": "explore",
                    "parent": "1", "children": [], "decisions": [], "notes": "", "rounds": 0},
        },
        "metadata": {"created": "2026-01-01 00:00:00", "updated": "2026-01-01 00:00:00", "md_file": ""},
    }


# ── Carrier-level: claim/heartbeat/steal/release/fencing semantics ──

class LeaseContract:
    """Subclassed by SingleFileLease and BundleLease; supplies the storage."""

    def build(self) -> str:
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.build()
        self.now = 1_700_000_000.0  # fixed clock → deterministic expiry math

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        r = RoadmapBundle(self.path) if Path(self.path).is_dir() else Roadmap(self.path)
        r.load()
        return r

    def _lease_events(self, r) -> list[dict]:
        if getattr(r, "is_bundle", False):
            lines = (r.path / "history/events.jsonl").read_text(encoding="utf-8").splitlines()
            return [json.loads(line) for line in lines if line.strip()]
        store = json.loads(Path(r.json_path + ".leases.json").read_text(encoding="utf-8"))
        return store.get("events", [])

    # slice 1: claim
    def test_claim_sets_ttl_and_fencing(self):
        r = self.load()
        lease = r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, device_id="win", now=self.now)
        self.assertEqual(lease["agent_id"], "agent-7")
        self.assertEqual(lease["fencing_token"], 1)
        self.assertAlmostEqual(lease["expires_at"] - lease["claimed_at"], LEASE_TTL, delta=0.001)
        self.assertTrue(lease["expires_at"] > self.now)
        # persisted and re-readable from storage
        self.assertEqual(r.get_lease("1-1")["fencing_token"], 1)

    def test_claim_on_active_lease_rejected(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        with self.assertRaises(LeaseHeld):
            r.claim_lease("1-1", "agent-8", ttl=LEASE_TTL, now=self.now + 1)

    # slice 2: heartbeat (idempotent)
    def test_heartbeat_anchors_to_now_not_accumulates(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        r.heartbeat_lease("1-1", "agent-7", now=self.now + 10)
        hb2 = r.heartbeat_lease("1-1", "agent-7", now=self.now + 20)
        # expires_at = now_of_heartbeat + ttl, never now_initial + 2*ttl
        self.assertAlmostEqual(hb2["expires_at"], self.now + 20 + LEASE_TTL, delta=0.001)

    def test_heartbeat_by_wrong_agent_rejected(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        with self.assertRaises(LeaseHeld):
            r.heartbeat_lease("1-1", "agent-9", now=self.now + 1)

    def test_heartbeat_on_expired_lease_rejected(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        with self.assertRaises(LeaseHeld):
            r.heartbeat_lease("1-1", "agent-7", now=self.now + LEASE_TTL + 1)

    # slice 3: steal (only after expiry, increments fencing)
    def test_steal_only_after_expiry_and_increments_fencing(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        with self.assertRaises(LeaseHeld):
            r.steal_lease("1-1", "agent-8", now=self.now + 1)  # not expired
        stolen = r.steal_lease("1-1", "agent-8", now=self.now + LEASE_TTL + 1)
        self.assertEqual(stolen["agent_id"], "agent-8")
        self.assertEqual(stolen["fencing_token"], 2)  # old holder fenced out

    def test_zombie_holder_write_rejected_after_steal(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        r.steal_lease("1-1", "agent-8", now=self.now + LEASE_TTL + 1)
        # original holder's later heartbeat fails: its fencing token (1) is stale
        with self.assertRaises(LeaseHeld):
            r.heartbeat_lease("1-1", "agent-7", now=self.now + LEASE_TTL + 2)

    # slice 4: release / release --force
    def test_release_by_holder_clears_lease(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        with self.assertRaises(LeaseHeld):
            r.release_lease("1-1", "agent-9", now=self.now + 1)  # not holder
        r.release_lease("1-1", "agent-7", now=self.now + 1)
        self.assertIsNone(r.get_lease("1-1"))

    def test_release_force_succeeds_and_is_audited(self):
        r = self.load()
        r.claim_lease("1-1", "agent-7", ttl=LEASE_TTL, now=self.now)
        r.release_lease("1-1", "agent-x", force=True, now=self.now + 1)
        self.assertIsNone(r.get_lease("1-1"))
        events = [e for e in self._lease_events(r) if e.get("operation") == "lease-released"]
        forced = [e for e in events
                  if e.get("force") or (e.get("payload") or {}).get("force")]
        self.assertTrue(forced, "release --force must be in the event log")

    # slice 5/6 helpers: rev stable semantics
    def test_current_revision_changes_with_semantic_edit(self):
        r = self.load()
        rev1 = r.current_revision()
        r.update_node("1-1", label="changed")
        r.save()
        self.assertNotEqual(rev1, r.current_revision())


class SingleFileLease(LeaseContract, unittest.TestCase):
    def build(self) -> str:
        path = os.path.join(self.tmp.name, "roadmap.json")
        r = Roadmap(path)
        r.data = build_data()
        r.save()
        return path


class BundleLease(LeaseContract, unittest.TestCase):
    def build(self) -> str:
        path = Path(self.tmp.name) / "roadmap.bundle"
        RoadmapBundle.create_from_data(path, build_data())
        return str(path)


# ── CLI-level: exit codes are the Agent-facing contract ──

def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                          capture_output=True, text=True)


def rev_of(path: str) -> str:
    r = RoadmapBundle(path) if Path(path).is_dir() else Roadmap(path)
    r.load()
    return r.current_revision()


class LeaseCliContract:
    storage = "single"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / ("roadmap.json" if self.storage == "single" else "roadmap.bundle")
        init = run_cli("init", str(path), "--title", "lease-cli", "--storage", self.storage)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.path = str(path)
        self.assertEqual(run_cli("add", self.path, "1", "child").returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    # lifecycle exit codes
    def test_claim_exit_zero_and_lease_visible(self):
        self.assertEqual(run_cli("lease", "claim", self.path, "1-1", "--agent", "a7").returncode, 0)
        # 未过期 claim 同一节点 → E_LEASE_HELD (exit 1)
        bad = run_cli("lease", "claim", self.path, "1-1", "--agent", "a8")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)

    def test_steal_before_expiry_rejected_after_claim(self):
        self.assertEqual(run_cli("lease", "claim", self.path, "1-1", "--agent", "a7", "--ttl", "1").returncode, 0)
        early = run_cli("lease", "steal", self.path, "1-1", "--agent", "a8")
        self.assertEqual(early.returncode, 1)
        self.assertIn("E_LEASE_HELD", early.stderr)

    # slice 5: fencing guard on writes (E_LEASE_HELD)
    def test_write_without_credentials_blocked_while_leased(self):
        self.assertEqual(run_cli("lease", "claim", self.path, "1-1", "--agent", "a7").returncode, 0)
        blocked = run_cli("update", self.path, "1-1", "--status", "completed")
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("E_LEASE_HELD", blocked.stderr)
        # holder with matching token writes fine
        ok = run_cli("update", self.path, "1-1", "--status", "completed", "--as-agent", "a7", "--token", "1")
        self.assertEqual(ok.returncode, 0)

    def test_stale_token_write_blocked_after_steal(self):
        self.assertEqual(run_cli("lease", "claim", self.path, "1-1", "--agent", "a7", "--ttl", "1").returncode, 0)
        time.sleep(1.2)  # let the 1s TTL lapse
        stolen = run_cli("lease", "steal", self.path, "1-1", "--agent", "a8")
        self.assertEqual(stolen.returncode, 0)
        self.assertIn('"fencing_token": 2', stolen.stdout)
        stale = run_cli("update", self.path, "1-1", "--label", "z", "--as-agent", "a7", "--token", "1")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("E_LEASE_HELD", stale.stderr)
        fresh = run_cli("update", self.path, "1-1", "--label", "z", "--as-agent", "a8", "--token", "2")
        self.assertEqual(fresh.returncode, 0)

    # slice 6: --if-rev optimistic concurrency (E_CONFLICT)
    def test_if_rev_conflict_rejects_stale_writer(self):
        rev0 = rev_of(self.path)
        first = run_cli("update", self.path, "1-1", "--label", "A", "--if-rev", rev0)
        self.assertEqual(first.returncode, 0, first.stderr)
        # a concurrent writer still holding rev0 must be rejected
        conflict = run_cli("update", self.path, "1-1", "--label", "B", "--if-rev", rev0)
        self.assertEqual(conflict.returncode, 1)
        self.assertIn("E_CONFLICT", conflict.stderr)


class SingleFileLeaseCli(LeaseCliContract, unittest.TestCase):
    storage = "single"


class BundleLeaseCli(LeaseCliContract, unittest.TestCase):
    storage = "bundle"


if __name__ == "__main__":
    unittest.main(verbosity=2)

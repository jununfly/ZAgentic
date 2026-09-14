#!/usr/bin/env python3
"""Contract tests for P2 failure semantics and escalation (issue #114).

Spec (docs/plans/zj-roadmap-dag-concurrency.md §4 + Story 33/34):

  * Story 33: a failed node records `attempts` / `last_error` / `retry_backoff`,
    so retries are bounded and inspectable.
  * Story 34: a node that fails N times raises an **open question** so a stuck
    loop escalates to a Human instead of spinning.

Decisions taken with zj before the loop (ambiguities in the plan itself):

  1. **Escalation does NOT write `status`.** The plan is self-contradictory:
     §4 line 232 says "超过阈值转 `blocked`", but §3 (2026-09-09 decision)
     says `blocked` is purely *derived* from `blocks` edges and `--status
     blocked` returns `E_INVALID_STATUS`. We keep `blocked` derived-only and
     let escalation set a node-level `open_question` marker instead. `status`
     is never touched by `fail`; the `[!]` icon stays reserved for real
     dependency-derived blocking.
  2. **open_question lives on the node** as a single source of truth:
     `node["open_question"] = {question, raised_at, raised_by, attempts}`.
     #115's md queue scans nodes carrying this field — no second list to keep
     in sync, and deleting a node auto-clears its question.
  3. **Threshold + backoff:** default `max_attempts = 3`, overridable per node
     via `--max-attempts` on `fail`. `retry_backoff = min(60 * 2**(n-1), 3600)`
     (capped exponential), recomputed and stored on every failure so a caller
     can "retry later" rather than immediately.

Seams under test
----------------
  1. Pure policy helpers in `roadmap` (one source of truth for both carriers):
     `compute_retry_backoff`, `should_escalate`, `DEFAULT_MAX_ATTEMPTS`.
  2. Carrier layer: `Roadmap.record_failure` / `RoadmapBundle.record_failure`
     (parallel implementations sharing the pure helpers) — run on both
     carriers.
  3. CLI contract (subprocess: exit code + stderr `E_*` code) — `fail` runs
     against **both** carriers. `fail` is executor-owned, so it passes through
     the same lease gate as `status` (Story 33 "records" is an execution
     signal; depends on #111).

Run: python tests/test_failure_semantics.py        (also works under pytest)
"""

import json
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
from roadmap_sqlite import RoadmapSqlite
from roadmap import (
    DEFAULT_MAX_ATTEMPTS,
    compute_retry_backoff,
    should_escalate,
)


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                          capture_output=True, text=True)


def load_instance(path: str, storage: str):
    if storage == "bundle":
        from roadmap_bundle import RoadmapBundle
        rb = RoadmapBundle(path)
        rb.load()
        return rb
    if storage == "sqlite":
        r = RoadmapSqlite(path)
        r.load()
        return r
    r = roadmap.Roadmap(path)
    r.load()
    return r


# ── Slice 1: pure backoff / threshold policy ──

class BackoffPolicy(unittest.TestCase):
    def test_backoff_grows_exponentially_from_base(self):
        self.assertEqual(compute_retry_backoff(1), 60)
        self.assertEqual(compute_retry_backoff(2), 120)
        self.assertEqual(compute_retry_backoff(3), 240)

    def test_backoff_is_capped(self):
        self.assertEqual(compute_retry_backoff(7), 3600)
        self.assertEqual(compute_retry_backoff(50), 3600)

    def test_escalation_threshold_is_inclusive(self):
        # the Nth failure (attempts == max_attempts) is the one that escalates
        self.assertFalse(should_escalate(2, 3))
        self.assertTrue(should_escalate(3, 3))
        self.assertTrue(should_escalate(4, 3))

    def test_default_threshold_is_three(self):
        self.assertEqual(DEFAULT_MAX_ATTEMPTS, 3)


# ── Slice 2: carrier layer (both carriers) ──

class FailureContract:
    storage = "single"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / ("r.sqlite" if self.storage == "sqlite"
                                         else "r.json" if self.storage == "single" else "r.bundle")
        init = run_cli("init", str(path), "--title", "fail", "--storage", self.storage)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.assertEqual(run_cli("add", str(path), "1", "A").returncode, 0)
        self.path = str(path)
        self.r = load_instance(self.path, self.storage)

    def tearDown(self):
        self.tmp.cleanup()

    def node(self):
        return self.r.get_node("1-1")

    def test_first_failure_increments_attempts_and_records_error(self):
        self.r.record_failure("1-1", "boom")
        n = self.node()
        self.assertEqual(n["attempts"], 1)
        self.assertEqual(n["last_error"], "boom")
        self.assertIn("last_failed_at", n)

    def test_first_failure_backoff_is_base(self):
        self.r.record_failure("1-1", "boom")
        self.assertEqual(self.node()["retry_backoff"], 60)

    def test_backoff_grows_across_failures(self):
        self.r.record_failure("1-1", "e1")
        self.r.record_failure("1-1", "e2")
        self.r.record_failure("1-1", "e3")
        self.assertEqual(self.node()["retry_backoff"], 240)
        self.assertEqual(self.node()["attempts"], 3)

    def test_no_open_question_below_threshold(self):
        self.r.record_failure("1-1", "e1")
        self.r.record_failure("1-1", "e2")
        self.assertNotIn("open_question", self.node())

    def test_escalation_sets_open_question_on_threshold(self):
        self.r.record_failure("1-1", "e1")
        self.r.record_failure("1-1", "e2")
        self.r.record_failure("1-1", "e3")
        n = self.node()
        self.assertIn("open_question", n)
        oq = n["open_question"]
        self.assertEqual(oq["attempts"], 3)
        self.assertIn("question", oq)
        self.assertIn("raised_at", oq)
        self.assertIn("raised_by", oq)

    def test_escalation_does_not_write_status(self):
        """Regression guard for decision #1: `blocked` stays purely derived."""
        self.r.record_failure("1-1", "e1")
        self.r.record_failure("1-1", "e2")
        self.r.record_failure("1-1", "e3")
        n = self.node()
        self.assertEqual(n["status"], "pending")  # add default; fail must not change it
        self.assertNotIn("blocked", n)            # no blocks edge → never a blocked marker

    def test_per_node_max_attempts_override(self):
        # 通过 record_failure 的 max_attempts 覆盖参数落盘（两 carrier 都走真实写回）。
        self.r.record_failure("1-1", "e1", max_attempts=2)
        self.assertNotIn("open_question", self.node())
        self.r.record_failure("1-1", "e2")
        self.assertIn("open_question", self.node())

    def test_refail_after_escalation_keeps_open_question(self):
        for _ in range(3):
            self.r.record_failure("1-1", "e")
        before = self.node()["open_question"]["raised_at"]
        self.r.record_failure("1-1", "e-again")
        n = self.node()
        self.assertIn("open_question", n)
        self.assertEqual(n["open_question"]["attempts"], 4)
        self.assertEqual(n["open_question"]["raised_at"], before)  # first raise timestamp kept


class SingleFileFailure(FailureContract, unittest.TestCase):
    storage = "single"


class BundleFailure(FailureContract, unittest.TestCase):
    storage = "bundle"


class SqliteFailure(FailureContract, unittest.TestCase):
    """Third-pass carrier for #116: RoadmapSqlite must agree on failure semantics."""
    storage = "sqlite"


# ── Slice 3: CLI contract (both carriers) ──

class FailureCliContract:
    storage = "single"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / ("r.sqlite" if self.storage == "sqlite"
                                         else "r.json" if self.storage == "single" else "r.bundle")
        init = run_cli("init", str(path), "--title", "fail", "--storage", self.storage)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.assertEqual(run_cli("add", str(path), "1", "A").returncode, 0)
        self.path = str(path)
        self.assertEqual(run_cli("lease", "claim", self.path, "1-1", "--agent", "a7").returncode, 0)
        self.holder = ["--as-agent", "a7", "--token", "1"]

    def tearDown(self):
        self.tmp.cleanup()

    def get_node(self, node_id="1-1"):
        out = run_cli("get", self.path, node_id)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_fail_requires_lease_like_status(self):
        bad = run_cli("fail", self.path, "1-1", "--error", "boom")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)

    def test_holder_can_fail(self):
        ok = run_cli("fail", self.path, "1-1", "--error", "boom", *self.holder)
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_fail_cli_records_attempts_and_backoff(self):
        run_cli("fail", self.path, "1-1", "--error", "boom", *self.holder)
        n = self.get_node()
        self.assertEqual(n["attempts"], 1)
        self.assertEqual(n["retry_backoff"], 60)

    def test_fail_cli_escalates_and_surface_open_question(self):
        for i in range(3):
            rc = run_cli("fail", self.path, "1-1", "--error", f"e{i}", *self.holder)
            self.assertEqual(rc.returncode, 0, rc.stderr)
        n = self.get_node()
        self.assertIn("open_question", n)
        self.assertEqual(n["open_question"]["attempts"], 3)
        # status untouched — decision #1
        self.assertEqual(n["status"], "pending")

    def test_fail_cli_per_node_max_attempts(self):
        run_cli("fail", self.path, "1-1", "--error", "e1", "--max-attempts", "2", *self.holder)
        self.assertNotIn("open_question", self.get_node())
        run_cli("fail", self.path, "1-1", "--error", "e2", *self.holder)
        self.assertIn("open_question", self.get_node())


class SingleFileFailureCli(FailureCliContract, unittest.TestCase):
    storage = "single"


class BundleFailureCli(FailureCliContract, unittest.TestCase):
    storage = "bundle"


class SqliteFailureCli(FailureCliContract, unittest.TestCase):
    """Third-pass CLI carrier for #116: `fail` against sqlite-backed roadmap."""
    storage = "sqlite"


if __name__ == "__main__":
    unittest.main(verbosity=2)

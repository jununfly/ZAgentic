#!/usr/bin/env python3
"""Phase-4d wiring locks: the §4.4 lease clock must reach the paths that actually decide
writes, views, and claims — not just the library API.

Every test here fails against Phase-4c behavior:
  * `task/ticket status` ignored the clock → an expired claim still blocked a write (W1);
  * `orchestrate --execute` minted lease-less claims → a dead agent held a plan forever (W2);
  * `viz --now` was parsed but never reached `render()` → `.mmd` disagreed with `.html` (W3/W4);
  * the step-2 `.governed.json` marker survived closeout (W6).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import dp_driven_viz                                      # noqa: E402
from dp_driven_model import DpDriven                      # noqa: E402


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")

    def run_cli(self, *args, expect_code=0):
        proc = subprocess.run([sys.executable, str(CLI), *args],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, expect_code,
                         f"cmd={args}\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def init(self, destination="w"):
        self.run_cli("init", self.db, "--destination", destination)

    def plan0_claimed_by_alice(self, lease=100, at=1000):
        self.init()
        self.run_cli("task", "add", self.db, "--name", "P")        # plan/task 0
        self.run_cli("claim", self.db, "plan", "0", "--agent", "alice",
                     "--lease-seconds", str(lease), "--now", str(at))

    def claims_at(self, epoch):
        return json.loads(self.run_cli("claims", "list", self.db, "--now", str(epoch)).stdout)

    def row(self, kind, ref_id, rows=None):
        rows = self.claims_at(0) if rows is None else rows
        return next(r for r in rows if r["kind"] == kind and r["ref_id"] == ref_id)


class StatusGate(Harness):
    """W1: the claim gate must see the same clock `claim` wrote."""

    def test_expired_lets_other_agent_write_plan_status(self):
        self.plan0_claimed_by_alice(lease=100, at=1000)
        # expired at 1200 → §4.4 "an expired claim is inert" holds on the real write path
        self.run_cli("task", "status", self.db, "0", "--set", "已完成",
                     "--agent", "bob", "--now", "1200")
        tv = json.loads(self.run_cli("task", "view", self.db, "0").stdout)
        self.assertEqual(tv["status"], "已完成")
        # ownership is *not* silently transferred: alice's stale row stays, expired
        self.assertEqual(self.row("plan", 0, self.claims_at(1200))["agent"], "alice")

    def test_unexpired_other_agent_is_still_blocked(self):
        """Counterpart that keeps the previous test from being vacuous."""
        self.plan0_claimed_by_alice(lease=100, at=1000)
        p = self.run_cli("task", "status", self.db, "0", "--set", "已完成",
                         "--agent", "bob", "--now", "1050", expect_code=2)
        self.assertIn("E_CLAIM_HELD_BY_OTHER", p.stderr)
        self.assertEqual(self.row("plan", 0)["agent"], "alice")

    def test_expired_lets_other_agent_write_ticket_status(self):
        self.init()
        self.run_cli("task", "add", self.db, "--name", "P")
        self.run_cli("ticket", "add", self.db, "--task", "0")
        self.run_cli("claim", self.db, "ticket", "0", "--agent", "alice",
                     "--lease-seconds", "100", "--now", "1000")
        p = self.run_cli("ticket", "status", self.db, "0", "--set", "已完成",
                         "--agent", "bob", "--now", "1050", expect_code=2)
        self.assertIn("E_CLAIM_HELD_BY_OTHER", p.stderr)          # still held…
        self.run_cli("ticket", "status", self.db, "0", "--set", "已完成",
                     "--agent", "bob", "--now", "1200")           # …now inert
        out = json.loads(self.run_cli("status", self.db, "ticket:0").stdout)
        self.assertEqual(out["status"], "已完成")

    def test_status_without_agent_bypasses_gate_even_when_unexpired(self):
        """§4.4: `agent=None` = Human direct action. The injected clock must not
        silently turn Human writes into gated ones."""
        self.plan0_claimed_by_alice(lease=100, at=1000)
        self.run_cli("task", "status", self.db, "0", "--set", "已完成", "--now", "1050")

    def test_status_default_clock_is_wall(self):
        """D1: no `--now` ⇒ wall clock. A lease stamped at epoch 0 for 1s is long expired."""
        self.init()
        self.run_cli("task", "add", self.db, "--name", "P")
        self.run_cli("claim", self.db, "plan", "0", "--agent", "alice",
                     "--lease-seconds", "1", "--now", "0")
        self.run_cli("task", "status", self.db, "0", "--set", "已完成", "--agent", "bob")


class OrchestrateLease(Harness):
    """W2: `orchestrate --execute` must mint a *revivable* claim."""

    def linked_pair(self):
        self.init()
        self.run_cli("ticket", "add", self.db)
        self.run_cli("ticket", "add", self.db)
        self.run_cli("blocks", "add", self.db, "--from", "ticket:0", "--to", "ticket:1")

    def isolated_pair(self):
        self.init()
        self.run_cli("ticket", "add", self.db)
        self.run_cli("ticket", "add", self.db)

    def execute(self, *extra):
        out = json.loads(self.run_cli("orchestrate", self.db, "--agent", "alice",
                                      "--execute", *extra).stdout)
        return out["applied"]

    def test_new_plan_claim_carries_a_real_lease(self):
        self.linked_pair()
        applied = self.execute("--now", "1000", "--lease-seconds", "100")
        tid = next(a["task_id"] for a in applied if a["action"] == "new_plan")
        r = self.row("plan", tid)
        self.assertEqual(r["last_seen_at"], 1000)
        self.assertEqual(r["lease_seconds"], 100)
        self.assertTrue(self.claims_at(1200) and self.row("plan", tid,
                                                          self.claims_at(1200))["expired"])

    def test_orchestrated_claim_is_renewable(self):
        """Only a stamped `last_seen_at` can be heartbeated — this is the crash-recovery
        counterpart of the previous test."""
        self.linked_pair()
        tid = next(a["task_id"] for a in self.execute("--now", "1000",
                                                      "--lease-seconds", "100")
                   if a["action"] == "new_plan")
        self.run_cli("renew", self.db, "plan", str(tid), "--agent", "alice", "--now", "1050")
        self.assertFalse(self.row("plan", tid, self.claims_at(1140))["expired"])
        self.assertTrue(self.row("plan", tid, self.claims_at(1200))["expired"])

    def test_no_lease_flag_pins_orchestrated_claim(self):
        self.linked_pair()
        tid = next(a["task_id"] for a in self.execute("--now", "0", "--no-lease")
                   if a["action"] == "new_plan")
        self.assertFalse(self.row("plan", tid,
                                  self.claims_at(2_000_000_000))["expired"])

    def test_settlement_step_claim_matches_model_shape(self):
        """W5: the optimizer's settle step used to hand-append a claim row missing the
        lease columns; the claim table must stay one uniform shape."""
        self.isolated_pair()
        tid = next(a["task_id"] for a in self.execute("--now", "1000")
                   if a["action"] == "settle")
        r = self.row("plan", tid)
        self.assertEqual(r["agent"], "__settlement__")
        self.assertIn("last_seen_at", r)
        self.assertIn("lease_seconds", r)
        self.assertIsNone(r["last_seen_at"])        # sentinel never expires (§4.5)
        self.assertIsNone(r["lease_seconds"])

    def test_preview_mints_no_lease(self):
        self.linked_pair()
        before = Path(self.db).read_bytes()
        self.run_cli("orchestrate", self.db, "--agent", "alice",
                     "--now", "1000", "--lease-seconds", "100")   # no --execute
        self.assertEqual(Path(self.db).read_bytes(), before)


class VizClock(Harness):
    """W3/W4: one clock, both formats, and the API stays clock-free."""

    def test_mermaid_honors_now(self):
        self.plan0_claimed_by_alice(lease=100, at=1000)
        self.assertIn("class T0 plan_inflight",
                      self.run_cli("viz", self.db, "--now", "1050").stdout)
        self.assertIn("class T0 plan_paused",
                      self.run_cli("viz", self.db, "--now", "1200").stdout)

    def test_mermaid_and_html_agree_on_expired_plan(self):
        self.plan0_claimed_by_alice(lease=100, at=1000)
        mmd = self.run_cli("viz", self.db, "--now", "1200").stdout
        html = self.run_cli("viz", self.db, "--format", "html", "--now", "1200").stdout
        self.assertIn("class T0 plan_paused", mmd)
        self.assertIn("class T0 plan_paused", html)               # graph BODY, not just the card
        ir = json.loads(html.split('id="dp-ir">')[1].split("</script>")[0])
        self.assertEqual(ir["T0"]["claim_class"], "plan_paused")
        self.assertEqual(ir["T0"]["claim_agent"], "alice")   # stale holder stays visible (§4.4)
        self.assertTrue(ir["T0"]["claim_expired"])

    def test_python_api_stays_clock_free(self):
        self.plan0_claimed_by_alice(lease=100, at=1000)
        m = DpDriven.open(self.db)
        self.assertIn("class T0 plan_inflight", dp_driven_viz.render(m))     # epoch=None ⇒ not judged
        self.assertIn("class T0 plan_paused", dp_driven_viz.render(m, epoch=1200))

    def test_render_is_deterministic_per_epoch(self):
        self.plan0_claimed_by_alice()
        m = DpDriven.open(self.db)
        self.assertEqual(dp_driven_viz.render(m, epoch=1), dp_driven_viz.render(m, epoch=1))

    def test_render_to_file_uses_the_epoch(self):
        self.plan0_claimed_by_alice(lease=100, at=1000)
        m = DpDriven.open(self.db)
        out = str(Path(self.tmp.name) / "dp_driven.mmd")
        dp_driven_viz.render_to_file(m, out, epoch=1200)
        with open(out, encoding="utf-8") as fh:
            self.assertIn("class T0 plan_paused", fh.read())


class CloseoutMarker(Harness):
    """W6: marker lifecycle — removed on success, untouched on a failed gate."""

    def complete_run(self, marker_dir=None):
        self.init()
        self.run_cli("task", "add", self.db, "--name", "唯一计划")
        self.run_cli("task", "status", self.db, "0", "--set", "已完成")
        marker = os.path.join(marker_dir or os.path.dirname(self.db),
                              "dp_driven.governed.json")
        with open(marker, "w", encoding="utf-8") as fh:
            json.dump({"governed_at": "2026-01-01 00:00:00", "corpus": []}, fh)
        return marker

    def test_custom_marker_path_is_the_one_removed(self):
        other = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(other, ignore_errors=True))
        marker = self.complete_run(marker_dir=other)
        payload = json.loads(self.run_cli("closeout", "delete", self.db, "--force",
                                         "--marker", marker).stdout)
        self.assertIn(marker, payload["sidecars_removed"])
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(os.path.exists(self.db))

    def test_failed_gate_keeps_marker_carrier_and_log(self):
        self.init()
        self.run_cli("task", "add", self.db, "--name", "未终态")          # not terminal
        marker = os.path.join(os.path.dirname(self.db), "dp_driven.governed.json")
        with open(marker, "w", encoding="utf-8") as fh:
            json.dump({"governed_at": "t", "corpus": []}, fh)
        self.run_cli("metrics", "record", self.db, "--type", "token", "--value", "1")
        p = self.run_cli("closeout", "delete", self.db, "--force", expect_code=2)
        self.assertIn("E_NOT_COMPLETE", p.stderr)
        self.assertTrue(os.path.exists(marker))            # the clock-injected cleanup is
        self.assertTrue(os.path.exists(self.db))           # reachable only after the gate
        self.assertTrue(os.path.exists(
            os.path.join(os.path.dirname(self.db), "dp_driven.events.jsonl")))


class DocScope(unittest.TestCase):
    """D6: the wall-clock claim is true only for expiry — keep the docs scoped (W7)."""

    SCOPED = "lease/expiry evaluation never reads the wall clock"
    UNSCOPED = "model never reads the wall clock"

    def doc(self, rel):
        with open(SKILL_DIR / rel, encoding="utf-8") as fh:
            # collapse whitespace: the docs wrap these sentences across lines
            return " ".join(fh.read().split()).lower()

    def test_docs_scope_the_clock_claim_to_lease_evaluation(self):
        for rel in ("SKILL.md", "references/dp_driven-ttl.md",
                    "references/dp_driven-data-model.md"):
            text = self.doc(rel)
            self.assertIn(self.SCOPED, text,
                          f"{rel}: the expiry claim must name what it scopes to")
            self.assertNotIn(self.UNSCOPED, text,
                             f"{rel}: unscoped overclaim regressed")

    def test_model_helper_documents_its_own_scope(self):
        with open(SKILL_DIR / "scripts" / "dp_driven_model.py", encoding="utf-8") as fh:
            src = " ".join(fh.read().split())
        self.assertIn("expiry itself consults no clock", src)
        self.assertNotIn("model never reads wall clock", src)   # the #314-era blanket phrasing


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""§9 metrics collection — invariant locks (Phase-4c).

Three hard guarantees plus the arithmetic:
1. **log ≠ state (§3.1)**: events are an observation channel; no derivation may read them
   — `test_events_inert_to_state` fails the moment render()/suggest() ever consults the log.
2. **read-only + deterministic** surfaces (report / reflow-check never write).
3. **honest calibration**: nothing claims a baseline; §9's two data-gated thresholds stay
   `null` and every metric is `calibrated: false`.

Run: python tests/test_dp_driven_metrics.py
"""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"

from dp_driven_model import DpDriven, DpDrivenError
import dp_driven_metrics as met


def seeded_db(dirname=None):
    """Carrier + a cohesive pool pair + two orphans, so orchestrate creates one plan and
    settlement still finds work."""
    d = dirname or tempfile.mkdtemp()
    db = os.path.join(d, "dp_driven.sqlite")
    m = DpDriven.init(db, "登录改造")
    m.add_task("起点")
    tk = [m.add_ticket() for _ in range(4)]
    m.add_blocks("ticket", tk[0], "ticket", tk[1])
    m.add_finding()
    m.save()
    return db, m


def cli(*args):
    return subprocess.run([sys.executable, str(CLI), *[str(a) for a in args]],
                          capture_output=True, text=True)


class EventLog(unittest.TestCase):
    def test_default_events_path(self):
        self.assertEqual(met.default_events_path("/tmp/x.sqlite"), "/tmp/x.events.jsonl")
        self.assertEqual(met.default_events_path("/tmp/x.db"), "/tmp/x.events.jsonl")

    def test_append_creates_file_and_round_trips(self):
        db, _ = seeded_db()
        ev = met.append_event(db, "token", agent="alice", value=42.5, now="2026-01-01 00:00:00")
        back = met.read_events(db)
        self.assertEqual(back, [ev])
        self.assertEqual(back[0]["value"], 42.5)
        self.assertEqual(back[0]["type"], "token")

    def test_read_events_absent_file_is_empty(self):
        db, _ = seeded_db()
        self.assertEqual(met.read_events(db), [])

    def test_malformed_line_raises(self):
        db, _ = seeded_db()
        met.append_event(db, "token", value=1)
        with open(met.default_events_path(db), "a", encoding="utf-8") as fh:
            fh.write("{ not json\n")
        with self.assertRaises(DpDrivenError) as cm:
            met.read_events(db)
        self.assertEqual(cm.exception.code, "E_METRICS_LOG")

    def test_unknown_event_type_rejected(self):
        db, _ = seeded_db()
        with self.assertRaises(DpDrivenError):
            met.append_event(db, "bogus")

    def test_events_inert_to_state(self):
        # §3.1 red line: the observation channel must never feed a derivation.
        db, m = seeded_db()
        rendered_before = __import__("dp_driven_viz").render(m)
        steps_before = json.dumps(
            [vars(s) for s in __import__("dp_driven_optimize").suggest(m)],
            default=str, sort_keys=True)
        for i in range(5):
            met.append_event(db, "orchestrate", agent="x", payload=[{"action": "new_plan",
                                                                    "task_id": 99, "items": []}])
            met.append_event(db, "verdict", kind="plan", ref_id=99, payload={"verdict": "kept"})
        self.assertEqual(__import__("dp_driven_viz").render(m), rendered_before)
        self.assertEqual(json.dumps([vars(s) for s in __import__("dp_driven_optimize").suggest(m)],
                                    default=str, sort_keys=True), steps_before)
        m2 = DpDriven.open(db)
        self.assertEqual(m2.data, m.data)          # the log never leaks into the carrier

    def test_write_report_md_only_target_path(self):
        db, m = seeded_db()
        out = os.path.join(os.path.dirname(db), "metrics.md")
        met.append_event(db, "token", value=7)
        r = met.write_report_md(m, out)
        self.assertEqual(r, out)
        self.assertEqual(sorted(os.listdir(os.path.dirname(db))),
                         sorted(["dp_driven.sqlite", "dp_driven.events.jsonl", "metrics.md"]))


class ReportMath(unittest.TestCase):
    def setUp(self):
        self.db, self.m = seeded_db()

    def test_round_counts_and_settlement_rate(self):
        met.append_event(self.db, "orchestrate", payload=[])
        met.append_event(self.db, "orchestrate", payload=[])
        met.append_event(self.db, "settlement", kind="plan", ref_id=1)
        rep = met.report(self.m, met.read_events(self.db))
        self.assertEqual(rep["metrics"]["orchestration_rounds"]["value"], 3)
        self.assertEqual(rep["metrics"]["orchestration_rounds"]["breakdown"],
                         {"orchestrate": 2, "settlement": 1})
        self.assertAlmostEqual(rep["metrics"]["settlement_trigger_rate"]["value"], 33.33, places=2)

    def test_cohesion_hit_rate_denominator_is_annotated_only(self):
        applied = [{"action": "new_plan", "task_id": 1, "items": []},
                   {"action": "new_plan", "task_id": 2, "items": []},
                   {"action": "new_plan", "task_id": 3, "items": []}]
        met.append_event(self.db, "orchestrate", payload=applied)
        met.append_event(self.db, "verdict", kind="plan", ref_id=1, payload={"verdict": "kept"})
        met.append_event(self.db, "verdict", kind="plan", ref_id=2, payload={"verdict": "split"})
        rep = met.report(self.m, met.read_events(self.db))
        c = rep["metrics"]["cohesion_hit_rate"]
        self.assertAlmostEqual(c["value"], 50.0)          # 1 kept / 2 annotated
        self.assertEqual(c["unannotated_plans"], [3])     # missing data is NOT a score
        self.assertEqual(c["denominator"]["annotated"], 2)

    def test_no_events_yields_null_not_zero(self):
        rep = met.report(self.m, [])
        self.assertIsNone(rep["metrics"]["cohesion_hit_rate"]["value"])
        self.assertIsNone(rep["metrics"]["settlement_trigger_rate"]["value"])
        self.assertIsNone(rep["metrics"]["token_per_effort"]["value"])

    def test_token_sum_and_missing_threshold(self):
        met.append_event(self.db, "token", value=1200.5)
        met.append_event(self.db, "token", value=800)
        rep = met.report(self.m, met.read_events(self.db))
        t = rep["metrics"]["token_per_effort"]
        self.assertEqual(t["value"], 2000.5)
        self.assertIsNone(t["threshold"])                  # §9: no prior for tokens
        self.assertFalse(t["calibrated"])

    def test_uncalibrated_flags(self):
        rep = met.report(self.m, [])
        self.assertEqual(rep["calibration"]["state"], "uncalibrated")
        for key, entry in rep["metrics"].items():
            self.assertFalse(entry["calibrated"], key)
        self.assertIsNone(rep["metrics"]["orchestration_rounds"]["threshold"])

    def test_report_deterministic(self):
        met.append_event(self.db, "orchestrate", payload=[{"action": "new_plan", "task_id": 1}])
        events = met.read_events(self.db)
        a = json.dumps(met.report(self.m, events), sort_keys=True, ensure_ascii=False)
        b = json.dumps(met.report(self.m, events), sort_keys=True, ensure_ascii=False)
        self.assertEqual(a, b)

    def test_report_is_pure_read(self):
        db_bytes = hashlib.sha256(Path(self.db).read_bytes()).hexdigest()
        before = copy.deepcopy(self.m.data)
        met.append_event(self.db, "token", value=5)
        ev_bytes = Path(met.default_events_path(self.db)).read_bytes()
        met.report(self.m, met.read_events(self.db))
        self.assertEqual(self.m.data, before)
        self.assertEqual(hashlib.sha256(Path(self.db).read_bytes()).hexdigest(), db_bytes)
        self.assertEqual(Path(met.default_events_path(self.db)).read_bytes(), ev_bytes)


class ReflowAudit(unittest.TestCase):
    def test_reflow_passes_on_honest_state(self):
        db, m = seeded_db()
        m.set_ticket_status(m.data["tickets"]["2"]["id"], "已完成")
        out = met.reflow_check(m)
        self.assertTrue(out["correct"], out["violations"])
        self.assertEqual(out["violations"], [])
        self.assertEqual(out["rate_pct"], 100.0)

    def test_reflow_detects_stale_derivation_canary(self):
        # Non-vacuous: a model whose derived view lies MUST be caught. node_view is
        # overridden to invert the blocked flag — exactly the failure the §3.2 "always
        # derive" discipline exists to prevent.
        db, m = seeded_db()
        class LyingModel(DpDriven):
            def node_view(self, kind, node_id):
                v = super().node_view(kind, node_id)
                if "blocked" in v:
                    del v["blocked"]; v.pop("blocked_reason", None)
                else:
                    v["blocked"] = True
                v["derived_blocked"] = "blocked" in v
                v["shown_blocked"] = v["derived_blocked"] or v.get("external_hold") is not None
                return v
        m2 = LyingModel.open(db) if hasattr(LyingModel, "open") else m
        m2.__class__ = LyingModel
        out = met.reflow_check(m2)
        self.assertFalse(out["correct"])
        self.assertTrue(out["violations"])

    def test_reflow_tracks_derivation_as_prereq_completes(self):
        # The §3.2 recomputation ("回灌") is what the metric audits: completing the
        # prereq must flip the dependent from blocked→free with no stale residue.
        db, m = seeded_db()
        t0 = m.data["tickets"]["0"]["id"]
        t1 = m.data["tickets"]["1"]["id"]
        self.assertTrue(m.node_view("ticket", t1).get("blocked"))
        out = met.reflow_check(m)
        self.assertEqual(out["violations"], [])
        m.set_ticket_status(t0, "已完成")
        self.assertNotIn("blocked", m.node_view("ticket", t1))   # absent, not False (§3.2)
        out2 = met.reflow_check(m)
        self.assertEqual(out2["violations"], [])
        self.assertTrue(out2["correct"])


class MetricsCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")
        r = cli("init", self.db, "--destination", "登录改造")
        self.assertEqual(r.returncode, 0, r.stderr)
        for _ in range(4):
            self.assertEqual(cli("ticket", "add", self.db).returncode, 0)
        self.assertEqual(cli("task", "add", self.db, "--name", "起点").returncode, 0)
        self.assertEqual(cli("blocks", "add", self.db, "--from", "ticket:0",
                             "--to", "ticket:1").returncode, 0)
        self.evp = met.default_events_path(self.db)

    def test_auto_events_orchestrate_settlement_terminal_reassign_membership(self):
        self.assertEqual(cli("orchestrate", self.db, "--agent", "alice", "--execute").returncode, 0)
        self.assertEqual(cli("settlement", "run", self.db).returncode, 0)
        self.assertEqual(cli("ticket", "add", self.db).returncode, 0)
        self.assertEqual(cli("ticket", "assign", self.db, "4", "--task", "1").returncode, 0)
        self.assertEqual(cli("finding", "add", self.db).returncode, 0)
        self.assertEqual(cli("finding", "membership", "add", self.db, "0", "--task", "1").returncode, 0)
        self.assertEqual(cli("finding", "membership", "remove", self.db, "0", "--task", "1").returncode, 0)
        self.assertEqual(cli("task", "status", self.db, "1", "--set", "已完成").returncode, 0)
        types = [json.loads(l)["type"] for l in open(self.evp, encoding="utf-8")]
        for want in ("orchestrate", "settlement", "reassign", "membership", "plan_terminal"):
            self.assertIn(want, types, types)

    def test_dry_run_writes_no_event(self):
        self.assertEqual(cli("suggest", self.db).returncode, 0)
        self.assertEqual(cli("orchestrate", self.db, "--agent", "alice").returncode, 0)  # preview
        self.assertFalse(os.path.exists(self.evp))

    def test_nonterminal_status_writes_no_plan_terminal(self):
        self.assertEqual(cli("task", "status", self.db, "0", "--set", "未完成").returncode, 0)
        self.assertFalse(os.path.exists(self.evp))

    def test_report_cli_json_shape(self):
        self.assertEqual(cli("orchestrate", self.db, "--agent", "alice", "--execute").returncode, 0)
        rep = json.loads(cli("metrics", "report", self.db).stdout)
        self.assertEqual(sorted(rep["metrics"]),
                         ["cohesion_hit_rate", "orchestration_rounds", "reflow_correctness",
                          "settlement_trigger_rate", "token_per_effort"])
        self.assertEqual(rep["calibration"]["state"], "uncalibrated")

    def test_report_cli_is_readonly(self):
        self.assertEqual(cli("metrics", "report", self.db).returncode, 0)
        self.assertFalse(os.path.exists(self.evp))
        before = Path(self.db).read_bytes()
        self.assertEqual(cli("metrics", "reflow-check", self.db).returncode, 0)
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_record_and_analyze_flow(self):
        self.assertEqual(cli("metrics", "record", self.db, "--type", "token",
                             "--value", "500", "--agent", "alice").returncode, 0)
        self.assertEqual(cli("orchestrate", self.db, "--agent", "alice", "--execute").returncode, 0)
        plan = json.loads(cli("metrics", "report", self.db, "--no-audit").stdout)
        pid = plan["metrics"]["cohesion_hit_rate"]["optimizer_plans"][0]
        self.assertEqual(cli("metrics", "annotate", self.db, "plan", pid,
                             "--verdict", "kept").returncode, 0)
        rep = json.loads(cli("metrics", "report", self.db, "--no-audit").stdout)
        self.assertEqual(rep["metrics"]["cohesion_hit_rate"]["value"], 100.0)
        self.assertEqual(rep["metrics"]["token_per_effort"]["value"], 500.0)

    def test_annotate_unknown_plan_exit2(self):
        p = cli("metrics", "annotate", self.db, "plan", "77", "--verdict", "kept")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("E_NO_SUCH_TASK", p.stderr)

    def test_bad_verdict_is_usage_error(self):
        self.assertEqual(cli("metrics", "annotate", self.db, "plan", "0",
                             "--verdict", "meh").returncode, 1)

    def test_report_missing_db_exit3(self):
        self.assertEqual(cli("metrics", "report",
                             str(Path(self.tmp.name) / "nope.sqlite")).returncode, 3)

    def test_report_out_writes_markdown(self):
        out = str(Path(self.tmp.name) / "metrics.md")
        p = cli("metrics", "report", self.db, "--out", out)
        self.assertEqual(p.returncode, 0, p.stderr)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("# Metrics report (§9)", text)
        self.assertIn("calibrated", text)
        self.assertIn("| reflow_correctness |", text)

    def test_malformed_log_surfaces_exit2(self):
        cli("metrics", "record", self.db, "--type", "token", "--value", "1")
        with open(self.evp, "a", encoding="utf-8") as fh:
            fh.write("garbage\n")
        p = cli("metrics", "report", self.db)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("E_METRICS_LOG", p.stderr)


class MetricsCloseout(unittest.TestCase):
    """§5.2 lifecycle: the sidecar log is process fuel — it dies WITH the carrier, and the
    exported md report survives (process becomes fuel)."""

    def test_closeout_delete_removes_event_log(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "dp_driven.sqlite")
        self.assertEqual(cli("init", db, "--destination", "收尾").returncode, 0)
        self.assertEqual(cli("task", "add", db, "--name", "唯一计划").returncode, 0)
        self.assertEqual(cli("metrics", "record", db, "--type", "token", "--value", "10").returncode, 0)
        evp = met.default_events_path(db)
        self.assertTrue(os.path.exists(evp))
        self.assertEqual(cli("task", "status", db, "0", "--set", "已完成").returncode, 0)
        out = os.path.join(d, "metrics.md")
        self.assertEqual(cli("metrics", "report", db, "--out", out).returncode, 0)
        with open(os.path.join(d, "dp_driven.governed.json"), "w", encoding="utf-8") as fh:
            json.dump({"governed_at": "2026-01-01 00:00:00", "corpus": [out]}, fh)
        p = cli("closeout", "delete", db, "--force")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(db))
        self.assertFalse(os.path.exists(evp))          # log removed with the carrier
        self.assertTrue(os.path.exists(out))           # durable corpus survives
        payload = json.loads(p.stdout)
        # Phase-4d: the step-2 marker is process fuel too, so it dies in the same step.
        self.assertEqual(payload["sidecars_removed"],
                         [evp, os.path.join(d, "dp_driven.governed.json")])
        self.assertFalse(os.path.exists(os.path.join(d, "dp_driven.governed.json")))

    def test_closeout_delete_blocked_without_marker(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "dp_driven.sqlite")
        cli("init", db, "--destination", "x")
        cli("task", "add", db, "--name", "t")
        cli("task", "status", db, "0", "--set", "已完成")
        met.append_event(db, "token", value=1)
        p = cli("closeout", "delete", db, "--force")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("E_CLOSEOUT_NOT_GOVERNED", p.stderr)
        self.assertTrue(os.path.exists(met.default_events_path(db)))   # gate holds: nothing deleted


if __name__ == "__main__":
    unittest.main(verbosity=2)

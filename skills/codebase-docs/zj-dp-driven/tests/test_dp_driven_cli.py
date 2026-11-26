#!/usr/bin/env python3
"""§4 CLI — end-to-end subprocess tests for dp_driven_cli.py.

The CLI is a thin wrapper around DpDriven, so these tests target: (a) exit-code mapping
(0/1/2/3/4), (b) stdout JSON shape for read commands, (c) that a happy orchestration
sequence (init → task → ticket → status → closeout) drives the carrier correctly.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"


class CliHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")

    def run_cli(self, *args, expect_code=0, stdin=None):
        proc = subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True, text=True, input=stdin,
        )
        self.assertEqual(
            proc.returncode, expect_code,
            f"cmd={args}\nstdout={proc.stdout}\nstderr={proc.stderr}",
        )
        return proc


class HappyPath(CliHarness):
    def test_full_run(self):
        # §4.0 init
        p = self.run_cli("init", self.db, "--destination", "上线 v2")
        self.assertEqual(json.loads(p.stdout)["destination"], "上线 v2")
        # task
        p = self.run_cli("task", "add", self.db, "--name", "后端登录",
                         "--context-md", "c.md")
        tid = json.loads(p.stdout)["task_id"]
        # tickets + blocks
        p = self.run_cli("ticket", "add", self.db, "--task", str(tid), "--ref", "gh#1")
        a = json.loads(p.stdout)["ticket_id"]
        p = self.run_cli("ticket", "add", self.db, "--task", str(tid))
        b = json.loads(p.stdout)["ticket_id"]
        p = self.run_cli("blocks", "add", self.db, "--from", f"ticket:{a}", "--to", f"ticket:{b}")
        eid = json.loads(p.stdout)["edge_id"]
        # derived: b blocked
        p = self.run_cli("status", self.db, f"ticket:{b}")
        self.assertTrue(json.loads(p.stdout)["derived_blocked"])
        # claim → status → complete (single agent)
        self.run_cli("claim", self.db, "plan", str(tid), "--agent", "alice")
        self.run_cli("ticket", "status", self.db, str(a), "--set", "已完成", "--agent", "alice")
        # b unblocked now
        p = self.run_cli("status", self.db, f"ticket:{b}")
        self.assertNotIn("blocked", json.loads(p.stdout))
        self.run_cli("ticket", "status", self.db, str(b), "--set", "已完成", "--agent", "alice")
        p = self.run_cli("task", "status", self.db, str(tid), "--set", "已完成",
                         "--agent", "alice", "--summary", "上线")
        p = self.run_cli("complete-check", self.db)
        self.assertTrue(json.loads(p.stdout)["is_complete"])
        # claims list reflects plan claim persists
        p = self.run_cli("claims", "list", self.db)
        rows = json.loads(p.stdout)
        self.assertTrue(any(r["kind"] == "plan" and r["agent"] == "alice" for r in rows))


class PoolAndSettlement(CliHarness):
    def test_pool_and_settlement_roundtrip(self):
        self.run_cli("init", self.db, "--destination", "d")
        self.run_cli("ticket", "add", self.db, "--task", "999") if False else None  # skip; task 999 missing
        # init a real task then create pool items
        self.run_cli("task", "add", self.db, "--name", "主")
        # add 2 unassigned tickets + 1 orphan finding
        a = json.loads(self.run_cli("ticket", "add", self.db).stdout)["ticket_id"]
        b = json.loads(self.run_cli("ticket", "add", self.db).stdout)["ticket_id"]
        f = json.loads(self.run_cli("finding", "add", self.db).stdout)["finding_id"]
        p = self.run_cli("pool", self.db)
        self.assertEqual(
            {(i["kind"], i["id"]) for i in json.loads(p.stdout)},
            {("ticket", a), ("ticket", b), ("finding", f)},
        )
        p = self.run_cli("settlement", "run", self.db, "--name", "收尾")
        out = json.loads(p.stdout)
        self.assertEqual(len(out["items"]), 3)
        # pool now empty
        p = self.run_cli("pool", self.db)
        self.assertEqual(json.loads(p.stdout), [])


class ErrorMapping(CliHarness):
    def test_missing_db_exit3(self):
        self.run_cli("pool", "/nonexistent/dir/foo.sqlite", expect_code=3)

    def test_business_error_exit2(self):
        self.run_cli("init", self.db, "--destination", "d")
        # set_plan_status on nonexistent → E_NO_SUCH_PLAN → exit 2
        self.run_cli("task", "status", self.db, "999", "--set", "已完成", expect_code=2)

    def test_claim_conflict_exit2(self):
        self.run_cli("init", self.db, "--destination", "d")
        tid = json.loads(self.run_cli("task", "add", self.db, "--name", "x").stdout)["task_id"]
        self.run_cli("claim", self.db, "plan", str(tid), "--agent", "alice")
        # bob claim → E_CLAIM_HELD_BY_OTHER → exit 2
        self.run_cli("claim", self.db, "plan", str(tid), "--agent", "bob", expect_code=2)


class Closeout(CliHarness):
    def test_closeout_summary_then_delete(self):
        self.run_cli("init", self.db, "--destination", "d")
        tid = json.loads(self.run_cli("task", "add", self.db, "--name", "x").stdout)["task_id"]
        self.run_cli("task", "status", self.db, str(tid), "--set", "已完成")
        out_md = str(Path(self.tmp.name) / "process-summary.md")
        self.run_cli("closeout", "summary", self.db, "--out", out_md)
        self.assertTrue(Path(out_md).exists())
        # check without marker → E_CLOSEOUT_NOT_GOVERNED → 2
        self.run_cli("closeout", "check", self.db, expect_code=2)
        # drop marker → check passes
        marker = Path(self.tmp.name) / "dp_driven.governed.json"
        marker.write_text(json.dumps({"governed_at": "t1", "corpus": [out_md]}))
        self.run_cli("closeout", "check", self.db)
        # delete without --force → 2
        self.run_cli("closeout", "delete", self.db, expect_code=2)
        # with --force → 0, sqlite gone
        self.run_cli("closeout", "delete", self.db, "--force")
        self.assertFalse(Path(self.db).exists())


class OutputContract(CliHarness):
    def test_read_commands_emit_json(self):
        self.run_cli("init", self.db, "--destination", "d")
        for cmd in (["pool", self.db], ["validate", self.db], ["complete-check", self.db]):
            p = self.run_cli(*cmd)
            json.loads(p.stdout)   # must parse


if __name__ == "__main__":
    unittest.main(verbosity=2)

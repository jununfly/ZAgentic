#!/usr/bin/env python3
"""§4.2 orchestration via CLI — suggest (read-only) + orchestrate (--execute) subprocess tests."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"


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

    def pair(self):
        """two tickets a~b via blocks → suggests one new_plan."""
        self.run_cli("init", self.db, "--destination", "d")
        self.run_cli("ticket", "add", self.db)
        self.run_cli("ticket", "add", self.db)
        self.run_cli("blocks", "add", self.db, "--from", "ticket:0", "--to", "ticket:1")


class SuggestCmd(Harness):
    def test_suggest_outputs_steps(self):
        self.pair()
        out = json.loads(self.run_cli("suggest", self.db).stdout)
        self.assertEqual([s["action"] for s in out["steps"]], ["new_plan"])
        self.assertEqual(sorted(map(tuple, out["steps"][0]["items"])),
                         [("ticket", 0), ("ticket", 1)])

    def test_suggest_does_not_write(self):
        self.pair()
        before = Path(self.db).read_bytes()
        self.run_cli("suggest", self.db)
        self.assertEqual(Path(self.db).read_bytes(), before)   # sqlite bytes unchanged


class OrchestrateCmd(Harness):
    def test_dry_run_preview_no_write(self):
        self.pair()
        before = Path(self.db).read_bytes()
        out = json.loads(self.run_cli("orchestrate", self.db, "--agent", "alice").stdout)
        self.assertFalse(out["executed"])
        self.assertEqual(out["steps"][0]["action"], "new_plan")
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_execute_creates_plan(self):
        self.pair()
        out = json.loads(self.run_cli("orchestrate", self.db, "--agent", "alice",
                                      "--execute").stdout)
        self.assertTrue(out["executed"])
        tid = out["applied"][0]["task_id"]
        # pool drained, plan claimed by alice
        self.assertEqual(json.loads(self.run_cli("pool", self.db).stdout), [])
        rows = json.loads(self.run_cli("claims", "list", self.db).stdout)
        self.assertTrue(any(r["kind"] == "plan" and r["ref_id"] == tid and r["agent"] == "alice"
                            for r in rows))

    def test_execute_hotplug_lock_free(self):
        """§4.4: orchestrator may hotplug an item into a plan claimed by ANOTHER agent."""
        self.run_cli("init", self.db, "--destination", "d")
        self.run_cli("task", "add", self.db, "--name", "P")          # task 0
        self.run_cli("ticket", "add", self.db, "--task", "0")        # x in plan 0
        self.run_cli("claim", self.db, "plan", "0", "--agent", "bob")
        self.run_cli("ticket", "add", self.db)                        # y in pool
        # link y~x via parent (non-blocking)
        self.run_cli("ticket", "add", self.db, "--parent", "0")       # ticket 2 parent=0 → but that adds ticket2; use assign trick
        # simpler: make ticket 2 (y) child of ticket 0 (x)
        # note: --parent on add links ticket2~ticket0
        out = json.loads(self.run_cli("orchestrate", self.db, "--agent", "alice",
                                      "--execute").stdout)
        # alice hotplugged the unblocked linked item into bob's claimed plan 0
        self.assertTrue(any(a["action"] == "hotplug" and a["task_id"] == 0
                            for a in out["applied"]))


class OrchestrateErrors(Harness):
    def test_empty_pool_exit2(self):
        self.run_cli("init", self.db, "--destination", "d")
        self.run_cli("suggest", self.db, expect_code=2)      # E_POOL_EMPTY
        self.run_cli("orchestrate", self.db, "--agent", "a", "--execute", expect_code=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

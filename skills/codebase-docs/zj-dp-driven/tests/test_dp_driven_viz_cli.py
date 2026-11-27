#!/usr/bin/env python3
"""§6 viz CLI subprocess tests (Phase-3c)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"


class VizCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")

    def run_cli(self, *args, expect_code=0):
        proc = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True)
        self.assertEqual(proc.returncode, expect_code, f"cmd={args}\n{proc.stderr}")
        return proc

    def build(self):
        self.run_cli("init", self.db, "--destination", "d")
        self.run_cli("task", "add", self.db, "--name", "后端")
        self.run_cli("ticket", "add", self.db, "--task", "0")
        self.run_cli("ticket", "add", self.db, "--task", "0")
        self.run_cli("blocks", "add", self.db, "--from", "ticket:0", "--to", "ticket:1")

    def test_viz_stdout(self):
        self.build()
        out = self.run_cli("viz", self.db).stdout
        self.assertTrue(out.startswith("flowchart TD"))
        self.assertIn("tk1_T0", out)

    def test_viz_write_file(self):
        self.build()
        p = str(Path(self.tmp.name) / "view.mmd")
        self.run_cli("viz", self.db, "--out", p)
        self.assertTrue(Path(p).exists())
        self.assertIn("flowchart TD", Path(p).read_text(encoding="utf-8"))

    def test_viz_cli_readonly(self):
        self.build()
        before = Path(self.db).read_bytes()
        self.run_cli("viz", self.db)
        self.run_cli("viz", self.db, "--out", str(Path(self.tmp.name) / "x.mmd"))
        self.assertEqual(Path(self.db).read_bytes(), before)   # no lock, no write

    def test_viz_default_format_mermaid(self):
        self.run_cli("init", self.db, "--destination", "d")
        out = self.run_cli("viz", self.db, "--format", "mermaid").stdout
        self.assertIn("flowchart TD", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

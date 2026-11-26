#!/usr/bin/env python3
"""§5.2 two-stage closeout — invariant locks.

Design:
  完成判定 → 导出 process-summary.md → Human 治理 md → 删 sqlite。
  顺序门 = is_complete + .governed.json marker + 显式 force。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

from dp_driven_model import DpDriven, DpDrivenError, KIND_TICKET, KIND_FINDING, S_DONE, S_ABANDONED


class CloseoutSummary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "dp_driven.sqlite")
        self.md_a = str(self.root / "task_a.md")
        Path(self.md_a).write_text("# ctx a\n")
        self.md_f = str(self.root / "finding_0.md")
        Path(self.md_f).write_text("# finding\n")

    def build(self) -> DpDriven:
        m = DpDriven.init(self.db, destination="上线", now="t0")
        t1 = m.add_task("甲", context_md=self.md_a)
        t2 = m.add_task("乙")
        f0 = m.add_finding(md_path=self.md_f)             # finding first (id=0)
        up = m.add_ticket(task_id=t1, ref="gh#1")
        dn = m.add_ticket(task_id=t2, derived_from_finding=f0)
        m.add_finding_membership(f0, t1)
        m.add_finding_membership(f0, t2)      # 多归属
        m.add_blocks(KIND_TICKET, up, KIND_TICKET, dn)
        m.save()
        return m

    def test_summary_written_to_disk(self):
        m = self.build()
        out = str(self.root / "process-summary.md")
        m.closeout_export_summary(out)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("# Process summary", text)
        self.assertIn("上线", text)
        self.assertIn("甲", text)
        self.assertIn("gh#1", text)                        # §2 ticket ref column
        self.assertIn("Cross-plan blocks", text)           # §3.6 F2 section header
        self.assertIn("Finding multi-membership", text)    # §3.4 section header
        self.assertIn("Ticket materialization", text)      # §7 Q1 section header
        # finding 0 belongs to plans 0,1 (多归属)
        self.assertIn("| 0 | 0,1 | 未完成 |", text)

    def test_summary_is_deterministic_byte_equal(self):
        m = self.build()
        a = str(self.root / "s1.md")
        b = str(self.root / "s2.md")
        m.closeout_export_summary(a)
        m.closeout_export_summary(b)
        self.assertEqual(Path(a).read_bytes(), Path(b).read_bytes())

    def test_closeout_export_does_not_delete_carrier(self):
        # §5.2 步 1: sqlite 仍在。
        m = self.build()
        out = str(self.root / "s.md")
        m.closeout_export_summary(out)
        self.assertTrue(os.path.exists(self.db))


class CloseoutGovernedGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "dp_driven.sqlite")

    def build_and_complete(self) -> DpDriven:
        m = DpDriven.init(self.db, destination="d")
        t = m.add_task("只一个")
        m.set_plan_status(t, S_DONE)
        m.save()
        return m

    def test_refuses_when_not_complete(self):
        m = DpDriven.init(self.db, destination="d")
        m.add_task("甲")   # still open
        with self.assertRaises(DpDrivenError) as cm:
            m.closeout_verify_governed()
        self.assertEqual(cm.exception.code, "E_NOT_COMPLETE")

    def test_refuses_when_marker_missing(self):
        m = self.build_and_complete()
        with self.assertRaises(DpDrivenError) as cm:
            m.closeout_verify_governed()
        self.assertEqual(cm.exception.code, "E_CLOSEOUT_NOT_GOVERNED")

    def test_marker_malformed_rejected(self):
        m = self.build_and_complete()
        marker = self.root / "dp_driven.governed.json"
        marker.write_text("not-json")
        with self.assertRaises(DpDrivenError) as cm:
            m.closeout_verify_governed(str(marker))
        self.assertEqual(cm.exception.code, "E_CLOSEOUT_MARKER_MALFORMED")

    def test_marker_without_governed_at_rejected(self):
        m = self.build_and_complete()
        marker = self.root / "x.governed.json"
        marker.write_text(json.dumps({"corpus": []}))
        with self.assertRaises(DpDrivenError) as cm:
            m.closeout_verify_governed(str(marker))
        self.assertEqual(cm.exception.code, "E_CLOSEOUT_MARKER_MALFORMED")

    def test_valid_marker_passes(self):
        m = self.build_and_complete()
        marker = self.root / "x.governed.json"
        marker.write_text(json.dumps({"governed_at": "t", "corpus": ["a.md"]}))
        payload = m.closeout_verify_governed(str(marker))
        self.assertEqual(payload["governed_at"], "t")


class CloseoutDelete(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "dp_driven.sqlite")
        self.md = str(self.root / "corpus.md")
        Path(self.md).write_text("# durable\n")

    def ready(self) -> DpDriven:
        m = DpDriven.init(self.db, destination="d")
        t = m.add_task("甲", context_md=self.md)
        m.set_plan_status(t, S_DONE)
        m.save()
        marker = self.root / "dp_driven.governed.json"
        marker.write_text(json.dumps({"governed_at": "t1", "corpus": [self.md]}))
        return m

    def test_delete_requires_force(self):
        m = self.ready()
        with self.assertRaises(DpDrivenError) as cm:
            m.closeout_delete_carrier(force=False)
        self.assertEqual(cm.exception.code, "E_CLOSEOUT_CONFIRM_REQUIRED")

    def test_delete_with_force_removes_sqlite_and_sidecars(self):
        m = self.ready()
        # simulate sidecars
        (self.root / "dp_driven.sqlite-wal").write_text("")
        (self.root / "dp_driven.sqlite-shm").write_text("")
        (self.root / "dp_driven.sqlite.lock").write_text("")
        deleted = m.closeout_delete_carrier(force=True)
        self.assertEqual(deleted, self.db)
        self.assertFalse(os.path.exists(self.db))
        self.assertFalse(os.path.exists(self.db + "-wal"))
        self.assertFalse(os.path.exists(self.db + "-shm"))
        self.assertFalse(os.path.exists(self.db + ".lock"))

    def test_md_corpus_survives_delete(self):
        """§5.3 md 是长期语料；sqlite 是过程燃料。删除不得触碰 md。"""
        m = self.ready()
        m.closeout_delete_carrier(force=True)
        self.assertTrue(os.path.exists(self.md))
        self.assertEqual(Path(self.md).read_text(encoding="utf-8"), "# durable\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Regression tests: zj-discuss Phase 4 disposition guard (dispose.py).

Guards sub-02 Q3 findings: a discussion folder must not be retired until every
sub-document is concluded AND the folder is committed to git (no RPO=total-loss
deletion). Deletion is never a raw rm — archive moves via git mv into a recycle
window. The git check is injected so the suite stays hermetic.
"""

import sys
import unittest
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import dispose  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _subdoc(status="DONE", extra=""):
    return (
        "# 子问题：示例\n\n"
        "## Agent viewpoints\n\n"
        "### 视角：B（技术经理）\n`视角来源: 跨会话独立Agent`\n"
        "**观点 1** — x\n- 发现：原文 L10\n- 影响：y\n- 建议：z\n\n"
        "## conclusion（含沉淀指令）\n\n"
        "- **子问题结论：** 定了\n"
        "- **沉淀指令：**\n  - 改哪些文档：`x.py`\n  - 待删临时脚手架：briefings/\n"
        "- **状态协议：** {}\n{}".format(status, extra)
    )


class _GitStub:
    def __init__(self, clean=True):
        self.clean = clean

    def __call__(self, *args):
        class _P:
            returncode = 0
            stdout = "" if self.clean else " M discussions/x/sub-01.md\n"
            stderr = ""
        return _P()


class _MoveStub:
    """Simulates `git mv` (performs the rename) so archive() is testable
    without a real repository."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if args and args[0] == "mv":
            import shutil

            shutil.move(str(Path(args[1])), str(Path(args[2])))
        class _P:
            returncode = 0
            stdout = ""
            stderr = ""
        return _P()


class AllConcluded(unittest.TestCase):
    def test_all_done_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            _write(d / "sub-02.md", _subdoc("DONE_WITH_CONCERNS"))
            ok, probs = dispose.all_concluded(d)
            self.assertTrue(ok, probs)

    def test_blocked_subdoc_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            _write(d / "sub-02.md", _subdoc("BLOCKED"))
            ok, probs = dispose.all_concluded(d)
            self.assertFalse(ok)
            self.assertTrue(any("sub-02" in p for p in probs))

    def test_missing_status_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", "# 无状态协议\n")
            ok, probs = dispose.all_concluded(d)
            self.assertFalse(ok)

    def test_empty_folder_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            d.mkdir()
            ok, probs = dispose.all_concluded(d)
            self.assertFalse(ok)


class SafeToDispose(unittest.TestCase):
    def test_clean_and_concluded_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            ok, reasons = dispose.safe_to_dispose(d, git_fn=_GitStub(clean=True))
            self.assertTrue(ok, reasons)

    def test_dirty_git_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            ok, reasons = dispose.safe_to_dispose(d, git_fn=_GitStub(clean=False))
            self.assertFalse(ok)
            self.assertTrue(any("未提交" in r for r in reasons), reasons)

    def test_missing_receipt_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            ok, reasons = dispose.safe_to_dispose(
                d, receipt=str(Path(td) / "no-receipt.md"), git_fn=_GitStub(clean=True)
            )
            self.assertFalse(ok)
            self.assertTrue(any("回执" in r for r in reasons), reasons)


class Archive(unittest.TestCase):
    def test_archive_moves_folder(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            root = Path(td) / ".discussions-archive"
            ok, msg = dispose.archive(d, archive_root=root, git_fn=_MoveStub())
            self.assertTrue(ok, msg)
            self.assertTrue((root / "disc" / "sub-01.md").exists())
            self.assertFalse(d.exists())

    def test_archive_refuses_existing_dest(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            root = Path(td) / ".discussions-archive"
            root.mkdir()
            (root / "disc").mkdir()
            ok, msg = dispose.archive(d, archive_root=root)
            self.assertFalse(ok)


class Cli(unittest.TestCase):
    def test_dry_run_reports_safe(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("DONE"))
            code = dispose.main(["--dry-run", str(d)], git_fn=_GitStub(clean=True))
            self.assertEqual(code, 0)

    def test_refuses_unconcluded(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "disc"
            _write(d / "sub-01.md", _subdoc("BLOCKED"))
            code = dispose.main(["--dry-run", str(d)])
            self.assertEqual(code, 1)

    def test_missing_folder_refused(self):
        code = dispose.main(["--dry-run", "/nope/does-not-exist"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

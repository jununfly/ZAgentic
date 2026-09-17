#!/usr/bin/env python3
"""P5 真实计划语料常态化回归（spec §4.3）。

把 `verify_real_plan_corpus.py` 包成 unittest 可发现套件：从仓库 `docs/plans`
语料造 legacy fixture → 迁移到 sqlite → validate/stats/有界读/源不变，并断言
S2 新增 trace 后 plan 遍历字节不变（trace 不泄进视图，升级不误报）。
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

import verify_real_plan_corpus  # noqa: E402


def _repo_root(skill_dir: Path) -> Path | None:
    """仓库感知地定位仓库根：用 git 找工作树顶层。

    独立 installed 副本拍平为 skills/zj-roadmap-driven，不在任何 git 仓库内，
    无法定位 → 返回 None，由调用方 skipTest（与 Slice06 历史基线同类处置）。
    相比硬编码「上爬 3 层」，此法在 monorepo 内与 worktree 下都正确。
    """
    try:
        env = dict(os.environ)
        env.pop("NODE_OPTIONS", None)
        out = subprocess.run(
            ["git", "-C", str(skill_dir), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    root = Path(out.stdout.strip())
    return root if root.is_dir() else None


class RealPlanCorpusRegressionTest(unittest.TestCase):
    def test_corpus_contract_and_trace_invariant(self):
        repo_root = _repo_root(SKILL_DIR)
        if repo_root is None:
            self.skipTest(
                "不在 git 仓库内（独立 installed 副本），无法定位 docs/plans 语料"
            )
        plans_dir = repo_root / "docs" / "plans"
        if not plans_dir.is_dir():
            self.skipTest(f"corpus dir missing: {plans_dir}")
        if not any(plans_dir.rglob("*.md")):
            self.skipTest(f"corpus dir empty (no .md): {plans_dir}")
        result = verify_real_plan_corpus.verify(plans_dir)
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(result["markdown_import"], "rejected")
        self.assertTrue(result["trace_add_invariant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

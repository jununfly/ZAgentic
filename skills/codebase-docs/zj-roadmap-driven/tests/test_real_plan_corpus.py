#!/usr/bin/env python3
"""P5 真实计划语料常态化回归（spec §4.3）。

把 `verify_real_plan_corpus.py` 包成 unittest 可发现套件：从仓库 `docs/plans`
语料造 legacy fixture → 迁移 bundle → validate/stats/有界读/源不变，并断言
S2 新增 trace 后 plan 遍历字节不变（trace 不泄进视图，升级不误报）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

import verify_real_plan_corpus  # noqa: E402

REPO_ROOT = verify_real_plan_corpus.SKILL_DIR.parent.parent.parent
PLANS_DIR = REPO_ROOT / "docs" / "plans"


class RealPlanCorpusRegressionTest(unittest.TestCase):
    def test_corpus_contract_and_trace_invariant(self):
        self.assertTrue(PLANS_DIR.is_dir(), f"corpus dir missing: {PLANS_DIR}")
        result = verify_real_plan_corpus.verify(PLANS_DIR)
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(result["markdown_import"], "rejected")
        self.assertTrue(result["trace_add_invariant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""research_eval_cli operation→资产映射的单元测试（不涉及外部编译器）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import research_eval_cli as ev  # noqa: E402


class OperationAssetsTests(unittest.TestCase):
    def test_validate_assets_requires_four_inputs(self):
        count, keys = ev.OPERATION_ASSETS["validate-assets"]
        self.assertEqual(count, 4)
        self.assertEqual(keys, ("manifest", "rubrics", "annotations", "calibration"))

    def test_calibrate_judge_requires_two_inputs(self):
        count, keys = ev.OPERATION_ASSETS["calibrate-judge"]
        self.assertEqual(count, 2)
        self.assertEqual(keys, ("rubrics", "calibration"))

    def test_all_required_operations_are_mapped(self):
        self.assertEqual(set(ev.OPERATION_ASSETS), ev.REQUIRED_OPERATIONS)


if __name__ == "__main__":
    unittest.main()

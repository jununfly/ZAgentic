#!/usr/bin/env python3
"""sealed ledger 形状边界测试（不涉及外部编译器）。

Pin 边界（zj-review-findings Step 4）：合法的 repository 对象（持有 stars /
topicMatch / immutable revision）必须被接受；被标量或字符串估计替换的
repository 必须被拒绝。语义层的「不得被模型估计替换」属 review 职责，不在此机械判定。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from research_cli import ResearchCliError, validate_sealed_ledger  # noqa: E402


def minimal_ledger(**overrides: object) -> dict:
    ledger = {
        "schema": "zj-verified-evidence-ledger/v1",
        "repositories": [
            {"owner": "o", "name": "r", "stars": 10, "topicMatch": 0.9, "immutableRevision": "abc"},
        ],
        "candidates": [],
        "evidence": [],
        "unknownCriteria": [],
        "navigation": [],
        "collection": {},
        "briefFingerprint": "0" * 64,
    }
    ledger.update(overrides)
    return ledger


class SealedLedgerShapeTests(unittest.TestCase):
    def test_valid_ledger_with_owned_repository_objects_passes(self):
        validate_sealed_ledger(minimal_ledger())  # must not raise

    def test_repository_replaced_by_scalar_estimate_is_rejected(self):
        with self.assertRaises(ResearchCliError):
            validate_sealed_ledger(minimal_ledger(repositories=[42]))

    def test_repository_entry_must_be_object_not_string(self):
        with self.assertRaises(ResearchCliError):
            validate_sealed_ledger(minimal_ledger(repositories=["repo-stars-estimate"]))


if __name__ == "__main__":
    unittest.main()

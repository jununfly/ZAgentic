#!/usr/bin/env python3
"""Generic tests for zj-doc-collab gate_core (defaults = zj-discuss vocabulary)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from gate_core import (
    split_sections,
    check_viewpoint_marker,
    check_non_degradation,
    split_viewpoint_blocks,
    count_evidence,
    placeholder_markers_in,
    CROSS_SESSION_MARKER,
    PREVIEW_MARKER,
    ALLOWED_MARKERS,
    CLAIMED_STATUS,
)


class CheckViewpointMarkerTest(unittest.TestCase):
    def test_missing_marker(self):
        v = check_viewpoint_marker("some body without source", role="B")
        self.assertEqual(v, ["视角 B 未标注 `视角来源`"])

    def test_invalid_marker(self):
        v = check_viewpoint_marker("视角来源: 外星视角", role="B")
        self.assertTrue(any("取值非法" in s for s in v))

    def test_cross_session_ok(self):
        body = "视角来源: 跨会话独立Agent"
        self.assertEqual(check_viewpoint_marker(body, role="B"), [])

    def test_preview_missing_label(self):
        body = "视角来源: 同会话SubAgent(低权重)"
        v = check_viewpoint_marker(body, role="X")
        self.assertTrue(any("⚠ 非独立" in s for s in v))

    def test_preview_with_label_ok(self):
        body = "视角来源: 同会话SubAgent(低权重)\n⚠ 非独立"
        self.assertEqual(check_viewpoint_marker(body, role="X"), [])


class CheckNonDegradationTest(unittest.TestCase):
    def test_anchor_present_clean(self):
        self.assertEqual(
            check_non_degradation("## conclusion\n状态协议: DONE", has_cross_session_anchor=True),
            [],
        )

    def test_no_anchor_claimed_status_violation(self):
        v = check_non_degradation(
            "## conclusion\n状态协议: DONE", has_cross_session_anchor=False
        )
        self.assertTrue(any("非降级红线" in s for s in v))

    def test_no_anchor_blocked_exempt(self):
        # BLOCKED makes no resolution claim -> exempt from non-degradation.
        self.assertEqual(
            check_non_degradation(
                "## conclusion\n状态协议: BLOCKED", has_cross_session_anchor=False
            ),
            [],
        )

    def test_custom_claimed_status(self):
        v = check_non_degradation(
            "## conclusion\n状态协议: RESOLVED",
            has_cross_session_anchor=False,
            claimed_statuses={"RESOLVED"},
        )
        self.assertTrue(v)


class SplitViewpointBlocksTest(unittest.TestCase):
    def test_drops_preamble(self):
        body = "视角来源: 跨会话独立Agent\npreamble prose\n#### 观点 1\nevidence\n#### 观点 2\nmore\n"
        blocks = split_viewpoint_blocks(body)
        self.assertEqual(len(blocks), 2)
        self.assertIn("观点 1", blocks[0])
        self.assertIn("观点 2", blocks[1])

    def test_no_delimiter_single_block(self):
        body = "视角来源: 跨会话独立Agent\nonly prose, no viewpoint delimiter\n"
        blocks = split_viewpoint_blocks(body)
        self.assertEqual(len(blocks), 1)


class CountEvidenceTest(unittest.TestCase):
    def test_classifies_all_four_shapes(self):
        blocks = [
            "#### 观点 1\n原文 L10 here",                       # evidence
            "#### 观点 2\n<主题> 未填占位",                       # placeholder
            "#### 观点 3\n原文 ADR 0008 缺行号",                  # missing anchor
            "#### 观点 4\n只是泛泛而谈",                          # missing citation
        ]
        evidence, placeholder_at, missing_anchor_at, missing_citation_at = count_evidence(blocks)
        self.assertEqual(evidence, 1)
        self.assertEqual(placeholder_at, [2])
        self.assertEqual(missing_anchor_at, [3])
        self.assertEqual(missing_citation_at, [4])

    def test_placeholder_markers_in(self):
        self.assertEqual(placeholder_markers_in("<主题> 东西"), ["<主题>"])
        self.assertEqual(placeholder_markers_in("正常 <tag> 行内"), [])


class SplitSectionsImportTest(unittest.TestCase):
    def test_reexported(self):
        self.assertTrue(callable(split_sections))


if __name__ == "__main__":
    unittest.main()

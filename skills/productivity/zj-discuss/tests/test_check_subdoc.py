"""Regression tests: the structural gate for zj-discuss sub-documents.

Guard for discussion item 3 / item 4 (status-protocol fields, the preview
``非独立`` label, and the "conclusion must never cite preview output as
authority" gate). Previously these existed only as prose in the SKILL and in
``design.md``; these tests make them mechanically enforceable.

Seam: ``check_subdoc.check(text) -> list[str]`` plus the CLI exit code, so both
the library logic and the Human-facing command are covered.
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_subdoc  # noqa: E402


def doc(viewpoints: str = "", conclusion: str = "") -> str:
    return (
        "# 子问题：示例\n\n"
        "## Agent viewpoints（独立视角 — 须跨会话独立 Agent）\n\n"
        + viewpoints
        + "\n## conclusion（含沉淀指令）\n\n"
        + conclusion
    )


GOOD_VIEWPOINT = (
    "### 视角：B（技术经理 / 可落地）\n"
    "`视角来源: 跨会话独立Agent`\n"
    "<独立撰写>\n\n"
)

GOOD_CONCLUSION = (
    "> 结论必须给出可执行沉淀指令。\n\n"
    "- **子问题结论：** 定了\n"
    "- **状态协议：** DONE（已回填 MASTER.md 索引）\n"
)


class WellFormedPasses(unittest.TestCase):
    def test_clean_document_has_no_violations(self):
        self.assertEqual(check_subdoc.check(doc(GOOD_VIEWPOINT, GOOD_CONCLUSION)), [])

    def test_all_status_enums_accepted(self):
        for status in check_subdoc.VALID_STATUS:
            body = doc(GOOD_VIEWPOINT, "- **状态协议：** {}\n".format(status))
            self.assertEqual(check_subdoc.check(body), [], "status {} rejected".format(status))

    def test_preview_viewpoint_labelled_is_accepted(self):
        # A properly-labelled preview is legal *alongside* a real cross-session
        # anchor. Preview-only is illegal, and is asserted separately in
        # IndependenceNonDegradation.
        self.assertEqual(
            check_subdoc.check(doc(CROSS_SESSION_ANCHOR + PREVIEW_VIEWPOINT, GOOD_CONCLUSION)),
            [],
        )


class SourceMarkerEnforcement(unittest.TestCase):
    def test_viewpoint_without_source_marker_fails(self):
        vp = "### 视角：B（技术经理）\n<没标注来源>\n\n"
        violations = check_subdoc.check(doc(vp, GOOD_CONCLUSION))
        self.assertTrue(any("来源" in v for v in violations), violations)

    def test_unknown_source_marker_fails(self):
        vp = "### 视角：B（技术经理）\n`视角来源: 火星来源`\n<内容>\n\n"
        violations = check_subdoc.check(doc(vp, GOOD_CONCLUSION))
        self.assertTrue(violations, "invalid marker accepted")

    def test_preview_without_label_fails(self):
        vp = (
            "### 视角：X（自定义 / 预演）\n"
            "`视角来源: 同会话SubAgent(低权重)`\n"
            "<缺少 ⚠ 标记>\n\n"
        )
        violations = check_subdoc.check(doc(vp, GOOD_CONCLUSION))
        self.assertTrue(any("非独立" in v or "预演" in v for v in violations), violations)


class ConclusionProtocolEnforcement(unittest.TestCase):
    def test_missing_status_protocol_fails(self):
        conclusion = "- **子问题结论：** 定了\n"
        violations = check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion))
        self.assertTrue(any("状态协议" in v for v in violations), violations)

    def test_invalid_status_value_fails(self):
        conclusion = "- **状态协议：** ✅ 已结论\n"
        violations = check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion))
        self.assertTrue(violations, "non-enum status accepted")

    def test_conclusion_discussing_the_rule_is_not_a_citation(self):
        """A conclusion may legitimately *talk about* the preview rule.

        Discovered against the real ``sub-02-rigor.md``: an earlier bare-token
        detector flagged "conclusion 无预演字段" as citing preview output. A gate
        that cries wolf gets switched off, so this case must stay clean.
        """
        conclusion = (
            "- **解法：** `subdoc-template.md` 增状态协议字段 + 预演标签 +"
            " conclusion 无预演字段；扫描拒绝预演引用。\n"
            "- **状态协议：** DONE\n"
        )
        self.assertEqual(
            check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion)),
            [],
            "normative mention of 预演 must not be flagged as a citation",
        )

    def test_conclusion_citing_preview_as_authority_fails(self):
        conclusion = (
            "- **子问题结论：** 依据同会话SubAgent 预演 的结论，采纳 B\n"
            "- **状态协议：** DONE\n"
        )
        violations = check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion))
        self.assertTrue(any("预演" in v or "权威" in v or "结论" in v for v in violations), violations)


CROSS_SESSION_ANCHOR = "### 视角：B（技术经理 / 可落地）\n`视角来源: 跨会话独立Agent`\n<独立撰写>\n\n"

PREVIEW_VIEWPOINT = (
    "### 视角：X（自定义 / 预演）\n"
    "`视角来源: 同会话SubAgent(低权重)`\n"
    "⚠ 非独立\n"
    "<内容>\n\n"
)


class IndependenceNonDegradation(unittest.TestCase):
    """The operational form of "never degrade to same-session".

    The independence ladder is cross-provider > cross-session > same-session.
    Same-session is a floor you must not settle at, so a conclusion *claiming*
    resolution (DONE / DONE_WITH_CONCERNS) must be anchored by at least one
    genuinely cross-session viewpoint. A document that honestly reports BLOCKED
    is not claiming resolution, so it is exempt.
    """

    def test_conclusion_supported_only_by_previews_is_rejected(self):
        violations = check_subdoc.check(doc(PREVIEW_VIEWPOINT, GOOD_CONCLUSION))
        self.assertTrue(
            any("非降级" in v for v in violations),
            "preview-only conclusion was accepted (silent degradation): {}".format(violations),
        )

    def test_conclusion_with_no_viewpoints_is_rejected(self):
        violations = check_subdoc.check(doc("", GOOD_CONCLUSION))
        self.assertTrue(
            any("非降级" in v for v in violations),
            "conclusion with zero viewpoints was accepted: {}".format(violations),
        )

    def test_cross_session_anchor_makes_it_clean(self):
        both = CROSS_SESSION_ANCHOR + PREVIEW_VIEWPOINT
        self.assertEqual(check_subdoc.check(doc(both, GOOD_CONCLUSION)), [])

    def test_blocked_is_exempt(self):
        for status in ("BLOCKED", "NEEDS_CONTEXT"):
            conclusion = "- **状态协议：** {}\n".format(status)
            violations = check_subdoc.check(doc(PREVIEW_VIEWPOINT, conclusion))
            self.assertFalse(
                any("非降级" in v for v in violations),
                "{} should be exempt: it makes no resolution claim".format(status),
            )


class CommandLineSeam(unittest.TestCase):
    def _write(self, text: str) -> Path:
        import tempfile

        d = Path(tempfile.mkdtemp())
        p = d / "sub-01.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_clean_document_exits_zero(self):
        p = self._write(doc(GOOD_VIEWPOINT, GOOD_CONCLUSION))
        self.assertEqual(check_subdoc.main([str(p)]), 0)

    def test_violating_document_exits_nonzero(self):
        p = self._write(doc("### 视角：B（技术经理）\n<no marker>\n\n", GOOD_CONCLUSION))
        self.assertNotEqual(check_subdoc.main([str(p)]), 0)

    def test_missing_file_exits_nonzero(self):
        self.assertNotEqual(check_subdoc.main(["/nope/does-not-exist.md"]), 0)


if __name__ == "__main__":
    unittest.main()

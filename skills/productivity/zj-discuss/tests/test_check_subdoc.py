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
    "**观点 1** — 排期\n"
    "- 发现：原文 L10 要求排期可行\n"
    "- 影响：否则延期\n"
    "- 建议：显式关键路径\n\n"
    "**观点 2** — 风险\n"
    "- 发现：原文 L20 列出主风险\n"
    "- 影响：无回退\n"
    "- 建议：补回退方案\n\n"
    "**观点 3** — 验收\n"
    "- 发现：原文 L30 验收口径缺失\n"
    "- 影响：做到算完模糊\n"
    "- 建议：量化验收\n\n"
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


CROSS_SESSION_ANCHOR = (
    "### 视角：B（技术经理 / 可落地）\n"
    "`视角来源: 跨会话独立Agent`\n"
    "**观点 1** — 排期\n"
    "- 发现：原文 L10 要求排期可行\n"
    "- 影响：否则延期\n"
    "- 建议：显式关键路径\n\n"
    "**观点 2** — 风险\n"
    "- 发现：原文 L20 列出主风险\n"
    "- 影响：无回退\n"
    "- 建议：补回退方案\n\n"
    "**观点 3** — 验收\n"
    "- 发现：原文 L30 验收口径缺失\n"
    "- 影响：做到算完模糊\n"
    "- 建议：量化验收\n\n"
)

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


def viewpoint_with_blocks(role="B", n=3, evidence=True, marker="跨会话独立Agent"):
    """Build a cross-session viewpoint body with ``n`` viewpoint blocks.

    When ``evidence`` is False the blocks carry no ``原文`` locator, so they
    should fail the gated-method evidence requirement.
    """
    lines = [
        "### 视角：{}（技术经理 / 可落地）".format(role),
        "`视角来源: {}`".format(marker),
        "",
    ]
    for i in range(1, n + 1):
        ev = "原文 L{}".format(10 * i) if evidence else "无证据占位"
        lines.append("**观点 {}** — 主题{}".format(i, i))
        lines.append("- 发现：{} 某事实".format(ev))
        lines.append("- 影响：某影响")
        lines.append("- 建议：某建议")
        lines.append("")
    return "\n".join(lines)


class ViewpointGateNCheck(unittest.TestCase):
    """The mechanical form of gated-method ④ (roadmap node 1-2).

    Turns "≥N viewpoint blocks, each citing original evidence" from a prompt
    request into a hard, machine-verifiable constraint — the D lever against
    the self-reference bias risk (design.md §10.6 R1).
    """

    def test_three_evidence_blocks_pass(self):
        self.assertEqual(
            check_subdoc.check(doc(viewpoint_with_blocks(n=3), GOOD_CONCLUSION)), []
        )

    def test_four_blocks_pass(self):
        self.assertEqual(
            check_subdoc.check(doc(viewpoint_with_blocks(n=4), GOOD_CONCLUSION)), []
        )

    def test_two_blocks_below_n3_fails(self):
        violations = check_subdoc.check(doc(viewpoint_with_blocks(n=2), GOOD_CONCLUSION))
        self.assertTrue(
            any("闸门" in v or "低于" in v for v in violations), violations
        )

    def test_blocks_without_evidence_fail(self):
        violations = check_subdoc.check(
            doc(viewpoint_with_blocks(n=3, evidence=False), GOOD_CONCLUSION)
        )
        self.assertTrue(
            any("原文证据" in v or "低于闸门" in v for v in violations), violations
        )

    def test_preview_viewpoint_exempt_from_gate(self):
        # A same-session preview viewpoint is exempt from the N-gate itself
        # (it carries no viewpoint blocks and is not counted as coverage). The
        # non-degradation rule is a conclusion-level check and is covered
        # separately by IndependenceNonDegradation — it is NOT asserted here.
        body = (
            "`视角来源: 同会话SubAgent(低权重)`\n"
            "⚠ 非独立\n<内容>\n\n"
        )
        self.assertEqual(
            check_subdoc._check_viewpoint("### 视角：X（自定义 / 预演）", body), []
        )

    def test_stub_viewpoint_without_blocks_fails(self):
        # The legacy "<独立撰写>" stub carries no viewpoint blocks → must fail.
        stub = "### 视角：B（技术经理 / 可落地）\n`视角来源: 跨会话独立Agent`\n<独立撰写>\n\n"
        violations = check_subdoc.check(doc(stub, GOOD_CONCLUSION))
        self.assertTrue(any("闸门" in v for v in violations), violations)

    def test_gate_n_for_role_reads_ssot(self):
        # N is the single source of truth in role-methods/*.md (design.md §10.6 R1).
        self.assertEqual(check_subdoc.gate_n_for_role("B（技术经理）"), 3)
        self.assertEqual(check_subdoc.gate_n_for_role("A（架构师）"), 3)
        # C solo baseline is N=2 (first "N = " in C.md).
        self.assertEqual(check_subdoc.gate_n_for_role("C（产品专家）"), 2)
        # Unknown / custom key falls back to the default.
        self.assertEqual(check_subdoc.gate_n_for_role("Z（不存在）"), 3)


class DepositionGate(unittest.TestCase):
    """Hard rule 5 closure guard (sub-02 Q3 finding): a conclusion carrying a
    `沉淀指令` block must list at least one substantive item."""

    def test_deposition_with_items_passes(self):
        conclusion = (
            "- **子问题结论：** 定了\n"
            "- **沉淀指令：**\n"
            "  - 改哪些文档：`scripts/check_subdoc.py`\n"
            "  - 待删临时脚手架：briefings/\n"
            "- **状态协议：** DONE\n"
        )
        self.assertEqual(check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion)), [])

    def test_empty_deposition_block_fails(self):
        conclusion = (
            "- **子问题结论：** 定了\n"
            "- **沉淀指令：**\n"
            "- **状态协议：** DONE\n"
        )
        violations = check_subdoc.check(doc(GOOD_VIEWPOINT, conclusion))
        self.assertTrue(
            any("沉淀指令" in v or "闭环" in v for v in violations), violations
        )

    def test_missing_deposition_block_not_gated(self):
        # Legacy docs without the block are not flagged (backward compatible).
        self.assertEqual(check_subdoc.check(doc(GOOD_VIEWPOINT, GOOD_CONCLUSION)), [])


if __name__ == "__main__":
    unittest.main()

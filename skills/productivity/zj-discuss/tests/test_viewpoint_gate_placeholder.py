"""#165 + #166 — 观点闸门：模板占位块不得充当证据，且失败要报出**原因**。

两条议题是同一个洞的两面，合成一个切片守：

- **#166**：`references/subdoc-template.md` 为每个视角生成恰好 N 个占位观点块，
  每个占位块的「发现」里都带一个假定位（`原文 L20`）。闸门只数"含 `原文` 的
  块数"，于是**一字未填的模板骨架能通过闸门**——模板绕过了模板自己的闸门。
- **#165**：闸门的 `EVIDENCE_RE` 要求 `原文` 后跟定位锚点，但生成器写进子文档
  的示例一半不合格（`原文 ADR 0008` 判 FAIL）。失败文案却只报"有效观点仅 0 条，
  低于 N"，把**格式问题误诊为数量问题**，把修复方向带偏。

守的不变量：

1. **占位块恒计 0 条**：含模板占位标记（`<...>` / `<主题>` …）的观点块不算证据，
   不管它里面塞了几个 `原文 Lxx`；
2. **模板骨架必然失败**：从 `subdoc-template.md` 抽段构造的 fixture 必须返违规
   （模板改了而闸门没跟上时，这条会红）；
3. **逐块报因**：失败文案点名是"占位"还是"缺定位锚点"，后者还要给出合规写法，
   而不是笼统报"观点数不足"；
4. **合规写法不误伤**：`原文 L96` / `原文 ADR 0008 L28` / `原文 X.md ## 章节`
   三种仍 PASS。

seam：`check_subdoc.check(text)`（库缝）+ CLI 退出码（Human 缝）。

运行：python tests/test_viewpoint_gate_placeholder.py
"""

import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_subdoc  # noqa: E402

TEMPLATE = SKILL_DIR / "references" / "subdoc-template.md"
CLI = SCRIPTS_DIR / "check_subdoc.py"

GOOD_CONCLUSION = (
    "- **子问题结论：** 定了\n"
    "- **沉淀指令：**\n"
    "  - 改哪些 PRD / ADR / 文档：改 docs/prds/x.md 第 1 节\n"
    "- **状态协议：** DONE（已回填 MASTER.md 索引）\n"
)


def doc(viewpoints: str, conclusion: str = GOOD_CONCLUSION) -> str:
    return (
        "# 子问题：示例\n\n"
        "## Agent viewpoints（独立视角 — 须跨会话独立 Agent）\n\n"
        + viewpoints
        + "\n## conclusion（含沉淀指令）\n\n"
        + conclusion
    )


def template_viewpoints() -> str:
    """从 `subdoc-template.md` 抽出三视角段——模板骨架，一字未填。

    从模板**抽**而不是硬编码：模板改了（比如占位块数变化）时这条 fixture 跟着
    变，"模板改了闸门没跟上"才可能被这条测试抓到。
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("### 视角：B")
    end = text.index("## 主力AI 整合立场")
    return text[start:end].rstrip()


def viewpoint(role_key, blocks) -> str:
    return (
        "### 视角：{}\n"
        "`视角来源: 跨会话独立Agent`\n\n".format(role_key) + blocks
    )


def placeholder_block(index, locator="原文 L10") -> str:
    return (
        "**观点 {i}** — <主题>\n"
        "- 发现：<... `{loc}`>\n"
        "- 影响：<...>\n"
        "- 建议：<...>\n\n"
    ).format(i=index, loc=locator)


def filled_block(index, citation) -> str:
    return (
        "**观点 {i}** — 主题\n"
        "- 发现：{c} 说明了事实\n"
        "- 影响：有影响\n"
        "- 建议：有建议\n\n"
    ).format(i=index, c=citation)


class TemplateSkeletonMustFail(unittest.TestCase):
    """#166：一份照模板生成的零内容 stub 绝不能通过闸门。"""

    def test_template_skeleton_is_rejected(self):
        violations = check_subdoc.check(doc(template_viewpoints()))

        self.assertTrue(violations, "模板骨架通过了闸门——模板绕过了模板自己的闸门")

    def test_template_skeleton_failure_names_placeholders(self):
        """报"占位"而不是笼统报"观点数不足"——否则 Agent 会去多写观点。"""
        joined = "\n".join(check_subdoc.check(doc(template_viewpoints())))

        self.assertIn("占位", joined)

    def test_cli_exits_1_on_template_skeleton(self):
        # 不用 tempfile：本机 Security Center 会拦临时目录的删除，gettempdir()
        # 会因此判定"没有可用临时目录"（环境噪音，与被测逻辑无关）。
        scratch = Path("/tmp") / "zj-gate-{}".format(uuid.uuid4().hex)
        scratch.mkdir()
        try:
            path = scratch / "stub.md"
            path.write_text(doc(template_viewpoints()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CLI), str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("占位", result.stderr)


class PlaceholderBlocksNeverCountAsEvidence(unittest.TestCase):
    """#166 核心：占位块数量恰好等于 N 时也不能过——旧行为恰好踩在这个阈值上。"""

    def _b_blocks(self, blocks) -> str:
        return viewpoint("B（技术经理 / 可落地）", blocks)

    def test_placeholder_count_equal_to_n_still_fails(self):
        blocks = "".join(placeholder_block(i, "原文 L{}".format(10 * i)) for i in (1, 2, 3))

        violations = check_subdoc.check(doc(self._b_blocks(blocks)))

        self.assertTrue(violations, "3 个占位块（= N）通过了闸门")

    def test_placeholder_and_filled_mix_counts_only_filled(self):
        """2 真 + 1 占位 = 2 < N=3 → 仍失败；占位块那块被报出来。"""
        blocks = (
            filled_block(1, "原文 L10")
            + filled_block(2, "原文 L20")
            + placeholder_block(3)
        )

        violations = check_subdoc.check(doc(self._b_blocks(blocks)))
        joined = "\n".join(violations)

        self.assertTrue(violations)
        self.assertIn("占位", joined)

    def test_three_filled_blocks_pass(self):
        blocks = "".join(filled_block(i, "原文 L{}".format(10 * i)) for i in (1, 2, 3))

        self.assertEqual(check_subdoc.check(doc(self._b_blocks(blocks))), [])


class FailureNamesTheReason(unittest.TestCase):
    """#165：把"格式不达标"报成"观点写少了"会把修复方向带偏。"""

    def _b_blocks(self, blocks) -> str:
        return viewpoint("B（技术经理 / 可落地）", blocks)

    def test_file_only_citation_is_rejected(self):
        blocks = "".join(filled_block(i, "原文 ADR 0008") for i in (1, 2, 3))

        self.assertTrue(check_subdoc.check(doc(self._b_blocks(blocks))))

    def test_file_only_citation_failure_names_the_missing_anchor(self):
        blocks = "".join(filled_block(i, "原文 ADR 0008") for i in (1, 2, 3))
        joined = "\n".join(check_subdoc.check(doc(self._b_blocks(blocks))))

        self.assertIn("定位锚点", joined)

    def test_failure_shows_a_compliant_rewrite(self):
        blocks = "".join(filled_block(i, "原文 ADR 0008") for i in (1, 2, 3))
        joined = "\n".join(check_subdoc.check(doc(self._b_blocks(blocks))))

        # 文案要给出"补个行号就好"的具体写法，而不是让人再去多写观点。
        self.assertIn("原文 ADR 0008 L28", joined)

    def test_failure_reports_block_positions(self):
        """逐块报因：第几块出的问题要说清楚，便于定位。"""
        blocks = "".join(filled_block(i, "原文 ADR 0008") for i in (1, 2, 3))
        joined = "\n".join(check_subdoc.check(doc(self._b_blocks(blocks))))

        self.assertIn("第 1、2、3 块", joined)

    def test_missing_citation_is_reported_as_such(self):
        blocks = "".join(
            "**观点 {i}** — 主题\n- 发现：凭印象\n- 影响：有影响\n- 建议：有建议\n\n".format(i=i)
            for i in (1, 2, 3)
        )
        joined = "\n".join(check_subdoc.check(doc(self._b_blocks(blocks))))

        self.assertIn("原文", joined)


class CompliantCitationsStillPass(unittest.TestCase):
    """修闸门不能把合规引用一起打掉——那会逼使用者关闸门（狼来了）。"""

    def _b_doc(self, citation) -> str:
        blocks = "".join(filled_block(i, citation) for i in (1, 2, 3))
        return doc(viewpoint("B（技术经理 / 可落地）", blocks))

    def test_bare_line_number_passes(self):
        self.assertEqual(check_subdoc.check(self._b_doc("原文 L96")), [])

    def test_file_with_line_passes(self):
        self.assertEqual(check_subdoc.check(self._b_doc("原文 ADR 0008 L28")), [])

    def test_file_with_section_passes(self):
        self.assertEqual(
            check_subdoc.check(self._b_doc("原文 ZJ-CONTEXT.md ## 路线外 Provider 验证")), []
        )


if __name__ == "__main__":
    unittest.main()

"""Regression tests: R4 recomputable metrics registry for zj-discuss.

Behavior-driven (RED first). Each test assembles a temp discussions/ folder from
literal fixtures and asserts computed metrics equal *independently hand-derived*
values. Expected values come from the authored string literals themselves (the
ground-truth file content), NOT from re-running the algorithm — so a parser that
grabs the wrong span (includes 主力AI text, misses a block, double-counts, or
reads a hardcoded constant) diverges from the assertion.

Seam: ``metrics.compute_subdoc_metrics(path)`` / ``metrics.compute_discussion_metrics(dir)``
plus the CLI JSON output, so both the library logic and the Human-facing command
are covered.

Spec: docs/designs/zj-discuss/design.md §9 (single schema, discussion- and
sub-doc-level isomorphic). Closure convention: sub-doc-level closure
(open_questions_total=1, closed=1 iff conclusion status ∈ {DONE, DONE_WITH_CONCERNS});
discussion-level totals aggregate sub-docs.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import metrics  # noqa: E402

CROSS = "跨会话独立Agent"
PREVIEW = "同会话SubAgent(低权重)"


def _vp_block(role, prose, preview):
    """One `### 视角：X` block exactly as it lands on disk.

    Returns (heading, body); on-disk block = heading + "\\n" + body + "\\n".
    """
    heading = "### 视角：{}（{}）".format(role, role)
    if preview:
        body = "视角来源: {}\n⚠ 非独立\n{}".format(PREVIEW, prose)
    else:
        body = "视角来源: {}\n{}".format(CROSS, prose)
    return heading, body


def build_subdoc(declared_roles, vp_specs, conclusion_status, conclusion_prose):
    """Assemble a minimal-but-realistic sub-doc.

    vp_specs: list of (role, prose, preview_bool).
    Returns (text, exp_raw, exp_solution_chars, exp_viewpoint_count, exp_closed).
    """
    expected_raw = 0
    expected_viewpoint_count = 0
    parts = []
    parts.append("# 子问题：示例\n\n")
    parts.append("## 上下文\n\n")
    parts.append("- **声明必需角色集：** " + ",".join(declared_roles) + "\n\n")
    parts.append("## Agent viewpoints（独立视角 — 须跨会话独立 Agent）\n\n")
    for role, prose, preview in vp_specs:
        heading, body = _vp_block(role, prose, preview)
        block = heading + "\n" + body + "\n"
        parts.append(block)
        parts.append("\n")
        expected_raw += len(block)
        if not preview:
            expected_viewpoint_count += 1
    parts.append("## 主力AI 整合立场（主会话，非独立视角，低权重）\n\n")
    parts.append("`视角来源: " + PREVIEW + "`\n<主会话整合立场，不计入独立视角>\n\n")
    parts.append("## conclusion（含沉淀指令）\n\n")
    status_line = "- **状态协议：** " + conclusion_status
    parts.append(status_line + "\n" + conclusion_prose + "\n")
    text = "".join(parts)
    expected_solution_chars = len(status_line) + 1 + len(conclusion_prose)
    expected_closed = 1 if conclusion_status in ("DONE", "DONE_WITH_CONCERNS") else 0
    return text, expected_raw, expected_solution_chars, expected_viewpoint_count, expected_closed


def write_discussion(tmp, subdocs, master_solution):
    d = Path(tmp) / "disc-r4"
    d.mkdir()
    for name, text in subdocs.items():
        (d / name).write_text(text, encoding="utf-8")
    master = (
        "# MASTER\n\n## 核心问题\n- ...\n\n"
        "## 解决思路（整合叙事）\n" + master_solution + "\n"
        "## 文档索引\n| 子文档 | 状态 |\n| --- | --- |\n"
    )
    (d / "MASTER.md").write_text(master, encoding="utf-8")
    return d


class SubDocMetrics(unittest.TestCase):
    def test_basic_fields(self):
        text, exp_raw, exp_sol, exp_vp, exp_closed = build_subdoc(
            ["B", "C", "A"],
            [("B", "B 落地性与排期风险，须给出可验证交付。", False),
             ("C", "C 用户价值与生态位，优先级判据。", False),
             ("A", "A 长期约束与边界，以后会不会炸。", False)],
            "DONE",
            "结论：采用方案 X，回填 MASTER 索引。",
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sub-01-a.md"
            p.write_text(text, encoding="utf-8")
            m = metrics.compute_subdoc_metrics(p)
        self.assertEqual(m["sub_doc_id"], "sub-01-a")
        self.assertEqual(m["roles_used"], ["B", "C", "A"], m["roles_used"])
        self.assertEqual(m["viewpoint_count"], exp_vp)
        self.assertEqual(exp_vp, 3)
        self.assertEqual(m["raw_volume_chars"], exp_raw)
        self.assertEqual(m["solution_volume_chars"], exp_sol)
        self.assertEqual(m["compression_ratio"], exp_raw / exp_sol)
        self.assertEqual(m["open_questions_total"], 1)
        self.assertEqual(m["open_questions_closed"], exp_closed)
        self.assertEqual(exp_closed, 1)
        self.assertEqual(m["closure_rate"], 1.0)
        self.assertIs(m["recomputable"], True)

    def test_preview_excluded_from_count_but_kept_in_raw(self):
        text, exp_raw, exp_sol, exp_vp, exp_closed = build_subdoc(
            ["B", "T"],
            [("B", "B 可落地。", False),
             ("T", "T 验证策略，如何证明对。", True)],
            "BLOCKED",
            "信息不足，暂缓。",
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sub-02-b.md"
            p.write_text(text, encoding="utf-8")
            m = metrics.compute_subdoc_metrics(p)
        # preview viewpoint must NOT count, but its chars stay in raw
        self.assertEqual(m["viewpoint_count"], 1, m["viewpoint_count"])
        self.assertEqual(m["raw_volume_chars"], exp_raw)
        self.assertEqual(m["open_questions_closed"], 0)  # BLOCKED -> not claimed
        self.assertEqual(m["closure_rate"], 0.0)
        # roles_used still lists both (declared set), regardless of preview
        self.assertEqual(m["roles_used"], ["B", "T"])

    def test_never_counts_lead_integrator_or_briefing_as_viewpoint(self):
        # 主力AI section + 视角 briefing section must not inflate raw/count
        text, exp_raw, _, exp_vp, _ = build_subdoc(
            ["B"], [("B", "B 独立视角。", False)], "DONE", "结论。")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sub-03.md"
            p.write_text(text, encoding="utf-8")
            m = metrics.compute_subdoc_metrics(p)
        self.assertEqual(m["viewpoint_count"], exp_vp)
        self.assertEqual(exp_vp, 1)
        self.assertEqual(m["raw_volume_chars"], exp_raw)


class DiscussionMetrics(unittest.TestCase):
    def test_aggregates_subdocs_and_master(self):
        t1, r1, s1, v1, c1 = build_subdoc(
            ["B", "C", "A"],
            [("B", "B1", False), ("C", "C1", False), ("A", "A1", False)],
            "DONE", "s1")
        t2, r2, s2, v2, c2 = build_subdoc(
            ["B", "T"],
            [("B", "B2", False), ("T", "T2", False)],
            "BLOCKED", "s2")
        master_solution = "整合叙事：子问题一采用 X，子问题二暂缓。"
        with tempfile.TemporaryDirectory() as tmp:
            d = write_discussion(tmp, {"sub-01-a.md": t1, "sub-02-b.md": t2}, master_solution)
            m = metrics.compute_discussion_metrics(d)
        self.assertEqual(m["discussion_slug"], "disc-r4")
        self.assertEqual(m["roles_used"], ["A", "B", "C", "T"], m["roles_used"])
        self.assertEqual(m["viewpoint_count"], v1 + v2)
        self.assertEqual(v1 + v2, 5)
        self.assertEqual(m["raw_volume_chars"], r1 + r2)
        self.assertEqual(m["solution_volume_chars"], len(master_solution))
        self.assertEqual(m["compression_ratio"], (r1 + r2) / len(master_solution))
        self.assertEqual(m["open_questions_total"], 2)
        self.assertEqual(m["open_questions_closed"], c1 + c2)
        self.assertEqual(c1 + c2, 1)
        self.assertEqual(m["closure_rate"], 0.5)
        self.assertIs(m["recomputable"], True)


class GracefulHandling(unittest.TestCase):
    def test_no_master_dir_is_graceful(self):
        t1, r1, s1, v1, c1 = build_subdoc(
            ["B"], [("B", "B1", False)], "DONE", "s1")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "disc-r4"
            d.mkdir()
            (d / "sub-01-a.md").write_text(t1, encoding="utf-8")
            m = metrics.compute_discussion_metrics(d)
        self.assertEqual(m["solution_volume_chars"], 0)
        self.assertIsNone(m["compression_ratio"])
        self.assertEqual(m["open_questions_total"], 1)
        self.assertEqual(m["open_questions_closed"], 1)

    def test_empty_discussion_is_graceful(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "disc-r4"
            d.mkdir()
            (d / "MASTER.md").write_text(
                "# M\n\n## 解决思路（整合叙事）\nsol\n\n", encoding="utf-8")
            m = metrics.compute_discussion_metrics(d)
        self.assertEqual(m["viewpoint_count"], 0)
        self.assertEqual(m["raw_volume_chars"], 0)
        self.assertEqual(m["open_questions_total"], 0)
        self.assertEqual(m["closure_rate"], 0.0)
        self.assertEqual(m["solution_volume_chars"], len("sol"))


class CliSeam(unittest.TestCase):
    def test_cli_emits_discussion_json(self):
        t1, *_ = build_subdoc(["B"], [("B", "B1", False)], "DONE", "s1")
        with tempfile.TemporaryDirectory() as tmp:
            d = write_discussion(tmp, {"sub-01-a.md": t1}, "整合叙事。")
            out = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "metrics.py"), str(d)],
                capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            rec = json.loads(out.stdout)
            self.assertEqual(rec["discussion_slug"], "disc-r4")
            self.assertIs(rec["recomputable"], True)
            sub = d / "sub-01-a.md"
            out2 = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "metrics.py"), str(sub)],
                capture_output=True, text=True)
            rec2 = json.loads(out2.stdout)
            self.assertEqual(rec2["sub_doc_id"], "sub-01-a")

    def test_missing_path_exits_nonzero(self):
        self.assertNotEqual(
            metrics.main(["/nope/does-not-exist"]), 0)


class SensitivityGuard(unittest.TestCase):
    """Mutation-style: metrics must read real file content, not a constant."""

    def test_extra_chars_change_raw_by_exactly_that(self):
        base_text, base_raw, _, _, _ = build_subdoc(
            ["B"], [("B", "原始观点。", False)], "DONE", "结论。")
        extra = "追加的额外辩论内容。"
        mut_text, mut_raw, _, _, _ = build_subdoc(
            ["B"], [("B", "原始观点。" + extra, False)], "DONE", "结论。")
        with tempfile.TemporaryDirectory() as tmp:
            pb = Path(tmp) / "b.md"
            pb.write_text(base_text, encoding="utf-8")
            pm = Path(tmp) / "m.md"
            pm.write_text(mut_text, encoding="utf-8")
            mb = metrics.compute_subdoc_metrics(pb)
            mm = metrics.compute_subdoc_metrics(pm)
        self.assertEqual(mut_raw - base_raw, len(extra))
        self.assertEqual(mm["raw_volume_chars"] - mb["raw_volume_chars"], len(extra))
        self.assertEqual(mm["viewpoint_count"], mb["viewpoint_count"])
        self.assertEqual(mm["viewpoint_count"], 1)


if __name__ == "__main__":
    unittest.main()

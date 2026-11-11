#!/usr/bin/env python3
"""#245 切片 1 — 只读编排信号（read-only advisory）。

纪律（与 #242 / #245 的边界一致）：

- 信号只从 roadmap **自身可机械判定的结构状态**派生，不推断产品事实或外部证据
  （process-state 权威边界见 SKILL.md:78-82）。
- 无信号时两个 Markdown 视图逐字节不变。本文件用 `compose_*` 默认参数与显式
  空串的字节断言 + 无信号图 CLI 控制例钉住；仓里 `Slice06` 的无阻塞三态归一化
  控制例与 `test_cross_carrier_render.py` 的双 carrier 断言再补两道。
  注意 `Slice06` 对历史 commit 的基线比对因 radial render 被有意 skip，不作依据。
- 命令不写入：不进 `LOCK_COMMANDS`，跑前跑后 carrier 字节不变。
- `checked == 0` 不得当成「检查通过」：payload 必须报实际检查过的节点数。

运行：python tests/test_orchestration_signals.py
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import roadmap as core  # noqa: E402
import roadmap_cli as cli  # noqa: E402

CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"
TARGETS = {"single": "roadmap.json", "sqlite": "roadmap.sqlite"}

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
DATA_LINE = re.compile(r"^> 数据文件: .*$", re.MULTILINE)


def normalize(text: str) -> str:
    """跨 carrier 唯一合法差异：文件名与写入时刻。"""
    return TIMESTAMP.sub("<T>", DATA_LINE.sub("> 数据文件: <F>", text))


def node(nid, **overrides):
    base = {
        "id": nid,
        "label": f"节点{nid}",
        "status": "pending",
        "mode": "exploit",
        "children": [],
        "layer": "plan",
    }
    base.update(overrides)
    return (nid, base)


# ── 规则层：每类信号都必须有命中 / 不命中成对 fixture ──────────────

class SignalRulesTest(unittest.TestCase):
    def kinds(self, *nodes):
        return [s["kind"] for s in core.orchestration_signal_items(nodes)]

    # 1. completed 节点仍挂 open_question
    def test_completed_with_open_question_is_a_signal(self):
        self.assertIn(
            "completed_with_open_question",
            self.kinds(node("1-1", status="completed",
                            open_question={"question": "要不要拆 sibling?"})),
        )

    def test_open_question_on_pending_node_is_not_a_signal(self):
        self.assertNotIn(
            "completed_with_open_question",
            self.kinds(node("1-1", status="pending",
                            open_question={"question": "要不要拆 sibling?"})),
        )

    def test_completed_without_open_question_is_not_a_signal(self):
        self.assertEqual([], self.kinds(node("1-1", status="completed")))

    # 2. 探索预算触顶（子节点数 / 开工轮次）
    def test_exhausted_child_budget_is_a_signal(self):
        self.assertIn(
            "budget_exhausted",
            self.kinds(node("1-1", budget={"max_children": 1}, children=["1-1-1"])),
        )

    def test_unused_child_budget_is_not_a_signal(self):
        self.assertEqual([], self.kinds(node("1-1", budget={"max_children": 3}, children=[])))

    def test_exhausted_round_budget_is_a_signal(self):
        self.assertIn(
            "budget_exhausted",
            self.kinds(node("1-1", budget={"max_rounds": 2}, rounds=2)),
        )

    def test_unused_round_budget_is_not_a_signal(self):
        self.assertEqual([], self.kinds(node("1-1", budget={"max_rounds": 2}, rounds=1)))

    # 3. 判据被显式清空但节点未完工
    def test_cleared_exit_criteria_on_unfinished_work_is_a_signal(self):
        self.assertIn(
            "cleared_exit_criteria",
            self.kinds(node("1-1", status="in_progress", exit_criteria=[])),
        )

    def test_non_empty_exit_criteria_is_not_a_signal(self):
        self.assertEqual([], self.kinds(node("1-1", status="in_progress",
                                            exit_criteria=["全部测试通过"])))

    def test_absent_exit_criteria_is_not_a_signal(self):
        """从未设置判据 ≠ 判据被清空。只报后者，避免一建图就满屏噪声。"""
        self.assertEqual([], self.kinds(node("1-1", status="in_progress")))

    def test_cleared_criteria_on_completed_node_is_not_a_signal(self):
        self.assertEqual([], self.kinds(node("1-1", status="completed", exit_criteria=[])))

    # 确定性与「检查确实跑过」
    def test_order_is_deterministic_regardless_of_input_order(self):
        first = core.orchestration_signal_items([
            node("1-3", status="completed", open_question={"question": "q"}),
            node("1-1", budget={"max_children": 1}, children=["1-1-1"]),
        ])
        second = core.orchestration_signal_items([
            node("1-1", budget={"max_children": 1}, children=["1-1-1"]),
            node("1-3", status="completed", open_question={"question": "q"}),
        ])
        self.assertEqual(first, second)
        self.assertEqual([(s["node"], s["kind"]) for s in first],
                         sorted((s["node"], s["kind"]) for s in first))

    def test_payload_reports_checked_count_even_with_zero_signals(self):
        payload = core.orchestration_signals([node("1"), node("1-1")])
        self.assertEqual(payload["checked"], 2)
        self.assertEqual(payload["signal_count"], 0)
        self.assertEqual(payload["signals"], [])
        self.assertTrue(payload["read_only"])

    def test_every_signal_carries_a_confirmable_suggested_action(self):
        signals = core.orchestration_signal_items([
            node("1-1", budget={"max_children": 1}, children=["1-1-1"]),
            node("1-2", status="in_progress", exit_criteria=[]),
        ])
        self.assertTrue(signals)
        for s in signals:
            self.assertTrue(s["node"])
            self.assertTrue(s["detail"])
            self.assertTrue(s["suggested_action"])


# ── 模板层：无信号时逐字节不变 ────────────────────────────────

class TemplateControlTest(unittest.TestCase):
    def test_light_section_with_default_signals_equals_explicit_empty(self):
        kwargs = dict(artifact_name="r.json", updated="2026-01-01 00:00:00",
                      tree_text="[ ] 1. root", chain="", open_questions="", focus_detail="")
        self.assertEqual(core.compose_light_section(**kwargs),
                         core.compose_light_section(**kwargs, signals=""))

    def test_full_section_with_default_signals_equals_explicit_empty(self):
        kwargs = dict(artifact_name="r.json", updated="2026-01-01 00:00:00",
                      focus_head="", tree_text="[ ] 1. root", chain="", open_questions="")
        self.assertEqual(core.compose_full_section(**kwargs),
                         core.compose_full_section(**kwargs, signals=""))

    def test_empty_signal_list_renders_no_block(self):
        self.assertEqual("", core.render_orchestration_signals_collapsed([]))
        self.assertEqual("", core.render_orchestration_signals_plain([]))

    def test_signals_command_is_not_a_locked_writer(self):
        self.assertIn("signals", cli.COMMANDS)
        self.assertNotIn("signals", cli.LOCK_COMMANDS)


# ── CLI 进程级：只读、确定性、双 carrier、两道 md 出口 ─────────────

class SignalsCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, cwd=None, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(cwd or self.workdir), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"CLI 失败 ({' '.join(map(str, args))})\n"
                      f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def build(self, storage: str, with_signals: bool = True) -> Path:
        """同一串命令在两个 carrier 各放一份，返回该 carrier 的工作目录。"""
        here = self.workdir / storage
        here.mkdir(parents=True, exist_ok=True)
        path = here / TARGETS[storage]
        (here / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        link = ["--md-file", "plan.md"]
        self.run_cli("init", path, "--storage", storage, "--title", "信号验收", *link, cwd=here)
        # with_signals=False 时把上限放宽，让同一串命令造出一张真正干净的无信号图：
        # 否则 budget_exhausted 会命中，「无信号」控制例就名不副实。
        cap = "1" if with_signals else "2"
        self.run_cli("add", path, "1", "探索", "--mode", "explore", "--max-children", cap, cwd=here)
        self.run_cli("add", path, "1-1", "子节点", cwd=here)
        self.run_cli("add", path, "1", "实现", "--exit-criteria", "全部通过", cwd=here)
        if with_signals:
            self.run_cli("update", path, "1-2", "--clear-exit-criteria", cwd=here)
        return here

    def payload(self, here: Path):
        return json.loads(self.run_cli("signals", here / TARGETS[here.name],
                                      cwd=here).stdout)

    def test_signals_command_is_read_only_on_both_carriers(self):
        for storage in TARGETS:
            here = self.build(storage)
            path = here / TARGETS[storage]
            self.run_cli("signals", path, cwd=here)  # 预热：sqlite 首次会建 schema
            before = path.read_bytes()
            md_before = (here / "plan.md").read_bytes()
            self.run_cli("signals", path, cwd=here)
            self.assertEqual(before, path.read_bytes(), f"{storage}: carrier 被改写")
            self.assertEqual(md_before, (here / "plan.md").read_bytes(),
                             f"{storage}: md 视图被改写")

    def test_output_is_byte_identical_on_repeated_calls(self):
        here = self.build("single")
        first = self.run_cli("signals", here / "roadmap.json", cwd=here).stdout
        second = self.run_cli("signals", here / "roadmap.json", cwd=here).stdout
        self.assertEqual(first, second)

    def test_checked_is_positive_and_counts_plan_nodes(self):
        here = self.build("single")
        payload = self.payload(here)
        self.assertGreater(payload["checked"], 0)  # checked==0 不得判 PASS
        self.assertEqual(payload["checked"], 4)    # 1, 1-1, 1-1-1, 1-2
        self.assertEqual(payload["schema"], "zj-orchestration-signals/v1")

    def test_expected_signals_are_detected_through_the_cli(self):
        here = self.build("single")
        kinds = {s["kind"] for s in self.payload(here)["signals"]}
        self.assertEqual(kinds, {"budget_exhausted", "cleared_exit_criteria"})

    def test_both_carriers_produce_identical_payloads(self):
        outputs = []
        for storage in TARGETS:
            here = self.build(storage)
            outputs.append(self.run_cli("signals", here / TARGETS[storage], cwd=here).stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_light_view_collapses_signals_and_states_the_count(self):
        here = self.build("single")
        self.run_cli("render", here / "roadmap.json", cwd=here)
        md = (here / "plan.md").read_text(encoding="utf-8")
        self.assertIn("编排信号：2 条待确认", md)
        self.assertIn("<details>", md)
        self.assertIn("1-1", md)
        self.assertIn("1-2", md)

    def test_export_view_lists_signals_plain_without_details(self):
        here = self.build("single")
        section = self.run_cli("section", here / "roadmap.json", cwd=here).stdout
        self.assertIn("### 编排信号", section)
        self.assertNotIn("<details>", section)
        self.assertIn("1-1", section)

    def test_both_carriers_render_identical_markdown_views(self):
        lights, sections = [], []
        for storage in TARGETS:
            here = self.build(storage)
            path = here / TARGETS[storage]
            self.run_cli("render", path, cwd=here)
            lights.append(normalize((here / "plan.md").read_text(encoding="utf-8")))
            sections.append(normalize(self.run_cli("section", path, cwd=here).stdout))
        self.assertEqual(lights[0], lights[1])
        self.assertEqual(sections[0], sections[1])

    def test_no_signal_graph_leaves_both_views_unchanged(self):
        here = self.build("single", with_signals=False)
        path = here / "roadmap.json"
        self.assertEqual([], self.payload(here)["signals"])
        self.run_cli("render", path, cwd=here)
        md = (here / "plan.md").read_text(encoding="utf-8")
        section = self.run_cli("section", path, cwd=here).stdout
        self.assertNotIn("编排信号", md)
        self.assertNotIn("### 编排信号", section)
        self.assertNotIn("<details>", md)


# ── 可发现性：`next`（早已存在却没登记）与新的 `signals` ──────────

class DiscoverabilityContractTest(unittest.TestCase):
    def test_cli_reference_lists_both_read_only_commands(self):
        text = (SKILL_DIR / "references" / "roadmap-cli.md").read_text(encoding="utf-8")
        # Match the command, not its published path prefix: the install-state
        # path basis (and the scripts/ location) can change without breaking
        # the discoverability contract.
        self.assertRegex(text, r'roadmap_cli\.py" next <roadmap_path>')
        self.assertRegex(text, r'roadmap_cli\.py" signals <roadmap_path>')
        heading = "## Orchestration signals (read-only)"
        self.assertIn(heading, text)
        # 专门章节必须声明「只读 + 不替人执行」，否则命令列出来仍会被误当成写入口。
        paragraph = text[text.find(heading):text.find(heading) + 1400]
        self.assertIn("只读", paragraph)
        self.assertIn("把命令写出来 ≠ 替人跑", paragraph)

    def test_skill_workflow_names_both_commands(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`next`", text)
        self.assertIn("`signals`", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

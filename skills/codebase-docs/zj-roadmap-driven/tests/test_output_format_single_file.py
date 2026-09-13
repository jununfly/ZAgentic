"""#104 S5 — 输出格式 --format/--fields/--quiet + context/next。single-file carrier。

测试缝：CLI 进程级（每条命令新进程，证明输出层落盘稳定）。
核心契约：
- 默认（无 flag）输出与现状逐字节一致（向后兼容，验收 #1）
- --format json 等价默认；--format md/table 渲染表格
- --fields 投影键；--quiet 只打 id
- context <id> 输出上游/下游/阻塞链；next 输出就绪优先节点
- 两 carrier 覆盖

本文件覆盖 single-file carrier；bundle 跑同一套断言的文件是
`test_output_format_bundle.py`（继承本文件的 Slice，不复制）。

运行：python tests/test_output_format_single_file.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

CLI = SKILL_DIR / "roadmap_cli.py"

FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}


class OutputFormatContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.roadmap = self.workdir / "roadmap.json"

    def tearDown(self):
        self.tmp.cleanup()

    # ── helpers ──────────────────────────────────────────

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=self.workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=FIXED_ENV,
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--title", "fmt")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def get_node(self, ref):
        return json.loads(self.run_cli("get", self.roadmap, ref).stdout)

    def get_raw(self, *args):
        return self.run_cli(*args).stdout


# ── Slice A：_emit 发射器 + get 接线 ─────────────────────────
#
# RED：当前 cmd_get 忽略 --format/--fields/--quiet，输出完整 JSON。
# 以下断言在接线前会失败。

class SliceAGetFormatTest(OutputFormatContractTest):
    """get 经 --format/--fields/--quiet，且默认输出逐字节不变。"""

    def test_default_get_is_unchanged_full_json(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        out = self.get_raw("get", self.roadmap, "1-1")
        node = self.get_node("1-1")
        # 默认必须 = 现状（完整 JSON，含派生字段）
        self.assertEqual(json.loads(out), node)

    def test_format_json_equals_default(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        default = self.get_raw("get", self.roadmap, "1-1")
        explicit = self.get_raw("get", self.roadmap, "1-1", "--format", "json")
        self.assertEqual(json.loads(default), json.loads(explicit))

    def test_fields_projects_keys(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        out = self.get_raw("get", self.roadmap, "1-1", "--fields", "id,label")
        data = json.loads(out)
        self.assertEqual(set(data.keys()), {"id", "label"})
        self.assertEqual(data["id"], "1-1")
        self.assertEqual(data["label"], "设计")

    def test_quiet_prints_only_id(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        out = self.get_raw("get", self.roadmap, "1-1", "--quiet").strip()
        self.assertEqual(out, "1-1")

    def test_format_table_renders_text_table_not_json(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        out = self.get_raw("get", self.roadmap, "1-1", "--format", "table")
        self.assertNotIn('"', out)  # 不是 JSON
        self.assertIn("1-1", out)
        self.assertIn("设计", out)

    def test_format_md_renders_markdown_table(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        out = self.get_raw("get", self.roadmap, "1-1", "--format", "md")
        self.assertIn("|", out)  # markdown 表格分隔符
        self.assertIn("1-1", out)


class SliceBStructuralFormatTest(OutputFormatContractTest):
    """stats/decisions/edge list/focus 经 --format/--fields，默认逐字节不变。"""

    def test_stats_default_json_and_format_table(self):
        self.init_roadmap()
        default = json.loads(self.get_raw("stats", self.roadmap))
        self.assertIsInstance(default, dict)
        self.assertIn("total_nodes", default)
        tbl = self.get_raw("stats", self.roadmap, "--format", "table")
        self.assertNotIn('"', tbl)  # 不是 JSON

    def test_decisions_fields_projects(self):
        self.init_roadmap()
        self.add_node("1", "A")
        self.run_cli("decide", self.roadmap, "1-1", "q?", "a")
        out = json.loads(self.get_raw("decisions", self.roadmap, "1-1", "--fields", "q"))
        self.assertEqual(set(out[0].keys()), {"q"})

    def test_edge_list_fields_projects(self):
        self.init_roadmap()
        self.add_node("1", "A")
        self.add_node("1", "B")
        self.run_cli("edge", "add", self.roadmap, "1-1", "1-2", "--type", "blocks")
        out = json.loads(self.get_raw("edge", "list", self.roadmap, "--fields", "id,type"))
        self.assertEqual(set(out[0].keys()), {"id", "type"})

    def test_focus_fields_projects(self):
        self.init_roadmap()
        self.add_node("1", "A")
        self.run_cli("update", self.roadmap, "1-1", "--status", "in_progress")
        out = json.loads(self.get_raw("focus", self.roadmap, "--fields", "focus"))
        self.assertEqual(set(out.keys()), {"focus"})
        self.assertEqual(out["focus"], "1-1")


class SliceCRowFormatTest(OutputFormatContractTest):
    """ready/impact/critical-path/path/siblings 行式命令：--quiet 只打 id，--format 转结构化。"""

    def _two_leaves(self):
        self.init_roadmap()
        self.add_node("1", "A")  # 1-1
        self.add_node("1", "B")  # 1-2

    def test_ready_quiet_prints_only_ids(self):
        self._two_leaves()
        out = [l for l in self.get_raw("ready", self.roadmap, "--quiet").strip().splitlines() if l]
        self.assertEqual(set(out), {"1-1", "1-2"})

    def test_ready_default_text_lines(self):
        self._two_leaves()
        out = self.get_raw("ready", self.roadmap)
        self.assertIn("1-1", out)
        self.assertIn(".", out)  # 文本行格式 "id. label icon"

    def test_ready_format_json_list(self):
        self._two_leaves()
        out = json.loads(self.get_raw("ready", self.roadmap, "--format", "json"))
        self.assertEqual({n["id"] for n in out}, {"1-1", "1-2"})

    def test_impact_quiet_only_ids(self):
        self._two_leaves()
        self.run_cli("edge", "add", self.roadmap, "1-1", "1-2", "--type", "blocks")
        out = [l for l in self.get_raw("impact", self.roadmap, "1-1", "--quiet").strip().splitlines() if l]
        self.assertEqual(out, ["1-2"])

    def test_critical_path_quiet_only_ids(self):
        self._two_leaves()
        out = [l for l in self.get_raw("critical-path", self.roadmap, "--quiet").strip().splitlines() if l]
        self.assertTrue(all("." not in x for x in out))

    def test_path_quiet_only_ids(self):
        self._two_leaves()
        out = [l for l in self.get_raw("path", self.roadmap, "1-2", "--quiet").strip().splitlines() if l]
        self.assertEqual(out, ["1", "1-2"])

    def test_siblings_quiet_only_ids(self):
        self._two_leaves()
        out = [l for l in self.get_raw("siblings", self.roadmap, "1-1", "--quiet").strip().splitlines() if l]
        self.assertEqual(out, ["1-2"])


class SliceDContextTest(OutputFormatContractTest):
    """context <id>：上游/下游/阻塞链（#104 S5）。"""

    def _chain(self):
        self.init_roadmap()
        self.add_node("1", "A")  # 1-1
        self.add_node("1", "B")  # 1-2
        self.run_cli("edge", "add", self.roadmap, "1-1", "1-2", "--type", "blocks")
        return "1-1", "1-2"

    def test_context_downstream_and_blocked_by(self):
        _, b = self._chain()
        ctx = json.loads(self.get_raw("context", self.roadmap, b))
        self.assertEqual(ctx["id"], b)
        self.assertEqual(ctx["upstream"], ["1-1"])
        self.assertEqual(ctx["downstream"], [])
        self.assertEqual(ctx["blocked_by"], ["1-1"])  # 1-1 pending → 仍阻塞

    def test_context_upstream(self):
        a, _ = self._chain()
        ctx = json.loads(self.get_raw("context", self.roadmap, a))
        self.assertEqual(ctx["upstream"], [])
        self.assertEqual(ctx["downstream"], ["1-2"])
        self.assertEqual(ctx["blocked_by"], [])

    def test_context_fields_projects(self):
        _, b = self._chain()
        ctx = json.loads(self.get_raw("context", self.roadmap, b, "--fields", "id,upstream"))
        self.assertEqual(set(ctx.keys()), {"id", "upstream"})

    def test_context_quiet_only_id(self):
        _, b = self._chain()
        out = self.get_raw("context", self.roadmap, b, "--quiet").strip()
        self.assertEqual(out, b)


class SliceENextTest(OutputFormatContractTest):
    """next：就绪优先建议（#104 S5）。"""

    def test_next_returns_ready_nodes(self):
        self.init_roadmap()
        self.add_node("1", "A")  # 1-1
        self.add_node("1", "B")  # 1-2
        out = json.loads(self.get_raw("next", self.roadmap))
        self.assertEqual({n["id"] for n in out}, {"1-1", "1-2"})

    def test_next_quiet_only_ids(self):
        self.init_roadmap()
        self.add_node("1", "A")
        self.add_node("1", "B")
        out = [l for l in self.get_raw("next", self.roadmap, "--quiet").splitlines() if l]
        self.assertEqual(set(out), {"1-1", "1-2"})

    def test_next_respects_blocking(self):
        self.init_roadmap()
        self.add_node("1", "A")  # 1-1
        self.add_node("1", "B")  # 1-2
        self.run_cli("edge", "add", self.roadmap, "1-1", "1-2", "--type", "blocks")
        out = json.loads(self.get_raw("next", self.roadmap))
        # 1-2 被 1-1 阻塞，仅 1-1 就绪
        self.assertEqual([n["id"] for n in out], ["1-1"])


if __name__ == "__main__":
    unittest.main()

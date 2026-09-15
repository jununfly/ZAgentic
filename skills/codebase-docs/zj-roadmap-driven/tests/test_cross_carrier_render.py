#!/usr/bin/env python3
"""#117 — 三个 carrier 的 Human 视野必须逐字节相等。

为什么单开一个文件
------------------
这是从 #117 里剥出来的第二处漂移：迁移本身已经能证明"事实源搬过去了"，但
`render` / `section` 是 Human 唯一看得到的面子，它两边的**模板是各抄一份的**
（`Roadmap.render_full_section` 一份、`RoadmapBundle.render_full_section` 一份）。
抄两份就等于承诺它们永远同步——bundle 那边已经缺了 `> 当前施工` 行、
`ROADMAP_TREE` 标记与"当前施工点"块，light section 里焦点节点的决策又丢了备注。

所以这个文件守的是一条比"迁移保真"更强的断言：**同一张图，三个 carrier 的两个
Markdown 视图逐字节相同**。迁不迁移都得成立。

覆盖的形状（每一条对应一处曾经真实的差异）：
  - 焦点节点（最深 in_progress 叶子）→ `> 当前施工` 行 + 焦点块
  - 焦点节点的决策带备注 → light section 的 `- Q: ... → ...（备注）`
  - blocks 边产生的阻塞链 → 两个视图都有
  - `--all` 的决策历史表

运行：python tests/test_cross_carrier_render.py
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

CLI = SKILL_DIR / "roadmap_cli.py"

# 载体 → 文件名后缀。init 的 --storage 与后缀要一致，否则 CLI 会按路径形状挑错载体。
TARGETS = {"single": "roadmap.json", "bundle": "roadmap.bundle", "sqlite": "roadmap.sqlite"}

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
# 数据文件名与最后更新时间在两个 carrier 上必然不同（文件名不同、写入时刻不同），
# 这两行是"合法差异"——其余任何一处不同都是漂移。
DATA_LINE = re.compile(r"^> 数据文件: .*$", re.MULTILINE)


def normalize(text: str) -> str:
    return TIMESTAMP.sub("<T>", DATA_LINE.sub("> 数据文件: <F>", text))


class CrossCarrierRenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, cwd=None, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(cwd or self.workdir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"roadmap_cli failed with {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def build(self, storage: str) -> Path:
        """在独立目录里重放同一串命令，返回该 carrier 的工作目录。"""
        name = TARGETS[storage]
        here = self.workdir / storage
        here.mkdir(parents=True, exist_ok=True)
        path = here / name
        # 每个目录一份 plan.md：共用一份会把上一个 carrier 写的 section 带进下一个，
        # 那不是渲染差异，是测试自己造的干扰。
        (here / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        link = ["--md-file", "plan.md"]
        self.run_cli("init", path, "--storage", storage, "--title", "渲染一致性", *link, cwd=here)
        self.run_cli("add", path, "1", "设计", "--mode", "explore", "--max-children", "3", cwd=here)
        self.run_cli("add", path, "1", "实现", "--mode", "exploit", "--exit-criteria", "全部通过", cwd=here)
        self.run_cli("add", path, "1-2", "子任务", cwd=here)
        self.run_cli("update", path, "1-2-1", "--status", "in_progress", cwd=here)
        self.run_cli("decide", path, "1-2-1", "先做什么", "先打通链路", "带备注", cwd=here)
        self.run_cli("decide", path, "1-1", "为什么这样切", "因为 carrier 要各自成立", cwd=here)
        self.run_cli("edge", "add", path, "1-1", "1-2", "--type", "blocks", cwd=here)
        self.run_cli("render", path, cwd=here)
        return here

    def light_sections(self) -> dict[str, str]:
        """`render` 写进 md 的轻量视图。"""
        return {s: normalize((self.build(s) / "plan.md").read_text(encoding="utf-8"))
                for s in TARGETS}

    def full_sections(self) -> dict[str, str]:
        """`section` 打给 stdout 的 bounded 视图。"""
        out = {}
        for storage in TARGETS:
            here = self.build(storage)
            out[storage] = normalize(self.run_cli("section", here / TARGETS[storage], cwd=here).stdout)
        return out

    def test_the_light_section_is_byte_identical_across_carriers(self):
        views = self.light_sections()

        self.assertEqual(views["single"], views["sqlite"])
        self.assertEqual(views["single"], views["bundle"])

    def test_the_full_section_is_byte_identical_across_carriers(self):
        views = self.full_sections()

        self.assertEqual(views["single"], views["sqlite"])
        self.assertEqual(views["single"], views["bundle"])

    def test_the_full_export_is_byte_identical_across_carriers(self):
        views = {}
        for storage in TARGETS:
            here = self.build(storage)
            views[storage] = normalize(
                self.run_cli("section", here / TARGETS[storage], "--all", cwd=here).stdout
            )

        self.assertEqual(views["single"], views["sqlite"])
        self.assertEqual(views["single"], views["bundle"])

    def test_the_focus_node_is_named_in_both_views(self):
        """差异最容易被肉眼放过的一处：bundle 曾完全没有"当前施工"这一行。"""
        for storage in TARGETS:
            with self.subTest(storage=storage):
                here = self.build(storage)
                light = normalize((here / "plan.md").read_text(encoding="utf-8"))
                full = normalize(
                    self.run_cli("section", here / TARGETS[storage], cwd=here).stdout
                )
                self.assertIn("1-2-1. 子任务", light)
                self.assertIn("> 当前施工: 1-2-1. 子任务", full)


if __name__ == "__main__":
    unittest.main()

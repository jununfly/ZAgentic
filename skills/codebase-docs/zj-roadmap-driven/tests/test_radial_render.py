#!/usr/bin/env python3
"""焦点辐射视图（radial）的验收测试。

#142 之后 `render_light_section` 从「固定 depth=2 的整树」重构为「焦点辐射 +
异常折叠」，`tree --anchor <id>` 提供 CLI 入口。这份测试守的是四件事：

  1. 有焦点时祖先链必现、焦点子树下钻、非焦点兄弟折叠计数（radial 三件套）。
  2. completed 子树折叠、过深子树截断（异常折叠两分支）。
  3. 无 in_progress 叶子时回退根树 depth=2，与历史快照逐字节一致（D2 保快照）。
  4. 轻量视图尾部出现 ready 小节，补 Human readiness 缺口（D3）。
  5. 两 carrier 的径向轻量视图逐字节相等（载体无关模板的唯一真相源契约）。

运行：python tests/test_radial_render.py
"""

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import roadmap
from roadmap import Roadmap
import roadmap_sqlite
from roadmap_sqlite import RoadmapSqlite

CLI = SKILL_DIR / "roadmap_cli.py"

CARRIERS = {"single": Roadmap, "sqlite": RoadmapSqlite}


def radial_sample() -> dict:
    """焦点 = 1-1-1（in_progress 叶子）；1-1 是它唯一祖先兄弟层；1-2/1-3 是被折叠的兄弟。

    刻意造了三类形状：
      - 祖先链 1 → 1-1 → 1-1-1（radial 必现）
      - 兄弟 1-2（completed 子树）、1-3（深 pending 子树）→ 折叠 / 截断
      - 焦点子树里 1-1-2 是 completed 整子树 → 折叠计数
    """
    return {
        "title": "radial",
        "version": 1,
        "nodes": {
            "1":       {"id": "1", "uid": "u1", "label": "root", "status": "in_progress",
                        "mode": "explore", "parent": None, "children": ["1-1", "1-2", "1-3"],
                        "decisions": [], "notes": "", "rounds": 1},
            "1-1":     {"id": "1-1", "uid": "u1-1", "label": "design", "status": "pending",
                        "mode": "explore", "parent": "1", "children": ["1-1-1", "1-1-2"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-1-1":   {"id": "1-1-1", "uid": "u1-1-1", "label": "api", "status": "in_progress",
                        "mode": "explore", "parent": "1-1", "children": [],
                        "decisions": [], "notes": "", "rounds": 1},
            "1-1-2":   {"id": "1-1-2", "uid": "u1-1-2", "label": "schema", "status": "completed",
                        "mode": "explore", "parent": "1-1", "children": ["1-1-2-1", "1-1-2-2"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-1-2-1": {"id": "1-1-2-1", "uid": "u1-1-2-1", "label": "idx", "status": "completed",
                        "mode": "explore", "parent": "1-1-2", "children": ["1-1-2-1-1", "1-1-2-1-2"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-1-2-1-1": {"id": "1-1-2-1-1", "uid": "u1-1-2-1-1", "label": "a", "status": "completed",
                          "mode": "explore", "parent": "1-1-2-1", "children": [],
                          "decisions": [], "notes": "", "rounds": 0},
            "1-1-2-1-2": {"id": "1-1-2-1-2", "uid": "u1-1-2-1-2", "label": "b", "status": "completed",
                          "mode": "explore", "parent": "1-1-2-1", "children": [],
                          "decisions": [], "notes": "", "rounds": 0},
            "1-1-2-2": {"id": "1-1-2-2", "uid": "u1-1-2-2", "label": "mig", "status": "completed",
                        "mode": "explore", "parent": "1-1-2", "children": [],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-2":     {"id": "1-2", "uid": "u1-2", "label": "impl", "status": "completed",
                        "mode": "exploit", "parent": "1", "children": ["1-2-1", "1-2-2"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-2-1":   {"id": "1-2-1", "uid": "u1-2-1", "label": "core", "status": "completed",
                        "mode": "exploit", "parent": "1-2", "children": [],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-2-2":   {"id": "1-2-2", "uid": "u1-2-2", "label": "cli", "status": "completed",
                        "mode": "exploit", "parent": "1-2", "children": [],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-3":     {"id": "1-3", "uid": "u1-3", "label": "qa", "status": "pending",
                        "mode": "explore", "parent": "1", "children": ["1-3-1"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-3-1":   {"id": "1-3-1", "uid": "u1-3-1", "label": "e2e", "status": "pending",
                        "mode": "explore", "parent": "1-3", "children": ["1-3-1-1"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-3-1-1": {"id": "1-3-1-1", "uid": "u1-3-1-1", "label": "deep", "status": "pending",
                        "mode": "explore", "parent": "1-3-1", "children": ["1-3-1-1-1"],
                        "decisions": [], "notes": "", "rounds": 0},
            "1-3-1-1-1": {"id": "1-3-1-1-1", "uid": "u1-3-1-1-1", "label": "leaf", "status": "pending",
                          "mode": "explore", "parent": "1-3-1-1", "children": [],
                          "decisions": [], "notes": "", "rounds": 0},
        },
        "edges": [],
        "metadata": {"created": "2026-01-01 00:00:00", "updated": "2026-01-01 00:00:00",
                     "md_file": ""},
    }


def no_focus_sample() -> dict:
    """全 completed：没有 in_progress 叶子 → 无焦点，触发 D2 回退根树 depth=2。"""
    return {
        "title": "no-focus",
        "version": 1,
        "nodes": {
            "1":     {"id": "1", "uid": "n1", "label": "root", "status": "completed",
                      "mode": "explore", "parent": None, "children": ["1-1", "1-2"],
                      "decisions": [], "notes": "", "rounds": 1},
            "1-1":   {"id": "1-1", "uid": "n1-1", "label": "design", "status": "completed",
                      "mode": "explore", "parent": "1", "children": ["1-1-1"],
                      "decisions": [], "notes": "", "rounds": 0},
            "1-1-1": {"id": "1-1-1", "uid": "n1-1-1", "label": "api", "status": "completed",
                      "mode": "explore", "parent": "1-1", "children": [],
                      "decisions": [], "notes": "", "rounds": 0},
            "1-2":   {"id": "1-2", "uid": "n1-2", "label": "impl", "status": "completed",
                      "mode": "exploit", "parent": "1", "children": [],
                      "decisions": [], "notes": "", "rounds": 0},
        },
        "edges": [],
        "metadata": {"created": "2026-01-01 00:00:00", "updated": "2026-01-01 00:00:00",
                     "md_file": ""},
    }


def persist(path: str, data: dict, carrier_cls):
    r = carrier_cls(path)
    r.data = copy.deepcopy(data)
    r.save()
    return r


def _body(section: str) -> str:
    """去掉「数据文件」行（文件名/时间戳两 carrier 必然不同），其余须逐字节相同。"""
    return "\n".join(
        ln for ln in section.splitlines() if not ln.startswith("> 数据文件:")
    )


class RadialTreeUnit(unittest.TestCase):
    """直接调 `get_tree_radial`，逐分支断言三件套（载体无关，single carrier 即可）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "roadmap.json"
        self.r = persist(str(self.path), radial_sample(), Roadmap)
        self.r.load()
        self.owners = self.r.owner_map()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ancestor_chain_visible_with_sibling_folds(self):
        # 焦点 1-1-1：祖先 1 / 1-1 必现，两个兄弟层各折叠计数。
        text = self.r.get_tree_radial("1-1-1", self.owners, 2)
        self.assertIn("1. root", text)
        self.assertIn("1-1. design", text)
        self.assertIn("1-1-1. api", text)
        # 兄弟折叠：1-1 层剩 1 个（1-1-2），根层剩 2 个（1-2 / 1-3）。
        self.assertIn("该层还有 1 个兄弟", text)
        self.assertIn("该层还有 2 个兄弟", text)
        # 被折叠的兄弟非焦点节点不应单独成行（只出现在折叠计数里）。
        self.assertNotIn("1-2. impl", text)
        self.assertNotIn("1-3. qa", text)
        self.assertNotIn("1-1-2. schema", text)

    def test_focus_subtree_expands_in_progress_and_folds_completed(self):
        # 焦点 = 1-1（direct call）：焦点直接子必现，in_progress 子下钻、completed 子的
        # completed 孙节点折叠计数（焦点一层邻域恒现，更深 completed 分支折叠）。
        text = self.r.get_tree_radial("1-1", self.owners, 2)
        self.assertIn("1-1. design", text)
        self.assertIn("1-1-1. api", text)            # in_progress 子：强制展开
        self.assertIn("1-1-2. schema", text)         # 焦点直接子：恒现
        # completed 孙节点折叠，cnt 含整棵（1-1-2-1 → 自身 + 2 孙 = 3）。
        self.assertIn("1-1-2-1 已完成（折叠 3 项）", text)
        self.assertIn("1-1-2-2 已完成（折叠 1 项）", text)
        self.assertNotIn("1-1-2-1-1", text)          # 折叠子树内部不展开
        self.assertNotIn("1-1-2-1-2", text)

    def test_deep_pending_subtree_truncated(self):
        # 焦点 = 1-3，focus_subtree_depth=1：过深 pending 子树截断提示。
        text = self.r.get_tree_radial("1-3", self.owners, 1)
        self.assertIn("1-3. qa", text)
        self.assertIn("1-3-1. e2e", text)
        self.assertIn("子树过深，run tree 1-3-1-1 --depth 2 for full view", text)
        # 截断层之下不再逐行展开。
        self.assertNotIn("1-3-1-1-1. leaf", text)

    def test_unknown_focus_reports_gracefully(self):
        self.assertEqual(self.r.get_tree_radial("nope", self.owners), "(节点 nope 不存在)")


class RadialLightSection(unittest.TestCase):
    """`render_light_section` 的两条分支 + ready 小节。载体无关（single）即可。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "roadmap.json"
        self.r = persist(str(self.path), radial_sample(), Roadmap)
        self.r.load()

    def tearDown(self):
        self.tmp.cleanup()

    def test_light_section_uses_radial_when_focus_present(self):
        # 焦点 1-1-1 存在 → 径向树进 md，且等于直接调 get_tree_radial 的产出。
        section = self.r.render_light_section()
        self.assertIn("1-1-1. api", section)
        self.assertIn("该层还有", section)
        self.assertIn(self.r.get_tree_radial("1-1-1", self.r.owner_map(), 2), section)

    def test_light_section_ready_preview_lists_top_ready(self):
        # ready 集前 3：1-1 / 1-3 / 1-3-1（1-3、1-3-1 只在 ready 小节出现，树里被折叠）。
        section = self.r.render_light_section()
        self.assertIn("下一步可开工（ready 前 3）", section)
        self.assertIn("1-3. qa", section)
        self.assertIn("1-3-1. e2e", section)

    def test_light_section_falls_back_to_depth2_when_no_focus(self):
        # 无焦点（全 completed）→ 回退根树 depth=2，无径向折叠、无 ready 小节。
        r = persist(str(Path(self.tmp.name) / "nf.json"), no_focus_sample(), Roadmap)
        r.load()
        section = r.render_light_section()
        self.assertNotIn("该层还有", section)        # 不是径向视图
        self.assertNotIn("下一步可开工", section)    # 无就绪集
        # 回退树整棵展开（不折叠）：根 + 直接子 + 孙都出现。
        self.assertIn("1. root", section)
        self.assertIn("1-1-1. api", section)


class RadialCrossCarrier(unittest.TestCase):
    """两 carrier 的径向轻量视图必须逐字节相等（模板只写一份的硬验收）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.carriers = {}
        for name, cls in CARRIERS.items():
            p = self.d / f"roadmap.{('sqlite' if name == 'sqlite' else 'json')}"
            persist(str(p), radial_sample(), cls)  # writes identical bytes
            self.carriers[name] = cls(str(p))
            self.carriers[name].load()             # fresh instance, read back

    def tearDown(self):
        self.tmp.cleanup()

    def test_radial_light_section_byte_identical_across_carriers(self):
        single = _body(self.carriers["single"].render_light_section())
        sqlite = _body(self.carriers["sqlite"].render_light_section())
        self.assertEqual(single, sqlite)

    def test_radial_tree_byte_identical_across_carriers(self):
        single = self.carriers["single"].get_tree_radial(
            "1-1-1", self.carriers["single"].owner_map(), 2)
        sqlite = self.carriers["sqlite"].get_tree_radial(
            "1-1-1", self.carriers["sqlite"].owner_map(), 2)
        self.assertEqual(single, sqlite)


class RadialCliAnchor(unittest.TestCase):
    """CLI `tree --anchor <id>` 必须路由到径向视图（D1）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "roadmap.json"
        persist(str(self.path), radial_sample(), Roadmap).load()

    def tearDown(self):
        self.tmp.cleanup()

    def _cli(self, *args):
        res = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        return res.stdout

    def test_tree_anchor_routes_to_radial(self):
        out = self._cli("tree", str(self.path), "--anchor", "1-1-1")
        self.assertIn("1-1-1. api", out)
        self.assertIn("该层还有", out)  # 径向折叠标记，普通树没有

    def test_tree_anchor_true_uses_current_focus(self):
        # `--anchor` 不带值 → 以当前焦点（1-1-1）为锚。
        out = self._cli("tree", str(self.path), "--anchor")
        self.assertIn("1-1-1. api", out)

    def test_tree_without_anchor_is_plain(self):
        # 不带 --anchor 走老路径：整树 depth=10，无径向折叠。
        out = self._cli("tree", str(self.path))
        self.assertIn("1-2. impl", out)
        self.assertNotIn("该层还有", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

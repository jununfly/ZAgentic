#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue #260 回归测试：真实 carrier（blocks 边以 uid 端点存储）下，
父子层级连线与 blocks 依赖连线必须都可见。

背景：roadmap_cli.py edge add 把边端点存为节点 uid（与 roadmap.py 的
edge_endpoints_as_display 展示约定一致）。demo fixture（roadmap_viz_sample.json）
误用 id 端点，导致原 viz 管线（假设 id 端点、从不翻译 uid→id）在测试里「正常」、
在真实 carrier 上整条边消失——这就是 #260 被掩盖的根因。本测试用 uid 端点 carrier
直接锁住该回归。

运行：
  /Users/bilibili/anaconda3/bin/python3 viz/tests/test_issue260.py
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIZ = HERE.parent
SKILL = VIZ.parent
import sys
for p in (str(SKILL), str(SKILL / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from viz.graph import RoadmapGraph  # noqa: E402
from viz import dependency as dep  # noqa: E402
from viz.render_html import render_html  # noqa: E402


def _uid_carrier() -> dict:
    """模拟 roadmap_cli.py edge add 的真实产物：边端点 = 节点 uid。"""
    return {
        "title": "uid-endpoint carrier",
        "nodes": {
            "1":   {"id": "1",   "uid": "u1",   "label": "根",   "status": "pending",
                    "mode": "explore", "parent": None, "children": [], "decisions": [],
                    "notes": "", "layer": "plan", "rounds": 1},
            "1-1": {"id": "1-1", "uid": "u1-1", "label": "完成设计", "status": "in_progress",
                    "mode": "explore", "parent": "1", "children": [], "decisions": [],
                    "notes": "", "layer": "plan", "rounds": 1},
            "1-2": {"id": "1-2", "uid": "u1-2", "label": "开始实现", "status": "pending",
                    "mode": "explore", "parent": "1", "children": [], "decisions": [],
                    "notes": "", "layer": "plan", "rounds": 1},
        },
        # 端点存的是 uid（真实 carrier 规范），不是 id
        "edges": [
            {"id": "e1", "from": "u1-1", "to": "u1-2", "type": "blocks"},
        ],
        "debts": [],
    }


def _id_carrier() -> dict:
    """老数据 / 部分 fixture：边端点直接用 id（endpoint_to_id 应幂等）。"""
    d = _uid_carrier()
    d["edges"] = [{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}]
    return d


class TestIssue260UidEndpoints(unittest.TestCase):
    def setUp(self):
        self.data = _uid_carrier()
        self.graph = RoadmapGraph.from_data(self.data, carrier_stem="uid-carrier")

    def test_blocks_edges_resolved_to_ids(self):
        """Bug A：边端点必须归一化为 id，使邻接/嵌入/前端一致。"""
        self.assertEqual(len(self.graph.edges), 1)
        e = self.graph.edges[0]
        self.assertEqual(e["from"], "1-1")
        self.assertEqual(e["to"], "1-2")
        self.assertNotIn("u1", e["from"])
        self.assertNotIn("u1", e["to"])

    def test_adjacency_populated(self):
        """Bug A：真实 carrier 下 pred/succ 必须非空（之前因 uid 键对不上 id 全空）。"""
        self.assertEqual(self.graph.pred["1-2"], {"1-1"})
        self.assertEqual(self.graph.succ["1-1"], {"1-2"})

    def test_hierarchy_derived(self):
        """Bug B：父子层级边必须从 node.parent 派生。"""
        self.assertIn({"from": "1", "to": "1-1"}, self.graph.hierarchy)
        self.assertIn({"from": "1", "to": "1-2"}, self.graph.hierarchy)
        self.assertEqual(len(self.graph.hierarchy), 2)

    def test_dependency_projection_unmasked(self):
        """Bug A：Python dependency 投影在真实 carrier 下必须正确（曾被完全掩盖）。"""
        d = dep.build_dependency("1-2", self.graph)
        self.assertEqual(d["edge_count"], 1)
        self.assertEqual(d["blocked_by"], ["1-1"])
        self.assertEqual(d["critical_path"], ["1-1", "1-2"])
        # EDGE_META 的 from/to 也必须是 id（供前端 EDGE_BY_PAIR 命中）
        self.assertEqual(d["edges"][0]["from"], "1-1")
        self.assertEqual(d["edges"][0]["to"], "1-2")

    def test_legacy_id_endpoints_still_work(self):
        """endpoint_to_id 对 id 端点应幂等，老数据不退化。"""
        g = RoadmapGraph.from_data(_id_carrier(), carrier_stem="id-carrier")
        self.assertEqual(g.edges[0]["from"], "1-1")
        self.assertEqual(g.edges[0]["to"], "1-2")
        self.assertEqual(g.pred["1-2"], {"1-1"})

    def test_embed_carries_ids_and_hierarchy(self):
        """渲染产物必须内嵌 id 端点的 edges + hierarchy，供前端画线。"""
        html = render_html(self.graph, "1-2")
        m = re.search(r"const GRAPH = (\{.*?\});\nconst ENVELOPE", html, re.S)
        self.assertIsNotNone(m)
        g = json.loads(m.group(1))
        self.assertEqual(g["edges"][0]["from"], "1-1")
        self.assertEqual(g["edges"][0]["to"], "1-2")
        self.assertIn({"from": "1", "to": "1-1"}, g["hierarchy"])
        # 关键判据：blocks 与 hierarchy 端点都在 nodes key 中 → 前端能画线
        nodes = g["nodes"]
        for e in g["edges"]:
            self.assertIn(e["from"], nodes)
            self.assertIn(e["to"], nodes)
        for h in g["hierarchy"]:
            self.assertIn(h["from"], nodes)
            self.assertIn(h["to"], nodes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Generic tests for zj-doc-collab launch_pack_core (engine only, no consumer wording)."""

import sys
import shutil
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from launch_pack_core import (
    parse_declared_set,
    load_role_pool,
    load_signals,
    render_pack,
    generate_prep,
    generate,
)

MATRIX = """# Role Matrix

| key | 角色 | 默认 | 结构立场 | 差异锚点 | 一句话简介 |
| --- | --- | --- | --- | --- | --- |
| B | 技术经理 | ✅ | 可落地 | 排期 | 把方案逼到能做 |
| C | 产品专家 | ✅ | 用户价值 | 优先级 | 问值不值 |
| A | 架构师 | ✅ | 约束 | 边界 | 问以后炸不炸 |
| S | 安全 | ⚪ | 攻击面 | 权限 | 问被打穿 |

## 推荐启发式

| 信号（子问题触及…） | 建议追加角色 |
| --- | --- |
| 权限 / 数据泄露 | S（安全） |
"""


class LaunchPackCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path.home() / ".cache" / "zj-doc-collab-tests" / uuid.uuid4().hex
        cls.tmp.mkdir(parents=True, exist_ok=True)
        cls.matrix = cls.tmp / "role-matrix.md"
        cls.matrix.write_text(MATRIX, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_parse_declared_set(self):
        text = "声明必需角色集：B, C, A\n"
        self.assertEqual(parse_declared_set(text), ["B", "C", "A"])

    def test_parse_declared_set_empty(self):
        self.assertEqual(parse_declared_set("no such field here"), [])

    def test_load_role_pool(self):
        pool = load_role_pool(self.matrix)
        self.assertIn("B", pool)
        self.assertIn("S", pool)
        self.assertTrue(pool["B"]["is_base"])
        self.assertFalse(pool["S"]["is_base"])
        self.assertEqual(pool["B"]["name"], "技术经理")

    def test_load_signals(self):
        sig = load_signals(self.matrix)
        self.assertEqual(sig.get("S"), "权限 / 数据泄露")

    def test_render_pack_fills_slots(self):
        info = {"name": "技术经理", "stance": "可落地", "intro": "把方案逼到能做"}
        out = render_pack(
            "B", info, "/p/sub-01.md",
            executor_cmd="zj-discuss-view --role B /p/sub-01.md",
            role_method_ref="references/role-methods/B.md",
        )
        self.assertIn("技术经理", out)
        self.assertIn("zj-discuss-view --role B /p/sub-01.md", out)
        self.assertIn("references/role-methods/B.md", out)

    def test_generate_prep_two_tables(self):
        pool = load_role_pool(self.matrix)
        sig = load_signals(self.matrix)
        out = generate_prep(pool, sig, base_reason=lambda r: "base")
        self.assertIn("推荐参与角色", out)
        self.assertIn("其他可选角色", out)
        self.assertIn("| B |", out)
        self.assertIn("| S |", out)

    def test_generate_writes_packs(self):
        subdoc = self.tmp / "sub-01.md"
        subdoc.write_text("声明必需角色集：B, A\n", encoding="utf-8")
        out_dir = self.tmp / "briefings"
        packs = generate(
            subdoc, None, out_dir, self.matrix,
            executor_cmd_template="zj-discuss-view --role {key} {subdoc}",
            role_method_ref_template="references/role-methods/{key}.md",
        )
        self.assertEqual(len(packs), 2)
        for p in packs:
            self.assertTrue(p.exists())
            self.assertIn("zj-discuss-view --role", p.read_text(encoding="utf-8"))

    def test_generate_refuses_unknown_role(self):
        subdoc = self.tmp / "sub-02.md"
        subdoc.write_text("声明必需角色集：Z\n", encoding="utf-8")
        with self.assertRaises(Exception):
            generate(subdoc, None, self.tmp / "b2", self.matrix)


if __name__ == "__main__":
    unittest.main()

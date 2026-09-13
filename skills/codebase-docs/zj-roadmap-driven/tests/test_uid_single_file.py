"""#99 S2 — 不可变节点 uid（P0 地基）。

spec：每个节点一个不可变 `uid`，一经生成永不变更、永不复用；显示 id（`1-1-2`）
继续给人用，两者并存。P2 租约与 P5 trace 都硬依赖它——**它们挂的是 uid，不是
位置 id**（位置 id 会复用，租约会挂到错误的节点上，且这种 bug 静默）。

测试缝：CLI 进程级。每条 CLI 调用都是新进程，所以"uid 是否真的落盘、是否稳定"
由命令本身证明，不需要额外造 reload。

本文件覆盖 single-file carrier；bundle 跑同一套断言的文件是 `test_uid_bundle.py`
（继承本文件的 Slice，不复制）。

运行：python tests/test_uid_single_file.py
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


class UidContractTest(unittest.TestCase):
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
        self.run_cli("init", self.roadmap, "--title", "uid")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def get_node(self, node_id):
        return json.loads(self.run_cli("get", self.roadmap, node_id).stdout)

    def md_section(self):
        return self.run_cli("section", self.roadmap).stdout

    def strip_uids(self):
        """把 carrier 里的 uid 全部抹掉，模拟 P0 之前的老 roadmap。"""
        path = self.workdir / "roadmap.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data["nodes"].values():
            node.pop("uid", None)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Slice01UidOnCreationTest(UidContractTest):
    """建出来的节点必须带 uid，且它稳定、唯一。"""

    def test_the_root_node_has_a_uid(self):
        self.init_roadmap()

        self.assertTrue(self.get_node("1").get("uid"))

    def test_every_new_node_gets_a_uid(self):
        self.init_roadmap()

        first = self.add_node("1", "设计")
        second = self.add_node("1", "实现")

        self.assertTrue(first["uid"])
        self.assertTrue(second["uid"])

    def test_uids_are_unique_within_a_roadmap(self):
        self.init_roadmap()
        created = [self.add_node("1", label) for label in ("a", "b", "c")]

        uids = [self.get_node(node["id"])["uid"] for node in created]
        uids.append(self.get_node("1")["uid"])

        self.assertEqual(len(uids), len(set(uids)))

    def test_a_uid_is_stable_across_commands(self):
        """uid 生成后只读：换一条命令（新进程）读回来必须还是同一个。"""
        self.init_roadmap()
        created = self.add_node("1", "设计")

        first_read = self.get_node(created["id"])["uid"]
        self.add_node("1", "实现")  # 触发一次写入 + 落盘
        second_read = self.get_node(created["id"])["uid"]

        self.assertEqual(second_read, first_read)


class Slice02UidStaysOutOfTheHumanViewTest(UidContractTest):
    """uid 是给机器用的，不许泄进 md —— §6 护栏 2：新字段默认不进 md。"""

    def test_the_md_view_does_not_contain_any_uid(self):
        self.init_roadmap()
        created = self.add_node("1", "设计")
        uid = self.get_node(created["id"])["uid"]

        self.assertNotIn(uid, self.md_section())

    def test_the_md_view_still_uses_the_display_id(self):
        """反向控制：md 里仍然该出现人说的那个位置 id。"""
        self.init_roadmap()
        self.add_node("1", "设计")

        self.assertIn("1-1", self.md_section())


class Slice03LegacyUpgradeTest(UidContractTest):
    """老 roadmap（没有 uid）在下一次写入时被补齐 —— 迁移走写侧，不自动。"""

    def test_a_legacy_roadmap_is_upgraded_on_the_next_write(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.strip_uids()

        # 一次写入命令：save 是 single-file 的唯一写入点，迁移挂在那里。
        self.add_node("1", "实现")

        for node_id in ("1", "1-1", "1-2"):
            self.assertTrue(
                self.get_node(node_id).get("uid"),
                f"{node_id} 在写入后仍未补上 uid",
            )

    def test_the_upgrade_does_not_change_the_display_ids(self):
        """补齐 uid 是加字段，不是改视图 —— Human 看到的 id 一个都不许动。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.strip_uids()

        self.add_node("1", "实现")

        self.assertEqual(self.get_node("1-1")["id"], "1-1")
        self.assertEqual(self.get_node("1-2")["id"], "1-2")


if __name__ == "__main__":
    unittest.main()

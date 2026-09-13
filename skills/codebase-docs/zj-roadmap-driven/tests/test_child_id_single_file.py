"""#99 S1 — 子节点序号单调递增（删除后不回收）。

Problem #5：老实现取 `children[-1]` 再 +1，删掉尾部子节点后新节点会拿回刚删掉
的那个 id，外部引用（租约 / ticket / ADR / 跨设备同步）静默串号。

测试缝：CLI 进程级。每条 CLI 调用都是**新进程**，所以"水位是否真的落盘"不需要
额外造 reload —— 命令本身就是 reload。

本文件只覆盖 single-file carrier；bundle 跑同一套断言的文件是
`test_child_id_bundle.py`（继承本文件的 Slice，不复制）。

运行：python tests/test_child_id_single_file.py
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

# stats 的 status_counts 由 set 推导，键顺序跟着 PYTHONHASHSEED 变。
FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}


class ChildIdContractTest(unittest.TestCase):
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
        self.run_cli("init", self.roadmap, "--title", "child id")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def delete_node(self, node_id):
        return self.run_cli("delete", self.roadmap, node_id)

    def get_node(self, node_id):
        return json.loads(self.run_cli("get", self.roadmap, node_id).stdout)


class Slice01NoReuseAfterTailDeletionTest(ChildIdContractTest):
    """删掉尾部子节点后，那个序号不得再次发出去。"""

    def test_a_deleted_tail_id_is_not_handed_out_again(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.delete_node("1-2")

        self.assertEqual(self.add_node("1", "返工")["id"], "1-3")

    def test_the_high_water_mark_survives_a_new_process(self):
        """水位必须落盘：连删两次都要继续往上抬，不能回到"最后一个 +1"。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.delete_node("1-2")
        self.add_node("1", "返工")

        self.delete_node("1-3")

        self.assertEqual(self.add_node("1", "再返工")["id"], "1-4")

    def test_deleting_twice_keeps_raising_the_mark(self):
        self.init_roadmap()
        for label in ("a", "b", "c"):
            self.add_node("1", label)

        self.delete_node("1-3")
        self.delete_node("1-2")

        self.assertEqual(self.add_node("1", "d")["id"], "1-4")


class Slice02UnchangedWithoutDeletionTest(ChildIdContractTest):
    """没删过东西时行为与从前一致 —— 证明防复用没有误伤正常路径。"""

    def test_numbering_is_unchanged_when_nothing_was_deleted(self):
        self.init_roadmap()

        self.assertEqual(self.add_node("1", "a")["id"], "1-1")
        self.assertEqual(self.add_node("1", "b")["id"], "1-2")
        self.assertEqual(self.add_node("1", "c")["id"], "1-3")

    def test_deleting_a_middle_child_does_not_shift_the_next_id(self):
        self.init_roadmap()
        for label in ("a", "b", "c"):
            self.add_node("1", label)

        # 删中间那个：children 最后一个仍是 1-3，下一个自然该是 1-4。
        self.delete_node("1-2")

        self.assertEqual(self.add_node("1", "d")["id"], "1-4")

    def test_a_parent_that_never_lost_a_child_has_no_high_water_field(self):
        """水位惰性物化：没删过就不写字段，存量 roadmap 的字节因此不变。

        这条同时是"防复用"与"Slice08 无边路径不被污染"之间的契约——
        水位只在真的发生过删除之后才出现。
        """
        self.init_roadmap()
        self.add_node("1", "a")
        self.add_node("1", "b")

        self.assertNotIn("childSequence", self.get_node("1"))

        self.delete_node("1-2")

        self.assertEqual(self.get_node("1").get("childSequence"), 2)


if __name__ == "__main__":
    unittest.main()

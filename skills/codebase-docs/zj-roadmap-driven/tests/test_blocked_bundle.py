"""#80 第二刀 — bundle carrier 的阻塞派生。

与 single-file 跑**同一套断言**：直接继承 test_blocked_single_file.py 里的
Slice 类，只换掉存储（`--storage bundle`）。继承而非复制，是"两个 carrier 同语义"
这条不变式唯一的机械证明——复制一份副本的话，改了一边另一边不会红。

运行：python tests/test_blocked_bundle.py
"""

import json
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# 以模块方式引用：unittest 的 loader 会收集模块里出现的每一个 TestCase 子类，
# from-import 会把 single-file 那边那一份也收进来跑一遍，计数虚高且看不出哪份
# 是哪个 carrier 的。
import test_blocked_single_file as sf  # noqa: E402


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "P1 阻塞派生")

    def on_disk_nodes(self):
        """落盘缝：节点分片 + 决策分片拼出来的"存着的东西"，不含派生字段。"""
        nodes = {}
        for shard in sorted((self.roadmap / "nodes").glob("*.json")):
            node = json.loads(shard.read_text(encoding="utf-8"))
            decisions = self.roadmap / "decisions" / shard.name
            node["decisions"] = (
                json.loads(decisions.read_text(encoding="utf-8"))["decisions"]
                if decisions.is_file()
                else []
            )
            nodes[node["id"]] = node
        return nodes


class Slice01BlockedIsDerivedAtReadBundleTest(BundleStorageMixin, sf.Slice01BlockedIsDerivedAtReadTest):
    """同 Slice01，跑在 bundle carrier 上。"""


class Slice02PredecessorCompletesBundleTest(BundleStorageMixin, sf.Slice02PredecessorCompletesTest):
    """同 Slice02：前驱一完成，两个派生字段在同一次读里消失。"""


class Slice03EdgeRemovedBundleTest(BundleStorageMixin, sf.Slice03EdgeRemovedTest):
    """同 Slice03：删掉那条边后同样立即消失。"""


class Slice04NeverPersistedBundleTest(BundleStorageMixin, sf.Slice04NeverPersistedTest):
    """同 Slice04：status 从未被写成 blocked。

    bundle 的分片是一个节点一个文件，所以"落盘"在这里更直白——不存在"整图重写
    时顺手带上派生字段"的模糊地带。
    """


class Slice05BlockedIsNotSettableBundleTest(BundleStorageMixin, sf.Slice05BlockedIsNotSettableTest):
    """同 Slice05：`--status blocked` 在两个 carrier 上同样被拒。"""


class Slice07SoftEdgesDoNotBlockBundleTest(BundleStorageMixin, sf.Slice07SoftEdgesDoNotBlockTest):
    """同 Slice07（负向控制例）：软边不阻塞。"""


class Slice08NoEdgeControlBundleTest(BundleStorageMixin, sf.Slice08NoEdgeControlTest):
    """同 Slice08：无边路径上不凭空多出字段。"""


class Slice10TreeRendersTheDerivedIconBundleTest(BundleStorageMixin, sf.Slice10TreeRendersTheDerivedIconTest):
    """同 Slice10：md / tree 视图里被挡住的节点显示 `[!]`。

    bundle 没有整图可扫，图标按 `edges/` 目录现算两个 carrier 最容易在这里
    漂移——一边按边算、一边按 status 算，tree 就会不一致。
    """


class Slice09IndexIsRedundantTest(BundleStorageMixin, sf.BlockedContractTest):
    """派生读的是边本身，不是边索引。

    `edges/index.json` 是纯冗余（能重扫重建）。派生若走了索引，索引一丢就
    读不出 blocked——那是把一个派生值挂在了另一个可失效的副本上。
    """

    def test_blocked_is_derived_after_the_edge_index_is_deleted(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        (self.roadmap / "edges" / "index.json").unlink()

        node = self.get_node("1-2")

        self.assertTrue(node["blocked"])
        self.assertEqual(node["blocked_reason"], ["e1"])

    def test_the_index_lists_each_edge_once(self):
        """同一条边不能在索引里登记两次。

        堵的是 `add_edge` 的旧写法：先写边文件、再把 id 追加进索引，而读索引
        时若索引不存在会按目录重建——重建已经含了刚写进去的那条，追加之后就
        变成两条。`list_edges` 用 set 去重所以看不见，派生字段直接读索引就会
        把同一条边报两遍。
        """
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        index = json.loads((self.roadmap / "edges" / "index.json").read_text(encoding="utf-8"))

        self.assertEqual(index["to"]["1-3"], ["e1", "e2"])

    def test_unblocking_still_works_without_the_index(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        (self.roadmap / "edges" / "index.json").unlink()

        self.complete("1-1")

        self.assertNotIn("blocked", self.get_node("1-2"))


if __name__ == "__main__":
    unittest.main()

"""#82 第二刀 — bundle carrier 的 md 阻塞链。

与 single-file 跑**同一套断言**：继承 test_blocked_chain_single_file.py 里的
Slice 类，只换存储（`--storage bundle`）。继承而非复制是"两个 carrier 渲染一致"
这条验收唯一的机械证明——复制一份副本的话，改了单边另一边不会红。

Slice06（a8ee1b9 基线字节比对）不继承：那个基线的 bundle 还没有后来的 md 出口
形态，它验的是 single-file 那条路径不被污染。

运行：python tests/test_blocked_chain_bundle.py
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

import test_blocked_chain_single_file as sf  # noqa: E402


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.md_file.write_text("# 我的计划\n\n", encoding="utf-8")
        self.run_cli(
            "init",
            self.roadmap,
            "--storage",
            "bundle",
            "--title",
            "P1 阻塞链",
            "--md-file",
            str(self.md_file),
        )


class Slice01HumanViewCollapsesTheChainBundleTest(
    BundleStorageMixin, sf.Slice01HumanViewCollapsesTheChainTest
):
    """同 Slice01：Human 主视图里的折叠阻塞链。"""


class Slice02ExportViewListsTheChainPlainBundleTest(
    BundleStorageMixin, sf.Slice02ExportViewListsTheChainPlainTest
):
    """同 Slice02：`section` 非折叠。

    两个 carrier 的 `render_full_section` 本来就不一样（只有 single-file 那版
    有 TREE markers / 当前施工点），所以这里钉的是链那一节而不是整份输出。
    """


class Slice03TheChainTracksTheCurrentGraphBundleTest(
    BundleStorageMixin, sf.Slice03TheChainTracksTheCurrentGraphTest
):
    """同 Slice03：链跟着边走，没有"上次算的残留"。

    bundle 读的是 `edges/` 目录分片，不能直接拿整图迭代，最容易在这里漏更新。
    """


class Slice04TheChainStaysShortAndMarksTruncationBundleTest(
    BundleStorageMixin, sf.Slice04TheChainStaysShortAndMarksTruncationTest
):
    """同 Slice04：上限与截断标注。"""


class Slice05SoftEdgesNeverEnterTheChainBundleTest(
    BundleStorageMixin, sf.Slice05SoftEdgesNeverEnterTheChainTest
):
    """同 Slice05（负向控制例）：软边不进链。"""


class Slice07NothingBlockedMeansNoBundleTest(BundleStorageMixin, sf.BlockedChainContractTest):
    """bundle 自己的一动即错点：没有 `edges/` 目录时不能出任何东西。

    bundle 在从没加过边的情况下连 `edges/` 目录都不存在。"渲染一个不存在的
    目录"最容易顺手写成"报 None / 吞异常"，那会让 bundle 在无边时比 single-file
    多出或缺少字节——而这正是 #73 不变式 3 要守住的地方。
    """

    def test_a_fresh_bundle_renders_without_any_chain(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        md = self.human_md()

        self.assertNotIn("<details>", md)
        self.assertNotIn("### 阻塞链", md)

    def test_the_edges_directory_stays_absent_until_an_edge_is_added(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.assertFalse((self.roadmap / "edges").exists())

    def test_the_edge_index_is_not_required_to_render_the_chain(self):
        """`edges/index.json` 是纯冗余：丢了照样能算出链。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        (self.roadmap / "edges" / "index.json").unlink()

        md = self.human_md()

        self.assertIn("<details>", md)
        self.assertIn("1 个节点被阻塞", self.details_block(md))

    def test_each_edge_is_listed_once_in_the_index(self):
        """同一条边不能在索引里登记两次——派生若照抄索引就会报两遍。"""
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        index = json.loads((self.roadmap / "edges" / "index.json").read_text(encoding="utf-8"))

        self.assertEqual(index["to"]["1-3"], ["e1", "e2"])


class Slice08BothCarriersRenderTheSameChainTest(BundleStorageMixin, sf.BlockedChainContractTest):
    """"两个 carrier 渲染结果一致"这条验收的直接证明。

    上面几个 Slice 继承的是同一套**断言**——那只能证明两边各自满足契约。这里
    拿同一张图在两个存储上各渲染一次，直接比链那一节的字节：一处拼 `- `、另一
    处漏个空格，断言照样全绿，而 Human 看到的是两份不一样的 md。
    """

    def build_graph(self, init):
        self.md_file.write_text("# 我的计划\n\n", encoding="utf-8")
        init()
        for label in ("设计", "实现", "上线"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

    def on_single_file(self, render):
        self.roadmap = self.workdir / "roadmap.json"
        try:
            self.build_graph(
                lambda: self.run_cli(
                    "init", self.roadmap, "--title", "P1 阻塞链", "--md-file", str(self.md_file)
                )
            )
            return render()
        finally:
            self.roadmap = self.workdir / "roadmap.bundle"

    def on_bundle(self, render):
        self.build_graph(self.init_roadmap)
        return render()

    def test_both_carriers_render_the_same_plain_chain(self):
        single = self.on_single_file(lambda: self.plain_chain_block(self.exported_section()))
        bundle = self.on_bundle(lambda: self.plain_chain_block(self.exported_section()))

        self.assertEqual(bundle, single)

    def test_both_carriers_render_the_same_collapsed_block(self):
        single = self.on_single_file(lambda: self.details_block(self.human_md()))
        bundle = self.on_bundle(lambda: self.details_block(self.human_md()))

        self.assertEqual(bundle, single)

    def test_the_chain_itself_is_not_empty_on_either_carrier(self):
        """防这条对照退化：两边都空的话相等是白给的。"""
        chain = self.on_single_file(lambda: self.plain_chain_block(self.exported_section()))
        bundle_chain = self.on_bundle(lambda: self.plain_chain_block(self.exported_section()))

        self.assertIn("1-3. 上线", chain)
        self.assertIn("1-3. 上线", bundle_chain)


if __name__ == "__main__":
    unittest.main()

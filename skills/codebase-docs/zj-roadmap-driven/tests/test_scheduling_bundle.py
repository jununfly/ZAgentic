"""#81 调度查询（ready / critical-path / impact）— bundle carrier。

与 single-file 跑**同一套断言**：继承 test_scheduling_single_file.py 里的 Slice
类，只换存储（`--storage bundle`）。继承而非复制，是"两个 carrier 同语义"这条
不变式唯一的机械证明——复制一份副本的话，改了一边另一边不会红。

bundle 侧另有三个它自己才有的错法，单独钉在 Slice03：
- `edges/` 目录在从没加过边时根本不存在；
- `indexes/status/<status>/<id>` 是另一份节点状态的副本，可能失效；
- 节点分片 `nodes/*.json` 才是权威。

运行：python tests/test_scheduling_bundle.py
"""

import json
import shutil
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
import test_scheduling_single_file as sf  # noqa: E402


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    STORAGE = "bundle"

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def pending_ids_from_carrier(self):
        """控制例的对照真相：节点分片里 status == pending 的 id。

        bundle 的状态还有一份 `indexes/status/` 副本，这里刻意读分片——那个副本
        正是"派生值依赖派生值"的位置，拿它当真相对照不出任何东西。
        """
        return {
            node["id"]
            for node in (
                json.loads(shard.read_text(encoding="utf-8"))
                for shard in (self.roadmap / "nodes").glob("*.json")
            )
            if node.get("status") == "pending"
        }


class Slice01ReadyBundleTest(BundleStorageMixin, sf.Slice01Ready):
    """同 Slice01：pending 且无未完成 `blocks` 前驱。"""


class Slice02ReadyControlBundleTest(BundleStorageMixin, sf.Slice02ReadyControl):
    """同 Slice02：没边时 `ready` 必须退化为 pending 语义。"""


class Slice03BundleOwnFailureModesTest(BundleStorageMixin, sf.SchedulingTestBase):
    """bundle 自己的一动即错点：目录不存在 / 索引失效 / 权威源。"""

    def build_two(self):
        self.init_map()
        self.add_node("1", "甲")
        self.add_node("1", "乙")

    def test_ready_survives_a_bundle_without_an_edges_directory(self):
        """从没加过边时 `edges/` 目录不存在——"枚举一个不存在的目录"最容易
        顺手写成吞异常或报 None，那会让 bundle 在无边时给出与 single-file 不同
        的答案。"""
        self.build_two()
        self.assertFalse((self.roadmap / "edges").exists())

        self.assertEqual({"1-1", "1-2"}, set(self.ready_ids()))

    def test_ready_reads_node_shards_not_the_status_index(self):
        """`indexes/status/` 整份删掉，答案不变：节点分片才是权威。

        那份索引是节点状态的第二副本。挂在它上面，等于让"谁就绪"这个派生值依赖
        另一个派生值——索引一漂移（分片改了、索引没跟上）就绪集就静默错。
        """
        self.build_two()
        self.add_edge("1-1", "1-2")
        before = set(self.ready_ids())

        shutil.rmtree(self.roadmap / "indexes" / "status")
        after = set(self.ready_ids())

        self.assertEqual(before, after)
        self.assertEqual({"1-1"}, after)

    def test_a_stale_entry_in_the_status_index_does_not_become_a_node(self):
        """索引里多一个没人认领的 id，不能凭空多出一行。

        反面是"拿索引当节点清单"——那会把索引当枚举源，而索引里出现悬空条目
        （旧版本残留、手工编辑）时 ready 会报一个不存在的节点。
        """
        self.build_two()
        self.add_edge("1-1", "1-2")
        stale = self.roadmap / "indexes" / "status" / "pending" / "9-9"
        stale.write_text("", encoding="utf-8")

        self.assertEqual({"1-1"}, set(self.ready_ids()))

    def test_a_fresh_bundle_reports_no_ready_nodes(self):
        """只有根节点（in_progress）的图：不报错，明确说没有。"""
        self.init_map()
        result = self.run_cli("ready", self.roadmap)

        self.assertEqual(0, result.returncode)
        self.assertIn("No ready nodes.", result.stdout)


class Slice04BothCarriersPrintTheSameReadyTest(BundleStorageMixin, sf.SchedulingTestBase):
    """"两个 carrier 输出一致"这条验收的直接证明。

    上面两个 Slice 继承的是同一套**断言**——那只能证明两边各自满足契约。这里拿
    同一张图在两个存储上各跑一次，直接比 stdout 的字节：一处多个空格、另一处排
    序不同，断言照样全绿，而调用方（Agent 取活）看到的是两份不一样的答案。
    """

    def build_graph(self, init):
        init()
        for label in ("设计", "实现", "上线"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3")
        self.add_edge("1-2", "1-3", "informs")

    def on_single_file(self):
        self.roadmap = self.workdir / "roadmap.json"
        try:
            self.build_graph(lambda: self.run_cli("init", self.roadmap, "--title", "P"))
            return self.run_cli("ready", self.roadmap).stdout
        finally:
            self.roadmap = self.workdir / "roadmap.bundle"

    def on_bundle(self):
        self.build_graph(self.init_map)
        return self.run_cli("ready", self.roadmap).stdout

    def test_both_carriers_print_the_same_ready_output(self):
        bundle_out = self.on_bundle()
        single_out = self.on_single_file()

        self.assertEqual(bundle_out, single_out)

    def test_the_output_is_not_empty_on_either_carrier(self):
        """防这条对照退化：两边都空的话相等是白给的。"""
        self.assertEqual("1-1. 设计 [ ]\n1-2. 实现 [ ]\n", self.on_bundle())
        self.assertEqual("1-1. 设计 [ ]\n1-2. 实现 [ ]\n", self.on_single_file())


if __name__ == "__main__":
    unittest.main()

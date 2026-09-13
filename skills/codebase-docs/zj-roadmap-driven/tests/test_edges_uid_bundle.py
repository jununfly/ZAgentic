"""#106 S4 第二刀 — bundle carrier 的边 uid 存储与迁移。

与 single-file 跑**同一套断言**：直接继承 test_edges_uid_single_file.py 里的 Slice 类，
只换掉存储（`--storage bundle`）。继承而非复制，是"两个 carrier 同语义"这条不变式
唯一的机械证明——复制一份副本的话，改了一边另一边不会红。

运行：python tests/test_edges_uid_bundle.py
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# 以模块方式引用，不用 from-import：unittest 的 loader 会收集模块里出现的
# 每一个 TestCase 子类，from-import 会把 single-file 那边那一份也收进来跑一遍，
# 计数虚高且看不出哪份是哪个 carrier 的。
import test_edges_uid_single_file as sf  # noqa: E402

from roadmap import Roadmap  # noqa: E402
from roadmap_bundle import EDGE_SCHEMA, RoadmapBundle  # noqa: E402

from roadmap import looks_like_uid  # noqa: E402  （断言落盘端点是 uid）


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "S4")

    def raw_edge_endpoints(self):
        """落盘字节里的边（bundle：edges/<id>.json 逐个读）。"""
        out = []
        for path in sorted((self.roadmap / "edges").glob("e*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop("schema", None)
            out.append(data)
        return out

    def node_uids(self):
        """当前图中所有节点的 uid 集合（bundle）。"""
        bundle = RoadmapBundle(str(self.roadmap))
        bundle.load()
        return {n.get("uid") for n in bundle._all_nodes()}

    def seed_display_id_edges(self, edges):
        """手工塞显示 id 边文件，模拟存量数据（未跑 migrate）。

        ！！要求调用前已 init 且建好 1-1 / 1-2 两个节点——这里只写边分片。
        """
        directory = self.roadmap / "edges"
        directory.mkdir(parents=True, exist_ok=True)
        for edge in edges:
            (directory / f"{edge['id']}.json").write_text(
                json.dumps({"schema": EDGE_SCHEMA, **edge}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        RoadmapBundle(str(self.roadmap))._rebuild_edge_index()


class SliceANewEdgeStoresUidBundleTest(BundleStorageMixin, sf.SliceANewEdgeStoresUidTest):
    """同 SliceA，跑在 bundle carrier 上。"""


class SliceBMigrationBundleTest(BundleStorageMixin, sf.SliceBMigrationTest):
    """同 SliceB：存量显示 id 边文件转为 uid，Human 视野不变、幂等。"""


class SliceCCycleInUidSpaceBundleTest(BundleStorageMixin, sf.SliceCCycleInUidSpaceTest):
    """同 SliceC：bundle 上 uid 空间环检测正确。"""


if __name__ == "__main__":
    unittest.main()

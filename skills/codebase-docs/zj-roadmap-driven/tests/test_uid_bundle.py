"""#99 S2 — bundle carrier 的 uid（与 single-file 同语义）。

继承 `test_uid_single_file.py` 的 Slice，只换存储（`--storage bundle`）。

bundle 的迁移路径与 single-file 不同：它没有"整图 save"这个唯一写入点，
分片是懒读的。所以 uid 补在两个地方——`_write_node_file`（写侧，任何一次
节点写入都会补）与 `_initialize_layout`（create / migrate 时覆盖全量节点）。
读侧（`_read_node_file`）**故意不补**：只读命令不拿整图锁，在那里写文件
并发时可能给同一节点生成两个不同 uid。

运行：python tests/test_uid_bundle.py
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

import test_uid_single_file as sf  # noqa: E402


class BundleStorageMixin:
    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "uid")

    def strip_uids(self):
        """bundle 没有单一 JSON：逐个分片抹掉 uid。"""
        for shard in (self.roadmap / "nodes").glob("*.json"):
            data = json.loads(shard.read_text(encoding="utf-8"))
            data.pop("uid", None)
            shard.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Slice01UidOnCreationBundleTest(BundleStorageMixin, sf.Slice01UidOnCreationTest):
    """同 Slice01，跑在 bundle carrier 上。"""


class Slice02UidStaysOutOfTheHumanViewBundleTest(
    BundleStorageMixin, sf.Slice02UidStaysOutOfTheHumanViewTest
):
    """同 Slice02：uid 不进 md，md 里仍然用位置 id。"""


class Slice03BundleMigrationTest(BundleStorageMixin, sf.UidContractTest):
    """bundle 的迁移契约与 single-file 不同，这里单独定义，不直接继承。

    bundle 没有"整图 save"这个唯一写入点，分片是懒读的，所以契约是两条：

    1. **写侧逐片升级** —— 任何一次分片写入都会给该分片补上 uid；
    2. **从 legacy 迁入时全量补齐** —— `migrate --to bundle` 走 `_initialize_layout`，
       每个节点都过一遍 `_write_node_file`。

    **未被写入过的老分片不会凭空长出 uid**，这是有意的边界而不是遗漏：要在读侧
    补就得在读的时候写文件，而只读命令（`ready` / `critical-path` / `impact`）
    不拿整图锁，两个进程同时读到"缺 uid"会各自生成一个并各自写回，uid 因此
    不再不可变——那正好毁掉它存在的理由。要全量升级就走 `migrate`。
    """

    def test_the_nodes_touched_by_a_write_are_upgraded(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.strip_uids()

        self.add_node("1", "实现")

        self.assertTrue(self.get_node("1").get("uid"), "父节点被写过，应补上 uid")
        self.assertTrue(self.get_node("1-2").get("uid"), "新节点应有 uid")

    def test_migrating_a_legacy_roadmap_gives_every_node_a_uid(self):
        legacy = self.workdir / "legacy.json"
        self.run_cli("init", legacy, "--title", "legacy")
        self.run_cli("add", legacy, "1", "设计")
        self.run_cli("add", legacy, "1", "实现")
        # 抹成 P0 之前的样子：没有任何 uid。
        data = json.loads(legacy.read_text(encoding="utf-8"))
        for node in data["nodes"].values():
            node.pop("uid", None)
        legacy.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        target = self.workdir / "migrated.bundle"
        self.run_cli("migrate", legacy, "--to", "bundle", "--output", target)

        for node_id in ("1", "1-1", "1-2"):
            got = json.loads(self.run_cli("get", target, node_id).stdout)
            self.assertTrue(got.get("uid"), f"{node_id} 迁移后没有 uid")

    def test_migration_keeps_the_display_ids(self):
        """补齐 uid 是加字段，不是改视图。"""
        legacy = self.workdir / "legacy.json"
        self.run_cli("init", legacy, "--title", "legacy")
        self.run_cli("add", legacy, "1", "设计")

        target = self.workdir / "migrated.bundle"
        self.run_cli("migrate", legacy, "--to", "bundle", "--output", target)

        got = json.loads(self.run_cli("get", target, "1-1").stdout)
        self.assertEqual(got["id"], "1-1")


if __name__ == "__main__":
    unittest.main()

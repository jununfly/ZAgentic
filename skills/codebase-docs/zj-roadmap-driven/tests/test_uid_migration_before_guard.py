"""#170 — 「迁移触发早于守卫」的纯函数层断言（不依赖 subprocess CLI）。

#170 根因：写侧守卫的租约身份解析（`get_lease` → `_lease_identity`）依赖 uid，
而 P0 的「老数据补齐 uid」迁移原本挂在 `save()` 里——守卫比迁移先跑，于是缺 uid
的存量 roadmap 在第一次写命令时就被守卫拦下（`E_ROADMAP: node X 缺少 uid`），
永远卡在「缺 uid」、无法被写命令补齐。

本文件在纯函数层断言：

1. 守卫调用 `_enforce_write_guard` 时，若节点缺 uid，必须**先**补齐再校验——
   不得抛 `RoadmapError`，且迁移后 uid 被填上、显示 id 不变。
2. `migrate_legacy_uids()` 对 single / sqlite 两 carrier 的 `self.data` 形状
   都正确补齐（sqlite 通过继承拿到同一份方法，数据形状一致）。
3. 迁移是**加字段**，绝不改显示 id（Human 视图零变化）。

运行：python tests/test_uid_migration_before_guard.py
"""

import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import Roadmap, RoadmapError  # noqa: E402
from roadmap_sqlite import RoadmapSqlite  # noqa: E402
from roadmap_cli import _enforce_write_guard  # noqa: E402

SCRATCH_ROOT = Path.home() / ".cache" / "zj-roadmap-tests"


def _legacy_data() -> dict:
    """一份没有 uid 的 P0 之前 roadmap（模拟 #170 的存量数据）。"""
    return {
        "title": "legacy",
        "version": 1,
        "nodes": {
            "1": {
                "id": "1",
                "label": "root",
                "status": "in_progress",
                "mode": "explore",
                "layer": "plan",
                "parent": None,
                "children": ["1-1"],
                "decisions": [],
                "notes": "",
            },
            "1-1": {
                "id": "1-1",
                "label": "设计",
                "status": "pending",
                "mode": "explore",
                "layer": "plan",
                "parent": "1",
                "children": [],
                "decisions": [],
                "notes": "",
            },
        },
        "metadata": {},
    }


def _assert_only_uids_were_added(self, before: dict, after: dict) -> None:
    """迁移必须只补 uid / layer，显示 id 等原有字段一个都不能变。"""
    self.assertEqual(set(before["nodes"].keys()), set(after["nodes"].keys()))
    for nid, node in before["nodes"].items():
        self.assertEqual(node["id"], after["nodes"][nid]["id"], f"{nid} 显示 id 变了")
        self.assertEqual(node["parent"], after["nodes"][nid]["parent"])
        self.assertEqual(node["children"], after["nodes"][nid]["children"])
        # 补齐的 uid 必须存在且 shape 合法（<12 hex>-<10 hex>）。
        uid = after["nodes"][nid].get("uid")
        self.assertTrue(uid, f"{nid} 迁移后仍未补上 uid")
        self.assertRegex(uid, r"^[0-9a-f]{12}-[0-9a-f]{10}$")


class SingleCarrierMigrationBeforeGuardTest(unittest.TestCase):
    def _roadmap(self) -> Roadmap:
        r = Roadmap(str(SCRATCH_ROOT / "single-legacy.json"))
        r.data = _legacy_data()
        return r

    def test_the_guard_triggers_migration_before_validating(self):
        """守卫读到缺 uid 的节点时，必须先补齐；不得抛 RoadmapError。"""
        r = self._roadmap()
        before = deepcopy(r.data)

        # 直接调守卫（不经由 CLI / 不落盘）——这正是 #170 的崩溃点。
        _enforce_write_guard(r, "1", {})

        _assert_only_uids_were_added(self, before, r.data)
        # 守卫之后，lease 身份解析必须能正常拿到 uid，不再报错。
        display_id, node_uid = r._lease_identity("1")
        self.assertEqual(display_id, "1")
        self.assertEqual(node_uid, r.data["nodes"]["1"]["uid"])

    def test_the_guard_returns_normally_without_lease_on_legacy(self):
        """无租约的存量节点，守卫应放行（planner 字段可写），不误报 E_LEASE_HELD。"""
        r = self._roadmap()
        # 不应抛任何异常（此前会抛 E_ROADMAP: 缺少 uid）。
        _enforce_write_guard(r, "1-1", {})
        self.assertTrue(r.data["nodes"]["1-1"]["uid"])

    def test_migrate_legacy_uids_is_idempotent_on_p0_data(self):
        """已是 P0 形态的数据，迁移返回 0、不产生新 uid。"""
        r = Roadmap(str(SCRATCH_ROOT / "single-p0.json"))
        r.data = _legacy_data()
        r.migrate_legacy_uids()  # 第一次补齐
        uids_first = {nid: n["uid"] for nid, n in r.data["nodes"].items()}
        count = r.migrate_legacy_uids()  # 第二次应当幂等
        self.assertEqual(count, 0)
        self.assertEqual(uids_first, {nid: n["uid"] for nid, n in r.data["nodes"].items()})

    def test_migrate_legacy_uids_returns_count(self):
        r = self._roadmap()
        self.assertEqual(r.migrate_legacy_uids(), 2)  # 两个节点都补了 uid


class SqliteCarrierMigrationBeforeGuardTest(unittest.TestCase):
    """sqlite carrier 继承同一份 `migrate_legacy_uids`，数据形状一致。

    不落盘成「缺 uid」的 sqlite（save 会补 uid），只在内存里构造缺 uid 的
    `self.data` 验证方法与守卫对 sqlite carrier 同样生效。
    """

    def _roadmap(self) -> RoadmapSqlite:
        r = RoadmapSqlite(str(SCRATCH_ROOT / "sqlite-legacy.db"))
        r.data = _legacy_data()
        return r

    def test_guard_triggers_migration_on_sqlite_carrier(self):
        r = self._roadmap()
        before = deepcopy(r.data)
        _enforce_write_guard(r, "1", {})
        _assert_only_uids_were_added(self, before, r.data)
        display_id, node_uid = r._lease_identity("1")
        self.assertEqual(display_id, "1")
        self.assertEqual(node_uid, r.data["nodes"]["1"]["uid"])

    def test_migrate_legacy_uids_fills_sqlite_shape(self):
        r = self._roadmap()
        self.assertEqual(r.migrate_legacy_uids(), 2)
        for nid in ("1", "1-1"):
            self.assertRegex(r.data["nodes"][nid]["uid"], r"^[0-9a-f]{12}-[0-9a-f]{10}$")
            self.assertEqual(r.data["nodes"][nid]["id"], nid)


if __name__ == "__main__":
    unittest.main()

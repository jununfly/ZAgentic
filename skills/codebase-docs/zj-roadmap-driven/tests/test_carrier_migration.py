#!/usr/bin/env python3
"""#117 P3 — 显式迁移与 recommend-storage 建议（Story 39 / 40）。

Spec 来源：docs/plans/zj-roadmap-dag-concurrency.md §5 + Story 39/40。
  Story 39  `recommend-storage` 保持只读建议，任何命令都不许悄悄换掉我的事实源。
  Story 40  换 carrier 只能走一条显式命令，迁移前后我永远知道哪个产物是事实源。

测试缝（2026-09-15 与 zj 确认，两层都覆盖）
------------------------------------------
  1. **CLI 命令层** — `roadmap_cli.py migrate <source> --to <carrier>`：Agent 的
     真实入口，唯一能同时钉住 stdout 契约与退出码的缝。
  2. **Python 函数层** — `carrier_migration` 的 detect_storage / export_roadmap_data /
     export_lease_store / migrate：钉住"三家 carrier 都吐同形 canonical 数据"这种
     用 CLI 输出难表达的语义。
  3. **Roadmap API** — `current_revision()` 跨 carrier 相等：这条既有函数（本次
     不改动它）是"迁移没丢东西"的最强单条断言，它覆盖节点/边/决策/metadata 的结构。

运行：python tests/test_carrier_migration.py
"""

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from carrier_migration import (  # noqa: E402
    CARRIERS,
    default_output,
    detect_storage,
    export_lease_store,
    load_carrier,
    write_carrier,
)
from roadmap import Roadmap  # noqa: E402
from roadmap_bundle import BundleError, RoadmapBundle  # noqa: E402
from roadmap_sqlite import RoadmapSqlite  # noqa: E402

CLI = SKILL_DIR / "roadmap_cli.py"
CARRIERS = ("single", "bundle", "sqlite")
SUFFIX = {"single": ".json", "bundle": ".bundle", "sqlite": ".sqlite"}


def revision_of(path):
    """独立 Oracle：按路径形状自己挑 carrier，不复用被测的 detect_storage。

    被测代码要是猜错了 carrier，`load()` 会炸或在错误的数据上算出个哈希——用被测
    代码当期望值来源，等于把"迁对了没有"这条断言变成自我比较。
    """
    target = Path(path)
    if target.is_dir():
        carrier = RoadmapBundle(target)
    elif target.suffix.lower() in (".sqlite", ".sqlite3", ".db"):
        carrier = RoadmapSqlite(target)
    else:
        carrier = Roadmap(target)
    carrier.load()
    return carrier.current_revision()


def lease_of(path, node_uid):
    carrier = RoadmapSqlite(path) if Path(path).suffix == ".sqlite" else (
        RoadmapBundle(path) if Path(path).is_dir() else Roadmap(path)
    )
    carrier.load()
    return carrier.get_lease(node_uid)


class MigrationCliTest(unittest.TestCase):
    """缝 1：CLI 契约。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.single = self.workdir / "roadmap.json"
        self.build_single()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=self.workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"roadmap_cli failed with {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def build_single(self):
        """一张能把各家 carrier 的存储差异都逼出来的图：树 + 决策 + blocks 边 + 预算字段。

        只用 `add` 建空树的话，边（uid 端点 vs 显示 id 端点）和 decisions（bundle
        单独分片）这两处最容易静默丢数据的地方就不会被覆盖到。
        """
        self.run_cli("init", self.single, "--title", "跨载体迁移")
        self.run_cli("add", self.single, "1", "设计", "--mode", "explore", "--max-children", "3")
        self.run_cli("add", self.single, "1", "实现", "--mode", "exploit", "--exit-criteria", "全部通过")
        self.run_cli("update", self.single, "1-2", "--status", "in_progress")
        self.run_cli("decide", self.single, "1-1", "为什么这样切", "因为 carrier 要各自成立")
        self.run_cli("edge", "add", self.single, "1-1", "1-2", "--type", "blocks")

    def migrate_to(self, source, storage, output=None):
        # 目标名带上这一站的目标 carrier：连续迁移时（single→bundle→sqlite）每一站
        # 的 stem 都不同，才不会一路都算出同一个文件名去撞已存在的产物。
        target = output or source.parent / f"{source.stem}.to-{storage}{SUFFIX[storage]}"
        self.run_cli("migrate", source, "--to", storage, "--output", target)
        return target

    def make_bundle(self, source):
        """用 Python API 造一个 bundle 夹具（migrate --to bundle 已弃用 #140）。

        原测试用 `migrate_to(source, "bundle")` 造 bundle，现在 create-from-migrate
        被封死；改用 RoadmapBundle.create_from_data 从同一份 single 数据直接落盘，
        保留节点/边/决策/metadata（租约侧车不进 seed.data，本批用例不需要它）。
        """
        from roadmap import Roadmap
        from roadmap_bundle import RoadmapBundle
        seed = Roadmap(source)
        seed.load()
        bundle_path = source.parent / f"{source.stem}.bundle-fixture.bundle"
        RoadmapBundle.create_from_data(bundle_path, seed.data, 100)
        return bundle_path

    # ── 迁移是保真的 ────────────────────────────────────

    def test_single_to_sqlite_preserves_the_revision(self):
        target = self.migrate_to(self.single, "sqlite")

        self.assertEqual(revision_of(self.single), revision_of(target))

    def test_migrate_to_bundle_is_rejected(self):
        """`--to bundle` 被封死（bundle 弃用 #140）：CLI 退出非 0 且报错指向迁移逃生路线。"""
        result = self.run_cli("migrate", self.single, "--to", "bundle", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("deprecated", result.stderr)
        self.assertIn("migrate", result.stderr)

    def test_bundle_to_sqlite_preserves_the_revision(self):
        bundle = self.make_bundle(self.single)
        target = self.migrate_to(bundle, "sqlite")

        self.assertEqual(revision_of(self.single), revision_of(target))

    def test_sqlite_to_single_preserves_the_revision(self):
        """绕一圈回到出发载体，revision 必须与最开始那份逐字节相同。

        这条能抓住"边端点被翻成 uid 后没翻回来"那类漂移——它让单边命令在 round-trip
        上看起来没问题，却把 Human 视野里的显示 id 悄悄掉包成 uid。
        """
        sqlite = self.migrate_to(self.single, "sqlite")
        back = self.migrate_to(sqlite, "single")

        self.assertEqual(revision_of(self.single), revision_of(back))
        self.assertEqual(
            json.loads((back).read_text(encoding="utf-8"))["edges"],
            json.loads(self.single.read_text(encoding="utf-8"))["edges"],
        )

    def test_the_human_view_of_edges_survives_a_bundle_round_trip(self):
        """导出保留 uid 端点；Human 看到的仍须是显示 id。

        翻译层本来就在读侧（`edge_endpoints_as_display`），导出不该替它做这一步——
        那是"看起来对"但会让三家 carrier 的 rev 漂移的做法。这条钉住另一半：
        存储换成 uid 了，Human 视野不许跟着变。
        """
        bundle = self.make_bundle(self.single)
        target = self.migrate_to(bundle, "single")

        listing = json.loads(self.run_cli("edge", "list", target).stdout)["edges"]
        self.assertEqual([("1-1", "1-2")], [(e["from"], e["to"]) for e in listing])
        self.assertEqual(revision_of(self.single), revision_of(target))

    # ── Story 40：显式 ────────────────────────────────

    def test_the_source_file_is_never_rewritten(self):
        before = self.single.read_bytes()
        before_mtime = self.single.stat().st_mtime_ns

        self.migrate_to(self.single, "sqlite")

        self.assertEqual(before, self.single.read_bytes())
        self.assertEqual(before_mtime, self.single.stat().st_mtime_ns)

    def test_an_existing_target_is_refused(self):
        existing = self.workdir / "occupied.sqlite"
        self.run_cli("init", existing, "--storage", "sqlite", "--title", "别覆盖我")
        before = existing.read_bytes()

        result = self.run_cli(
            "migrate", self.single, "--to", "sqlite", "--output", existing, check=False
        )

        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, existing.read_bytes())

    def test_migrating_to_the_same_carrier_is_refused(self):
        result = self.run_cli("migrate", self.single, "--to", "single", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("already", result.stderr)

    def test_an_unknown_target_carrier_is_refused(self):
        result = self.run_cli("migrate", self.single, "--to", "carrier-of-the-month", check=False)

        self.assertNotEqual(0, result.returncode)

    # ── 租约与审计随事实源一起走（zj 决策）────────────────
    #
    # 租约与事件的键是**显示 id**，不是 uid：bundle 的 `_lease_path` 走
    # `safe_node_id`，uid 那种带十六进制的串会被它直接拒掉；single / sqlite 的侧车
    # 也是同一套键。所以这里没有"先查 uid 再认领"这一步——CLI 收的本来就是显示 id。

    def test_leases_and_audit_events_come_across(self):
        self.run_cli("lease", "claim", self.single, "1-2", "--agent", "agent-7")
        source_lease = lease_of(self.single, "1-2")

        sqlite = self.migrate_to(self.single, "sqlite")

        for migrated in (sqlite,):
            carried = lease_of(migrated, "1-2")
            self.assertIsNotNone(carried, migrated)
            self.assertEqual(source_lease["agent_id"], carried["agent_id"])
            self.assertEqual(source_lease["fencing_token"], carried["fencing_token"])
            self.assertEqual(source_lease["expires_at"], carried["expires_at"])

    def test_the_audit_trail_survives_a_full_round_trip(self):
        """single → sqlite → single：事件数量与顺序不许变，时刻也不许被改写成"现在"。

        bundle 弃用 #140 后，最像"真实逃生"的全往返是 single→sqlite→single；这条
        钉住审计事件不丢、过期时刻不被刷成"现在"。
        """
        self.run_cli("lease", "claim", self.single, "1-2", "--agent", "agent-7")
        sqlite = self.migrate_to(self.single, "sqlite")
        back = self.migrate_to(sqlite, "single")

        sidecar = json.loads(Path(f"{back}.leases.json").read_text(encoding="utf-8"))
        self.assertEqual(["lease-claimed"], [e["operation"] for e in sidecar["events"]])
        self.assertEqual(lease_of(self.single, "1-2")["expires_at"],
                         lease_of(back, "1-2")["expires_at"])

    def test_the_carried_lease_still_guards_writes_on_the_new_carrier(self):
        """带过去的租约不能只是"数据搬过去了"，它得还是那把锁。"""
        self.run_cli("lease", "claim", self.single, "1-2", "--agent", "agent-7")

        sqlite = self.migrate_to(self.single, "sqlite")

        stranger = self.run_cli(
            "update", sqlite, "1-2", "--status", "completed",
            "--as-agent", "intruder", "--token", "1", check=False,
        )
        self.assertNotEqual(0, stranger.returncode)
        self.assertIn("E_LEASE_HELD", stranger.stderr)

        holder = self.run_cli(
            "update", sqlite, "1-2", "--status", "completed",
            "--as-agent", "agent-7", "--token", "1",
        )
        self.assertEqual(0, holder.returncode)


class MigrationFunctionTest(MigrationCliTest):
    """缝 2 + 缝 3：函数层与 Human 视野。

    同一个 `MigrationCliTest` 继承过来不是偷懒——这批用例要在完全相同的那张图上
    问"换了 shell 之后还是不是同一份事实源"，图不一样就比不出东西。
    """

    TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def human_view(self, path) -> str:
        """Human 主视图字节：剥掉会正常变化的那两行（数据文件名 / 时间戳）。"""
        result = self.run_cli("section", path)
        lines = [
            line for line in result.stdout.splitlines()
            if not line.startswith("> 数据文件:")
        ]
        return self.TIMESTAMP.sub("<T>", "\n".join(lines))

    def test_detect_storage_agrees_with_the_cli_routing_rule(self):
        b = self.make_bundle(self.single)
        s = self.migrate_to(self.single, "sqlite")

        self.assertEqual("single", detect_storage(self.single))
        self.assertEqual("bundle", detect_storage(b))
        self.assertEqual("sqlite", detect_storage(s))

    def test_write_carrier_refuses_an_existing_target(self):
        existing = self.workdir / "occupied.json"
        existing.write_text("{}", encoding="utf-8")

        for storage in ("single", "sqlite", "bundle"):
            with self.subTest(storage=storage):
                with self.assertRaises(BundleError):
                    write_carrier(existing, storage, {"nodes": {"1": {"id": "1"}}})

    def test_default_output_never_points_back_at_the_source(self):
        """默认的落点不能等于输入——那样"显式性护栏"反而先一步覆盖了事实源。"""
        for storage in CARRIERS:
            with self.subTest(storage=storage):
                target = default_output(self.single, storage)
                self.assertNotEqual(self.single.resolve(), target.resolve())

    def test_export_lease_store_is_uniform_across_the_three_carriers(self):
        single = load_carrier(self.single)
        store = export_lease_store(single)
        self.assertEqual({"leases", "events"}, set(store.keys()))

        bundle = export_lease_store(load_carrier(self.make_bundle(self.single), "bundle"))
        sqlite = export_lease_store(load_carrier(self.migrate_to(self.single, "sqlite"), "sqlite"))
        self.assertEqual(set(store.keys()), set(bundle.keys()))
        self.assertEqual(set(store.keys()), set(sqlite.keys()))

    def test_the_human_view_is_identical_after_every_hop(self):
        """换了 carrier，Human 主视图必须逐字节等于出发那份——**每一种 carrier 都直比**。

        这条之所以敢直接比 bundle（而不是绕道"再迁回 single"）：bundle 的 md 模板
        曾经是另抄一份，缺 `> 当前施工` 行、ROADMAP_TREE 标记与"当前施工点"块，焦点
        决策还丢备注，#117 里与 single 收敛成了同一份模板。在那之前只能比同一套渲染
        器的跳数，现在三家 carrier 的 md 本就该逐字节相同（`test_cross_carrier_render.py`
        不经过迁移也这么断言，那份是这条的前提）。
        """
        bundle = self.make_bundle(self.single)
        sqlite = self.migrate_to(self.single, "sqlite")
        from_bundle = self.migrate_to(bundle, "sqlite")
        from_bundle_single = self.migrate_to(bundle, "single")

        reference = self.human_view(self.single)
        for migrated in (bundle, sqlite, from_bundle, from_bundle_single):
            with self.subTest(migrated=migrated.name):
                self.assertEqual(reference, self.human_view(migrated))

    def test_migrate_to_bundle_is_rejected_at_function_layer(self):
        """缝 2：Python API `migrate()` 也必须拒 `--to bundle`（#140）。

        CLI 只是薄壳，真正的单向护栏在 carrier_migration.migrate 里；这条钉住
        即便绕过 CLI 直接调函数，也造不出新 bundle。
        """
        from carrier_migration import migrate
        with self.assertRaises(ValueError):
            migrate(self.single, "bundle")


if __name__ == "__main__":
    unittest.main()

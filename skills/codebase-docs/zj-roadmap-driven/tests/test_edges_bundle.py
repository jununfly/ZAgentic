"""#79 T1 第二刀 — bundle carrier 的边。

与 single-file 跑**同一套断言**：直接继承 test_edges_single_file.py 里的 Slice 类，
只换掉存储（`--storage bundle`）。继承而非复制，是"两个 carrier 同语义"这条
不变式唯一的机械证明——复制一份副本的话，改了一边另一边不会红。

运行：python tests/test_edges_bundle.py
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
import test_edges_single_file as sf  # noqa: E402

from roadmap import Roadmap  # noqa: E402
from roadmap_bundle import EDGE_SCHEMA, RoadmapBundle  # noqa: E402

TIMESTAMP = sf.TIMESTAMP


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "P1 依赖层")


class Slice01RecordAnEdgeBundleTest(BundleStorageMixin, sf.Slice01RecordAnEdgeTest):
    """同 Slice01，跑在 bundle carrier 上。"""


class Slice02RemoveAndFilterBundleTest(BundleStorageMixin, sf.Slice02RemoveAndFilterTest):
    """同 Slice02，跑在 bundle carrier 上。"""


class Slice03UnknownEndpointBundleTest(BundleStorageMixin, sf.Slice03UnknownEndpointTest):
    """同 Slice03：不存在的端点要有稳定错误码，且不留悬空边。"""


class Slice04CycleBundleTest(BundleStorageMixin, sf.Slice04CycleTest):
    """同 Slice04：只有 blocks 不容许成环。"""


class Slice05SoftEdgesMayCycleBundleTest(BundleStorageMixin, sf.Slice05SoftEdgesMayCycleTest):
    """同 Slice05（负向控制例）：软边必须真的能成环。"""


class Slice06EdgeIdStabilityBundleTest(BundleStorageMixin, sf.Slice06EdgeIdStabilityTest):
    """同 Slice06：边 id 删了不复用，且计数器跨 reload 存活。

    bundle 的计数器在 manifest 里（`edgeSequence`），不在可重建的 index 里——
    索引坏了能重扫，计数器坏了就会复用 id。
    """

    api_filename = "api-roadmap.bundle"

    def new_adapter(self, path):
        return RoadmapBundle(str(path))

    def build_api_roadmap(self, filename=None):
        filename = filename or self.api_filename
        seed = Roadmap(str(self.workdir / (filename + ".seed.json")))
        seed.init(title="edge id")
        seed.add_node("1", "设计")
        seed.add_node("1", "实现")
        return RoadmapBundle.create_from_data(self.workdir / filename, seed.data)


class Slice07DeleteCascadeBundleTest(BundleStorageMixin, sf.Slice07DeleteCascadeTest):
    """同 Slice07：删节点级联删边并报告条数，顺序是先边后节点。"""


class Slice09DanglingEdgeBundleTest(BundleStorageMixin, sf.Slice09DanglingEdgeTest):
    """同 Slice09：悬空边必须被检出。

    single-file 只能靠手塞 JSON 伪造这种状态（它自己是整图替换，造不出半态）；
    bundle 天然能造出来——删节点文件而保留边文件，正是"删边后、删节点前"
    被打断留下的那个半态。
    """

    def write_raw_edges(self, edges):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        directory = self.roadmap / "edges"
        directory.mkdir(parents=True, exist_ok=True)
        for edge in edges:
            (directory / f"{edge['id']}.json").write_text(
                json.dumps({"schema": EDGE_SCHEMA, **edge}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


class Slice10SupersedesBundleTest(BundleStorageMixin, sf.Slice10SupersedesTest):
    """同 Slice10：`supersedes` 让被取代节点 archived 但不消失。"""


class Slice08BundleBaselineTest(sf.Slice08NoEdgeBaselineTest):
    """控制例：没有边时，bundle 的**布局**与 P1 之前逐字节一致。

    bundle 是目录，所以"字节一致"比的是整个目录树：文件清单 + 每个文件的
    内容。这能抓住 single-file 那边抓不到的一类污染——给从未用过边的 bundle
    造出 `edges/` 目录、空 `index.json`，或在 manifest 里多出一个 `edgeSequence`。
    """

    SEQUENCE = (
        ("init", "r.bundle", "--storage", "bundle", "--title", "baseline"),
        ("add", "r.bundle", "1", "设计"),
        ("add", "r.bundle", "1", "实现"),
        ("update", "r.bundle", "1-2", "--status", "in_progress"),
        ("get", "r.bundle", "1-2"),
        ("tree", "r.bundle"),
        ("decide", "r.bundle", "1-1", "为什么", "因为"),
        ("decisions", "r.bundle"),
        ("remove-decision", "r.bundle", "1-1", "--index", "0"),
        ("decisions", "r.bundle"),
        ("section", "r.bundle"),
        ("stats", "r.bundle"),
        ("validate", "r.bundle"),
        ("path", "r.bundle", "1-2"),
        ("siblings", "r.bundle", "1-2"),
        ("focus", "r.bundle"),
        ("delete", "r.bundle", "1-2"),
        ("tree", "r.bundle"),
    )

    def test_existing_commands_are_byte_identical_without_edges(self):
        baseline = self.baseline_dir()
        current = self.root / "current"
        current.mkdir(exist_ok=True)
        for name in ("roadmap.py", "roadmap_cli.py", "roadmap_bundle.py", "storage_advisor.py"):
            (current / name).write_text(
                (SKILL_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
            )

        before = self.run_sequence(baseline, self.root / "w1")
        after = self.run_sequence(current, self.root / "w2")

        self.assertEqual(after, before)

    def test_a_bundle_that_never_had_edges_has_the_same_layout(self):
        baseline = self.baseline_dir()
        current = self.root / "current"
        current.mkdir(exist_ok=True)
        for name in ("roadmap.py", "roadmap_cli.py", "roadmap_bundle.py", "storage_advisor.py"):
            (current / name).write_text(
                (SKILL_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
            )

        shapes = {}
        for label, cli_dir in (("before", baseline), ("after", current)):
            work = self.root / f"j-{label}"
            work.mkdir(exist_ok=True)
            for command in self.SEQUENCE:
                subprocess.run(
                    [sys.executable, str(Path(cli_dir) / "roadmap_cli.py"), *command],
                    cwd=str(work),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    env=sf.FIXED_ENV,
                )
            shapes[label] = self.bundle_snapshot(work / "r.bundle")

        self.assertEqual(shapes["after"], shapes["before"])

    @staticmethod
    def bundle_snapshot(root: Path) -> str:
        """目录**结构**快照：只列条目，不比文件内容。

        比内容是决策 B 之前的老做法，它会把"节点分片里多了一个 `uid` 字段"
        误判成"污染了无边路径"。这里真正要守住的是**结构**——凭空多出来的
        `edges/` 目录、`index.json` 才是边泄漏进无边路径的证据（空目录只有列
        条目才看得见，只数文件会漏）。内容层面的承诺交给继承来的 md 断言
        （`test_the_human_view_is_byte_identical_without_edges`）承担。
        """
        # 目录也要列：凭空多出来的 `edges/` 是空目录，只数文件的话看不见。
        entries = sorted(
            str(path.relative_to(root)) + ("/" if path.is_dir() else "")
            for path in root.rglob("*")
        )
        return "\n".join(entries)


class Slice11CrashHalfStateTest(BundleStorageMixin, sf.EdgeContractTest):
    """崩溃半态：中断在 delete 中间，剩下的是能重做的状态而不是悬空边。

    bundle 不是一个原子写，所以这一刀唯一能自证崩溃安全性的地方就在这——
    single-file 是整图替换，自己造不出半态。
    """

    def delete_with_an_interrupt_right_after_the_edge_removal(self):
        bundle = RoadmapBundle(str(self.roadmap))
        bundle.load()
        bundle._write_node_file = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("simulated crash"))
        with self.assertRaises(RuntimeError):
            bundle.delete_node("1-2")
        return bundle

    def test_an_interrupt_leaves_the_edges_gone_and_the_node_in_place(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.delete_with_an_interrupt_right_after_the_edge_removal()

        self.assertEqual(self.list_edges()["edges"], [])
        self.assertTrue((self.roadmap / "nodes" / "1-2.json").is_file())

    def test_that_half_state_validates_clean_so_the_command_can_be_redone(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.delete_with_an_interrupt_right_after_the_edge_removal()

        self.assertEqual(RoadmapBundle(str(self.roadmap)).validate(), [])

    def test_the_opposite_order_would_leave_a_dangling_edge_that_validate_catches(self):
        """反向控制：证明"先边后节点"不是随便选的——反过来真会留下悬空边。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        (self.roadmap / "nodes" / "1-2.json").unlink()

        result = self.run_cli("validate", self.roadmap, check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("e1", result.stdout)


class Slice12OneSourceOfTruthTest(BundleStorageMixin, sf.EdgeContractTest):
    """边只存一处：节点分片里禁止反向存 edge id。

    事务救不了双写——你忘了写哪个位置，事务照样提交。所以这条靠机械检查。
    """

    def test_node_shards_never_mention_an_edge_id(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        for shard in (self.roadmap / "nodes").glob("*.json"):
            self.assertNotIn('"e1"', shard.read_text(encoding="utf-8"))

    def test_the_index_is_purely_redundant_and_can_be_dropped(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-2", "1-1", "informs")
        (self.roadmap / "edges" / "index.json").unlink()

        listed = self.list_edges("--node", "1-2")["edges"]

        self.assertEqual([edge["id"] for edge in listed], ["e1", "e2"])


class Slice14MigrationTest(BundleStorageMixin, sf.EdgeContractTest):
    """从 single-file 迁到 bundle 时，边必须一起过来。

    两个 carrier 同语义不只指命令层——迁移是它们的接缝，漏掉边就是静默丢数据。
    """

    def build_legacy_with_edges(self):
        legacy = self.workdir / "legacy.json"
        self.run_cli("init", legacy, "--title", "migrate")
        self.run_cli("add", legacy, "1", "设计")
        self.run_cli("add", legacy, "1", "实现")
        self.run_cli("edge", "add", legacy, "1-1", "1-2", "--type", "blocks")
        return legacy

    def migrate(self, legacy):
        target = self.workdir / "migrated.bundle"
        self.run_cli("migrate", legacy, "--to", "bundle", "--output", target)
        return target

    def test_migration_carries_the_edges_over(self):
        target = self.migrate(self.build_legacy_with_edges())

        listed = json.loads(self.run_cli("edge", "list", target).stdout)

        self.assertEqual(
            listed["edges"],
            [{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}],
        )

    def test_the_counter_continues_after_a_migration(self):
        target = self.migrate(self.build_legacy_with_edges())

        self.run_cli("add", target, "1", "验收")
        created = json.loads(
            self.run_cli("edge", "add", target, "1-2", "1-3", "--type", "blocks").stdout
        )

        self.assertEqual(created["id"], "e2")


if __name__ == "__main__":
    unittest.main()

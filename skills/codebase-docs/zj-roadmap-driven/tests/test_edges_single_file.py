"""#79 T1 — single-file carrier 的边（P1 依赖层地基）。

测试缝（2026-09-11 与 zj 确认）：
1. CLI 进程级 —— Agent 的真实入口，唯一能同时钉住错误码与退出码的缝；
2. Roadmap Python API —— 钉住环检测、边 id 稳定性等用 JSON 输出难表达的语义；
3. 控制例 —— 没有边时，既有命令的输出与今天字节一致。

本文件只覆盖 single-file carrier；bundle 跑同一套断言的文件属于 #79 第二刀。

运行：python tests/test_edges_single_file.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import Roadmap  # noqa: E402  （辅缝：Python API）
CLI = SKILL_DIR / "roadmap_cli.py"

E_CYCLE = "E_CYCLE"
E_NODE_NOT_FOUND = "E_NODE_NOT_FOUND"

# metadata.updated 每次运行都变，比对前归一掉。
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

# stats 的 status_counts 由 `set` 推导，键顺序跟着 PYTHONHASHSEED 变。
# 控制例要在两个**不同进程**之间比对输出，不固定种子就会随机失败。
FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}

# 调 git 时要剔掉 NODE_OPTIONS：WorkBuddy 的 safe-delete shim 经它注入 Node
# 子进程，git 清理 stale ref 时会被 shim 把文件移进回收站。
#
# POSIX 上这件事是 `env -u NODE_OPTIONS git ...`，但 `env` 是外部可执行文件，
# Windows 上没有（Git Bash 里的 env 靠 MSYS 提供，CreateProcess 找不到），
# 所以改成构造一个不含该键的 env 字典传下去——两边都能用，且不依赖 shell。
GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}


class EdgeContractTest(unittest.TestCase):
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
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--title", "P1 依赖层")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def add_edge(self, from_id, to_id, edge_type):
        return json.loads(
            self.run_cli("edge", "add", self.roadmap, from_id, to_id, "--type", edge_type).stdout
        )

    def list_edges(self, *extra):
        return json.loads(self.run_cli("edge", "list", self.roadmap, *extra).stdout)

    def get_node(self, node_id):
        return json.loads(self.run_cli("get", self.roadmap, node_id).stdout)


class Slice01RecordAnEdgeTest(EdgeContractTest):
    """能记录任意两个节点之间的依赖，并且这张图能读回来。"""

    def test_a_blocks_edge_is_recorded_and_survives_a_new_process(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(
            self.list_edges()["edges"],
            [{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}],
        )

    def test_an_edge_add_returns_the_edge_it_wrote(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.assertEqual(
            self.add_edge("1-1", "1-2", "informs"),
            {"id": "e1", "from": "1-1", "to": "1-2", "type": "informs"},
        )


class Slice02RemoveAndFilterTest(EdgeContractTest):
    """记下来的依赖能精确删掉，也能按节点查。"""

    def test_removing_one_edge_leaves_the_others_untouched(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        self.run_cli("edge", "remove", self.roadmap, "e1")

        self.assertEqual(
            self.list_edges()["edges"],
            [{"id": "e2", "from": "1-2", "to": "1-3", "type": "blocks"}],
        )

    def test_list_filters_to_a_nodes_in_and_out_edges(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-3", "1-2", "informs")
        self.add_edge("1-2", "1-3", "derives-from")

        listed = self.list_edges("--node", "1-2")["edges"]

        self.assertEqual(
            [e["id"] for e in listed],
            ["e1", "e2", "e3"],
        )


class Slice03UnknownEndpointTest(EdgeContractTest):
    """引用不存在的节点时明确失败，不允许静默留下悬空边。"""

    def test_an_edge_pointing_at_a_missing_node_is_refused_with_a_stable_code(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-1", "9-9", "--type", "blocks", check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(E_NODE_NOT_FOUND, result.stderr)
        self.assertEqual(self.list_edges()["edges"], [])

    def test_a_missing_from_endpoint_is_also_refused(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        result = self.run_cli(
            "edge", "add", self.roadmap, "9-9", "1-1", "--type", "blocks", check=False
        )

        self.assertIn(E_NODE_NOT_FOUND, result.stderr)
        self.assertEqual(self.list_edges()["edges"], [])


class Slice04CycleTest(EdgeContractTest):
    """只有 blocks 不容许成环，且失败信号要让 Agent 能按码分支。"""

    def test_a_three_node_blocks_cycle_is_refused(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-3", "1-1", "--type", "blocks", check=False
        )

        self.assertIn(E_CYCLE, result.stderr)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.list_edges()["edges"]), 2)

    def test_a_two_node_blocks_cycle_is_refused(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-2", "1-1", "--type", "blocks", check=False
        )

        self.assertIn(E_CYCLE, result.stderr)
        self.assertEqual(result.returncode, 1)

    def test_a_node_cannot_block_itself(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-1", "1-1", "--type", "blocks", check=False
        )

        self.assertIn(E_CYCLE, result.stderr)
        self.assertEqual(result.returncode, 1)

    def test_an_unknown_edge_type_is_refused(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-1", "1-2", "--type", "blokcs", check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.list_edges()["edges"], [])


class Slice05SoftEdgesMayCycleTest(EdgeContractTest):
    """负向控制例：informs / derives-from 成环必须真的建得起来。

    防的是"环检测没按类型过滤"——那种实现会让下面这几条建不起来，
    而 Slice04 的测试一条也不会红，因为那边只测了 blocks。
    """

    def test_informs_edges_may_form_a_cycle(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.add_edge("1-1", "1-2", "informs")
        self.add_edge("1-2", "1-1", "informs")

        self.assertEqual(len(self.list_edges()["edges"]), 2)

    def test_derives_from_edges_may_form_a_cycle(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.add_edge("1-1", "1-2", "derives-from")
        self.add_edge("1-2", "1-1", "derives-from")

        self.assertEqual(len(self.list_edges()["edges"]), 2)

    def test_a_soft_cycle_does_not_block_a_hard_edge(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "informs")
        self.add_edge("1-2", "1-1", "informs")

        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(len(self.list_edges()["edges"]), 3)


class Slice06EdgeIdStabilityTest(EdgeContractTest):
    """边 id 删了不复用——下游 #80 要用它解释"被哪几条边挡住了"。

    走 Python API 缝：这条要保证的是 id 生成器的性质，用 CLI 的 JSON 输出
    只能看到结果，看不到"删掉最后一条之后再建"这个关键顺序。
    """

    # bundle carrier 是目录，不能用 .json 后缀（会让人以为是单文件）。
    api_filename = "api-roadmap.json"

    def new_adapter(self, path):
        """返回一个尚未 load 的 carrier 适配器。bundle 那边会覆盖它。"""
        return Roadmap(str(path))

    def build_api_roadmap(self, filename=None):
        filename = filename or self.api_filename
        roadmap = self.new_adapter(self.workdir / filename)
        roadmap.init(title="edge id")
        roadmap.add_node("1", "设计")
        roadmap.add_node("1", "实现")
        return roadmap

    def reload_adapter(self, path):
        adapter = self.new_adapter(path)
        adapter.load()
        return adapter

    def test_a_removed_id_is_not_reused_when_it_was_the_last_one(self):
        r = self.build_api_roadmap()
        r.add_edge("1-1", "1-2", "informs")
        second = r.add_edge("1-2", "1-1", "informs")
        r.remove_edge(second["id"])

        self.assertEqual(r.add_edge("1-1", "1-2", "blocks")["id"], "e3")

    def test_the_counter_survives_a_reload(self):
        r = self.build_api_roadmap()
        r.add_edge("1-1", "1-2", "informs")
        second = r.add_edge("1-2", "1-1", "informs")
        r.remove_edge(second["id"])
        r.save()

        reloaded = self.reload_adapter(self.workdir / self.api_filename)

        self.assertEqual(reloaded.add_edge("1-1", "1-2", "blocks")["id"], "e3")


class Slice07DeleteCascadeTest(EdgeContractTest):
    """删节点时级联删边，并报告删了几条。

    顺序是先删边、后删节点（#79 定）：万一中间被打断，剩下的是"边没了、
    节点还在"这种能重做的半态，而不是悬空边。
    """

    def test_deleting_a_node_removes_the_edges_touching_it_and_reports_the_count(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-2", "1-3", "blocks")
        self.add_edge("1-1", "1-2", "informs")

        result = self.run_cli("delete", self.roadmap, "1-2")

        self.assertIn("Removed edges: 3", result.stdout)
        self.assertEqual(self.list_edges()["edges"], [])

    def test_the_report_breaks_the_count_down_by_type(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-1", "1-2", "informs")

        result = self.run_cli("delete", self.roadmap, "1-2")

        self.assertIn("blocks 1", result.stdout)
        self.assertIn("informs 1", result.stdout)

    def test_cascade_reaches_the_edges_of_descendants(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1-1", "子设计")
        self.add_node("1", "实现")
        self.add_edge("1-1-1", "1-2", "blocks")

        result = self.run_cli("delete", self.roadmap, "1-1")

        self.assertIn("Removed edges: 1", result.stdout)
        self.assertEqual(self.list_edges()["edges"], [])


class Slice08NoEdgeBaselineTest(unittest.TestCase):
    """控制例：没有边时，既有命令的输出与 P1 之前逐字节一致。

    用 `git show main:` 导出改动前的脚本，在两边跑同一串命令，比对输出。
    不硬编码期望值——期望值就是"P1 之前的那份实现"，它不会 stale。
    """

    # 跑得到、且不需要外部 md 文件的命令。render / link 依赖 md 文件，另算。
    SEQUENCE = (
        ("init", "r.json", "--title", "baseline"),
        ("add", "r.json", "1", "设计"),
        ("add", "r.json", "1", "实现"),
        ("update", "r.json", "1-2", "--status", "in_progress"),
        ("get", "r.json", "1-2"),
        ("tree", "r.json"),
        ("decide", "r.json", "1-1", "为什么", "因为"),
        ("decisions", "r.json"),
        ("remove-decision", "r.json", "1-1", "--index", "0"),
        ("decisions", "r.json"),
        ("section", "r.json"),
        ("stats", "r.json"),
        ("validate", "r.json"),
        ("path", "r.json", "1-2"),
        ("siblings", "r.json", "1-2"),
        ("focus", "r.json"),
        ("delete", "r.json", "1-2"),
        ("tree", "r.json"),
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def repo_root():
        """向上找同时含 .git 与 docs/ 的祖先。

        不能硬编码 parents[N]：skill 靠整目录拷贝分发，源在
        skills/<domain>/<skill>/tests/，副本在 <root>/skills/<skill>/tests/，
        同一个索引在两处表示的层级差一级。
        """
        probe = SKILL_DIR
        for _ in range(6):
            if (probe / ".git").exists() and (probe / "docs").is_dir():
                return probe
            probe = probe.parent
        return None

    # 控制例的基线是「P1 边存储落地之前」的那份实现，不是 main 的当前头。
    #
    # 用 `main` 是错的：PR #85/#86 一合进 main，main 上的脚本就等于工作树里的
    # 脚本，控制例变成自己跟自己比，恒真但零信息量——它会在每次"没污染无边
    # 路径"时通过，也会在真的污染了时照样通过。
    #
    # 所以钉死在一个历史 commit 上：a8ee1b9 是 PR #85 的第一父，即 P1 之前
    # 最后一个 main commit。commit 不可变，这个基线不会 stale；要重新校准，
    # 就把 P1/P2……的起点 commit 换进来，并在 commit message 里说明理由。
    BASELINE_REF = "a8ee1b9"
    BASELINE_FILES = ("roadmap.py", "roadmap_cli.py", "roadmap_bundle.py", "storage_advisor.py")

    def baseline_dir(self):
        repo = self.repo_root()
        if repo is None:
            self.skipTest("找不到仓库根（含 .git 与 docs/ 的祖先）")
        rel = SKILL_DIR.relative_to(repo)
        target = self.root / "baseline"
        target.mkdir(exist_ok=True)
        # git 的路径一律用正斜杠：Path 在 Windows 上拼出的是反斜杠，而
        # `git show <rev>:<path>` 的 path 部分是按 / 解析的。
        prefix = rel.as_posix()
        for name in self.BASELINE_FILES:
            result = subprocess.run(
                ["git", "show", f"{self.BASELINE_REF}:{prefix}/{name}"],
                cwd=str(repo),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=GIT_ENV,
            )
            if result.returncode != 0:
                self.skipTest(f"取不到基线 {name}: {result.stderr.strip()}")
            (target / name).write_text(result.stdout, encoding="utf-8")

        self.assert_baseline_is_not_the_current_implementation()
        return target

    def assert_baseline_is_not_the_current_implementation(self):
        """判别力守卫：基线若与当前实现逐字节相同，控制例就是恒真的。

        这不是多虑——用 `main:` 做基线时它就发生过：PR 一合进 main，基线
        自动变成被改动后的自己，于是「没有边时输出与 P1 之前一致」这条断言
        在真的被污染时也通过。一个会无条件通过的控制例比没有控制例更危险，
        因为它给的是假信心。
        """
        target = self.root / "baseline"
        identical = [
            name
            for name in self.BASELINE_FILES
            if (target / name).read_text(encoding="utf-8")
            == (SKILL_DIR / name).read_text(encoding="utf-8")
        ]
        if len(identical) == len(self.BASELINE_FILES):
            self.fail(
                f"基线 {self.BASELINE_REF} 与当前实现完全相同，控制例失去判别力。"
                f"把 BASELINE_REF 指向被测改动之前的那个 commit。"
            )
        return identical

    def run_sequence(self, cli_dir, workdir):
        workdir.mkdir(parents=True, exist_ok=True)
        output = []
        for command in self.SEQUENCE:
            result = subprocess.run(
                [sys.executable, str(Path(cli_dir) / "roadmap_cli.py"), *command],
                cwd=str(workdir),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=FIXED_ENV,
            )
            text = f"$ {result.returncode}\n{result.stdout}{result.stderr}".replace(
                str(workdir), "<W>"
            )
            output.append(TIMESTAMP.sub("<T>", text))
        return "\n".join(output)

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

    def test_a_roadmap_that_never_had_edges_has_the_same_json_bytes(self):
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
                    env=FIXED_ENV,
                )
            shapes[label] = TIMESTAMP.sub("<T>", (work / "r.json").read_text(encoding="utf-8"))

        self.assertEqual(shapes["after"], shapes["before"])


class Slice09DanglingEdgeTest(EdgeContractTest):
    """悬空边必须被检出，而不是静默参与调度。

    手工往 JSON 里塞边来模拟：外部手改文件，或 bundle carrier 上"删节点后、
    删边前"崩溃留下的半态（single-file 写是整图替换，自己造不出这种状态）。
    """

    def write_raw_edges(self, edges):
        roadmap = Roadmap(str(self.roadmap))
        roadmap.init(title="dangling")
        roadmap.add_node("1", "设计")
        roadmap.add_node("1", "实现")
        roadmap.data["edges"] = edges
        roadmap.save()

    def test_validate_reports_an_edge_pointing_at_a_missing_node(self):
        self.write_raw_edges([{"id": "e1", "from": "1-1", "to": "9-9", "type": "blocks"}])

        result = self.run_cli("validate", self.roadmap, check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("e1", result.stdout)
        self.assertIn("9-9", result.stdout)

    def test_a_healthy_edge_keeps_validate_clean(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(self.run_cli("validate", self.roadmap).stdout.strip(), "Valid.")


class Slice10SupersedesTest(EdgeContractTest):
    """`supersedes` 保留历史：被取代的节点转为 archived，但不从图里消失。

    archived 是节点上的一个事实标记，不是 status——"completed 且 archived"
    （做完了但被取代）是合理组合，塞进 status 会丢掉"完成过"这个信息。
    """

    def test_a_supersedes_edge_archives_the_superseded_node(self):
        self.init_roadmap()
        self.add_node("1", "旧方案")
        self.add_node("1", "新方案")

        self.add_edge("1-2", "1-1", "supersedes")

        self.assertTrue(self.get_node("1-1")["archived"])
        self.assertNotIn("archived", self.get_node("1-2"))

    def test_the_superseded_node_and_its_history_stay_readable(self):
        self.init_roadmap()
        self.add_node("1", "旧方案")
        self.add_node("1", "新方案")
        self.run_cli("decide", self.roadmap, "1-1", "为什么旧", "因为当时")

        self.add_edge("1-2", "1-1", "supersedes")

        node = self.get_node("1-1")
        self.assertEqual(node["label"], "旧方案")
        self.assertEqual(len(node["decisions"]), 1)

    def test_archiving_leaves_the_status_alone(self):
        self.init_roadmap()
        self.add_node("1", "旧方案")
        self.add_node("1", "新方案")
        self.run_cli("update", self.roadmap, "1-1", "--status", "completed")

        self.add_edge("1-2", "1-1", "supersedes")

        self.assertEqual(self.get_node("1-1")["status"], "completed")
        self.assertTrue(self.get_node("1-1")["archived"])


if __name__ == "__main__":
    unittest.main()

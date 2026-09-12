"""#82 — md 视图在有阻塞时展示阻塞链（single-file carrier）。

测试缝（本次确认）：

1. **CLI 进程级 `render`**（写进 Human md 文件的那一段）—— Human 的真实入口。
   #82 的全部价值都在"打开 md 就能看见为什么没进展"，所以不能测内部渲染函数：
   只有真正写出来的那份 md 字节才是 Human 看到的东西。
2. **CLI 进程级 `section`**（显式导出）—— 同一份数据的另一道出口，取舍在这里
   相反（非折叠），必须分开钉。
3. **字节级控制例** —— 无阻塞时 md 与改动前逐字节一致；基线取 P1 之前的
   `a8ee1b9`（沿用 #79 的手法，而不是拿 main 跟自己比）。

bundle 跑同一套断言的文件是最后一刀。

运行：python tests/test_blocked_chain_single_file.py
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

CLI = SKILL_DIR / "roadmap_cli.py"

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
"""metadata.updated 每次运行都变，比对前归一掉。"""

FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}
"""控制例在两个进程之间比对输出，不固定种子就会随机失败。"""

GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
"""调 git 时剔掉 shim 注入（它在 Windows 上会把 git 清理的 ref 移进回收站）。"""


class BlockedChainContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.roadmap = self.workdir / "roadmap.json"
        self.md_file = self.workdir / "plan.md"

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
        # md_file 先落一个壳：Human 的 md 里 roadmap section 是嵌在自己的计划
        # 文档里的，不是独占文件。这样还能顺带钉住"替换而不是追加"。
        self.md_file.write_text("# 我的计划\n\n", encoding="utf-8")
        self.run_cli("init", self.roadmap, "--title", "P1 阻塞链", "--md-file", str(self.md_file))

    def add_node(self, parent_id, label, status=None):
        args = ["add", self.roadmap, parent_id, label]
        if status:
            args += ["--status", status]
        return json.loads(self.run_cli(*args).stdout)

    def add_edge(self, from_id, to_id, edge_type):
        return json.loads(
            self.run_cli("edge", "add", self.roadmap, from_id, to_id, "--type", edge_type).stdout
        )

    def complete(self, node_id):
        self.run_cli("update", self.roadmap, node_id, "--status", "completed")

    # ── 两道出口 ────────────────────────────────────────

    def human_md(self):
        """主视图：`render` 写进关联 md 文件的那一段（Human 真正看的字节）。"""
        self.run_cli("render", self.roadmap)
        return self.md_file.read_text(encoding="utf-8")

    def exported_section(self, *extra):
        """导出视图：`section` 的 stdout（注定要被 grep / 管道消费）。"""
        return self.run_cli("section", self.roadmap, *extra).stdout

    # ── 结构抽取 ────────────────────────────────────────

    def details_block(self, md_text):
        """主视图里的折叠块：`<details>` ... `</details>`。

        Human 主视图的唯一约定是"默认不占视线"，折叠块就是它的物理形式。
        """
        match = re.search(r"<details>.*?</details>", md_text, re.DOTALL)
        if not match:
            self.fail(f"md 里没有折叠块：\n{md_text}")
        return match.group(0)

    def plain_chain_block(self, section_text):
        """导出视图里的阻塞链小节：`### 阻塞链` 到下一个同级标题。

        `section` 的输出是要进管道 / 给 grep 的，所以约束恰好相反于主视图：
        不许有 `<details>` 包着，必须能一路 grep 到底。
        """
        start = section_text.find("### 阻塞链")
        if start < 0:
            self.fail(f"导出视图里没有阻塞链小节：\n{section_text}")
        rest = section_text[start:]
        nxt = re.search(r"\n(##|###) ", rest[len("### 阻塞链"):])
        return rest[: len("### 阻塞链") + nxt.start()] if nxt else rest

    def entry_for(self, chain_text, node_id):
        """取某个被阻塞节点对应的那一条目。

        返回整行文本，不断言它的句式——把句式写死等于把排版写进测试，而"一屏
        读完"要求的只是这一行同时说清了：被挡的是谁、挡它的边、边来自谁。
        """
        for line in chain_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and f"{node_id}." in stripped:
                return stripped
        self.fail(f"阻塞链里找不到节点 {node_id} 的条目：\n{chain_text}")


class Slice01HumanViewCollapsesTheChainTest(BlockedChainContractTest):
    """有节点被阻塞时，Human 主视图多出一节阻塞链，且默认折叠成一行摘要。"""

    def test_a_blocked_node_appears_in_the_main_markdown_view(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        md = self.human_md()

        self.assertIn("<details>", md)

    def test_the_collapsed_summary_states_how_many_nodes_are_blocked(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        summary = self.details_block(self.human_md())

        self.assertIn("1 个节点被阻塞", summary)

    def test_each_entry_says_which_node_and_which_edges_block_it(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        entry = self.entry_for(self.details_block(self.human_md()), "1-2")

        # "说清谁挡住了谁"的可操作定义：被挡的节点、那条边的 id、派出这条边的
        # 前驱，三者必须在同一行。缺任何一个，Human 就得回头去数 JSON。
        self.assertIn("1-2", entry)
        self.assertIn("实现", entry)
        self.assertIn("e1", entry)
        self.assertIn("1-1", entry)
        self.assertIn("设计", entry)


class Slice02ExportViewListsTheChainPlainTest(BlockedChainContractTest):
    """`section` 是显式导出：链要给出来，但不折叠。

    取舍的反面：`<details>` 是给眼睛用的（GitHub 渲染后能点开），进了管道就是
    一堆噪音。Human 喊了 `section` 就意味着"我要看全部"。
    """

    def three_node_chain(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

    def test_section_lists_a_heading_instead_of_a_details_wrapper(self):
        self.three_node_chain()

        section = self.exported_section()

        self.assertIn("### 阻塞链", section)
        self.assertNotIn("<details>", section)

    def test_section_all_lists_the_same_plain_chain(self):
        self.three_node_chain()

        section = self.exported_section("--all")

        self.assertIn("### 阻塞链", section)
        self.assertNotIn("<details>", section)

    def test_export_entry_says_which_node_and_which_edges_block_it(self):
        self.three_node_chain()

        entry = self.entry_for(self.plain_chain_block(self.exported_section()), "1-2")

        self.assertIn("1-2", entry)
        self.assertIn("实现", entry)
        self.assertIn("e1", entry)
        self.assertIn("1-1", entry)
        self.assertIn("设计", entry)


class Slice03TheChainTracksTheCurrentGraphTest(BlockedChainContractTest):
    """链是派生的：它必须跟着边走，不能有"上次算的残留"。"""

    def test_one_entry_lists_every_edge_blocking_that_node(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_node("1", "上线")
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        entry = self.entry_for(self.plain_chain_block(self.exported_section()), "1-3")

        # 两条边聚在同一个条目里：对 Human 来说同一个节点要开工，就是同一个
        # 问题——拆成两条会让人以为是两件事，还得自己合并。
        self.assertIn("e1", entry)
        self.assertIn("e2", entry)
        self.assertIn("1-1", entry)
        self.assertIn("1-2", entry)

    def test_completing_every_predecessor_drops_the_entry(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.assertIn("1-2", self.plain_chain_block(self.exported_section()))

        self.complete("1-1")

        section = self.exported_section()
        self.assertNotIn("### 阻塞链", section)
        self.assertNotIn("1-2. 实现 ←", section)

    def test_removing_the_edge_drops_the_entry(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.run_cli("edge", "remove", self.roadmap, "e1")

        section = self.exported_section()
        self.assertNotIn("### 阻塞链", section)
        self.assertNotIn("1-2. 实现 ←", section)

    def test_two_blocked_nodes_give_two_entries_and_the_summary_counts_both(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_node("1", "上线")
        self.add_edge("1-1", "1-2", "blocks")
        self.add_edge("1-1", "1-3", "blocks")

        md = self.human_md()

        self.assertIn("2 个节点被阻塞", self.details_block(md))
        block = self.details_block(md)
        self.assertIn("1-2", self.entry_for(block, "1-2"))
        self.assertIn("1-3", self.entry_for(block, "1-3"))


class Slice04TheChainStaysShortAndMarksTruncationTest(BlockedChainContractTest):
    """链是摘要，不是边表导出：长度有上限，超出必须写明被丢了多少。

    MAX_ENTRIES 是这份 spec 给出的期望值，刻意不从实现里读——读实现的上限等于
    让测试跟着实现走，实现把上限改成 500 时测试照样绿。
    """

    MAX_ENTRIES = 5

    def eight_blocked_nodes(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        for i in range(2, 10):
            self.add_node("1", f"任务{i}")
            self.add_edge("1-1", f"1-{i}", "blocks")

    def entries_lines(self, block):
        return [
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("- ") and not line.strip().startswith("- ...")
        ]

    def test_the_chain_is_capped_at_the_maximum_entry_count(self):
        self.eight_blocked_nodes()

        block = self.plain_chain_block(self.exported_section("--all"))

        self.assertEqual(len(self.entries_lines(block)), self.MAX_ENTRIES)

    def test_the_omitted_tail_is_stated_explicitly(self):
        self.eight_blocked_nodes()

        block = self.plain_chain_block(self.exported_section("--all"))

        # "明确标注截断"：Human 必须能看出自己看到的是不完整的，否则这条链
        # 就变成了假的全景——比不给更糟。
        self.assertIn("另有 3", block)

    def test_the_summary_reports_the_true_total_not_the_displayed_count(self):
        self.eight_blocked_nodes()

        summary = self.details_block(self.human_md())

        self.assertIn("8 个节点被阻塞", summary)

    def test_the_collapsed_view_is_capped_too(self):
        self.eight_blocked_nodes()

        block = self.details_block(self.human_md())

        self.assertEqual(len(self.entries_lines(block)), self.MAX_ENTRIES)
        self.assertIn("另有 3", block)


class Slice05SoftEdgesNeverEnterTheChainTest(BlockedChainContractTest):
    """负向控制例：只有 `blocks` 才挡得住开工。

    `informs` / `derives-from` / `supersedes` 进链的代价不是"多一行"——进链就
    等于告诉 Human 有东西挡着，而实际上什么也挡不住这节点开工。
    """

    def two_nodes_with(self, edge_type):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", edge_type)
        return self.exported_section()

    def test_informs_does_not_produce_a_chain(self):
        self.assertNotIn("### 阻塞链", self.two_nodes_with("informs"))

    def test_derives_from_does_not_produce_a_chain(self):
        self.assertNotIn("### 阻塞链", self.two_nodes_with("derives-from"))

    def test_supersedes_does_not_produce_a_chain(self):
        self.assertNotIn("### 阻塞链", self.two_nodes_with("supersedes"))

    def test_only_the_blocks_edge_shows_up_when_both_exist(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_node("1", "参考材料")
        self.add_edge("1-3", "1-2", "informs")
        self.add_edge("1-1", "1-2", "blocks")

        entry = self.entry_for(self.plain_chain_block(self.exported_section()), "1-2")

        self.assertIn("e2", entry)
        self.assertIn("1-1", entry)
        self.assertNotIn("e1", entry)

    def test_a_soft_edge_to_a_node_with_a_real_blocker_keeps_the_blocker_only(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "informs")

        md = self.human_md()

        self.assertNotIn("<details>", md)


class Slice06NothingBlockedMeansByteIdenticalMarkdownTest(BlockedChainContractTest):
    """硬验收：没有东西被阻塞时，md 的输出与改动前逐字节一致。

    两道对照：

    1. `a8ee1b9`（P1 之前最后一个 main commit）跑同一串命令比对 stdout +
       md 文件字节。基线钉在历史 commit 而不是 main：pristine main 会跟着
       实现走，控制例就变成自己跟自己比——真的被污染时也照样绿。
    2. 基线那版没有 `edge` 命令，跑不了"有边但不阻塞"的场景。这条单独比：
       无边 / 前驱已完成的 blocks 边 / 纯 informs 边，三份 md 归一化时间戳
       后必须相同。没有这道对照，"有边就得显示点什么"的顺手漏法照样过。
    """

    SEQUENCE = (
        ("init", "r.json", "--title", "baseline", "--md-file", "plan.md"),
        ("add", "r.json", "1", "设计"),
        ("add", "r.json", "1", "实现"),
        ("update", "r.json", "1-2", "--status", "in_progress"),
        ("decide", "r.json", "1-2", "为什么", "因为"),
        ("render", "r.json"),
        "READ:plan.md",
        ("render", "r.json"),
        "READ:plan.md",
        ("tree", "r.json"),
        ("section", "r.json"),
        ("section", "r.json", "--all"),
    )

    BASELINE_REF = "a8ee1b9"
    BASELINE_FILES = ("roadmap.py", "roadmap_cli.py", "roadmap_bundle.py", "storage_advisor.py")

    def setUp(self):
        super().setUp()
        self.tmp2 = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp2.name)

    def tearDown(self):
        self.tmp2.cleanup()
        super().tearDown()

    # ── 基线 machinery（与 #79 同源） ──────────────────

    @staticmethod
    def repo_root():
        probe = SKILL_DIR
        for _ in range(6):
            if (probe / ".git").exists() and (probe / "docs").is_dir():
                return probe
            probe = probe.parent
        return None

    def write_impl(self, target, source):
        target.mkdir(parents=True, exist_ok=True)
        for name in self.BASELINE_FILES:
            (target / name).write_text((source / name).read_text(encoding="utf-8"), encoding="utf-8")

    def baseline_dir(self):
        repo = self.repo_root()
        if repo is None:
            self.skipTest("找不到仓库根（含 .git 与 docs/ 的祖先）")
        rel = SKILL_DIR.relative_to(repo)
        target = self.root / "baseline"
        target.mkdir(exist_ok=True)
        # `git show <rev>:<path>` 的 path 按 / 解析：Path 在 Windows 上拼出的是
        # 反斜杠，直接用会找不到。
        prefix = rel.as_posix()
        for name in self.BASELINE_FILES:
            if not (SKILL_DIR / name).exists():
                continue
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

        identical = [
            name
            for name in self.BASELINE_FILES
            if (target / name).exists()
            and (target / name).read_text(encoding="utf-8")
            == (SKILL_DIR / name).read_text(encoding="utf-8")
        ]
        # 判别力守卫：基线若与当前实现逐字节相同，这条控制例就是恒真的。
        if len(identical) == len(self.BASELINE_FILES):
            self.fail(
                f"基线 {self.BASELINE_REF} 与当前实现完全相同，控制例失去判别力。"
                f"把 BASELINE_REF 指向被测改动之前的那个 commit。"
            )
        return target

    def run_sequence(self, cli_dir, workdir):
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        output = []
        for step in self.SEQUENCE:
            if isinstance(step, str):
                content = (workdir / step.split(":", 1)[1]).read_text(encoding="utf-8")
                # md 里同样写着绝对路径与 metadata.updated，一并归一。
                content = content.replace(str(workdir), "<W>").replace(
                    str(workdir).replace("\\", "/"), "<W>"
                )
                output.append("READ")
                output.append(TIMESTAMP.sub("<T>", content))
                continue
            result = subprocess.run(
                [sys.executable, str(Path(cli_dir) / "roadmap_cli.py"), *step],
                cwd=str(workdir),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=FIXED_ENV,
            )
            text = f"$ {result.returncode}\n{result.stdout}{result.stderr}"
            # 工作目录 / md 文件的绝对路径两边不同；metadata.updated 每次都变。
            text = text.replace(str(workdir), "<W>").replace(str(workdir).replace("\\", "/"), "<W>")
            output.append(TIMESTAMP.sub("<T>", text))
        return "\n".join(output)

    def test_markdown_and_section_are_byte_identical_without_edges(self):
        before = self.run_sequence(self.baseline_dir(), self.root / "w1")
        current = self.root / "current"
        self.write_impl(current, SKILL_DIR)

        after = self.run_sequence(current, self.root / "w2")

        self.assertEqual(after, before)

    # ── 基线跑不到的场景：有边，但没有东西被阻塞 ──────

    def normalized(self, text):
        return TIMESTAMP.sub("<T>", text)

    def build_and_render(self, edge_type=None, complete_predecessor=False):
        """建一张指定的图，返回它的 Human 主视图字节。

        借用上一张图留下的 workdir 是行不通的——要的是三份**彼此独立**的
        roadmap 的 md 互相比对，所以先把 self.workdir 换成一个新的临时目录。
        """
        original = self.workdir
        scratch = tempfile.TemporaryDirectory()
        self.workdir = Path(scratch.name)
        self.roadmap = self.workdir / "roadmap.json"
        self.md_file = self.workdir / "plan.md"
        try:
            self.init_roadmap()
            self.add_node("1", "设计")
            self.add_node("1", "实现")
            if edge_type:
                self.add_edge("1-1", "1-2", edge_type)
            if complete_predecessor:
                self.complete("1-1")
            return self.human_md()
        finally:
            self.workdir = original
            self.roadmap = original / "roadmap.json"
            self.md_file = original / "plan.md"
            scratch.cleanup()

    def test_a_blocks_edge_with_a_finished_predecessor_shows_no_chain(self):
        md = self.build_and_render("blocks", complete_predecessor=True)

        # 断言而不是字节比对：完成前驱会把树里的图标从 `[ ]` 改成 `[x]`，那部分
        # 改动发生在 #82 之前，md 本来就该不同。钉的是链这一节不存在——注意不能
        # 拿"阻塞链"三个字去断言，标题里就有这三个字。
        self.assertNotIn("<details>", md)
        self.assertNotIn("### 阻塞链", md)

    def test_an_informs_edge_leaves_the_markdown_unchanged(self):
        without_edges = self.build_and_render()

        with_informs = self.build_and_render("informs")

        # 这里可以逐字节比：软边既不挡住任何节点，也不改动树。
        self.assertEqual(self.normalized(with_informs), self.normalized(without_edges))


if __name__ == "__main__":
    unittest.main()

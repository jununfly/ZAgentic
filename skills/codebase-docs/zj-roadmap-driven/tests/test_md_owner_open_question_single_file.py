"""#115 — md 视图：owner 列 + open question 队列（single-file carrier）。

测试缝（与 #82 同源）：Human 真实看到的是 `render` 写进关联 md 的那份字节，
`section` 是同一份数据的非折叠出口。两个 carrier 跑**同一套断言**（bundle 文件
继承）。只测有状态时才出现的内容——无租约、无待决问题时 md 必须与改动前逐字节
一致，那是 §6 护栏 3（新视图元素默认不进 md）的硬验收。

运行：python tests/test_md_owner_open_question_single_file.py
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
FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}


class MdOwnerOqContractTest(unittest.TestCase):
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
            env=FIXED_ENV,
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.md_file.write_text("# 我的计划\n\n", encoding="utf-8")
        self.run_cli("init", self.roadmap, "--title", "P2 md 视图", "--md-file", str(self.md_file))

    def add_node(self, parent_id, label, status=None):
        args = ["add", self.roadmap, parent_id, label]
        if status:
            args += ["--status", status]
        return json.loads(self.run_cli(*args).stdout)

    def claim_lease(self, node_id, agent, device=""):
        args = ["lease", "claim", self.roadmap, node_id, "--agent", agent]
        if device:
            args += ["--device", device]
        return self.run_cli(*args)

    def release_lease(self, node_id, agent):
        return self.run_cli("lease", "release", self.roadmap, node_id, "--agent", agent)

    def fail_node(self, node_id, error, agent="a7", max_attempts=None):
        args = ["fail", self.roadmap, node_id, "--error", error,
                "--as-agent", agent, "--token", "1"]
        if max_attempts is not None:
            args += ["--max-attempts", str(max_attempts)]
        return self.run_cli(*args)

    def human_md(self):
        """主视图：`render` 写进关联 md 文件的那一段（Human 真正看的字节）。"""
        self.run_cli("render", self.roadmap)
        return self.md_file.read_text(encoding="utf-8")

    def exported_section(self, *extra):
        """导出视图：`section` 的 stdout。"""
        return self.run_cli("section", self.roadmap, *extra).stdout

    # ── 结构抽取 ────────────────────────────────────────

    def owner_line(self, md, node_id):
        """返回含 `node_id.` 且带 `owner:` 的那一行（没有 owner 时返回 None）。"""
        for line in md.splitlines():
            stripped = line.strip()
            if f"{node_id}." in stripped and "owner:" in stripped:
                return stripped
        return None

    def oq_block(self, md):
        """抽取待决问题那一节：Light 是 `<details>` 块，Export 是 `### 待决问题`。"""
        for m in re.finditer(r"<details>.*?</details>", md, re.DOTALL):
            if "待决问题" in m.group(0):
                return m.group(0)
        start = md.find("### 待决问题")
        if start < 0:
            return ""
        rest = md[start:]
        nxt = re.search(r"\n(##|###) ", rest[len("### 待决问题"):])
        return rest[: len("### 待决问题") + nxt.start()] if nxt else rest

    def oq_entry_for(self, block, node_id):
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and f"{node_id}." in stripped:
                return stripped
        self.fail(f"待决问题里找不到节点 {node_id}：\n{block}")


class Slice01OpenQuestionQueueAppearsInHumanViewTest(MdOwnerOqContractTest):
    """失败达阈值挂起 open question 后，Human 主视图多出一节待决问题，且折叠。"""

    def _escalate(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        # fail 走租约守卫：先 claim（制造 owner），挂起后 release 清掉 owner，
        # 这样本 Slice 只验 open question，不被 owner 列干扰。
        self.claim_lease("1-2", "a7")
        self.fail_node("1-2", "boom", max_attempts=1)
        self.release_lease("1-2", "a7")

    def test_open_question_shows_as_a_collapsed_section(self):
        self._escalate()
        md = self.human_md()
        self.assertIn("<details>", md)
        self.assertIn("待决问题", md)

    def test_entry_names_the_node_and_the_question(self):
        self._escalate()
        entry = self.oq_entry_for(self.oq_block(self.human_md()), "1-2")
        # "说清等谁决策"的可操作定义：节点、它的标签、失败原因、谁挂起的、试了几次
        # 必须同在一行——缺任何一项 Human 都得回头翻 JSON。
        self.assertIn("1-2", entry)
        self.assertIn("实现", entry)
        self.assertIn("boom", entry)
        self.assertIn("a7", entry)
        self.assertIn("attempts 1", entry)


class Slice02OpenQuestionQueuePlainInExportTest(MdOwnerOqContractTest):
    """`section` 是显式导出：待决问题要给出来，但不折叠（进管道必须能 grep）。"""

    def _escalate(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.claim_lease("1-2", "a7")
        self.fail_node("1-2", "boom", max_attempts=1)
        self.release_lease("1-2", "a7")

    def test_section_lists_open_questions_plain(self):
        self._escalate()
        section = self.exported_section()
        self.assertIn("### 待决问题", section)
        self.assertNotIn("<details>", section)

    def test_export_entry_names_node_and_question(self):
        self._escalate()
        entry = self.oq_entry_for(self.oq_block(self.exported_section()), "1-2")
        self.assertIn("1-2", entry)
        self.assertIn("实现", entry)
        self.assertIn("boom", entry)
        self.assertIn("a7", entry)


class Slice03NoOpenQuestionMeansNoSectionTest(MdOwnerOqContractTest):
    """硬验收（§6 护栏 3）：没有任何待决问题时，md 里不能出现待决问题那一节。"""

    def test_no_failed_node_shows_no_open_question_section(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        md = self.human_md()
        self.assertNotIn("待决问题", md)
        self.assertNotIn("### 待决问题", md)


class Slice04OwnerColumnInTreeTest(MdOwnerOqContractTest):
    """owner 列：持有未过期租约的节点，其树行末尾标出 agent/device。"""

    def test_leased_node_shows_owner_in_tree_line(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.claim_lease("1-2", "a7", "win-rog")

        line = self.owner_line(self.human_md(), "1-2")
        self.assertIsNotNone(line)
        self.assertIn("owner: a7/win-rog", line)

    def test_owner_appears_in_export_tree_too(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.claim_lease("1-2", "a7", "win-rog")

        line = self.owner_line(self.exported_section(), "1-2")
        self.assertIsNotNone(line)
        self.assertIn("owner: a7/win-rog", line)

    def test_unleased_node_has_no_owner_suffix(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        md = self.human_md()
        for line in md.splitlines():
            if "1-2." in line:
                self.assertNotIn("owner:", line)


class Slice05ExpiredLeaseShowsNoOwnerTest(MdOwnerOqContractTest):
    """负向控制例：僵尸租约（过期但未被清理）不能当成持有者显示在 md 里。

    侧车直接用 fixture 写一份过期租约——CLI 的 claim 用真实时间，无法造出
    "已过期"状态，但过期租约真实存在（崩溃的 agent 不会来 release），md 必须忽略它。
    """

    def write_expired_lease(self, node_id, agent, device):
        # 租约字段是 epoch 浮点（new_lease 把 now+ttl 落盘）；这里 expires_at=1.0
        # 远早于现在 → 必然过期。字段形状必须与真实 claim 落盘的一致，否则测的是
        # 一份不存在的租约。
        store = {
            "leases": {
                node_id: {
                    "node_uid": node_id,
                    "agent_id": agent,
                    "device_id": device,
                    "fencing_token": 1,
                    "claimed_at": 1.0,
                    "heartbeat_at": 1.0,
                    "expires_at": 1.0,
                    "ttl": 300,
                }
            },
            "events": [],
        }
        sidecar = self.roadmap.with_suffix(self.roadmap.suffix + ".leases.json")
        sidecar.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_expired_lease_is_not_shown_as_owner(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.write_expired_lease("1-2", "a7", "win-rog")

        md = self.human_md()
        for line in md.splitlines():
            if "1-2." in line:
                self.assertNotIn("owner:", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)

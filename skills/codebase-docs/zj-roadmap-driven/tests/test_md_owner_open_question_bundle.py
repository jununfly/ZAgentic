"""#115 — bundle carrier 的 md 视图：owner 列 + open question 队列。

与 single-file 跑**同一套断言**：继承 test_md_owner_open_question_single_file.py
里的 Slice 类，只换存储（`--storage bundle`）。继承而非复制是"两个 carrier 渲染
一致"这条验收唯一的机械证明——复制一份副本的话，改了单边另一边不会红。

Slice05 的过期租约 fixture 在 single-file 里写的是 `<json>.leases.json` 侧车，
bundle 把租约落进 `leases/<node_uid>.json`，所以这里覆盖 `write_expired_lease`
写进 bundle 真实路径——否则 bundle 那边不会有任何租约，测试变成假绿。

Slice06 是跨 carrier 字节比对：同一张图在两个存储上各渲染一次，直接比 owner 树行
和待决问题节。一处拼 `- `、另一处漏个空格，断言照样全绿，而 Human 看到的是两份
不一样的 md——这条对照把"渲染一致"从"各自满足契约"升级成"输出逐字节相等"。

运行：python tests/test_md_owner_open_question_bundle.py
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

import test_md_owner_open_question_single_file as sf  # noqa: E402


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
            "P2 md 视图",
            "--md-file",
            str(self.md_file),
        )


class Slice01OpenQuestionQueueAppearsInHumanViewBundleTest(
    BundleStorageMixin, sf.Slice01OpenQuestionQueueAppearsInHumanViewTest
):
    """同 Slice01：Human 主视图里的折叠待决问题队列。"""


class Slice02OpenQuestionQueuePlainInExportBundleTest(
    BundleStorageMixin, sf.Slice02OpenQuestionQueuePlainInExportTest
):
    """同 Slice02：`section` 非折叠。"""


class Slice03NoOpenQuestionMeansNoSectionBundleTest(
    BundleStorageMixin, sf.Slice03NoOpenQuestionMeansNoSectionTest
):
    """同 Slice03（硬验收）：没有任何待决问题时 md 里不能出现待决问题节。"""


class Slice04OwnerColumnInTreeBundleTest(
    BundleStorageMixin, sf.Slice04OwnerColumnInTreeTest
):
    """同 Slice04：owner 列出现在树行末尾。"""


class Slice05ExpiredLeaseShowsNoOwnerBundleTest(
    BundleStorageMixin, sf.Slice05ExpiredLeaseShowsNoOwnerTest
):
    """同 Slice05（负向控制例）：僵尸租约不能当成持有者显示在 md 里。

    bundle 把租约落进 `leases/<node_uid>.json`，用真实 uid 写（uid 可能 != 显示 id）。
    """

    def write_expired_lease(self, node_id, agent, device):
        node = json.loads(self.run_cli("get", self.roadmap, node_id).stdout)
        uid = node.get("uid") or node_id
        lease = {
            "node_uid": uid,
            "agent_id": agent,
            "device_id": device,
            "fencing_token": 1,
            "claimed_at": 1.0,
            "heartbeat_at": 1.0,
            "expires_at": 1.0,
            "ttl": 300,
        }
        leases_dir = self.roadmap / "leases"
        leases_dir.mkdir(parents=True, exist_ok=True)
        (leases_dir / f"{uid}.json").write_text(
            json.dumps(lease, ensure_ascii=False, indent=2), encoding="utf-8"
        )


class Slice06BothCarriersRenderTheSameTest(BundleStorageMixin, sf.MdOwnerOqContractTest):
    """"两个 carrier 渲染结果一致"这条验收的直接证明。"""

    def build_state(self, init):
        self.md_file.write_text("# 我的计划\n\n", encoding="utf-8")
        init()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.claim_lease("1-2", "a7", "win-rog")
        self.fail_node("1-2", "boom", max_attempts=1)
        self.release_lease("1-2", "a7")

    def on_single_file(self):
        self.roadmap = self.workdir / "roadmap.json"
        try:
            self.build_state(
                lambda: self.run_cli(
                    "init", self.roadmap, "--title", "P2 md 视图",
                    "--md-file", str(self.md_file),
                )
            )
            return self.human_md(), self.exported_section()
        finally:
            self.roadmap = self.workdir / "roadmap.bundle"

    def on_bundle(self):
        self.build_state(self.init_roadmap)
        return self.human_md(), self.exported_section()

    def test_owner_line_matches_across_carriers(self):
        sf_human, _ = self.on_single_file()
        bd_human, _ = self.on_bundle()
        self.assertEqual(
            self.owner_line(bd_human, "1-2"),
            self.owner_line(sf_human, "1-2"),
        )

    def test_open_question_plain_section_matches_across_carriers(self):
        _, sf_section = self.on_single_file()
        _, bd_section = self.on_bundle()
        self.assertEqual(self.oq_block(bd_section), self.oq_block(sf_section))


if __name__ == "__main__":
    unittest.main()

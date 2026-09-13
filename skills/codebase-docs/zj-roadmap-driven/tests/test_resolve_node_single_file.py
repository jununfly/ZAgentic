"""#105 S3 — 命令接受 uid（或显示 id）。single-file carrier。

测试缝：CLI 进程级（每条命令新进程，证明 uid 解析落盘且稳定）。
核心契约：
- `get <uid>` ≡ `get <display-id>`（指向同一节点，输出一致）
- uid 与显示 id 命名空间不重叠（uid 含 hex 字母 a-f，显示 id 只有数字与 -）
- 传错 ref 有清晰报错，不会静默误命中
- 基线守卫不红（uid 不进 md，已由 S2 处理）

本文件覆盖 single-file carrier；bundle 跑同一套断言的文件是
`test_resolve_node_bundle.py`（继承本文件的 Slice，不复制）。

运行：python tests/test_resolve_node_single_file.py
"""

import json
import os
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


class ResolveNodeContractTest(unittest.TestCase):
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
            env=FIXED_ENV,
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--title", "resolve")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def get_node(self, ref):
        return json.loads(self.run_cli("get", self.roadmap, ref).stdout)


class Slice01ResolveByUidTest(ResolveNodeContractTest):
    """get <uid> 必须返回与 get <display-id> 完全相同的节点。"""

    def test_get_by_uid_returns_the_same_node_as_by_display_id(self):
        self.init_roadmap()
        self.add_node("1", "设计")  # 显示 id "1-1"

        display = self.get_node("1-1")
        by_uid = self.get_node(display["uid"])

        self.assertEqual(by_uid["id"], display["id"])
        self.assertEqual(by_uid, display)


class Slice02ResolveErrorsTest(ResolveNodeContractTest):
    """传错 ref 的报错必须清晰，且历史错误文案不被破坏。"""

    def test_a_uid_that_matches_no_node_fails_with_a_clear_error(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        # 形状合法（12 hex - 10 hex）但不在图里 → 应明确说"uid 不匹配"。
        result = self.run_cli("get", self.roadmap, "ffffffffffff-0000000000", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uid", result.stderr)
        self.assertIn("节点不存在", result.stderr)

    def test_a_wrong_display_id_still_raises_the_legacy_keyerror(self):
        self.init_roadmap()

        # 错的显示 id（非 uid 形状）→ 走 get_node 的 KeyError，文案不变（#99）。
        result = self.run_cli("get", self.roadmap, "9-9", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("节点不存在", result.stderr)
        self.assertNotIn("uid", result.stderr)

    def test_a_valid_display_id_resolves_to_itself(self):
        self.init_roadmap()

        # 显示 id 直查命中，绝不被当成 uid 误解析。
        root = self.get_node("1")
        self.assertEqual(root["id"], "1")


class Slice03OtherCommandsAcceptUidTest(ResolveNodeContractTest):
    """其余取节点 id 的命令也该认 uid：update / decide / edge / siblings。"""

    def test_update_decide_edge_and_siblings_work_by_uid(self):
        self.init_roadmap()
        a = self.add_node("1", "设计")  # 1-1
        b = self.add_node("1", "实现")  # 1-2
        ua, ub = a["uid"], b["uid"]

        # update by uid
        self.run_cli("update", self.roadmap, ua, "--status", "completed")
        self.assertEqual(self.get_node("1-1")["status"], "completed")

        # decide by uid
        self.run_cli("decide", self.roadmap, ua, "为什么", "因为")
        self.assertEqual(len(self.get_node("1-1")["decisions"]), 1)

        # edge add by uid（from, to 都是 uid）→ 影响集里应含下游 1-2
        self.run_cli("edge", "add", self.roadmap, ua, ub, "--type", "blocks")
        self.assertIn("1-2", self.run_cli("impact", self.roadmap, ua).stdout)

        # siblings by uid
        sib = self.run_cli("siblings", self.roadmap, ua).stdout
        self.assertIn("1-2", sib)


if __name__ == "__main__":
    unittest.main()

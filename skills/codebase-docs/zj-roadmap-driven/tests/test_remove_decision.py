"""#112 — remove_decision 在两个 carrier 上语义一致（retract-and-keep）。

守门点：早期 carrier 曾用 hard-delete（pop / 列表过滤），与 retract-and-keep
（保留原记录 + 追加 retracted:True 孪生 + retracts 溯源哈希）两边漂移。
本文件把"撤回保留原记录"钉为契约，在两个 carrier、Python API 与 CLI
两个缝上各跑一遍同一套断言。

关键不变量：
- 原决策记录保留（不物理删除）；
- 追加一条 {"retracted": True, "retracts": sha256(canonical_json(原决策))} 孪生；
- retracts 哈希跨 carrier 字节一致（两个 carrier 的 canonical_json/sha256 同公式）；
- 已撤回记录再撤回幂等返回 0，不追加；
- total_decisions 计入 retracted 孪生。

运行：python tests/test_remove_decision.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import Roadmap, canonical_json, sha256  # noqa: E402
from roadmap_sqlite import RoadmapSqlite  # noqa: E402  # 第二个 carrier，验证 retract-and-keep 跨 carrier 一致
CLI = SKILL_DIR / "roadmap_cli.py"

NODE = "1-1"  # 根 "1" 下挂的第一个子节点


def expected_twin(original: dict) -> dict:
    """两个 carrier 撤回孪生记录的权威期望形状（由同一公式推导）。

    两个 carrier 必须都产出与之逐字段相等的记录，方能证明无语义漂移。
    """
    return {
        "q": original.get("q", ""),
        "answer": "",
        "note": f"retracted: {original.get('note', '')}".rstrip(),
        "retracted": True,
        "retracts": sha256(canonical_json(original)),
    }


class RemoveDecisionContractTest:
    """抽象契约基类——不继承 unittest.TestCase，避免被 loadTestsFromModule 收集。

    两个 carrier 的具体子类各自继承 (本类, unittest.TestCase)。
    本类提供 carrier 无关的断言 + 共用 helper；carrier 相关构造交给子类 hook。
    """

    # 子类可覆盖为更具体的错误类型；默认 Exception
    NO_TARGET_ERROR = Exception

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.path = self._build()

    def tearDown(self):
        self.tmp.cleanup()

    # ── carrier 相关 hook（子类实现）─────────────────────────

    def _build(self):
        """构造一个含根 "1" + 子 "1-1"（无决策）的 carrier，持久化，返回路径。"""
        raise NotImplementedError

    def _carrier(self):
        """从 self.path 重新加载 carrier（CLI 改写后用于回读）。"""
        raise NotImplementedError

    def _raw_decisions(self, carrier, node_id):
        """读取节点原始决策记录列表（绕过 get_decisions 的形状差异）。"""
        raise NotImplementedError

    def _total_decisions(self, carrier):
        raise NotImplementedError

    # ── 共用 helper ────────────────────────────────────────

    def _add(self, carrier, q, a, note=""):
        return carrier.add_decision(NODE, q, a, note)

    def _remove(self, carrier, index=None, question=None):
        return carrier.remove_decision(NODE, index=index, question=question)

    def _run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(self.workdir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result

    def _cli_decisions(self):
        result = self._run_cli("decisions", self.path, NODE)
        if result.returncode != 0:
            self.fail(f"decisions CLI 失败\n{result.stdout}\n{result.stderr}")
        payload = json.loads(result.stdout)
        return payload["decisions"] if isinstance(payload, dict) else payload

    # ── 契约断言：Python API 缝 ──────────────────────────────

    def test_retract_keeps_original_and_appends_twin(self):
        carrier = self._carrier()
        original = self._add(carrier, "为什么", "因为", "note-x")
        carrier.save()

        removed = self._remove(carrier, index=0)
        self.assertEqual(removed, 1)

        decisions = self._raw_decisions(carrier, NODE)
        self.assertEqual(len(decisions), 2)
        # 原记录保留且未被改写
        self.assertEqual(decisions[0], original)
        self.assertFalse(decisions[0].get("retracted", False))
        # 追加的孪生逐字段等于权威期望
        self.assertEqual(decisions[1], expected_twin(original))

    def test_retracts_hash_matches_the_shared_formula(self):
        carrier = self._carrier()
        original = self._add(carrier, "q1", "a1", "n1")
        carrier.save()

        self._remove(carrier, index=0)
        decisions = self._raw_decisions(carrier, NODE)
        twin = decisions[1]
        self.assertEqual(twin["retracts"], sha256(canonical_json(original)))
        self.assertEqual(twin["retracts"], sha256(canonical_json(original)))

    def test_reremove_is_idempotent(self):
        carrier = self._carrier()
        self._add(carrier, "为什么", "因为", "note-x")
        carrier.save()

        first = self._remove(carrier, index=0)  # 撤回原记录 → 追加孪生
        self.assertEqual(first, 1)
        # 原记录永不被标记 retracted，所以再次 --index 0 仍会追加孪生（命中非撤回原记录）。
        # 真正的幂等保证是：对已处于 retracted 的记录再撤回返回 0、不追加。
        second = self._remove(carrier, index=0)
        self.assertEqual(second, 1)

        third = self._remove(carrier, index=1)  # 对已撤回的孪生再撤回
        self.assertEqual(third, 0)

        decisions = self._raw_decisions(carrier, NODE)
        self.assertEqual(len(decisions), 3)  # 原记录 + 2 条孪生（仅非撤回目标会追加）

    def test_remove_by_question_only_targets_matching(self):
        carrier = self._carrier()
        self._add(carrier, "A", "a1", "n-a")
        self._add(carrier, "B", "b1", "n-b")
        carrier.save()

        removed = self._remove(carrier, question="A")
        self.assertEqual(removed, 1)

        decisions = self._raw_decisions(carrier, NODE)
        self.assertEqual(len(decisions), 3)
        twins = [d for d in decisions if d.get("retracted")]
        self.assertEqual(len(twins), 1)
        self.assertEqual(twins[0]["q"], "A")
        # "B" 未被触碰
        self.assertIn({"q": "B", "answer": "b1", "note": "n-b"}, decisions)

    def test_total_decisions_counts_retracted_twin(self):
        carrier = self._carrier()
        self._add(carrier, "为什么", "因为", "note-x")
        carrier.save()
        self.assertEqual(self._total_decisions(carrier), 1)

        self._remove(carrier, index=0)
        # retracted 孪生计入 total_decisions
        self.assertEqual(self._total_decisions(carrier), 2)

    def test_index_out_of_range_raises(self):
        carrier = self._carrier()
        self._add(carrier, "为什么", "因为", "note-x")
        carrier.save()
        with self.assertRaises(IndexError):
            self._remove(carrier, index=99)

    def test_requires_index_or_question(self):
        carrier = self._carrier()
        self._add(carrier, "为什么", "因为", "note-x")
        carrier.save()
        with self.assertRaises(self.NO_TARGET_ERROR):
            self._remove(carrier)  # 既不给 index 也不给 question

    # ── 契约断言：CLI 缝 ─────────────────────────────────────

    def test_cli_remove_by_index_retracts(self):
        # 通过 CLI 完整走 decide → remove-decision → decisions
        add = self._run_cli("decide", self.path, NODE, "为什么", "因为", "note-x")
        self.assertEqual(add.returncode, 0)

        rm = self._run_cli("remove-decision", self.path, NODE, "--index", "0")
        self.assertEqual(rm.returncode, 0)
        self.assertIn("Removed: 1 decision(s)", rm.stdout)

        decisions = self._cli_decisions()
        self.assertEqual(len(decisions), 2)
        self.assertFalse(decisions[0].get("retracted", False))
        self.assertTrue(decisions[1]["retracted"])
        self.assertEqual(decisions[1]["retracts"], sha256(canonical_json(decisions[0])))

    def test_cli_remove_by_question_retracts(self):
        add = self._run_cli("decide", self.path, NODE, "A", "a1", "n-a")
        self.assertEqual(add.returncode, 0)
        add2 = self._run_cli("decide", self.path, NODE, "B", "b1", "n-b")
        self.assertEqual(add2.returncode, 0)

        rm = self._run_cli("remove-decision", self.path, NODE, "--question", "A")
        self.assertEqual(rm.returncode, 0)
        self.assertIn("Removed: 1 decision(s)", rm.stdout)

        decisions = self._cli_decisions()
        twins = [d for d in decisions if d.get("retracted")]
        self.assertEqual(len(twins), 1)
        self.assertEqual(twins[0]["q"], "A")

    def test_cli_remove_without_target_errors(self):
        add = self._run_cli("decide", self.path, NODE, "为什么", "因为", "note-x")
        self.assertEqual(add.returncode, 0)
        rm = self._run_cli("remove-decision", self.path, NODE)
        self.assertNotEqual(rm.returncode, 0)


class SingleFileRemoveDecisionTest(RemoveDecisionContractTest, unittest.TestCase):
    NO_TARGET_ERROR = ValueError

    def _build(self):
        path = self.workdir / "roadmap.json"
        r = Roadmap(str(path))
        r.init(title="rm-dec", description="", md_file="")
        r.add_node("1", "根")
        r.add_node("1", "子")
        r.save()
        return path

    def _carrier(self):
        r = Roadmap(str(self.path))
        r.load()
        return r

    def _raw_decisions(self, carrier, node_id):
        return carrier.data["nodes"][node_id]["decisions"]

    def _total_decisions(self, carrier):
        return carrier.stats()["total_decisions"]


class SqliteRemoveDecisionTest(RemoveDecisionContractTest, unittest.TestCase):
    """sqlite 与 single-file 必须产出逐字段相同的撤回孪生。

    sqlite 继承 `Roadmap` 的 `remove_decision`，默认抛 ValueError（与 single-file 同），
    retracts 哈希用同一 canonical_json/sha256 公式 → 跨 carrier 字节一致。
    """

    NO_TARGET_ERROR = ValueError

    def _build(self):
        path = self.workdir / "roadmap.sqlite"
        r = RoadmapSqlite(str(path))
        r.init(title="rm-dec", description="", md_file="")
        r.add_node("1", "根")
        r.add_node("1", "子")
        r.save()
        return path

    def _carrier(self):
        r = RoadmapSqlite(str(self.path))
        r.load()
        return r

    def _raw_decisions(self, carrier, node_id):
        return carrier.data["nodes"][node_id]["decisions"]

    def _total_decisions(self, carrier):
        return carrier.stats()["total_decisions"]


if __name__ == "__main__":
    unittest.main(verbosity=2)

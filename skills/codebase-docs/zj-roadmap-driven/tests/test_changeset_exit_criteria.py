#!/usr/bin/env python3
"""#245 切片 2 — work.patch 收敛入口（复用 ChangeSet，不新增写入命令）。

纪律（与 #242 / #245 边界一致）：

- `work.patch` 补 `exit_criteria`（追加）+ `clear_exit_criteria`（清空），两种语义
  **显式区分、不猜默认**：同一条 patch 里 clear 与非空 append 互斥，直接拒。
- 单个 ChangeSet 能同时含 `work.patch(exit_criteria)` + `edge.put` + `decision.append`
  并原子 apply；digest / `--idempotency-key` / `--scope` 语义不回归；越界仍 `E_SCOPE`、
  stale / 错 digest 仍拒。
- `validate` 不因新字段误报；exit_criteria 是 fact-source-only，**不进 md 视图**
  （数据模型既定），所以追加它 md 逐字节不变。
- direct bypass（#234 S3-2 验收前提）仍被拒；命令总数不因新写入入口增加。

运行：python tests/test_changeset_exit_criteria.py
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

import roadmap as core  # noqa: E402
import roadmap_cli as cli  # noqa: E402

CLI = SKILL_DIR / "roadmap_cli.py"
TARGETS = {"single": "roadmap.json", "sqlite": "roadmap.sqlite"}

# 切片 2 落地前已有的命令清单快照：新增只应是 flag，不该出现新顶层命令。
EXPECTED_COMMANDS = frozenset({
    "init", "add", "update", "delete", "fail", "get", "tree", "ready",
    "critical-path", "impact", "edge", "lease", "decide", "decisions",
    "remove-decision", "render", "section", "link", "unlock", "stats",
    "recommend-storage", "validate", "path", "siblings", "focus", "migrate",
    "migrate-placements", "migrate-types", "placement", "context", "trace",
    "promote", "reconcile", "apply", "apply-batch", "changeset", "next",
    "signals", "authority-check",
})


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *[str(arg) for arg in args]],
        cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({result.returncode})\nargs: {args}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def new_roadmap() -> "core.Roadmap":
    """内存态 Roadmap（不落盘）；Roadmap 构造需要 json_path，但只作路径字符串。"""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    return core.Roadmap(path)


# ── 核心：work.patch 现在能吃 exit_criteria ──────────────────

class WorkPatchExitCriteriaTest(unittest.TestCase):
    def _build(self, storage: str, tmpdir: Path) -> Path:
        here = tmpdir / storage
        here.mkdir(parents=True, exist_ok=True)
        path = here / TARGETS[storage]
        args = ["init", path, "--title", "Slice2", "--md-file", "plan.md"]
        if storage == "sqlite":
            args += ["--storage", "sqlite"]
        run_cli(*args, cwd=here)
        work = json.loads(run_cli("add", path, "1", "Work", cwd=here).stdout)
        other = json.loads(run_cli("add", path, "1", "Context", cwd=here).stdout)
        return path, work, other

    def test_work_patch_exit_criteria_plus_edge_plus_decision_apply_atomically(self):
        """验收行 1：单个 ChangeSet 同时含三种 kind 可原子 apply（双 carrier）。"""
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                path, work, other = self._build(storage, tmpdir)
                changes = json.dumps([
                    {
                        "kind": "work.patch",
                        "work_uid": work["uid"],
                        "patch": {"label": "Work (renamed)", "exit_criteria": ["全部测试通过"]},
                    },
                    {
                        "kind": "edge.put",
                        "from_uid": other["uid"],
                        "to_uid": work["uid"],
                        "type": "informs",
                    },
                    {
                        "kind": "decision.append",
                        "node_uid": work["uid"],
                        "question": "为什么把判据收敛进同一个 ChangeSet？",
                        "answer": "避免散落多次确认，一次 preview/apply 收口。",
                    },
                ])
                preview = json.loads(run_cli(
                    "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
                ).stdout)
                self.assertEqual(
                    preview["change_kinds"],
                    ["work.patch", "edge.put", "decision.append"],
                )
                receipt = json.loads(run_cli(
                    "changeset", "apply", path, "--changes", changes,
                    "--approved-digest", preview["digest"],
                    "--idempotency-key", "slice2-combo-1", cwd=tmpdir,
                ).stdout)
                self.assertEqual(receipt["status"], "committed")

                stored = json.loads(run_cli("get", path, work["uid"], cwd=tmpdir).stdout)
                self.assertEqual(stored["label"], "Work (renamed)")
                self.assertEqual(stored["exit_criteria"], ["全部测试通过"])
                self.assertEqual(stored["decisions"][-1]["answer"],
                                 "避免散落多次确认，一次 preview/apply 收口。")
                edges = json.loads(run_cli("edge", "list", path, cwd=tmpdir).stdout)["edges"]
                self.assertTrue(any(
                    e["type"] == "informs" and e["from"] == other["id"] and e["to"] == work["id"]
                    for e in edges
                ))

    def test_work_patch_clear_exit_criteria(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                path, work, _ = self._build(storage, tmpdir)
                run_cli("update", path, work["id"], "--exit-criteria", "旧判据", cwd=tmpdir)
                changes = json.dumps([
                    {"kind": "work.patch", "work_uid": work["uid"],
                     "patch": {"clear_exit_criteria": True}},
                ])
                preview = json.loads(run_cli(
                    "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
                ).stdout)
                run_cli(
                    "changeset", "apply", path, "--changes", changes,
                    "--approved-digest", preview["digest"],
                    "--idempotency-key", "slice2-clear-1", cwd=tmpdir,
                )
                stored = json.loads(run_cli("get", path, work["uid"], cwd=tmpdir).stdout)
                self.assertEqual(stored["exit_criteria"], [])

    def test_clear_and_nonempty_append_are_mutually_exclusive(self):
        # 字段级校验在 apply 时触发（preview 只校验 kind + scope），故断言 apply。
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                path, work, _ = self._build(storage, tmpdir)
                changes = json.dumps([
                    {"kind": "work.patch", "work_uid": work["uid"],
                     "patch": {"clear_exit_criteria": True, "exit_criteria": ["X"]}},
                ])
                preview = json.loads(run_cli(
                    "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
                ).stdout)
                applied = run_cli(
                    "changeset", "apply", path, "--changes", changes,
                    "--approved-digest", preview["digest"],
                    "--idempotency-key", "slice2-conflict-1", cwd=tmpdir, check=False,
                )
                self.assertEqual(applied.returncode, 1)
                self.assertIn("互斥", applied.stderr)

    def test_exit_criteria_must_be_a_list(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            path, work, _ = self._build("single", tmpdir)
            changes = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"exit_criteria": "不是 list"}},
            ])
            preview = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
            ).stdout)
            applied = run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-list-1", cwd=tmpdir, check=False,
            )
            self.assertEqual(applied.returncode, 1)
            self.assertIn("list", applied.stderr)

    def test_unknown_patch_field_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            path, work, _ = self._build("single", tmpdir)
            changes = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"bogus_field": 1}},
            ])
            preview = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
            ).stdout)
            applied = run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-bogus-1", cwd=tmpdir, check=False,
            )
            self.assertEqual(applied.returncode, 1)
            self.assertIn("不允许字段", applied.stderr)


# ── 验收行 2：digest / idempotency-key / scope 语义不回归 ──────────

class DigestScopeRegressionTest(unittest.TestCase):
    def _build(self, tmpdir: Path) -> Path:
        here = tmpdir / "single"
        here.mkdir(parents=True, exist_ok=True)
        path = here / "roadmap.json"
        run_cli("init", path, "--title", "Slice2", "--md-file", "plan.md", cwd=here)
        inside = json.loads(run_cli("add", path, "1", "Inside", cwd=here).stdout)
        outside = json.loads(run_cli("add", path, "1", "Outside", cwd=here).stdout)
        return path, inside, outside

    def test_scope_rejects_exit_criteria_patch_out_of_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            path, inside, outside = self._build(tmpdir)
            changes = json.dumps([
                {"kind": "work.patch", "work_uid": outside["uid"],
                 "patch": {"exit_criteria": ["出界判据"]}},
            ])
            failed = run_cli(
                "changeset", "preview", path, "--scope", inside["uid"],
                "--changes", changes, cwd=tmpdir, check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertIn("E_SCOPE", failed.stderr)

    def test_stale_digest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            path, inside, outside = self._build(tmpdir)
            work = json.loads(run_cli("add", path, inside["id"], "W", cwd=tmpdir).stdout)
            changes = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"exit_criteria": ["判据"]}},
            ])
            preview = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
            ).stdout)
            # 改底层数据让 revision 推进，再用旧 digest 申请 → stale 拒。
            run_cli("update", path, work["id"], "--notes", "扰动", cwd=tmpdir)
            stale = run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-stale-1", cwd=tmpdir, check=False,
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn("stale", stale.stderr)

    def test_idempotency_key_replays_same_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            path, inside, outside = self._build(tmpdir)
            work = json.loads(run_cli("add", path, inside["id"], "W", cwd=tmpdir).stdout)
            changes = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"exit_criteria": ["判据"]}},
            ])
            preview = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
            ).stdout)
            first = json.loads(run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-idem-1", cwd=tmpdir,
            ).stdout)
            second = json.loads(run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-idem-1", cwd=tmpdir,
            ).stdout)
            self.assertEqual(first, second)


# ── 验收行 3：validate 不误报；exit_criteria 不进 md 视图 ──────────

class ValidateAndViewStabilityTest(unittest.TestCase):
    def test_validate_clean_when_exit_criteria_present(self):
        rm = new_roadmap()
        rm.init("Root")
        work = rm.add_node("1", "Work", mode=core.MODE_EXPLOIT)
        # 直接构造一个带 exit_criteria 的节点，绕开 CLI，专测 validate 不误报。
        work["exit_criteria"] = ["全部测试通过", "文档补齐"]
        self.assertEqual(rm.validate(), [])

    def test_exit_criteria_does_not_leak_into_view(self):
        """exit_criteria 是 fact-source-only，追加它不进任一 Human 视图。"""
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            here = tmpdir / "single"
            here.mkdir(parents=True, exist_ok=True)
            path = here / "roadmap.json"
            run_cli("init", path, "--title", "Slice2", cwd=here)
            work = json.loads(run_cli("add", path, "1", "Work", cwd=here).stdout)

            changes = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"exit_criteria": ["完成判据文本"]}},
            ])
            preview = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes, cwd=tmpdir,
            ).stdout)
            run_cli(
                "changeset", "apply", path, "--changes", changes,
                "--approved-digest", preview["digest"],
                "--idempotency-key", "slice2-md-1", cwd=tmpdir,
            )
            # 正控制：exit_criteria 文本不应出现在导出视图里（它不渲染）。
            section = run_cli("section", path, cwd=tmpdir).stdout
            self.assertNotIn("完成判据文本", section)
            # 数据层确实写进去了。
            stored = json.loads(run_cli("get", path, work["uid"], cwd=tmpdir).stdout)
            self.assertEqual(stored["exit_criteria"], ["完成判据文本"])

            # 反控制：同样的 work.patch 改 label 会进视图，证明上面不是空断言。
            changes_label = json.dumps([
                {"kind": "work.patch", "work_uid": work["uid"],
                 "patch": {"label": "WorkRenamed"}},
            ])
            preview2 = json.loads(run_cli(
                "changeset", "preview", path, "--changes", changes_label, cwd=tmpdir,
            ).stdout)
            run_cli(
                "changeset", "apply", path, "--changes", changes_label,
                "--approved-digest", preview2["digest"],
                "--idempotency-key", "slice2-md-2", cwd=tmpdir,
            )
            section2 = run_cli("section", path, cwd=tmpdir).stdout
            self.assertIn("WorkRenamed", section2)


# ── 验收行 4：命令总数不因新写入入口增加 ──────────────────────

class NoNewWriteCommandTest(unittest.TestCase):
    def test_command_inventory_unchanged(self):
        self.assertEqual(frozenset(cli.COMMANDS.keys()), EXPECTED_COMMANDS)

    def test_signals_remains_read_only(self):
        """切片 2 只给 signals 加了只读 flag，没把它变成写命令。"""
        self.assertIn("signals", cli.COMMANDS)
        self.assertNotIn("signals", cli.LOCK_COMMANDS)

    def test_direct_bypass_still_rejected_after_slice2(self):
        """#234 S3-2 验收前提：promote --accept 直接拓扑写仍被拒。"""
        # 直接复用已落地的 #234 验收测试文件，确保 slice 2 没破坏那条不变量。
        target = SKILL_DIR / "tests" / "test_s3_rollout_closeout.py"
        result = subprocess.run(
            [sys.executable, str(target)], cwd=str(SKILL_DIR), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0,
                        f"#234 验收测试回归:\n{result.stdout}\n{result.stderr}")


# ── 桥接：信号 → 候选 ChangeSet → 一次 Human 确认 ──────────────

class SignalToChangesetBridgeTest(unittest.TestCase):
    def _signal(self, kind, nid="1-2"):
        return {
            "node": nid, "label": "节点", "kind": kind,
            "detail": f"[{kind}] 描述",
            "suggested_action": f"[{kind}] 建议动作",
        }

    def test_cleared_with_criterion_yields_work_patch_and_decision(self):
        rm = new_roadmap()
        rm.init("Root")
        node = rm.add_node("1", "Target")
        resolve_uid = lambda ref: rm.get_node(rm.resolve_node(ref))["uid"]
        changes = core.signal_to_changeset(
            self._signal("cleared_exit_criteria", nid="1-1"), resolve_uid, criterion="全部测试通过"
        )
        self.assertEqual(changes[0]["kind"], "work.patch")
        self.assertEqual(changes[0]["patch"]["exit_criteria"], ["全部测试通过"])
        self.assertEqual(changes[0]["work_uid"], node["uid"])
        self.assertEqual(changes[1]["kind"], "decision.append")
        self.assertEqual(changes[1]["node_uid"], node["uid"])

    def test_cleared_without_criterion_yields_decision_only(self):
        rm = new_roadmap()
        rm.init("Root")
        rm.add_node("1", "Target")
        resolve_uid = lambda ref: rm.get_node(rm.resolve_node(ref))["uid"]
        changes = core.signal_to_changeset(
            self._signal("cleared_exit_criteria", nid="1-1"), resolve_uid
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "decision.append")

    def test_other_kinds_yield_decision_only(self):
        rm = new_roadmap()
        rm.init("Root")
        rm.add_node("1", "Target")
        resolve_uid = lambda ref: rm.get_node(rm.resolve_node(ref))["uid"]
        for kind in ("budget_exhausted", "completed_with_open_question"):
            with self.subTest(kind=kind):
                changes = core.signal_to_changeset(
                    self._signal(kind, nid="1-1"), resolve_uid
                )
                self.assertEqual(changes, [{
                    "kind": "decision.append",
                    "node_uid": resolve_uid("1-1"),
                    "question": f"[{kind}] 描述",
                    "answer": f"[{kind}] 建议动作",
                }])

    def test_cli_signals_as_changeset_round_trips_through_changeset(self):
        """只读 `signals --as-changeset` 产出的候选，喂回 changeset 可原子 apply。"""
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                here = tmpdir / storage
                here.mkdir(parents=True, exist_ok=True)
                path = here / TARGETS[storage]
                args = ["init", path, "--title", "Slice2", "--md-file", "plan.md"]
                if storage == "sqlite":
                    args += ["--storage", "sqlite"]
                run_cli(*args, cwd=here)
                run_cli("add", path, "1", "探索", "--mode", "explore",
                        "--max-children", "1", cwd=here)
                run_cli("add", path, "1-1", "子节点", cwd=here)
                run_cli("add", path, "1", "实现", "--exit-criteria", "全部通过", cwd=here)
                run_cli("update", path, "1-2", "--clear-exit-criteria", cwd=here)

                # 只读：运行前后 carrier 字节不变。
                before = path.read_bytes()
                candidate_raw = run_cli(
                    "signals", path, "--as-changeset", "--criterion", "重补判据",
                    cwd=here,
                ).stdout
                self.assertEqual(before, path.read_bytes(), "signals --as-changeset 改写了 carrier")

                candidate = json.loads(candidate_raw)
                self.assertTrue(candidate)  # 至少一条候选（cleared_exit_criteria）
                preview = json.loads(run_cli(
                    "changeset", "preview", path, "--changes", json.dumps(candidate), cwd=here,
                ).stdout)
                run_cli(
                    "changeset", "apply", path, "--changes", json.dumps(candidate),
                    "--approved-digest", preview["digest"],
                    "--idempotency-key", "slice2-bridge-1", cwd=here,
                )
                # 被清空判据的节点（1-2）现在已重补判据 + 落了一条决策。
                target = json.loads(run_cli("get", path, "1-2", cwd=here).stdout)
                self.assertIn("重补判据", target["exit_criteria"])
                self.assertTrue(target["decisions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

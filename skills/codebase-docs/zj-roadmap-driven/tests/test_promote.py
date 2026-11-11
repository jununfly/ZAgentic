#!/usr/bin/env python3
"""P5-S3 promote compatibility adapter and legacy state semantics.

验收（来自 `docs/designs/zj-roadmap-execution-graph.md`）：
- promote 默认只写 `promotion.state=proposed`，不落 plan 节点、md 字节不变。
- promote --accept requires a reviewed reconciliation digest and applies one
  atomic ChangeSet, with the same receipt/view semantics on both carriers.
- 幂等：重复 propose / accept / reject 均 exit 0 且节点数不变。
- 错误码断言：E_INVALID_LAYER / E_PROMOTE_TARGET_INVALID / E_PROMOTE_STATE_INVALID /
  E_REFERENCED，全部 exit 1。
- 删除已被 accept 引用的 trace → E_REFERENCED（参照完整性，§3.4）。

单元（apply_promotion 纯函数）+ 两个 carrier（single / sqlite）各跑一遍；sqlite 继承 single-file。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from roadmap import (  # noqa: E402
    Roadmap,
    LAYER_TRACE,
    LAYER_PLAN,
    apply_promotion,
    PROMOTE_PROPOSED,
    PROMOTE_ACCEPTED,
    PROMOTE_REJECTED,
    PromoteStateInvalid,
    PromoteTargetInvalid,
    InvalidLayer,
    ReferencedError,
    RoadmapError,
    ERROR_EXIT_CODES,
)
from roadmap_sqlite import RoadmapSqlite  # noqa: E402


TARGETS = {
    "single": "roadmap.json",
    "sqlite": "roadmap.sqlite",
}


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CLI), *[str(a) for a in args]],
        cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({completed.returncode})\nargs: {args}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def load_carrier(storage: str, path: Path):
    rm = Roadmap(str(path)) if storage == "single" else RoadmapSqlite(str(path))
    rm.load()
    return rm


# md 头 `最后更新: <timestamp>` 会随每次 save 漂移 1 秒；propose 不改变结构但
# 会触发 save，故 before/after 的 section 仅在时间戳上不同。归一化后再比对，
# 否则"propose 不改变 md"这条断言会被时间戳噪声误伤（与 test_trace.py 同纪律）。
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def normalize(s: str) -> str:
    return TS_RE.sub("TS", s)


def normalize_identity(value, uid_apply: str, uid_promote: str):
    """Collapse each path's freshly minted WorkItem uid into one shared token.

    ``new_uid()`` deliberately uses time + randomness, so two independent
    executions cannot be byte-identical; the revision is derived from that
    identity and is collapsed as well.  Used to prove that ``promote --accept``
    and ``apply`` emit the same receipt shape.
    """
    if isinstance(value, str):
        for uid in (uid_apply, uid_promote):
            value = value.replace(uid, "<WORK_UID>")
        return value
    if isinstance(value, list):
        return [normalize_identity(v, uid_apply, uid_promote) for v in value]
    if isinstance(value, dict):
        return {
            key: ("<REVISION>" if key == "revision"
                  else "<IDEMPOTENCY_KEY>" if key == "idempotency_key"
                  else normalize_identity(v, uid_apply, uid_promote))
            for key, v in value.items()
        }
    return value


def get_trace(rm, trace_id: str) -> dict:
    for n in rm.iter_nodes(layer=LAYER_TRACE):
        if n["id"] == trace_id:
            return n
    raise KeyError(trace_id)


class PromoteUnitTest(unittest.TestCase):
    def test_reject_records_reason_keeps_trace(self):
        node = {"id": "9-1", "layer": "trace", "kind": "finding"}
        apply_promotion(node, "propose", target="1-1", label="L")
        apply_promotion(node, "reject", reason="out of scope")
        self.assertEqual(node["promotion"]["state"], PROMOTE_REJECTED)
        self.assertEqual(node["promotion"]["reason"], "out of scope")
        self.assertIsNotNone(node.get("id"))

    def test_error_codes_exit_1(self):
        for code in (
            "E_PROMOTE_STATE_INVALID",
            "E_RECONCILIATION_REQUIRED",
            "E_REFERENCED",
            "E_PRUNE_NO_EDGE",
        ):
            self.assertIn(code, ERROR_EXIT_CODES, code)
            self.assertEqual(ERROR_EXIT_CODES[code], 1, code)


class PromoteSliceTest(unittest.TestCase):
    def _seed(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        run_cli("trace", "add", path, "--kind", "finding", "--body", "b", "--under", "1-1", cwd=tmpd)
        rm = load_carrier(storage, path)
        trace_id = rm.node_ids(layer=LAYER_TRACE)[0]
        return path, trace_id

    def _seed_reconciliation(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        trace = json.loads(run_cli(
            "trace", "add", path, "--kind", "finding", "--body", "new risk",
            "--obligation-key", "risk:new", "--evidence", "scan:1", cwd=tmpd,
        ).stdout)
        return path, trace["uid"]

    def _seed_refinement_reconciliation(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        run_cli(
            "add", path, "1", "completed work", "--status", "completed",
            "--obligation-key", "risk:refine", cwd=tmpd,
        )
        trace = json.loads(run_cli(
            "trace", "add", path, "--kind", "finding", "--body", "new evidence",
            "--obligation-key", "risk:refine", "--evidence", "scan:refine", cwd=tmpd,
        ).stdout)
        return path, trace["uid"]

    def _accept_routes_through_reviewed_reconciliation(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli(
                "reconcile", path, trace_uid, cwd=tmpd,
            ).stdout)

            accepted = run_cli(
                "promote", path, trace_uid, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-reconcile-1", cwd=tmpd,
            )
            receipt = json.loads(accepted.stdout)
            self.assertEqual(receipt["status"], "committed")
            stored = json.loads(run_cli("get", path, trace_uid, cwd=tmpd).stdout)
            self.assertEqual(stored["reconciliation"]["disposition"], "novel")
            self.assertIsNotNone(stored["reconciliation"]["work_uid"])

    def _direct_api_accept_requires_reconciliation(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            roadmap = load_carrier(storage, path)
            before = json.dumps(roadmap.data, sort_keys=True)

            with self.assertRaises(RoadmapError) as raised:
                roadmap.promote(trace_uid, "accept")

            self.assertEqual(raised.exception.code, "E_RECONCILIATION_REQUIRED")
            self.assertEqual(json.dumps(roadmap.data, sort_keys=True), before)

    def _accept_retry_returns_original_receipt(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli(
                "reconcile", path, trace_uid, cwd=tmpd,
            ).stdout)
            command = (
                "promote", path, trace_uid, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-retry-1",
            )

            first = json.loads(run_cli(*command, cwd=tmpd).stdout)
            second = json.loads(run_cli(*command, cwd=tmpd).stdout)

            self.assertEqual(second, first)

    def _accept_rejects_wrong_digest_without_mutation(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            before_tree = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout

            rejected = run_cli(
                "promote", path, trace_uid, "--accept",
                "--approved-digest", "0" * 64,
                "--idempotency-key", "promote-wrong-digest-1",
                check=False, cwd=tmpd,
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("E_APPROVAL_MISMATCH", rejected.stderr)
            self.assertEqual(
                run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                before_tree,
            )
            self.assertNotIn(
                "reconciliation",
                json.loads(run_cli("get", path, trace_uid, cwd=tmpd).stdout),
            )

    def _accept_rejects_stale_preview_without_mutation(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli("reconcile", path, trace_uid, cwd=tmpd).stdout)
            run_cli("add", path, "1", "unrelated change", cwd=tmpd)
            before_tree = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout

            rejected = run_cli(
                "promote", path, trace_uid, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-stale-1",
                check=False, cwd=tmpd,
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("E_APPROVAL_MISMATCH", rejected.stderr)
            self.assertEqual(
                run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                before_tree,
            )
            self.assertNotIn(
                "reconciliation",
                json.loads(run_cli("get", path, trace_uid, cwd=tmpd).stdout),
            )

    def _accept_rejects_cross_proposal_idempotency_reuse(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, first_uid = self._seed_reconciliation(storage, tmpd)
            second = json.loads(run_cli(
                "trace", "add", path, "--kind", "finding", "--body", "second risk",
                "--obligation-key", "risk:second", "--evidence", "scan:2", cwd=tmpd,
            ).stdout)
            first_proposal = json.loads(run_cli(
                "reconcile", path, first_uid, cwd=tmpd,
            ).stdout)
            second_proposal = json.loads(run_cli(
                "reconcile", path, second["uid"], cwd=tmpd,
            ).stdout)
            run_cli(
                "promote", path, first_uid, "--accept",
                "--approved-digest", first_proposal["proposal_digest"],
                "--idempotency-key", "promote-shared-key",
                cwd=tmpd,
            )
            before_tree = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout

            rejected = run_cli(
                "promote", path, second["uid"], "--accept",
                "--approved-digest", second_proposal["proposal_digest"],
                "--idempotency-key", "promote-shared-key",
                check=False, cwd=tmpd,
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("E_IDEMPOTENCY_CONFLICT", rejected.stderr)
            self.assertEqual(
                run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                before_tree,
            )
            self.assertNotIn(
                "reconciliation",
                json.loads(run_cli("get", path, second["uid"], cwd=tmpd).stdout),
            )

    def _accept_publishes_the_same_view_receipt_as_apply(self, storage: str):
        # 修复此前只断言 view_status/published 的"假 parity"：现在从同一份 seed
        # 出发，分别走显式 apply 与 promote --accept，归一化各自新建的 work_uid
        # 后逐字段比较两条路径产出的 receipt，确认 accept 视图与 apply 视图同构。
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            ext = "sqlite" if storage == "sqlite" else "json"
            seed = tmpd / f"seed.{ext}"
            init_args = ["init", seed, "--title", "t"]
            if storage == "sqlite":
                init_args += ["--storage", "sqlite"]
            run_cli(*init_args, cwd=tmpd)
            trace = json.loads(run_cli(
                "trace", "add", seed, "--kind", "finding", "--body", "new risk",
                "--obligation-key", "risk:new", "--evidence", "scan:1", cwd=tmpd,
            ).stdout)
            uid = trace["uid"]
            proposal = json.loads(run_cli("reconcile", seed, uid, cwd=tmpd).stdout)

            apply_path = tmpd / f"apply.{ext}"
            promote_path = tmpd / f"promote.{ext}"
            shutil.copy(seed, apply_path)
            shutil.copy(seed, promote_path)

            apply_receipt = json.loads(run_cli(
                "apply", apply_path, proposal["proposal_id"],
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "view-apply-1", cwd=tmpd,
            ).stdout)
            promote_receipt = json.loads(run_cli(
                "promote", promote_path, uid, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "view-promote-1", cwd=tmpd,
            ).stdout)

            apply_work = {
                c["work_uid"] for c in apply_receipt.get("changes", [])
                if "work_uid" in c
            }
            promote_work = {
                c["work_uid"] for c in promote_receipt.get("changes", [])
                if "work_uid" in c
            }
            self.assertEqual(len(apply_work), 1, "apply 应落一个 work item")
            self.assertEqual(len(promote_work), 1, "promote --accept 应落一个 work item")
            a_id, p_id = apply_work.pop(), promote_work.pop()
            self.assertEqual(
                normalize_identity(apply_receipt, a_id, p_id),
                normalize_identity(promote_receipt, a_id, p_id),
                "两条路径的 receipt 应逐字段同构",
            )
            self.assertEqual(promote_receipt["view_status"], "published")
            self.assertIn("new risk", (tmpd / "ROADMAP.md").read_text(encoding="utf-8"))

    def _accept_rejects_legacy_topology_overrides(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli("reconcile", path, trace_uid, cwd=tmpd).stdout)
            before = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout

            rejected = run_cli(
                "promote", path, trace_uid, "--accept",
                "--under", "1", "--label", "wrong target", "--reason", "wrong reason",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-legacy-override-1",
                check=False, cwd=tmpd,
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("E_USAGE", rejected.stderr)
            self.assertEqual(run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout, before)

    def _accept_forwards_refinement_answer(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_uid = self._seed_refinement_reconciliation(storage, tmpd)
            answer = {
                "disposition": "refine",
                "action": "reopen",
                "reason": "新的执行证据需要继续原 WorkItem",
            }
            answer_arg = json.dumps(answer, ensure_ascii=False)
            proposal = json.loads(run_cli(
                "reconcile", path, trace_uid, "--answer", answer_arg, cwd=tmpd,
            ).stdout)

            receipt = json.loads(run_cli(
                "promote", path, trace_uid, "--accept",
                "--answer", answer_arg,
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-refine-1", cwd=tmpd,
            ).stdout)

            self.assertEqual(receipt["status"], "committed")
            work = json.loads(run_cli("get", path, "1-1", cwd=tmpd).stdout)
            self.assertEqual(work["status"], "in_progress")
            stored_trace = json.loads(run_cli("get", path, trace_uid, cwd=tmpd).stdout)
            self.assertEqual(stored_trace["reconciliation"]["disposition"], "refine")

    def _propose_does_not_change_plan_or_md(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed(storage, tmpd)
            before_tree = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout
            before_section = normalize(run_cli("section", path, cwd=tmpd).stdout)
            p = run_cli("promote", path, trace_id, "--under", "1-1", "--label", "NewPlan", cwd=tmpd)
            self.assertEqual(p.returncode, 0)
            after_tree = run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout
            after_section = normalize(run_cli("section", path, cwd=tmpd).stdout)
            self.assertEqual(before_tree, after_tree, "propose 不应改变 plan 树")
            self.assertEqual(before_section, after_section, "propose 不应改变 md")
            t = get_trace(load_carrier(storage, path), trace_id)
            self.assertEqual(t["promotion"]["state"], PROMOTE_PROPOSED)
            self.assertEqual(t["promotion"]["label"], "NewPlan")

    def _accept_creates_plan_node_and_edge(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed_reconciliation(storage, tmpd)
            before_plan_count = len(load_carrier(storage, path).node_ids(layer=LAYER_PLAN))
            before_section = normalize(run_cli("section", path, cwd=tmpd).stdout)
            proposal = json.loads(run_cli("reconcile", path, trace_id, cwd=tmpd).stdout)
            acc = run_cli(
                "promote", path, trace_id, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-accept-1", cwd=tmpd,
            )
            self.assertEqual(json.loads(acc.stdout)["status"], "committed")
            rm = load_carrier(storage, path)
            after_plan_count = len(rm.node_ids(layer=LAYER_PLAN))
            self.assertEqual(after_plan_count, before_plan_count + 1, "accept 应新增一个 plan 节点")
            # derives-from 边 +1
            derives = [e for e in rm.list_edges() if e["type"] == "derives-from"]
            self.assertEqual(len(derives), 1, "accept 应写一条 derives-from 边")
            self.assertEqual(derives[0]["from"], rm.resolve_node(trace_id))
            # 新节点按 reconciliation 的 trace provenance 挂到 root 下。
            self.assertEqual(rm.get_node(derives[0]["to"])["parent"], "1")
            # md 变化（这次是预期）
            after_section = normalize(run_cli("section", path, cwd=tmpd).stdout)
            self.assertNotEqual(before_section, after_section, "accept 后 md 应变化")

    def _idempotent_accept(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli("reconcile", path, trace_id, cwd=tmpd).stdout)
            command = (
                "promote", path, trace_id, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-idempotent-1",
            )
            run_cli(*command, cwd=tmpd)
            run_cli(*command, cwd=tmpd)  # 第二次幂等
            rm = load_carrier(storage, path)
            self.assertEqual(len(rm.node_ids(layer=LAYER_PLAN)), 2, "重复 accept 不应落第二个节点")
            self.assertEqual(len([e for e in rm.list_edges() if e["type"] == "derives-from"]), 1)

    def _delete_accepted_trace_rejected(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed_reconciliation(storage, tmpd)
            proposal = json.loads(run_cli("reconcile", path, trace_id, cwd=tmpd).stdout)
            run_cli(
                "promote", path, trace_id, "--accept",
                "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", "promote-delete-1", cwd=tmpd,
            )
            p = run_cli("delete", path, trace_id, check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1, "删除已被 accept 的 trace 应被拒")
            self.assertIn("E_REFERENCED", p.stderr)

    def _negative_promote_on_plan_node(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed(storage, tmpd)
            p = run_cli("promote", path, "1-1", "--under", "1", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_INVALID_LAYER", p.stderr)

    def _negative_under_a_trace(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed(storage, tmpd)
            # 第二条 trace，promote --under 指向第一条 trace（非 plan）
            run_cli("trace", "add", path, "--kind", "doubt", "--body", "x", cwd=tmpd)
            rm = load_carrier(storage, path)
            other = [t for t in rm.node_ids(layer=LAYER_TRACE) if t != trace_id][0]
            p = run_cli("promote", path, other, "--under", trace_id, check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_PROMOTE_TARGET_INVALID", p.stderr)

    def _negative_accept_without_proposal(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id = self._seed_reconciliation(storage, tmpd)
            p = run_cli("promote", path, trace_id, "--accept", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_USAGE", p.stderr)


for _storage in ("single", "sqlite"):
    def _make(storage):
        def test_propose(self): self._propose_does_not_change_plan_or_md(storage)
        def test_accept(self): self._accept_creates_plan_node_and_edge(storage)
        def test_idem(self): self._idempotent_accept(storage)
        def test_del(self): self._delete_accepted_trace_rejected(storage)
        def test_neg_plan(self): self._negative_promote_on_plan_node(storage)
        def test_neg_under(self): self._negative_under_a_trace(storage)
        def test_neg_accept(self): self._negative_accept_without_proposal(storage)
        def test_accept_reconciliation(self):
            self._accept_routes_through_reviewed_reconciliation(storage)
        def test_direct_api_accept(self):
            self._direct_api_accept_requires_reconciliation(storage)
        def test_accept_retry(self):
            self._accept_retry_returns_original_receipt(storage)
        def test_accept_wrong_digest(self):
            self._accept_rejects_wrong_digest_without_mutation(storage)
        def test_accept_stale(self):
            self._accept_rejects_stale_preview_without_mutation(storage)
        def test_accept_idempotency_conflict(self):
            self._accept_rejects_cross_proposal_idempotency_reuse(storage)
        def test_accept_publishes_view(self):
            self._accept_publishes_the_same_view_receipt_as_apply(storage)
        def test_accept_rejects_legacy_overrides(self):
            self._accept_rejects_legacy_topology_overrides(storage)
        def test_accept_forwards_refinement_answer(self):
            self._accept_forwards_refinement_answer(storage)
        name = f"test_{_storage}"
        setattr(PromoteSliceTest, f"test_propose_{_storage}", test_propose)
        setattr(PromoteSliceTest, f"test_accept_{_storage}", test_accept)
        setattr(PromoteSliceTest, f"test_idempotent_accept_{_storage}", test_idem)
        setattr(PromoteSliceTest, f"test_delete_accepted_{_storage}", test_del)
        setattr(PromoteSliceTest, f"test_negative_plan_{_storage}", test_neg_plan)
        setattr(PromoteSliceTest, f"test_negative_under_trace_{_storage}", test_neg_under)
        setattr(PromoteSliceTest, f"test_negative_accept_no_proposal_{_storage}", test_neg_accept)
        setattr(PromoteSliceTest, f"test_accept_reconciliation_{_storage}", test_accept_reconciliation)
        setattr(PromoteSliceTest, f"test_direct_api_accept_{_storage}", test_direct_api_accept)
        setattr(PromoteSliceTest, f"test_accept_retry_{_storage}", test_accept_retry)
        setattr(PromoteSliceTest, f"test_accept_wrong_digest_{_storage}", test_accept_wrong_digest)
        setattr(PromoteSliceTest, f"test_accept_stale_{_storage}", test_accept_stale)
        setattr(PromoteSliceTest, f"test_accept_idempotency_conflict_{_storage}", test_accept_idempotency_conflict)
        setattr(PromoteSliceTest, f"test_accept_publishes_view_{_storage}", test_accept_publishes_view)
        setattr(PromoteSliceTest, f"test_accept_rejects_legacy_overrides_{_storage}", test_accept_rejects_legacy_overrides)
        setattr(PromoteSliceTest, f"test_accept_forwards_refinement_answer_{_storage}", test_accept_forwards_refinement_answer)
    _make(_storage)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Contract tests for P2 scope tokens and field-level ownership (issue #113).

Scope (docs/plans/zj-roadmap-dag-concurrency.md §4 + Story 29/30/32):

  * `--as-agent <id> --scope <node>` — a subagent physically cannot write
    outside its assigned subtree; an out-of-scope write fails with `E_SCOPE`
    naming the allowed scope (Story 30).
  * field-level ownership — status/notes belong to the lease holder,
    label/mode/budget/exit_criteria to the planner, decisions are append-only,
    "so that most concurrent edits never conflict at all" (Story 32).

Decisions taken with zj before the loop started (both are spec ambiguities):

  1. **Absent `--scope` means unrestricted**, not read-only. The spec's
     "subagent 默认无 scope（只读）" would make #111's delivered acceptance
     (`update --as-agent a7 --token 1` without `--scope` → exit 0) red, and it
     contradicts field ownership: the lease holder must be able to write
     `status` on the node it holds. Read-only is a policy the *parent* agent
     enforces by handing down a `--scope`; the CLI cannot tell a subagent from
     a planner or a human.
  2. **Planner fields = label + mode + budget + exit_criteria** (planning
     metadata; changing them does not move execution forward).
  3. **Fencing outranks field ownership.** Discovered by the full-suite run:
     making every planner write unconditional also let the fenced-out holder of
     a stolen lease keep writing, so a zombie only had to swap `--status` for
     `--label`. A presentation of a superseded `--token` is rejected on *any*
     field; ownership only decides between "not the holder" callers.

The three decisions are recorded in the plan doc §4 so the next P2 ticket does
not re-litigate them.

Seams under test
----------------
  1. Policy functions in `roadmap` (pure, one source of truth for both
     carriers): `is_within_scope`, `write_requires_lease`, `ERROR_EXIT_CODES`.
  2. CLI contract (subprocess: exit code + stderr `E_*` code) — the documented
     main seam. Every CLI test runs against **both** carriers.

Run: python tests/test_scope_ownership.py        (also works under pytest)
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

import roadmap
from roadmap import (
    ERROR_EXIT_CODES,
    ScopeError,
    exit_code_for,
    is_within_scope,
    write_requires_lease,
)


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                          capture_output=True, text=True)


# ── Slice 1: the error code is part of the Agent-facing contract ──

class ScopeErrorCode(unittest.TestCase):
    """E_SCOPE joins the *existing* code table; no new mechanism (#110 §不变式 2)."""

    def test_scope_error_has_stable_code_and_exit_code(self):
        self.assertEqual(ScopeError.code, "E_SCOPE")
        self.assertEqual(ERROR_EXIT_CODES["E_SCOPE"], 1)
        self.assertEqual(exit_code_for(ScopeError("out of scope")), 1)

    def test_scope_error_is_a_roadmap_error(self):
        self.assertIsInstance(ScopeError("x"), roadmap.RoadmapError)


# ── Slice 2: scope policy is a pure function (one source of truth) ──

class ScopePolicy(unittest.TestCase):
    """`is_within_scope` walks parent links; the subtree is inclusive.

    A cycle in the parent chain (corrupt carrier) must terminate instead of
    hanging the CLI.
    """

    PARENTS = {"1": None, "1-1": "1", "1-2": "1", "1-1-1": "1-1"}

    def _in_scope(self, node_id, scope_root):
        return is_within_scope(node_id, scope_root, self.PARENTS.get)

    def test_scope_root_itself_is_in_scope(self):
        self.assertTrue(self._in_scope("1-1", "1-1"))

    def test_descendant_is_in_scope(self):
        self.assertTrue(self._in_scope("1-1-1", "1-1"))

    def test_sibling_is_out_of_scope(self):
        self.assertFalse(self._in_scope("1-2", "1-1"))

    def test_ancestor_is_out_of_scope(self):
        self.assertFalse(self._in_scope("1", "1-1"))

    def test_parent_cycle_terminates(self):
        cyclic = {"a": "b", "b": "a", "c": "a"}
        self.assertFalse(is_within_scope("c", "missing", cyclic.get))
        self.assertTrue(is_within_scope("b", "a", cyclic.get))


# ── Slice 3: field ownership partition ──

class FieldOwnershipPolicy(unittest.TestCase):
    def test_executor_fields_require_the_lease(self):
        self.assertTrue(write_requires_lease({"status"}))
        self.assertTrue(write_requires_lease({"notes"}))

    def test_planner_fields_never_require_the_lease(self):
        self.assertFalse(write_requires_lease({"label"}))
        self.assertFalse(write_requires_lease({"mode"}))
        self.assertFalse(write_requires_lease({"budget"}))
        self.assertFalse(write_requires_lease({"exit_criteria"}))
        self.assertFalse(write_requires_lease({"label", "mode", "budget", "exit_criteria"}))

    def test_append_only_decisions_never_require_the_lease(self):
        self.assertFalse(write_requires_lease({"decisions"}))

    def test_structural_writes_require_the_lease(self):
        # empty set == structural (add / delete / retract), not "no fields"
        self.assertTrue(write_requires_lease(set()))

    def test_executor_field_in_a_mixed_write_wins(self):
        self.assertTrue(write_requires_lease({"label", "status"}))


# ── CLI contract: both carriers, every slice ──

class ScopeCliContract:
    storage = "single"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / ("roadmap.json" if self.storage == "single" else "roadmap.bundle")
        init = run_cli("init", str(path), "--title", "scope", "--storage", self.storage)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.path = str(path)
        # 1 -> {1-1 -> {1-1-1}, 1-2}
        for parent, label in (("1", "A"), ("1", "B"), ("1-1", "A1")):
            self.assertEqual(run_cli("add", self.path, parent, label).returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def uid_of(self, node_id: str) -> str:
        out = run_cli("get", self.path, node_id)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["uid"]

    # -- out of scope ------------------------------------------------
    def test_write_to_sibling_is_refused_naming_the_allowed_scope(self):
        bad = run_cli("update", self.path, "1-2", "--label", "x", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)
        # Story 30: the error names the allowed scope so the agent can correct
        # the call instead of guessing.
        self.assertIn("1-1", bad.stderr)

    def test_write_to_ancestor_is_refused(self):
        bad = run_cli("update", self.path, "1", "--label", "x", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)

    # -- in scope ----------------------------------------------------
    def test_write_to_scope_root_is_allowed(self):
        ok = run_cli("update", self.path, "1-1", "--label", "x", "--scope", "1-1")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_write_to_descendant_is_allowed(self):
        ok = run_cli("update", self.path, "1-1-1", "--label", "y", "--scope", "1-1")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_scope_accepts_uid_as_well_as_display_id(self):
        uid = self.uid_of("1-1")
        ok = run_cli("update", self.path, "1-1-1", "--label", "z", "--scope", uid)
        self.assertEqual(ok.returncode, 0, ok.stderr)

    # -- add / delete / edge -----------------------------------------
    def test_add_outside_scope_is_refused(self):
        bad = run_cli("add", self.path, "1-2", "C", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)

    def test_add_inside_scope_is_allowed(self):
        ok = run_cli("add", self.path, "1-1", "C", "--scope", "1-1")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_delete_outside_scope_is_refused(self):
        bad = run_cli("delete", self.path, "1-2", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)

    def test_edge_with_an_out_of_scope_endpoint_is_refused(self):
        # an edge is a write too: it must not let a subagent pull a node from
        # outside its subtree into its own dependency graph
        bad = run_cli("edge", "add", self.path, "1-1", "1-2", "--type", "informs", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)

    # -- the control cases -------------------------------------------
    def test_without_scope_every_write_is_unrestricted(self):
        """Regression guard: absent --scope must not become read-only.

        #111 shipped `--as-agent a7 --token 1` (no --scope) as a successful
        write; #113 must not quietly turn that into a denial.
        """
        for target in ("1", "1-1", "1-1-1", "1-2"):
            ok = run_cli("update", self.path, target, "--label", "free")
            self.assertEqual(ok.returncode, 0, f"{target}: {ok.stderr}")

    def test_scope_is_checked_before_the_lease(self):
        """Out of scope is a permission error; it outranks "someone holds it"."""
        self.assertEqual(run_cli("lease", "claim", self.path, "1-2", "--agent", "a7").returncode, 0)
        bad = run_cli("update", self.path, "1-2", "--status", "completed", "--scope", "1-1")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_SCOPE", bad.stderr)
        self.assertNotIn("E_LEASE_HELD", bad.stderr)


class SingleFileScopeCli(ScopeCliContract, unittest.TestCase):
    storage = "single"


class BundleScopeCli(ScopeCliContract, unittest.TestCase):
    storage = "bundle"


# ── Slice 4: field-level ownership through the CLI ──

class OwnershipCliContract:
    """status/notes 归租约持有者；planner 字段与追加型 decisions 不受阻。

    这些用例同时是 #111 的回归防线：把守卫退回"租约期内一切写都拦"时，
    planner 字段那几条必须变红。
    """

    storage = "single"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / ("roadmap.json" if self.storage == "single" else "roadmap.bundle")
        init = run_cli("init", str(path), "--title", "ownership", "--storage", self.storage)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.path = str(path)
        self.assertEqual(run_cli("add", self.path, "1", "A").returncode, 0)
        claim = run_cli("lease", "claim", self.path, "1-1", "--agent", "a7")
        self.assertEqual(claim.returncode, 0, claim.stderr)
        self.holder = ["--as-agent", "a7", "--token", "1"]

    def tearDown(self):
        self.tmp.cleanup()

    def label_of(self, node_id="1-1") -> str:
        out = run_cli("get", self.path, node_id)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["label"]

    # -- planner fields: never blocked -------------------------------
    def test_label_is_writable_while_another_agent_holds_the_lease(self):
        ok = run_cli("update", self.path, "1-1", "--label", "renamed")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(self.label_of(), "renamed")

    def test_mode_is_writable_while_another_agent_holds_the_lease(self):
        ok = run_cli("update", self.path, "1-1", "--mode", "exploit")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_budget_is_writable_while_another_agent_holds_the_lease(self):
        ok = run_cli("update", self.path, "1-1", "--max-children", "3")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_exit_criteria_is_writable_while_another_agent_holds_the_lease(self):
        ok = run_cli("update", self.path, "1-1", "--exit-criteria", "done")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    # -- executor fields: lease holder only --------------------------
    def test_status_is_blocked_for_non_holders(self):
        bad = run_cli("update", self.path, "1-1", "--status", "completed")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)

    def test_notes_are_blocked_for_non_holders(self):
        bad = run_cli("update", self.path, "1-1", "--notes", "progress")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)

    def test_holder_can_still_write_executor_fields(self):
        ok = run_cli("update", self.path, "1-1", "--status", "completed", *self.holder)
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_mixed_write_is_blocked_and_writes_nothing(self):
        """一次 update 里带了执行者字段 → 整条拒绝，planner 字段也不落盘。

        半写入比全拒更难诊断：调用方会以为 label 改成了。
        """
        bad = run_cli("update", self.path, "1-1", "--label", "half", "--status", "completed")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)
        self.assertNotEqual(self.label_of(), "half")

    # -- decisions: append-only --------------------------------------
    def test_decision_append_is_never_blocked(self):
        """追加不覆盖 → 永不冲突 → 不过租约闸（Story 32 的 so that）。"""
        ok = run_cli("decide", self.path, "1-1", "q1", "a1")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_decisions_are_append_only(self):
        self.assertEqual(run_cli("decide", self.path, "1-1", "q1", "a1").returncode, 0)
        self.assertEqual(run_cli("decide", self.path, "1-1", "q2", "a2").returncode, 0)
        # 撤回也要留痕：原条目必须在（retract-and-keep，#112 的语义）
        self.assertEqual(
            run_cli("remove-decision", self.path, "1-1", "--index", "0", *self.holder).returncode, 0)
        out = run_cli("decisions", self.path, "1-1")
        self.assertEqual(out.returncode, 0, out.stderr)
        decisions = json.loads(out.stdout)
        self.assertEqual([d["q"] for d in decisions if not d.get("retracted")], ["q1", "q2"])
        self.assertEqual(sum(1 for d in decisions if d.get("retracted")), 1)

    def test_retracting_a_decision_is_lease_guarded(self):
        """撤回是权威动作（动别人的记录），不是追加——仍过租约闸。"""
        self.assertEqual(run_cli("decide", self.path, "1-1", "q1", "a1").returncode, 0)
        bad = run_cli("remove-decision", self.path, "1-1", "--index", "0")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("E_LEASE_HELD", bad.stderr)

    # -- the boundary between fencing and ownership ------------------
    def test_fenced_out_holder_is_blocked_even_on_planner_fields(self):
        """出示已作废 token 的僵尸持有者：任何字段都拒，包括 planner 字段。

        fencing 防的是"被回收的旧持有者醒来继续写"（spec §4）。若只按字段放行，
        僵尸 Agent 把 `--status` 换成 `--label` 就能绕过去——那 fencing 就等于没有。
        这条同时钉住 #111 与 #113 的接缝：`test_lease` 的 `--label` + 旧 token
        用例必须继续红于"退回仅在 status 上查租赁"的实现。
        """
        self.assertEqual(
            run_cli("lease", "release", self.path, "1-1", "--agent", "a7", "--force").returncode, 0)
        self.assertEqual(
            run_cli("lease", "claim", self.path, "1-1", "--agent", "a7", "--ttl", "1").returncode, 0)
        time.sleep(1.2)  # 让 1s TTL 过期后才能 steal
        steal = run_cli("lease", "steal", self.path, "1-1", "--agent", "a8")
        self.assertEqual(steal.returncode, 0, steal.stderr)
        self.assertIn('"fencing_token": 2', steal.stdout)

        stale = run_cli("update", self.path, "1-1", "--label", "zombie",
                        "--as-agent", "a7", "--token", "1")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("E_LEASE_HELD", stale.stderr)

        # 同一时刻：没出示凭据的第三方写 planner 字段仍然合法。
        ok = run_cli("update", self.path, "1-1", "--label", "planner")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(self.label_of(), "planner")


class SingleFileOwnershipCli(OwnershipCliContract, unittest.TestCase):
    storage = "single"


class BundleOwnershipCli(OwnershipCliContract, unittest.TestCase):
    storage = "bundle"


if __name__ == "__main__":
    unittest.main(verbosity=2)

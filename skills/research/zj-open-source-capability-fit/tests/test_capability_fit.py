#!/usr/bin/env python3
"""zj-open-source-capability-fit 回归测试 (stdlib unittest).

覆盖: 有效拟合度乘积、满足判定、关键缺口->D、可控B边界->C/D、
A/B1/B2/B3/C 分类边界、机械闸门拒绝 (缺矩阵/缺证据/缺版本)。
"""

import json
import os
import tempfile
import unittest

from scripts.capability_fit import (
    effective_fit, cell_satisfied, is_must, run_gates,
    classify_candidate, main, FIT_OK, FIT_FAIL,
)


def _cell(coverage, semantic, composability, status, evidence="src:x"):
    return {"coverage": coverage, "semantic_match": semantic,
            "composability": composability, "status": status,
            "evidence": evidence, "notes": "test fixture"}


def _base(reqs, matrix, cost=None, adaptation=None):
    data = {
        "goal": "test",
        "requirements": reqs,
        "candidates": [{"id": "O1", "name": "O1", "url": "u", "version": "v1", "license": "MIT"}],
        "matrix": {"O1": matrix},
    }
    if cost is not None:
        data["cost"] = {"O1": cost}
    if adaptation is not None:
        data["adaptation"] = {"O1": adaptation}
    return data


class TestFitMath(unittest.TestCase):
    def test_effective_fit_product(self):
        self.assertAlmostEqual(effective_fit(_cell(1.0, 0.5, 0.5, "native")), 0.25)

    def test_effective_fit_clamps(self):
        self.assertAlmostEqual(effective_fit(_cell(2.0, 1.0, 1.0, "native")), 1.0)

    def test_cell_satisfied_threshold(self):
        self.assertTrue(cell_satisfied(_cell(1.0, 1.0, 1.0, "native")))
        self.assertFalse(cell_satisfied(_cell(1.0, 1.0, 0.8, "native")))  # 0.8<0.9
        self.assertFalse(cell_satisfied(_cell(1.0, 1.0, 1.0, "unknown")))

    def test_is_must(self):
        self.assertTrue(is_must({"priority": "must", "critical": False}))
        self.assertTrue(is_must({"priority": "want", "critical": True}))
        self.assertFalse(is_must({"priority": "nice", "critical": False}))


class TestCriticalGap(unittest.TestCase):
    def test_unsupported_must_forces_D(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            {"R1": _cell(0.0, 0.0, 0.0, "unsupported")},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "D")
        self.assertTrue(res.critical_gap)

    def test_unknown_must_forces_D(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            {"R1": _cell(0.0, 0.0, 0.0, "unknown")},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "D")

    def test_low_fit_must_forces_D(self):
        # 有效拟合度 < FIT_FAIL (0.5) 但状态 native -> 关键缺口
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            {"R1": _cell(0.8, 0.8, 0.8, "native")},  # 0.512 >=0.5 -> 注意边界
        )
        res = classify_candidate(data, "O1")
        self.assertGreaterEqual(effective_fit(data["matrix"]["O1"]["R1"]), FIT_FAIL)
        # 0.512>=0.5 不算关键缺口, 但 0.512<0.9 -> must_gap
        self.assertNotEqual(res.recommended, "D")

    def test_just_below_fail_is_D(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            {"R1": _cell(0.7, 0.7, 0.7, "native")},  # 0.343 < 0.5
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "D")


class TestControlledBBoundary(unittest.TestCase):
    def _good_matrix(self):
        return {"R1": _cell(1.0, 1.0, 1.0, "native")}

    def test_forbidden_plus_uncontrolled_D(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            self._good_matrix(),
            adaptation={"scope": ["storage-sync-infra"], "mode": "adapter",
                        "responsibility_uncontrolled": True, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "D")
        self.assertTrue(res.forbidden_touched)

    def test_forbidden_controlled_C(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            self._good_matrix(),
            adaptation={"scope": ["storage-sync-infra"], "mode": "adapter",
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "C")


class TestClassification(unittest.TestCase):
    def _full_native(self):
        return {"R1": _cell(1.0, 1.0, 1.0, "native"),
                "R2": _cell(1.0, 1.0, 1.0, "native")}

    def test_A_direct(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            self._full_native(),
            cost={"initial_dev": 0, "integration": 0, "maintenance": 0,
                  "upstream_adapt": 0, "ops": 0, "security_gov": 0},
            adaptation={"scope": [], "mode": None, "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "A")

    def test_B1_adapter(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native"),
                  "R2": _cell(1.0, 1.0, 1.0, "adapted")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            matrix,
            cost={"initial_dev": 10, "integration": 5, "maintenance": 5,
                  "upstream_adapt": 0, "ops": 0, "security_gov": 0},
            adaptation={"scope": ["query-adapt"], "mode": "adapter",
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "B1")

    def test_B2_upstream(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native"),
                  "R2": _cell(1.0, 1.0, 1.0, "adapted")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            matrix,
            cost={"initial_dev": 10, "integration": 5, "maintenance": 5, "upstream_adapt": 0, "ops": 0, "security_gov": 0},
            adaptation={"scope": ["query-adapt"], "mode": "upstream-contrib",
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "B2")

    def test_B3_fork(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native"),
                  "R2": _cell(1.0, 1.0, 1.0, "adapted")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            matrix,
            cost={"initial_dev": 10, "integration": 5, "maintenance": 5, "upstream_adapt": 0, "ops": 0, "security_gov": 0},
            adaptation={"scope": ["query-adapt"], "mode": "fork",
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "B3")

    def test_B_needs_mode(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native"),
                  "R2": _cell(1.0, 1.0, 1.0, "adapted")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            matrix,
            cost={"initial_dev": 10, "integration": 5, "maintenance": 5, "upstream_adapt": 0, "ops": 0, "security_gov": 0},
            adaptation={"scope": ["query-adapt"], "mode": None,
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "B")

    def test_C_high_cost(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native"),
                  "R2": _cell(1.0, 1.0, 1.0, "adapted")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            matrix,
            cost={"initial_dev": 100, "integration": 100, "maintenance": 100, "upstream_adapt": 100, "ops": 100, "security_gov": 100},
            adaptation={"scope": ["query-adapt"], "mode": "adapter",
                        "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "C")


class TestGates(unittest.TestCase):
    def test_gate_matrix_incomplete_blocks(self):
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"},
             {"id": "R2", "statement": "s", "priority": "want", "critical": False, "acceptance": "a"}],
            {"R1": _cell(1.0, 1.0, 1.0, "native")},  # 缺 R2
        )
        gates = run_gates(data, "O1")
        self.assertTrue(any(not g.ok for g in gates))
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "BLOCKED")

    def test_gate_missing_evidence_blocks(self):
        matrix = {"R1": _cell(1.0, 1.0, 1.0, "native", evidence="")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            matrix,
        )
        gates = run_gates(data, "O1")
        self.assertTrue(any(g.name == "G4-evidence-present" and not g.ok for g in gates))
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "BLOCKED")

    def test_gate_version_missing_blocks(self):
        data = {
            "goal": "t",
            "requirements": [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            "candidates": [{"id": "O1", "name": "O1", "url": "u", "version": "", "license": "MIT"}],
            "matrix": {"O1": {"R1": _cell(1.0, 1.0, 1.0, "native")}},
        }
        gates = run_gates(data, "O1")
        self.assertTrue(any(g.name == "G3-version-pinned" and not g.ok for g in gates))
        res = classify_candidate(data, "O1")
        self.assertEqual(res.recommended, "BLOCKED")

    def test_gate_unknown_must_needs_poc(self):
        matrix = {"R1": _cell(0.0, 0.0, 0.0, "unknown")}
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            matrix,
            adaptation={"scope": [], "mode": None, "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        gates = run_gates(data, "O1")
        self.assertTrue(any(g.name == "G5-unknown-poc-plan" and not g.ok for g in gates))


class TestAssessExitCode(unittest.TestCase):
    """契约: 退出码 1 仅当硬闸门(G1-G4)未过; G5(就绪度提示)不影响退出码."""

    def _write(self, data: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".json", prefix="capfit_exit_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path

    def test_G5_failure_keeps_exit_0(self):
        # 关键需求 unknown -> 分类 D(自信产出); 同时 G5 失败(无 poc_plan)
        # 按合同 G5 不阻塞 -> 退出码应为 0
        data = _base(
            [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            {"R1": _cell(0.0, 0.0, 0.0, "unknown")},
            adaptation={"scope": [], "mode": None, "responsibility_uncontrolled": False, "poc_plan": ""},
        )
        path = self._write(data)
        try:
            rc = main(["assess", "--input", path, "--json"])
        finally:
            os.unlink(path)
        self.assertEqual(rc, 0)

    def test_hard_gate_failure_exits_1(self):
        # G3 版本缺失 -> 硬闸门, 退出码应为 1
        data = {
            "goal": "t",
            "requirements": [{"id": "R1", "statement": "s", "priority": "must", "critical": True, "acceptance": "a"}],
            "candidates": [{"id": "O1", "name": "O1", "url": "u", "version": "", "license": "MIT"}],
            "matrix": {"O1": {"R1": _cell(1.0, 1.0, 1.0, "native")}},
        }
        path = self._write(data)
        try:
            rc = main(["assess", "--input", path, "--json"])
        finally:
            os.unlink(path)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

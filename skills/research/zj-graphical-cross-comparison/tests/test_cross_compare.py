#!/usr/bin/env python3
"""zj-graphical-cross-comparison 闸门回归守卫。

红绿纪律：每一条测试都对应 agreement 的一条复核条件或一条不变量；
缺陷态必须 FAIL，修复态必须 PASS，绝不接受「脚本返回 0 就算过」。
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import cross_compare as cc  # noqa: E402

FIXTURE = SKILL_DIR / "tests" / "fixtures" / "valid-bundle.json"
YAML_FIXTURE = SKILL_DIR / "tests" / "fixtures" / "valid-bundle.yaml"
SCRIPT = SKILL_DIR / "scripts" / "cross_compare.py"
try:
    import yaml as _yaml
    HAS_YAML = True
except ModuleNotFoundError:  # pragma: no cover - YAML 路径在无 PyYAML 环境跳过
    HAS_YAML = False


def load_valid() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def check(checks, code: str):
    return next(item for item in checks if item.code == code)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


class GateTests(unittest.TestCase):
    def test_valid_bundle_passes_all_ten_checks(self):
        checks = cc.run_checks(load_valid())
        self.assertEqual(len(checks), 10)
        failures = [f"{c.code}: {c.problems}" for c in checks if not c.ok]
        self.assertEqual([], failures)

    def test_chk03_unruled_relation_blocks_stage_3(self):
        data = load_valid()
        data["graphs"][0]["undeclared-relations"].append({
            "id": "UR::unruled", "elements": [], "description": "疑似依赖但无裁决",
            "candidate-interpretations": ["补依赖边"], "impact": "DE::0001",
            "ruling-result": "unknown",
        })
        result = check(cc.run_checks(data), "CHK-03")
        self.assertFalse(result.ok)
        self.assertEqual("error", result.severity)

    def test_chk03_unruled_without_differences_is_warning_only(self):
        data = load_valid()
        data["graphs"][0]["undeclared-relations"].append({
            "id": "UR::unruled", "elements": [], "description": "疑似依赖但无裁决",
            "candidate-interpretations": ["补依赖边"], "impact": "DE::0001",
            "ruling-result": "unknown",
        })
        data["difference-entries"] = []
        result = check(cc.run_checks(data), "CHK-03")
        self.assertFalse(result.ok)
        self.assertEqual("warning", result.severity)

    def test_chk02_slice_requires_both_feature_and_capability(self):
        data = load_valid()
        data["graphs"][0]["slice-edges"][0]["members"] = ["F::personal-shared-scope"]
        self.assertFalse(check(cc.run_checks(data), "CHK-02").ok)

    def test_chk02_context_entry_cannot_enter_slice_members(self):
        data = load_valid()
        data["graphs"][0]["slice-edges"][0]["members"].append("CTX::data-residency")
        result = check(cc.run_checks(data), "CHK-02")
        self.assertFalse(result.ok)
        self.assertTrue(any("CTX::" in problem for problem in result.problems))

    def test_chk02_dependency_relation_must_be_requires(self):
        data = load_valid()
        data["graphs"][0]["dependency-edges"][0]["relation"] = "co-varies"
        self.assertFalse(check(cc.run_checks(data), "CHK-02").ok)

    def test_chk04_scene_set_must_be_external(self):
        data = load_valid()
        data["scene-set"]["derived-from-graphs"] = True
        self.assertFalse(check(cc.run_checks(data), "CHK-04").ok)

    def test_chk04_scene_cannot_prescribe_modules(self):
        data = load_valid()
        data["scene-set"]["scenes"][0]["required-nodes"] = ["F::personal-shared-scope"]
        self.assertFalse(check(cc.run_checks(data), "CHK-04").ok)

    def test_chk05_equivalence_ruling_needs_both_acceptance(self):
        data = load_valid()
        data["equivalence-rulings"].append({
            "id": "EQ::001",
            "left": "P1::F::personal-shared-scope",
            "right": "P1::T::scoped-memory",
            "left-acceptance": "同一目标可在两种空间分别创建",
            "ruling-by": "zj",
        })
        self.assertFalse(check(cc.run_checks(data), "CHK-05").ok)

    def test_chk06_unsupported_needs_explicit_negative_statement(self):
        data = load_valid()
        entry = data["difference-entries"][0]
        entry["verdict"] = "unsupported"
        self.assertFalse(check(cc.run_checks(data), "CHK-06").ok)

    def test_chk06_unknown_needs_verification_plan(self):
        data = load_valid()
        entry = data["difference-entries"][0]
        entry["verdict"] = "unknown"
        entry["context-refs"] = []
        entry["context-verdicts"] = []
        self.assertFalse(check(cc.run_checks(data), "CHK-06").ok)

    def test_chk06_context_unknown_needs_verification_plan(self):
        data = load_valid()
        data["difference-entries"][0]["context-verdicts"][0] = {
            "ref": "CTX::data-residency", "verdict": "unknown",
        }
        self.assertFalse(check(cc.run_checks(data), "CHK-06").ok)

    def test_chk07_requires_human_review_note(self):
        data = load_valid()
        data["optional-scene-pool-review"] = {}
        self.assertFalse(check(cc.run_checks(data), "CHK-07").ok)

    def test_chk08_orphan_nodes_are_warning_only(self):
        data = load_valid()
        data["graphs"][0]["orphan-nodes"] = ["F::personal-shared-scope"]
        result = check(cc.run_checks(data), "CHK-08")
        self.assertFalse(result.ok)
        self.assertEqual("warning", result.severity)

    def test_chk09_summary_metrics_cannot_rank(self):
        data = load_valid()
        data["summary-metrics-usage"] = "ranking"
        self.assertFalse(check(cc.run_checks(data), "CHK-09").ok)

    def test_chk09_report_needs_eight_sections(self):
        data = load_valid()
        data["report-sections"].pop()
        self.assertFalse(check(cc.run_checks(data), "CHK-09").ok)

    def test_chk10_domain_entry_cannot_be_scoped_project(self):
        data = load_valid()
        data["scene-set"]["context-entries"][0]["scope"] = "project"
        self.assertFalse(check(cc.run_checks(data), "CHK-10").ok)

    def test_chk10_context_entry_cannot_hold_graph_fields(self):
        data = load_valid()
        data["graphs"][0]["context-entries"][0]["members"] = ["F::personal-shared-scope"]
        self.assertFalse(check(cc.run_checks(data), "CHK-10").ok)

    def test_chk01_version_pin_is_mandatory(self):
        data = load_valid()
        data["graphs"][0].pop("version-pin")
        self.assertFalse(check(cc.run_checks(data), "CHK-01").ok)


class MetricTests(unittest.TestCase):
    def test_metrics_are_never_conclusions(self):
        metrics = cc.summary_metrics(load_valid())
        self.assertTrue(metrics["not_for_conclusion"])
        self.assertEqual("display-only", metrics["usage"])
        self.assertEqual(0, metrics["undecided-stock"])

    def test_fan_in_dependency_closure_and_no_scc_on_acyclic_graph(self):
        graph = cc.summary_metrics(load_valid())["graphs"][0]
        self.assertEqual([], graph["scc-size-distribution"])
        self.assertEqual(2, graph["max-dependency-closure"])
        self.assertEqual(1, graph["fan-in-distribution"]["T::scoped-memory"])
        self.assertEqual(1.0, graph["slice-coverage"])
        self.assertEqual(0.0, graph["sharing-degree"])

    def test_scc_only_counts_cycles_not_fan_in_clusters(self):
        data = load_valid()
        data["graphs"][0]["dependency-edges"].append({
            "id": "D::memory-requires-scope",
            "from": "T::scoped-memory",
            "to": "F::personal-shared-scope",
            "relation": "requires",
            "evidence-ref": "P1/src/scopes.py#L30",
        })
        graph = cc.summary_metrics(data)["graphs"][0]
        self.assertEqual([2], graph["scc-size-distribution"])

    def test_context_entries_are_excluded_from_coverage_denominator(self):
        data = load_valid()
        before = cc.summary_metrics(data)["graphs"][0]["evidence-binding-coverage"]
        data["graphs"][0]["context-entries"].append({
            "id": "CTX::extra", "scope": "project", "kind": "actor",
            "statement": "审批人", "evidence-ref": "P1/docs/roles.md",
        })
        self.assertEqual(before, cc.summary_metrics(data)["graphs"][0]["evidence-binding-coverage"])


class CliTests(unittest.TestCase):
    def test_valid_fixture_exits_zero(self):
        result = run_cli("validate", "--input", str(FIXTURE))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("0 ERROR", result.stdout)

    def test_defect_fixture_exits_one_with_chk03(self):
        data = load_valid()
        data["graphs"][0]["undeclared-relations"].append({
            "id": "UR::unruled", "elements": [], "description": "疑似依赖但无裁决",
            "candidate-interpretations": ["补依赖边"], "impact": "DE::0001",
            "ruling-result": "unknown",
        })
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "defect.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_cli("validate", "--input", str(path))
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("FAIL CHK-03", result.stdout)

    def test_report_without_out_only_prints(self):
        result = run_cli("report", "--input", str(FIXTURE))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["not_for_conclusion"])

    def test_init_requires_explicit_out(self):
        result = run_cli("init")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("--out", result.stderr)

    def test_init_template_is_a_valid_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "template.json"
            result = run_cli("init", "--out", str(path))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(cc.SCHEMA, payload["schema"])
            self.assertFalse(payload["scene-set"]["derived-from-graphs"])


@unittest.skipUnless(HAS_YAML, "PyYAML is not installed; YAML parity skipped")
class YamlParityTests(unittest.TestCase):
    """agreement 的 SoT 是 YAML：它必须是一等输入，不是被降级成 JSON 的替身。"""

    def test_yaml_fixture_is_semantically_identical_to_json_fixture(self):
        from_yaml = _yaml.safe_load(YAML_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(load_valid(), from_yaml)

    def test_yaml_and_json_produce_identical_gate_results(self):
        def shape(checks):
            return [(c.code, c.severity, c.problems, c.note) for c in checks]
        self.assertEqual(
            shape(cc.run_checks(load_valid())),
            shape(cc.run_checks(cc.load(str(YAML_FIXTURE)))),
        )

    def test_cli_validate_accepts_yaml_directly(self):
        result = run_cli("validate", "--input", str(YAML_FIXTURE))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("0 ERROR", result.stdout)

    def test_cli_init_yaml_roundtrips(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bundle.yaml"
            result = run_cli("init", "--out", str(path))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = _yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(cc.SCHEMA, payload["schema"])
            self.assertIs(False, payload["scene-set"]["derived-from-graphs"])

    def test_yaml_non_mapping_top_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "not-a-bundle.yaml"
            path.write_text("- one\n- two\n", encoding="utf-8")
            result = run_cli("validate", "--input", str(path))
            self.assertEqual(1, result.returncode)
            self.assertIn("mapping", result.stderr)

    def test_report_can_emit_yaml_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metrics.yaml"
            result = run_cli("report", "--input", str(YAML_FIXTURE), "--out", str(path))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = _yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["not_for_conclusion"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

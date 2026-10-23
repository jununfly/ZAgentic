"""F8 一致性守卫：死链 docstring + drift harness CLI 退出码语义 (stdlib unittest)."""

import importlib.util
import pathlib
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
DRIFT_HARNESS = REPO / "tests/ui_agent_skills_drift_harness.py"
GOLDEN = REPO / "tests/ui-agent-skills/fixtures/adapters/F-A2/json-render"

DELETED_REF = "ui-agent-skills-roadmap.json"  # 路线图已收口清理，不得再被引用


def _module_doc(path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.__doc__ or ""


class DeadLinkDocstringTest(unittest.TestCase):
    def test_scripts_no_longer_reference_deleted_roadmap(self):
        for name in ("hard_gates.py", "verification_receipt.py", "dual_lane_runner.py"):
            doc = _module_doc(SCRIPTS / name)
            self.assertNotIn(
                DELETED_REF, doc,
                f"{name} 仍引用已删除的 {DELETED_REF}",
            )


class DriftHarnessCliTest(unittest.TestCase):
    def _run(self, baseline, candidate, *extra):
        proc = subprocess.run(
            [sys.executable, str(DRIFT_HARNESS), str(baseline), str(candidate), *extra],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stdout

    def test_identical_golden_exits_zero(self):
        rc, _ = self._run(
            GOLDEN / "FF-JR-PROJ-01/expected.json",
            GOLDEN / "FF-JR-PROJ-01/expected.json",
            "--baseline-anchor", str(GOLDEN / "anchor.json"),
            "--candidate-anchor", str(GOLDEN / "anchor.json"),
        )
        self.assertEqual(rc, 0)

    def test_semantic_loss_exits_one(self):
        import copy
        import json
        base = json.loads((GOLDEN / "FF-JR-PROJ-01/expected.json").read_text(encoding="utf-8"))
        cand = copy.deepcopy(base)
        cand["projection"]["elements"].pop("btn-detail", None)
        tmp = GOLDEN / "_candidate_tmp.json"
        tmp.write_text(json.dumps(cand, ensure_ascii=False), encoding="utf-8")
        try:
            rc, _ = self._run(
                GOLDEN / "FF-JR-PROJ-01/expected.json", tmp,
                "--baseline-anchor", str(GOLDEN / "anchor.json"),
                "--candidate-anchor", str(GOLDEN / "anchor.json"),
            )
            self.assertEqual(rc, 1)
        finally:
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

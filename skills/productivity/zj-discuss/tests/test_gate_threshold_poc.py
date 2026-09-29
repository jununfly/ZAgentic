#!/usr/bin/env python3
import unittest
"""Regression guard for the R1 gate-threshold PoC calibration.

Prevents the per-role ``N`` declaration in ``role-methods/*.md`` from silently
drifting away from the ratified value recorded in ``design.md`` §10.6 R1.

Rationale (see design.md §10.6 R1 + skills-outputs/zj-discuss/n-threshold-poc):
- B/A (and the 10 optional roles) keep N=3 (base default).
- C drops to N=2 for solo/internal sub-problems (no real market signal),
  N=3 when an external market signal is present.
- The stale "待 PoC 校准" wording must be gone everywhere (calibration done).
"""

import pathlib

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
ROLE_METHODS = SKILL_DIR / "references" / "role-methods"
REPO_ROOT = SKILL_DIR.parent.parent.parent
DESIGN = REPO_ROOT / "docs" / "designs" / "zj-discuss" / "design.md"
PROTOCOL = REPO_ROOT / "skills-outputs" / "zj-discuss" / "n-threshold-poc" / "protocol.md"
PROBE = REPO_ROOT / "skills-outputs" / "zj-discuss" / "n-threshold-poc" / "probe-views.md"

OPTIONAL_KEYS = ["T", "S", "O", "D", "L", "F", "U", "R", "P", "E"]
ALL_NON_C = ["B", "A"] + OPTIONAL_KEYS  # 12 files


class TestGateThresholdPoC(unittest.TestCase):
    def test_all_role_method_files_present(self):
        for key in ["B", "C", "A"] + OPTIONAL_KEYS:
            self.assertTrue(
                (ROLE_METHODS / f"{key}.md").exists(), f"missing role-method {key}"
            )

    def test_non_c_files_declare_n3_and_not_stale(self):
        for key in ALL_NON_C:
            text = (ROLE_METHODS / f"{key}.md").read_text(encoding="utf-8")
            self.assertIn("N = 3", text, f"{key}.md missing 'N = 3' declaration")
            self.assertNotIn(
                "待 PoC 校准", text, f"{key}.md still has stale '待 PoC 校准'"
            )

    def test_c_file_conditional_n(self):
        text = (ROLE_METHODS / "C.md").read_text(encoding="utf-8")
        self.assertIn("N = 2", text, "C.md missing solo N=2 declaration")
        self.assertIn("N = 3", text, "C.md missing market-signal N=3 declaration")
        self.assertIn("solo", text.lower(), "C.md missing solo-exemption wording")
        self.assertIn("⑤", text, "C.md missing '⑤ C 专属' exemption section")

    def test_design_doc_records_calibration(self):
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("N=3", text, "design.md §10.6 R1 missing ratified N=3")
        self.assertIn("N=2", text, "design.md §10.6 R1 missing ratified C solo N=2")
        self.assertIn("solo", text.lower(), "design.md §10.6 R1 missing solo context")

    def test_poc_artifacts_exist(self):
        self.assertTrue(PROTOCOL.exists(), "PoC protocol.md missing")
        self.assertTrue(PROBE.exists(), "PoC probe-views.md missing")


if __name__ == "__main__":
    unittest.main()

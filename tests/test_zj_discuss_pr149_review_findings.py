"""Regression guard for PR #149 code-review findings on zj-discuss / zj-discuss-view.

Seam under test: the contract between the durable SPEC (docs/designs/zj-discuss/design.md)
and the IMPLEMENTATION (the two SKILL.md files + bucket README). The defect class the
review caught was *spec/implementation drift* — this test makes that drift fail loudly.

All assertions derive from the review's required fixes (independent source of truth),
not from recomputing the code's own wording, so they survive rephrasing.
"""

import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/productivity/zj-discuss/SKILL.md"
VIEW = REPO / "skills/productivity/zj-discuss-view/SKILL.md"
DESIGN = REPO / "docs/designs/zj-discuss/design.md"
BUCKET_README = REPO / "skills/productivity/README.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    s = text.index(start_marker)
    e = text.index(end_marker, s)
    return text[s:e]


class TestPr149ReviewFindings(unittest.TestCase):
    # --- Standards finding S1: design.md §2 R1 overclaims `--role X,Y` ---
    def test_design_r1_no_x_comma_overclaim(self):
        d = _read(DESIGN)
        # The exact overclaim phrase must be gone: `--all` superseded the X,Y syntax.
        self.assertNotIn(
            "`--role X,Y` 按需增删",
            d,
            "design.md §2 R1 still claims `--role X,Y` comma syntax is implemented; "
            "`--all` supersedes it (see SKILL.md which only has `--role <single>` + `--all`).",
        )
        # The implemented mechanism must be referenced instead.
        self.assertIn("`--all`", d, "design.md §2 R1 should reference the implemented `--all`.")

    # --- Spec finding SP1: dynamic agenda must be wired into the Phase 2 workflow ---
    def test_phase2_wires_agenda(self):
        s = _read(SKILL)
        phase2 = _section(s, "### Phase 2", "### Phase 3")
        self.assertIn(
            "研讨会议程",
            phase2,
            "Phase 2 must cross-reference the fixed+dynamic agenda section so it is not orphaned.",
        )
        self.assertIn(
            "动态议程决策",
            phase2,
            "Phase 2 must name the dynamic-agenda decision function as the per-round driver.",
        )

    # --- Spec finding SP2: dynamic agenda must not invent a role outside the pool (SSOT) ---
    def test_dynamic_agenda_no_ssot_violation(self):
        s = _read(SKILL)
        # role-matrix.md is the sole source of roles; no "supplemental role" may be invented.
        self.assertNotIn(
            "补充角色",
            s,
            "Dynamic agenda decision function invents a role outside role-matrix.md pool (SSOT violation).",
        )
        # The disagreement branch must prescribe restarting genuine isolation instead.
        self.assertIn(
            "重开真隔离会话对齐分歧",
            s,
            "Dynamic agenda must prescribe restarting a genuine-isolation session to align disagreement, "
            "not adding an out-of-pool role.",
        )

    # --- Spec finding SP3: F2 must clarify manual (Human) copy, not auto-distribution ---
    def test_f2_clarifies_manual_distribution(self):
        s = _read(SKILL)
        f2 = _section(s, "**F2", "**F3")
        self.assertIn("Human", f2, "F2 must name the Human as the one who copies briefings.")
        self.assertIn("复制", f2, "F2 must state briefings are copied (not auto-distributed).")

    # --- Standards finding S2 (minor): bucket README must advertise the new capabilities ---
    def test_bucket_readme_advertises_capabilities(self):
        r = _read(BUCKET_README)
        self.assertIn("role pool", r, "Bucket README undersells: missing role-pool mention.")
        self.assertIn("fixed", r, "Bucket README undersells: missing fixed-agenda mention.")
        self.assertIn("dynamic agenda", r, "Bucket README undersells: missing dynamic-agenda mention.")


if __name__ == "__main__":
    unittest.main()

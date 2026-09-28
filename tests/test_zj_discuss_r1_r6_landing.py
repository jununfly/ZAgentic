"""Anti-drift guard: R1–R6 must be LAND IN THE SKILL, not only in the spec.

Origin of this test: the previous round recorded these six revisions in
``design.md`` as "written back" while most of them never reached the skill
files. A doc-counting diff looked like progress; the behaviour never changed.

This guard therefore asserts *presence in the shipped artifact* — the SKILL,
the template, and the scripts on disk — rather than presence in a design doc.
If any of these landings is reverted or edited away, this fails loudly.
"""

import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/productivity/zj-discuss/SKILL.md"
VIEW = REPO / "skills/productivity/zj-discuss-view/SKILL.md"
TEMPLATE = REPO / "skills/productivity/zj-discuss/references/subdoc-template.md"
DESIGN = REPO / "docs/designs/zj-discuss/design.md"
SCRIPTS = REPO / "skills/productivity/zj-discuss/scripts"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class LandedInSkillNotJustDocs(unittest.TestCase):
    """R2 / R3 / R5: the artifact itself must carry the change."""

    def test_r2_generator_referenced_by_skill(self):
        self.assertIn(
            "scripts/launch_pack.py",
            _read(SKILL),
            "R2 regressed: the generator is no longer referenced from zj-discuss/SKILL.md.",
        )

    def test_r2_generator_actually_exists_on_disk(self):
        self.assertTrue(
            (SCRIPTS / "launch_pack.py").exists(),
            "R2 regressed: scripts/launch_pack.py is gone from disk.",
        )

    def test_r3_gate_referenced_by_skill(self):
        self.assertIn(
            "scripts/check_subdoc.py",
            _read(SKILL),
            "R3 regressed: the structural gate is no longer referenced from the SKILL.",
        )

    def test_r3_gate_actually_exists_on_disk(self):
        self.assertTrue(
            (SCRIPTS / "check_subdoc.py").exists(),
            "R3 regressed: scripts/check_subdoc.py is gone from disk.",
        )

    def test_r3_status_protocol_in_template(self):
        body = _read(TEMPLATE)
        for token in ("状态协议", "DONE_WITH_CONCERNS", "launchpack", "⚠ 非独立"):
            self.assertIn(token, body, "R3 regressed: template lost {}.".format(token))

    def test_r5_integration_boundary_lives_in_skill(self):
        body = _read(SKILL)
        for token in ("外部能力集成边界", "组件引用", "薄层复用", "voice-only"):
            self.assertIn(
                token,
                body,
                "R5 regressed: the boundary is documented elsewhere but not in the SKILL "
                "(prescribed landing spot) — missing {}.".format(token),
            )

    def test_r1_xy_syntax_closure_is_recorded(self):
        self.assertIn(
            "closed",
            _read(SKILL),
            "R1 closure regressed: SKILL.md no longer records that --role X,Y is closed.",
        )
        # One session, one viewpoint — no comma syntax anywhere in the companion.
        self.assertNotIn(
            "--role X,Y",
            _read(VIEW),
            "R1 violated: zj-discuss-view must not advertise multi-role-per-session.",
        )

    def test_design_rows_point_at_real_artifacts(self):
        design = _read(DESIGN)
        # Guard against the earlier failure mode: a row marked "已回写" that
        # describes no actual artifact.
        for row_marker, artifact in (
            ("| R2 |", "scripts/launch_pack.py"),
            ("| R3 |", "scripts/check_subdoc.py"),
        ):
            start = design.index(row_marker)
            row = design[start : design.index("\n", start)]
            self.assertIn(
                artifact,
                row,
                "{} row claims write-back without naming the shipped artifact.".format(
                    row_marker.strip("| ")
                ),
            )


    def test_r7_non_degradation_self_check_landed_in_skill(self):
        """R7 is a sub-clause of prescription 4, found only by counting finely."""
        body = _read(SKILL)
        for token in ("独立性阶梯", "非降级自检项", "跨 provider", "锚点"):
            self.assertIn(
                token,
                body,
                "R7 regressed: SKILL.md lost {} from the non-degradation self-check.".format(
                    token
                ),
            )
        # The companion must refuse to rubber-stamp a degraded conclusion.
        self.assertIn(
            "anchor, not a rubber stamp",
            _read(VIEW),
            "R7 regressed: zj-discuss-view lost the anchor clause from its hard contract.",
        )


if __name__ == "__main__":
    unittest.main()

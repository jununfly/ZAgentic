"""Anti-drift guard: core disciplines must LAND IN zj-roadmap-driven/SKILL.md.

Precedent: zj-discuss lost its disciplines twice (#153 / #167) when they were
pushed into references to satisfy a line-count target. The script layer stayed
green and the behaviour silently changed; only the landing guard went red.

This guard asserts presence *in the shipped artifact*, not in a design doc.
It also guards the opposite direction: reference-only design material must be
behind a pointer, and an explicit exemption must explain why this SKILL.md is
longer than zj-write-a-skill's 100-line guidance. Line count alone is never a
reason to move a discipline out of the top file.
"""

from __future__ import annotations

import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven"
SKILL_MD = SKILL / "SKILL.md"
VIZ_DESIGN = SKILL / "references" / "viz-design.md"
CLI_REF = SKILL / "references" / "roadmap-cli.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class CoreDisciplineLandsInSkill(unittest.TestCase):
    """If any of these leaves SKILL.md, this file must fail loudly."""

    DISCIPLINES = {
        "authority_boundary": "权威边界 — process-state only",
        "authority_direction": "roadmap → 持久权威 → code/docs",
        "carrier_is_sole_fact_source": "存储载体是过程状态的事实源",
        "markdown_is_a_view": "Markdown 是轻量渐进式视图",
        "scope_gate": "Scope gate — before any node write or project edit",
        "scope_product": "Product execution",
        "scope_acceptance": "Acceptance/evaluation",
        "scope_unclear": "Unclear/mixed",
        "auto_render": "自动 render 是默认且必需",
        "decide_before_direction": "决策不落盘 = 没发生",
        "no_direct_md_edit": "Agent 禁止直接 Read/Edit md 的路线图 section",
        "no_parallel_writes": "Agent 禁止并行执行同一 JSON 的写类命令",
        "progressive_pointers": "## 按需参考",
        "install_path_basis": "SKILL_ROOT",
    }

    def test_every_core_discipline_is_in_the_shipped_skill(self):
        body = _read(SKILL_MD)
        missing = [name for name, needle in self.DISCIPLINES.items() if needle not in body]
        self.assertEqual(
            [],
            missing,
            "core disciplines were pushed out of SKILL.md; script tests stay green "
            "while agent behaviour silently changes (see #153 / #167)",
        )

    def test_readonly_signals_discipline_is_not_lost_with_the_details(self):
        body = _read(SKILL_MD)
        self.assertIn("signals", body)
        self.assertIn("把命令写出来 ≠ 替人跑", body)

    def test_viz_readonly_discipline_is_not_lost_with_the_details(self):
        body = _read(SKILL_MD)
        self.assertIn("绝不回写 carrier", body)


class ExemptionIsDeclared(unittest.TestCase):
    """A long SKILL.md is legitimate only with a stated, guarded reason."""

    def test_exemption_names_the_guard_and_the_reason(self):
        body = _read(SKILL_MD)
        self.assertIn("landing guard", body, "no exemption declaration in SKILL.md")
        self.assertIn("纪律正确性优先于行数", body)
        self.assertIn("tests/test_zj_roadmap_driven_landing.py", body)


class ReferenceMaterialIsDisclosed(unittest.TestCase):
    """Design detail belongs behind a pointer; only branches that need it read it."""

    def test_viz_design_lives_in_a_reference_file(self):
        self.assertTrue(VIZ_DESIGN.is_file(), "references/viz-design.md is missing")
        design = _read(VIZ_DESIGN)
        for needle in ("DOI", "T1 图邻近", "θ", "S3 dependency", "S4 context"):
            self.assertIn(needle, design, f"viz design lost {needle!r} during the move")

    def test_advanced_topology_lives_in_the_cli_reference(self):
        cli = _read(CLI_REF)
        for needle in ("reconciliation", "placement", "ChangeSet"):
            self.assertIn(needle, cli, f"advanced topology lost {needle!r} during the move")

    def test_skill_md_no_longer_inlines_design_detail(self):
        body = _read(SKILL_MD)
        for needle in ("六权重加权", "S4 context side-pack", "migrate-placements <source>"):
            self.assertNotIn(
                needle, body, f"design detail {needle!r} is still inlined in SKILL.md"
            )

    def test_top_file_stays_legible_without_cutting_disciplines(self):
        lines = len(_read(SKILL_MD).splitlines())
        self.assertLessEqual(
            lines,
            200,
            f"SKILL.md grew back to {lines} lines; disclose reference, do not cut disciplines",
        )


if __name__ == "__main__":
    unittest.main()

"""Regression test: every role's gated-method file carries the §4.1 four-piece.

Guards discussion item from ``design.md §10.4 项1`` (role gated methods). The
"teeth" of ``role-matrix.md`` must be mechanically present, not just promised
in prose — if a method file loses any of the four sections (① Read 原文 /
② 核查清单 / ③ 输出结构 / ④ 闸门), this test fails loudly.

Seam: in-process file scan over the shipped ``references/role-methods/`` dir.
"""

import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
METHODS_DIR = SKILL_DIR / "references" / "role-methods"

REQUIRED_ROLES = ("B", "C", "A", "T", "S", "O", "D", "L", "F", "U", "R", "P", "E")

# The four contract sections every gated method must declare.
SECTION_MARKERS = ("## ①", "## ②", "## ③", "## ④")


class RoleMethodsPresent(unittest.TestCase):
    def test_methods_dir_exists(self):
        self.assertTrue(METHODS_DIR.is_dir(), "role-methods/ dir missing")

    def test_all_thirteen_files_present(self):
        for key in REQUIRED_ROLES:
            path = METHODS_DIR / "{}.md".format(key)
            self.assertTrue(path.exists(), "missing gated method: {}".format(path))


class RoleMethodsHaveFourPiece(unittest.TestCase):
    def test_each_file_declares_four_sections(self):
        for key in REQUIRED_ROLES:
            path = METHODS_DIR / "{}.md".format(key)
            text = path.read_text(encoding="utf-8")
            for marker in SECTION_MARKERS:
                self.assertIn(
                    marker,
                    text,
                    "role {} method missing section {} (see design.md §10.4 项1)".format(
                        key, marker
                    ),
                )

    def test_each_file_has_a_checklist_under_teeth(self):
        for key in REQUIRED_ROLES:
            path = METHODS_DIR / "{}.md".format(key)
            text = path.read_text(encoding="utf-8")
            # The ② section must carry at least one "- " checklist item.
            self.assertIn(
                "- ",
                text,
                "role {} method has no checklist items under ② (牙齿空了)".format(key),
            )

    def test_each_file_points_at_role_matrix_ssot(self):
        for key in REQUIRED_ROLES:
            path = METHODS_DIR / "{}.md".format(key)
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "role-matrix.md",
                text,
                "role {} method must point at role-matrix.md SSOT".format(key),
            )


if __name__ == "__main__":
    unittest.main()

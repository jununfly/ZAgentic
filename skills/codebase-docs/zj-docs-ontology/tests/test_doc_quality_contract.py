#!/usr/bin/env python3
"""Contract-text guards for the distilled document-quality clauses.

Distilled from chromium / deepseek-harness / semantica / openai-codex `docs/`
(Plan `docs-best-practices-distill-2026-10-28`, Step 4 design
`change-design-2026-10-28.md`). These clauses are contract text, not runtime
diagnostics: no new `MAP_*` code, no change to `docs_governance.py`. What is
worth guarding mechanically is therefore *coverage and completeness* — a
`doc-kind` without a template row, a template row without its negative
boundary, a slop class without a way to fix it, a clause that silently
disappears, or the deletion default quietly flipping.

Anchors are section headings, table headers and explicit markers, never prose
wording, so normal editing does not trip these.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = SKILL_ROOT / "references" / "governance-contract.md"
KIND_TEMPLATES = SKILL_ROOT / "references" / "kind-templates.md"
SLOP = SKILL_ROOT / "references" / "doc-slop-checklist.md"
SKILL = SKILL_ROOT / "SKILL.md"

REQUIRED_SECTIONS = (
    "## One home per fact",
    "## Page form: tutorial or reference",
    "## Page content contract",
    "## Evidence: run the facts",
    "## Retirement",
    "## Generated regions",
    "## What a green run does not mean",
    "## Rejected defaults",
)

SLOP_SLUGS = (
    "duplicate-rule",
    "history-leak",
    "status-annotation",
    "hand-copied-restatement",
    "reasoning-aside",
    "rationale-repeat",
    "paragraph-wall",
    "emphasis-inflation",
    "spec-speak",
)

PAGE_FORMS = ("tutorial", "reference", "either")
FORBIDDEN_DEFAULT_PHRASES = ("delete by default", "default to deletion", "默认删除", "默认删")


def doc_kinds(text: str) -> list[str]:
    """The `doc-kind` vocabulary, read from the contract that defines it."""
    match = re.search(r"`doc-kind` is one of(.*?)\.", text, re.S)
    assert match, "the contract no longer declares the doc-kind vocabulary"
    return re.findall(r"`([a-z][a-z0-9-]*)`", match.group(1))


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if cells and cells[0].lower() == "doc-kind":
            continue
        rows.append(cells)
    return rows


def sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    current: list[str] = []
    head = ""
    for line in text.splitlines():
        if line.startswith("## "):
            if head:
                found[head] = "\n".join(current)
            head = line.strip()
            current = []
        elif head:
            current.append(line)
    if head:
        found[head] = "\n".join(current)
    return found


class ContractClauseTest(unittest.TestCase):
    """Every distilled clause has to be findable, or it is not a clause."""

    def setUp(self) -> None:
        self.text = CONTRACT.read_text(encoding="utf-8")

    def test_every_distilled_clause_has_a_section(self) -> None:
        self.assertEqual(len(REQUIRED_SECTIONS), len(set(REQUIRED_SECTIONS)))
        missing = [s for s in REQUIRED_SECTIONS if s not in self.text]
        self.assertEqual([], missing)

    def test_the_vocabulary_is_readable_and_nonempty(self) -> None:
        kinds = doc_kinds(self.text)
        self.assertTrue(len(kinds) >= 10, "the doc-kind list must be parseable")
        self.assertIn("method", kinds)
        self.assertIn("fixture-documentation", kinds)

    def test_green_run_caveat_is_stated_as_a_boundary(self) -> None:
        """Green proves 'confirmed consistent on this content', never
        'the confirmation was right'."""
        body = sections(self.text).get("## What a green run does not mean", "")
        self.assertNotEqual("", body.strip())
        self.assertIn("review", body.lower())

    def test_retirement_is_a_stage_before_deletion(self) -> None:
        body = sections(self.text).get("## Retirement", "").lower()
        self.assertNotEqual("", body.strip())
        self.assertIn("tombstone", body)
        self.assertIn("human", body)

    def test_generated_regions_are_declared_unhandeditable(self) -> None:
        body = sections(self.text).get("## Generated regions", "").lower()
        self.assertNotEqual("", body.strip())
        self.assertTrue(any(w in body for w in ("手改", "hand-edit", "not hand", "禁止")))


class KindTemplateTest(unittest.TestCase):
    """C-7: doc-kind -> skeleton is a 1:1 mapping, and the negative boundary
    column is half the definition — a row without it is a kind that has not
    been placed."""

    def setUp(self) -> None:
        self.assertTrue(CONTRACT.is_file(), "contract missing")
        self.kinds = doc_kinds(CONTRACT.read_text(encoding="utf-8"))

    def rows(self) -> list[list[str]]:
        self.assertTrue(KIND_TEMPLATES.is_file(), "references/kind-templates.md missing")
        return table_rows(KIND_TEMPLATES.read_text(encoding="utf-8"))

    def test_the_template_table_exists(self) -> None:
        self.assertNotEqual([], self.rows())

    def test_every_doc_kind_has_exactly_one_row(self) -> None:
        seen: dict[str, int] = {}
        for row in self.rows():
            kind = row[0].strip("`")
            seen[kind] = seen.get(kind, 0) + 1
        self.assertEqual(sorted(self.kinds), sorted(seen), "template coverage must match the vocabulary exactly")
        self.assertEqual([], [k for k, n in seen.items() if n != 1], "one row per doc-kind")

    def test_every_row_carries_all_six_cells(self) -> None:
        for row in self.rows():
            with self.subTest(kind=row[0]):
                self.assertEqual(6, len(row), "Job / Does NOT belong there / Must-write / Page form / Focused check")
                self.assertEqual([], [c for c in row if not c], "no empty cell")

    def test_the_negative_boundary_column_is_not_a_placeholder(self) -> None:
        for row in self.rows():
            with self.subTest(kind=row[0]):
                self.assertNotEqual("-", row[2])
                self.assertTrue(len(row[2]) >= 8, "Does NOT belong there must actually say something")

    def test_page_form_is_declared(self) -> None:
        for row in self.rows():
            with self.subTest(kind=row[0]):
                self.assertIn(row[4].strip("`").lower(), PAGE_FORMS)


class SlopChecklistTest(unittest.TestCase):
    """C-8: an audit list is only usable if every class says how to find it
    and how to fix it."""

    def setUp(self) -> None:
        self.assertTrue(SLOP.is_file(), "references/doc-slop-checklist.md missing")
        self.text = SLOP.read_text(encoding="utf-8")

    def test_all_nine_classes_are_present(self) -> None:
        for slug in SLOP_SLUGS:
            with self.subTest(slug=slug):
                self.assertIn(slug, self.text)

    def test_each_class_has_detection_and_remedy(self) -> None:
        bodies = sections(self.text)
        matched = [h for h in bodies if any(s in h for s in SLOP_SLUGS)]
        self.assertEqual(len(SLOP_SLUGS), len(matched), "one section per slop class")
        for head in matched:
            with self.subTest(section=head):
                body = bodies[head]
                self.assertIn("**Detect:**", body)
                self.assertIn("**Fix:**", body)

    def test_it_stays_an_audit_list_not_a_gate(self) -> None:
        """The Plan classified this B1 with the audit-list default; it must not
        smuggle in a diagnostic code."""
        self.assertNotIn("MAP_", self.text)


class DeletionDefaultTest(unittest.TestCase):
    """C-11 was rejected: deletion stays a named action, never a default.

    This is the anti-regression guard — the clause may be *discussed* inside
    Rejected defaults, but nowhere else may the default flip.
    """

    def setUp(self) -> None:
        self.contract = CONTRACT.read_text(encoding="utf-8")
        self.skill = SKILL.read_text(encoding="utf-8")

    def test_preserve_meaning_is_the_declared_default(self) -> None:
        self.assertIn("Default: preserve meaning", self.contract)

    def test_the_skill_keeps_the_same_default(self) -> None:
        self.assertIn("Preserve meaning by default", self.skill)

    def test_delete_by_default_appears_only_where_it_is_rejected(self) -> None:
        operative = self.contract.split("## Rejected defaults")[0]
        hits = [p for p in FORBIDDEN_DEFAULT_PHRASES if p in operative]
        self.assertEqual([], hits)

    def test_deletion_requires_a_named_confirmation(self) -> None:
        operative = self.contract.split("## Rejected defaults")[0].lower()
        self.assertIn("human", operative)


class SkillPointerTest(unittest.TestCase):
    """New references are only reachable if SKILL.md points at them."""

    def test_skill_links_the_new_references(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("kind-templates.md", text)
        self.assertIn("doc-slop-checklist.md", text)


if __name__ == "__main__":
    unittest.main()

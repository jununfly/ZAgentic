"""Frontmatter seam: one shared schema, no per-skill compatibility branches.

zj-roadmap-driven was the sole registered exception to the ZAgentic frontmatter
schema (top-level `triggers`/`title`). Its only consumer was the validator that
enforced the exception, and none of the 69 installed skills uses `triggers` —
so it cannot be a host discovery mechanism. The description already carries
the same trigger words as context pointer, making the list pure duplication.

This suite asserts the shipped artifact, the validator, and the schema doc all
agree on the generic contract.
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
PERSONAL = REPO / "personal"
SKILL_MD = SKILLS / "codebase-docs" / "zj-roadmap-driven" / "SKILL.md"
VALIDATOR = REPO / "scripts" / "validate-skill-frontmatter.py"
SCHEMA_DOC = REPO / "docs" / "designs" / "zj-skill-frontmatter-schema.md"

# The generic contract from scripts/validate-skill-frontmatter.py.
ALLOWED_GENERIC = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "disable-model-invocation",
    "argument-hint",
    "source",
}


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    assert match, "missing YAML frontmatter"
    return match.group(1)


def _top_fields(text: str) -> set[str]:
    # Top-level YAML keys are unindented. Skip folded continuation lines.
    return set(re.findall(r"^([A-Za-z][A-Za-z0-9-]*):", _frontmatter(text), re.M))


class SharedSchema(unittest.TestCase):
    def test_skill_uses_only_generic_top_level_fields(self):
        fields = _top_fields(_read(SKILL_MD))
        self.assertEqual(set(), fields - ALLOWED_GENERIC, f"non-generic fields: {fields}")
        self.assertNotIn("triggers", fields)
        self.assertNotIn("title", fields)

    def test_validator_has_no_skill_specific_branch(self):
        source = _read(VALIDATOR)
        self.assertNotIn("ROADMAP_FIELDS", source)
        self.assertNotIn("zj-roadmap-driven", source)

    def test_schema_doc_registers_no_exception(self):
        doc = _read(SCHEMA_DOC)
        self.assertNotIn("sole registered exception", doc)
        self.assertNotIn("zj-roadmap-driven", doc)

    def test_no_skill_in_the_catalog_declares_triggers(self):
        offenders = []
        for pattern in ("*/*/SKILL.md",):
            for path in sorted(SKILLS.glob(pattern)):
                if "triggers" in _top_fields(_read(path)):
                    offenders.append(str(path.relative_to(REPO)))
        for path in sorted(PERSONAL.glob("*/SKILL.md")):
            if "triggers" in _top_fields(_read(path)):
                offenders.append(str(path.relative_to(REPO)))
        self.assertEqual([], offenders, f"legacy triggers fields: {offenders}")


class DescriptionAsContextPointer(unittest.TestCase):
    def test_description_carries_triggers_without_implementation_detail(self):
        body = _read(SKILL_MD)
        match = re.search(r"^description: >-\n((?:  .*\n)+)", body, re.M)
        self.assertIsNotNone(match, "description must be a folded block")
        description = " ".join(line.strip() for line in match.group(1).splitlines())
        self.assertIn("Use when", description)
        self.assertLessEqual(len(description), 1024)
        for leaked in ("载体支持单文件 JSON 与 SQLite", "zj-wayfinder", "zj-to-tickets"):
            self.assertNotIn(
                leaked, description,
                f"implementation detail '{leaked}' is paying permanent context load",
            )


if __name__ == "__main__":
    unittest.main()

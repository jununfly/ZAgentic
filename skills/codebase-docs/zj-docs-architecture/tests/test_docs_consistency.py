#!/usr/bin/env python3
"""Regression tests for documentation that is deliberately stated twice."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
CONTRACT = SKILL_ROOT / "references" / "architecture-contract.md"
HEADING = "## Maintenance triggers"
ITEM_RE = re.compile(r"^- \*\*(.+?)\*\* — (.+)$")
EXPECTED = (
    "Extension seam",
    "Durable owner",
    "Cross-process contract",
    "Effect policy",
    "Replay boundary",
    "Lifecycle rule",
    "Accepted ADR",
    "Source-map target",
)


def triggers(text: str) -> list[tuple[str, str]]:
    """Items under the heading, with wrapped continuation lines folded in."""
    items: list[tuple[str, str]] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == HEADING
            continue
        if not inside:
            continue
        match = ITEM_RE.match(line)
        if match:
            items.append((match.group(1), match.group(2)))
        elif items and line.startswith("  ") and line.strip():
            name, body = items[-1]
            items[-1] = (name, f"{body} {line.strip()}")
    return items


class MaintenanceTriggersTest(unittest.TestCase):
    """#50 — the trigger list lives in both documents on purpose: SKILL.md is
    what an agent reads first, the contract is the authority. Two copies of one
    rule is the drift a review catches, so they are compared here rather than
    left to stay in step by hand.
    """

    def items(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        return (
            triggers(SKILL_MD.read_text(encoding="utf-8")),
            triggers(CONTRACT.read_text(encoding="utf-8")),
        )

    def test_both_documents_carry_the_same_items(self) -> None:
        skill_items, contract_items = self.items()
        self.assertEqual(contract_items, skill_items)

    def test_every_named_trigger_is_covered(self) -> None:
        skill_items, _ = self.items()
        names = [name for name, _ in skill_items]
        self.assertEqual(sorted(EXPECTED), sorted(names))
        self.assertEqual(len(EXPECTED), len(names))

    def test_each_trigger_states_a_signal(self) -> None:
        """A bare noun is not a trigger; the item has to say what to watch for."""
        skill_items, _ = self.items()
        self.assertNotEqual([], skill_items)
        for name, body in skill_items:
            self.assertLess(40, len(body), name)


if __name__ == "__main__":
    unittest.main()

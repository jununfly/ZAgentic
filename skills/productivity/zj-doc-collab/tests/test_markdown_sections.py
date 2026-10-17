#!/usr/bin/env python3
"""Generic tests for zj-doc-collab markdown_sections (no consumer vocabulary)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from markdown_sections import split_sections


class SplitSectionsTest(unittest.TestCase):
    def test_basic_split(self):
        text = "# A\nbody a\n\n## B\nbody b\n"
        secs = split_sections(text)
        self.assertEqual(secs[0][0], "# A")
        self.assertEqual(secs[0][1].strip(), "body a")
        self.assertEqual(secs[1][0], "## B")
        self.assertEqual(secs[1][1].strip(), "body b")

    def test_fence_keeps_hashes_inert(self):
        # A '#' inside a code fence must NOT start a new section.
        text = "# Real\nouter\n\n```\n# not a heading\ncode\n```\n\nafter\n"
        secs = split_sections(text)
        # Only one section: the real heading owns everything including the fence.
        self.assertEqual(len(secs), 1)
        self.assertIn("# not a heading", secs[0][1])

    def test_no_heading_returns_empty(self):
        self.assertEqual(split_sections("just text\nmore text\n"), [])

    def test_multiple_same_level(self):
        text = "## X\nx\n## Y\ny\n## Z\nz\n"
        secs = split_sections(text)
        self.assertEqual([h for h, _ in secs], ["## X", "## Y", "## Z"])


if __name__ == "__main__":
    unittest.main()

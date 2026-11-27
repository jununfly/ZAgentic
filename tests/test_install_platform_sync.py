#!/usr/bin/env python3
"""Install-platform sync locks (A of the qianwen PR).

The platform list lives in two places that must never diverge:
  * scripts/link-skills.sh  -> the PLATFORMS array
  * README.md               -> the "Local installation" table

Adding a platform means editing both (plus the two error messages). Nothing
else in CI compares them, so a forgotten side silently ships a README that
teaches a platform the installer rejects (or the reverse). These tests are
that lock. They also keep --help honest: help is extracted from the leading
comment block by content, so the test asserts every platform name is visible
in it — if the extraction regresses, this goes red, not the user's terminal.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "link-skills.sh"
README = REPO / "README.md"


def script_platforms() -> list[str]:
    """Platform keys from the PLATFORMS array (robust to how each dir is built)."""
    text = SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"^PLATFORMS=\(\n(.*?)^\)$", text, re.S | re.M)
    if not block:
        raise AssertionError("link-skills.sh no longer declares a PLATFORMS array")
    return sorted(re.findall(r"^  ([a-z0-9]+):", block.group(1), re.M))


def readme_platforms() -> list[str]:
    """Platform keys from the first column of the Local installation table."""
    text = README.read_text(encoding="utf-8")
    section = text.split("## Local installation", 1)[1]
    return sorted(re.findall(r"^\| `([a-z0-9]+)` \|", section, re.M))


class PlatformSync(unittest.TestCase):
    def test_readme_table_matches_the_installer(self):
        a, b = script_platforms(), readme_platforms()
        self.assertEqual(
            a, b,
            f"platform lists diverged: script-only={sorted(set(a) - set(b))} "
            f"readme-only={sorted(set(b) - set(a))}",
        )

    def test_the_list_is_not_accidentally_empty(self):
        self.assertGreaterEqual(len(script_platforms()), 4)

    def test_qianwen_resolves_to_the_cn_edition_with_fallback(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('QIANWEN_DIR="$HOME/.qwenworkcn"', text)
        self.assertIn('QIANWEN_DIR="$HOME/.qwenwork"', text)


class HelpContract(unittest.TestCase):
    def setUp(self):
        self.proc = subprocess.run(
            ["bash", str(SCRIPT), "--help"], capture_output=True, text=True, timeout=30
        )
        self.assertIn(self.proc.returncode, (0,), self.proc.stderr)

    def test_help_contains_every_platform(self):
        for name in script_platforms():
            self.assertIn(name, self.proc.stdout, f"--help lost platform {name!r}")

    def test_help_is_the_full_header_not_a_truncated_range(self):
        # Content-based extraction: both the opening and the closing paragraph
        # of the header must be present (usage() strips the "# " prefix). The
        # closing one ("Uninstall ...") is what a hand-maintained `sed -n 'a,bp'`
        # range loses first.
        self.assertIn("Usage:", self.proc.stdout)
        self.assertIn("Uninstall", self.proc.stdout)

    def test_unknown_platform_error_names_every_valid_choice(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--platform", "__nope__"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(proc.returncode, 0)
        for name in script_platforms():
            self.assertIn(name, proc.stderr, f"error message lost platform {name!r}")


if __name__ == "__main__":
    unittest.main()

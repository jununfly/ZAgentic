#!/usr/bin/env python3
"""Regression tests for the official-first plugin validation entrypoint."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "validate-plugin.sh"


class ValidatePluginTest(unittest.TestCase):
    def test_official_success_is_the_first_and_only_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            official = Path(temporary) / "official-passes.py"
            official.write_text(
                "#!/usr/bin/env python3\n"
                "print('official validator fixture passed')\n",
                encoding="utf-8",
            )
            official.chmod(official.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
                [
                    str(ENTRYPOINT),
                    "--official-validator",
                    str(official),
                    str(ROOT),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("official validator fixture passed", result.stdout)
        self.assertNotIn("repository recursive validation", result.stdout)

    def test_official_failure_falls_back_to_recursive_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            official = Path(temporary) / "official-fails.py"
            official.write_text(
                "#!/usr/bin/env python3\n"
                "print('official validator fixture failed')\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            official.chmod(official.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
                [
                    str(ENTRYPOINT),
                    "--official-validator",
                    str(official),
                    str(ROOT),
                ],
                cwd=ROOT,
                env={**os.environ, "ZAGENTIC_OFFICIAL_PLUGIN_VALIDATOR": ""},
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Official validator returned 1", result.stdout)
        self.assertIn("ZAgentic recursive validation passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression tests for the official-first plugin validation entrypoint."""

from __future__ import annotations

import os
import importlib.util
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "validate-plugin.sh"
LAYOUT_VALIDATOR = ROOT / "scripts" / "validate-zagentic-plugin.py"
SPEC = importlib.util.spec_from_file_location("zagentic_layout_validator", LAYOUT_VALIDATOR)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ValidatePluginTest(unittest.TestCase):
    def test_public_bucket_skill_needs_readme_and_guide_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            (fixture / ".codex-plugin").mkdir()
            (fixture / ".codex-plugin" / "plugin.json").write_text('{"skills":"./skills/"}', encoding="utf-8")
            (fixture / "scripts").mkdir()
            (fixture / "scripts" / "validate-skill-frontmatter.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
            (fixture / "README.md").write_text(
                "[zj-guide](./skills/engineering/zj-guide/SKILL.md)\n"
                "[zj-example](./skills/codebase-docs/zj-example/SKILL.md)\n",
                encoding="utf-8",
            )
            for bucket in VALIDATOR.PUBLIC_BUCKETS:
                directory = fixture / "skills" / bucket
                directory.mkdir(parents=True)
                (directory / "README.md").write_text("", encoding="utf-8")
            (fixture / "personal").mkdir()
            guide_dir = fixture / "skills" / "engineering" / "zj-guide"
            guide_dir.mkdir()
            (guide_dir / "SKILL.md").write_text(
                "---\nname: zj-guide\n---\n\nRoutes zj-guide and zj-example.\n",
                encoding="utf-8",
            )
            skill_dir = fixture / "skills" / "codebase-docs" / "zj-example"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: zj-example\n---\n", encoding="utf-8")
            personal_dir = fixture / "personal" / "zj-private"
            personal_dir.mkdir()
            (personal_dir / "SKILL.md").write_text("---\nname: zj-private\n---\n", encoding="utf-8")
            guide_readme = fixture / "skills" / "engineering" / "README.md"
            guide_readme.write_text("[zj-guide](./zj-guide/SKILL.md)\n", encoding="utf-8")
            bucket_readme = fixture / "skills" / "codebase-docs" / "README.md"
            bucket_readme.write_text("[zj-example](./zj-example/SKILL.md)\n", encoding="utf-8")

            self.assertEqual(VALIDATOR.validate(fixture), [])
            (fixture / "README.md").write_text("", encoding="utf-8")
            self.assertIn("README.md does not register public skill zj-example", VALIDATOR.validate(fixture))
            (fixture / "README.md").write_text(
                "[zj-guide](./skills/engineering/zj-guide/SKILL.md)\n"
                "[zj-example](./skills/codebase-docs/zj-example/SKILL.md)\n",
                encoding="utf-8",
            )
            (guide_dir / "SKILL.md").write_text(
                "---\nname: zj-guide\n---\n\nRoutes zj-guide.\n",
                encoding="utf-8",
            )
            self.assertIn(
                "zj-guide does not route public skill zj-example",
                VALIDATOR.validate(fixture),
            )

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

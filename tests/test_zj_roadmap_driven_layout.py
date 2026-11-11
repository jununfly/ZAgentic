"""Layout seam: a published skill ships scripts/ and tests/, not a flat root.

The bucket convention (docs/architecture/ta-skill-bucket-codebase-docs.md) is
SKILL.md + references/ + scripts/ + tests/. zj-roadmap-driven grew ten runtime
modules and two test modules directly in its root, so an installed copy carries
test code and cache dirs as top-level payload and every path constant disagrees
with its neighbours.

These tests observe the shipped directory and the published path basis only;
they do not import the modules or assert on their internals.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven"
SCRIPTS = SKILL / "scripts"
TESTS = SKILL / "tests"

RUNTIME_MODULES = (
    "authority_boundary.py",
    "carrier_migration.py",
    "placement_migration.py",
    "roadmap.py",
    "roadmap_cli.py",
    "roadmap_sqlite.py",
    "storage_advisor.py",
    "type_migration.py",
)


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class PublishedLayout(unittest.TestCase):
    def test_runtime_modules_live_in_scripts(self):
        self.assertTrue(SCRIPTS.is_dir(), "skill has no scripts/ directory")
        missing = [name for name in RUNTIME_MODULES if not (SCRIPTS / name).is_file()]
        self.assertEqual([], missing, f"runtime modules not in scripts/: {missing}")

    def test_no_runtime_module_or_test_module_in_skill_root(self):
        stray = sorted(
            p.name
            for p in SKILL.glob("*.py")
            if p.name in RUNTIME_MODULES or p.name.startswith("test_")
        )
        self.assertEqual([], stray, f"flat root still ships: {stray}")

    def test_root_test_modules_moved_into_tests(self):
        for name in ("test_roadmap.py", "test_storage_advisor.py"):
            self.assertTrue((TESTS / name).is_file(), f"{name} not in tests/")

    def test_published_commands_point_into_scripts(self):
        for path in (SKILL / "SKILL.md", SKILL / "references" / "roadmap-cli.md"):
            body = _read(path)
            self.assertIn(
                "$SKILL_ROOT/scripts/roadmap_cli.py",
                body,
                f"{path.name} still publishes a pre-migration script path",
            )
            self.assertNotIn(
                '"$SKILL_ROOT/roadmap_cli.py"',
                body,
                f"{path.name} still points at the old root location",
            )

    def test_ci_authority_check_uses_the_shipped_path(self):
        workflow = _read(REPO / ".github" / "workflows" / "skill-closure-lint.yml")
        self.assertIn("zj-roadmap-driven/scripts/roadmap_cli.py authority-check", workflow)

    def test_no_flat_path_constants_left_in_skill_tests(self):
        """A test that still builds SKILL_DIR / 'roadmap_cli.py' cannot run."""
        offenders = []
        for path in sorted(TESTS.glob("*.py")) + sorted(SKILL.glob("viz/tests/*.py")):
            body = _read(path)
            if re.search(r"SKILL_DIR\s*/\s*[\"']roadmap_cli\.py[\"']", body):
                offenders.append(str(path.relative_to(SKILL)))
        self.assertEqual([], offenders, f"stale CLI path constants: {offenders}")

    def test_runtime_dirs_are_not_tracked(self):
        result = subprocess.run(
            ["git", "ls-files", str(SKILL.relative_to(REPO))],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        leaked = [
            line for line in result.stdout.splitlines()
            if "__pycache__" in line or ".pytest_cache" in line or line.endswith(".pyc")
        ]
        self.assertEqual([], leaked, f"cache artifacts are tracked: {leaked}")


if __name__ == "__main__":
    unittest.main()

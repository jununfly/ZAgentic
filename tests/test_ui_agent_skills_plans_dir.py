"""Guards for the ui-agent-skills plans-directory resolver (R-HAR-1).

Why these tests exist: installed skills live outside the project
(~/.claude/skills/zj-ui-core), so deriving the fixture directory from the script
location used to produce a path rooted at "/" that looked valid but was not.
Regression: `selfcheck` from an installed copy failed with a FileNotFoundError
coming from deep inside `open()`, instead of telling the caller what to do.

These tests pin three behaviours:

1. the operating project (cwd) wins over the script location,
2. an unreachable repository raises an actionable RuntimeError instead of
   returning a bogus path,
3. an explicit --plans always works, even when discovery would fail -- i.e. the
   resolver stays lazy so argparse never evaluates it eagerly at import time.
"""

import io
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills/ui/zj-ui-core/scripts"

sys.path.insert(0, str(SKILL_DIR))
import dual_lane_runner as runner  # noqa: E402

PLANS = REPO / "docs/designs/ui-agent-skills"


class PlansDirResolution(unittest.TestCase):
    def test_cwd_repo_wins_over_script_location(self):
        """Skills are installed centrally but act on the project being worked on."""
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "project"
            (project / ".git").mkdir(parents=True)
            expected = project / "docs" / "designs" / "ui-agent-skills"
            expected.mkdir(parents=True)
            with mock.patch.object(os, "getcwd", return_value=str(project)):
                self.assertEqual(runner.default_plans_dir(), str(expected))

    def test_falls_back_to_script_location_when_cwd_is_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(os, "getcwd", return_value=tmp):
                self.assertEqual(runner.default_plans_dir(), str(PLANS))

    def test_raises_actionable_error_when_no_repo_reachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "outside"
            outside.mkdir()
            fake_script = outside / "dual_lane_runner.py"
            with mock.patch.object(os, "getcwd", return_value=str(outside)), \
                    mock.patch.object(runner, "__file__", str(fake_script)):
                with self.assertRaises(RuntimeError) as caught:
                    runner.default_plans_dir()
        message = str(caught.exception)
        self.assertIn("--plans", message)
        self.assertIn("docs/designs/ui-agent-skills", message)

    def test_explicit_plans_works_without_a_repository(self):
        """Would fail if --plans were resolved eagerly while building the parser."""
        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "outside"
            outside.mkdir()
            fake_script = outside / "dual_lane_runner.py"
            with mock.patch.object(os, "getcwd", return_value=str(outside)), \
                    mock.patch.object(runner, "__file__", str(fake_script)):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = runner.main(["selfcheck", "--plans", str(PLANS)])
        self.assertEqual(code, 0)
        self.assertIn("matrix_key", buffer.getvalue())

    def test_demo_needs_no_repository(self):
        """Commands that do not read fixtures must not trigger resolution."""
        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "outside"
            outside.mkdir()
            fake_script = outside / "dual_lane_runner.py"
            with mock.patch.object(os, "getcwd", return_value=str(outside)), \
                    mock.patch.object(runner, "__file__", str(fake_script)):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = runner.main(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("determinism_stable", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()

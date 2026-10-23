"""Guards for the ui-agent-skills plans-directory resolver (R-HAR-1).

Why these tests exist: skills ship their contracts inside the skill install at
`<skill>/contracts/` (skill-runtime-closure, see AGENTS.md). `default_plans_dir()`
therefore resolves from the script's own location, NOT from $PWD or a
surrounding repo. An installed copy under ~/.workbuddy/skills/zj-ui-core finds
its contracts the same way, with no dependency on the project being worked on.

These tests pin three behaviours:
1. resolution is self-contained (from __file__, independent of cwd),
2. a missing bundled contracts dir raises an actionable RuntimeError (mentioning
   --plans) instead of returning a bogus path,
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

PLANS = REPO / "skills/ui/zj-ui-core/contracts"


class PlansDirResolution(unittest.TestCase):
    def test_resolves_to_skill_internal_contracts(self):
        """Resolution is self-contained: from __file__, not cwd/repo."""
        with tempfile.TemporaryDirectory() as tmp:
            # cwd is an unrelated directory; resolution must still find the
            # skill-bundled contracts dir.
            with mock.patch.object(os, "getcwd", return_value=tmp):
                self.assertEqual(runner.default_plans_dir(), str(PLANS))

    def test_missing_contracts_dir_raises_actionable_error(self):
        """A broken install (no bundled contracts) must tell the caller to use --plans."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_script = pathlib.Path(tmp) / "dual_lane_runner.py"
            with mock.patch.object(runner, "__file__", str(fake_script)):
                with self.assertRaises(RuntimeError) as caught:
                    runner.default_plans_dir()
        message = str(caught.exception)
        self.assertIn("--plans", message)
        self.assertIn("contracts", message)

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

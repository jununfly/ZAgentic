#!/usr/bin/env python3
"""TDD regression for F2: dual_lane_runner selfcheck must surface its verdict
in the process exit code, not silently return 0.

Seam under test (S1 — CLI process boundary): the public ``main()`` entrypoint
returns an integer exit code that reflects ``rerun_idempotent``. The legacy
implementation ``return 0`` unconditionally, so a non-idempotent selfcheck read
as green. We assert the honest contract instead.
"""
import importlib.util
import pathlib
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "ui" / "zj-ui-core" / "scripts"
PLANS = REPO_ROOT / "docs" / "designs" / "ui-agent-skills"


def _load():
    spec = importlib.util.spec_from_file_location(
        "dual_lane_runner_under_test", SCRIPTS / "dual_lane_runner.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSelfcheckExitCode(unittest.TestCase):
    def test_exit_zero_when_idempotent(self):
        mod = _load()
        rc = mod.main(["selfcheck", "--plans", str(PLANS)])
        self.assertEqual(rc, 0, "idempotent selfcheck must exit 0")

    def test_exit_nonzero_when_drift(self):
        mod = _load()
        # Force the two fingerprint captures to disagree so rerun_idempotent
        # becomes False; the CLI must then surface that as a non-zero exit.
        calls = {"n": 0}

        def _drift(plans_dir, write=False):
            base = mod.fingerprint.__wrapped__(plans_dir, write=write) \
                if hasattr(mod.fingerprint, "__wrapped__") else None
            return base

        real_fp = mod.fingerprint

        def flaky(plans_dir, write=False):
            calls["n"] += 1
            res = real_fp(plans_dir, write=write)
            if calls["n"] == 2:  # second capture diverges
                res = dict(res)
                res["env_hash"] = "DRIFTED-" + res.get("env_hash", "")
            return res

        with mock.patch.object(mod, "fingerprint", flaky):
            rc = mod.main(["selfcheck", "--plans", str(PLANS)])
        self.assertNotEqual(rc, 0, "drifting selfcheck must exit non-zero")


if __name__ == "__main__":
    unittest.main()

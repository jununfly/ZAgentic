#!/usr/bin/env python3
"""TDD: ZJ_RESEARCH_PUBLISHER must be injected; no sibling-skill hard path.

Decouples the hidden debt from verify_golden_contract.py: the publisher lives
in a separate skill (zj-tech-research-report) and must be injected by the
caller, never resolved from a hard-coded parent-path assumption.
"""

import importlib.util
import os
import pathlib
import tempfile
import unittest

GOLDEN = pathlib.Path(__file__).resolve().parents[1] / "tests" / "verify_golden_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("golden_publisher_test", GOLDEN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublisherInjectionTest(unittest.TestCase):
    def test_missing_env_raises_setup_failure(self):
        saved = os.environ.pop("ZJ_RESEARCH_PUBLISHER", None)
        try:
            with self.assertRaises(RuntimeError) as raised:
                load_module().publisher_path()
            self.assertIn("ZJ_RESEARCH_PUBLISHER", str(raised.exception))
        finally:
            if saved is not None:
                os.environ["ZJ_RESEARCH_PUBLISHER"] = saved

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["ZJ_RESEARCH_PUBLISHER"] = str(pathlib.Path(folder) / "nope.py")
            try:
                with self.assertRaises(RuntimeError) as raised:
                    load_module().publisher_path()
                self.assertIn("missing", str(raised.exception))
            finally:
                os.environ.pop("ZJ_RESEARCH_PUBLISHER", None)

    def test_existing_file_resolves(self):
        with tempfile.TemporaryDirectory() as folder:
            pub = pathlib.Path(folder) / "publish_report.py"
            pub.write_text("# publisher", encoding="utf-8")
            os.environ["ZJ_RESEARCH_PUBLISHER"] = str(pub)
            try:
                self.assertEqual(load_module().publisher_path(), pub)
            finally:
                os.environ.pop("ZJ_RESEARCH_PUBLISHER", None)


if __name__ == "__main__":
    unittest.main()

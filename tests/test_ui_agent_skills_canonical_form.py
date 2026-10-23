#!/usr/bin/env python3
"""TDD/refactor guard for F6: the canonical JSON form and the sha256 hash base
must have ONE source of truth.

Seam under test (S3 — public functions):
  core.canonical_json / core.sha256_text, dual_lane_runner.canonical_json /
  dual_lane_runner.sha256_text, and the storybook adapter's canonical/sha helpers
  must all produce byte-identical output for the same input. Any silent drift in
  one copy would change manifest_hash / receipt hashes without any test failing.
"""
import importlib.util
import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "ui" / "zj-ui-core" / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = _load("uis_core", SCRIPTS / "ui_skill_core.py")
dlr = _load("uidlr", SCRIPTS / "dual_lane_runner.py")
sb = _load("uisb", SCRIPTS / "adapters" / "storybook_adapter.py")

SAMPLES = [
    {"b": 1, "a": 2, "z": [3, 2, 1]},
    {"fixtures": {"entries": [{"id": "F-1", "role": "body"}]}},
    {"color": {"on_surface": "#222222", "surface": "#ffffff"},
     "intents": ["submit", "cancel"]},
]


class TestCanonicalFormSingleSource(unittest.TestCase):
    def test_canonical_json_identical(self):
        for s in SAMPLES:
            c = core.canonical_json(s)
            self.assertEqual(dlr.canonical_json(s), c)
            self.assertEqual(sb._canonical(s), c)

    def test_sha256_identical(self):
        for s in SAMPLES:
            text = core.canonical_json(s)
            self.assertEqual(dlr.sha256_text(text), core.sha256_text(text))
            self.assertEqual(sb._sha(text), core.sha256_text(text))

    def test_canonical_is_stable_form(self):
        # Pin the contract: sorted keys, no whitespace, UTF-8 kept.
        self.assertEqual(core.canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')
        # sha256 of that exact byte string.
        import hashlib
        self.assertEqual(
            core.sha256_text('{"a":2,"b":1}'),
            hashlib.sha256(b'{"a":2,"b":1}').hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""TDD regression for F3: the two WCAG contrast implementations
(hard_gates.contrast_ratio vs ui_skill_core) must agree byte-for-byte on the
same colour pair, and the same borderline ratio must yield the same PASS/FAIL
verdict in both the S9 hard-gate and the S4 stage check.

Seam under test (S3 — public functions):
  - core.contrast_ratio_rgb(fg_rgb, bg_rgb)  -> full-precision WCAG ratio
  - hg.contrast_ratio(fg_rgb, bg_rgb)        -> must equal the above
  - hg.gate_contrast(bundle) verdict must match the stage check (ratio < 4.5).
"""
import importlib.util
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
hg = _load("uishg", SCRIPTS / "hard_gates.py")

PAIRS = [
    ((0, 0, 0), (255, 255, 255)),
    ((255, 255, 255), (0, 0, 0)),
    ((119, 119, 119), (255, 255, 255)),
    ((68, 68, 68), (255, 255, 255)),
    ((22, 24, 39), (255, 255, 255)),
]


class TestContrastUnified(unittest.TestCase):
    def test_two_implementations_agree(self):
        for fg, bg in PAIRS:
            a = hg.contrast_ratio(fg, bg)
            b = core.contrast_ratio_rgb(fg, bg)
            self.assertAlmostEqual(
                a, b, places=9, msg=f"contrast mismatch {fg} on {bg}: {a} vs {b}"
            )

    def test_borderline_verdict_consistent(self):
        # Find a grey-on-white pair whose ratio sits just below 4.5 (WCAG AA),
        # then assert the S9 hard-gate and the S4 stage check agree on FAIL.
        target = None
        for r in range(0, 256):
            fg = (r, r, r)
            ratio = core.contrast_ratio_rgb(fg, (255, 255, 255))
            if 4.45 < ratio < 4.55:
                target = (fg, ratio)
                break
        self.assertIsNotNone(target, "no borderline pair found in scan")
        fg, ratio = target
        bundle = {
            "fixture_id": "F-1",
            "viewport": "1440x900",
            "contrast": {"samples": [
                {"node_id": "title", "kind": "text", "fg": "#%02x%02x%02x" % fg,
                 "bg": "#ffffff", "font_size_px": 16, "font_weight": 400},
            ]},
        }
        gate = hg.gate_contrast(bundle)
        # stage check: ratio < CONTRAST_MIN (4.5) => should block
        stage_blocks = ratio < core.CONTRAST_MIN
        gate_failed = any(f["code"].startswith("HG-CON") for f in gate.get("findings", []))
        self.assertEqual(
            gate_failed, stage_blocks,
            f"verdict split at ratio={ratio}: gate_failed={gate_failed} "
            f"stage_blocks={stage_blocks}",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"

# Issue #236 Human review (zj, 2026-11-10): final notation chosen from
# A (`↪ reference: <label>`), B (`<label> [reference to <id>]`) and C.
# Renderer, this test, SKILL.md, CLI reference, data model, ZJ-CONTEXT.md and
# the plan review record must all carry this exact string.
REFERENCE_MARKER = "↪ reference (same WorkItem, not a copy):"

LONG_LABEL = (
    "Very long English title used to exercise plain-text wrapping and "
    "screen-reader linear reading when the same WorkItem appears again as "
    "a reference Placement in a second outline context"
)


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *[str(arg) for arg in args]],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({result.returncode})\n"
            f"args: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def build_review_fixture(tmpdir: Path, storage: str) -> dict:
    """One WorkItem in three outline contexts; every #236 review dimension covered.

    The per-roadmap lock key is the carrier stem, so single and sqlite use
    distinct stems to stay independent even when tests run back to back.
    """
    filename = "review-sqlite.sqlite" if storage == "sqlite" else "review-single.json"
    source = tmpdir / filename
    target = tmpdir / f"typed-{filename}"
    init = ["init", source, "--title", "Reference notation review"]
    if storage == "sqlite":
        init += ["--storage", "sqlite"]
    run_cli(*init, cwd=tmpdir)

    def add(parent: str, label: str, status: str | None = None) -> dict:
        argv = ["add", source, parent, label]
        if status:
            argv += ["--status", status]
        return json.loads(run_cli(*argv, cwd=tmpdir).stdout)

    shared = add("1", "Shared work")
    ctx_a = add("1", "Context A (中文上下文甲)")
    add(ctx_a["id"], "Context A child")
    ctx_b = add("1", "Context B (中文上下文乙)")
    add(ctx_b["id"], "Context B child")
    done = add("1", "已完成：中文长标题复核节点", "completed")
    wip = add("1", "进行中：中文 in_progress 节点", "in_progress")
    blocked = add("1", "被阻塞：等待上游机械闸结论")
    long_en = add("1", LONG_LABEL)

    run_cli("migrate-placements", source, "--output", target, cwd=tmpdir)
    for work, parent in (
        (shared, ctx_a), (shared, ctx_b), (long_en, ctx_a),
        (done, ctx_b), (wip, ctx_a), (blocked, ctx_b),
    ):
        run_cli(
            "placement", "add-reference", target,
            work["uid"], parent["uid"], cwd=tmpdir,
        )
    run_cli("edge", "add", target, wip["id"], blocked["id"],
            "--type", "blocks", cwd=tmpdir)
    return {"target": target, "shared": shared, "long": long_en}


def tree_block(section_text: str) -> str:
    """Isolate the tree from a section export (which also names the carrier)."""
    start = section_text.index("<!-- ROADMAP_TREE_START -->")
    end = section_text.index("<!-- ROADMAP_TREE_END -->")
    return section_text[start:end]


class PlacementProjectionTest(unittest.TestCase):
    def test_tree_and_section_render_reference_placements_from_placement_facts(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                shared = json.loads(run_cli("add", roadmap, "1", "Shared work", cwd=tmpdir).stdout)
                context = json.loads(run_cli("add", roadmap, "1", "Context", cwd=tmpdir).stdout)
                run_cli("add", roadmap, context["id"], "Context child", cwd=tmpdir)
                run_cli("migrate-placements", roadmap, "--output", tmpdir / f"typed-{filename}", cwd=tmpdir)
                target = tmpdir / f"typed-{filename}"
                run_cli(
                    "placement", "add-reference", target, shared["uid"], context["uid"],
                    "--rank", "0", cwd=tmpdir,
                )
                run_cli("update", target, shared["uid"], "--status", "in_progress", cwd=tmpdir)

                tree = run_cli("tree", target, cwd=tmpdir).stdout
                section = run_cli("section", target, cwd=tmpdir).stdout
                run_cli("render", target, cwd=tmpdir)
                rendered = (target.parent / "ROADMAP.md").read_text(encoding="utf-8")

                self.assertIn("↪", tree)
                self.assertIn("Shared work", tree)
                self.assertIn("↪", section)
                self.assertIn("↪", rendered)
                self.assertEqual(tree.count("Shared work"), 2)
                self.assertIn(REFERENCE_MARKER, tree)
                self.assertIn(REFERENCE_MARKER, section)
                self.assertIn(REFERENCE_MARKER, rendered)
                self.assertIn("same WorkItem, not a copy", tree.replace("↪", ""))
                self.assertNotIn("[reference to", tree)

                radial = run_cli("tree", target, "--anchor", shared["uid"], cwd=tmpdir).stdout
                self.assertIn("Context", radial)
                self.assertIn(f"{REFERENCE_MARKER} Shared work", radial)
                self.assertEqual(radial.count("Shared work"), 2)


class ReferenceNotationReviewTest(unittest.TestCase):
    """#236 Human short-read acceptance, pinned mechanically on both carriers."""

    def test_every_skill_surface_uses_the_chosen_marker(self):
        for name in (
            "SKILL.md",
            "references/roadmap-cli.md",
            "references/roadmap-data-model.md",
        ):
            with self.subTest(surface=name):
                text = (SKILL_DIR / name).read_text(encoding="utf-8")
                self.assertIn(REFERENCE_MARKER, text)
                self.assertNotIn("`↪ reference:`", text)

    def test_marker_is_leading_plain_text_and_glyph_independent(self):
        for storage in ("single", "sqlite"):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                fixture = build_review_fixture(tmpdir, storage)
                target = fixture["target"]
                tree = run_cli("tree", target, "--depth", "6", cwd=tmpdir).stdout
                lines = tree.splitlines()
                reference_lines = [line for line in lines if REFERENCE_MARKER in line]

                self.assertEqual(len(reference_lines), 6)
                # Long title: the marker must come BEFORE the label, not trail it.
                long_lines = [line for line in reference_lines if LONG_LABEL in line]
                self.assertEqual(len(long_lines), 1)
                self.assertLess(
                    long_lines[0].index(REFERENCE_MARKER),
                    long_lines[0].index(LONG_LABEL),
                )
                # Chinese, completed, in_progress, blocked all covered.
                self.assertTrue(any("中文" in line for line in reference_lines))
                self.assertTrue(any("in_progress" in line for line in reference_lines))
                for label, icon in (
                    ("已完成：中文长标题复核节点", "[x]"),
                    ("进行中：中文 in_progress 节点", "[~]"),
                    ("被阻塞：等待上游机械闸结论", "[!]"),
                ):
                    rows = [line for line in lines if label in line]
                    self.assertEqual(len(rows), 2, label)
                    for row in rows:
                        self.assertIn(icon, row, row)

                # Same WorkItem in three outline contexts: one primary, two references.
                self.assertEqual(tree.count("Shared work"), 3)
                self.assertEqual(
                    sum(1 for line in lines
                        if "Shared work" in line and REFERENCE_MARKER in line),
                    2,
                )
                # Acceptance criterion 2: no color/icon-only meaning; rejected B stays out.
                self.assertIn(
                    "reference (same WorkItem, not a copy):", tree.replace("↪", "")
                )
                self.assertNotIn("[reference to", tree)

    def test_review_matrix_is_identical_across_carriers(self):
        captured: dict[str, dict[str, str]] = {}
        for storage in ("single", "sqlite"):
            with tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                target = build_review_fixture(tmpdir, storage)["target"]
                captured[storage] = {
                    "tree": run_cli("tree", target, "--depth", "6", cwd=tmpdir).stdout,
                    "section": tree_block(
                        run_cli("section", target, cwd=tmpdir).stdout
                    ),
                }
        for view in ("tree", "section"):
            self.assertEqual(captured["single"][view], captured["sqlite"][view], view)


if __name__ == "__main__":
    unittest.main()

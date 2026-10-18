#!/usr/bin/env python3
"""Deterministic tests for the Composer discovery + snapshot rewrite (issue #177)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from discover_catalog import (  # noqa: E402
    detect_layout,
    discover_catalog,
    main as discover_main,
    resolve_root,
    skill_files,
)
from generate_snapshot import build_snapshot, main as snapshot_main  # noqa: E402


def write_skill(package_dir: Path, *, source: str | None = "zagentic") -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = (
        "---\n"
        f"name: {package_dir.name}\n"
        "description: fixture skill\n"
    )
    if source is not None:
        frontmatter += f"source: {source}\n"
    frontmatter += "---\n# fixture\n"
    (package_dir / "SKILL.md").write_text(frontmatter, encoding="utf-8")


class FlatLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        write_skill(self.root / "zj-alpha")
        write_skill(self.root / "zj-beta", source="external")
        self.script = self.root / "zj-alpha" / "scripts" / "disc.py"
        self.script.parent.mkdir(parents=True, exist_ok=True)
        self.script.write_text("", encoding="utf-8")

    def test_layout_detected(self) -> None:
        self.assertEqual(detect_layout(self.root), "installed-flat")

    def test_classification_by_frontmatter(self) -> None:
        catalog = discover_catalog(self.root)
        by_name = {s["name"]: s for s in catalog["skills"]}
        self.assertTrue(by_name["zj-alpha"]["is_zagentic"])
        self.assertFalse(by_name["zj-beta"]["is_zagentic"])

    def test_deterministic_sorted(self) -> None:
        catalog = discover_catalog(self.root)
        paths = [s["path"] for s in catalog["skills"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(paths, ["zj-alpha/SKILL.md", "zj-beta/SKILL.md"])

    def test_catalog_present_true(self) -> None:
        catalog = discover_catalog(self.root)
        self.assertTrue(catalog["catalog_present"])
        self.assertEqual(catalog["layout"], "installed-flat")
        self.assertEqual(len(catalog["skills"]), 2)


class MonorepoDevLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "skills" / "engineering" / "zj-guide").mkdir(parents=True)
        write_skill(self.root / "skills" / "engineering" / "zj-guide")
        write_skill(self.root / "skills" / "productivity" / "group" / "zj-nested")
        self.script = (
            self.root / "skills" / "productivity" / "zj-composer" / "scripts" / "disc.py"
        )
        self.script.parent.mkdir(parents=True, exist_ok=True)
        self.script.write_text("", encoding="utf-8")

    def test_layout_detected(self) -> None:
        self.assertEqual(detect_layout(self.root), "monorepo-dev")

    def test_paths_are_root_relative(self) -> None:
        catalog = discover_catalog(self.root)
        paths = {s["path"] for s in catalog["skills"]}
        self.assertIn("skills/engineering/zj-guide/SKILL.md", paths)
        self.assertIn("skills/productivity/group/zj-nested/SKILL.md", paths)

    def test_classification(self) -> None:
        catalog = discover_catalog(self.root)
        self.assertTrue(all(s["is_zagentic"] for s in catalog["skills"]))


class HonestFailureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.empty = Path(tempfile.mkdtemp())
        self.no_skills = Path(tempfile.mkdtemp())
        (self.no_skills / "README.md").write_text("no skills here", encoding="utf-8")

    def test_empty_root_reports_absent(self) -> None:
        catalog = discover_catalog(self.empty)
        self.assertFalse(catalog["catalog_present"])
        self.assertIn("diagnostics", catalog)
        self.assertEqual(catalog["skills"], [])

    def test_no_skill_packages_reports_absent(self) -> None:
        catalog = discover_catalog(self.no_skills)
        self.assertFalse(catalog["catalog_present"])

    def test_snapshot_main_exits_nonzero(self) -> None:
        code = snapshot_main(["--root", str(self.empty)])
        self.assertEqual(code, 1)


class SymlinkEscapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        write_skill(self.root / "zj-inside")
        outside = Path(tempfile.mkdtemp()) / "secret.md"
        outside.write_text("should not be read", encoding="utf-8")
        evil = self.root / "zj-evil"
        evil.mkdir()
        (evil / "SKILL.md").symlink_to(outside)

    def test_symlinked_skill_excluded(self) -> None:
        catalog = discover_catalog(self.root)
        names = {s["name"] for s in catalog["skills"]}
        self.assertIn("zj-inside", names)
        self.assertNotIn("zj-evil", names)

    def test_skill_files_excludes_escape(self) -> None:
        files = skill_files(self.root, "installed-flat")
        resolved_root = self.root.resolve()
        for path in files:
            self.assertTrue(path.resolve().is_relative_to(resolved_root))


class ResolveRootTest(unittest.TestCase):
    def test_flat_derivation(self) -> None:
        root = Path(tempfile.mkdtemp())
        write_skill(root / "zj-x")
        script = root / "zj-x" / "scripts" / "disc.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("", encoding="utf-8")
        self.assertEqual(resolve_root(start_script=script), root.resolve())

    def test_dev_derivation(self) -> None:
        root = Path(tempfile.mkdtemp())
        write_skill(root / "skills" / "productivity" / "zj-composer")
        script = (
            root / "skills" / "productivity" / "zj-composer" / "scripts" / "disc.py"
        )
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("", encoding="utf-8")
        self.assertEqual(resolve_root(start_script=script), root.resolve())

    def test_explicit_override(self) -> None:
        root = Path(tempfile.mkdtemp())
        other = Path(tempfile.mkdtemp())
        self.assertEqual(resolve_root(explicit=other, start_script=root / "disc.py"), other.resolve())


class SnapshotDigestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        write_skill(self.root / "zj-one")
        write_skill(self.root / "zj-two", source="external")

    def test_snapshot_digest_is_content_addressed(self) -> None:
        snapshot = build_snapshot(self.root)
        self.assertTrue(snapshot["catalog"]["catalog_present"])
        files = snapshot["source"]["files"]
        digests = {f["path"]: f["sha256"] for f in files}
        self.assertIn("zj-one/SKILL.md", digests)
        self.assertIsNotNone(digests["zj-one/SKILL.md"])
        # Same content yields the same digest across runs.
        again = build_snapshot(self.root)
        self.assertEqual(again["snapshot_id"], snapshot["snapshot_id"])

    def test_snapshot_records_real_root(self) -> None:
        snapshot = build_snapshot(self.root)
        self.assertEqual(snapshot["source"]["skills_root"], str(self.root.resolve()))


class ScriptOutsidePackageTest(unittest.TestCase):
    def test_script_outside_package_yields_absent(self) -> None:
        # Spec Slice 1/3: when Composer's script is not inside a skill-package
        # tree, root derivation must not invent a catalog; discovery reports
        # catalog_present:false (the honest-failure path) rather than drifting.
        root = Path(tempfile.mkdtemp())
        script = root / "scripts" / "disc.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("", encoding="utf-8")
        resolved = resolve_root(start_script=script)
        catalog = discover_catalog(resolved)
        self.assertFalse(catalog["catalog_present"])
        self.assertEqual(catalog["skills"], [])


class MalformedFrontmatterTest(unittest.TestCase):
    def test_missing_name_warns_per_skill(self) -> None:
        # Spec Slice 2: provenance/metadata defects belong on the per-skill
        # record, not only the catalog-level warning bucket.
        root = Path(tempfile.mkdtemp())
        package = root / "zj-bad"
        package.mkdir(parents=True, exist_ok=True)
        (package / "SKILL.md").write_text(
            "---\ndescription: missing name\n---\n# fixture\n", encoding="utf-8"
        )
        catalog = discover_catalog(root)
        self.assertEqual(len(catalog["skills"]), 1)
        skill = catalog["skills"][0]
        self.assertIn("frontmatter name is missing or empty", skill["warnings"])


class SnapshotHonestFailureJsonTest(unittest.TestCase):
    def test_absent_writes_diagnostic_to_stdout(self) -> None:
        # Spec design principle: structured diagnostics belong on stdout JSON,
        # not stderr (discover_catalog already prints to stdout).
        empty = Path(tempfile.mkdtemp())
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = snapshot_main(["--root", str(empty)])
        self.assertEqual(code, 1)
        payload = json.loads(buffer.getvalue())
        self.assertFalse(payload["catalog_present"])
        self.assertIn("diagnostics", payload)


class NoZagenticCatalogTest(unittest.TestCase):
    def test_no_zagentic_still_present_and_exit_zero(self) -> None:
        # Spec Slice 3: locating a root with skill packages but zero ZAgentic
        # skills is a legal non-empty catalog -> catalog_present:true, exit 0.
        root = Path(tempfile.mkdtemp())
        write_skill(root / "zj-a", source="external")
        write_skill(root / "zj-b", source="external")
        catalog = discover_catalog(root)
        self.assertTrue(catalog["catalog_present"])
        self.assertEqual(len(catalog["skills"]), 2)
        self.assertTrue(all(not s["is_zagentic"] for s in catalog["skills"]))
        self.assertEqual(discover_main(["--root", str(root)]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

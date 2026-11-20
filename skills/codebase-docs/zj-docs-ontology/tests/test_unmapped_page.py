#!/usr/bin/env python3
"""UNMAPPED_PAGE — map-coverage completeness (baseline pre-flight, 2026-11-20).

Found on a real run: a long-lived ADR sat committed under docs/zj-adr/ with no
map entry while docs_governance.py --validate exited zero — the proposal
inventory is disk-derived, but every diagnostic is map-anchored, so the page
was invisible to all of them and a reorganization anchored on that green
baseline would have inherited the hole. These tests pin both directions: the
defect state fires, the repaired state is green, and the deliberate
exclusions (non-markdown evidence, process material, proposal mode) hold.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
SPEC_NAME = "docs_governance_unmapped"

import importlib.util
import sys

SPEC = importlib.util.spec_from_file_location(
    SPEC_NAME, SKILL_ROOT / "scripts" / "docs_governance.py"
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def unmapped(payload: dict) -> list[dict[str, str]]:
    return [item for item in payload["diagnostics"] if item["code"] == "UNMAPPED_PAGE"]


class UnmappedPageDefectTest(unittest.TestCase):
    """缺陷态：committed-but-unmapped page fires while every other check is green."""

    def payload(self) -> dict:
        return TOOL.report(FIXTURES / "unmapped-page", validate_links=True)

    def test_the_orphan_page_fires(self) -> None:
        self.assertEqual(1, len(unmapped(self.payload())))

    def test_the_signal_names_the_page(self) -> None:
        self.assertEqual("docs/prds/orphan.md", unmapped(self.payload())[0]["path"])

    def test_the_remedy_is_register_or_reclassify_never_delete(self) -> None:
        message = unmapped(self.payload())[0]["message"]
        self.assertIn("register", message)
        self.assertIn("never delete", message)

    def test_the_mapped_page_stays_silent(self) -> None:
        paths = {item["path"] for item in unmapped(self.payload())}
        self.assertNotIn("docs/prds/priced.md", paths)

    def test_a_non_markdown_file_is_an_evidence_surface_not_a_page(self) -> None:
        paths = {item["path"] for item in unmapped(self.payload())}
        self.assertNotIn("docs/prds/spec.json", paths)

    def test_the_signal_does_not_change_exit_semantics(self) -> None:
        payload = self.payload()
        self.assertIn("UNMAPPED_PAGE", TOOL.SIGNAL_CODES)
        self.assertNotIn("UNMAPPED_PAGE", TOOL.ERROR_CODES)
        self.assertFalse(TOOL.has_error(payload))


class UnmappedPageRepairedTest(unittest.TestCase):
    """修复态：registering the page in the map clears the signal."""

    def test_registering_the_page_clears_the_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "unmapped-page", root)
            map_path = root / "docs" / "team-map.md"
            map_path.write_text(
                "# Team map\n\n"
                "- [Product requirement](prds/priced.md)\n"
                "- [Orphan requirement](prds/orphan.md)\n",
                encoding="utf-8",
            )
            payload = TOOL.report(root, validate_links=True)
            self.assertEqual([], unmapped(payload))

    def test_a_registered_page_moved_out_of_coverage_fires_again(self) -> None:
        """Coverage is a fact about the map's links, not about the page's
        existence: deleting the entry re-arms the signal."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "unmapped-page", root)
            (root / "docs" / "team-map.md").write_text(
                "# Team map\n\n- [Orphan requirement](prds/orphan.md)\n",
                encoding="utf-8",
            )
            payload = TOOL.report(root, validate_links=True)
            paths = {item["path"] for item in unmapped(payload)}
            self.assertEqual({"docs/prds/priced.md"}, paths)


class UnmappedPageBoundaryTest(unittest.TestCase):
    """Deliberate exclusions — each one is a contract claim, not an oversight."""

    def test_process_material_is_inventoried_never_map_bound(self) -> None:
        payload = TOOL.report(FIXTURES / "read-boundary", validate_links=True)
        self.assertEqual([], unmapped(payload))
        self.assertIn(
            "docs/plans/active.md", payload["inventory"]["process_material"]["plans"]
        )

    def test_proposal_mode_stays_about_shape(self) -> None:
        """Link-level checks belong to --validate (the same placement rule as
        MAP_AUTHORITY_CONFLICT); --proposal carries no coverage claims."""
        payload = TOOL.report(FIXTURES / "unmapped-page", validate_links=False)
        self.assertEqual([], unmapped(payload))


if __name__ == "__main__":
    unittest.main()

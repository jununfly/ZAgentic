#!/usr/bin/env python3
"""Contract tests for the bounded architecture documentation validator."""

from __future__ import annotations

import contextlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
MODULE_PATH = SKILL_ROOT / "scripts" / "validate_architecture_docs.py"
SPEC = importlib.util.spec_from_file_location("architecture_validator", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ArchitectureValidatorTest(unittest.TestCase):
    def codes(self, fixture: str) -> set[str]:
        diagnostics, _, _ = VALIDATOR.validate(FIXTURES / fixture)
        return {item.code for item in diagnostics}

    def test_accepts_minimal_and_multiview_handbooks(self) -> None:
        self.assertEqual(self.codes("valid-minimal"), set())
        self.assertEqual(self.codes("valid-multiview"), set())

    def test_accepts_a_lazy_architecture_category(self) -> None:
        self.assertEqual(self.codes("valid-lazy"), set())

    def test_rejects_duplicate_authority_and_source_drift(self) -> None:
        self.assertIn("AUTHORITY_ID_DUPLICATE", self.codes("invalid-duplicate-authority"))
        self.assertIn("SOURCE_TARGET_MISSING", self.codes("invalid-source-drift"))

    def test_rejects_unaccepted_adr(self) -> None:
        self.assertIn("ADR_UNACCEPTED", self.codes("invalid-adr"))

    def test_never_reads_process_or_fixture_payloads(self) -> None:
        diagnostics, reads, _ = VALIDATOR.validate(FIXTURES / "read-boundary")
        self.assertEqual(diagnostics, [])
        self.assertFalse(any(path.endswith("docs/plans/active.md") for path in reads))
        self.assertFalse(any(path.endswith("fixtures/payload.json") for path in reads))


NAMING = "invalid-page-naming"
STABLE_CONTROL = "docs/architecture/ta-catalog.md"
EXTERNAL = "valid-external-layout"


class PageNamingTest(unittest.TestCase):
    """#49 — a mapped architecture page must carry a stable name.

    Stable means: prefixed `ta-` / `ba-` / `pa-`, lowercase and hyphenated,
    and free of dates, commit shas, versions, and temporary-status words. A
    name that encodes *when* it was written or *how current* it is will rot
    the first time the page is revised.
    """

    def diagnostics(self, fixture: str):
        return VALIDATOR.validate(FIXTURES / fixture)[0]

    def codes_for(self, path: str, fixture: str = NAMING) -> set[str]:
        return {item.code for item in self.diagnostics(fixture) if item.path == path}

    def test_rejects_a_date_stamped_name(self) -> None:
        self.assertIn("PAGE_NAME_DATE", self.codes_for("docs/architecture/ta-overview-2026-09-10.md"))

    def test_rejects_a_commit_sha_name(self) -> None:
        self.assertIn("PAGE_NAME_DATE", self.codes_for("docs/architecture/ta-flow-9f3c1ab.md"))

    def test_rejects_a_missing_prefix(self) -> None:
        self.assertIn("PAGE_NAME_PREFIX", self.codes_for("docs/architecture/overview.md"))

    def test_rejects_a_name_that_is_not_lowercase_hyphenated(self) -> None:
        self.assertIn("PAGE_NAME_SHAPE", self.codes_for("docs/architecture/ta-Checkout_Flow.md"))

    def test_rejects_version_and_temporary_status_names(self) -> None:
        self.assertIn("PAGE_NAME_VERSION_OR_STATUS", self.codes_for("docs/architecture/ta-catalog-v2.md"))
        self.assertIn("PAGE_NAME_VERSION_OR_STATUS", self.codes_for("docs/architecture/ta-catalog-draft.md"))

    def test_leaves_the_stable_control_page_alone(self) -> None:
        self.assertEqual(set(), self.codes_for(STABLE_CONTROL))

    def test_adds_no_naming_diagnostics_to_valid_fixtures(self) -> None:
        for fixture in ("valid-minimal", "valid-multiview", "valid-lazy", EXTERNAL):
            codes = {item.code for item in self.diagnostics(fixture) if item.code.startswith("PAGE_NAME")}
            self.assertEqual(set(), codes, fixture)


class ExternalLayoutTest(unittest.TestCase):
    """#52 — the validator must survive a repository shaped unlike this one.

    The other valid fixtures all share ZAgentic's layout, so green on them only
    proves self-consistency. `valid-external-layout` has no `docs/` tree at all,
    keeps its map at `handbook/map.md`, and nests architecture pages one level
    deeper. Two things have to hold: the layout produces no diagnostics, and the
    pages are still genuinely checked — otherwise "no diagnostics" would just
    mean "nothing was looked at".
    """

    def mutated(self):
        """A throwaway copy, so a probe never edits the fixture in place."""
        return mutated_fixture()

    def codes_in(self, root: Path) -> set[str]:
        return {item.code for item in VALIDATOR.validate(root)[0]}

    def test_accepts_a_repository_without_a_docs_tree(self) -> None:
        diagnostics, reads, metadata = VALIDATOR.validate(FIXTURES / EXTERNAL)
        self.assertEqual([], diagnostics)
        self.assertEqual("explicit-pointer", metadata["origin"])
        self.assertEqual("handbook/map.md", metadata["map"])
        joined = "\n".join(reads)
        for page in ("ta-billing-engine", "pa-inference-router", "ba-tenant-model"):
            self.assertIn(page, joined)  # green must not mean "silently skipped"

    def test_unmapped_pages_are_never_read(self) -> None:
        """An unstable draft name and a date-stamped note are not the
        validator's business until the map claims them."""
        _, reads, _ = VALIDATOR.validate(FIXTURES / EXTERNAL)
        joined = "\n".join(reads)
        self.assertNotIn("drafts/ta-checkout-v2", joined)
        self.assertNotIn("notes/meeting-2026-01-02", joined)

    def test_the_layout_is_checked_not_skipped(self) -> None:
        """Drop a required view section: the contract diagnostic must appear."""
        with self.mutated() as repo:
            page = repo / "handbook" / "architecture" / "subsystems" / "ta-billing-engine.md"
            page.write_text(page.read_text().replace("## Responsibility\nx\n", ""))
            self.assertIn("PAGE_VIEW_CONTRACT_MISSING", self.codes_in(repo))

    def test_mapping_an_unstable_name_is_what_fails(self) -> None:
        """The negative control: the draft page is only wrong once the map points at it."""
        with self.mutated() as repo:
            map_path = repo / "handbook" / "map.md"
            map_path.write_text(
                map_path.read_text()
                + "- [Checkout draft](architecture/drafts/ta-checkout-v2.md) — authority-id: nimbus.flow.checkout\n"
            )
            self.assertIn("PAGE_NAME_VERSION_OR_STATUS", self.codes_in(repo))


@contextlib.contextmanager
def mutated_fixture(name: str = EXTERNAL):
    """A throwaway copy of a fixture, so a probe never edits it in place."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(FIXTURES / name, repo)
        yield repo


SOURCE_MAP_PAGE = "handbook/architecture/subsystems/ta-billing-engine.md"
PAGE_RELATIVE = "../../../src/billing/engine.rs"
ROOT_RELATIVE = "src/billing/engine.rs"
ESCAPING = "../../../../../src/billing/engine.rs"


class LinkBaseTest(unittest.TestCase):
    """#67 — one base, pinned rather than left to be inferred.

    Every relative path in a handbook resolves from the directory holding the
    file that writes it. Until #67 the `## Source map` was the exception and
    resolved from the repository root; the exception was invisible, because the
    entries written Markdown's way — 86 of them in this repository's own
    handbook — resolved outside the root and were dropped with no diagnostic at
    all. The section was never checked and the exit code still said 0.

    So each test resolves the same target both ways and asserts which spelling
    lands on the file. Asserting "the fixture is clean" is not enough: that
    passes under either base.
    """

    def codes_in(self, root: Path) -> set[str]:
        return {item.code for item in VALIDATOR.validate(root)[0]}

    def test_source_map_paths_resolve_from_the_page(self) -> None:
        root = (FIXTURES / EXTERNAL).resolve()
        page = root / SOURCE_MAP_PAGE
        resolved = dict(VALIDATOR.source_paths(root, page, page.read_text(encoding="utf-8")))
        self.assertEqual(root / "src" / "billing" / "engine.rs", resolved[PAGE_RELATIVE])

    def test_root_relative_spelling_is_what_fails(self) -> None:
        """The other spelling still resolves — to a path *under the page* — so
        a Source map written the old way is reported, not silently ignored."""
        with mutated_fixture() as repo:
            page = repo / SOURCE_MAP_PAGE
            page.write_text(page.read_text().replace(PAGE_RELATIVE, ROOT_RELATIVE))
            self.assertIn("SOURCE_TARGET_MISSING", self.codes_in(repo))

    def test_this_repository_source_maps_are_actually_resolved(self) -> None:
        """The control that #67 was about. This handbook was green before it
        too; what was missing is that its Source map entries resolved to files.
        A green exit code cannot tell those apart, so count the entries."""
        repo = handbook_repo()
        if repo is None:
            self.skipTest("not running inside a handbook repository")
        unresolved: list[str] = []
        checked = 0
        for page in sorted((repo / "docs").rglob("*.md")):
            text = page.read_text(encoding="utf-8")
            for value, target in VALIDATOR.source_paths(repo, page, text):
                checked += 1
                if target is None or not target.exists():
                    unresolved.append(f"{page.relative_to(repo).as_posix()}: {value}")
        self.assertGreater(checked, 0)
        self.assertEqual([], unresolved)

    def test_a_target_that_escapes_the_repository_is_reported(self) -> None:
        """#69 — a path climbing past the root cannot mean anything, and it used
        to be dropped in silence: `path_from` returns None for it and the loop
        skipped None. The message distinguishes it from a stale path, because
        the fixes differ — one is "the file moved", the other "this was never
        right"."""
        with mutated_fixture() as repo:
            page = repo / SOURCE_MAP_PAGE
            page.write_text(page.read_text().replace(PAGE_RELATIVE, ESCAPING))
            codes = self.codes_in(repo)
            self.assertIn("SOURCE_TARGET_OUTSIDE", codes)
            self.assertNotIn("SOURCE_TARGET_MISSING", codes)

    def test_an_external_reference_is_not_an_escape(self) -> None:
        """A Source map may cite a stable external reference. It also reaches
        `path_from` as None, so collapsing the two would turn every external
        citation into a defect."""
        with mutated_fixture() as repo:
            page = repo / SOURCE_MAP_PAGE
            before = page.read_text()
            after = before.replace(f"`{PAGE_RELATIVE}`", "[spec](https://example.com/spec)")
            self.assertNotEqual(before, after, "the edit did not apply; this would pass unedited")
            page.write_text(after)
            # Guard against the edit being invisible to the parser: an autolink
            # (`<https://…>`) is not matched by LINK_RE, so a test built on one
            # would assert "no diagnostics" against a Source map the validator
            # never read. Prove the entry is seen before asserting it is clean.
            self.assertIn(
                "https://example.com/spec",
                [value for value, _ in VALIDATOR.source_paths(repo.resolve(), page, after)],
            )
            self.assertEqual(set(), self.codes_in(repo))

    def test_map_links_resolve_from_the_map(self) -> None:
        with mutated_fixture() as repo:
            map_path = repo / "handbook" / "map.md"
            map_path.write_text(
                map_path.read_text().replace(
                    "(architecture/subsystems/ta-billing-engine.md)",
                    "(handbook/architecture/subsystems/ta-billing-engine.md)",
                )
            )
            self.assertIn("MAP_LINK_BROKEN", self.codes_in(repo))


def handbook_repo() -> Path | None:
    """The nearest ancestor that is both a repo and carries a `docs/` tree.

    A fixed `parents[N]` breaks the moment the skill is copied into
    `~/.codex/skills/…`, where the same index lands on `$HOME` and the
    validator dutifully fails on someone's home directory.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() and (parent / "docs").is_dir():
            return parent
    return None


class CommandLineTest(unittest.TestCase):
    """Exit codes live at the CLI seam; the in-process seam cannot see them."""

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args], capture_output=True, text=True
        ).returncode

    def test_naming_fixture_exits_nonzero(self) -> None:
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / NAMING)))

    def test_valid_fixture_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(FIXTURES / "valid-minimal")))

    def test_external_layout_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(FIXTURES / EXTERNAL)))

    def test_this_repository_stays_green(self) -> None:
        """The real handbook is the control: a naming rule that fires on
        today's pages is too strict to ship."""
        repo = handbook_repo()
        if repo is None:
            self.skipTest("no repo with a docs/ tree above this skill copy")
        self.assertEqual(0, self.exit_code(str(repo)))


if __name__ == "__main__":
    unittest.main()

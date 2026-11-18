#!/usr/bin/env python3
"""Regression tests for the read-only documentation governance proposal."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
CONFLICT = "conflicting-authority"
SPEC = importlib.util.spec_from_file_location("docs_governance", SKILL_ROOT / "scripts" / "docs_governance.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def front_matter(page: Path) -> str:
    """Only the header block: the fixtures carry prose that mentions these
    fields without declaring them."""
    text = page.read_text(encoding="utf-8")
    parts = text.split("---\n", 2)
    return parts[1] if text.startswith("---") and len(parts) > 2 else ""


class GovernanceProposalTest(unittest.TestCase):
    def test_greenfield_is_a_confirmation_bound_proposal(self) -> None:
        payload = TOOL.report(FIXTURES / "greenfield", validate_links=True)
        self.assertEqual(payload["map_origin"], "greenfield")
        self.assertEqual(payload["mutations"], [])
        self.assertEqual(payload["proposed_actions"][0]["action"], "create-map")

    def test_explicit_compatible_map_wins(self) -> None:
        payload = TOOL.report(FIXTURES / "existing-map", validate_links=True)
        self.assertEqual(payload["map"], "docs/team-map.md")
        self.assertEqual(payload["map_origin"], "explicit-pointer")
        self.assertEqual(payload["mutations"], [])

    def test_broken_map_link_is_mechanical(self) -> None:
        payload = TOOL.report(FIXTURES / "broken-map", validate_links=True)
        self.assertIn("MAP_LINK_BROKEN", {item["code"] for item in payload["diagnostics"]})

    def test_process_content_is_listed_but_never_read(self) -> None:
        payload = TOOL.report(FIXTURES / "read-boundary", validate_links=True)
        self.assertIn("docs/plans/active.md", payload["inventory"]["process_material"]["plans"])
        self.assertNotIn("docs/plans/active.md", payload["read_paths"])
        self.assertEqual(payload["mutations"], [])


class AuthorityConflictTest(unittest.TestCase):
    """#51 — one authority-id bound to two pages is a governance failure.

    Not a matter of which page happens to come first in the map: two pages
    answering the same bounded question is exactly what the Human has to settle,
    so it is reported rather than silently resolved by navigation order.

    The fixture isolates the *binding* layer from the *declaration* layer. The
    map binds the id twice and no page declares anything, so this is the only
    tool that can fire here — see the last test in this class for why that
    matters.
    """

    def payload(self, validate: bool = True):
        return TOOL.report(FIXTURES / CONFLICT, validate_links=validate)

    def conflicts(self) -> list[dict[str, str]]:
        return [item for item in self.payload()["diagnostics"] if item["code"] == "MAP_AUTHORITY_CONFLICT"]

    def test_one_authority_id_bound_to_two_pages_is_reported_once(self) -> None:
        self.assertEqual(1, len(self.conflicts()))

    def test_the_conflict_names_both_pages(self) -> None:
        message = self.conflicts()[0]["message"]
        self.assertIn("docs/prds/payment.md", message)
        self.assertIn("docs/designs/payments.md", message)

    def test_a_link_without_an_authority_binding_is_not_part_of_it(self) -> None:
        self.assertNotIn("docs/prds/refund.md", self.conflicts()[0]["message"])

    def test_the_fixture_stays_inside_the_binding_layer(self) -> None:
        """Two ways this sample could slip into `zj-docs-architecture`'s layer,
        where a page's own front matter and its `docs/architecture/` placement
        are the contract. Either one would make the fixture describe a
        repository that one tool calls valid and the other calls broken — and
        both tools run against the same repository, so no such repository
        exists.
        """
        root = FIXTURES / CONFLICT
        pages = [p for p in (root / "docs").rglob("*.md") if p.name != "team-map.md"]
        self.assertNotEqual([], pages)
        self.assertEqual(
            [],
            [str(p.relative_to(root)) for p in pages if "architecture" in p.parts],
            "an architecture page here must satisfy the architecture page contract too",
        )
        self.assertEqual(
            [],
            [str(p.relative_to(root)) for p in pages if "authority" in front_matter(p)],
            "a page declaring the id would also fire the declaration-layer check",
        )

    def test_the_report_stays_a_proposal(self) -> None:
        self.assertEqual([], self.payload()["mutations"])

    def test_proposal_mode_does_not_report_it(self) -> None:
        """Link-level checks belong to --validate; --proposal stays about shape."""
        codes = {item["code"] for item in self.payload(validate=False)["diagnostics"]}
        self.assertNotIn("MAP_AUTHORITY_CONFLICT", codes)


class RetirementTest(unittest.TestCase):
    """The retirement contract (governance-contract.md, "Retirement") is only
    prose until the tool can see it. A map entry declares retirement with
    `retired-to:`; the mechanical surface is then three-fold: the named
    destination must exist, the declaration must name a page, and inbound
    references must drain before the page is a deletion candidate.

    The drain scan skips evidence and process-material surfaces on purpose:
    frozen records and transient plans are not living references, and reading
    them would cross the read boundary this tool already asserts.
    """

    def payload(self, fixture: str, validate: bool = True) -> dict:
        return TOOL.report(FIXTURES / fixture, validate_links=validate)

    def codes(self, fixture: str) -> set[str]:
        return {item["code"] for item in self.payload(fixture)["diagnostics"]}

    def test_drain_incomplete_is_reported_with_the_source(self) -> None:
        codes = self.codes("retired-drain")
        self.assertIn("RETIRE_DRAIN_INCOMPLETE", codes)
        item = next(i for i in self.payload("retired-drain")["diagnostics"] if i["code"] == "RETIRE_DRAIN_INCOMPLETE")
        self.assertIn("docs/prds/referrer.md", item["message"])
        self.assertIn("docs/prds/old-page.md", item["message"])

    def test_a_drained_page_is_a_deletion_candidate(self) -> None:
        payload = self.payload("retired-clean")
        self.assertEqual([], [i for i in payload["diagnostics"] if i["code"].startswith("RETIRE_")])
        entry = payload["retirement"]["entries"][0]
        self.assertEqual("deletion-candidate", entry["status"])
        self.assertEqual(0, entry["inbound_count"])

    def test_a_tombstone_may_not_name_a_missing_destination(self) -> None:
        self.assertIn("RETIRE_TARGET_MISSING", self.codes("retired-missing-target"))

    def test_the_missing_destination_does_not_block_the_drain_report(self) -> None:
        entry = self.payload("retired-missing-target")["retirement"]["entries"][0]
        self.assertFalse(entry["target_exists"])

    def test_retirement_checks_belong_to_validate_mode(self) -> None:
        codes = self.codes_retirement_proposal = {
            item["code"] for item in self.payload("retired-drain", validate=False)["diagnostics"]
        }
        self.assertNotIn("RETIRE_DRAIN_INCOMPLETE", codes)

    def test_the_drain_scan_never_reads_process_or_evidence_material(self) -> None:
        """The boundary is behavioral: a process page linking at the retired
        page must neither fire the diagnostic nor appear as a read path."""
        root = FIXTURES / "retired-drain"
        plans = root / "docs" / "plans"
        plans.mkdir(exist_ok=True)
        page = plans / "active.md"
        page.write_text("Plan notes linking [legacy](../prds/old-page.md).\n", encoding="utf-8")
        try:
            payload = self.payload("retired-drain")
            drain = [i for i in payload["diagnostics"] if i["code"] == "RETIRE_DRAIN_INCOMPLETE"]
            self.assertEqual(1, len(drain))
            self.assertNotIn("docs/plans/active.md", drain[0]["message"])
            self.assertNotIn("docs/plans/active.md", payload["read_paths"])
        finally:
            import shutil

            shutil.rmtree(plans)


class ArchitectureWitnessTest(unittest.TestCase):
    """Q7: the `/zj-docs-architecture` composition at ontology Step 5 gains a
    mechanical witness. Reuses P0 Ruling 3's two codes — no new diagnostic code:
    existence is an external fact (ERROR); fingerprint is in-pass (signal).

    The witness is caller-supplied: the tool never imports or invokes the
    architecture skill (portability boundary). A report that declares no
    witness stays valid — the tool cannot know whether this pass was a full
    governance pass; that declaration is the caller's responsibility.
    """

    ROOT = FIXTURES / "existing-map"

    def payload(self, **kwargs: object) -> dict:
        return TOOL.report(self.ROOT, validate_links=True, **kwargs)

    def artifact(self) -> Path:
        """A real file stands in for saved architecture-validator stdout: the
        witness only checks existence + fingerprint, never content semantics."""
        path = self.ROOT / "AGENTS.md"
        self.assertTrue(path.is_file())
        return path

    def codes(self, payload: dict) -> set[str]:
        return {item["code"] for item in payload["diagnostics"]}

    def test_undeclared_witness_keeps_existing_report_shape(self) -> None:
        payload = self.payload()
        witness = payload["architecture_witness"]
        self.assertEqual("not-declared", witness["status"])
        self.assertFalse(witness["exists"])
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(payload))
        self.assertEqual([], payload["mutations"])

    def test_declared_but_missing_artifact_is_a_mechanical_error(self) -> None:
        payload = self.payload(arch_witness="tmp/no-such-artifact.json")
        self.assertIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(payload))
        witness = payload["architecture_witness"]
        self.assertEqual("declared", witness["status"])
        self.assertFalse(witness["exists"])
        self.assertIn("tmp/no-such-artifact.json", witness["artifact"])

    def test_existing_artifact_records_fingerprint_without_error(self) -> None:
        payload = self.payload(arch_witness=str(self.artifact()))
        witness = payload["architecture_witness"]
        self.assertTrue(witness["exists"])
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(payload))
        digest = hashlib.sha256(self.artifact().read_bytes()).hexdigest()
        self.assertEqual(digest, witness["fingerprint"])

    def test_fingerprint_mismatch_is_a_signal_not_an_error(self) -> None:
        payload = self.payload(
            arch_witness=str(self.artifact()),
            arch_fingerprint="0" * 64,
        )
        self.assertIn("EXEC_STEP5_FINGERPRINT_MISMATCH", self.codes(payload))
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(payload))

    def test_matching_fingerprint_emits_no_signal(self) -> None:
        digest = hashlib.sha256(self.artifact().read_bytes()).hexdigest()
        payload = self.payload(arch_witness=str(self.artifact()), arch_fingerprint=digest)
        self.assertNotIn("EXEC_STEP5_FINGERPRINT_MISMATCH", self.codes(payload))
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(payload))

    def test_witness_does_not_expand_the_read_boundary(self) -> None:
        """The tool hashes bytes at a caller-supplied path; declaring a witness
        must not add that path to the tool's own read_paths inventory."""
        before = self.payload()["read_paths"]
        after = self.payload(arch_witness=str(self.artifact()))["read_paths"]
        self.assertEqual(before, after)


class ArchitectureWitnessCommandLineTest(unittest.TestCase):
    """Strength separation lives at the exit-code seam."""

    ROOT = FIXTURES / "existing-map"

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "docs_governance.py"), *args],
            capture_output=True,
            text=True,
        ).returncode

    def test_missing_artifact_exits_nonzero(self) -> None:
        self.assertNotEqual(
            0,
            self.exit_code(str(self.ROOT), "--validate", "--arch-witness", "tmp/no-such-artifact.json"),
        )

    def test_matching_witness_exits_zero(self) -> None:
        artifact = self.ROOT / "AGENTS.md"
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        self.assertEqual(
            0,
            self.exit_code(
                str(self.ROOT), "--validate",
                "--arch-witness", str(artifact),
                "--arch-fingerprint", digest,
            ),
        )

    def test_fingerprint_mismatch_still_exits_zero(self) -> None:
        artifact = self.ROOT / "AGENTS.md"
        self.assertEqual(
            0,
            self.exit_code(
                str(self.ROOT), "--validate",
                "--arch-witness", str(artifact),
                "--arch-fingerprint", "0" * 64,
            ),
        )


class CommandLineTest(unittest.TestCase):
    """Exit codes only exist at the CLI seam; `report()` cannot show them."""

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "docs_governance.py"), *args],
            capture_output=True,
            text=True,
        ).returncode

    def test_conflicting_authority_exits_nonzero(self) -> None:
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / CONFLICT), "--validate"))

    def test_the_existing_fixtures_keep_their_exit_codes(self) -> None:
        for fixture in ("greenfield", "existing-map", "read-boundary"):
            self.assertEqual(0, self.exit_code(str(FIXTURES / fixture), "--validate"), fixture)
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / "broken-map"), "--validate"))

    def test_undrained_retirement_exits_nonzero(self) -> None:
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / "retired-drain"), "--validate"))
        self.assertNotEqual(0, self.exit_code(str(FIXTURES / "retired-missing-target"), "--validate"))

    def test_a_drained_retirement_keeps_exit_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(FIXTURES / "retired-clean"), "--validate"))


if __name__ == "__main__":
    unittest.main()

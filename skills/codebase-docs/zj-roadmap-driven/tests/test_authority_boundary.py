"""Public authority-boundary contracts for roadmap consumers.

The tests cross the CLI seam: installed Agents consume `section` stdout and the
Markdown written by `render`, not the renderer's private helpers.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"
AUTHORITY_ENVELOPE = """<!-- zj-roadmap-authority/v1
role: process-state
durable-citation: forbidden
promote-via: ADR|design|contract|runtime-evidence
-->"""


def run_cli(*args: object, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *(str(arg) for arg in args)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def run_authority_check(
    root: Path, *extra: object
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "authority-check",
            str(root),
            *(str(arg) for arg in extra),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def seed_process_plan(root: Path) -> str:
    """Create one transient plan artifact and return its project-relative path."""
    process = root / "docs" / "plans" / "release" / "roadmap.json"
    process.parent.mkdir(parents=True, exist_ok=True)
    process.write_text("{}\n", encoding="utf-8")
    return process.relative_to(root).as_posix()


def write_file(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class RoadmapAuthorityEnvelopeCliTest(unittest.TestCase):
    def test_all_public_markdown_views_declare_process_authority(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, init_args in (
                ("single.json", ()),
                ("sqlite.db", ("--storage", "sqlite")),
            ):
                carrier_dir = root / name.replace(".", "-")
                carrier_dir.mkdir()
                carrier = carrier_dir / name
                markdown = carrier_dir / "ROADMAP.md"
                run_cli(
                    "init",
                    carrier,
                    "--title",
                    "Authority boundary",
                    "--md-file",
                    markdown.name,
                    *init_args,
                    cwd=carrier_dir,
                )

                section = run_cli("section", carrier, cwd=carrier_dir).stdout
                run_cli("render", carrier, cwd=carrier_dir)

                with self.subTest(carrier=name, view="section"):
                    self.assertIn(AUTHORITY_ENVELOPE, section)
                with self.subTest(carrier=name, view="render"):
                    self.assertIn(AUTHORITY_ENVELOPE, markdown.read_text(encoding="utf-8"))


class RoadmapAuthorityCheckCliTest(unittest.TestCase):
    def test_durable_code_cannot_cite_a_process_artifact_as_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = root / "docs" / "plans" / "release" / "roadmap.json"
            process.parent.mkdir(parents=True)
            process.write_text("{}\n", encoding="utf-8")
            source = root / "src" / "release.py"
            source.parent.mkdir()
            source.write_text(
                "# Evidence: docs/plans/release/roadmap.json\nREADY = True\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn("src/release.py:1", result.stderr)

    def test_durable_document_cannot_link_to_a_roadmap_view(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            roadmap = root / "docs" / "plans" / "release" / "ROADMAP.md"
            roadmap.parent.mkdir(parents=True)
            roadmap.write_text("## ZJ Roadmap\n", encoding="utf-8")
            architecture = root / "docs" / "architecture" / "system.md"
            architecture.parent.mkdir()
            architecture.write_text(
                "Release support is complete; see [roadmap proof](../plans/release/ROADMAP.md).\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn("docs/architecture/system.md:1", result.stderr)

    def test_governance_example_can_allow_one_reference_on_the_same_line(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            roadmap = root / "docs" / "plans" / "release" / "ROADMAP.md"
            roadmap.parent.mkdir(parents=True)
            roadmap.write_text("## ZJ Roadmap\n", encoding="utf-8")
            governance = root / "docs" / "architecture" / "layers.md"
            governance.parent.mkdir()
            governance.write_text(
                "Forbidden example: [roadmap](../plans/release/ROADMAP.md). "
                "<!-- roadmap-authority-allow: governance-example -->\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Authority boundary: clean.", result.stdout)

    def test_arbitrary_allowance_reason_cannot_bypass_the_boundary(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            roadmap = root / "docs" / "plans" / "release" / "roadmap.json"
            roadmap.parent.mkdir(parents=True)
            roadmap.write_text("{}\n", encoding="utf-8")
            source = root / "src" / "release.py"
            source.parent.mkdir()
            source.write_text(
                "# Evidence: docs/plans/release/roadmap.json "
                "roadmap-authority-allow: convenient\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn("src/release.py:1", result.stderr)

    def test_common_durable_source_types_are_checked(self):
        suffixes = (
            ".c", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js",
            ".json", ".jsx", ".kt", ".php", ".rb", ".rs", ".sh",
            ".swift", ".toml", ".ts", ".tsx", ".yaml", ".yml",
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = root / "docs" / "plans" / "release" / "roadmap.json"
            process.parent.mkdir(parents=True)
            process.write_text("{}\n", encoding="utf-8")
            source_dir = root / "src"
            source_dir.mkdir()
            for index, suffix in enumerate(suffixes):
                (source_dir / f"leak-{index}{suffix}").write_text(
                    "Evidence: docs/plans/release/roadmap.json\n",
                    encoding="utf-8",
                )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            for index, suffix in enumerate(suffixes):
                with self.subTest(suffix=suffix):
                    self.assertIn(f"src/leak-{index}{suffix}:1", result.stderr)

    def test_dependencies_and_generated_temporary_files_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = root / "docs" / "plans" / "release" / "roadmap.json"
            process.parent.mkdir(parents=True)
            process.write_text("{}\n", encoding="utf-8")
            generated = (
                root / "node_modules" / "pkg" / "index.js",
                root / "tmp" / "generated.ts",
            )
            for source in generated:
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(
                    "Evidence: docs/plans/release/roadmap.json\n",
                    encoding="utf-8",
                )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)

    def test_roadmap_completion_claims_cannot_serve_as_durable_proof(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = root / "docs" / "plans" / "release" / "roadmap.json"
            process.parent.mkdir(parents=True)
            process.write_text("{}\n", encoding="utf-8")
            durable = root / "docs" / "architecture" / "release.md"
            durable.parent.mkdir()
            durable.write_text(
                "Proof: roadmap node 1-2-3 is completed.\n"  # roadmap-authority-allow: governance-example
                "根据 roadmap 节点 1-2 已完成。\n"  # roadmap-authority-allow: governance-example
                "Roadmap node 1-2 remains part of the implementation plan.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("docs/architecture/release.md:1", result.stderr)
            self.assertIn("docs/architecture/release.md:2", result.stderr)
            self.assertNotIn("docs/architecture/release.md:3", result.stderr)

    def test_copied_completion_claim_is_rejected_after_process_cleanup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            durable = root / "docs" / "architecture" / "release.md"
            durable.parent.mkdir(parents=True)
            durable.write_text(
                "Evidence: roadmap node 2-4 is done.\n",  # roadmap-authority-allow: governance-example
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "authority-check", str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn("docs/architecture/release.md:1", result.stderr)


class AuthorityCheckScopeCliTest(unittest.TestCase):
    """Issue #239: the gate must scan durable sources, not process state itself.

    Judgement semantics stay untouched; these contracts only bound *what* is
    scanned, so a project with memory logs / a roadmap carrier can still use
    `authority-check` as a CI gate.
    """

    def test_append_only_memory_logs_and_git_metadata_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            for relative in (
                ".workbuddy/memory/2026-11-04.md",
                ".git/notes.md",
            ):
                write_file(root, relative, f"- Evidence: {target}\n")

            result = run_authority_check(root)

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Authority boundary: clean.", result.stdout)

    def test_roadmap_carrier_and_render_view_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            carrier = root / "docs" / "roadmap" / "roadmap.json"
            carrier.parent.mkdir(parents=True)
            run_cli(
                "init",
                carrier,
                "--title",
                "Scope",
                "--description",
                f"编排自 {target}",
                "--md-file",
                "ROADMAP.md",
                cwd=carrier.parent,
            )
            run_cli("render", carrier, cwd=carrier.parent)
            view = carrier.parent / "ROADMAP.md"
            self.assertIn(AUTHORITY_ENVELOPE, view.read_text(encoding="utf-8"))
            with view.open("a", encoding="utf-8") as handle:
                handle.write(f"\nEvidence: {target}\n")

            result = run_authority_check(root)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_a_generic_nodes_json_is_still_a_durable_source(self):
        """The carrier signature must be narrow, not a blanket `.json` bypass."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            write_file(
                root,
                "docs/architecture/graph.json",
                '{"nodes": {}, "title": "Graph"}\n'
                f'{{"evidence": "{target}"}}\n',
            )

            result = run_authority_check(root)

            self.assertEqual(1, result.returncode)
            self.assertIn("docs/architecture/graph.json:2", result.stderr)

    def test_process_state_files_do_not_mask_a_real_durable_leak(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            write_file(root, ".workbuddy/memory/2026-11-05.md", f"- Evidence: {target}\n")
            carrier = root / "docs" / "roadmap" / "roadmap.json"
            carrier.parent.mkdir(parents=True)
            run_cli(
                "init",
                carrier,
                "--title",
                "Scope",
                "--description",
                f"编排自 {target}",
                "--md-file",
                "ROADMAP.md",
                cwd=root,
            )
            write_file(root, "docs/architecture/release.md", f"Evidence: {target}\n")

            result = run_authority_check(root)

            self.assertEqual(1, result.returncode)
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn("docs/architecture/release.md:1", result.stderr)
            self.assertNotIn("docs/roadmap/roadmap.json", result.stderr)
            self.assertNotIn(".workbuddy/memory", result.stderr)

    def test_exclude_covers_only_declared_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            write_file(root, "docs/architecture/release.md", f"Evidence: {target}\n")
            write_file(root, "docs/generated/notes.md", f"Evidence: {target}\n")

            excluded = run_authority_check(root, "--exclude", "docs/generated")

            self.assertEqual(1, excluded.returncode, excluded.stderr)
            self.assertIn("docs/architecture/release.md:1", excluded.stderr)
            self.assertNotIn("docs/generated/notes.md", excluded.stderr)

            unexcluded = run_authority_check(root)

            self.assertEqual(1, unexcluded.returncode)
            self.assertIn("docs/generated/notes.md:1", unexcluded.stderr)

    def test_exclude_is_repeatable_for_files_and_directories(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            write_file(root, "docs/generated/notes.md", f"Evidence: {target}\n")
            write_file(root, "vendor/cache/notes.md", f"Evidence: {target}\n")

            result = run_authority_check(
                root,
                "--exclude",
                "docs/generated/notes.md",
                "--exclude",
                "vendor/cache",
            )

            self.assertEqual(0, result.returncode, result.stderr)

    def test_exclude_cannot_disable_the_entire_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for candidate in (".", "..", "/"):
                with self.subTest(exclude=candidate):
                    result = run_authority_check(root, "--exclude", candidate)
                    self.assertEqual(1, result.returncode, result.stdout)
                    self.assertIn("E_USAGE", result.stderr)

    def test_single_and_sqlite_carriers_stay_out_of_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            for name, init_args in (
                ("single.json", ()),
                ("sqlite.db", ("--storage", "sqlite")),
            ):
                carrier_dir = root / name.replace(".", "-")
                carrier_dir.mkdir()
                carrier = carrier_dir / name
                run_cli(
                    "init",
                    carrier,
                    "--title",
                    "Scope",
                    "--description",
                    f"编排自 {target}",
                    "--md-file",
                    "ROADMAP.md",
                    *init_args,
                    cwd=carrier_dir,
                )
                run_cli("render", carrier, cwd=carrier_dir)
                with self.subTest(carrier=name):
                    self.assertIn(
                        AUTHORITY_ENVELOPE,
                        (carrier_dir / "ROADMAP.md").read_text(encoding="utf-8"),
                    )

            result = run_authority_check(root)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_governance_allowance_still_line_local_with_process_state_present(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = seed_process_plan(root)
            write_file(
                root,
                "docs/architecture/layers.md",
                f"Forbidden example: {target}. "
                "<!-- roadmap-authority-allow: governance-example -->\n"
                f"Real leak: {target}\n",
            )
            write_file(root, ".workbuddy/memory/2026-11-05.md", f"- {target}\n")

            result = run_authority_check(root)

            self.assertEqual(1, result.returncode)
            self.assertIn("docs/architecture/layers.md:2", result.stderr)
            self.assertNotIn("docs/architecture/layers.md:1", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

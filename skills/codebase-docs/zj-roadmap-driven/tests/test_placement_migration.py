from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"


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


class PlacementMigrationTest(unittest.TestCase):
    def test_migration_writes_primary_placements_without_rewriting_source(self):
        for storage, source_name, target_name in (
            ("single", "source.json", "target.json"),
            ("sqlite", "source.sqlite", "target.sqlite"),
        ):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                source = tmpdir / source_name
                target = tmpdir / target_name
                init_args = ["init", source, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                first = json.loads(
                    run_cli("add", source, "1", "First work", cwd=tmpdir).stdout
                )
                second = json.loads(
                    run_cli("add", source, "1", "Second work", cwd=tmpdir).stdout
                )
                run_cli("edge", "add", source, "1-1", "1-2", "--type", "blocks", cwd=tmpdir)
                source_bytes = source.read_bytes()

                report = json.loads(
                    run_cli(
                        "migrate-placements",
                        source,
                        "--output",
                        target,
                        cwd=tmpdir,
                    ).stdout
                )
                placements = json.loads(
                    run_cli("placement", "list", target, cwd=tmpdir).stdout
                )["placements"]

                self.assertEqual(source_bytes, source.read_bytes())
                self.assertEqual(report["placements"], 2)
                self.assertEqual(
                    [(p["work_id"], p["parent_id"], p["kind"], p["outline_rank"])
                     for p in placements],
                    [("1-1", "1", "primary", 0), ("1-2", "1", "primary", 1)],
                )
                self.assertEqual(placements[0]["work_uid"], first["uid"])
                self.assertEqual(placements[1]["work_uid"], second["uid"])
                self.assertEqual(
                    json.loads(run_cli("edge", "list", target, cwd=tmpdir).stdout),
                    json.loads(run_cli("edge", "list", source, cwd=tmpdir).stdout),
                )

    def test_nested_order_is_projected_and_sqlite_to_json_uses_output_carrier(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            source = tmpdir / "source.sqlite"
            target = tmpdir / "target.json"
            run_cli("init", source, "--title", "Roadmap", "--storage", "sqlite", cwd=tmpdir)
            first = json.loads(run_cli("add", source, "1", "First", cwd=tmpdir).stdout)
            nested = json.loads(run_cli("add", source, "1-1", "Nested", cwd=tmpdir).stdout)
            second = json.loads(run_cli("add", source, "1", "Second", cwd=tmpdir).stdout)

            report = json.loads(
                run_cli("migrate-placements", source, "--output", target, cwd=tmpdir).stdout
            )
            placements = json.loads(
                run_cli("placement", "list", target, cwd=tmpdir).stdout
            )["placements"]

            self.assertEqual(report["target_storage"], "single")
            self.assertEqual(
                [(p["work_uid"], p["parent_id"], p["outline_rank"]) for p in placements],
                [
                    (first["uid"], "1", 0),
                    (nested["uid"], "1-1", 0),
                    (second["uid"], "1", 1),
                ],
            )

    def test_migration_refuses_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            source = tmpdir / "source.json"
            target = tmpdir / "target.sqlite"
            run_cli("init", source, "--title", "Roadmap", cwd=tmpdir)
            target.write_text("keep me", encoding="utf-8")

            result = run_cli(
                "migrate-placements", source, "--output", target, cwd=tmpdir, check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_reference_placement_can_move_without_copying_work_state(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            roadmap = tmpdir / "roadmap.json"
            run_cli("init", roadmap, "--title", "Roadmap", cwd=tmpdir)
            work = json.loads(run_cli("add", roadmap, "1", "Shared work", cwd=tmpdir).stdout)
            context = json.loads(run_cli("add", roadmap, "1", "Second context", cwd=tmpdir).stdout)
            run_cli("update", roadmap, work["id"], "--status", "in_progress", cwd=tmpdir)

            reference = json.loads(run_cli(
                "placement", "add-reference", roadmap, work["uid"], context["uid"],
                "--rank", "0", cwd=tmpdir,
            ).stdout)
            moved = json.loads(run_cli(
                "placement", "move", roadmap, reference["id"], "1", "--rank", "1", cwd=tmpdir,
            ).stdout)
            placements = json.loads(run_cli("placement", "list", roadmap, cwd=tmpdir).stdout)["placements"]
            stored_work = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)

            self.assertEqual(reference["kind"], "reference")
            self.assertEqual(moved["kind"], "reference")
            self.assertEqual(moved["work_uid"], work["uid"])
            self.assertEqual(moved["parent_id"], "1")
            self.assertEqual(moved["outline_rank"], 1)
            self.assertEqual(stored_work["status"], "in_progress")
            self.assertEqual(len([p for p in placements if p["work_uid"] == work["uid"]]), 2)


if __name__ == "__main__":
    unittest.main()

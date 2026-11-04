from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"


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


class TypeMigrationTest(unittest.TestCase):
    def test_migrate_types_preserves_uids_edges_status_and_classifies_nodes(self):
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
                group = json.loads(run_cli("add", source, "1", "Group", cwd=tmpdir).stdout)
                work = json.loads(run_cli("add", source, group["id"], "Leaf", cwd=tmpdir).stdout)
                run_cli("update", source, work["id"], "--status", "in_progress", cwd=tmpdir)
                run_cli("edge", "add", source, group["id"], work["id"], "--type", "blocks", cwd=tmpdir)
                source_bytes = source.read_bytes()

                report = json.loads(run_cli(
                    "migrate-types", source, "--output", target, cwd=tmpdir,
                ).stdout)
                stored_group = json.loads(run_cli("get", target, group["uid"], cwd=tmpdir).stdout)
                stored_work = json.loads(run_cli("get", target, work["uid"], cwd=tmpdir).stdout)

                self.assertEqual(source_bytes, source.read_bytes())
                self.assertEqual(report["typed_plan_nodes"], 3)
                self.assertEqual(stored_group["node_type"], "group")
                self.assertEqual(stored_work["node_type"], "work")
                self.assertEqual(stored_work["status"], "in_progress")
                self.assertEqual(
                    json.loads(run_cli("edge", "list", source, cwd=tmpdir).stdout),
                    json.loads(run_cli("edge", "list", target, cwd=tmpdir).stdout),
                )
                self.assertEqual(run_cli("validate", target, cwd=tmpdir).stdout.strip(), "Valid.")


if __name__ == "__main__":
    unittest.main()

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

                radial = run_cli("tree", target, "--anchor", shared["uid"], cwd=tmpdir).stdout
                self.assertIn("Context", radial)
                self.assertIn("↪ reference: Shared work", radial)
                self.assertEqual(radial.count("Shared work"), 2)


if __name__ == "__main__":
    unittest.main()

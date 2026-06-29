import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
CLI = SKILL_DIR / "roadmap_cli.py"


class RoadmapCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.roadmap = self.workdir / "roadmap.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=self.workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"roadmap_cli failed with {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def test_concurrent_add_commands_keep_json_valid_and_all_nodes(self):
        self.run_cli("init", self.roadmap, "--title", "Concurrent roadmap")

        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(CLI),
                    "add",
                    str(self.roadmap),
                    "1",
                    f"Concurrent child {i}",
                ],
                cwd=self.workdir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for i in range(12)
        ]

        failures = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            if process.returncode != 0:
                failures.append((process.returncode, stdout, stderr))

        self.assertEqual([], failures)
        self.run_cli("validate", self.roadmap)

        data = json.loads(self.roadmap.read_text(encoding="utf-8"))
        children = data["nodes"]["1"]["children"]
        self.assertEqual(12, len(children))
        self.assertEqual(13, len(data["nodes"]))

    def test_unlock_removes_stale_lock_so_writes_can_resume(self):
        self.run_cli("init", self.roadmap, "--title", "Unlock roadmap")
        lock_dir = Path(str(self.roadmap) + ".lock")
        lock_dir.mkdir()
        (lock_dir / "owner.json").write_text(
            '{"pid": 123, "created_at": "2026-06-29 00:00:00"}',
            encoding="utf-8",
        )

        locked = self.run_cli("add", self.roadmap, "1", "Blocked child", check=False)
        self.assertEqual(2, locked.returncode)
        self.assertIn("Roadmap file is locked", locked.stderr)
        self.assertIn(str(lock_dir), locked.stderr)
        self.assertIn("unlock", locked.stderr)

        self.run_cli("unlock", self.roadmap)
        self.assertFalse(lock_dir.exists())
        self.run_cli("add", self.roadmap, "1", "Resumed child")
        self.run_cli("validate", self.roadmap)

    def test_light_render_shows_bounded_focus_subtree(self):
        md_file = self.workdir / "roadmap.md"
        self.run_cli("init", self.roadmap, "--title", "Focus roadmap", "--md-file", md_file)
        self.run_cli("add", self.roadmap, "1", "Implementation focus", "--status", "in_progress")
        self.run_cli("update", self.roadmap, "1-1", "--notes", "Build the next slice.")
        self.run_cli("decide", self.roadmap, "1-1", "How deep?", "One level in light render")
        self.run_cli("add", self.roadmap, "1-1", "Visible child")
        self.run_cli("add", self.roadmap, "1-1-1", "Hidden grandchild")
        self.run_cli("add", self.roadmap, "1-1-1", "Second hidden grandchild")

        self.run_cli("render", self.roadmap)
        rendered = md_file.read_text(encoding="utf-8")

        self.assertIn("### 当前施工：1-1. Implementation focus", rendered)
        self.assertIn("Build the next slice.", rendered)
        self.assertIn("Q: How deep?", rendered)
        self.assertIn("[ ][X+] 1-1-1. Visible child", rendered)
        self.assertNotIn("[ ][X+] 1-1-1-1. Hidden grandchild", rendered)
        self.assertIn("... 2 more child nodes; run tree 1-1-1 --depth 2 for full view", rendered)


if __name__ == "__main__":
    unittest.main()

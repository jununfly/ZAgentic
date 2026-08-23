import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
CLI = SKILL_DIR / "roadmap_cli.py"


class StorageAdvisorCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.single = self.workdir / "roadmap.json"
        self.bundle = self.workdir / "roadmap.bundle"

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

    @staticmethod
    def file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        for child in sorted(path.rglob("*")) if path.is_dir() else [path]:
            if child.is_file():
                digest.update(str(child.relative_to(path) if path.is_dir() else child.name).encode())
                digest.update(child.read_bytes())
        return digest.hexdigest()

    def write_single_with_children(self, node_count: int):
        nodes = {
            "1": {
                "id": "1",
                "label": "Generated roadmap",
                "status": "in_progress",
                "mode": "explore",
                "parent": None,
                "children": [f"1-{index}" for index in range(1, node_count)],
                "decisions": [],
                "notes": "",
            }
        }
        for index in range(1, node_count):
            nodes[f"1-{index}"] = {
                "id": f"1-{index}",
                "label": f"Branch {index}",
                "status": "pending",
                "mode": "explore",
                "parent": "1",
                "children": [],
                "decisions": [],
                "notes": "",
            }
        self.single.write_text(
            json.dumps(
                {
                    "title": "Generated roadmap",
                    "description": "",
                    "version": 1,
                    "nodes": nodes,
                    "metadata": {"created": "2026-08-23 00:00:00", "updated": "2026-08-23 00:00:00", "md_file": ""},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def test_small_single_is_keep_and_read_only(self):
        self.run_cli("init", self.single, "--title", "Small roadmap")
        self.run_cli("add", self.single, "1", "One branch")
        self.run_cli("decide", self.single, "1", "Keep JSON?", "Yes")
        before = self.file_digest(self.single)
        before_mtime = self.single.stat().st_mtime_ns

        result = json.loads(self.run_cli("recommend-storage", self.single).stdout)

        self.assertEqual("zj-roadmap-storage-recommendation/v1", result["schema"])
        self.assertEqual("single", result["storage"])
        self.assertTrue(result["read_only"])
        self.assertEqual("keep-single", result["recommendation"]["action"])
        self.assertEqual(2, result["metrics"]["total_nodes"])
        self.assertEqual(1, result["metrics"]["total_decisions"])
        self.assertEqual({}, result["measurements_ms"])
        self.assertEqual(before, self.file_digest(self.single))
        self.assertEqual(before_mtime, self.single.stat().st_mtime_ns)

    def test_large_single_recommends_bundle(self):
        self.write_single_with_children(5000)
        before = self.file_digest(self.single)

        result = json.loads(self.run_cli("recommend-storage", self.single).stdout)

        self.assertEqual("recommend-bundle", result["recommendation"]["action"])
        self.assertGreaterEqual(result["metrics"]["total_nodes"], 5000)
        self.assertTrue(result["signals"]["recommend_bundle"])
        self.assertEqual(before, self.file_digest(self.single))

    def test_medium_single_suggests_consider_bundle(self):
        self.write_single_with_children(1000)

        result = json.loads(self.run_cli("recommend-storage", self.single).stdout)

        self.assertEqual("consider-bundle", result["recommendation"]["action"])
        self.assertEqual(1000, result["metrics"]["total_nodes"])
        self.assertEqual("total_nodes", result["signals"]["consider_bundle"][0]["metric"])

    def test_bundle_is_keep_bundle_and_measurement_is_read_only(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Bundle roadmap")
        self.run_cli("add", self.bundle, "1", "One branch")
        before = self.file_digest(self.bundle)

        result = json.loads(self.run_cli("recommend-storage", self.bundle, "--measure").stdout)

        self.assertEqual("bundle", result["storage"])
        self.assertEqual("keep-bundle", result["recommendation"]["action"])
        self.assertIn("bounded_tree_ms", result["measurements_ms"])
        self.assertIn("full_section_ms", result["measurements_ms"])
        self.assertEqual(before, self.file_digest(self.bundle))

    def test_missing_bundle_index_is_not_rebuilt(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Indexless bundle")
        stats_path = self.bundle / "indexes/stats.json"
        stats_path.unlink()

        result = json.loads(self.run_cli("recommend-storage", self.bundle).stdout)

        self.assertEqual("bundle", result["storage"])
        self.assertEqual("keep-bundle", result["recommendation"]["action"])
        self.assertFalse(stats_path.exists())


if __name__ == "__main__":
    unittest.main()

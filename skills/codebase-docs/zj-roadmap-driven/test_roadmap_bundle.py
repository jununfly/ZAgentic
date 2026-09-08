import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

from roadmap_bundle import RoadmapBundle
from roadmap import RoadmapLockTimeout, roadmap_file_lock, unlock_roadmap


class RoadmapBundleCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.legacy = self.workdir / "roadmap.json"
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

    def make_legacy(self):
        self.run_cli("init", self.legacy, "--title", "Bundle roadmap")
        self.run_cli("add", self.legacy, "1", "First branch", "--status", "in_progress")
        self.run_cli("add", self.legacy, "1-1", "Deep branch")
        self.run_cli("add", self.legacy, "1-1-1", "Deep leaf")
        self.run_cli("decide", self.legacy, "1-1", "Use bundle?", "Yes", "large roadmap")

    def test_migrate_keeps_source_and_supports_bounded_cli(self):
        self.make_legacy()
        source_bytes = self.legacy.read_bytes()

        migrated = self.run_cli("migrate", self.legacy, "--to", "bundle", "--output", self.bundle)
        self.assertIn("Migrated:", migrated.stdout)
        self.assertEqual(source_bytes, self.legacy.read_bytes())
        self.assertTrue((self.bundle / "manifest.json").is_file())
        self.assertTrue((self.bundle / "nodes/1-1.json").is_file())
        self.assertTrue((self.bundle / "decisions/1-1.json").is_file())
        self.assertTrue((self.bundle / "history/events.jsonl").is_file())

        self.run_cli("validate", self.bundle)
        tree = self.run_cli("tree", self.bundle).stdout
        self.assertIn("1-1. Deep branch", tree)
        self.assertNotIn("1-1-1-1. Deep leaf", tree)
        bounded = self.run_cli("section", self.bundle).stdout
        self.assertNotIn("1-1-1-1. Deep leaf", bounded)
        full = self.run_cli("section", self.bundle, "--all").stdout
        self.assertIn("1-1-1-1. Deep leaf", full)
        limited = self.run_cli("section", self.bundle, "--all", "--max-bytes", "80").stdout
        self.assertIn("View truncated", limited)

        decisions = json.loads(self.run_cli("decisions", self.bundle, "1-1").stdout)
        self.assertEqual("Use bundle?", decisions[0]["q"])

        self.run_cli("remove-decision", self.bundle, "1-1", "--index", "0")
        decisions = json.loads(self.run_cli("decisions", self.bundle, "1-1").stdout)
        self.assertEqual(2, len(decisions))
        self.assertFalse(decisions[0].get("retracted", False))
        self.assertTrue(decisions[1]["retracted"])
        history = [json.loads(line) for line in (self.bundle / "history/events.jsonl").read_text().splitlines()]
        self.assertEqual("decision-retracted", history[-1]["operation"])
        self.run_cli("validate", self.bundle)

        md_file = self.workdir / "roadmap.md"
        self.run_cli("link", self.bundle, md_file)
        self.run_cli("update", self.bundle, "1-1-1-1", "--status", "in_progress")
        self.run_cli("render", self.bundle)
        self.assertIn("ROADMAP_SECTION_START", md_file.read_text(encoding="utf-8"))
        self.assertIn("1-1-1-1. Deep leaf", self.run_cli("path", self.bundle, "1-1-1-1").stdout)
        self.assertIn('"focus": "1-1-1-1"', self.run_cli("focus", self.bundle).stdout)

    def test_bundle_init_and_mutations_keep_parent_status_consistent(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Fresh bundle")
        self.run_cli("add", self.bundle, "1", "Completed child", "--status", "completed")
        node = json.loads(self.run_cli("get", self.bundle, "1").stdout)
        self.assertEqual("completed", node["status"])

        self.run_cli("add", self.bundle, "1", "Pending child")
        node = json.loads(self.run_cli("get", self.bundle, "1").stdout)
        self.assertEqual("in_progress", node["status"])
        self.run_cli("update", self.bundle, "1-2", "--status", "completed")
        node = json.loads(self.run_cli("get", self.bundle, "1").stdout)
        self.assertEqual("completed", node["status"])

        self.run_cli("delete", self.bundle, "1-1")
        self.run_cli("validate", self.bundle)
        stats = json.loads(self.run_cli("stats", self.bundle).stdout)
        self.assertEqual(2, stats["total_nodes"])

    def test_materialized_snapshots_follow_configured_interval(self):
        self.run_cli(
            "init",
            self.bundle,
            "--storage",
            "bundle",
            "--snapshot-interval",
            "2",
            "--title",
            "Snapshot interval",
        )
        self.run_cli("add", self.bundle, "1", "First")
        manifest = json.loads((self.bundle / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("snapshots/snapshot-000000.json", manifest["currentSnapshot"])
        self.run_cli("add", self.bundle, "1", "Second")
        manifest = json.loads((self.bundle / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("snapshots/snapshot-000002.json", manifest["currentSnapshot"])
        self.run_cli("validate", self.bundle)

    def test_corrupt_or_stale_shard_is_rejected(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Corruption test")
        self.run_cli("add", self.bundle, "1", "Child")
        node_shard = self.bundle / "nodes/1-1.json"
        node_shard.write_text("{not json", encoding="utf-8")
        result = self.run_cli("validate", self.bundle, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("could not read node shard", result.stdout + result.stderr)

        # Recreate, then prove that a stale materialized index is also visible.
        import shutil

        shutil.rmtree(self.bundle, ignore_errors=True)
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Stale stats")
        stats_path = self.bundle / "indexes/stats.json"
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        stats["total_nodes"] = 99
        stats_path.write_text(json.dumps(stats), encoding="utf-8")
        result = self.run_cli("validate", self.bundle, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("materialized stats do not match", result.stdout)

    def test_invalid_migration_does_not_create_output(self):
        self.legacy.write_text('{"nodes": {}}', encoding="utf-8")
        source_bytes = self.legacy.read_bytes()
        result = self.run_cli("migrate", self.legacy, "--to", "bundle", "--output", self.bundle, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.bundle.exists())
        self.assertEqual(source_bytes, self.legacy.read_bytes())

    def test_bounded_tree_reads_only_requested_depth(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Lazy reads")
        for index in range(5):
            self.run_cli("add", self.bundle, "1", f"Branch {index}")
            self.run_cli("add", self.bundle, f"1-{index + 1}", f"Leaf {index}")

        bundle = RoadmapBundle(self.bundle)
        bundle.load()
        original = bundle._read_node_file
        reads = []

        def counted(node_id):
            reads.append(node_id)
            return original(node_id)

        bundle._read_node_file = counted
        output = bundle.get_tree(max_depth=1)
        self.assertIn("1-5. Branch 4", output)
        self.assertNotIn("1-5-1. Leaf 4", output)
        self.assertEqual({"1", "1-1", "1-2", "1-3", "1-4", "1-5"}, set(reads))

    def test_concurrent_bundle_writes_keep_shards_and_history_valid(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Concurrent bundle")
        processes = [
            subprocess.Popen(
                [sys.executable, str(CLI), "add", str(self.bundle), "1", f"Concurrent {index}"],
                cwd=self.workdir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for index in range(8)
        ]
        failures = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            if process.returncode != 0:
                failures.append((process.returncode, stdout, stderr))
        self.assertEqual([], failures)
        self.run_cli("validate", self.bundle)
        stats = json.loads(self.run_cli("stats", self.bundle).stdout)
        self.assertEqual(9, stats["total_nodes"])
        history = (self.bundle / "history/events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(8, len(history))

    def test_bundle_path_uses_the_same_stale_lock_recovery(self):
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", "Lock recovery")
        lock_dir = Path(str(self.bundle) + ".lock")
        lock_dir.mkdir()
        with self.assertRaises(RoadmapLockTimeout):
            with roadmap_file_lock(str(self.bundle), timeout_seconds=0.01):
                pass
        unlock_roadmap(str(self.bundle))
        with roadmap_file_lock(str(self.bundle), timeout_seconds=0.1):
            pass


if __name__ == "__main__":
    unittest.main()

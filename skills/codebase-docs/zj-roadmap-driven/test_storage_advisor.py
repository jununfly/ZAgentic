import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
CLI = SKILL_DIR / "roadmap_cli.py"


class AdvisorCliCase(unittest.TestCase):
    """治具与 helper 的共同底座（不含用例本体）。

    两个具体类各自只放自己那一组用例：如果让 sqlite 组去继承 single
    组，unittest 会把父类的用例在子类里重跑一遍——计数虚高，且看不出哪份是哪
    个 carrier 的（#79 那边直接继承时就踩过同一种虚高）。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.single = self.workdir / "roadmap.json"

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

    def write_single_with_decisions(self, node_count: int, decision_count: int):
        nodes = {
            "1": {
                "id": "1",
                "label": "Decision-heavy roadmap",
                "status": "in_progress",
                "mode": "explore",
                "parent": None,
                "children": [f"1-{index}" for index in range(1, node_count)],
                "decisions": [
                    {"q": f"Question {index}", "answer": "Keep evaluating", "note": "x" * 500}
                    for index in range(decision_count)
                ],
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
                    "title": "Decision-heavy roadmap",
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

    def write_single_with_bytes(self, target_bytes: int):
        """造一份 canonical 体积够大的单文件 roadmap。

        用 `notes` 撑体积而不是堆节点：advisor 要抓的是"每次命令都要 load 整图"
        （§5 第 3 条读放大），体积本身就是信号；堆两万个节点只为把字节凑够既慢，
        又把无关的树遍历成本掺进了 measurements。
        """
        notes = "x" * target_bytes
        self.single.write_text(
            json.dumps(
                {
                    "title": "Heavy roadmap",
                    "description": "",
                    "version": 1,
                    "nodes": {
                        "1": {
                            "id": "1",
                            "label": "Heavy roadmap",
                            "status": "in_progress",
                            "mode": "explore",
                            "parent": None,
                            "children": ["1-1"],
                            "decisions": [],
                            "notes": notes,
                        },
                        "1-1": {
                            "id": "1-1",
                            "label": "Branch",
                            "status": "pending",
                            "mode": "explore",
                            "parent": "1",
                            "children": [],
                            "decisions": [],
                            "notes": "",
                        },
                    },
                    "metadata": {"created": "2026-08-23 00:00:00", "updated": "2026-08-23 00:00:00", "md_file": ""},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


class StorageAdvisorCliTest(AdvisorCliCase):
    """single / sqlite 两档。"""

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

    def test_medium_single_stays_single_below_sqlite_threshold(self):
        # 1000/5000 节点都还不到 sqlite 阈值（2万），仍是 keep-single。
        self.write_single_with_children(5000)
        before = self.file_digest(self.single)

        result = json.loads(self.run_cli("recommend-storage", self.single).stdout)

        self.assertEqual("keep-single", result["recommendation"]["action"])
        self.assertGreaterEqual(result["metrics"]["total_nodes"], 5000)
        self.assertEqual([], result["signals"]["consider_sqlite"])
        self.assertEqual(before, self.file_digest(self.single))

    def test_two_moderate_structural_signals_stay_single_without_measurement(self):
        self.write_single_with_decisions(23, 694)

        result = json.loads(self.run_cli("recommend-storage", self.single).stdout)

        self.assertEqual("keep-single", result["recommendation"]["action"])
        self.assertEqual([], result["signals"]["consider_sqlite"])

    def test_non_execution_registry_json_is_rejected(self):
        self.single.write_text(
            json.dumps({"schema": "global-initiative-roadmap/v1", "initiatives": []}),
            encoding="utf-8",
        )

        result = self.run_cli("recommend-storage", self.single, check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("not a valid execution roadmap", result.stderr)

if __name__ == "__main__":
    unittest.main()

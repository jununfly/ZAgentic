#!/usr/bin/env python3
"""Verify roadmap bundle behavior against a real Markdown planning corpus.

The input corpus is intentionally not imported as Markdown. This contract builds
an equivalent temporary legacy JSON fixture from the corpus, migrates that JSON
through the public CLI, and proves that the source Markdown remains read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

from roadmap_bundle import RoadmapBundle  # noqa: E402


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CLI), *[str(arg) for arg in args]],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({completed.returncode})\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def build_legacy_fixture(plans_dir: Path, view_path: Path) -> tuple[dict[str, Any], list[Path]]:
    files = sorted(path for path in plans_dir.rglob("*.md") if path.is_file())
    if not files:
        raise AssertionError(f"no Markdown planning files found under {plans_dir}")
    relative_parents = sorted({path.parent.relative_to(plans_dir).as_posix() for path in files})
    if len(relative_parents) != 1:
        raise AssertionError(f"expected one planning cohort, found {relative_parents}")

    cohort_id = "1-1"
    cohort_label = relative_parents[0]
    nodes: dict[str, dict[str, Any]] = {
        "1": {
            "id": "1",
            "label": f"{plans_dir.name} real planning corpus",
            "status": "in_progress",
            "mode": "explore",
            "parent": None,
            "children": [cohort_id],
            "decisions": [],
            "notes": "Temporary verification fixture; source Markdown remains external and read-only.",
        },
        cohort_id: {
            "id": cohort_id,
            "label": cohort_label,
            "status": "in_progress",
            "mode": "exploit",
            "parent": "1",
            "children": [],
            "decisions": [],
            "notes": "One node per real planning document follows.",
        },
    }

    for index, path in enumerate(files, start=1):
        node_id = f"{cohort_id}-{index}"
        relative = path.relative_to(plans_dir).as_posix()
        content = path.read_text(encoding="utf-8")
        nodes[cohort_id]["children"].append(node_id)
        nodes[node_id] = {
            "id": node_id,
            "label": heading(path),
            "status": "pending",
            "mode": "exploit",
            "parent": cohort_id,
            "children": [],
            "decisions": [{"q": "Source document", "answer": relative, "note": "real-plan corpus"}],
            "notes": content,
        }

    return {
        "title": "Real plan corpus verification",
        "description": "Temporary fixture derived from a real Markdown planning corpus",
        "version": 1,
        "nodes": nodes,
        "metadata": {"md_file": str(view_path.resolve())},
    }, files


def verify(plans_dir: Path) -> dict[str, Any]:
    plans_dir = plans_dir.expanduser().resolve()
    before_hash = sha256_tree(plans_dir)
    with tempfile.TemporaryDirectory(prefix="zj-roadmap-real-case-") as temporary:
        workspace = Path(temporary)
        source = workspace / "real-plans.json"
        bundle = workspace / "real-plans.bundle"
        view = workspace / "real-plans.md"
        data, files = build_legacy_fixture(plans_dir, view)
        source.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        source_before = source.read_bytes()
        source_hash = sha256_tree(workspace)

        run_cli("migrate", source, "--to", "bundle", "--output", bundle, "--snapshot-interval", "3", cwd=workspace)
        run_cli("validate", bundle, cwd=workspace)
        stats = json.loads(run_cli("stats", bundle, cwd=workspace).stdout)
        expected_nodes = len(files) + 2
        if stats["total_nodes"] != expected_nodes or stats["total_decisions"] != len(files):
            raise AssertionError(f"unexpected migrated stats: {stats}")

        bounded_bundle = RoadmapBundle(bundle)
        bounded_bundle.load()
        original_read = bounded_bundle._read_node_file
        reads: list[str] = []

        def counted_read(node_id: str) -> dict[str, Any]:
            reads.append(node_id)
            return original_read(node_id)

        bounded_bundle._read_node_file = counted_read  # type: ignore[method-assign]
        bounded_bundle.get_tree(max_depth=1)
        if reads != ["1", "1-1"]:
            raise AssertionError(f"depth-bounded tree read unexpected shards: {reads}")

        target_id = "1-1-1"
        target = json.loads(run_cli("get", bundle, target_id, cwd=workspace).stdout)
        source_content = files[0].read_text(encoding="utf-8")
        if target["notes"] != source_content:
            raise AssertionError("migrated node shard did not preserve source document content")

        tree = run_cli("tree", bundle, "--depth", "1", cwd=workspace).stdout
        if "1-1." not in tree or target["label"] in tree:
            raise AssertionError("bounded tree exposed document nodes")
        bounded_section = run_cli("section", bundle, "--max-depth", "1", cwd=workspace).stdout
        if target["label"] in bounded_section:
            raise AssertionError("bounded section exposed document nodes")
        full_section = run_cli("section", bundle, "--all", cwd=workspace).stdout
        if target["label"] not in full_section:
            raise AssertionError("full section omitted migrated document node")

        run_cli("link", bundle, view, cwd=workspace)
        run_cli("render", bundle, cwd=workspace)
        if "ROADMAP_SECTION_START" not in view.read_text(encoding="utf-8"):
            raise AssertionError("bundle render did not write the linked Markdown view")

        imported = run_cli("import", source, view, cwd=workspace, check=False)
        if imported.returncode == 0 or "Unknown command" not in imported.stdout:
            raise AssertionError("legacy Markdown import unexpectedly remains supported")
        if source.read_bytes() != source_before or sha256_tree(plans_dir) != before_hash:
            raise AssertionError("migration or rendering modified a source corpus")
        if sha256_tree(workspace) == source_hash:
            raise AssertionError("verification fixture did not produce migration artifacts")

        return {
            "plans_dir": str(plans_dir),
            "markdown_files": len(files),
            "source_bytes": sum(path.stat().st_size for path in files),
            "migrated_nodes": stats["total_nodes"],
            "migrated_decisions": stats["total_decisions"],
            "source_unchanged": True,
            "markdown_import": "rejected",
            "bounded_depth_1_reads": reads,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.plans_dir)
    print("roadmap real plan corpus contract passed")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the Repository Map artifact and bounded-view contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repository_map.py"


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed


def git(repo: Path, *args: str) -> None:
    run(["git", "-C", str(repo), *args])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="repository-map-contract-") as directory:
        root = Path(directory) / "fixture"
        root.mkdir()
        (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (root / "package.json").write_text('{"name":"fixture-package","version":"1.0.0"}\n', encoding="utf-8")
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "test.yml").write_text("name: test\n", encoding="utf-8")
        (root / "integrations").mkdir()
        (root / "integrations" / "remote.md").write_text("adapter\n", encoding="utf-8")
        git(root, "init", "-q")
        git(root, "config", "user.email", "repository-map@example.test")
        git(root, "config", "user.name", "Repository Map")
        git(root, "add", ".")
        git(root, "commit", "-qm", "fixture")
        bundle = root / "map-bundle"
        run([sys.executable, str(SCRIPT), "scan", str(root), str(bundle)])
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema"] != "zj-repository-map-manifest/v1" or manifest["immutable"] is not True:
            raise AssertionError("manifest contract failed")
        if manifest["source"]["state"] != "clean" or not manifest["source"]["commit"]:
            raise AssertionError("clean commit source was not recorded")
        tree = (bundle / "facts" / "tree.jsonl").read_text(encoding="utf-8")
        if "map-bundle" in tree:
            raise AssertionError("output bundle was not excluded")
        targets = json.loads((bundle / "navigation" / "targets.json").read_text(encoding="utf-8"))["targets"]
        kinds = {item["kind"] for item in targets}
        if not {"package", "workflow", "integration", "top-level"}.issubset(kinds):
            raise AssertionError(f"navigation targets incomplete: {kinds}")
        run([sys.executable, str(SCRIPT), "validate", str(bundle)])
        bounded = run([sys.executable, str(SCRIPT), "view", str(bundle), "--section", "targets", "--limit", "1"])
        target_section = bounded.stdout.split("## Navigation targets\n\n", 1)[1].split("\n## Unknowns", 1)[0]
        if target_section.count("- `") > 1:
            raise AssertionError("bounded target view exceeded its limit")
        duplicate = run([sys.executable, str(SCRIPT), "scan", str(root), str(bundle)], check=False)
        if duplicate.returncode == 0 or "immutable" not in duplicate.stderr:
            raise AssertionError("existing bundle was overwritten")
        (root / "src" / "main.py").write_text("print('changed')\n", encoding="utf-8")
        dirty_bundle = root / "dirty-map-bundle"
        run([sys.executable, str(SCRIPT), "scan", str(root), str(dirty_bundle)])
        dirty_manifest = json.loads((dirty_bundle / "manifest.json").read_text(encoding="utf-8"))
        if dirty_manifest["source"]["state"] != "dirty" or dirty_manifest["source"]["workingTreeFingerprint"] == manifest["source"]["workingTreeFingerprint"]:
            raise AssertionError("dirty working-tree fingerprint was not distinguished")
    print("repository map contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

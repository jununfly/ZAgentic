#!/usr/bin/env python3
"""Verify Architecture Study binding, record kinds, and evidence gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_SCRIPT = ROOT / "scripts" / "repository_map.py"
STUDY_SCRIPT = ROOT / "scripts" / "architecture_study.py"


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed


def git(repo: Path, *args: str) -> None:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(["git", "-C", str(repo), *args], env=environment, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="architecture-study-contract-") as directory:
        temporary = Path(directory)
        repository = temporary / "fixture"
        repository.mkdir()
        (repository / "src").mkdir()
        (repository / "src" / "main.py").write_text(
            "from helpers import run\n\nclass Worker:\n    def run(self):\n        return subprocess.run(['echo', 'ok'])\n\nif __name__ == '__main__':\n    Worker().run()\n",
            encoding="utf-8",
        )
        (repository / "src" / "helpers.py").write_text("def run(value):\n    return value\n", encoding="utf-8")
        (repository / "package.json").write_text('{"name":"study-fixture"}\n', encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "config", "user.email", "architecture-study@example.test")
        git(repository, "config", "user.name", "Architecture Study")
        git(repository, "add", ".")
        git(repository, "commit", "-qm", "fixture")
        map_bundle = temporary / "map"
        run([sys.executable, str(MAP_SCRIPT), "scan", str(repository), str(map_bundle)])
        map_targets = json.loads((map_bundle / "navigation" / "targets.json").read_text(encoding="utf-8"))["targets"]
        src_target = next(item for item in map_targets if item["path"] == "src")
        study_bundle = temporary / "study"
        run([
            sys.executable,
            str(STUDY_SCRIPT),
            "study",
            str(repository),
            str(study_bundle),
            "--map",
            str(map_bundle),
            "--target",
            src_target["id"],
        ])
        manifest = json.loads((study_bundle / "manifest.json").read_text(encoding="utf-8"))
        scope = json.loads((study_bundle / "facts" / "scope.json").read_text(encoding="utf-8"))
        map_manifest = json.loads((map_bundle / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema"] != "zj-architecture-study-manifest/v1" or manifest["mapBinding"]["snapshotId"] != map_manifest["snapshotId"]:
            raise AssertionError("map binding was not copied into the study manifest")
        evidence = load_jsonl(study_bundle / "facts" / "evidence.jsonl")
        claims = load_jsonl(study_bundle / "facts" / "claims.jsonl")
        unknowns = load_jsonl(study_bundle / "facts" / "unknowns.jsonl")
        risks = load_jsonl(study_bundle / "facts" / "risks.jsonl")
        decisions = scope["decisions"]
        kinds = {item["kind"] for item in evidence + claims + unknowns + risks + decisions}
        if not {"observed", "inferred", "unknown"}.issubset(kinds):
            raise AssertionError(f"map-bound study record kinds incomplete: {kinds}")
        evidence_ids = {item["id"] for item in evidence}
        for claim in claims:
            if claim.get("critical") is True and not set(claim.get("evidenceIds", [])).issubset(evidence_ids):
                raise AssertionError("critical claim has an invalid evidence link")
        run([sys.executable, str(STUDY_SCRIPT), "validate", str(study_bundle)])
        viewed = run([sys.executable, str(STUDY_SCRIPT), "view", str(study_bundle), "--section", "claims", "--limit", "1"])
        if viewed.stdout.count("\n- ") > 1:
            raise AssertionError("bounded study view exceeded its limit")
        direct_bundle = temporary / "direct-study"
        run([sys.executable, str(STUDY_SCRIPT), "study", str(repository), str(direct_bundle), "--target", "src"])
        direct_scope = json.loads((direct_bundle / "facts" / "scope.json").read_text(encoding="utf-8"))
        if direct_scope["mapBinding"]["used"] is not False or not any(item["decision"] == "direct-study-without-map" for item in direct_scope["decisions"]):
            raise AssertionError("direct study did not record the missing-map decision")
        run([sys.executable, str(STUDY_SCRIPT), "validate", str(direct_bundle)])
        (repository / "src" / "helpers.py").write_text("def run(value):\n    return value + 1\n", encoding="utf-8")
        stale = run([
            sys.executable,
            str(STUDY_SCRIPT),
            "study",
            str(repository),
            str(temporary / "stale-study"),
            "--map",
            str(map_bundle),
            "--target",
            src_target["id"],
        ], check=False)
        if stale.returncode == 0 or "no longer matches" not in stale.stderr:
            raise AssertionError("study accepted a stale map binding")
    print("architecture study contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

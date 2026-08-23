#!/usr/bin/env python3
"""Verify code-research hard gates, controlled fixtures, and calibration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_SCRIPT = ROOT / "scripts" / "repository_map.py"
STUDY_SCRIPT = ROOT / "scripts" / "architecture_study.py"
QUALITY_SCRIPT = ROOT / "scripts" / "code_research_quality.py"
ASSETS = ROOT.parents[2] / "research" / "evaluation" / "code-research-quality-v1"


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed


def git(repository: Path, *args: str) -> None:
    run(["git", "-C", str(repository), *args])


def materialize(case_id: str, root: Path, output_name: str | None = None) -> Path:
    source = ASSETS / "fixtures" / case_id
    repository = root / (output_name or case_id)
    shutil.copytree(source, repository)
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "code-research-quality@example.test")
    git(repository, "config", "user.name", "Code Research Quality")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", f"fixture {case_id}")
    return repository


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(bundle: Path, case_id: str, output: Path, map_bundle: Path | None = None) -> dict[str, object]:
    command = [
        sys.executable,
        str(QUALITY_SCRIPT),
        "evaluate",
        str(bundle),
        "--case",
        case_id,
        "--assets",
        str(ASSETS),
        "--output",
        str(output),
    ]
    if map_bundle is not None:
        command.extend(["--map", str(map_bundle)])
    run(command)
    return read_json(output)


def main() -> int:
    run([sys.executable, str(QUALITY_SCRIPT), "validate-assets", str(ASSETS)])
    calibration = run([sys.executable, str(QUALITY_SCRIPT), "calibrate", str(ASSETS)])
    result = json.loads(calibration.stdout)
    if result != {
        "schema": "zj-code-research-calibration-result/v1",
        "corpusVersion": "code-research-quality/v1",
        "sampleCount": 4,
        "scoreMeanAbsoluteError": 2.0833,
        "withinToleranceRate": 1.0,
        "recommendationAgreement": 1.0,
        "riskCountMeanAbsoluteError": 0.0,
        "passed": True,
    }:
        raise AssertionError(f"calibration result diverged: {json.dumps(result, ensure_ascii=False)}")

    with tempfile.TemporaryDirectory(prefix="code-research-quality-contract-") as directory:
        root = Path(directory)
        for case_id in ("landscape-balanced", "landscape-sparse"):
            repository = materialize(case_id, root)
            bundle = root / f"{case_id}-map"
            run([sys.executable, str(MAP_SCRIPT), "scan", str(repository), str(bundle)])
            gate = run([sys.executable, str(QUALITY_SCRIPT), "validate-map", str(bundle)])
            if read_json_from_text(gate.stdout).get("healthy") is not True:
                raise AssertionError(f"map hard gate was not healthy: {case_id}")
            evaluated = evaluate(bundle, case_id, root / f"{case_id}-result.json")
            if evaluated.get("healthy") is not True or evaluated["semanticEvaluation"]["passed"] is not True:
                raise AssertionError(f"landscape quality case failed: {case_id}: {evaluated}")

        study_cases = {
            "deep-read-runtime": "src",
            "deep-read-unknowns": "src",
        }
        for case_id, target_path in study_cases.items():
            repository = materialize(case_id, root)
            map_bundle = root / f"{case_id}-map"
            run([sys.executable, str(MAP_SCRIPT), "scan", str(repository), str(map_bundle)])
            targets = read_json(map_bundle / "navigation" / "targets.json")["targets"]
            target = next(item for item in targets if item["path"] == target_path)
            study_bundle = root / f"{case_id}-study"
            run([
                sys.executable,
                str(STUDY_SCRIPT),
                "study",
                str(repository),
                str(study_bundle),
                "--map",
                str(map_bundle),
                "--target",
                target["id"],
            ])
            gate = run([
                sys.executable,
                str(QUALITY_SCRIPT),
                "validate-study",
                str(study_bundle),
                "--map",
                str(map_bundle),
            ])
            if read_json_from_text(gate.stdout).get("healthy") is not True:
                raise AssertionError(f"study hard gate was not healthy: {case_id}")
            evaluated = evaluate(study_bundle, case_id, root / f"{case_id}-result.json", map_bundle)
            if evaluated.get("healthy") is not True or evaluated["semanticEvaluation"]["passed"] is not True:
                raise AssertionError(f"deep-read quality case failed: {case_id}: {evaluated}")

        tampered_repository = materialize("landscape-balanced", root, "tampered-repository")
        tampered_bundle = root / "tampered-map"
        run([sys.executable, str(MAP_SCRIPT), "scan", str(tampered_repository), str(tampered_bundle)])
        shard = tampered_bundle / "facts" / "summary.json"
        shard.write_text(shard.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        rejected = run([sys.executable, str(QUALITY_SCRIPT), "validate-map", str(tampered_bundle)], check=False)
        if rejected.returncode == 0 or "SHA-256 mismatch" not in rejected.stderr:
            raise AssertionError("quality gate accepted a tampered map bundle")

    print("code-research quality contract passed")
    return 0


def read_json_from_text(value: str) -> dict[str, object]:
    return json.loads(value)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"code-research quality contract: {error}", file=sys.stderr)
        raise SystemExit(1)

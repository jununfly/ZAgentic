#!/usr/bin/env python3
"""Mechanical gates and calibrated quality checks for code-research bundles.

The shared ZHarness evaluator owns technical-report families. This module owns
the separate ``landscape/v1`` and ``deep-read/v1`` contract: it validates the
immutable Repository Map / Architecture Study bundles, scores controlled
fixtures against human annotations, and reports calibrated Judge agreement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import architecture_study
import repository_map


ASSET_MANIFEST_SCHEMA = "zj-code-research-evaluation-manifest/v1"
RUBRIC_SCHEMA = "zj-code-research-rubric-set/v1"
ANNOTATION_SCHEMA = "zj-code-research-human-annotation-set/v1"
CALIBRATION_SCHEMA = "zj-code-research-judge-calibration-set/v1"
CALIBRATION_RESULT_SCHEMA = "zj-code-research-calibration-result/v1"
RECORD_KINDS = {"observed", "inferred", "unknown", "decision"}
ARTIFACT_KINDS = {"repository-map", "architecture-study"}
RUBRIC_VERSIONS = {"landscape/v1", "deep-read/v1"}


class QualityError(RuntimeError):
    """A code-research quality contract failure."""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise QualityError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise QualityError(f"JSON object expected: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise QualityError(f"could not read JSONL {path}: {error}") from error
    records: list[dict[str, Any]] = []
    for number, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise QualityError(f"invalid JSONL {path}:{number}: {error}") from error
        if not isinstance(value, dict):
            raise QualityError(f"JSON object expected at {path}:{number}")
        records.append(value)
    return records


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_list(value: Any, name: str, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list):
        raise QualityError(f"{name} must be a list")
    if len(value) < minimum:
        raise QualityError(f"{name} must contain at least {minimum} item(s)")
    return value


def load_assets(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = read_object(root / "manifest.json")
    rubrics = read_object(root / "rubrics.json")
    annotations = read_object(root / "annotations.json")
    calibration = read_object(root / "calibration.json")
    if manifest.get("schema") != ASSET_MANIFEST_SCHEMA:
        raise QualityError("code-research asset manifest has an unsupported schema")
    if manifest.get("method") != "zj-code-research":
        raise QualityError("code-research asset manifest has the wrong method")
    if rubrics.get("schema") != RUBRIC_SCHEMA:
        raise QualityError("code-research rubrics have an unsupported schema")
    if annotations.get("schema") != ANNOTATION_SCHEMA:
        raise QualityError("code-research annotations have an unsupported schema")
    if calibration.get("schema") != CALIBRATION_SCHEMA:
        raise QualityError("code-research calibration has an unsupported schema")
    corpus_version = manifest.get("corpusVersion")
    if not nonempty(corpus_version):
        raise QualityError("asset manifest needs corpusVersion")
    for name, document in (("rubrics", rubrics), ("annotations", annotations), ("calibration", calibration)):
        if document.get("corpusVersion") != corpus_version:
            raise QualityError(f"{name} corpusVersion does not match the manifest")

    rubric_items = require_list(rubrics.get("rubrics"), "rubrics.rubrics", 2)
    rubric_by_version: dict[str, dict[str, Any]] = {}
    for rubric in rubric_items:
        if not isinstance(rubric, dict) or rubric.get("id") not in RUBRIC_VERSIONS:
            raise QualityError("rubrics must define landscape/v1 and deep-read/v1")
        criteria = require_list(rubric.get("criteria"), f"rubric {rubric.get('id')}.criteria", 1)
        weight_sum = 0
        for criterion in criteria:
            if not isinstance(criterion, dict) or not nonempty(criterion.get("id")) or not nonempty(criterion.get("description")):
                raise QualityError(f"rubric {rubric.get('id')} has an invalid criterion")
            weight = criterion.get("weight")
            if not isinstance(weight, (int, float)) or weight <= 0:
                raise QualityError(f"rubric {rubric.get('id')} has an invalid weight")
            weight_sum += weight
        if weight_sum != 100:
            raise QualityError(f"rubric {rubric.get('id')} weights must sum to 100")
        rubric_by_version[rubric["id"]] = rubric
    if set(rubric_by_version) != RUBRIC_VERSIONS:
        raise QualityError("rubrics must contain exactly landscape/v1 and deep-read/v1")

    annotation_items = require_list(annotations.get("cases"), "annotations.cases", 4)
    annotation_by_case: dict[str, dict[str, Any]] = {}
    for item in annotation_items:
        if not isinstance(item, dict) or not nonempty(item.get("caseId")):
            raise QualityError("every annotation needs caseId")
        if item["caseId"] in annotation_by_case:
            raise QualityError(f"duplicate annotation case: {item['caseId']}")
        if item.get("rubricVersion") not in RUBRIC_VERSIONS:
            raise QualityError(f"annotation {item['caseId']} has an unsupported rubricVersion")
        if not isinstance(item.get("expected"), dict):
            raise QualityError(f"annotation {item['caseId']} needs expected checks")
        annotation_by_case[item["caseId"]] = item

    cases = require_list(manifest.get("cases"), "manifest.cases", 4)
    case_by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict) or not nonempty(case.get("id")):
            raise QualityError("every manifest case needs an id")
        case_id = case["id"]
        if case_id in case_by_id:
            raise QualityError(f"duplicate manifest case: {case_id}")
        if case.get("artifactKind") not in ARTIFACT_KINDS:
            raise QualityError(f"case {case_id} has an unsupported artifactKind")
        if case.get("rubricVersion") not in RUBRIC_VERSIONS:
            raise QualityError(f"case {case_id} has an unsupported rubricVersion")
        if case.get("annotationId") not in annotation_by_case:
            raise QualityError(f"case {case_id} has no matching annotation")
        fixture = root / str(case.get("fixture", ""))
        if not fixture.is_dir() or fixture == root:
            raise QualityError(f"case {case_id} fixture is missing: {fixture}")
        case_by_id[case_id] = case
    if set(case_by_id) != set(annotation_by_case):
        raise QualityError("manifest cases and annotation cases do not match")

    samples = require_list(calibration.get("samples"), "calibration.samples", 4)
    sample_ids: set[str] = set()
    for sample in samples:
        if not isinstance(sample, dict) or not nonempty(sample.get("caseId")):
            raise QualityError("every calibration sample needs caseId")
        if sample["caseId"] in sample_ids or sample["caseId"] not in case_by_id:
            raise QualityError(f"calibration sample references an invalid or duplicate case: {sample.get('caseId')}")
        sample_ids.add(sample["caseId"])
        for side in ("human", "judge"):
            assessment = sample.get(side)
            if not isinstance(assessment, dict) or not isinstance(assessment.get("scores"), dict):
                raise QualityError(f"calibration {sample['caseId']} needs {side}.scores")
            if not nonempty(assessment.get("recommendation")) or not isinstance(assessment.get("riskCount"), int):
                raise QualityError(f"calibration {sample['caseId']} needs recommendation and riskCount")
            for key, score in assessment["scores"].items():
                if not nonempty(key) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
                    raise QualityError(f"calibration {sample['caseId']} has an invalid score")
    return {
        "root": root,
        "manifest": manifest,
        "rubrics": rubric_by_version,
        "annotations": annotation_by_case,
        "cases": case_by_id,
        "calibration": calibration,
    }


def calibrate(assets: dict[str, Any]) -> dict[str, Any]:
    samples = assets["calibration"]["samples"]
    thresholds = assets["manifest"].get("calibration", {})
    absolute_errors: list[float] = []
    within_tolerance = 0
    score_count = 0
    recommendation_matches = 0
    risk_errors: list[float] = []
    tolerance = float(thresholds.get("scoreTolerance", 10))
    for sample in samples:
        human = sample["human"]
        judge = sample["judge"]
        human_scores = human["scores"]
        judge_scores = judge["scores"]
        keys = set(human_scores) & set(judge_scores)
        if not keys:
            raise QualityError(f"calibration {sample['caseId']} has no shared score dimensions")
        for key in keys:
            error = abs(float(human_scores[key]) - float(judge_scores[key]))
            absolute_errors.append(error)
            score_count += 1
            if error <= tolerance:
                within_tolerance += 1
        if human["recommendation"] == judge["recommendation"]:
            recommendation_matches += 1
        risk_errors.append(abs(human["riskCount"] - judge["riskCount"]))
    score_mae = sum(absolute_errors) / len(absolute_errors)
    within_rate = within_tolerance / score_count
    recommendation_rate = recommendation_matches / len(samples)
    risk_mae = sum(risk_errors) / len(risk_errors)
    result = {
        "schema": CALIBRATION_RESULT_SCHEMA,
        "corpusVersion": assets["manifest"]["corpusVersion"],
        "sampleCount": len(samples),
        "scoreMeanAbsoluteError": round(score_mae, 4),
        "withinToleranceRate": round(within_rate, 4),
        "recommendationAgreement": round(recommendation_rate, 4),
        "riskCountMeanAbsoluteError": round(risk_mae, 4),
    }
    result["passed"] = (
        len(samples) >= int(thresholds.get("minimumSamples", 4))
        and score_mae <= float(thresholds.get("maxMeanAbsoluteError", 5))
        and within_rate >= float(thresholds.get("minWithinToleranceRate", 0.8))
        and recommendation_rate >= float(thresholds.get("minRecommendationAgreement", 0.9))
        and risk_mae <= float(thresholds.get("maxRiskCountMeanAbsoluteError", 0.5))
    )
    return result


def duplicate_ids(records: Iterable[dict[str, Any]], label: str, seen: set[str]) -> None:
    for record in records:
        record_id = record.get("id")
        if not nonempty(record_id):
            raise QualityError(f"{label} record needs a stable id")
        if record_id in seen:
            raise QualityError(f"duplicate record id in {label}: {record_id}")
        seen.add(record_id)


def validate_map_quality(bundle: Path) -> dict[str, Any]:
    try:
        base = repository_map.validate_bundle(bundle)
    except repository_map.MapError as error:
        raise QualityError(f"Repository Map mechanical gate failed: {error}") from error
    bundle = bundle.resolve()
    manifest = read_object(bundle / "manifest.json")
    summary = read_object(bundle / "facts" / "summary.json")
    targets = read_object(bundle / "navigation" / "targets.json").get("targets")
    tree = read_jsonl(bundle / "facts" / "tree.jsonl")
    packages = read_jsonl(bundle / "facts" / "packages.jsonl")
    integrations = read_jsonl(bundle / "facts" / "integrations.jsonl")
    workflows = read_jsonl(bundle / "facts" / "workflows.jsonl")
    source = manifest.get("source")
    if not isinstance(source, dict) or not (nonempty(source.get("commit")) or nonempty(source.get("workingTreeFingerprint"))):
        raise QualityError("Repository Map source is not pinned")
    if summary.get("source") != source:
        raise QualityError("Repository Map manifest and summary source differ")
    scope = summary.get("scope")
    if not isinstance(scope, dict) or scope.get("root") != "." or ".git" not in scope.get("exclusions", []):
        raise QualityError("Repository Map scope/exclusions are not explicit")
    paths = [item.get("path") for item in tree]
    if any(not isinstance(path, str) for path in paths) or len(paths) != len(set(paths)):
        raise QualityError("Repository Map tree paths are not unique")
    if not isinstance(targets, list) or not targets:
        raise QualityError("Repository Map has no navigation targets")
    seen_ids: set[str] = set()
    tree_paths = set(paths)
    target_keys: set[tuple[str, str]] = set()
    for target in targets:
        if not isinstance(target, dict) or not all(nonempty(target.get(field)) for field in ("id", "kind", "path", "reason")):
            raise QualityError("navigation targets need id, kind, path, and reason")
        duplicate_ids([target], "navigation", seen_ids)
        key = (target["kind"], target["path"])
        if key in target_keys:
            raise QualityError(f"duplicate navigation target: {key[0]} {key[1]}")
        target_keys.add(key)
        if target["path"] != "." and target["path"] not in tree_paths:
            raise QualityError(f"navigation target points outside the tree: {target['path']}")
    inventory = summary.get("inventory")
    if not isinstance(inventory, dict):
        raise QualityError("Repository Map inventory is missing")
    if inventory.get("files") != sum(item.get("kind") == "file" for item in tree) or inventory.get("directories") != sum(item.get("kind") == "directory" for item in tree):
        raise QualityError("Repository Map inventory does not match the tree")
    unknowns = summary.get("unknowns")
    if not isinstance(unknowns, list):
        raise QualityError("Repository Map unknowns must be explicit, including an empty list")
    target_kinds = sorted({target["kind"] for target in targets})
    return {
        "healthy": True,
        "artifact": "repository-map",
        "schema": repository_map.MANIFEST_SCHEMA,
        "snapshotId": manifest["snapshotId"],
        "checks": {
            "sourcePinned": True,
            "scopeAndExclusions": True,
            "treeIntegrity": True,
            "inventoryConsistency": True,
            "navigationBinding": True,
            "unknownsExplicit": True,
        },
        "counts": {
            "files": inventory["files"],
            "directories": inventory["directories"],
            "packages": len(packages),
            "integrations": len(integrations),
            "workflows": len(workflows),
            "targets": len(targets),
            "unknowns": len(unknowns),
        },
        "targetKinds": target_kinds,
        "base": base,
    }


def validate_study_quality(bundle: Path, map_bundle: Path | None = None) -> dict[str, Any]:
    try:
        base = architecture_study.validate_study(bundle)
    except (architecture_study.StudyError, repository_map.MapError) as error:
        raise QualityError(f"Architecture Study mechanical gate failed: {error}") from error
    bundle = bundle.resolve()
    manifest = read_object(bundle / "manifest.json")
    scope = read_object(bundle / "facts" / "scope.json")
    evidence = read_jsonl(bundle / "facts" / "evidence.jsonl")
    relationships = read_jsonl(bundle / "facts" / "relationships.jsonl")
    flows = read_jsonl(bundle / "facts" / "flows.jsonl")
    claims = read_jsonl(bundle / "facts" / "claims.jsonl")
    unknowns = read_jsonl(bundle / "facts" / "unknowns.jsonl")
    risks = read_jsonl(bundle / "facts" / "risks.jsonl")
    diagrams = read_jsonl(bundle / "facts" / "diagrams.jsonl")
    followups = read_object(bundle / "navigation" / "follow-up-targets.json").get("targets")
    if not isinstance(followups, list):
        raise QualityError("Architecture Study follow-up targets must be a list")
    source = scope.get("source")
    if not isinstance(source, dict) or not (nonempty(source.get("commit")) or nonempty(source.get("workingTreeFingerprint"))):
        raise QualityError("Architecture Study source is not pinned")
    targets = scope.get("targets")
    if not isinstance(targets, list) or not targets:
        raise QualityError("Architecture Study has no selected scope")
    target_ids = [item.get("id") for item in targets if isinstance(item, dict)]
    if len(target_ids) != len(set(target_ids)) or any(not nonempty(value) for value in target_ids):
        raise QualityError("Architecture Study target IDs are not unique")
    if scope.get("mapBinding", {}).get("used") is True:
        binding = scope["mapBinding"]
        if not nonempty(binding.get("snapshotId")) or not set(target_ids).issubset(set(binding.get("targetIds", []))):
            raise QualityError("Architecture Study map binding does not cover selected targets")
        if map_bundle is not None:
            map_manifest = read_object(map_bundle.resolve() / "manifest.json")
            if map_manifest.get("snapshotId") != binding.get("snapshotId"):
                raise QualityError("Architecture Study references a different Repository Map snapshot")
    evidence_ids = {item.get("id") for item in evidence}
    if len(evidence_ids) != len(evidence) or any(not nonempty(value) for value in evidence_ids):
        raise QualityError("Architecture Study evidence IDs are not unique")
    for item in evidence:
        if item.get("kind") != "observed" or not nonempty(item.get("sourcePath")):
            raise QualityError("every Architecture Study evidence record must be observed and line-addressable")
        if not isinstance(item.get("lineStart"), int) or not isinstance(item.get("lineEnd"), int) or item["lineStart"] < 1 or item["lineEnd"] < item["lineStart"]:
            raise QualityError("Architecture Study evidence has invalid line coordinates")
        if item.get("commit") != source.get("commit") or item.get("workingTreeFingerprint") != source.get("workingTreeFingerprint"):
            raise QualityError("Architecture Study evidence source identity differs from scope")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise QualityError("Architecture Study evidence needs a file SHA-256")
    seen: set[str] = set(evidence_ids)
    for label, records in (("relationships", relationships), ("flows", flows), ("claims", claims), ("unknowns", unknowns), ("risks", risks), ("diagrams", diagrams), ("follow-ups", followups)):
        for record in records:
            if not isinstance(record, dict) or record.get("kind") not in RECORD_KINDS:
                raise QualityError(f"{label} record has an invalid kind")
            record_id = record.get("id")
            if not nonempty(record_id) or record_id in seen:
                raise QualityError(f"{label} contains a duplicate or missing record id: {record_id}")
            seen.add(record_id)
            for evidence_id in record.get("evidenceIds", []):
                if evidence_id not in evidence_ids:
                    raise QualityError(f"{label} references missing evidence: {evidence_id}")
            if label == "claims" and record.get("critical") is True and not record.get("evidenceIds"):
                raise QualityError("critical Architecture Study claim has no evidence IDs")
    if not diagrams or not flows or not risks:
        raise QualityError("Architecture Study must keep diagrams, flows, and explicit follow-up/unknown sections")
    return {
        "healthy": True,
        "artifact": "architecture-study",
        "schema": architecture_study.MANIFEST_SCHEMA,
        "snapshotId": manifest["snapshotId"],
        "checks": {
            "sourcePinned": True,
            "targetBinding": True,
            "evidenceCoordinates": True,
            "recordKinds": True,
            "uniqueRecordIds": True,
            "criticalClaimsEvidence": True,
            "unknownsAndRisksExplicit": True,
            "followUpNavigation": True,
        },
        "counts": {
            "targets": len(targets),
            "evidence": len(evidence),
            "relationships": len(relationships),
            "flows": len(flows),
            "claims": len(claims),
            "unknowns": len(unknowns),
            "risks": len(risks),
            "diagrams": len(diagrams),
            "followups": len(followups),
        },
        "base": base,
    }


def ratio(numerator: int, denominator: int) -> float:
    return 100.0 if denominator == 0 else round(100 * numerator / denominator, 2)


def evaluate_map(case: dict[str, Any], annotation: dict[str, Any], gate: dict[str, Any]) -> dict[str, float]:
    expected = annotation["expected"]
    targets = gate["counts"]
    target_kinds = set(expected.get("requiredTargetKinds", []))
    available_kinds = set(gate.get("targetKinds", []))
    required_target_kinds = len(target_kinds)
    target_kind_hits = len(target_kinds & available_kinds)
    min_files = int(expected.get("minimumFiles", 1))
    min_targets = int(expected.get("minimumTargets", 1))
    return {
        "scope-pinning": 100.0,
        "inventory-coverage": min(100.0, ratio(min(targets["files"], min_files), min_files)),
        "navigation-stability": min(100.0, ratio(min(targets["targets"], min_targets), min_targets)) if required_target_kinds == 0 else min(100.0, ratio(target_kind_hits, required_target_kinds)),
        "degradation-disclosure": 100.0 if isinstance(gate["base"], dict) else 0.0,
        "handoff-usefulness": 100.0 if targets["targets"] >= min_targets else ratio(targets["targets"], min_targets),
    }


def evaluate_study(annotation: dict[str, Any], gate: dict[str, Any], bundle: Path) -> dict[str, float]:
    expected = annotation["expected"]
    evidence = read_jsonl(bundle.resolve() / "facts" / "evidence.jsonl")
    claims = read_jsonl(bundle.resolve() / "facts" / "claims.jsonl")
    unknowns = read_jsonl(bundle.resolve() / "facts" / "unknowns.jsonl")
    risks = read_jsonl(bundle.resolve() / "facts" / "risks.jsonl")
    followups = read_object(bundle.resolve() / "navigation" / "follow-up-targets.json").get("targets") or []
    required_subjects = set(expected.get("requiredEvidenceSubjects", []))
    subjects = {item.get("subject") for item in evidence}
    required_unknowns = set(expected.get("requiredUnknownCategories", []))
    unknown_categories = {item.get("category") for item in unknowns}
    required_risks = set(expected.get("requiredRisks", []))
    risk_names = {item.get("risk") for item in risks}
    valid_claims = sum(1 for claim in claims if claim.get("critical") is not True or claim.get("evidenceIds"))
    return {
        "target-adherence": 100.0 if gate["checks"]["targetBinding"] else 0.0,
        "evidence-fidelity": ratio(len(required_subjects & subjects) + (1 if valid_claims == len(claims) else 0), len(required_subjects) + 1),
        "certainty-separation": ratio(len(required_unknowns & unknown_categories), len(required_unknowns)) if required_unknowns else 100.0,
        "runtime-ownership-risk": ratio(len(required_risks & risk_names), len(required_risks)) if required_risks else 100.0,
        "follow-up-utility": 100.0 if len(followups) >= int(expected.get("minimumFollowups", 1)) and all(nonempty(item.get("path")) and nonempty(item.get("reason")) for item in followups) else ratio(len(followups), int(expected.get("minimumFollowups", 1))),
    }


def evaluate_bundle(assets: dict[str, Any], case_id: str, bundle: Path, map_bundle: Path | None = None) -> dict[str, Any]:
    if case_id not in assets["cases"]:
        raise QualityError(f"unknown quality case: {case_id}")
    case = assets["cases"][case_id]
    annotation = assets["annotations"][case["annotationId"]]
    if case["artifactKind"] == "repository-map":
        gate = validate_map_quality(bundle)
        dimensions = evaluate_map(case, annotation, gate)
    else:
        gate = validate_study_quality(bundle, map_bundle)
        dimensions = evaluate_study(annotation, gate, bundle)
    minimum = float(assets["manifest"].get("minimumSemanticScore", 80))
    passed = gate["healthy"] and all(score >= minimum for score in dimensions.values())
    return {
        "schema": "zj-code-research-quality-result/v1",
        "corpusVersion": assets["manifest"]["corpusVersion"],
        "caseId": case_id,
        "artifactKind": case["artifactKind"],
        "hardGate": gate,
        "semanticEvaluation": {
            "rubricVersion": case["rubricVersion"],
            "dimensions": dimensions,
            "minimumScore": minimum,
            "passed": passed,
        },
        "calibration": calibrate(assets),
        "healthy": passed and calibrate(assets)["passed"],
    }


def write_result(result: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        output.write_text(rendered, encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Validate and evaluate code-research quality contracts")
    commands = root.add_subparsers(dest="command", required=True)
    assets = commands.add_parser("validate-assets")
    assets.add_argument("assets", type=Path)
    calibrate_command = commands.add_parser("calibrate")
    calibrate_command.add_argument("assets", type=Path)
    validate_map = commands.add_parser("validate-map")
    validate_map.add_argument("bundle", type=Path)
    validate_study = commands.add_parser("validate-study")
    validate_study.add_argument("bundle", type=Path)
    validate_study.add_argument("--map", dest="map_bundle", type=Path)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("bundle", type=Path)
    evaluate.add_argument("--case", required=True)
    evaluate.add_argument("--assets", required=True, type=Path)
    evaluate.add_argument("--map", dest="map_bundle", type=Path)
    evaluate.add_argument("--output", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "validate-assets":
        assets = load_assets(args.assets)
        result = {"healthy": True, "schema": ASSET_MANIFEST_SCHEMA, "corpusVersion": assets["manifest"]["corpusVersion"], "caseCount": len(assets["cases"]), "rubrics": sorted(assets["rubrics"])}
        write_result(result, None)
    elif args.command == "calibrate":
        write_result(calibrate(load_assets(args.assets)), None)
    elif args.command == "validate-map":
        write_result(validate_map_quality(args.bundle), None)
    elif args.command == "validate-study":
        write_result(validate_study_quality(args.bundle, args.map_bundle), None)
    else:
        result = evaluate_bundle(load_assets(args.assets), args.case, args.bundle, args.map_bundle)
        write_result(result, args.output)
        if not result["healthy"]:
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (QualityError, OSError, ValueError) as error:
        print(f"code-research quality: {error}", file=sys.stderr)
        raise SystemExit(1)

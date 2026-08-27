#!/usr/bin/env python3
"""Validate the technical decision brief and technical-c4 Report IR."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BRIEF_SCHEMA = "technical-decision-brief/v1"
REPORT_SCHEMA = "zj-research-report-ir/v1"
REPORT_FAMILY = "technical-c4/v1"
QUALITY_GATE_SCHEMA = "technical-research-quality-gate/v1"
STAGES = {"problem-discovery", "experience-version", "usefulness-validation", "dogfood", "release"}
METRIC_FIELDS = ("key", "definition", "unit", "method", "condition", "expected")


class QualityError(RuntimeError):
    """A report failed the technical quality gate."""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise QualityError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise QualityError(f"JSON object expected: {path}")
    return value


def unwrap_ledger(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("operation") == "collect" and isinstance(value.get("result"), dict):
        return value["result"]
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_object(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def require_list(value: Any, name: str, errors: list[str], minimum: int = 0) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return []
    if len(value) < minimum:
        errors.append(f"{name} must contain at least {minimum} item(s)")
    return value


def validate_brief(brief: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if brief.get("schema") != BRIEF_SCHEMA:
        errors.append(f"brief.schema must be {BRIEF_SCHEMA}")
    user = require_object(brief.get("user"), "brief.user", errors)
    for field in ("actor", "job"):
        if not nonempty(user.get(field)):
            errors.append(f"brief.user.{field} is required")
    baseline = require_object(brief.get("baseline"), "brief.baseline", errors)
    for field in ("workflow", "failureModes"):
        if field == "workflow" and not nonempty(baseline.get(field)):
            errors.append("brief.baseline.workflow is required")
        if field == "failureModes":
            require_list(baseline.get(field), "brief.baseline.failureModes", errors, 1)
    if not nonempty(brief.get("targetOutcome")):
        errors.append("brief.targetOutcome is required")
    require_list(brief.get("goals"), "brief.goals", errors, 1)
    require_list(brief.get("nonGoals"), "brief.nonGoals", errors, 1)
    constraints = require_list(brief.get("constraints"), "brief.constraints", errors, 1)
    for index, constraint in enumerate(constraints):
        if isinstance(constraint, str):
            if not constraint.strip():
                errors.append(f"brief.constraints[{index}] is empty")
        elif not isinstance(constraint, dict) or not nonempty(constraint.get("id")) or not nonempty(constraint.get("statement")):
            errors.append(f"brief.constraints[{index}] needs id and statement")
    require_list(brief.get("assumptions"), "brief.assumptions", errors, 1)
    if brief.get("stage") not in STAGES:
        errors.append(f"brief.stage must be one of: {', '.join(sorted(STAGES))}")
    if not nonempty(brief.get("decisionScope")):
        errors.append("brief.decisionScope is required")
    options = require_list(brief.get("options"), "brief.options", errors, 1)
    for index, option in enumerate(options):
        if isinstance(option, str):
            valid = bool(option.strip())
        else:
            valid = isinstance(option, dict) and nonempty(option.get("id")) and nonempty(option.get("name"))
        if not valid:
            errors.append(f"brief.options[{index}] needs a name or a non-empty string")
    if errors:
        raise QualityError("technical decision brief failed: " + "; ".join(errors))
    return {
        "schema": BRIEF_SCHEMA,
        "stage": brief["stage"],
        "constraintCount": len(constraints),
        "optionCount": len(options),
        "goalCount": len(brief["goals"]),
    }


def repository_key(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict) or not isinstance(value.get("owner"), str) or not isinstance(value.get("name"), str):
        return None
    return value["owner"], value["name"]


def text_of(item: dict[str, Any], *fields: str) -> str:
    return " ".join(str(item.get(field, "")) for field in fields)


def validate_report(report: dict[str, Any], ledger_value: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    brief_result = validate_brief(brief)
    ledger = unwrap_ledger(ledger_value)
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA:
        errors.append(f"report.schema must be {REPORT_SCHEMA}")
    if report.get("family") != REPORT_FAMILY:
        errors.append(f"report.family must be {REPORT_FAMILY}")
    if not nonempty(report.get("title")) or not nonempty(report.get("summary")):
        errors.append("report.title and report.summary are required")
    if report.get("ledgerFingerprint") != ledger.get("briefFingerprint"):
        errors.append("report.ledgerFingerprint must equal the sealed ledger briefFingerprint")
    concepts = require_list(report.get("concepts"), "report.concepts", errors, 1)
    if any(not isinstance(item, dict) or not nonempty(item.get("key")) or not nonempty(item.get("value")) for item in concepts):
        errors.append("every concept needs a key and value")
    diagrams = require_list(report.get("diagrams"), "report.diagrams", errors, 2)
    diagram_kinds = {str(item.get("kind", "")).lower() for item in diagrams if isinstance(item, dict)}
    if "landscape" not in diagram_kinds:
        errors.append("technical-c4 requires one landscape diagram")
    if not diagram_kinds.intersection({"container", "context", "topic"}):
        errors.append("technical-c4 requires one container, context, or topic diagram")
    ledger_evidence = {item.get("id") for item in ledger.get("evidence", []) if isinstance(item, dict)}
    ledger_candidates = {repository_key(item.get("repository")): item for item in ledger.get("candidates", []) if isinstance(item, dict) and repository_key(item.get("repository"))}
    candidates = require_list(report.get("candidates"), "report.candidates", errors, 1)
    candidate_keys: set[tuple[str, str]] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"report.candidates[{index}] must be an object")
            continue
        key = repository_key(candidate.get("repository"))
        if key is None:
            errors.append(f"report.candidates[{index}] needs repository.owner and repository.name")
        else:
            candidate_keys.add(key)
            source = ledger_candidates.get(key)
            if source is None:
                errors.append(f"candidate {key[0]}/{key[1]} is not present in the sealed ledger")
            else:
                for field in ("stars", "topicMatch"):
                    if candidate.get(field) != source.get(field):
                        errors.append(f"candidate {key[0]}/{key[1]} does not copy sealed ledger {field}")
        candidate_evidence_ids = candidate.get("evidenceIds")
        if not isinstance(candidate_evidence_ids, list) or not candidate_evidence_ids:
            errors.append(f"candidate {index} needs sealed evidenceIds")
        for evidence_id in candidate_evidence_ids or []:
            if evidence_id not in ledger_evidence:
                errors.append(f"candidate {index} references missing Evidence ID {evidence_id}")
    cards = require_list(report.get("cards"), "report.cards", errors, len(candidates))
    if len(cards) != len(candidates):
        errors.append("report.cards must contain exactly one card per serious candidate")
    claim_items = require_list(report.get("claims"), "report.claims", errors, 1)
    claim_ids = {item.get("id") for item in claim_items if isinstance(item, dict)}
    for index, card in enumerate(cards):
        if not isinstance(card, dict) or not nonempty(card.get("title")) or not nonempty(card.get("summary")):
            errors.append(f"report.cards[{index}] needs title and summary")
        if isinstance(card, dict) and not card.get("claimIds"):
            errors.append(f"report.cards[{index}] needs claimIds")
        for claim_id in card.get("claimIds", []) if isinstance(card, dict) else []:
            if claim_id not in claim_ids:
                errors.append(f"card {index} references missing claim {claim_id}")
    for index, claim in enumerate(claim_items):
        if not isinstance(claim, dict) or not nonempty(claim.get("id")) or not nonempty(claim.get("text")):
            errors.append(f"report.claims[{index}] needs id and text")
            continue
        evidence_ids = claim.get("evidenceIds")
        if not isinstance(evidence_ids, list) or (claim.get("critical") is True and not evidence_ids):
            errors.append(f"claim {claim.get('id')} needs evidenceIds; critical claims cannot be ungrounded")
        for evidence_id in evidence_ids or []:
            if evidence_id not in ledger_evidence:
                errors.append(f"claim {claim.get('id')} references missing Evidence ID {evidence_id}")
    comparisons = require_list(report.get("comparisons"), "report.comparisons", errors, 1)
    comparison_ids = {item.get("id") for item in comparisons if isinstance(item, dict)}
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict) or not nonempty(comparison.get("id")) or not nonempty(comparison.get("text")):
            errors.append(f"report.comparisons[{index}] needs id and text")
            continue
        claim_ids_for_comparison = comparison.get("claimIds")
        if not isinstance(claim_ids_for_comparison, list) or not claim_ids_for_comparison:
            errors.append(f"comparison {comparison.get('id')} needs claimIds")
        for claim_id in claim_ids_for_comparison or []:
            if claim_id not in claim_ids:
                errors.append(f"comparison {comparison.get('id')} references missing claim {claim_id}")
    recommendations = require_list(report.get("recommendations"), "report.recommendations", errors, 1)
    for index, recommendation in enumerate(recommendations):
        if not isinstance(recommendation, dict) or not nonempty(recommendation.get("id")) or not nonempty(recommendation.get("text")):
            errors.append(f"report.recommendations[{index}] needs id and text")
            continue
        for comparison_id in recommendation.get("comparisonIds", []):
            if comparison_id not in comparison_ids:
                errors.append(f"recommendation {recommendation.get('id')} references missing comparison {comparison_id}")
    metrics = require_list(report.get("metrics"), "report.metrics", errors, 1)
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict) or any(not nonempty(metric.get(field)) for field in METRIC_FIELDS):
            errors.append(f"report.metrics[{index}] needs key, definition, unit, method, condition, and expected")
    unknown_criteria = ledger.get("unknownCriteria", [])
    # SKILL.md §5: do NOT treat unknownCriteria: [] as "no information gaps".
    # The report must state gap status via a structured `informationGaps` field
    # (not loose free text), and it is cross-checked against the sealed ledger.
    gaps = require_object(report.get("informationGaps"), "report.informationGaps", errors)
    if gaps:
        status = gaps.get("status")
        rationale = gaps.get("rationale")
        if status not in ("has-gaps", "no-gaps"):
            errors.append("report.informationGaps.status must be 'has-gaps' or 'no-gaps'")
        if not nonempty(rationale):
            errors.append("report.informationGaps.rationale is required")
        else:
            gap_tokens = ("unknown", "unverified", "gap", "待验证", "未知", "未验证", "信息缺口")
            no_gap_tokens = ("no gap", "no information gap", "no known gap", "无信息缺口", "无已知gap", "信息完整", "不含未决", "无未决")
            rationale_lower = str(rationale).lower()
            if not any(token in rationale_lower for token in gap_tokens + no_gap_tokens):
                errors.append("report.informationGaps.rationale must explicitly state the gap status (gap / no-gap token)")
        if status == "has-gaps" and not unknown_criteria:
            errors.append("report.informationGaps.status='has-gaps' but ledger unknownCriteria is empty")
        if status == "no-gaps" and unknown_criteria:
            errors.append("report.informationGaps.status='no-gaps' but ledger unknownCriteria is non-empty")
    unknowns_explicit = bool(gaps) and not any("informationGaps" in e for e in errors)
    if errors:
        raise QualityError("technical Report IR failed: " + "; ".join(errors))
    return {
        "healthy": True,
        "schema": QUALITY_GATE_SCHEMA,
        "briefSchema": BRIEF_SCHEMA,
        "reportFamily": REPORT_FAMILY,
        "checks": {
            "decisionFrame": True,
            "diagramCoverage": True,
            "candidateScoresFromLedger": True,
            "criticalClaimsEvidence": True,
            "comparisonTraceability": True,
            "recommendationTraceability": True,
            "metricCoverage": True,
            "unknownsSurfaced": unknowns_explicit,
        },
        "counts": {
            "concepts": len(concepts),
            "candidates": len(candidates),
            "cards": len(cards),
            "claims": len(claim_items),
            "comparisons": len(comparisons),
            "recommendations": len(recommendations),
            "metrics": len(metrics),
            "ledgerEvidence": len(ledger_evidence),
            "ledgerUnknownCriteria": len(unknown_criteria),
        },
        "brief": brief_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a technical decision brief and technical-c4 report")
    parser.add_argument("report_ir", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("brief", type=Path)
    args = parser.parse_args()
    result = validate_report(read_object(args.report_ir), read_object(args.ledger), read_object(args.brief))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (QualityError, OSError, json.JSONDecodeError) as error:
        print(f"technical report quality gate: {error}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""Validate an external Composer Plan artifact.

The validator deliberately works at the Markdown artifact boundary.  It does
not import a Composer runtime or execute any step named by a Plan.  Its output
is a stable JSON record so fixture oracles can depend on failure categories
without depending on parser implementation details.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional


PLAN_SCHEMA = "zj-composer/plan/v1"
SNAPSHOT_SCHEMA = "zj-composer/catalog-snapshot/v1"
TEMPLATE_REGISTRY_SCHEMA = "zj-composer/template-versions/v1"
REQUIRED_SECTIONS = (
    "Identity",
    "Intent",
    "Capability composition",
    "Gaps and suggestions",
    "Human checkpoints",
    "Evidence and provenance",
    "Verification",
    "Failure and rollback",
    "Handoff",
)
IDENTITY_FIELDS = (
    "plan_id",
    "title",
    "status",
    "template_version",
    "generated_at",
    "composer_version",
    "human_review",
)
INTENT_FIELDS = (
    "goal",
    "scope",
    "constraints",
    "desired_output",
    "exclusions",
    "permission_boundary",
)
STEP_FIELDS = (
    "skill_or_workflow",
    "role",
    "reason",
    "inputs",
    "outputs",
    "prerequisites",
    "dependencies",
    "excluded_alternatives",
)
CHECKPOINT_FIELDS = (
    "approval_point",
    "decisions_needed",
    "rejection_path",
    "side_effect_authorization",
)
PROVENANCE_FIELDS = (
    "skill_index_snapshot",
    "catalog_revision_or_digest",
    "source_references",
    "evidence_requirements",
    "generated_assertions",
    "unknowns",
)
VERIFICATION_FIELDS = ("step_checks", "scenario_oracle", "plan_acceptance")
FAILURE_FIELDS = ("failure_exits", "safe_stop", "rollback", "undeclared_side_effect_response")
HANDOFF_FIELDS = ("consuming_execution_chain", "handoff_preconditions", "authority_statement")
ALLOWED_STATUS = {"planned", "approved", "rejected", "superseded", "cancelled"}
ALLOWED_REVIEW = {"pending", "approved", "rejected"}
ALLOWED_ACCEPTANCE = {"pending", "passed", "failed", "rejected"}

PLACEHOLDERS = {
    "",
    "-",
    "--",
    "?",
    "tbd",
    "tba",
    "tbc",
    "n/a",
    "n.a.",
    "na",
    "none",
    "null",
    "{{value}}",
}
EXPLICIT_NONE = {
    "none",
    "none declared",
    "no prerequisites",
    "no dependencies",
    "not applicable",
    "n/a",
}
SECTION_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
FIELD_RE = re.compile(r"^\s*-\s+\*\*([^*]+):\*\*\s*(.*?)\s*$")
STEP_RE = re.compile(r"^Step\s+(\d+)\s+[-—]\s+(.+?)\s*$", re.IGNORECASE)
GAP_RE = re.compile(r"^required skill：\s*\S.*$")
GAP_LIKE_RE = re.compile(r"required\s+skill\s*[:：]", re.IGNORECASE)
SUGGESTION_RE = re.compile(r"^suggested capability：\s*\S.*$", re.IGNORECASE)
PROVENANCE_CLASS_RE = re.compile(
    r"(?:^|;)\s*(selected|excluded|suggested|gap)\s*=\s*\[([^\]]*)\]",
    re.IGNORECASE,
)
STEP_REF_RE = re.compile(r"\bStep\s+(\d+)\b", re.IGNORECASE)
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:")
SECRET_PATTERNS = (
    ("secret-shaped-output", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("secret-shaped-output", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret-shaped-output", re.compile(r"\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("secret-shaped-output", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("secret-shaped-output", re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("secret-shaped-output", re.compile(r"\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[A-Za-z0-9_./+=-]{8,}", re.IGNORECASE)),
)
SIDE_EFFECT_TERMS = re.compile(
    r"\b(?:write|writes|writing|network(?:\s+call|\s+request)?|git\s+(?:push|publish)|publish|publication|credential(?:s)?|secret(?:s)?|irreversible|delete|install|execute|execution|modify|mutation)\b",
    re.IGNORECASE,
)
DIRECT_SIDE_EFFECT = re.compile(
    r"\b(?:write|writes|writing|network\s+(?:call|request)|publish|publication|git\s+(?:push|publish)|credential(?:s)?|secret(?:s)?|irreversible|delete|install)\b",
    re.IGNORECASE,
)
AFFIRMATIVE_SIDE_EFFECT = re.compile(
    r"\b(?:will|must|may|can|should|perform|make|send|use|run|execute|write|publish|push|delete|install|modify)\b[^\n]{0,100}\b(?:write|network|request|publish|push|credential|secret|irreversible|delete|install|execute|modify)\b",
    re.IGNORECASE,
)
AUTHORITY_BYPASS = re.compile(
    r"\b(?:without\s+(?:human|approval)|bypass(?:ing)?\s+(?:human|approval|authority)|automatically\s+(?:write|publish|push|delete|install|execute)|no\s+approval\s+required|composer\s+(?:is|becomes)\s+(?:the\s+)?(?:second\s+)?(?:durable\s+)?authority(?:\s+of\s+record)?|second\s+(?:durable\s+)?authority)\b",
    re.IGNORECASE,
)
CONFLICT_MARKER = re.compile(
    r"(?:\bconflict\b|\bunresolved\s+conflict\b|\bhuman\s+choice\s+required\b|\bchoose\s+one\b|冲突|需要\s*Human\s*选择)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Diagnostic:
    category: str
    message: str
    line: Optional[int] = None
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
        }
        if self.line is not None:
            value["line"] = self.line
        return value


def clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1].strip()
    return value


def meaningful(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = clean_value(value).strip().casefold()
    return bool(normalized) and normalized not in PLACEHOLDERS and "{{" not in normalized


def is_explicit_none(value: str) -> bool:
    return clean_value(value).strip().casefold() in EXPLICIT_NONE


def negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 48) : start].casefold()
    return bool(re.search(r"\b(?:no|not|never|without|禁止|不得|仅停止|stop|refuse|拒绝)\b", prefix))


def read_plan(path: Path) -> tuple[str, list[str], list[Diagnostic]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "", [], [Diagnostic("plan_read_error", f"unable to read Plan: {exc}")]
    if not text.strip():
        return text, [], [Diagnostic("plan_empty", "Plan is empty")]
    return text, text.splitlines(), []


def parse_sections(lines: list[str], diagnostics: list[Diagnostic]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    sections: dict[str, dict[str, Any]] = {}
    if not lines or lines[0].strip() != "# Composer Plan":
        diagnostics.append(Diagnostic("invalid_title", "Plan must start with '# Composer Plan'", 1))
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines, 1):
        match = SECTION_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append((index, level, title))

    h2 = [(line, title) for line, level, title in headings if level == 2]
    seen: set[str] = set()
    for line, title in h2:
        if title in seen:
            diagnostics.append(Diagnostic("duplicate_section", f"section {title!r} appears more than once", line))
        seen.add(title)
    actual = [title for _, title in h2]
    for position, required in enumerate(REQUIRED_SECTIONS):
        if required not in seen:
            diagnostics.append(Diagnostic("missing_section", f"required section {required!r} is missing"))
        elif actual.index(required) != position:
            diagnostics.append(Diagnostic("section_order", f"section {required!r} is out of order"))

    for offset, (line, title) in enumerate(h2):
        end = h2[offset + 1][0] if offset + 1 < len(h2) else len(lines) + 1
        fields: dict[str, tuple[str, int]] = {}
        steps: list[dict[str, Any]] = []
        current_step: Optional[dict[str, Any]] = None
        for line_no in range(line + 1, end):
            raw = lines[line_no - 1]
            heading = SECTION_RE.match(raw)
            if heading and len(heading.group(1)) == 3 and title == "Capability composition":
                step = STEP_RE.match(heading.group(2).strip())
                if not step:
                    diagnostics.append(Diagnostic("malformed_step", "capability step heading must be 'Step N — name'", line_no))
                    current_step = None
                else:
                    current_step = {
                        "number": int(step.group(1)),
                        "name": step.group(2).strip(),
                        "line": line_no,
                        "fields": {},
                    }
                    steps.append(current_step)
                continue
            field = FIELD_RE.match(raw)
            if not field:
                continue
            name = field.group(1).strip()
            value = clean_value(field.group(2))
            target = current_step["fields"] if current_step is not None and title == "Capability composition" else fields
            if name in target:
                diagnostics.append(Diagnostic("duplicate_field", f"field {name!r} appears more than once", line_no))
            target[name] = (value, line_no)
        sections[title] = {"line": line, "fields": fields, "steps": steps}
    return sections, [{"line": line, "level": level, "title": title} for line, level, title in headings]


def field_value(section: dict[str, Any], name: str) -> tuple[Optional[str], Optional[int]]:
    value = section.get("fields", {}).get(name)
    return value if value is not None else (None, None)


def add_required_fields(sections: dict[str, dict[str, Any]], section_name: str, fields: Iterable[str], diagnostics: list[Diagnostic]) -> None:
    section = sections.get(section_name)
    if section is None:
        return
    for name in fields:
        value, line = field_value(section, name)
        if not meaningful(value):
            diagnostics.append(Diagnostic("missing_field", f"{section_name}.{name} must be a non-placeholder value", line or section["line"]))


def snapshot_path(root: Path, snapshot_id: str, explicit: Optional[Path]) -> Optional[Path]:
    if explicit is not None:
        return explicit.resolve()
    return (root / "skills-outputs" / "zj-composer" / "catalog-snapshots" / f"{snapshot_id}.json").resolve()


def digest_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_manifest_digest(manifest: list[dict[str, Any]]) -> str:
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_template_pin(root: Path, version: Optional[str], diagnostics: list[Diagnostic]) -> None:
    """Bind a Plan version to the exact bundled template bytes."""

    registry_path = root / "skills/productivity/zj-composer/references/template-versions.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        diagnostics.append(
            Diagnostic("template_registry_invalid", f"unable to read template version registry: {exc}")
        )
        return
    if not isinstance(registry, dict) or registry.get("schema") != TEMPLATE_REGISTRY_SCHEMA:
        diagnostics.append(
            Diagnostic(
                "template_registry_invalid",
                f"template registry schema must be {TEMPLATE_REGISTRY_SCHEMA}",
            )
        )
        return
    entry = registry.get("versions", {}).get(version) if isinstance(version, str) else None
    if not isinstance(entry, dict):
        diagnostics.append(
            Diagnostic("invalid_template_version", f"template_version {version!r} is not registered")
        )
        return
    relative = entry.get("path")
    expected = entry.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        diagnostics.append(
            Diagnostic("template_registry_invalid", f"template_version {version!r} has no path/digest binding")
        )
        return
    template_path = (root / relative).resolve()
    try:
        template_path.relative_to(root.resolve())
    except ValueError:
        diagnostics.append(
            Diagnostic("template_registry_invalid", f"template path escapes repository root: {relative}")
        )
        return
    if not template_path.is_file():
        diagnostics.append(
            Diagnostic("template_version_mismatch", f"registered template is missing: {relative}")
        )
    elif digest_bytes(template_path) != expected:
        diagnostics.append(
            Diagnostic(
                "template_version_mismatch",
                f"template_version {version} no longer matches its registered digest; increment the version",
            )
        )


def load_snapshot(root: Path, snapshot_id: str, explicit: Optional[Path], diagnostics: list[Diagnostic]) -> Optional[dict[str, Any]]:
    path = snapshot_path(root, snapshot_id, explicit)
    if path is None or not path.is_file():
        diagnostics.append(Diagnostic("provenance_snapshot_missing", f"catalog snapshot not found: {path}"))
        return None
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        diagnostics.append(Diagnostic("provenance_snapshot_invalid", f"unable to read catalog snapshot: {exc}"))
        return None
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        diagnostics.append(Diagnostic("provenance_snapshot_invalid", f"snapshot schema must be {SNAPSHOT_SCHEMA}"))
        return None
    if snapshot.get("snapshot_id") != snapshot_id:
        diagnostics.append(Diagnostic("provenance_snapshot_mismatch", "Plan snapshot id does not match artifact snapshot_id"))
    source = snapshot.get("source")
    files = source.get("files") if isinstance(source, dict) else None
    if not isinstance(files, list) or not isinstance(source.get("content_digest"), str):
        diagnostics.append(Diagnostic("provenance_snapshot_invalid", "snapshot source manifest and content_digest are required"))
    elif canonical_manifest_digest(files) != source["content_digest"]:
        diagnostics.append(Diagnostic("provenance_digest_mismatch", "snapshot content_digest does not match its manifest"))
    metadata_warnings = snapshot.get("metadata_warnings", [])
    if isinstance(metadata_warnings, list) and metadata_warnings:
        diagnostics.append(Diagnostic("snapshot_metadata_warning", f"snapshot contains {len(metadata_warnings)} metadata warning(s)", severity="warning"))
    return snapshot


def validate_snapshot_files(
    root: Path,
    snapshot: dict[str, Any],
    selected: list[tuple[str, int]],
    stale_review_text: str,
    diagnostics: list[Diagnostic],
) -> None:
    source = snapshot.get("source", {})
    files = {item.get("path"): item for item in source.get("files", []) if isinstance(item, dict)}
    catalog = snapshot.get("catalog", {})
    catalog_skills = {item.get("name"): item for item in catalog.get("skills", []) if isinstance(item, dict) and item.get("name")}
    warning_paths = {
        item.get("path")
        for item in snapshot.get("metadata_warnings", [])
        if isinstance(item, dict) and item.get("path")
    }
    checked: set[str] = set()
    for name, line in selected:
        skill = catalog_skills.get(name)
        if skill is None:
            diagnostics.append(Diagnostic("provenance_unverifiable", f"selected capability {name!r} is absent from the catalog snapshot", line))
            continue
        path = skill.get("path")
        if not isinstance(path, str) or path not in files:
            diagnostics.append(Diagnostic("provenance_incomplete", f"selected capability {name!r} has no source manifest entry", line))
            continue
        if path in warning_paths:
            diagnostics.append(Diagnostic("provenance_incomplete", f"selected capability {name!r} has snapshot metadata warnings", line))
        if path in checked:
            continue
        checked.add(path)
        manifest = files[path]
        current = root / path
        reviewed = "stale source reviewed" in stale_review_text.casefold() and (
            path.casefold() in stale_review_text.casefold()
            or "all catalog sources" in stale_review_text.casefold()
        )
        if not current.is_file():
            diagnostics.append(
                Diagnostic(
                    "provenance_stale_reviewed" if reviewed else "provenance_stale",
                    f"snapshot source file is missing: {path}",
                    severity="warning" if reviewed else "error",
                )
            )
        elif manifest.get("sha256") != digest_bytes(current):
            diagnostics.append(
                Diagnostic(
                    "provenance_stale_reviewed" if reviewed else "provenance_stale",
                    f"snapshot source file changed: {path}",
                    severity="warning" if reviewed else "error",
                )
            )


def section_body_lines(lines: list[str], section: dict[str, Any]) -> list[tuple[int, str]]:
    start = section["line"]
    end = next(
        (line_no for line_no in range(start + 1, len(lines) + 1) if re.match(r"^##\s+", lines[line_no - 1])),
        len(lines) + 1,
    )
    return [(line_no, lines[line_no - 1].strip()) for line_no in range(start + 1, end)]


def provenance_segments(value: Optional[str]) -> dict[str, str]:
    if not isinstance(value, str):
        return {}
    return {
        match.group(1).casefold(): match.group(2).strip()
        for match in PROVENANCE_CLASS_RE.finditer(value)
    }


def reference_mappings(segment: Optional[str]) -> list[tuple[str, str]]:
    """Parse one class-scoped ``subject -> source`` mapping list.

    Subjects are kept as complete tokens.  Substring checks are unsafe here:
    ``zj-discuss-view`` must never satisfy a required mapping for
    ``zj-discuss``, and ``Step 10`` must not satisfy ``Step 1``.
    """

    if not isinstance(segment, str) or not meaningful(segment) or is_explicit_none(segment):
        return []
    mappings: list[tuple[str, str]] = []
    for entry in segment.split("|"):
        subject, separator, source = entry.partition("->")
        if not separator:
            continue
        subject = clean_value(subject)
        source = clean_value(source)
        if meaningful(subject) and meaningful(source):
            mappings.append((subject.casefold(), source))
    return mappings


def mapped_reference(segment: Optional[str], needle: Optional[str] = None) -> bool:
    mappings = reference_mappings(segment)
    if needle is None:
        return bool(mappings)
    expected = clean_value(needle).casefold()
    return any(subject == expected for subject, _source in mappings)


def gap_protocol_lines(
    lines: list[str], sections: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Return exact unresolved-gap and bounded-suggestion protocol lines."""

    gaps_section = sections.get("Gaps and suggestions")
    gap_lines: list[str] = []
    suggestion_lines: list[str] = []
    if gaps_section:
        for _, value in section_body_lines(lines, gaps_section):
            if GAP_RE.fullmatch(value):
                gap_lines.append(value)
            elif SUGGESTION_RE.fullmatch(value):
                suggestion_lines.append(value)
    return gap_lines, suggestion_lines


def validate_provenance_classes(
    lines: list[str],
    sections: dict[str, dict[str, Any]],
    selected: list[tuple[str, int]],
    references: Optional[str],
    references_line: Optional[int],
    diagnostics: list[Diagnostic],
) -> None:
    """Require class-scoped source mappings for every represented capability kind."""

    segments = provenance_segments(references)
    selected_segment = segments.get("selected")
    for skill, line in selected:
        if not mapped_reference(selected_segment, skill):
            diagnostics.append(
                Diagnostic(
                    "provenance_incomplete_selected",
                    f"selected capability {skill!r} needs a selected=[capability -> source] mapping",
                    references_line or line,
                )
            )

    excluded_steps = [
        step["number"]
        for step in sections.get("Capability composition", {}).get("steps", [])
        if meaningful(step.get("fields", {}).get("excluded_alternatives", (None, None))[0])
        and not is_explicit_none(step.get("fields", {}).get("excluded_alternatives", ("", None))[0])
    ]
    excluded_segment = segments.get("excluded")
    for number in excluded_steps:
        if not mapped_reference(excluded_segment, f"Step {number}"):
            diagnostics.append(
                Diagnostic(
                    "provenance_incomplete_excluded",
                    f"Step {number} excluded alternatives need an excluded=[Step {number} -> source] mapping",
                    references_line,
                )
            )

    gap_lines, suggestion_lines = gap_protocol_lines(lines, sections)
    for value in suggestion_lines:
        if not mapped_reference(segments.get("suggested"), value):
            diagnostics.append(
                Diagnostic(
                    "provenance_incomplete_suggested",
                    "suggested capability needs a suggested=[suggestion -> source] mapping",
                    references_line,
                )
            )
    for value in gap_lines:
        if not mapped_reference(segments.get("gap"), value):
            diagnostics.append(
                Diagnostic(
                    "provenance_incomplete_gap",
                    "required-skill gap needs a gap=[required skill line -> source] mapping",
                    references_line,
                )
            )


def validate_text_gates(lines: list[str], sections: dict[str, dict[str, Any]], diagnostics: list[Diagnostic]) -> None:
    gaps = sections.get("Gaps and suggestions")
    if gaps:
        start = gaps["line"]
        section_lines = lines[start:]
        next_h2 = next((i for i, line in enumerate(section_lines, start + 1) if re.match(r"^##\s+", line)), len(lines) + 1)
        for line_no in range(start + 1, next_h2):
            text = lines[line_no - 1].strip()
            if not text:
                continue
            if GAP_RE.fullmatch(text):
                continue
            if GAP_LIKE_RE.search(text):
                diagnostics.append(Diagnostic("malformed_gap", "unresolved gaps must use exactly 'required skill：...' on one line", line_no))

    for line_no, line in enumerate(lines, 1):
        for category, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                diagnostics.append(Diagnostic(category, "secret-shaped value must not appear in a Plan", line_no))
        if AUTHORITY_BYPASS.search(line):
            diagnostics.append(Diagnostic("authority_bypass", "Plan text bypasses Human approval or authority", line_no))

    checkpoint = sections.get("Human checkpoints", {})
    approval, approval_line = field_value(checkpoint, "approval_point")
    authorization, authorization_line = field_value(checkpoint, "side_effect_authorization")
    approval_text = (approval or "").casefold()
    authorization_text = (authorization or "").casefold()
    if meaningful(approval) and not re.search(r"human|approval|approve|review|人工|审批|审阅", approval_text):
        diagnostics.append(Diagnostic("missing_human_checkpoint", "approval_point must name a Human approval or review", approval_line))
    if meaningful(authorization) and not re.search(r"human|approval|approve|review|人工|审批|审阅", authorization_text):
        diagnostics.append(Diagnostic("missing_human_checkpoint", "side_effect_authorization must name a Human gate", authorization_line))
    if re.search(r"automatic|automatically|无需审批|无须审批|without approval", authorization_text):
        diagnostics.append(Diagnostic("authority_bypass", "side_effect_authorization cannot authorize automatic or approval-free action", authorization_line))

    for section_name in ("Intent", "Capability composition", "Handoff"):
        section = sections.get(section_name)
        if not section:
            continue
        values = []
        if section_name == "Capability composition":
            values = [
                (value, line)
                for step in section.get("steps", [])
                for value, line in step.get("fields", {}).values()
            ]
        else:
            values = list(section.get("fields", {}).values())
        for value, line in values:
            if not isinstance(value, str):
                continue
            direct = DIRECT_SIDE_EFFECT.search(value)
            if (
                (AFFIRMATIVE_SIDE_EFFECT.search(value) or (direct and not negated(value, direct.start())))
                and not re.search(r"human|approval|approve|review|授权|审批", value, re.IGNORECASE)
            ):
                category = "unapproved_side_effect" if direct else "undeclared_side_effect"
                diagnostics.append(Diagnostic(category, "side-effect-capable text lacks an explicit Human gate", line))

    boundary, boundary_line = field_value(sections.get("Intent", {}), "permission_boundary")
    if meaningful(boundary):
        boundary_denies_list = re.search(
            r"(?:\bno\b|\bwithout\b|禁止|不得)[^.;\n]{0,160}"
            r"(?:write|network|publish|credential|secret|irreversible|delete|install|execute|modify)",
            boundary,
            re.IGNORECASE,
        )
        if not boundary_denies_list:
            for match in SIDE_EFFECT_TERMS.finditer(boundary):
                if not negated(boundary, match.start()):
                    diagnostics.append(Diagnostic("unapproved_side_effect", "permission_boundary must explicitly deny or Human-gate side effects", boundary_line))
                    break
    authority, authority_line = field_value(sections.get("Handoff", {}), "authority_statement")
    if meaningful(authority) and not re.search(r"composer.{0,40}(?:no|without).{0,20}(?:execution|authority)|无执行权|没有执行权", authority, re.IGNORECASE):
        diagnostics.append(Diagnostic("authority_bypass", "authority_statement must preserve Composer's lack of execution authority", authority_line))

    for step in sections.get("Capability composition", {}).get("steps", []):
        fields = step.get("fields", {})
        alternatives, alternatives_line = fields.get("excluded_alternatives", (None, None))
        if isinstance(alternatives, str) and CONFLICT_MARKER.search(alternatives):
            diagnostics.append(
                Diagnostic(
                    "unresolved_conflict",
                    f"Step {step['number']} retains conflicting alternatives and requires a Human choice",
                    alternatives_line,
                )
            )
        prerequisites = fields.get("prerequisites")
        dependencies = fields.get("dependencies")
        for field_name, item in (("prerequisites", prerequisites), ("dependencies", dependencies)):
            if item is None:
                continue
            value, line = item
            lower = value.casefold()
            unresolved_terms = ("missing", "unresolved", "unmet", "unknown", "tbd", "待定", "未知", "缺少")
            if any(term in lower for term in unresolved_terms):
                category = "unresolved_prerequisite" if field_name == "prerequisites" else "dependency_contradiction"
                diagnostics.append(Diagnostic(category, f"Step {step['number']} has an unresolved {field_name} declaration", line))
            if ("none" in lower or "no " in lower) and re.search(r"depend|require|prerequisite", lower) and not is_explicit_none(value):
                diagnostics.append(Diagnostic("dependency_contradiction", f"Step {step['number']} {field_name} contradicts itself", line))
            for ref in STEP_REF_RE.findall(value):
                number = int(ref)
                if field_name == "dependencies" and (number >= step["number"] or number < 1):
                    diagnostics.append(Diagnostic("dependency_contradiction", f"Step {step['number']} references an invalid dependency on Step {number}", line))
    step_count = len(sections.get("Capability composition", {}).get("steps", []))
    # Dependency references to a non-existent later step are contradictions.
    for step in sections.get("Capability composition", {}).get("steps", []):
        value, line = step.get("fields", {}).get("dependencies", ("", None))
        for ref in STEP_REF_RE.findall(value):
            if int(ref) > step_count:
                diagnostics.append(Diagnostic("dependency_contradiction", f"dependency references missing Step {ref}", line))

    steps = sections.get("Capability composition", {}).get("steps", [])
    side_effect_step = any(
        any(isinstance(value, str) and SIDE_EFFECT_TERMS.search(value) and not negated(value, SIDE_EFFECT_TERMS.search(value).start()) for value, _ in step.get("fields", {}).values())
        for step in steps
    )
    if side_effect_step and not (re.search(r"human|approval|approve|review|人工|审批|审阅", approval_text) and re.search(r"human|approval|approve|review|人工|审批|审阅", authorization_text)):
        diagnostics.append(Diagnostic("missing_human_checkpoint", "side-effect-capable steps require approval_point and side_effect_authorization Human gates", approval_line or authorization_line))


def validate_plan(path: Path, root: Path, explicit_snapshot: Optional[Path]) -> dict[str, Any]:
    text, lines, diagnostics = read_plan(path)
    sections, headings = parse_sections(lines, diagnostics)
    for section, fields in (
        ("Identity", IDENTITY_FIELDS),
        ("Intent", INTENT_FIELDS),
        ("Human checkpoints", CHECKPOINT_FIELDS),
        ("Evidence and provenance", PROVENANCE_FIELDS),
        ("Verification", VERIFICATION_FIELDS),
        ("Failure and rollback", FAILURE_FIELDS),
        ("Handoff", HANDOFF_FIELDS),
    ):
        add_required_fields(sections, section, fields, diagnostics)

    identity = sections.get("Identity", {})
    values = {name: field_value(identity, name)[0] for name in IDENTITY_FIELDS}
    if values.get("status") and values["status"] not in ALLOWED_STATUS:
        diagnostics.append(Diagnostic("invalid_status", f"status must be one of: {', '.join(sorted(ALLOWED_STATUS))}", field_value(identity, "status")[1]))
    if values.get("human_review") and values["human_review"] not in ALLOWED_REVIEW:
        diagnostics.append(Diagnostic("invalid_review_state", f"human_review must be one of: {', '.join(sorted(ALLOWED_REVIEW))}", field_value(identity, "human_review")[1]))
    template = values.get("template_version")
    validate_template_pin(root, template, diagnostics)
    if values.get("generated_at") and not ISO_RE.match(values["generated_at"]):
        diagnostics.append(Diagnostic("invalid_generated_at", "generated_at must be an ISO-8601 timestamp", field_value(identity, "generated_at")[1]))
    elif values.get("generated_at"):
        try:
            datetime.fromisoformat(values["generated_at"].replace("Z", "+00:00"))
        except ValueError:
            diagnostics.append(Diagnostic("invalid_generated_at", "generated_at must be an ISO-8601 timestamp", field_value(identity, "generated_at")[1]))
    if values.get("plan_id") and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]+", values["plan_id"]):
        diagnostics.append(Diagnostic("invalid_plan_id", "plan_id must be a stable slug", field_value(identity, "plan_id")[1]))
    if values.get("status") == "approved" and values.get("human_review") != "approved":
        diagnostics.append(Diagnostic("review_state_mismatch", "approved Plan must have human_review: approved", field_value(identity, "human_review")[1]))
    if values.get("status") == "rejected" and values.get("human_review") != "rejected":
        diagnostics.append(Diagnostic("review_state_mismatch", "rejected Plan must have human_review: rejected", field_value(identity, "human_review")[1]))
    if values.get("status") == "rejected":
        rejection_path, rejection_line = field_value(sections.get("Human checkpoints", {}), "rejection_path")
        if not isinstance(rejection_path, str) or not re.search(
            r"(?:because\s+\S|reason\s*[:=]\s*\S|原因\s*[:：]\s*\S)",
            rejection_path,
            re.IGNORECASE,
        ):
            diagnostics.append(
                Diagnostic(
                    "missing_rejection_reason",
                    "rejected Plan must preserve a concrete because/reason in rejection_path",
                    rejection_line,
                )
            )

    steps = sections.get("Capability composition", {}).get("steps", [])
    numbers = [step["number"] for step in steps]
    if numbers != list(range(1, len(numbers) + 1)):
        diagnostics.append(Diagnostic("step_order", "capability steps must be numbered sequentially from 1"))
    selected: list[tuple[str, int]] = []
    for step in steps:
        for field in STEP_FIELDS:
            value, line = step.get("fields", {}).get(field, (None, None))
            explicit_empty_assessment = field in {"prerequisites", "dependencies"} and isinstance(value, str) and is_explicit_none(value)
            if not meaningful(value) and not explicit_empty_assessment:
                diagnostics.append(Diagnostic("missing_capability_field", f"Step {step['number']}.{field} must be a non-placeholder value", line or step["line"]))
        skill, line = step.get("fields", {}).get("skill_or_workflow", (None, None))
        reason, reason_line = step.get("fields", {}).get("reason", (None, None))
        if meaningful(skill):
            selected.append((skill.strip().strip("`"), line or step["line"]))
        if meaningful(reason) and len(reason.strip()) < 8:
            diagnostics.append(Diagnostic("weak_selection_reason", f"Step {step['number']} reason must explain an input or acceptance requirement", reason_line))
        if meaningful(reason) and not re.search(
            r"input|output|requirement|acceptance|evidence|goal|constraint|because|需要|验收|证据|目标|约束",
            reason,
            re.IGNORECASE,
        ):
            diagnostics.append(Diagnostic("weak_selection_reason", f"Step {step['number']} reason must tie to an input or acceptance requirement", reason_line))

    provenance = sections.get("Evidence and provenance", {})
    snapshot_id, snapshot_line = field_value(provenance, "skill_index_snapshot")
    digest, digest_line = field_value(provenance, "catalog_revision_or_digest")
    references, references_line = field_value(provenance, "source_references")
    unknowns, _ = field_value(provenance, "unknowns")
    stale_review_text = ""
    if values.get("status") == "approved" and values.get("human_review") == "approved":
        stale_review_text = unknowns or ""
    snapshot = None
    if meaningful(snapshot_id):
        snapshot = load_snapshot(root, snapshot_id.strip("`"), explicit_snapshot, diagnostics)
        if snapshot is not None:
            source_digest = snapshot.get("source", {}).get("content_digest")
            if meaningful(digest) and digest.strip("`") != source_digest:
                diagnostics.append(Diagnostic("provenance_digest_mismatch", "catalog_revision_or_digest must equal snapshot source.content_digest", digest_line))
            validate_snapshot_files(root, snapshot, selected, stale_review_text, diagnostics)

    validate_provenance_classes(
        lines,
        sections,
        selected,
        references,
        references_line,
        diagnostics,
    )

    acceptance, acceptance_line = field_value(sections.get("Verification", {}), "plan_acceptance")
    if meaningful(acceptance) and acceptance not in ALLOWED_ACCEPTANCE:
        diagnostics.append(Diagnostic("invalid_acceptance_state", f"plan_acceptance must be one of: {', '.join(sorted(ALLOWED_ACCEPTANCE))}", acceptance_line))
    validate_text_gates(lines, sections, diagnostics)

    # Keep the machine output stable even when a malformed Plan emits several
    # diagnostics for the same line.
    diagnostics = sorted(
        {(
            item.severity,
            item.category,
            item.line,
            item.message,
        ): item for item in diagnostics}.values(),
        key=lambda item: (0 if item.severity == "error" else 1, item.category, item.line or 0, item.message),
    )
    errors = [item for item in diagnostics if item.severity == "error"]
    warnings = [item for item in diagnostics if item.severity == "warning"]
    handoff_reasons: list[str] = []
    if errors:
        handoff_reasons.append("validation_errors")
    if values.get("status") != "approved":
        handoff_reasons.append("status_not_approved")
    if values.get("human_review") != "approved":
        handoff_reasons.append("human_review_not_approved")
    if acceptance != "passed":
        handoff_reasons.append("plan_acceptance_not_passed")
    gap_lines, suggestion_lines = gap_protocol_lines(lines, sections)
    if not steps and gap_lines and not suggestion_lines:
        # A required-skill-only Plan is a useful, valid planning artifact, but
        # there is no executable capability to hand off.
        handoff_reasons.append("no_matching_capability")
    return {
        "schema": PLAN_SCHEMA,
        "valid": not errors,
        "plan": {
            "path": str(path),
            "plan_id": values.get("plan_id"),
            "status": values.get("status"),
            "template_version": values.get("template_version"),
            "snapshot_id": snapshot_id,
            "capability_steps": len(steps),
        },
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "categories": sorted({item.category for item in diagnostics}),
        },
        "handoff": {
            "eligible": not handoff_reasons,
            "reasons": handoff_reasons,
        },
        "diagnostics": [item.as_dict() for item in diagnostics],
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an external Composer Plan Markdown artifact.")
    parser.add_argument("plan", type=Path, help="Plan Markdown path")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4], help="ZAgentic repository root")
    parser.add_argument("--snapshot", type=Path, help="Explicit catalog snapshot JSON path")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    result = validate_plan(args.plan.resolve(), args.root.resolve(), args.snapshot)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

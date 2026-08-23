#!/usr/bin/env python3
"""Build and read immutable, evidence-linked Architecture Study bundles."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import repository_map


MANIFEST_SCHEMA = "zj-architecture-study-manifest/v1"
SCOPE_SCHEMA = "zj-architecture-study-scope/v1"
FOLLOWUP_SCHEMA = "zj-architecture-study-followups/v1"
RECORD_KINDS = {"observed", "inferred", "unknown", "decision"}
DEFAULT_MAX_FILES = 120
DEFAULT_MAX_BYTES = 2_000_000

SYMBOL_PATTERNS = (
    ("module", re.compile(r"^\s*(?:class|def|function|interface|type|export\s+(?:class|function|interface|const))\b")),
    ("entrypoint", re.compile(r"\b(?:main|handler|route|router|server|app)\b|if\s+__name__\s*==")),
    ("persistence", re.compile(r"\b(?:sqlite|postgres|mysql|redis|database|repository|orm|prisma|sqlalchemy)\b", re.I)),
    ("execution", re.compile(r"\b(?:subprocess|child_process|exec|spawn|sandbox|docker|shell)\b", re.I)),
    ("extension", re.compile(r"\b(?:plugin|adapter|hook|registry|middleware|extension)\b", re.I)),
    ("dependency", re.compile(r"^\s*(?:import|from|use)\b|\b(?:require|import)\s*\(", re.I)),
)
IMPORT_PATTERNS = (
    re.compile(r"^\s*(?:from|import|use)\s+([A-Za-z0-9_./:@$-]+)"),
    re.compile(r"\b(?:from|require|import)\s*\(?\s*[\"']([^\"']+)[\"']"),
)


class StudyError(RuntimeError):
    """A user-actionable Architecture Study failure."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return repository_map.sha256_bytes(value)


def stable_id(identity: str, kind: str, path: str) -> str:
    return repository_map.stable_id(identity, kind, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StudyError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise StudyError(f"JSON object expected: {path}")
    return value


def jsonl(records: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as content:
        for line in content:
            if limit is not None and len(records) >= limit:
                break
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def safe_bundle_path(bundle: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise StudyError(f"bundle contains unsafe relative path: {value}")
    return bundle / path


def load_map(map_bundle: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        repository_map.validate_bundle(map_bundle)
    except repository_map.MapError as error:
        raise StudyError(f"Repository Map validation failed: {error}") from error
    bundle = map_bundle.resolve()
    manifest = read_json(bundle / "manifest.json")
    summary = read_json(bundle / "facts" / "summary.json")
    targets = read_json(bundle / "navigation" / "targets.json")
    return manifest, summary, targets


def current_source(repository: Path, output: Path, excluded: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    repository = repository.resolve()
    exclusions = repository_map.normalized_exclusions(repository, output.resolve(), excluded)
    tree, unknowns = repository_map.scan_tree(repository, exclusions)
    fingerprint = repository_map.source_fingerprint(tree)
    source = repository_map.git_source(repository, "HEAD") or {
        "repository": repository.name,
        "ref": None,
        "commit": None,
        "state": "unversioned",
        "statusEntries": None,
    }
    source["workingTreeFingerprint"] = fingerprint
    source["identity"] = "commit-plus-working-tree" if source["commit"] else "working-tree-fingerprint"
    return source, tree, unknowns


def verify_map_source(repository: Path, output: Path, map_manifest: dict[str, Any], map_summary: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    scope = map_summary.get("scope", {})
    excluded = [value for value in scope.get("exclusions", []) if isinstance(value, str)]
    source, tree, unknowns = current_source(repository, output, excluded)
    expected = map_manifest.get("source", {})
    if source.get("commit") != expected.get("commit") or source.get("workingTreeFingerprint") != expected.get("workingTreeFingerprint"):
        raise StudyError("repository no longer matches the pinned Repository Map commit/fingerprint")
    return source, tree, unknowns


def resolve_target_paths(repository: Path, requested: list[str], map_targets: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not requested:
        raise StudyError("at least one --target is required to keep the Architecture Study bounded")
    available = map_targets.get("targets", []) if map_targets else []
    by_id = {item.get("id"): item for item in available if isinstance(item, dict)}
    by_path = {item.get("path"): item for item in available if isinstance(item, dict)}
    selected: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for value in requested:
        candidate = by_id.get(value) or by_path.get(value)
        if candidate is not None:
            selected.append({key: candidate[key] for key in candidate if key in {"id", "kind", "path", "label", "reason"}})
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise StudyError(f"target must be a repository-relative path or map target ID: {value}")
        relative = path.as_posix() or "."
        if not (repository / path).exists():
            raise StudyError(f"target does not exist in repository: {value}")
        synthetic = {
            "id": f"target-{repository_map.sha256_bytes(relative.encode('utf-8'))[:20]}",
            "kind": "explicit-scope",
            "path": relative,
            "label": relative,
            "reason": "human-supplied scope converted to a study target",
        }
        selected.append(synthetic)
        decisions.append({
            "kind": "decision",
            "id": f"decision-{repository_map.sha256_bytes(('target:' + relative).encode('utf-8'))[:20]}",
            "decision": "explicit-target-conversion",
            "targetPath": relative,
            "reason": "the supplied path was converted to an equivalent navigation target",
        })
    unique = {item["id"]: item for item in selected}
    return list(sorted(unique.values(), key=lambda item: (item["path"], item["id"]))), decisions


def selected_files(repository: Path, tree: list[dict[str, Any]], targets: list[dict[str, Any]], max_files: int, max_bytes: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    target_paths = [Path(item["path"]) for item in targets]
    candidates = [
        item for item in tree
        if item.get("kind") == "file" and any(item["path"] == target.as_posix() or target.as_posix() == "." or target in Path(item["path"]).parents for target in target_paths)
    ]
    candidates.sort(key=lambda item: item["path"])
    unknowns: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    if len(candidates) > max_files:
        unknowns.append({"kind": "unknown", "id": "unknown-scope-file-limit", "category": "scope", "path": ".", "reason": f"{len(candidates) - max_files} selected files were outside max-files={max_files}"})
        decisions.append({"kind": "decision", "id": "decision-scope-file-limit", "decision": "bounded-file-selection", "reason": f"read the first {max_files} files in deterministic path order"})
        candidates = candidates[:max_files]
    selected: list[dict[str, Any]] = []
    total_bytes = 0
    for item in candidates:
        if total_bytes + int(item.get("size", 0)) > max_bytes and selected:
            unknowns.append({"kind": "unknown", "id": "unknown-scope-byte-limit", "category": "scope", "path": item["path"], "reason": f"remaining files exceeded max-bytes={max_bytes}"})
            decisions.append({"kind": "decision", "id": "decision-scope-byte-limit", "decision": "bounded-byte-selection", "reason": f"read selected files up to {max_bytes} bytes"})
            break
        selected.append(item)
        total_bytes += int(item.get("size", 0))
    return selected, unknowns, decisions


def line_evidence(identity: str, source: dict[str, Any], path: str, line_start: int, line_end: int, excerpt: str, file_hash: str, subject: str) -> dict[str, Any]:
    return {
        "kind": "observed",
        "id": stable_id(identity, "evidence", f"{path}:{line_start}:{subject}"),
        "subject": subject,
        "sourcePath": path,
        "commit": source.get("commit"),
        "workingTreeFingerprint": source.get("workingTreeFingerprint"),
        "lineStart": line_start,
        "lineEnd": line_end,
        "sha256": file_hash,
        "excerpt": excerpt[:240],
    }


def collect_records(repository: Path, source: dict[str, Any], files: list[dict[str, Any]], identity: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    category_evidence: dict[str, list[str]] = {}
    entrypoints: list[tuple[str, str]] = []
    for item in files:
        path = repository / item["path"]
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            readable = True
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
            readable = False
        lines = text.splitlines() or [""]
        file_record = line_evidence(identity, source, item["path"], 1, len(lines), " ".join(line.strip() for line in lines[:4] if line.strip()), item["sha256"], "file")
        file_record["textReadable"] = readable
        evidence.append(file_record)
        file_categories: dict[str, list[str]] = {}
        if not readable:
            category_evidence.setdefault("binary", []).append(file_record["id"])
        for line_number, line in enumerate(lines, start=1):
            for category, pattern in SYMBOL_PATTERNS:
                if not pattern.search(line):
                    continue
                record = line_evidence(identity, source, item["path"], line_number, line_number, line.strip(), item["sha256"], category)
                evidence.append(record)
                category_evidence.setdefault(category, []).append(record["id"])
                file_categories.setdefault(category, []).append(record["id"])
                if category == "entrypoint":
                    entrypoints.append((item["path"], record["id"]))
            for pattern in IMPORT_PATTERNS:
                match = pattern.search(line)
                if match:
                    reference = match.group(1)
                    dep_id = stable_id(identity, "evidence", f"{item['path']}:{line_number}:dependency")
                    if dep_id not in {record["id"] for record in evidence}:
                        evidence.append(line_evidence(identity, source, item["path"], line_number, line_number, line.strip(), item["sha256"], "dependency"))
                    relationships.append({
                        "kind": "observed",
                        "id": stable_id(identity, "relationship", f"{item['path']}:{line_number}:{reference}"),
                        "fromPath": item["path"],
                        "toReference": reference,
                        "relation": "imports-or-requires",
                        "evidenceIds": [dep_id],
                    })
                    break
        category = file_categories.get("module", [])
        if category:
            claims.append({
                "kind": "observed",
                "id": stable_id(identity, "claim", f"module:{item['path']}"),
                "claim": f"{item['path']} contains a declared module or interface symbol.",
                "critical": True,
                "evidenceIds": category[-1:],
                "sourcePath": item["path"],
            })
    evidence_ids = {record["id"] for record in evidence}
    for relation in relationships:
        relation["evidenceIds"] = [value for value in relation["evidenceIds"] if value in evidence_ids]
        claims.append({
            "kind": "inferred",
            "id": stable_id(identity, "claim", f"relation:{relation['id']}"),
            "claim": f"{relation['fromPath']} has a source-reference relationship to {relation['toReference']}.",
            "critical": False,
            "evidenceIds": relation["evidenceIds"],
            "sourcePath": relation["fromPath"],
        })
    return evidence, claims, relationships, [(path, evidence_id) for path, evidence_id in entrypoints]


def build_secondary_records(identity: str, source: dict[str, Any], targets: list[dict[str, Any]], files: list[dict[str, Any]], evidence: list[dict[str, Any]], claims: list[dict[str, Any]], relationships: list[dict[str, Any]], entrypoints: list[tuple[str, str]], inherited_unknowns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_by_subject: dict[str, list[str]] = {}
    for record in evidence:
        evidence_by_subject.setdefault(record["subject"], []).append(record["id"])
    unknowns = []
    for inherited in inherited_unknowns:
        unknowns.append({
            "kind": "unknown",
            "id": inherited.get("id") or stable_id(identity, "unknown", inherited.get("path", ".")),
            "category": inherited.get("category", inherited.get("kind", "scan")),
            "path": inherited.get("path", "."),
            "reason": inherited.get("reason", "source scan did not establish this path"),
        })
    for subject, label in (("persistence", "persistence"), ("execution", "execution-and-sandbox"), ("extension", "extensions-and-external-dependencies")):
        if not evidence_by_subject.get(subject):
            unknowns.append({"kind": "unknown", "id": stable_id(identity, "unknown", label), "category": label, "path": ".", "reason": f"the selected source does not establish {label} behavior"})
    if not evidence_by_subject.get("entrypoint"):
        unknowns.append({"kind": "unknown", "id": stable_id(identity, "unknown", "runtime-flow"), "category": "runtime-flow", "path": ".", "reason": "no entrypoint or handler was established in the selected source"})
    risks: list[dict[str, Any]] = []
    if evidence_by_subject.get("execution"):
        risks.append({"kind": "inferred", "id": stable_id(identity, "risk", "execution"), "risk": "execution-and-sandbox", "trigger": "selected code reaches process, shell, container, or sandbox primitives", "impact": "credentials, approvals, isolation, and recovery may be coupled to this path", "owner": "unknown", "evidenceIds": evidence_by_subject["execution"][:5]})
    if evidence_by_subject.get("persistence"):
        risks.append({"kind": "inferred", "id": stable_id(identity, "risk", "persistence"), "risk": "persistence-and-recovery", "trigger": "selected code reaches a persistence or database primitive", "impact": "data ownership, migration, consistency, and rollback need explicit review", "owner": "unknown", "evidenceIds": evidence_by_subject["persistence"][:5]})
    risks.append({"kind": "unknown", "id": stable_id(identity, "risk", "ownership"), "risk": "ownership", "trigger": "the selected scope crosses a module or integration seam", "impact": "maintenance and incident responsibility are not established by this pass", "owner": "unknown", "evidenceIds": []})
    flows: list[dict[str, Any]] = []
    for path, evidence_id in entrypoints:
        flows.append({"kind": "inferred", "id": stable_id(identity, "flow", path), "flow": "entrypoint-to-selected-module", "fromPath": path, "toPath": next((target["path"] for target in targets if target["path"] == "." or path == target["path"] or target["path"] in Path(path).parents), path), "evidenceIds": [evidence_id]})
    if not flows:
        flows.append({"kind": "unknown", "id": stable_id(identity, "flow", "unknown"), "flow": "runtime-flow", "fromPath": ".", "toPath": ".", "reason": "no selected entrypoint evidence"})
    diagrams = [{
        "kind": "inferred",
        "id": stable_id(identity, "diagram", "structure"),
        "diagramType": "structure",
        "nodes": [{"path": item["path"], "targetId": item["id"]} for item in targets],
        "edges": [{"fromPath": item["fromPath"], "toReference": item["toReference"], "evidenceIds": item["evidenceIds"]} for item in relationships[:40]],
        "evidenceIds": sorted({evidence_id for item in relationships[:40] for evidence_id in item["evidenceIds"]}),
    }]
    for target in targets:
        claims.append({
            "kind": "unknown",
            "id": stable_id(identity, "claim", f"owner:{target['path']}"),
            "claim": f"The owner of {target['path']} is not established by this study.",
            "critical": False,
            "evidenceIds": [],
            "sourcePath": target["path"],
        })
    return flows, claims, unknowns, risks, diagrams, []


def render_markdown(scope: dict[str, Any], claims: list[dict[str, Any]], relationships: list[dict[str, Any]], flows: list[dict[str, Any]], risks: list[dict[str, Any]], unknowns: list[dict[str, Any]], followups: list[dict[str, Any]], limit: int) -> str:
    source = scope["source"]
    lines = [
        f"# Architecture Study: {source['repository']}",
        "",
        f"- Snapshot: `{scope['snapshotId']}`",
        f"- Commit: `{source.get('commit') or 'unknown'}`",
        f"- Map snapshot: `{scope['mapBinding'].get('snapshotId') or 'none'}`",
        "",
        "## Selected scope",
        "",
    ]
    lines.extend(f"- `{target['path']}` — {target['reason']}" for target in scope["targets"][:limit])
    for title, records, formatter in (
        ("Claims", claims, lambda item: f"`{item['kind']}` {item['claim']}"),
        ("Relationships", relationships, lambda item: f"`{item['fromPath']}` → `{item['toReference']}` ({item['relation']})"),
        ("Runtime flows", flows, lambda item: f"`{item['fromPath']}` → `{item['toPath']}` ({item['flow']})"),
        ("Risks", risks, lambda item: f"{item.get('risk', 'unknown')}: {item.get('impact', item.get('reason', ''))}"),
        ("Unknowns", unknowns, lambda item: f"{item.get('category', 'unknown')}: {item.get('reason', '')}"),
        ("Follow-up targets", followups, lambda item: f"`{item['path']}` — {item['reason']}"),
    ):
        lines.extend(["", f"## {title}", ""])
        if records:
            lines.extend(f"- {formatter(item)}" for item in records[:limit])
        else:
            lines.append("- None recorded.")
    lines.extend(["", "> This study is descriptive; solution selection belongs to zj-tech-research-report.", ""])
    return "\n".join(lines)


def render_html(scope: dict[str, Any], claims: list[dict[str, Any]], relationships: list[dict[str, Any]], flows: list[dict[str, Any]], risks: list[dict[str, Any]], unknowns: list[dict[str, Any]], followups: list[dict[str, Any]], limit: int) -> str:
    markdown = render_markdown(scope, claims, relationships, flows, risks, unknowns, followups, limit)
    output = ["<!doctype html>", '<html lang="en"><meta charset="utf-8"><title>Architecture Study</title><body>']
    for line in markdown.splitlines():
        if line.startswith("# "):
            output.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            output.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            output.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.startswith("> "):
            output.append(f"<p><em>{html.escape(line[2:])}</em></p>")
        elif line:
            output.append(f"<p>{html.escape(line)}</p>")
    output.append("</body></html>\n")
    return "\n".join(output)


def write_bundle(repository: Path, bundle: Path, files: dict[str, str]) -> None:
    repository_map.write_bundle(repository, bundle, files)


def build_study(repository: Path, bundle: Path, map_bundle: Path | None, requested_targets: list[str], extra_excludes: list[str], max_files: int, max_bytes: int, view_limit: int) -> dict[str, Any]:
    repository = repository.resolve()
    bundle = bundle.resolve()
    if bundle.exists():
        raise StudyError(f"study bundle already exists and is immutable: {bundle}")
    map_manifest: dict[str, Any] | None = None
    map_summary: dict[str, Any] | None = None
    map_targets: dict[str, Any] | None = None
    map_manifest_hash: str | None = None
    if map_bundle is not None:
        map_manifest, map_summary, map_targets = load_map(map_bundle)
        map_manifest_hash = sha256_bytes((map_bundle.resolve() / "manifest.json").read_bytes())
        source, tree, scan_unknowns = verify_map_source(repository, bundle, map_manifest, map_summary)
    else:
        source, tree, scan_unknowns = current_source(repository, bundle, extra_excludes)
    targets, target_decisions = resolve_target_paths(repository, requested_targets, map_targets)
    files, selection_unknowns, selection_decisions = selected_files(repository, tree, targets, max_files, max_bytes)
    identity = source["commit"] or source["workingTreeFingerprint"]
    evidence, claims, relationships, entrypoints = collect_records(repository, source, files, identity)
    flows, secondary_claims, unknowns, risks, diagrams, _ = build_secondary_records(identity, source, targets, files, evidence, claims, relationships, entrypoints, scan_unknowns + selection_unknowns)
    claims.extend(secondary_claims)
    decisions = target_decisions + selection_decisions
    if map_bundle is None:
        decisions.append({"kind": "decision", "id": "decision-no-map", "decision": "direct-study-without-map", "reason": "no Repository Map was supplied; explicit scope was converted to equivalent targets"})
    map_exclusions = map_summary.get("scope", {}).get("exclusions", []) if map_summary else [".git"]
    study_exclusions = list(dict.fromkeys([value for value in map_exclusions + extra_excludes if isinstance(value, str)]))
    followups = []
    if map_targets is not None:
        selected_ids = {target["id"] for target in targets}
        followups = [
            {"kind": "decision", "id": stable_id(identity, "followup", target["id"]), "targetKind": target["kind"], "path": target["path"], "label": target["label"], "reason": "map target not selected for this bounded study"}
            for target in map_targets.get("targets", [])
            if target.get("id") not in selected_ids
        ]
    scope = {
        "schema": SCOPE_SCHEMA,
        "snapshotId": "pending",
        "source": source,
        "targets": targets,
        "exclusions": study_exclusions,
        "mapBinding": {"used": map_bundle is not None, "snapshotId": map_manifest.get("snapshotId") if map_manifest else None, "manifestSha256": map_manifest_hash, "targetIds": [target["id"] for target in targets]},
        "decisions": decisions,
    }
    digest = hashlib.sha256()
    for value in (source, targets, decisions, evidence, relationships, flows, claims, unknowns, risks, diagrams, followups):
        digest.update(canonical_json(value))
    snapshot_id = f"study-{digest.hexdigest()[:24]}"
    scope["snapshotId"] = snapshot_id
    followup_document = {"schema": FOLLOWUP_SCHEMA, "snapshotId": snapshot_id, "targets": followups}
    markdown = render_markdown(scope, claims, relationships, flows, risks, unknowns, followups, view_limit)
    html_view = render_html(scope, claims, relationships, flows, risks, unknowns, followups, view_limit)
    files_to_write = {
        "facts/scope.json": json.dumps(scope, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "facts/evidence.jsonl": jsonl(evidence),
        "facts/relationships.jsonl": jsonl(relationships),
        "facts/flows.jsonl": jsonl(flows),
        "facts/claims.jsonl": jsonl(claims),
        "facts/unknowns.jsonl": jsonl(unknowns),
        "facts/risks.jsonl": jsonl(risks),
        "facts/diagrams.jsonl": jsonl(diagrams),
        "navigation/follow-up-targets.json": json.dumps(followup_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "views/study.md": markdown,
        "views/study.html": html_view,
    }
    artifacts = []
    views = []
    for name in sorted(files_to_write):
        encoded = files_to_write[name].encode("utf-8")
        metadata = {"path": name, "sha256": sha256_bytes(encoded), "bytes": len(encoded)}
        (views if name.startswith("views/") else artifacts).append(metadata)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "kind": "architecture-study",
        "snapshotId": snapshot_id,
        "source": source,
        "mapBinding": scope["mapBinding"],
        "scope": {"path": "facts/scope.json", "targetCount": len(targets)},
        "recordKinds": sorted(RECORD_KINDS),
        "shards": artifacts,
        "views": {"defaultLimit": view_limit, "artifacts": views},
        "immutable": True,
    }
    files_to_write["manifest.json"] = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    write_bundle(repository, bundle, files_to_write)
    return manifest


def validate_study(bundle: Path) -> dict[str, Any]:
    bundle = bundle.resolve()
    manifest = read_json(bundle / "manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("kind") != "architecture-study" or manifest.get("immutable") is not True:
        raise StudyError("unsupported Architecture Study manifest")
    snapshot_id = manifest.get("snapshotId")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("study-"):
        raise StudyError("manifest has an invalid study snapshotId")
    artifacts = manifest.get("shards", []) + manifest.get("views", {}).get("artifacts", [])
    checked = 0
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise StudyError("manifest contains an invalid artifact entry")
        path = safe_bundle_path(bundle, item["path"])
        if not path.is_file() or sha256_bytes(path.read_bytes()) != item["sha256"]:
            raise StudyError(f"artifact is missing or has a hash mismatch: {path}")
        checked += 1
    scope = read_json(bundle / "facts" / "scope.json")
    if scope.get("schema") != SCOPE_SCHEMA or scope.get("snapshotId") != snapshot_id:
        raise StudyError("scope does not match the manifest")
    map_binding = scope.get("mapBinding", {})
    for decision in scope.get("decisions", []):
        if decision.get("kind") not in RECORD_KINDS:
            raise StudyError("scope decision has an invalid record kind")
    if map_binding.get("used") is False and not any(item.get("decision") == "direct-study-without-map" for item in scope.get("decisions", [])):
        raise StudyError("direct study must record why no Repository Map was used")
    if map_binding.get("used") is True and not map_binding.get("snapshotId"):
        raise StudyError("map-bound study has no map snapshot ID")
    evidence = read_jsonl(bundle / "facts" / "evidence.jsonl")
    evidence_ids = {item.get("id") for item in evidence}
    for record in evidence:
        if record.get("kind") != "observed" or not isinstance(record.get("sourcePath"), str) or int(record.get("lineStart", 0)) < 1 or int(record.get("lineEnd", 0)) < int(record.get("lineStart", 0)):
            raise StudyError("evidence record is missing observed source coordinates")
    record_counts: dict[str, int] = {}
    for name in ("relationships", "flows", "claims", "unknowns", "risks", "diagrams"):
        records = read_jsonl(bundle / "facts" / f"{name}.jsonl")
        record_counts[name] = len(records)
        for record in records:
            if record.get("kind") not in RECORD_KINDS:
                raise StudyError(f"{name} record has an invalid kind")
            for evidence_id in record.get("evidenceIds", []):
                if evidence_id not in evidence_ids:
                    raise StudyError(f"{name} record references missing evidence: {evidence_id}")
            if name == "claims" and record.get("critical") is True and not record.get("evidenceIds"):
                raise StudyError("critical claim has no evidence IDs")
    followups = read_json(bundle / "navigation" / "follow-up-targets.json")
    if followups.get("schema") != FOLLOWUP_SCHEMA or followups.get("snapshotId") != snapshot_id:
        raise StudyError("follow-up targets do not match the manifest")
    for target in followups.get("targets", []):
        if target.get("kind") not in RECORD_KINDS:
            raise StudyError("follow-up target has an invalid record kind")
    return {"valid": True, "schema": MANIFEST_SCHEMA, "snapshotId": snapshot_id, "artifactsChecked": checked, "evidenceCount": len(evidence), "records": record_counts}


def view_study(bundle: Path, section: str, limit: int, output_format: str) -> str:
    scope = read_json(bundle / "facts" / "scope.json")
    sections = {
        "claims": "claims",
        "relationships": "relationships",
        "flows": "flows",
        "risks": "risks",
        "unknowns": "unknowns",
        "evidence": "evidence",
    }
    records = read_jsonl(bundle / "facts" / f"{sections[section]}.jsonl", limit) if section != "scope" else []
    if section == "scope":
        lines = [f"# Architecture Study: {scope['source']['repository']}", "", "## Selected scope", ""]
        lines.extend(f"- `{item['path']}` — {item['reason']}" for item in scope["targets"][:limit])
        result = "\n".join(lines) + "\n"
    else:
        lines = [f"# Architecture Study: {scope['source']['repository']}", "", f"## {section.title()}", ""]
        lines.extend(f"- `{item.get('kind')}` {item.get('claim', item.get('reason', item.get('path', item.get('id', ''))))}" for item in records)
        result = "\n".join(lines) + "\n"
    if output_format == "html":
        return "<!doctype html><html><meta charset=\"utf-8\"><body><pre>" + html.escape(result) + "</pre></body></html>\n"
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Build and inspect Architecture Study bundles")
    commands = root.add_subparsers(dest="command", required=True)
    study = commands.add_parser("study", help="study selected repository paths")
    study.add_argument("repository", type=Path)
    study.add_argument("bundle", type=Path)
    study.add_argument("--map", dest="map_bundle", type=Path)
    study.add_argument("--target", action="append", required=True)
    study.add_argument("--exclude", action="append", default=[])
    study.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    study.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    study.add_argument("--view-limit", type=int, default=100)
    validate = commands.add_parser("validate", help="validate a study bundle")
    validate.add_argument("bundle", type=Path)
    view = commands.add_parser("view", help="render a bounded study view")
    view.add_argument("bundle", type=Path)
    view.add_argument("--section", choices=("scope", "claims", "relationships", "flows", "risks", "unknowns", "evidence"), default="scope")
    view.add_argument("--limit", type=int, default=100)
    view.add_argument("--format", choices=("markdown", "html"), default="markdown")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    for name in ("limit", "view_limit", "max_files", "max_bytes"):
        if hasattr(args, name) and getattr(args, name) <= 0:
            raise StudyError(f"{name} must be positive")
    if args.command == "study":
        manifest = build_study(args.repository, args.bundle, args.map_bundle, args.target, args.exclude, args.max_files, args.max_bytes, args.view_limit)
        print(json.dumps({"created": True, "bundle": str(args.bundle.resolve()), "snapshotId": manifest["snapshotId"]}, ensure_ascii=False))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_study(args.bundle), ensure_ascii=False))
        return 0
    output = view_study(args.bundle.resolve(), args.section, args.limit, args.format)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (StudyError, repository_map.MapError, OSError, json.JSONDecodeError) as error:
        print(f"architecture study: {error}", file=sys.stderr)
        raise SystemExit(1)

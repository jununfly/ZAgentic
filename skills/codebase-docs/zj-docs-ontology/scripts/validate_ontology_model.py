#!/usr/bin/env python3
"""Validate a per-repository ontology model instance against the meta-schema.

Module D (issue #275 continuation, amended 2026-11-20): this skill owns the
meta-schema (``references/ontology-meta-schema.json``); each repository
instantiates its own model with its own entity types and vocabulary. The
validator reads the meta-schema as the single source of the required-field
contract.

Structural integrity is a fact — an id used twice, an attribute without its
owner, a relation endpoint that does not exist — so those are ERRORs.
Coverage is a navigation gap: a map-covered page the model does not decompose
yet is ``CONTENT_UNCOVERED``, a signal (declare the receipt; never delete the
page on this signal).

A page may also declare a ``model-elements`` frontmatter anchor mirroring its
receipt. When present, the anchor must match the receipt exactly; a mismatch is
``ANCHOR_RECEIPT_DRIFT``, a signal (the receipt is the source of truth: fix the
mirror, never delete the page). Missing anchors are tolerated — receipts may
precede the anchor rollout — and the two-way "no silent anchor deletion" guard
lives in the root regression suite that observes the anchors as public pages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import docs_governance as gov  # noqa: E402

DEFAULT_META_SCHEMA = SCRIPT_DIR.parent / "references" / "ontology-meta-schema.json"
MODEL_SCHEMA_VERSION = "ontology-model/v1"

ERROR_CODES = frozenset({
    "ONTOLOGY_MODEL_UNREADABLE",
    "ONTOLOGY_MODEL_SCHEMA_UNSUPPORTED",
    "ONTOLOGY_REQUIRED_FIELD_MISSING",
    "ONTOLOGY_ID_DUPLICATE",
    "ONTOLOGY_ATTRIBUTE_ORPHAN",
    "ONTOLOGY_RELATION_ENDPOINT_MISSING",
    "ONTOLOGY_RULE_TRACE_MISSING",
    "ONTOLOGY_PAGE_RECEIPT_BROKEN",
})
SIGNAL_CODES = frozenset({"CONTENT_UNCOVERED", "ANCHOR_RECEIPT_DRIFT"})

# frontmatter ``model-elements: [entity.x, rule.y]`` — parse the inline list.
ANCHOR_RE = __import__("re").compile(r"^model-elements:\s*\[([^\]]*)\]", __import__("re").M)


def declared_anchor(text: str) -> list[str] | None:
    """Return the page's declared model-elements, or None when absent.
    An empty/absent anchor is 'not declared yet' (tolerated); a declared list
    is checked against the receipt.
    """
    match = ANCHOR_RE.search(text)
    if not match:
        return None
    return [item.strip().strip("\"'") for item in match.group(1).split(",") if item.strip()]


def has_error(diagnostics: list[dict[str, str]]) -> bool:
    return any(d["code"] in ERROR_CODES for d in diagnostics)


def load_meta_schema(path: Path | None) -> tuple[dict | None, dict[str, str] | None]:
    schema_path = path or DEFAULT_META_SCHEMA
    try:
        return json.loads(schema_path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, {
            "code": "ONTOLOGY_MODEL_UNREADABLE",
            "path": str(schema_path),
            "message": f"meta-schema unreadable: {exc}",
        }


def validate(root: Path, model_path: Path, meta_path: Path | None = None) -> dict:
    diagnostics: list[dict[str, str]] = []
    meta_schema, meta_error = load_meta_schema(meta_path)
    if meta_error is not None:
        return {"model": str(model_path), "diagnostics": [meta_error]}
    assert meta_schema is not None

    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "model": str(model_path),
            "diagnostics": [{
                "code": "ONTOLOGY_MODEL_UNREADABLE",
                "path": str(model_path),
                "message": f"model unreadable: {exc}",
            }],
        }

    version = model.get("schema_version")
    if version != MODEL_SCHEMA_VERSION:
        diagnostics.append({
            "code": "ONTOLOGY_MODEL_SCHEMA_UNSUPPORTED",
            "path": str(model_path),
            "message": f"schema_version must be {MODEL_SCHEMA_VERSION}, got {version!r}",
        })

    # Required-field contract comes from the meta-schema file, never a
    # second hard-coded copy (single source, Ruling 2). Collection keys are
    # declared per class too — plural forms are not derivable in code.
    classes = meta_schema["classes"]
    items_by_class: dict[str, list[dict]] = {
        name: model.get(spec["collection"], []) or [] for name, spec in classes.items()
    }
    for name, required in classes.items():
        for item in items_by_class[name]:
            missing = [field for field in required["required"] if not item.get(field)]
            if missing:
                diagnostics.append({
                    "code": "ONTOLOGY_REQUIRED_FIELD_MISSING",
                    "path": str(model_path),
                    "message": f"{name} {item.get('id', '?')!r} missing required fields: {', '.join(missing)}",
                })

    # Identity is a fact: one id names one element across all classes.
    seen: dict[str, str] = {}
    entity_ids: set[str] = set()
    for name, items in items_by_class.items():
        for item in items:
            item_id = item.get("id")
            if item_id is None:
                continue
            if item_id in seen:
                diagnostics.append({
                    "code": "ONTOLOGY_ID_DUPLICATE",
                    "path": str(model_path),
                    "message": f"id {item_id!r} used by both {seen[item_id]} and {name}",
                })
                continue
            seen[item_id] = name
            if name == "entity":
                entity_ids.add(item_id)

    # Explicit declarations that do not match the model's own facts are ERRORs.
    for item in items_by_class["attribute"]:
        if item.get("owner") not in entity_ids:
            diagnostics.append({
                "code": "ONTOLOGY_ATTRIBUTE_ORPHAN",
                "path": str(model_path),
                "message": f"attribute {item.get('id', '?')!r} owner {item.get('owner')!r} is not an entity id",
            })
    for item in items_by_class["relation"]:
        for endpoint in ("from", "to"):
            if item.get(endpoint) not in entity_ids:
                diagnostics.append({
                    "code": "ONTOLOGY_RELATION_ENDPOINT_MISSING",
                    "path": str(model_path),
                    "message": f"relation {item.get('id', '?')!r} {endpoint} {item.get(endpoint)!r} is not an entity id",
                })
    for item in items_by_class["rule"]:
        for trace in item.get("traces", []) or []:
            candidate = (root / str(trace)).resolve()
            if not candidate.is_file():
                diagnostics.append({
                    "code": "ONTOLOGY_RULE_TRACE_MISSING",
                    "path": str(model_path),
                    "message": f"rule {item.get('id', '?')!r} trace does not resolve to a page: {trace}",
                })

    # Page receipts: the decomposition mapping per page.
    receipt_paths: set[str] = set()
    receipt_spec = meta_schema["page_receipt"]
    for receipt in model.get("pages", []) or []:
        missing = [field for field in receipt_spec["required"] if field not in receipt]
        if missing:
            diagnostics.append({
                "code": "ONTOLOGY_PAGE_RECEIPT_BROKEN",
                "path": str(model_path),
                "message": f"page receipt missing required fields: {', '.join(missing)}",
            })
            continue
        raw = str(receipt["path"])
        candidate = (root / raw).resolve()
        if not candidate.is_file():
            diagnostics.append({
                "code": "ONTOLOGY_PAGE_RECEIPT_BROKEN",
                "path": str(model_path),
                "message": f"page receipt points at a page that does not exist: {raw}",
            })
            continue
        receipt_paths.add(gov.relative(root, candidate))
        elements = [str(e) for e in (receipt.get("elements", []) or [])]
        for element in elements:
            if element not in seen:
                diagnostics.append({
                    "code": "ONTOLOGY_PAGE_RECEIPT_BROKEN",
                    "path": str(model_path),
                    "message": f"page receipt for {raw} references unknown element: {element}",
                })

        # Anchor mirror check (signal): when a page declares model-elements,
        # it must match its receipt exactly — both directions, order-insensitive.
        # A missing anchor is tolerated (receipts may precede anchor rollout);
        # the root regression suite guards against silent anchor deletion.
        anchor = declared_anchor(candidate.read_text(encoding="utf-8"))
        if anchor is not None and set(anchor) != set(elements):
            diagnostics.append({
                "code": "ANCHOR_RECEIPT_DRIFT",
                "path": gov.relative(root, candidate),
                "message": (
                    f"model-elements anchor drifts from the model receipt "
                    f"(anchor={anchor}, receipt={elements}); the receipt is the "
                    f"source of truth — fix the mirror, never delete the page"
                ),
            })

    # Coverage invariant (signal): every map-covered page needs a receipt.
    selected, _origin, _diagnostics, reads = gov.discover(root)
    uncovered: list[str] = []
    if selected is not None:
        entries, _edges, _parse = gov.map_graph(root, selected, reads)
        covered = [str(e["path"]) for e in entries]
        for page in covered:
            if page not in receipt_paths:
                uncovered.append(page)
                diagnostics.append({
                    "code": "CONTENT_UNCOVERED",
                    "path": page,
                    "message": "map-covered page has no decomposition receipt in the model yet (declare it; never delete the page on this signal)",
                })

    return {
        "model": str(model_path),
        "meta_schema": str(meta_path or DEFAULT_META_SCHEMA),
        "model_schema_version": version,
        "coverage": {
            "receipts": len(receipt_paths),
            "uncovered": len(uncovered),
            "uncovered_pages": uncovered,
        },
        "anchor_drift": sum(
            1 for d in diagnostics if d["code"] == "ANCHOR_RECEIPT_DRIFT"
        ),
        "diagnostics": diagnostics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--meta-schema", type=Path, default=None)
    args = parser.parse_args()
    report = validate(args.repo.resolve(), args.model, args.meta_schema)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 1 if has_error(report["diagnostics"]) else 0


if __name__ == "__main__":
    sys.exit(main())

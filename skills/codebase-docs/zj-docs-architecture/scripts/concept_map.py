#!/usr/bin/env python3
"""architecture concept-map (B): schema, deterministic render/parse, and idempotency.

This is architecture's OWN map artifact (design doc §2), distinct from the repo
doc-map it consumes (owner=ontology). formatter(A) (code -> concepts) and the C\\B
consistency direction (which needs a page-side concept-declaration convention, D5)
land in PR-B; PR-A ships the B schema + the B\\C (CONSIST_UNDOC) consumer.

The fenced block is delimited by CONCEPT_MAP_START/END — deliberately separate from
the generated BASE_RULES_* block: check-shared-conventions.py only scans BASE_RULES,
and generate-shared-conventions.render_block never reads this, so the concept JSON
cannot leak into the closed-schema or byte-equal checks.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

# §2 :85 — initial concept vocabulary is the eight maintenance-triggers
# (architecture-contract.md), the "worth modeling from code" seeds.
CONCEPT_KINDS = {
    "extension-seam",
    "durable-owner",
    "cross-process-contract",
    "effect-policy",
    "replay-boundary",
    "lifecycle-rule",
    "accepted-adr",
    "source-map-target",
}


@dataclass(frozen=True)
class ConceptNode:
    id: str
    kind: str
    anchor: str | None  # "path" or "path:line" / symbol locator; None if unanchored


@dataclass(frozen=True)
class ConceptMap:
    # D2: no `index` field — concept->document is derived by the consistency
    # join, not stored here (formatter(A) cannot see the documents).
    nodes: tuple[ConceptNode, ...]
    edges: tuple[tuple[str, str], ...]  # concept -> concept decomposition/composition


_BLOCK_RE = re.compile(
    r"<!-- CONCEPT_MAP_START -->\s*```json\n(.*?)\n```\s*<!-- CONCEPT_MAP_END -->",
    re.S,
)


def render(cm: ConceptMap) -> str:
    """Deterministic, byte-stable rendering (sorted) so CI can diff a re-render."""
    payload = {
        "nodes": [
            {"id": n.id, "kind": n.kind, "anchor": n.anchor}
            for n in sorted(cm.nodes, key=lambda x: (x.kind, x.id))
        ],
        "edges": [list(e) for e in sorted(cm.edges)],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"<!-- CONCEPT_MAP_START -->\n```json\n{body}\n```\n<!-- CONCEPT_MAP_END -->"


def parse(text: str) -> ConceptMap:
    """Parse a rendered block. Raises on missing block or unknown concept kind."""
    match = _BLOCK_RE.search(text)
    if match is None:
        raise ValueError("no CONCEPT_MAP block found")
    data = json.loads(match.group(1))
    nodes = tuple(
        ConceptNode(n["id"], n["kind"], n.get("anchor")) for n in data.get("nodes", [])
    )
    bad = {n.kind for n in nodes} - CONCEPT_KINDS
    if bad:
        raise ValueError(f"concept kind(s) outside seed vocabulary: {sorted(bad)}")
    edges = tuple((a, b) for a, b in data.get("edges", []))
    return ConceptMap(nodes, edges)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_stale(text: str, cm: ConceptMap) -> bool:
    """CI invariant: B must equal formatter's deterministic output. A hand edit to
    B (or a formatter change not re-run) makes this True. Only the fenced block is
    compared, so surrounding prose in the B document is free."""
    match = _BLOCK_RE.search(text)
    if match is None:
        return True
    return _digest(match.group(0)) != _digest(render(cm))


# --- formatter(A): code -> concept-map (D1) --------------------------------
# Scan domain (D1-a): all repo source files, excluding docs/ and vendored dirs.
# B stays closed-world: only code-declared concepts enter, so "documented but not
# in code" can never be fabricated here — that is exactly the C\B signal's job.
SOURCE_EXTS = {".py", ".rs", ".go", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt",
               ".rb", ".c", ".h", ".cc", ".cpp", ".hpp", ".swift", ".scala"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "docs", "build", "dist", "target"}
_CONCEPT_MARKER_RE = re.compile(
    r"@concept:\s*([a-z][a-z0-9-]*)\s+([A-Za-z0-9._-]+)"
    r"(?:\s+--anchor=(\S+))?(?:\s+--owner=(\S+))?"
)


def format_concepts(repo, reader) -> "ConceptMap":
    """Deterministic scan of source files for `@concept: <kind> <id> [attrs]`.
    Runs as a separate command against code (face A) with its own Reader, so it is
    orthogonal to validate()'s bounded page-read contract. D1-c: MVP emits nodes
    only (edges empty)."""
    from pathlib import Path
    nodes: dict[str, ConceptNode] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_EXTS:
            continue
        rel = path.relative_to(repo)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        for line in reader.text(path).splitlines():
            marker = _CONCEPT_MARKER_RE.search(line)
            if marker and marker.group(1) in CONCEPT_KINDS:
                _kind, node_id, anchor, _owner = marker.groups()
                nodes[node_id] = ConceptNode(node_id, marker.group(1), anchor or rel.as_posix())
    return ConceptMap(tuple(nodes.values()), ())  # edges: D1-c MVP

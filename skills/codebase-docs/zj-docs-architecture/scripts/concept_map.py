#!/usr/bin/env python3
"""architecture concept-map (B): schema, deterministic render/parse, and idempotency.

This is architecture's OWN map artifact (design doc §2), distinct from the repo
doc-map it consumes (owner=ontology). formatter(A) ships with --format-concepts; the
consistency directions (B-to-C under-doc, C-to-B orphan, owner mismatch) ship with
--consistency. Edges (concept-to-concept) and owner are additive schema keys, so any
older B file without them still parses (owner/edges default to None/absent).

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

# §2 :85 seed — must equal the slugs of `## Maintenance triggers` in
# references/architecture-contract.md; enforced by ConceptVocabularyTest
# (tests/test_docs_consistency.py). Adding or renaming a trigger means updating
# BOTH the contract bullet AND this set — otherwise that test fails.
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
    owner: str | None = None  # D1 code-declared ownership (authority-id); an A-face fact, NOT the D2 document index


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
            {"id": n.id, "kind": n.kind, "anchor": n.anchor, "owner": n.owner}
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
        ConceptNode(n["id"], n["kind"], n.get("anchor"), n.get("owner"))
        for n in data.get("nodes", [])
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


def render_verified(cm: ConceptMap) -> str:
    """Render B and self-verify it before it is emitted — the write-side mirror of the
    read guard in `consistency`. Under a correct renderer this is a no-op; it exists so a
    render-level regression (a dropped closing fence / CONCEPT_MAP_END, a body that is no
    longer valid JSON, or an unknown kind) fails HERE instead of shipping an
    intact-looking block that `parse` / `--consistency` would later crash on. It re-applies
    the reader's own contract (`_BLOCK_RE` + `json.loads` + `parse`) independently of `render`."""
    block = render(cm)
    match = _BLOCK_RE.search(block)
    if match is None:
        raise ValueError("rendered concept-map B is not a closed CONCEPT_MAP block")
    try:
        json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"rendered concept-map B body is not valid JSON: {exc}") from exc
    parse(block)  # parses the fenced JSON back, re-checking kinds + structure
    return block


# --- formatter(A): code -> concept-map (D1) --------------------------------
# Scan domain (D1-a): all repo source files, excluding docs/ and vendored dirs.
# B stays closed-world: only code-declared concepts enter, so "documented but not
# in code" can never be fabricated here — that is exactly the C\B signal's job.
SOURCE_EXTS = {".py", ".rs", ".go", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt",
               ".rb", ".c", ".h", ".cc", ".cpp", ".hpp", ".swift", ".scala"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "docs", "build", "dist", "target"}
_CONCEPT_MARKER_RE = re.compile(
    r"@concept:\s*([a-z][a-z0-9-]*)\s+([A-Za-z0-9._-]+)"
    r"(?:\s+--anchor=(\S+))?(?:\s+--owner=(\S+))?(?:\s+--part-of=(\S+))?"
)


def format_concepts(repo, reader) -> "ConceptMap":
    """Deterministic scan of source files for `@concept: <kind> <id> [attrs]`.
    Runs as a separate command against code (face A) with its own Reader, so it is
    orthogonal to validate()'s bounded page-read contract. Emits nodes plus
    concept→concept edges from `--part-of` (closed-world: an edge whose endpoint is
    not a code-declared concept is dropped)."""
    from pathlib import Path
    nodes: dict[str, ConceptNode] = {}
    edges: list[tuple[str, str]] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_EXTS:
            continue
        rel = path.relative_to(repo)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        # block-level finditer: one marker per declared concept, incl. same-line multiples
        for marker in _CONCEPT_MARKER_RE.finditer(reader.text(path)):
            kind, node_id, anchor, owner, part_of = marker.groups()
            if kind not in CONCEPT_KINDS:
                continue
            nodes[node_id] = ConceptNode(node_id, kind, anchor or rel.as_posix(), owner)
            if part_of:
                for parent in part_of.split(","):
                    parent = parent.strip()
                    if parent:
                        edges.append((node_id, parent))
    valid = set(nodes)
    kept = tuple(sorted({e for e in edges if e[0] in valid and e[1] in valid}))
    return ConceptMap(tuple(nodes.values()), kept)  # closed-world: dangling part-of edges dropped


def find_cycle_nodes(edges: "tuple[tuple[str, str], ...]") -> "tuple[str, ...]":
    """Concepts that lie on a part-of decomposition cycle (the graph must be a DAG).

    Pure B structure: needs neither a doc-map nor C, so it is a well-formedness
    check on face A, distinct from the B<->C CONSIST_* signals. A node is reported
    iff some non-empty path of part-of edges returns to it (covers self-loops and
    multi-node cycles). Endpoints outside the node set are folded in as vertices, so
    a hand-edited dangling edge can never by itself fabricate a cycle. Sorted for a
    byte-stable result."""
    adj: dict[str, list[str]] = {}
    for child, parent in edges:
        adj.setdefault(child, []).append(parent)
        adj.setdefault(parent, [])

    def returns_to_start(start: str) -> bool:
        seen: set[str] = set()
        stack = list(adj[start])  # start from a neighbour: a 0-length self-hit never counts
        while stack:
            current = stack.pop()
            if current == start:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adj[current])
        return False

    return tuple(sorted(node for node in adj if returns_to_start(node)))

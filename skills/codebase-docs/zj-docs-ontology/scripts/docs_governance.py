#!/usr/bin/env python3
"""Produce a read-only documentation governance proposal for one repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


POINTER_RE = re.compile(r"(?im)^\s*docs-map:\s*([^\s`]+)\s*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
LONG_LIVED = ("methods", "prds", "architecture", "agreements", "designs", "testing", "benchmarks", "references", "zj-adr")
PROCESS = ("plans", "zj-retros")
EVIDENCE_NAMES = {"artifacts", "evidence", "evaluations", "fixtures", "research", "skills-outputs", "test-results"}


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, value: str, base: Path) -> Path | None:
    if value.startswith(("http://", "https://", "mailto:", "#")):
        return None
    candidate = (base / value.split("#", 1)[0]).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def read_pointers(root: Path) -> tuple[list[Path], list[dict[str, str]], list[str]]:
    pointers: list[Path] = []
    diagnostics: list[dict[str, str]] = []
    reads: list[str] = []
    for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
        path = root / name
        if not path.is_file():
            continue
        reads.append(relative(root, path))
        for value in POINTER_RE.findall(path.read_text(encoding="utf-8")):
            target = resolve(root, value, root)
            if target and target.is_file():
                pointers.append(target)
            else:
                diagnostics.append({"code": "MAP_POINTER_BROKEN", "path": name, "message": f"docs-map target does not exist: {value}"})
    return pointers, diagnostics, reads


def discover(root: Path) -> tuple[Path | None, str, list[dict[str, str]], list[str]]:
    pointers, diagnostics, reads = read_pointers(root)
    unique = sorted(set(pointers))
    if len(unique) == 1:
        return unique[0], "explicit-pointer", diagnostics, reads
    if len(unique) > 1:
        diagnostics.append({"code": "MAP_AMBIGUOUS", "path": ".", "message": "multiple distinct explicit docs-map pointers"})
        return None, "ambiguous", diagnostics, reads
    default = root / "docs" / "README.md"
    if default.is_file():
        return default, "default", diagnostics, reads
    candidates = sorted((root / "docs").glob("**/*-map.md")) if (root / "docs").is_dir() else []
    if len(candidates) == 1:
        return candidates[0], "candidate", diagnostics, reads
    if len(candidates) > 1:
        diagnostics.append({"code": "MAP_AMBIGUOUS", "path": "docs", "message": "multiple compatible map candidates"})
        return None, "ambiguous", diagnostics, reads
    return None, "greenfield", diagnostics, reads


def map_links(root: Path, path: Path, reads: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    reads.append(relative(root, path))
    text = path.read_text(encoding="utf-8")
    links: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    for value in LINK_RE.findall(text):
        target = resolve(root, value, path.parent)
        if target is None:
            continue
        target_value = relative(root, target) if target.exists() else value
        links.append({"target": target_value, "exists": str(target.exists()).lower()})
        if not target.exists():
            diagnostics.append({"code": "MAP_LINK_BROKEN", "path": relative(root, path), "message": f"map link does not exist: {value}"})
    return links, diagnostics


def files_under(root: Path, directory: Path) -> list[str]:
    return sorted(relative(root, path) for path in directory.rglob("*") if path.is_file())


def inventory(root: Path) -> dict[str, object]:
    docs = root / "docs"
    long_lived = {name: files_under(root, docs / name) for name in LONG_LIVED if (docs / name).is_dir()}
    process = {name: files_under(root, docs / name) for name in PROCESS if (docs / name).is_dir()}
    target_defined = []
    if docs.is_dir():
        known = set(LONG_LIVED) | set(PROCESS)
        target_defined = sorted(child.name for child in docs.iterdir() if child.is_dir() and child.name not in known)
    evidence = sorted(child.name for child in root.iterdir() if child.is_dir() and child.name in EVIDENCE_NAMES)
    root_entries = [name for name in ("ZJ-CONTEXT.md", "ZJ-CONTEXT-MAP.md") if (root / name).is_file()]
    return {"long_lived": long_lived, "process_material": process, "target_defined_categories": target_defined, "evidence_surfaces": evidence, "root_entries": root_entries}


def report(root: Path, validate_links: bool) -> dict[str, object]:
    selected, origin, diagnostics, reads = discover(root)
    proposal: dict[str, object] = {
        "repository": str(root.resolve()),
        "mode": "read-only-proposal",
        "map": relative(root, selected) if selected else None,
        "map_origin": origin,
        "inventory": inventory(root),
        "diagnostics": diagnostics,
        "proposed_actions": [],
        "mutations": [],
        "read_paths": reads,
    }
    if selected is None:
        if origin == "greenfield":
            proposal["proposed_actions"] = [{"action": "create-map", "target": "docs/README.md", "confirmation": "Human confirms the proposed map and lazy category creation"}]
        else:
            proposal["proposed_actions"] = [{"action": "resolve-map", "confirmation": "Human selects one map before any writes"}]
        return proposal
    if validate_links:
        links, link_diagnostics = map_links(root, selected, reads)
        proposal["map_links"] = links
        proposal["diagnostics"].extend(link_diagnostics)  # type: ignore[index]
    process_paths = [path for paths in proposal["inventory"]["process_material"].values() for path in paths]  # type: ignore[index,union-attr]
    if process_paths:
        proposal["proposed_actions"] = [{"action": "review-process-material", "targets": process_paths, "confirmation": "Human confirms any durable extraction and each deletion candidate"}]
    return proposal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--proposal", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    payload = report(args.repo.resolve(), validate_links=args.validate)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if any(item["code"].startswith("MAP_") for item in payload["diagnostics"]) and payload["map_origin"] != "greenfield" else 0


if __name__ == "__main__":
    sys.exit(main())

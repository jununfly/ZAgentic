#!/usr/bin/env python3
"""Read-only validator for a documentation map's architecture handbook."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


POINTER_RE = re.compile(r"(?im)^\s*docs-map:\s*([^\s`]+)\s*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
INLINE_PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+(?:\.[A-Za-z0-9_-]+)?)`")
AUTHORITY_RE = re.compile(r"authority-id:\s*`?([A-Za-z0-9._-]+)`?", re.I)
HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.M)
ARCHITECTURE_KINDS = {
    "architecture-overview",
    "architecture-layers",
    "architecture-subsystem",
    "architecture-flow",
    "architecture-cross-cutting",
}
COMMON_HEADINGS = {"question", "scope", "boundaries", "source map", "related authority"}
VIEW_HEADINGS = {
    "architecture-overview": {"system boundary", "major parts"},
    "architecture-layers": {"layers", "allowed dependencies"},
    "architecture-subsystem": {"responsibility", "owned state", "interface", "failure behavior"},
    "architecture-flow": {"trigger", "sequence", "state and effects", "failure or exit behavior", "observable evidence"},
    "architecture-cross-cutting": {"shared rule", "consumers"},
}
PROCESS_HEADINGS = {"status", "progress", "daily log", "execution log"}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str
    signal: bool = False


@dataclass(frozen=True)
class MapEntry:
    target: Path
    authority_id: str | None


class Reader:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def text(self, path: Path) -> str:
        self.paths.append(path.as_posix())
        return path.read_text(encoding="utf-8")


def path_from(root: Path, value: str, base: Path) -> Path | None:
    if value.startswith(("http://", "https://", "mailto:")) or value.startswith("#"):
        return None
    value = value.split("#", 1)[0]
    candidate = (base / value).resolve() if not value.startswith("/") else Path(value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def discover_map(root: Path, reader: Reader) -> tuple[Path | None, str, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    pointers: list[Path] = []
    for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
        path = root / name
        if not path.is_file():
            continue
        for value in POINTER_RE.findall(reader.text(path)):
            candidate = path_from(root, value, root)
            if candidate and candidate.is_file():
                pointers.append(candidate)
            else:
                diagnostics.append(Diagnostic("MAP_POINTER_BROKEN", name, f"docs-map target is not a repository Markdown file: {value}"))
    unique = sorted(set(pointers))
    if len(unique) == 1:
        return unique[0], "explicit-pointer", diagnostics
    if len(unique) > 1:
        diagnostics.append(Diagnostic("MAP_AMBIGUOUS", ".", "multiple distinct explicit docs-map pointers"))
        return None, "ambiguous", diagnostics
    default = root / "docs" / "README.md"
    if default.is_file():
        return default, "default", diagnostics
    candidates = sorted((root / "docs").glob("**/*-map.md")) if (root / "docs").is_dir() else []
    if len(candidates) == 1:
        return candidates[0], "candidate", diagnostics
    if len(candidates) > 1:
        diagnostics.append(Diagnostic("MAP_AMBIGUOUS", "docs", "multiple compatible map candidates"))
        return None, "ambiguous", diagnostics
    diagnostics.append(Diagnostic("MAP_MISSING", "docs", "no explicit map, docs/README.md, or unique map candidate"))
    return None, "missing", diagnostics


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def headings(text: str) -> set[str]:
    return {match.group(2).strip().lower() for match in HEADING_RE.finditer(text)}


def section(text: str, title: str) -> str:
    matches = list(HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(2).strip().lower() != title.lower():
            continue
        level = len(match.group(1))
        end = len(text)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        return text[match.end() : end]
    return ""


def map_entries(root: Path, map_path: Path, text: str) -> list[MapEntry]:
    entries: list[MapEntry] = []
    blocks = re.split(r"(?m)^(?=-\s+)", text)
    for block in blocks:
        authority = AUTHORITY_RE.search(block)
        for value in LINK_RE.findall(block):
            target = path_from(root, value, map_path.parent)
            if target and "/architecture/" in target.as_posix():
                entries.append(MapEntry(target, authority.group(1) if authority else None))
    return entries


def source_paths(root: Path, page_path: Path, text: str) -> Iterable[tuple[str, Path | None]]:
    body = section(text, "Source map")
    values = LINK_RE.findall(body) + INLINE_PATH_RE.findall(body)
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        yield value, path_from(root, value, root)


def validate(root: Path, *, explicit_map: str | None = None) -> tuple[list[Diagnostic], list[str], dict[str, str]]:
    root = root.resolve()
    reader = Reader()
    diagnostics: list[Diagnostic] = []
    if explicit_map:
        map_path = path_from(root, explicit_map, root)
        origin = "argument"
        if not map_path or not map_path.is_file():
            return [Diagnostic("MAP_POINTER_BROKEN", explicit_map, "--map target is not a repository Markdown file")], reader.paths, {"origin": origin}
    else:
        map_path, origin, discovery = discover_map(root, reader)
        diagnostics.extend(discovery)
        if map_path is None:
            return diagnostics, reader.paths, {"origin": origin}

    map_text = reader.text(map_path)
    entries = map_entries(root, map_path, map_text)
    if not entries:
        architecture_root = root / "docs" / "architecture"
        has_unmapped_page = architecture_root.is_dir() and any(architecture_root.rglob("*.md"))
        if has_unmapped_page:
            diagnostics.append(Diagnostic("MAP_ARCHITECTURE_EMPTY", map_path.relative_to(root).as_posix(), "map has no architecture links for existing architecture pages"))
        return diagnostics, reader.paths, {"origin": origin, "map": map_path.relative_to(root).as_posix()}

    page_seen: set[Path] = set()
    primary_ids: dict[str, Path] = {}
    linked_counts: dict[Path, int] = {}
    for entry in entries:
        linked_counts[entry.target] = linked_counts.get(entry.target, 0) + 1
        if not entry.target.is_file():
            diagnostics.append(Diagnostic("MAP_LINK_BROKEN", entry.target.relative_to(root).as_posix(), "architecture map link does not exist"))
            continue
        if entry.target in page_seen:
            continue
        page_seen.add(entry.target)
        page_text = reader.text(entry.target)
        relative = entry.target.relative_to(root).as_posix()
        meta = frontmatter(page_text)
        kind = meta.get("doc-kind")
        authority = meta.get("authority")
        if kind not in ARCHITECTURE_KINDS:
            diagnostics.append(Diagnostic("PAGE_KIND_INVALID", relative, "doc-kind must be an architecture view"))
        if authority not in {"primary", "supporting", "historical", "process", "external"}:
            diagnostics.append(Diagnostic("PAGE_AUTHORITY_INVALID", relative, "authority is missing or invalid"))
        page_headings = headings(page_text)
        if authority == "primary":
            authority_id = meta.get("authority-id")
            if not authority_id:
                diagnostics.append(Diagnostic("AUTHORITY_ID_MISSING", relative, "primary page lacks authority-id"))
            else:
                previous = primary_ids.get(authority_id)
                if previous:
                    diagnostics.append(Diagnostic("AUTHORITY_ID_DUPLICATE", relative, f"duplicates primary authority on {previous.relative_to(root)}"))
                primary_ids[authority_id] = entry.target
                bindings = [item for item in entries if item.target == entry.target and item.authority_id == authority_id]
                if len(bindings) != 1:
                    diagnostics.append(Diagnostic("AUTHORITY_MAP_BINDING", relative, "map must bind this primary path and authority-id exactly once"))
            for heading in sorted(COMMON_HEADINGS):
                if heading not in page_headings:
                    diagnostics.append(Diagnostic("PAGE_CONTRACT_MISSING", relative, f"missing required section: {heading}"))
            for heading in sorted(VIEW_HEADINGS.get(kind or "", set())):
                if heading not in page_headings:
                    diagnostics.append(Diagnostic("PAGE_VIEW_CONTRACT_MISSING", relative, f"missing {kind} section: {heading}"))
            for heading in sorted(PROCESS_HEADINGS & page_headings):
                diagnostics.append(Diagnostic("PAGE_PROCESS_HEADING", relative, f"process heading is not valid on a primary architecture page: {heading}"))

            for raw, source in source_paths(root, entry.target, page_text):
                if source is None:
                    continue
                if not source.exists():
                    diagnostics.append(Diagnostic("SOURCE_TARGET_MISSING", relative, f"source-map target does not exist: {raw}"))
                    continue
                if "zj-adr" in source.parts and source.is_file():
                    adr = reader.text(source)
                    status = frontmatter(adr).get("status", "").lower()
                    if status not in {"accepted", "superseded"}:
                        diagnostics.append(Diagnostic("ADR_UNACCEPTED", relative, f"ADR source is not accepted or superseded: {raw}"))

    for path, count in linked_counts.items():
        if count > 1:
            diagnostics.append(Diagnostic("SIGNAL_MAP_DUPLICATE_LINK", path.relative_to(root).as_posix(), "same architecture page is linked more than once", signal=True))
    metadata = {"origin": origin, "map": map_path.relative_to(root).as_posix()}
    return diagnostics, reader.paths, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--map", dest="map_path")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--audit-json", action="store_true")
    args = parser.parse_args()
    reader = Reader()
    if args.discover:
        path, origin, diagnostics = discover_map(args.repo.resolve(), reader)
        payload = {"map": str(path.relative_to(args.repo.resolve())) if path else None, "origin": origin, "diagnostics": [item.__dict__ for item in diagnostics], "read_paths": reader.paths}
        print(json.dumps(payload, indent=2))
        return 0 if path and not diagnostics else 1
    diagnostics, read_paths, metadata = validate(args.repo, explicit_map=args.map_path)
    if args.audit_json:
        print(json.dumps({"metadata": metadata, "diagnostics": [item.__dict__ for item in diagnostics], "read_paths": read_paths}, indent=2))
    else:
        for item in diagnostics:
            level = "signal" if item.signal else "error"
            print(f"{level} {item.code} {item.path}: {item.message}")
        if not diagnostics:
            print(f"Architecture documentation validation passed ({metadata.get('map')})")
    return 1 if any(not item.signal for item in diagnostics) else 0


if __name__ == "__main__":
    sys.exit(main())

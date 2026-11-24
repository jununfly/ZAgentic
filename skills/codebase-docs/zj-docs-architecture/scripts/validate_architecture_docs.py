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
# issue #275 Fix 4 (L4): the contract entry is the map entry's explicit role
# declaration. The lookbehind keeps `page-role:` (a page-side residue) from
# matching here — map entry level is the only legal declaration position.
ROLE_RE = re.compile(r"(?<![\w-])role:\s*`?(primary|supporting)`?", re.I)
HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.M)

# Shared value domains and the naming syntax core are NOT defined here. They
# are read from this skill's own inlined BASE_RULES block (generated from the
# repo-side authority docs/skill-conventions/skill-conventions.json). An
# installed skill carries that block, so this stays runtime-closure compliant:
# no read of docs/ or any external path at runtime. If the block is missing or
# malformed, import fails loud — there is deliberately no hardcoded fallback,
# because a silent fallback is exactly the "hardcoded enum still in force"
# fake-green this redesign removes.
_RULES_RE = re.compile(r"<!-- BASE_RULES_START -->.*?```json\n(.*?)\n```.*?<!-- BASE_RULES_END -->", re.S)


def _load_inline_conventions() -> dict:
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = _RULES_RE.search(text)
    if match is None:
        raise RuntimeError(f"BASE_RULES block missing or malformed in {skill_md}")
    payload = json.loads(match.group(1))
    core = payload["core"]
    for key in ("naming-syntax-core", "doc-kind", "authority"):
        if key not in core:
            raise RuntimeError(f"BASE_RULES block missing required core key: {key}")
    return core


_INLINE_CORE = _load_inline_conventions()

# Architecture kind vocabulary is derived from the inlined doc-kind domain,
# filtered to the architecture family. Keeping the architecture-* prefix filter
# preserves the private constraint "an architecture page must be an architecture
# view or map" without hardcoding the enumeration: a canary kind injected into
# the shared domain and re-rendered here is accepted, proving the read is wired.
MAP_KINDS = {k for k in _INLINE_CORE["doc-kind"]["values"] if k == "architecture-map"}
VALID_ARCHITECTURE_KINDS = {k for k in _INLINE_CORE["doc-kind"]["values"] if k.startswith("architecture-")}
# Authority values and naming core rules come from the inlined shared domain.
VALID_AUTHORITIES = set(_INLINE_CORE["authority"]["values"])
_NAME_RULES = {rule["id"]: rule for rule in _INLINE_CORE["naming-syntax-core"]["rules"]}

# Semantic payload (per-kind must-write sections) stays architecture-private.
COMMON_HEADINGS = {"question", "scope", "boundaries", "source map", "related authority"}
VIEW_HEADINGS = {
    "architecture-overview": {"system boundary", "major parts"},
    "architecture-layers": {"layers", "allowed dependencies"},
    "architecture-subsystem": {"responsibility", "owned state", "interface", "failure behavior"},
    "architecture-flow": {"trigger", "sequence", "state and effects", "failure or exit behavior", "observable evidence"},
    "architecture-cross-cutting": {"shared rule", "consumers"},
}
PROCESS_HEADINGS = {"status", "progress", "daily log", "execution log"}
# Page-prefix families are an architecture-private extension (declared in this
# skill's Shared Conventions); they are deliberately absent from the shared core.
NAME_PREFIXES = ("ta", "ba", "pa")
NAME_SHAPE_RE = re.compile(_NAME_RULES["shape"]["pattern"])
NAME_DATE_RE = re.compile(_NAME_RULES["no-date"]["pattern"])
NAME_COMMIT_RE = re.compile(_NAME_RULES["no-date"]["sha-segment-pattern"])
NAME_VERSION_RE = re.compile(_NAME_RULES["no-version"]["pattern"])
NAME_STATUS_TOKENS = set(_NAME_RULES["no-status"]["tokens"])


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
    # issue #275 Fix 4: "primary" applies the full primary contract,
    # "supporting" is fully exempt, and the declaration lives only on the map
    # entry — never inferred from a path substring.
    role: str


# A Source map may cite a stable external reference, so "path_from() returned
# None" has two very different meanings: the link is deliberately off-repo, or
# a relative path wandered out of the repository and means nothing. Only the
# second is worth reporting.
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


class Reader:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def text(self, path: Path) -> str:
        self.paths.append(path.as_posix())
        return path.read_text(encoding="utf-8")


def path_from(root: Path, value: str, base: Path) -> Path | None:
    if value.startswith(EXTERNAL_PREFIXES):
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
    # greenfield = legitimate cold start, aligned with ontology
    # (docs_governance.py:651 returns "greenfield", has_error short-circuits at :1457-1459).
    # No MAP_MISSING ERROR: validate() returns with empty diagnostics at the
    # map_path-is-None branch, so an empty repo exits 0 instead of failing the gate.
    return None, "greenfield", diagnostics


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


def naming_diagnostics(stem: str) -> list[tuple[str, str]]:
    """Stability rules for a mapped architecture page's file name.

    A name that encodes *when* a page was written, *which* revision it is, or
    *how current* it is becomes wrong the first time the page is revised — and
    every link to it goes stale with it. The name should answer what the page
    is about and nothing else.
    """
    found: list[tuple[str, str]] = []
    segments = stem.split("-")
    if len(segments) < 2 or segments[0] not in NAME_PREFIXES:
        prefixes = ", ".join(f"{prefix}-" for prefix in NAME_PREFIXES)
        found.append(("PAGE_NAME_PREFIX", f"name must start with one of {prefixes}: {stem}"))
    if not NAME_SHAPE_RE.match(stem):
        found.append(("PAGE_NAME_SHAPE", f"name must be lowercase and hyphen-separated: {stem}"))
    if NAME_DATE_RE.search(stem):
        found.append(("PAGE_NAME_DATE", f"name must not encode a date: {stem}"))
    if any(NAME_COMMIT_RE.match(segment) and any(char.isdigit() for char in segment) for segment in segments):
        found.append(("PAGE_NAME_DATE", f"name must not encode a commit sha: {stem}"))
    reported_date = any(code == "PAGE_NAME_DATE" for code, _ in found)
    for index, segment in enumerate(segments):
        if reported_date:
            break  # one cause per name; the date is the specific one
        trailing_number = segment.isdigit() and index == len(segments) - 1
        if NAME_VERSION_RE.match(segment) or trailing_number:
            found.append(("PAGE_NAME_VERSION_OR_STATUS", f"name must not encode a version: {stem}"))
            break
        if segment in NAME_STATUS_TOKENS:
            found.append(("PAGE_NAME_VERSION_OR_STATUS", f"name must not encode a temporary status: {stem}"))
            break
    return found


def map_entries(root: Path, map_path: Path, text: str) -> tuple[list[MapEntry], list[Path]]:
    """Collect declared map entries and undeclared architecture links.

    issue #275 Fix 4 (L4): an entry is a link whose map block carries an
    explicit `role:` declaration — the path substring judgment is gone. A
    link without a declaration is not an entry (fail-open: no contract is
    applied), but if it points into the repository's architecture root it is
    reported back so the validator can emit a `PAGE_ROLE_UNDECLARED` signal.
    That detection is zero-read: opening undeclared pages to inspect them
    would break the bounded-read contract the read-boundary fixture pins.
    """
    entries: list[MapEntry] = []
    undeclared: set[Path] = set()
    architecture_root = root / "docs" / "architecture"
    blocks = re.split(r"(?m)^(?=-\s+)", text)
    for block in blocks:
        authority = AUTHORITY_RE.search(block)
        role_match = ROLE_RE.search(block)
        role = role_match.group(1).lower() if role_match else None
        for value in LINK_RE.findall(block):
            target = path_from(root, value, map_path.parent)
            if target is None:
                continue
            if role is not None:
                entries.append(MapEntry(target, authority.group(1) if authority else None, role))
            elif target == architecture_root or architecture_root in target.parents:
                undeclared.add(target)
    return entries, sorted(undeclared)


def source_paths(root: Path, page_path: Path, text: str) -> Iterable[tuple[str, Path | None]]:
    body = section(text, "Source map")
    values = LINK_RE.findall(body) + INLINE_PATH_RE.findall(body)
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        yield value, path_from(root, value, page_path.parent)


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
    entries, undeclared_targets = map_entries(root, map_path, map_text)
    # issue #275 Fix 4: an undeclared page inside the architecture root gets
    # one reminder signal (declaration-missing = signal, per the severity
    # carve-out) and no contract. The signal is emitted before the empty-entry
    # early return so a legacy map with zero role declarations still shows
    # what to migrate.
    for target in undeclared_targets:
        diagnostics.append(Diagnostic(
            "PAGE_ROLE_UNDECLARED",
            target.relative_to(root).as_posix(),
            "linked architecture page has no role declaration in the map; declare role: primary or role: supporting on the map entry (fail-open: no contract is applied)",
            signal=True,
        ))
    if not entries:
        # Coverage of architecture pages that never reached the map is owned by
        # ontology UNMAPPED_PAGE (docs_governance.py:1090-1121, signal-only; the
        # `architecture` category is long_lived in canonical-preset.json:20). This
        # skill keeps only the empty-entry early return — the undeclared-role
        # reminder above (:294-300) still fires. ERROR->signal degradation is
        # accepted per §7(b) let-through / §9 Delta.
        return diagnostics, reader.paths, {"origin": origin, "map": map_path.relative_to(root).as_posix()}

    page_seen: set[Path] = set()
    primary_ids: dict[str, Path] = {}
    linked_counts: dict[Path, int] = {}
    for entry in entries:
        linked_counts[entry.target] = linked_counts.get(entry.target, 0) + 1
        if not entry.target.is_file():
            diagnostics.append(Diagnostic("MAP_LINK_BROKEN", entry.target.relative_to(root).as_posix(), "architecture map link does not exist", signal=True))
            continue
        if entry.target in page_seen:
            continue
        page_seen.add(entry.target)
        page_text = reader.text(entry.target)
        relative = entry.target.relative_to(root).as_posix()
        meta = frontmatter(page_text)
        kind = meta.get("doc-kind")
        authority = meta.get("authority")
        is_navigation = kind in MAP_KINDS
        # issue #275 Fix 4: a page-side `page-role:` residue is a second
        # declaration source; only the map entry may declare the role.
        if "page-role" in meta:
            diagnostics.append(Diagnostic(
                "ROLE_DECLARATION_OUT_OF_MAP",
                relative,
                "page-side page-role is not a legal declaration position; declare role on the map entry instead",
                signal=True,
            ))
        # A declared supporting view is fully exempt from the primary
        # contract (issue #275 Fix 4): existence above is the only check.
        if entry.role == "supporting":
            continue
        if kind not in VALID_ARCHITECTURE_KINDS:
            diagnostics.append(Diagnostic("PAGE_KIND_INVALID", relative, "doc-kind must be an architecture view or map"))
        if authority not in VALID_AUTHORITIES:
            diagnostics.append(Diagnostic("PAGE_AUTHORITY_INVALID", relative, "authority is missing or invalid"))
        if not is_navigation:
            for code, message in naming_diagnostics(entry.target.stem):
                diagnostics.append(Diagnostic(code, relative, message))
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
            if not is_navigation:
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
                    if raw.startswith(EXTERNAL_PREFIXES):
                        continue
                    diagnostics.append(
                        Diagnostic(
                            "SOURCE_TARGET_OUTSIDE",
                            relative,
                            f"source-map target resolves outside the repository: {raw}",
                        )
                    )
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

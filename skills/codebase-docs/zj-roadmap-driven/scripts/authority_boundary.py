"""Detect durable code that cites transient roadmap process artifacts.

Judgement is deliberately narrow: a *durable* source must not cite a transient
`docs/plans/` artifact, nor use a Roadmap node's completed status as proof.
Process-state files are not durable sources. Append-only agent memory logs, the
Roadmap carrier and its rendered views describe the process itself, so a
reference to another process artifact inside them is not an authority leak
(issue #239). Projects can declare further process-state paths with
`authority-check --exclude <path>`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import json
import os
import re
from typing import Iterable

from roadmap import RoadmapError, ROADMAP_AUTHORITY_ENVELOPE


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ALLOW_RE = re.compile(
    r"roadmap-authority-allow:\s*governance-example(?:\s|-->|$)"
)
ROADMAP_COMPLETION_CLAIM_RE = re.compile(
    r"(?:\b(?:proof|evidence)\s*:\s*roadmap\s+node\s+\d+(?:-\d+)*\s+"
    r"(?:is\s+)?(?:completed?|done)\b|"
    r"根据\s*roadmap\s*节点\s*\d+(?:-\d+)*\s*(?:已)?完成)",
    re.IGNORECASE,
)
DURABLE_SUFFIXES = frozenset({
    ".c", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".json",
    ".jsx", ".kt", ".md", ".php", ".py", ".rb", ".rs", ".sh", ".swift",
    ".toml", ".ts", ".tsx", ".yaml", ".yml",
})
# Directory *names* (compared per path segment). These trees never carry
# durable project facts; pruning them also keeps the walk off `.git/objects`.
EXCLUDED_DIR_PARTS = frozenset({
    ".git",
    ".workbuddy",  # append-only agent memory / logs
    "__pycache__",
    "node_modules",
    "tmp",
})
# A Roadmap view declares itself process-state with the same envelope that
# `render` / `section` emit. It lives at the top of the file.
PROCESS_STATE_HEAD_LIMIT = 512
# Narrow signature for a single-file Roadmap carrier; a generic `nodes.json`
# must not be able to opt out of the gate by growing a `nodes` key.
CARRIER_REQUIRED_KEYS = frozenset({"title", "version", "nodes", "metadata"})


class ProcessAuthorityLeak(RoadmapError):
    code = "E_PROCESS_AUTHORITY_LEAK"


@dataclass(frozen=True)
class AuthorityLeak:
    source: str
    line: int
    target: str


def _normalize_exclude(value: str | Path) -> PurePosixPath:
    """Turn a project-relative declaration into a comparable path prefix."""
    text = str(value).replace("\\", "/")
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ValueError(f"--exclude must be relative to the project root: {value}")
    parts = tuple(part for part in text.split("/") if part not in ("", "."))
    if not parts or ".." in parts:
        raise ValueError(
            f"--exclude must name a path inside the project root: {value}"
        )
    return PurePosixPath(*parts)


def _is_excluded(relative: Path, excludes: tuple[PurePosixPath, ...]) -> bool:
    parts = tuple(relative.parts)
    return any(
        len(exclude.parts) <= len(parts)
        and parts[: len(exclude.parts)] == exclude.parts
        for exclude in excludes
    )


def _iter_sources(
    root: Path, plans: Path, excludes: tuple[PurePosixPath, ...]
):
    """Walk durable candidates, pruning non-durable trees before descending."""
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        relative_dir = current.relative_to(root)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in EXCLUDED_DIR_PARTS
            and (current / name) != plans
            and not _is_excluded(relative_dir / name, excludes)
        ]
        for name in filenames:
            source = current / name
            if not source.is_file():
                continue
            relative = relative_dir / name
            if _is_excluded(relative, excludes):
                continue
            yield source, relative


def _is_roadmap_carrier(text: str) -> bool:
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return False
    if not isinstance(data, dict) or not CARRIER_REQUIRED_KEYS.issubset(data):
        return False
    nodes = data["nodes"]
    if not isinstance(nodes, (dict, list)) or not isinstance(data["metadata"], dict):
        return False
    values = nodes.values() if isinstance(nodes, dict) else nodes
    return all(isinstance(node, dict) and "status" in node for node in values)


def _is_process_state_file(source: Path, text: str) -> bool:
    suffix = source.suffix.lower()
    if suffix == ".md":
        return ROADMAP_AUTHORITY_ENVELOPE in text[:PROCESS_STATE_HEAD_LIMIT]
    if suffix == ".json":
        return _is_roadmap_carrier(text)
    return False


def find_process_authority_leaks(
    project_root: str | Path, exclude: Iterable[str | Path] = ()
) -> list[AuthorityLeak]:
    root = Path(project_root).resolve()
    plans = root / "docs" / "plans"
    excludes = tuple(_normalize_exclude(value) for value in exclude)
    process_targets = {
        path.resolve(): path.relative_to(root).as_posix()
        for path in plans.rglob("*")
        if path.is_file()
    } if plans.is_dir() else {}
    leaks: list[AuthorityLeak] = []
    for source, relative_source_path in _iter_sources(root, plans, excludes):
        if source.suffix.lower() not in DURABLE_SUFFIXES:
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        if _is_process_state_file(source, text):
            continue
        relative_source = relative_source_path.as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOW_RE.search(line):
                continue
            matched_targets = set()
            if ROADMAP_COMPLETION_CLAIM_RE.search(line):
                matched_targets.add("roadmap completion claim")
            for resolved, target in process_targets.items():
                if target in line:
                    matched_targets.add(target)
            if source.suffix.lower() == ".md":
                for raw_target in MARKDOWN_LINK_RE.findall(line):
                    target = raw_target.strip().strip("<>").split("#", 1)[0]
                    resolved = (source.parent / target).resolve()
                    if resolved in process_targets:
                        matched_targets.add(process_targets[resolved])
            for target in sorted(matched_targets):
                leaks.append(AuthorityLeak(relative_source, lineno, target))
    return leaks


def format_process_authority_leaks(leaks: list[AuthorityLeak]) -> str:
    return "\n".join(
        f"{leak.source}:{leak.line}: cites transient process artifact {leak.target}"
        for leak in leaks
    )

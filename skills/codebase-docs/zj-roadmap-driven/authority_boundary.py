"""Detect durable code that cites transient roadmap process artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from roadmap import RoadmapError


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
EXCLUDED_DIR_PARTS = frozenset({"node_modules", "tmp"})


class ProcessAuthorityLeak(RoadmapError):
    code = "E_PROCESS_AUTHORITY_LEAK"


@dataclass(frozen=True)
class AuthorityLeak:
    source: str
    line: int
    target: str


def find_process_authority_leaks(project_root: str | Path) -> list[AuthorityLeak]:
    root = Path(project_root).resolve()
    plans = root / "docs" / "plans"
    process_targets = {
        path.resolve(): path.relative_to(root).as_posix()
        for path in plans.rglob("*")
        if path.is_file()
    } if plans.is_dir() else {}
    leaks: list[AuthorityLeak] = []
    for source in root.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in DURABLE_SUFFIXES:
            continue
        relative_source_path = source.relative_to(root)
        if any(part in EXCLUDED_DIR_PARTS for part in relative_source_path.parts):
            continue
        if plans in source.parents:
            continue
        relative_source = relative_source_path.as_posix()
        for lineno, line in enumerate(
            source.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
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

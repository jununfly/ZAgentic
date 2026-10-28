#!/usr/bin/env python3
"""Read-only documentation health metering for one repository.

Opt-in and report-only. Without a config file this tool measures nothing and
exits zero. With one, it meters what the Human parameterized — line budgets,
freshness of pages against their declared `## Source map` targets, orphan and
zero-indegree pages — and prints a machine-readable outlier table. It never
mutates anything.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
INLINE_PATH_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"(?m)^##\s+(.+)$")
EVIDENCE_NAMES = {"artifacts", "evidence", "evaluations", "fixtures", "research", "skills-outputs", "test-results"}
PROCESS = ("plans", "zj-retros")


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


def source_map_targets(root: Path, page: Path) -> list[Path]:
    """Paths declared under the page's `## Source map` section, resolved from
    the page's directory (the architecture layer's one base)."""
    text = page.read_text(encoding="utf-8")
    headings = list(HEADING_RE.finditer(text))
    section = None
    for i, match in enumerate(headings):
        if match.group(1).strip().lower() == "source map":
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            section = text[match.end():end]
            break
    if section is None:
        return []
    targets: list[Path] = []
    seen: set[str] = set()
    for value in LINK_RE.findall(section) + INLINE_PATH_RE.findall(section):
        if value in seen:
            continue
        seen.add(value)
        target = resolve(root, value, page.parent)
        if target is not None and target.is_file() and target not in targets:
            targets.append(target)
    return targets


def mtime(path: Path, is_git: bool) -> float:
    """Last meaningful modification time. Git commit time when the repository
    is one (checkouts and rebases do not reset content age); file mtime
    otherwise, which keeps the meter usable in plain directories."""
    if is_git:
        result = subprocess.run(
            ["git", "-C", str(path.parent), "log", "-1", "--format=%ct", "--", str(path.name)],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip().splitlines()[0])
    return path.stat().st_mtime


def living_markdown(root: Path) -> list[Path]:
    """Living pages as resolved paths. Resolution is load-bearing: on systems
    where the temp or working directory sits behind a symlink, unresolved
    rglob paths never compare equal to the paths `resolve()` produces, and
    the link graph silently empties."""
    pages = []
    for md in sorted(root.rglob("*.md")):
        parts = relative(root, md).split("/")
        if any(part in EVIDENCE_NAMES or part in PROCESS for part in parts):
            continue
        pages.append(md.resolve())
    return pages


def measure(root: Path, config: dict) -> list[dict[str, str]]:
    outliers: list[dict[str, str]] = []
    is_git = (root / ".git").exists()
    docs = root / "docs"
    scope = docs if docs.is_dir() else root

    # Budgets: glob-scoped physical line caps.
    for rule in config.get("budgets", []):
        pattern, cap = rule.get("glob", ""), rule.get("max_lines")
        if not pattern or not isinstance(cap, int):
            continue
        for md in sorted(root.glob(pattern)):
            if not md.is_file() or md.suffix != ".md":
                continue
            lines = len(md.read_text(encoding="utf-8").splitlines())
            if lines > cap:
                outliers.append({
                    "code": "BUDGET_EXCEEDED",
                    "path": relative(root, md),
                    "detail": f"{lines} lines > max {cap} (rule: {pattern})",
                })

    # Freshness: a page against the newest source it declares.
    freshness = config.get("freshness")
    if isinstance(freshness, dict) and freshness.get("max_age_days") is not None:
        max_age = float(freshness["max_age_days"]) * 86400
        for md in living_markdown(scope):
            targets = source_map_targets(root, md)
            if not targets:
                continue
            page_time = mtime(md, is_git)
            newest_source = max(mtime(t, is_git) for t in targets)
            if newest_source - page_time > max_age:
                outliers.append({
                    "code": "FRESHNESS_DRIFT",
                    "path": relative(root, md),
                    "detail": f"newest source target is {int((newest_source - page_time) / 86400)} day(s) newer than the page (max {freshness['max_age_days']})",
                })

    # Orphans: link degree over living pages, map tracked separately.
    if config.get("orphans") is True:
        map_path = (docs / "README.md").resolve() if (docs / "README.md").is_file() else None
        pages = [p for p in living_markdown(scope) if p != map_path]
        inbound: dict[Path, set[Path]] = {p: set() for p in pages}
        map_inbound: set[Path] = set()
        for md in [map_path] if map_path else []:
            for value in LINK_RE.findall(md.read_text(encoding="utf-8")):
                target = resolve(root, value, md.parent)
                if target in inbound:
                    map_inbound.add(target)
        for md in pages:
            for value in LINK_RE.findall(md.read_text(encoding="utf-8")):
                target = resolve(root, value, md.parent)
                if target in inbound and target != md:
                    inbound[target].add(md)
        for page in pages:
            map_cites = page in map_inbound
            cited = bool(inbound[page])
            if not map_cites and not cited:
                outliers.append({"code": "ORPHAN_PAGE", "path": relative(root, page), "detail": "no inbound link from any living page, not even the map"})
            elif map_cites and not cited:
                outliers.append({
                    "code": "ZERO_INDEGREE",
                    "path": relative(root, page),
                    "detail": "linked from the map only; no living page cites it",
                })
    return outliers


def load_config(root: Path, explicit: str | None) -> tuple[Path | None, str | None]:
    candidate = Path(explicit) if explicit else root / "docs" / "doc-health.json"
    if not candidate.is_file():
        return None, None
    try:
        import json as _json

        return candidate, _json.loads(candidate.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        return candidate, f"unreadable config: {error}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    root = args.repo.resolve()
    config_path, config = load_config(root, args.config)
    if config_path is None:
        print(json.dumps({"status": "opt-in", "repository": str(root), "config": None,
                          "message": "doc-health is opt-in; no config found (docs/doc-health.json)", "outliers": []}, indent=2))
        return 0
    if isinstance(config, str):
        print(json.dumps({"status": "config-error", "repository": str(root), "config": relative(root, config_path),
                          "message": config, "outliers": []}, indent=2))
        return 1
    outliers = measure(root, config)
    print(json.dumps({
        "status": "measured",
        "repository": str(root),
        "config": relative(root, config_path),
        "mode": "read-only-report",
        "outliers": outliers,
    }, indent=2, ensure_ascii=False))
    return 1 if outliers else 0


if __name__ == "__main__":
    sys.exit(main())

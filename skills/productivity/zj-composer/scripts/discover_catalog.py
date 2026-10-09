#!/usr/bin/env python3
"""Discover ZAgentic's existing public-skill catalog without persisting state.

The Composer capability index is a read view over the repository's current
public-skill layout and catalog declarations. This helper deliberately writes
only to stdout; snapshot identity, revisions, and persistence belong to the
next provenance stage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    raise SystemExit(
        "PyYAML is required; install repository requirements before discovery."
    ) from exc


PUBLIC_BUCKETS = ("engineering", "codebase-docs", "productivity", "misc", "research")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(?:\n|$)", re.DOTALL)
BUCKET_LINK_RE = re.compile(r"\]\(\./([^/]+)/SKILL\.md\)")
ROOT_LINK_RE = re.compile(r"\]\(\./skills/[^/]+/([^/]+)/SKILL\.md\)")
GUIDE_NAME_RE = re.compile(r"\bzj-[a-z0-9]+(?:-[a-z0-9]+)*\b")


def relative_path(root: Path, path: Path) -> str:
    """Return a stable POSIX path relative to the repository root."""

    return path.relative_to(root).as_posix()


def read_text(path: Path, warnings: list[str], label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        warnings.append(f"{label}: unable to read {path}: {exc}")
        return ""


def parse_frontmatter(path: Path) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Parse frontmatter while preserving malformed entries as warnings."""

    warnings: list[str] = []
    text = read_text(path, warnings, "frontmatter")
    if not text:
        return None, warnings

    match = FRONTMATTER_RE.match(text)
    if not match:
        warnings.append("missing YAML frontmatter")
        return None, warnings

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        warnings.append(f"invalid YAML frontmatter: {exc}")
        return None, warnings
    if not isinstance(data, dict):
        warnings.append("frontmatter is not a mapping")
        return None, warnings

    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not name.strip():
        warnings.append("frontmatter name is missing or empty")
    if not isinstance(description, str) or not description.strip():
        warnings.append("frontmatter description is missing or empty")
    return data, warnings


def read_lines(path: Path, warnings: list[str], label: str) -> list[str]:
    text = read_text(path, warnings, label)
    return text.splitlines() if text else []


def names_from_install_list(path: Path, warnings: list[str]) -> set[str]:
    return {
        line.strip()
        for line in read_lines(path, warnings, "install-list")
        if line.strip() and not line.lstrip().startswith("#")
    }


def catalog_declarations(root: Path) -> tuple[dict[str, set[str]], list[str]]:
    """Read names declared by the existing README, guide, and install surfaces."""

    warnings: list[str] = []
    bucket_names: dict[str, set[str]] = {}
    for bucket in PUBLIC_BUCKETS:
        path = root / "skills" / bucket / "README.md"
        text = "\n".join(read_lines(path, warnings, f"{bucket}-README"))
        bucket_names[bucket] = set(BUCKET_LINK_RE.findall(text))

    root_readme = root / "README.md"
    root_text = "\n".join(read_lines(root_readme, warnings, "root-README"))
    guide = root / "skills" / "engineering" / "zj-guide" / "SKILL.md"
    guide_text = "\n".join(read_lines(guide, warnings, "zj-guide"))
    install_list = root / "scripts" / "zagentic-skills-list"

    return {
        "bucket_readmes": bucket_names,
        "root_readme": set(ROOT_LINK_RE.findall(root_text)),
        "guide": set(GUIDE_NAME_RE.findall(guide_text)),
        "install_list": names_from_install_list(install_list, warnings),
    }, warnings


def discover_catalog(root: Path) -> dict[str, Any]:
    """Return the current public catalog as a deterministic, non-persistent view."""

    root = root.resolve()
    declarations, warnings = catalog_declarations(root)
    skills: list[dict[str, Any]] = []

    for bucket in PUBLIC_BUCKETS:
        bucket_root = root / "skills" / bucket
        if not bucket_root.is_dir():
            warnings.append(f"missing public bucket: {relative_path(root, bucket_root)}")
            continue

        for skill_dir in sorted(bucket_root.iterdir(), key=lambda path: path.name):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                warnings.append(
                    f"skill directory missing SKILL.md: {relative_path(root, skill_dir)}"
                )
                continue

            frontmatter, skill_warnings = parse_frontmatter(skill_md)
            declared_name = frontmatter.get("name") if frontmatter else None
            if isinstance(declared_name, str) and declared_name != skill_dir.name:
                skill_warnings.append(
                    f"frontmatter name {declared_name!r} does not match directory {skill_dir.name!r}"
                )

            skills.append(
                {
                    "bucket": bucket,
                    "directory": skill_dir.name,
                    "name": declared_name if isinstance(declared_name, str) else None,
                    "path": relative_path(root, skill_md),
                    "frontmatter": frontmatter,
                    "declarations": {
                        "bucket_readme": skill_dir.name in declarations["bucket_readmes"][bucket],
                        "root_readme": skill_dir.name in declarations["root_readme"],
                        "guide": skill_dir.name in declarations["guide"],
                        "install_list": skill_dir.name in declarations["install_list"],
                    },
                    "warnings": skill_warnings,
                }
            )

    skills.sort(key=lambda item: (item["bucket"], item["directory"], item["path"]))
    return {
        "schema": "zj-composer/catalog-discovery/v1",
        "root": ".",
        "public_buckets": list(PUBLIC_BUCKETS),
        "index_surfaces": {
            "bucket_readmes": [
                f"skills/{bucket}/README.md" for bucket in PUBLIC_BUCKETS
            ],
            "root_readme": "README.md",
            "guide": "skills/engineering/zj-guide/SKILL.md",
            "install_list": "scripts/zagentic-skills-list",
        },
        "skills": skills,
        "warnings": sorted(warnings),
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a read-only discovery view of ZAgentic public skills."
    )
    default_root = Path(__file__).resolve().parents[4]
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help="Repository root (defaults to the ZAgentic checkout containing this script).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    payload = discover_catalog(args.root)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

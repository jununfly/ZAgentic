#!/usr/bin/env python3
"""Discover the installed skill catalog without persisting state.

The Composer capability index is a read view over the skills available to the
Agent that invoked Composer. Discovery is deterministic: the same catalog root
always yields the same, sorted catalog, with no cwd- or symlink-dependent
behaviour.

Design (see issue #177):
- Composer ships as one skill package among many. The catalog root is resolved
  explicitly (``--root`` / ``ZAGENTIC_ROOT``) when provided, otherwise derived
  from this script's location. It is never assumed to be a fixed ancestor depth.
- Skills are discovered generically instead of being tied to a bucket layout:
  either a flat install (``<root>/<skill>/SKILL.md``) or a monorepo checkout
  (``<root>/skills/<bucket>/<skill>/SKILL.md``).
- Each skill declares its provenance in its SKILL.md frontmatter. A skill is a
  ZAgentic skill when ``source: zagentic`` is present. No central roster.
- When the catalog root cannot be located, or contains no skill packages,
  discovery reports ``catalog_present: false`` and a structured diagnostic
  instead of silently returning an empty catalog (the issue #177 failure mode).
"""

from __future__ import annotations

import argparse
import json
import os
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


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(?:\n|$)", re.DOTALL)
CAPABILITY_METADATA_FIELDS = ("inputs", "outputs", "dependencies", "boundaries")
ZAGENTIC_SOURCE = "zagentic"
DISCOVERY_SCHEMA = "zj-composer/catalog-discovery/v1"


def relative_path(root: Path, path: Path) -> str:
    """Return a stable POSIX path relative to the catalog root."""

    return path.relative_to(root).as_posix()


def read_text(path: Path, warnings: list[str], label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        warnings.append(f"{label}: unable to read {path}: {exc}")
        return ""


def parse_frontmatter(
    path: Path, warnings: list[str]
) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Parse frontmatter; return ``(data, frontmatter_warnings)``.

    File-read failures are reported to the shared ``warnings`` bucket because
    they are cross-cutting. Frontmatter-level defects (missing/invalid
    frontmatter, missing name/description) are returned per-skill so the caller
    can attach them to the individual skill record rather than only the global
    bucket.
    """

    text = read_text(path, warnings, "frontmatter")
    fm_warnings: list[str] = []
    if not text:
        return None, fm_warnings
    match = FRONTMATTER_RE.match(text)
    if not match:
        fm_warnings.append("missing YAML frontmatter")
        return None, fm_warnings
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        fm_warnings.append(f"invalid YAML frontmatter: {exc}")
        return None, fm_warnings
    if not isinstance(data, dict):
        fm_warnings.append("frontmatter is not a mapping")
        return None, fm_warnings
    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not name.strip():
        fm_warnings.append("frontmatter name is missing or empty")
    if not isinstance(description, str) or not description.strip():
        fm_warnings.append("frontmatter description is missing or empty")
    return data, fm_warnings


def _has_direct_skill_packages(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    return any(
        child.is_dir() and (child / "SKILL.md").is_file()
        for child in directory.iterdir()
        if child.is_dir()
    )


def _has_bucket_structure(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    return any(
        child.is_dir() and _has_direct_skill_packages(child)
        for child in directory.iterdir()
        if child.is_dir()
    )


def _inside_monorepo_skills(candidate: Path) -> bool:
    """True when ``candidate`` sits beneath a ``<root>/skills/<bucket>`` tree."""

    for ancestor in candidate.parents:
        nested = ancestor / "skills"
        if nested.is_dir() and _has_bucket_structure(nested):
            return True
    return False


def resolve_root(
    explicit: Optional[Path] = None,
    env: Optional[str] = None,
    start_script: Optional[Path] = None,
) -> Path:
    """Resolve the catalog root without assuming a fixed ancestor depth.

    Priority: explicit ``--root`` > ``ZAGENTIC_ROOT`` env > location-derived.
    The location-derived root is the directory that holds the skill packages.
    Detection is content-based: a flat install keeps packages directly under a
    ``skills`` directory (the package's parent); a monorepo checkout nests them
    under ``<root>/skills/<bucket>``.  We never rely on a directory being named
    ``skills`` -- a bucket directory is structurally identical to a flat skills
    root (both have direct ``<child>/SKILL.md`` packages), so the monorepo case
    is distinguished by the presence of a wrapping ``skills/`` tree above the
    candidate, not by its name.
    """

    if explicit is not None:
        return Path(explicit).resolve()
    if env:
        return Path(env).resolve()
    here = (start_script or Path(__file__)).resolve()
    package_dir = here.parent.parent  # the <skill> package directory
    flat_root = package_dir.parent  # the <skills> directory in a flat install
    if _has_direct_skill_packages(flat_root) and not _inside_monorepo_skills(flat_root):
        return flat_root
    for ancestor in package_dir.parents:
        nested = ancestor / "skills"
        if nested.is_dir() and _has_bucket_structure(nested):
            return ancestor
    return flat_root


def detect_layout(root: Path) -> Optional[str]:
    """Return ``installed-flat`` or ``monorepo-dev``; ``None`` if no skills found."""

    if _has_direct_skill_packages(root):
        return "installed-flat"
    if (root / "skills").is_dir() and _has_bucket_structure(root / "skills"):
        return "monorepo-dev"
    return None


def skill_files(root: Path, layout: str) -> list[Path]:
    """Enumerate SKILL.md paths deterministically and reject symlink escape."""

    if layout == "installed-flat":
        files = [
            child / "SKILL.md"
            for child in sorted(root.iterdir())
            if child.is_dir() and (child / "SKILL.md").is_file()
        ]
    else:
        skills_dir = root / "skills"
        files = [
            path
            for path in sorted(skills_dir.rglob("SKILL.md"))
            if not any(part.startswith(".") for part in path.relative_to(skills_dir).parts)
        ]
    resolved_root = root.resolve()
    return [
        path for path in files if path.resolve().is_relative_to(resolved_root)
    ]


def discover_catalog(root: Path) -> dict[str, Any]:
    """Return the current skill catalog as a deterministic, non-persistent view."""

    root = root.resolve()
    layout = detect_layout(root)
    skills: list[dict[str, Any]] = []
    warnings: list[str] = []

    if layout is None:
        return {
            "schema": DISCOVERY_SCHEMA,
            "catalog_present": False,
            "skills_root": root.as_posix(),
            "layout": None,
            "skills": [],
            "warnings": sorted(warnings),
            "diagnostics": [
                "catalog root contains no skill packages; pass --root to point "
                "Composer at the directory that holds the installed skills."
            ],
        }

    for skill_md in skill_files(root, layout):
        skill_dir = skill_md.parent
        directory = skill_dir.relative_to(root).as_posix()
        leaf_directory = skill_dir.name
        frontmatter, fm_warnings = parse_frontmatter(skill_md, warnings)
        declared_name = frontmatter.get("name") if isinstance(frontmatter, dict) else None
        skill_warnings: list[str] = list(fm_warnings)
        if isinstance(declared_name, str) and declared_name != leaf_directory:
            skill_warnings.append(
                f"frontmatter name {declared_name!r} does not match directory {leaf_directory!r}"
            )
        declared_metadata = {
            field: frontmatter.get(field) if isinstance(frontmatter, dict) else None
            for field in CAPABILITY_METADATA_FIELDS
        }
        is_zagentic = (
            isinstance(frontmatter, dict)
            and frontmatter.get("source") == ZAGENTIC_SOURCE
        )
        skills.append(
            {
                "name": declared_name if isinstance(declared_name, str) else None,
                "directory": directory,
                "path": relative_path(root, skill_md),
                "is_zagentic": is_zagentic,
                "frontmatter": frontmatter,
                "declared": declared_metadata,
                "warnings": skill_warnings,
            }
        )

    skills.sort(key=lambda item: (item["directory"], item["path"]))
    return {
        "schema": DISCOVERY_SCHEMA,
        "catalog_present": True,
        "skills_root": root.as_posix(),
        "layout": layout,
        "skills": skills,
        "warnings": sorted(warnings),
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a read-only discovery view of installed skills."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Catalog root (directory holding the installed skills). "
        "Defaults to the skills directory derived from this script's location.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = resolve_root(
        explicit=args.root,
        env=os.environ.get("ZAGENTIC_ROOT"),
        start_script=Path(__file__),
    )
    payload = discover_catalog(root)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if payload.get("catalog_present", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())

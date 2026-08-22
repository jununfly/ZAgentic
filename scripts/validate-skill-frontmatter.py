#!/usr/bin/env python3
"""Validate ZAgentic SKILL.md frontmatter without rewriting skill sources."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOTS = (
    (ROOT / "skills", "*/*/SKILL.md"),
    (ROOT / "personal", "*/SKILL.md"),
)
MAX_DESCRIPTION_LENGTH = 1024
CORE_FIELDS = {"name", "description"}
STANDARD_OPTIONAL_FIELDS = {
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
INVOCATION_FIELDS = {"disable-model-invocation", "argument-hint"}
ROADMAP_FIELDS = {"title", "triggers"}


def frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def require_string(data: dict[str, Any], field: str, errors: list[str]) -> None:
    if not isinstance(data.get(field), str) or not data[field].strip():
        errors.append(f"{field} must be a non-empty string")


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = frontmatter(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]

    allowed = CORE_FIELDS | STANDARD_OPTIONAL_FIELDS | INVOCATION_FIELDS
    if path.parent.name == "zj-roadmap-driven":
        allowed |= ROADMAP_FIELDS
    unknown = sorted(set(data) - allowed)
    errors.extend(f"unknown top-level field: {field}" for field in unknown)

    for field in CORE_FIELDS:
        require_string(data, field, errors)

    expected_name = path.parent.name
    if isinstance(data.get("name"), str) and data["name"] != expected_name:
        errors.append(
            f"name {data['name']!r} does not match directory {expected_name!r}"
        )
    if isinstance(data.get("name"), str) and not data["name"].startswith("zj-"):
        errors.append("name must use the zj- namespace")

    description = data.get("description")
    if isinstance(description, str):
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append("description exceeds 1024 characters")
        if "<" in description or ">" in description:
            errors.append("description must not contain angle brackets")

    if "license" in data and not isinstance(data["license"], str):
        errors.append("license must be a string")
    if "compatibility" in data and not isinstance(data["compatibility"], str):
        errors.append("compatibility must be a string")
    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("metadata must be a mapping")
    if "allowed-tools" in data:
        tools = data["allowed-tools"]
        if not isinstance(tools, (str, list)) or (
            isinstance(tools, list)
            and not all(isinstance(item, str) for item in tools)
        ):
            errors.append("allowed-tools must be a string or list of strings")
    if "disable-model-invocation" in data and not isinstance(
        data["disable-model-invocation"], bool
    ):
        errors.append("disable-model-invocation must be boolean")
    if "argument-hint" in data and not isinstance(data["argument-hint"], str):
        errors.append("argument-hint must be a string")

    if path.parent.name == "zj-roadmap-driven":
        if "title" in data and not isinstance(data["title"], str):
            errors.append("title must be a string")
        triggers = data.get("triggers")
        if not isinstance(triggers, list) or not triggers or not all(
            isinstance(item, str) and item.strip() for item in triggers
        ):
            errors.append("triggers must be a non-empty list of strings")

    sidecar = path.parent / "agents" / "openai.yaml"
    if sidecar.exists():
        try:
            sidecar_data = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"agents/openai.yaml: {exc}")
        else:
            if not isinstance(sidecar_data, dict):
                errors.append("agents/openai.yaml must be a YAML mapping")
            else:
                policy = sidecar_data.get("policy")
                if policy is not None and not isinstance(policy, dict):
                    errors.append("agents/openai.yaml policy must be a mapping")
                elif isinstance(policy, dict):
                    implicit = policy.get("allow_implicit_invocation")
                    if implicit is not None and not isinstance(implicit, bool):
                        errors.append(
                            "agents/openai.yaml policy.allow_implicit_invocation must be boolean"
                        )
                    if data.get("disable-model-invocation") is True and implicit is True:
                        errors.append(
                            "sidecar enables implicit invocation while frontmatter disables it"
                        )
    return errors


def skill_paths(arguments: list[str]) -> list[Path]:
    if arguments:
        paths = []
        for argument in arguments:
            candidate = Path(argument)
            paths.extend(
                sorted(candidate.glob("SKILL.md"))
                if candidate.is_dir()
                else [candidate]
            )
        return paths
    return sorted(
        path
        for skill_root, pattern in SKILL_ROOTS
        for path in skill_root.glob(pattern)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="skill directories or SKILL.md files")
    args = parser.parse_args()

    failures = 0
    for path in skill_paths(args.paths):
        errors = validate_skill(path)
        if errors:
            failures += 1
            for error in errors:
                print(f"{path}: {error}")
    if failures:
        print(f"Frontmatter validation failed for {failures} skill(s)")
        return 1
    print(f"Frontmatter validation passed for {len(skill_paths(args.paths))} skill(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

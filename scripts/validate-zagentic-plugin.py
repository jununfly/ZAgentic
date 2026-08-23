#!/usr/bin/env python3
"""Validate ZAgentic's bucketed plugin layout recursively.

The official plugin validator is intentionally run by ``validate-plugin.sh``
before this repository-specific validator. This validator owns only the
repository layout contract: public skills live under ``skills/<bucket>/`` and
private skills live under the root-level ``personal/`` directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PUBLIC_BUCKETS = ("engineering", "productivity", "misc", "research")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate ZAgentic's recursive skill layout."
    )
    parser.add_argument(
        "plugin_path",
        nargs="?",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Path to the ZAgentic repository (default: this script's repository)",
    )
    return parser.parse_args()


def load_manifest(plugin_root: Path, errors: list[str]) -> dict[str, Any] | None:
    path = plugin_root / ".codex-plugin" / "plugin.json"
    if not path.is_file():
        errors.append("missing `.codex-plugin/plugin.json`")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append("`.codex-plugin/plugin.json` must contain valid JSON")
        return None
    if not isinstance(payload, dict):
        errors.append("`.codex-plugin/plugin.json` must contain a JSON object")
        return None
    return payload


def reject_todo_markers(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, str):
        if "[TODO:" in value:
            errors.append(f"{path} still contains a `[TODO: ...]` placeholder")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_todo_markers(item, f"{path}[{index}]", errors)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_todo_markers(item, f"{path}.{key}", errors)


def immediate_skill_paths(
    root: Path,
    label: str,
    errors: list[str],
) -> list[Path]:
    """Return immediate child skill manifests and reject malformed nesting."""

    if not root.is_dir():
        errors.append(f"missing {label} directory: {root}")
        return []

    manifests: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name):
        if child.name.startswith("."):
            continue
        if child.is_file() and child.name == "README.md":
            continue
        if not child.is_dir():
            errors.append(f"{label} contains a non-directory entry: {child}")
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{child} is missing SKILL.md")
            continue
        manifests.append(skill_md)

    return manifests


def discover_skill_manifests(plugin_root: Path, errors: list[str]) -> list[Path]:
    public_root = plugin_root / "skills"
    personal_root = plugin_root / "personal"
    manifests: list[Path] = []

    if public_root.is_dir():
        known_buckets = set(PUBLIC_BUCKETS) | {"personal"}
        for child in sorted(public_root.iterdir(), key=lambda path: path.name):
            if (
                child.is_dir()
                and not child.name.startswith(".")
                and child.name not in known_buckets
            ):
                errors.append(f"unsupported public bucket: {child}")

    for bucket in PUBLIC_BUCKETS:
        manifests.extend(
            immediate_skill_paths(
                public_root / bucket,
                f"public bucket {bucket!r}",
                errors,
            )
        )

    # A personal skill under skills/ would be inside the public plugin scope.
    misplaced_personal = public_root / "personal"
    if misplaced_personal.exists():
        errors.append(
            f"personal skills must live at root-level {personal_root}, not {misplaced_personal}"
        )

    manifests.extend(immediate_skill_paths(personal_root, "root-level personal", errors))

    # Catch a SKILL.md hidden below the required two-level layout instead of
    # silently ignoring it. Resources below a skill are allowed, but a second
    # SKILL.md would create an ambiguous install target.
    expected_parents = {
        *(public_root / bucket for bucket in PUBLIC_BUCKETS),
        personal_root,
    }
    for skill_md in plugin_root.rglob("SKILL.md"):
        if ".git" in skill_md.parts:
            continue
        if skill_md in manifests:
            continue
        if skill_md.parent.parent not in expected_parents:
            errors.append(f"SKILL.md is outside the supported skill layout: {skill_md}")

    return manifests


def validate_manifest_contract(
    manifest: dict[str, Any] | None,
    plugin_root: Path,
    errors: list[str],
) -> None:
    if manifest is None:
        return
    if manifest.get("skills") != "./skills/":
        errors.append("plugin.json field `skills` must resolve to `./skills/`")
    if not (plugin_root / "skills").is_dir():
        errors.append("plugin.json field `skills` points to a missing `skills/` directory")
    reject_todo_markers(manifest, "$", errors)


def validate_frontmatter(
    plugin_root: Path,
    manifests: list[Path],
    errors: list[str],
) -> None:
    validator = plugin_root / "scripts" / "validate-skill-frontmatter.py"
    if not validator.is_file():
        errors.append(f"missing repository frontmatter validator: {validator}")
        return

    result = subprocess.run(
        [sys.executable, str(validator), *(str(path) for path in manifests)],
        cwd=plugin_root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    if result.returncode != 0:
        errors.append("repository frontmatter validation failed")


def validate(plugin_root: Path) -> list[str]:
    errors: list[str] = []
    manifest = load_manifest(plugin_root, errors)
    validate_manifest_contract(manifest, plugin_root, errors)
    manifests = discover_skill_manifests(plugin_root, errors)
    validate_frontmatter(plugin_root, manifests, errors)
    return errors


def main() -> int:
    args = parse_args()
    plugin_root = args.plugin_path.expanduser().resolve()
    errors = validate(plugin_root)
    if errors:
        print("ZAgentic recursive validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    manifests = discover_skill_manifests(plugin_root, [])
    print(
        "ZAgentic recursive validation passed: "
        f"{plugin_root} ({len(manifests)} skills)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

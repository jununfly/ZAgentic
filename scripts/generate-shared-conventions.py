#!/usr/bin/env python3
"""Inline the shared skill conventions into each consuming skill's SKILL.md.

Repo-root, dev-time tool. Not shipped inside any skill: an installed skill
carries only its generated block, so runtime never depends on ``docs/``.

A consuming skill declares ``## Shared Conventions`` (fenced JSON) in its
SKILL.md body. Its ``consumes`` list selects which core keys of the rule source
are inlined into a delimited ``<!-- BASE_RULES_START/END -->`` block. The
declaration is human-authored; the block is generated. This tool writes only
the block and never touches the declaration.

Usage:
    python3 scripts/generate-shared-conventions.py                 # write blocks
    python3 scripts/generate-shared-conventions.py --check        # byte-equal only
    python3 scripts/generate-shared-conventions.py --root PATH     # explicit repo root
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULE_SOURCE_REL = "docs/skill-conventions/skill-conventions.json"
START_MARKER = "<!-- BASE_RULES_START -->"
END_MARKER = "<!-- BASE_RULES_END -->"
GENERATED_NOTICE = (
    "<!-- GENERATED from docs/skill-conventions/skill-conventions.json "
    "-- do not edit by hand; re-run the generator. -->"
)
DECL_RE = re.compile(
    r"^## Shared Conventions\s*\n+```json\n(.*?)\n```", re.MULTILINE | re.DOTALL
)


def parse_rule_source(root: Path) -> dict:
    path = root / RULE_SOURCE_REL
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def discover_consumers(root: Path, rule_source_rel: str) -> list[tuple[Path, dict]]:
    """Find SKILL.md files whose Shared Conventions declaration names rule_source."""
    skills_dir = root / "skills"
    found: list[tuple[Path, dict]] = []
    if not skills_dir.is_dir():
        return found
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        match = DECL_RE.search(text)
        if match is None:
            continue
        decl = json.loads(match.group(1))
        if decl.get("rule_source") != rule_source_rel:
            continue
        found.append((skill_md, decl))
    return found


def render_block(source: dict, consumes: list[str]) -> str:
    """Render the deterministic generated block for one consumer."""
    core_keys = source["core_keys"]
    unknown = [k for k in consumes if k not in core_keys]
    if unknown:
        raise ValueError(f"consumes has keys outside core: {unknown}")
    # Preserve core_keys order (not the caller's) for stable byte output.
    selected = {k: source["core"][k] for k in core_keys if k in consumes}
    payload = {
        "$generated": {
            "source": RULE_SOURCE_REL,
            "schema_version": source["schema_version"],
            "consumes": [k for k in core_keys if k in consumes],
        },
        "core": selected,
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return "\n".join([START_MARKER, GENERATED_NOTICE, "```json", body, "```", END_MARKER])


def upsert_block(content: str, block: str) -> str:
    """Idempotently replace the marker block (roadmap.py:4503-4531 precedent)."""
    start = content.find(START_MARKER)
    end = content.find(END_MARKER, start + len(START_MARKER)) if start >= 0 else -1
    if start >= 0 and end >= 0:
        end += len(END_MARKER)
        return content[:start] + block + content[end:]
    if start >= 0 and end < 0:
        # START present but END missing (truncated / half-write): replace from
        # START to EOF so a second marker is never appended.
        return content[:start] + block + "\n"
    # No marker: append as a new section at EOF.
    return content.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--check", action="store_true",
                    help="do not write; exit non-zero if any block is missing or stale")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    try:
        source = parse_rule_source(root)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read rule source: {exc}", file=sys.stderr)
        return 2

    consumers = discover_consumers(root, RULE_SOURCE_REL)
    if not consumers:
        print("ERROR: no consuming skill declares rule_source", file=sys.stderr)
        return 2

    drift: list[str] = []
    for skill_md, decl in consumers:
        rel = skill_md.relative_to(root)
        block = render_block(source, decl["consumes"])
        content = skill_md.read_text(encoding="utf-8")
        updated = upsert_block(content, block)
        if args.check:
            if updated != content:
                drift.append(str(rel))
        elif updated != content:
            with open(skill_md, "w", encoding="utf-8") as fh:
                fh.write(updated)
            print(f"generated: {rel} (consumes={decl['consumes']})")
        else:
            print(f"unchanged: {rel}")

    if args.check:
        if drift:
            print(f"CHECK FAILED: {len(drift)} skill(s) have stale/missing BASE_RULES block:",
                  file=sys.stderr)
            for rel in drift:
                print(f"  - {rel}", file=sys.stderr)
            return 1
        print(f"CHECK OK: {len(consumers)} skill(s) byte-equal to rule source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Skill runtime-closure gate for the ZAgentic source repo.

A skill is a published, self-contained unit: it is copied into agent product
directories (codex / workbuddy / claude) and runs WITHOUT the ZAgentic source
repo present. This script confirms that no skill reaches back into the source
repo's `docs/` (or other source paths) at runtime.

It deliberately uses *precise* fingerprints rather than a broad "ZAgentic"
string match, because that string also appears in brand strings, target-repo
operations, and intentional "run this skill inside the ZAgentic repo" rules.

Fingerprints (see docs/designs/zj-skill-runtime-closure.md):
  ERROR  upward relative escape to a docs/ dir:  (../)+docs
  ERROR  ZAgentic-specific ontology path:        docs/ontology
  WARN   absolute source-repo path (review):     /Users/.../ZAgentic/ ,
                                                 /home/.../jununfly/ , C:\\...
  WARN   unresolved reference:                   a path-bearing `example/x.json`
                                                 whose target exists in neither
                                                 the skill install nor the repo.
                                                 Bare filenames and paths rooted
                                                 in the target project (docs/,
                                                 .claude/, agents/, ...) are not
                                                 flagged; those name the repo the
                                                 skill runs in, not skill content.

Scan scope: the `skills/` tree, excluding dev/test scopes
(tests/, fixtures/, artifacts/, evals/, __pycache__, node_modules, binaries).
`personal/` is intentionally NOT scanned here — it is installable personal
setup and is out of the public governance scope.

Usage:
  python3 scripts/check-skill-runtime-closure.py [--repo PATH] [--strict]

Exit code: 0 if no ERROR (WARN alone is advisory); 1 if any ERROR.
With --strict, WARN also fails the gate.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Directories that are dev/test scope, not the skill's runtime surface.
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", "tests", "fixtures",
    "artifacts", "evals", ".venv", "venv",
}

# Inline suppression: a line containing this token is skipped.
SUPPRESS = re.compile(r"#\s*closure-allow\b")

# ERROR: relative escape upward out of the skill into a repo docs/ dir.
RE_UP_ESCAPE = re.compile(r"(?:\.\./){1,}docs")
# ERROR: ZAgentic-specific ontology path (not a generic target-repo path).
RE_ONTOLOGY = re.compile(r"docs/ontology")
# WARN: absolute source-repo path (advisory review signal).
RE_ABS_SOURCE = re.compile(
    r"(?:/Users/|/home/|/root/|C:\\)[^\"'<>\s]*/(?:ZAgentic|jununfly)/"
)

# Missing-reference check: a skill may point at a file (contract, script, schema,
# template) that itself must be present somewhere resolvable. A pointer at a file
# that exists nowhere is a broken reference even when it never escapes the skill
# dir -- which is exactly the class the escape patterns above cannot see.
RE_REF_PATH = re.compile(r"`([^`\s]+?\.(?:md|json|ya?ml|py|sh|js|ts))`")
# Placeholder/example shapes ("<skill>/SKILL.md", "*.md", "…/foo.py") are not real referents.
RE_PLACEHOLDER = re.compile(r"[<>*{}?\[\]]|…")
# Path prefixes that live in the project the skill RUNS IN, not in the skill
# install itself. Pointing there is not evidence of a broken skill reference.
TARGET_PROJECT_ROOTS = (
    "docs/", ".claude/", ".codex/", ".workbuddy/", ".zj-out-of-scope/",
    ".zj-retros/", "safe-bin/", "agents/", "discussions/", "skills-outputs/",
    # Layouts belonging to the repo a docs skill maintains, not to the skill:
    "handbook/", "architecture/", "views/", "navigation/", "app/",
)

ERROR_PATTERNS = (
    ("SKILL_ESCAPE_DOCS", RE_UP_ESCAPE, "relative escape out of skill into source docs/"),
    ("SKILL_ZAGENTIC_ONTOLOGY", RE_ONTOLOGY, "ZAgentic-specific docs/ontology path"),
)
WARN_PATTERNS = (
    ("SKILL_ABS_SOURCE_PATH", RE_ABS_SOURCE, "absolute source-repo path (review)"),
)


def _is_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(4096)
    except OSError:
        return True
    return b"\x00" in chunk


def _find_repo_root(start: str) -> str:
    cur = os.path.abspath(start)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        if os.path.isdir(os.path.join(cur, "skills")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def _skill_root_of(rel: str, root: str) -> str | None:
    """`<skill-install>` dir for rel like skills/<bucket>/<skill>/<...>."""
    parts = rel.split(os.sep)
    if parts[0] == "skills" and len(parts) >= 3:
        return os.path.join(root, "skills", parts[1], parts[2])
    return None


def _ref_resolves(ref: str, bases: list[str]) -> bool:
    return any(os.path.exists(os.path.join(b, ref)) for b in bases if b)


# Cache of <skill-install-root> -> its file paths relative to that root.
_SKILL_FILES: dict[str, set[str]] = {}


def _skill_files(skill_root: str) -> set[str]:
    if skill_root not in _SKILL_FILES:
        found: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(skill_root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fn), skill_root)
                found.add(rel.replace(os.sep, "/"))
        _SKILL_FILES[skill_root] = found
    return _SKILL_FILES[skill_root]


def scan_file(path: str, rel: str, findings: list[dict], root: str) -> None:
    if _is_binary(path):
        return
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return
    for lineno, line in enumerate(lines, 1):
        if SUPPRESS.search(line):
            continue
        for code, pat, hint in ERROR_PATTERNS:
            m = pat.search(line)
            if m:
                findings.append({
                    "severity": "ERROR", "code": code, "path": rel,
                    "line": lineno, "match": m.group(0), "hint": hint,
                })
        for code, pat, hint in WARN_PATTERNS:
            m = pat.search(line)
            if m:
                findings.append({
                    "severity": "WARN", "code": code, "path": rel,
                    "line": lineno, "match": m.group(0), "hint": hint,
                })
        # A referenced file must resolve, or exist somewhere inside the skill
        # install. Only *path-bearing* references are enforced: a bare filename
        # may legitimately name a target-project artifact the skill operates on
        # rather than ships (UI-BRIEF.md, input.json), so it is not evidence of
        # a broken pointer.
        skill_root = _skill_root_of(rel, root)
        for ref in RE_REF_PATH.findall(line):
            if ref.startswith(("/", "~", "#", "$", "./")) or "://" in ref:
                continue
            if RE_PLACEHOLDER.search(ref):
                continue
            norm = ref.replace(os.sep, "/")
            if "/" not in norm:
                continue
            if norm.startswith(TARGET_PROJECT_ROOTS):
                continue
            if _ref_resolves(ref, [os.path.dirname(path), skill_root, root]):
                continue
            if skill_root and norm in _skill_files(skill_root):
                continue
            findings.append({
                "severity": "WARN", "code": "SKILL_UNRESOLVED_REF", "path": rel,
                "line": lineno, "match": ref,
                "hint": "referenced file resolves nowhere in skill or repo",
            })


def scan_tree(root: str, skills_dir: str, findings: list[dict]) -> None:
    for dirpath, dirnames, filenames in os.walk(skills_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            scan_file(full, rel, findings, root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Skill runtime-closure gate")
    ap.add_argument("--repo", default=None, help="repo root (default: cwd or walk up)")
    ap.add_argument("--strict", action="store_true",
                    help="treat WARN as a gate failure too")
    args = ap.parse_args(argv)

    root = _find_repo_root(args.repo or os.getcwd())
    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        print(f"skills/ not found under {root}; nothing to scan", file=sys.stderr)
        return 0

    findings: list[dict] = []
    scan_tree(root, skills_dir, findings)

    errors = [f for f in findings if f["severity"] == "ERROR"]
    warns = [f for f in findings if f["severity"] == "WARN"]

    for f in sorted(findings, key=lambda x: (x["path"], x["line"])):
        print(f"{f['severity']:5} {f['code']:28} {f['path']}:{f['line']} "
              f"matched={f['match']!r} — {f['hint']}")

    print(f"\n scanned: {skills_dir}")
    print(f" findings: {len(errors)} ERROR, {len(warns)} WARN")

    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

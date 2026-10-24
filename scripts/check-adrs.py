#!/usr/bin/env python3
r"""Verify the evidence layer inside `docs/zj-adr/*.md` resolves against the repo.

Why this exists
---------------
ADRs are decision records. Their evidence layer cites skills, commits and
paths. `scripts/check-docs-dangling-refs.py` only scans markdown navigation
links and bare prose paths, and it suppresses the retired namespaces
(`skills-outputs/`, `docs/plans/`) that ADRs legitimately cite as history — so
a skill name or commit sha referenced in an ADR body is invisible to CI. A
wrong commit sha or a skill name that no longer exists is silent fact drift:
the record *looks* evidenced but points nowhere. This script makes that layer
mechanically checkable, so "ADR is part of the docs review surface" is enforced
on every push / pull_request rather than by memory.

Severity model (deliberately asymmetric)
----------------------------------------
* **ERROR — a commit sha cited as evidence** that `git cat-file -e` cannot
  resolve. A `commit <sha>` or backtick `<sha>` reference is a promise about
  the evidence trail; a dead one is always a defect.
* **WARN — a `zj-*` token that is not an installed skill**
  (`skills/<bucket>/<name>/SKILL.md` absent). Usually a renamed/retired skill
  name still referenced, or a path fragment; surfaced for review, never
  blocking. (A missing skill is often a *legitimate* historical reference — the
  skill was absorbed or renamed — which is exactly why it is WARN and not ERROR:
  it tells the reviewer "confirm this name is still correct", without ever
  turning a clean ADR red.)

Implementation notes
--------------------
* Skill existence is judged by `git ls-files`, not the filesystem, so it is
  checkout-independent and matches CI exactly.
* A tiny `ALLOW_MISSING` set covers tokens that are directory names
  (`zj-adr`) or documented renames, kept small and reviewed by hand.

Usage
-----
    python3 scripts/check-adrs.py [--repo-root PATH]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ADR_DIR = Path("docs") / "zj-adr"

# Tokens that are NOT skills but legitimately appear in ADR bodies.
# `zj-adr` is the directory itself; the rest are documented renames or
# helper scripts. Keep this set small and reviewed.
ALLOW_MISSING = {
    "zj-adr",                       # the docs/zj-adr/ directory name
    "zj-git-bypass-safe-delete",     # a helper script under skills/engineering, not a skill
    "zj-hv-analysis",                # documented rename -> zj-systematic-research
    "zj-research-report",            # documented rename -> zj-tech-research-report
}

# `commit <sha>` (explicit) and `<sha>` inside backticks.
COMMIT_EXPLICIT_RE = re.compile(r"commit\s+([0-9a-f]{7,40})\b", re.IGNORECASE)
COMMIT_BACKTICK_RE = re.compile(r"`([0-9a-f]{7,40})`")
SKILL_RE = re.compile(r"zj-[a-z][a-z0-9-]*")


def _git(repo_root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            env=env,
        )
    except OSError:
        return ""
    return proc.stdout


def _installed_skills(repo_root: Path) -> set[str]:
    out = _git(repo_root, "ls-files", "skills/*/*/SKILL.md")
    names: set[str] = set()
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) >= 3 and parts[0] == "skills":
            names.add(parts[2])
    return names


def _commit_exists(repo_root: Path, sha: str) -> bool:
    env = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "-e", sha],
        capture_output=True,
        env=env,
    )
    return proc.returncode == 0


def scan(repo_root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    skills = _installed_skills(repo_root)
    adr_root = repo_root / ADR_DIR
    if not adr_root.is_dir():
        print(f"ERROR: no {ADR_DIR} directory under {repo_root}")
        return errors, warns
    for md in sorted(adr_root.glob("*.md")):
        rel = md.relative_to(repo_root)
        for lineno, line in enumerate(
            md.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            # --- commit references (ERROR) ---
            for m in COMMIT_EXPLICIT_RE.finditer(line):
                sha = m.group(1)
                if not _commit_exists(repo_root, sha):
                    errors.append(f"{rel}:{lineno}: [commit] {sha} not found")
            for m in COMMIT_BACKTICK_RE.finditer(line):
                sha = m.group(1)
                if not _commit_exists(repo_root, sha):
                    errors.append(f"{rel}:{lineno}: [commit] {sha} (backtick) not found")
            # --- skill-name references (WARN) ---
            for m in SKILL_RE.finditer(line):
                start = m.start()
                # A zj- token that is a path component (prev "/") or part of a
                # larger composite identifier such as a work-item name
                # (prev "-") or a file extension boundary (prev ".") is not a
                # standalone skill reference — e.g. `scripts/zj-git`,
                # `../designs/zj-composer-plan-product-form.md`,
                # `work-zj-...-scope`. Only independent mentions are checked.
                if start > 0 and line[start - 1] in "/.-":
                    continue
                name = m.group(0)
                if name in ALLOW_MISSING or name in skills:
                    continue
                warns.append(f"{rel}:{lineno}: [skill] {name} not an installed skill")
    return errors, warns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verify ADR hard references")
    parser.add_argument("--repo-root", default=None, help="defaults to the parent of scripts/")
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parent.parent
    )
    if not (repo_root / ADR_DIR).is_dir():
        print(f"ERROR: no {ADR_DIR} directory under {repo_root}")
        return 1

    errors, warns = scan(repo_root)
    for line in errors:
        print(f"ERROR: {line}")
    for line in warns:
        print(f"WARN: {line}")
    print(
        f"check-adrs: {len(errors)} bad commit reference(s), "
        f"{len(warns)} unresolved skill name(s) (repo_root={repo_root})"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Disposition guard for zj-discuss discussion folders (Phase 4).

A discussion folder (``discussions/<slug>/``) is transient process material.
Before it can be retired, two mechanical preconditions must hold (sub-02 Q3
findings):

1. every sub-document is concluded (``状态协议`` ∈ {DONE, DONE_WITH_CONCERNS});
2. the folder is committed to git (no uncommitted changes) — otherwise deletion
   has RPO = total loss with no reflog recovery.

Optionally a ``zj-docs-ontology`` receipt (``--receipt``) must exist. Deletion is
never a raw ``rm``: ``--archive`` moves the folder under
``.discussions-archive/<slug>/`` via ``git mv`` (a recoverable recycle window);
``--dry-run`` only reports. The default safe action reports without mutating.

Usage:

    python3 dispose.py <discussions-folder> [--dry-run] [--archive] [--receipt PATH]
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

STATUS_RE = re.compile(r"状态协议[*`\s]*[：:][*`\s]*([A-Za-z_]+)")
CLAIMED_STATUS = {"DONE", "DONE_WITH_CONCERNS"}


def _git(*args):
    env = dict(os.environ)
    env.pop("NODE_OPTIONS", None)  # mirror `env -u NODE_OPTIONS git`
    proc = subprocess.run(
        ["git", *args], capture_output=True, text=True, env=env
    )
    return proc


def find_subdocs(folder):
    folder = Path(folder)
    return sorted(p for p in folder.glob("sub-*.md") if p.is_file())


def all_concluded(folder):
    """Return (ok, problems) — every sub-*.md must carry a claimed status."""
    problems = []
    subs = find_subdocs(folder)
    if not subs:
        return False, ["文件夹内无任何 sub-*.md 子文档"]
    for sub in subs:
        m = STATUS_RE.search(sub.read_text(encoding="utf-8"))
        if not m:
            problems.append("{} 缺 状态协议（未结论）".format(sub.name))
            continue
        if m.group(1).strip() not in CLAIMED_STATUS:
            problems.append("{} 状态={}（未收敛，不得处置）".format(sub.name, m.group(1).strip()))
    return (len(problems) == 0), problems


def git_is_clean(folder, git_fn=None):
    git_fn = git_fn or _git
    proc = git_fn("status", "--porcelain", "--", str(folder))
    if proc.returncode != 0:
        return False, "git status 失败：{}".format(proc.stderr.strip() or "exit {}".format(proc.returncode))
    if proc.stdout.strip():
        return False, "文件夹有未提交改动（须先 git add && commit）：\n{}".format(proc.stdout.strip())
    return True, ""


def safe_to_dispose(folder, receipt=None, git_fn=None):
    """Return (ok, reasons). Pure-checkable: inject git_fn to avoid real git."""
    reasons = []
    ok, probs = all_concluded(folder)
    if not ok:
        reasons.append("子文档未全部结论：")
        reasons.extend("  - {}".format(p) for p in probs)
    clean, msg = git_is_clean(folder, git_fn=git_fn)
    if not clean:
        reasons.append(msg)
    if receipt is not None and not Path(receipt).exists():
        reasons.append("缺失沉淀回执（--receipt）：{}".format(receipt))
    return (len(reasons) == 0), reasons


def archive(folder, archive_root=None, git_fn=None):
    folder = Path(folder)
    git_fn = git_fn or _git
    archive_root = Path(archive_root or folder.parent / ".discussions-archive")
    dest = archive_root / folder.name
    if dest.exists():
        return False, "归档目标已存在：{}".format(dest)
    archive_root.mkdir(parents=True, exist_ok=True)
    proc = git_fn("mv", str(folder), str(dest))
    if proc.returncode != 0:
        return False, "git mv 失败：{}".format(proc.stderr.strip())
    return True, "已归档到 {}".format(dest)


def main(argv=None, git_fn=None):
    parser = argparse.ArgumentParser(description="Disposition guard for a zj-discuss folder.")
    parser.add_argument("folder", help="discussions/<slug>/ folder to retire")
    parser.add_argument("--dry-run", action="store_true", help="only report; never mutate")
    parser.add_argument("--archive", action="store_true", help="git mv into .discussions-archive/<slug>/")
    parser.add_argument("--receipt", help="require this zj-docs-ontology receipt file to exist")
    parser.add_argument("--archive-root", help="override archive root (default: <parent>/.discussions-archive)")
    args = parser.parse_args(argv)

    folder = Path(args.folder)
    if not folder.is_dir():
        print("refused: folder not found: {}".format(folder), file=sys.stderr)
        return 2

    ok, reasons = safe_to_dispose(folder, receipt=args.receipt, git_fn=git_fn)
    if not ok:
        print("REFUSED — 处置前检查未通过：", file=sys.stderr)
        for r in reasons:
            print("  {}".format(r), file=sys.stderr)
        return 1

    if args.dry_run:
        print("SAFE — 可处置（dry-run，未改动）：")
        print("  {}".format(folder))
        if args.archive:
            print("  将 git mv 到 {}".format(Path(args.archive_root or folder.parent / ".discussions-archive") / folder.name))
        return 0

    if args.archive:
        ok_mv, msg = archive(folder, args.archive_root)
        if not ok_mv:
            print("refused: {}".format(msg), file=sys.stderr)
            return 2
        print(msg)
        return 0

    # Default safe action: report, never delete.
    print("SAFE — 可处置。默认不删除（用 --archive 归档 / 由 Human 确认后删）：")
    print("  {}".format(folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

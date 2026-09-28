#!/usr/bin/env python3
"""R4 — zj-discuss 复盘度量注册表：纯可重算度量计算机（只读，不写不注入）。

给定 discussions/<slug>/ 目录（或单个子文档路径），按
docs/designs/zj-discuss/design.md §9 的单一 schema 重算度量。

设计要点（与 §8 边界一致）：本脚本**只读磁盘文件、不写入、不注入任何
digest / learnings**。所有字段随时可从磁盘重算，无隐藏状态（recomputable 恒 true）。
它解析的是现有稳定结构（视角区块、`视角来源` 标注、`## conclusion`、`## 解决思路`），
与「结构性 digest 注入」是 §8 已显式推迟的独立特性，互不影响。

Closure 口径（已与用户确认，零模板改动）：
- 子文档级：open_questions_total = 1（该子文档作为一单位）；closed = 1 当且仅当
  conclusion 状态协议 ∈ {DONE, DONE_WITH_CONCERNS}；closure_rate = closed / 1。
- 讨论级：total = 子文档数；closed = 已 claim 收敛的子文档数；closure_rate = closed / total。

Usage:

    python3 metrics.py <discussions-dir | sub-doc-path>
    # prints a JSON metric record (discussion-level or sub-doc-level)
"""

import argparse
import json
import re
import sys
from pathlib import Path

CROSS_SESSION_MARKER = "跨会话独立Agent"
PREVIEW_MARKER = "同会话SubAgent(低权重)"
CLAIMED_STATUS = {"DONE", "DONE_WITH_CONCERNS"}

# A viewpoint block heading is `### 视角：X` (level 2/3 + 视角 + colon).
# The `## 视角 briefing` section (no colon) and `## 主力AI 整合立场` (no 视角)
# must NOT match.
VIEWPOINT_HEADING_RE = re.compile(r"^#{2,3}\s*视角\s*[：:]")
SOURCE_RE = re.compile(r"视角来源\s*[：:]\s*(.+)")
STATUS_RE = re.compile(r"状态协议\s*[：:]\s*\*+\s*([A-Za-z_]+)")
ROLES_LINE_RE = re.compile(r"声明必需角色集\s*[：:]\s*(.+)")
STRIP_CHARS = " \t`\"'*_"


def split_sections(text):
    """Split Markdown into (heading, body) pairs by ATX headings."""
    sections = []
    heading = None
    body = []
    for line in text.splitlines():
        if line.startswith("#"):
            if heading is not None:
                sections.append((heading, "\n".join(body)))
            heading = line.strip()
            body = []
        else:
            body.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body)))
    return sections


def _section_body(sections, startswith):
    for heading, body in sections:
        if heading.startswith(startswith):
            return body
    return ""


def _viewpoint_blocks(sections):
    """Return (heading, body) for `### 视角：X` blocks only."""
    blocks = []
    for heading, body in sections:
        if VIEWPOINT_HEADING_RE.match(heading):
            blocks.append((heading, body))
    return blocks


def _roles_used(text):
    m = ROLES_LINE_RE.search(text)
    if not m:
        return []
    # findall tolerates bold markers / spaces / Chinese prose around the keys.
    return re.findall(r"[A-Za-z0-9]+", m.group(1))


def _block_chars(heading, body):
    """Character volume of one viewpoint block as it sits on disk.

    split_sections yields the heading (no newline) and the body string with its
    internal + trailing newlines intact, so the on-disk block is exactly
    ``heading + "\\n" + body``. The inter-block separator newline belongs to the
    next block's body, not this one, so this reproduces the file content exactly.
    """
    return len(heading) + 1 + len(body)


def compute_subdoc_metrics(subdoc_path):
    """Compute the §9 schema for one sub-document. Recomputable: true."""
    subdoc_path = Path(subdoc_path)
    text = subdoc_path.read_text(encoding="utf-8")
    sections = split_sections(text)
    blocks = _viewpoint_blocks(sections)

    roles = _roles_used(text)
    viewpoint_count = 0
    raw_chars = 0
    for heading, body in blocks:
        raw_chars += _block_chars(heading, body)
        sm = SOURCE_RE.search(body)
        if sm and sm.group(1).strip(STRIP_CHARS) == CROSS_SESSION_MARKER:
            viewpoint_count += 1

    conclusion_body = _section_body(sections, "## conclusion")
    solution_chars = len(conclusion_body.strip())
    status_m = STATUS_RE.search(conclusion_body)
    status = status_m.group(1).strip() if status_m else None
    closed = 1 if status in CLAIMED_STATUS else 0

    return {
        "sub_doc_id": subdoc_path.stem,
        "roles_used": roles,
        "viewpoint_count": viewpoint_count,
        "open_questions_total": 1,
        "open_questions_closed": closed,
        "closure_rate": (closed / 1.0),
        "raw_volume_chars": raw_chars,
        "solution_volume_chars": solution_chars,
        "compression_ratio": (raw_chars / solution_chars) if solution_chars else None,
        "recomputable": True,
    }


def _discover_subdocs(discussions_dir):
    discussions_dir = Path(discussions_dir)
    subs = []
    for p in sorted(discussions_dir.glob("*.md")):
        if p.name.lower() == "master.md":
            continue
        subs.append(p)
    return subs


def compute_discussion_metrics(discussions_dir):
    """Compute the §9 schema for a whole discussions/<slug>/ folder."""
    discussions_dir = Path(discussions_dir)
    slug = discussions_dir.name
    subdocs = _discover_subdocs(discussions_dir)
    sub_metrics = [compute_subdoc_metrics(p) for p in subdocs]

    master = discussions_dir / "MASTER.md"
    solution_chars = 0
    if master.exists():
        msections = split_sections(master.read_text(encoding="utf-8"))
        solution_chars = len(_section_body(msections, "## 解决思路").strip())

    roles_union = sorted({r for s in sub_metrics for r in s["roles_used"]})
    viewpoint_count = sum(s["viewpoint_count"] for s in sub_metrics)
    raw_chars = sum(s["raw_volume_chars"] for s in sub_metrics)
    total = len(sub_metrics)
    closed = sum(s["open_questions_closed"] for s in sub_metrics)
    closure_rate = (closed / total) if total else 0.0

    return {
        "discussion_slug": slug,
        "roles_used": roles_union,
        "viewpoint_count": viewpoint_count,
        "open_questions_total": total,
        "open_questions_closed": closed,
        "closure_rate": closure_rate,
        "raw_volume_chars": raw_chars,
        "solution_volume_chars": solution_chars,
        "compression_ratio": (raw_chars / solution_chars) if solution_chars else None,
        "recomputable": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="R4 recomputable metrics registry for zj-discuss."
    )
    parser.add_argument(
        "path", help="discussions/<slug>/ directory or a sub-document .md path"
    )
    args = parser.parse_args(argv)
    p = Path(args.path)
    if p.is_dir():
        record = compute_discussion_metrics(p)
    elif p.is_file():
        record = compute_subdoc_metrics(p)
    else:
        print("missing: {}".format(p), file=sys.stderr)
        return 2
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generic structural-gate primitives for zj-doc-collab.

Parameterized by consumer vocabulary (defaults = zj-discuss values) so any
consumer can supply its own markers / statuses / placeholder vocabulary without
forking the mechanism. The *mechanism* (source-marking, non-degradation,
evidence citation) is universal to document-backed multi-agent collaboration.

What is generic here (belongs in the base skill):

- markdown section splitting (see markdown_sections.py)
- viewpoint source-marker validation (is the viewpoint's isolation stated?)
- preview-label requirement (a same-session preview must be flagged low-weight)
- non-degradation check (a claimed conclusion needs a cross-session anchor)
- viewpoint-block splitting + evidence/placeholder classification

What stays in the consumer (e.g. zj-discuss):

- the conclusion *status enum* and which statuses "claim" resolution
- the *deposition* (closed-loop) check
- the per-role N-gate calibrated in role-methods
- the viewpoint heading term / role-matrix format specifics

Usage (consumer side):

    from gate_core import (
        split_sections, check_viewpoint_marker, check_non_degradation,
        split_viewpoint_blocks, count_evidence, placeholder_markers_in,
    )
"""

import re

from markdown_sections import split_sections

# --- defaults (zj-discuss vocabulary); consumers override per call ---
CROSS_SESSION_MARKER = "跨会话独立Agent"
PREVIEW_MARKER = "同会话SubAgent(低权重)"
ALLOWED_MARKERS = {CROSS_SESSION_MARKER, PREVIEW_MARKER}
PREVIEW_LABEL = "⚠ 非独立"
CLAIMED_STATUS = {"DONE", "DONE_WITH_CONCERNS"}

VIEWPOINT_RE = re.compile(r"^#{2,3}\s*视角\s*[：:]")
LABEL_SEPARATOR = r"[*`\s]*"
SOURCE_RE = re.compile(r"视角来源" + LABEL_SEPARATOR + r"[：:]" + LABEL_SEPARATOR + r"(.+)")
ROLE_RE = re.compile(r"视角\s*[：:]\s*([^（(]+)")
PREVIEW_TOKENS = ("预演", "同会话SubAgent")
RELIANCE_CUES = ("依据", "采纳", "参考", "基于", "来自", "取自", "据")
STRIP_CHARS = " \t`\"'*_\u00a0"
VIEWPOINT_BLOCK_RE = re.compile(r"^(#{4}\s*观点|\*\*观点)")
EVIDENCE_RE = re.compile(r"原文\s*(?:[\w./\-]+\s+){0,2}[Ll#§（(第]")
CITATION_RE = re.compile(r"原文")
PLACEHOLDER_TOKEN_RE = re.compile(r"<([^<>\n]{0,80})>")
DEFAULT_PLACEHOLDER_MARKERS = (
    "主题", "未填", "留空", "从原文读到", "该发现对方案", "具体、可执行",
    "主会话撰写", "若有", "...",
)
STATUS_RE = re.compile(
    r"状态协议" + LABEL_SEPARATOR + r"[：:]" + LABEL_SEPARATOR + r"([A-Za-z_]+)"
)


def _role_of(heading):
    match = ROLE_RE.search(heading)
    return match.group(1).strip() if match else heading


def check_viewpoint_marker(body, role="", allowed_markers=ALLOWED_MARKERS,
                           preview_marker=PREVIEW_MARKER, preview_label=PREVIEW_LABEL):
    """Validate a viewpoint's source marker + (if preview) preview label.

    Returns a list of violation strings (empty = clean). Message format matches
    the consumer's historical wording so delegated checks preserve test output.
    """
    marker_match = SOURCE_RE.search(body)
    if not marker_match:
        return ["视角 {} 未标注 `视角来源`".format(role)]
    marker = marker_match.group(1).strip(STRIP_CHARS)
    if marker not in allowed_markers:
        return [
            "视角 {} 的 `视角来源` 取值非法：{}（须为 {}）".format(
                role, marker, " / ".join(sorted(allowed_markers))
            )
        ]
    if marker == preview_marker:
        if preview_label not in body:
            return ["视角 {} 是同会话预演视角，缺少 `{}` 标签".format(role, preview_label)]
    return []


def check_non_degradation(conclusion_body, has_cross_session_anchor,
                          cross_session_marker=CROSS_SESSION_MARKER,
                          claimed_statuses=CLAIMED_STATUS, status_re=STATUS_RE):
    """Hard rule 6 operational form: a claimed conclusion needs a real anchor.

    The independence ladder is cross-provider > cross-session > same-session.
    Same-session is a floor to pass through, never a place to settle, so a
    conclusion claiming resolution must rest on >=1 cross-session viewpoint.
    """
    if has_cross_session_anchor:
        return []
    status_match = status_re.search(conclusion_body)
    status = status_match.group(1).strip() if status_match else None
    if status not in claimed_statuses:
        return []
    return [
        "非降级红线：「{}」声称已收敛，但本子文档没有任何 `{}` 视角作为锚点"
        "（仅有同会话预演，或根本没有视角）。同会话是下限而非终点——"
        "须重开真隔离会话取得至少一个独立视角后方可标为已结论。".format(
            status, cross_session_marker
        )
    ]


def split_viewpoint_blocks(body):
    """Split a viewpoint body into viewpoint blocks by their delimiter.

    A block starts at a line matching ``#### 观点`` (h4) or ``**观点`` (bold),
    and runs until the next delimiter or the end of the body. The preamble before
    the first delimiter is dropped (it is not a viewpoint block). A body with no
    delimiter keeps its single (likely non-compliant) block.
    """
    blocks = []
    current = []
    for line in body.splitlines():
        if VIEWPOINT_BLOCK_RE.match(line.strip()):
            blocks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    blocks.append("\n".join(current))
    if len(blocks) > 1:
        blocks = blocks[1:]  # drop the preamble; keep the single-block fallback
    return blocks


def placeholder_markers_in(block, placeholder_markers=DEFAULT_PLACEHOLDER_MARKERS):
    """Return the placeholder markers (`<...>` vocabulary) present in a block."""
    found = []
    for match in PLACEHOLDER_TOKEN_RE.finditer(block):
        inner = match.group(1).strip()
        if any(marker in inner for marker in placeholder_markers):
            found.append(match.group(0))
    return found


def count_evidence(blocks, placeholder_markers=DEFAULT_PLACEHOLDER_MARKERS,
                   evidence_re=EVIDENCE_RE, citation_re=CITATION_RE,
                   placeholder_re=PLACEHOLDER_TOKEN_RE):
    """Classify viewpoint blocks by evidence quality.

    Returns ``(evidence_count, placeholder_at, missing_anchor_at,
    missing_citation_at)`` with the three position lists 1-indexed.

    - a template placeholder block is not evidence;
    - a block with a citation but no locator is a format failure;
    - a block with no citation at all is a missing-evidence failure.
    """
    placeholder_at = []
    missing_anchor_at = []
    missing_citation_at = []
    evidence = 0
    for position, block in enumerate(blocks, start=1):
        if placeholder_markers_in(block, placeholder_markers):
            placeholder_at.append(position)
        elif evidence_re.search(block):
            evidence += 1
        elif citation_re.search(block):
            missing_anchor_at.append(position)
        else:
            missing_citation_at.append(position)
    return evidence, placeholder_at, missing_anchor_at, missing_citation_at


__all__ = [
    "split_sections", "check_viewpoint_marker", "check_non_degradation",
    "split_viewpoint_blocks", "placeholder_markers_in", "count_evidence",
    "VIEWPOINT_RE", "ROLE_RE", "PLACEHOLDER_TOKEN_RE", "DEFAULT_PLACEHOLDER_MARKERS",
    "EVIDENCE_RE", "CITATION_RE",
]

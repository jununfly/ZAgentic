#!/usr/bin/env python3
"""Structural gate for zj-discuss sub-documents.

Turns previously prose-only invariants into mechanically enforced checks:

1. every viewpoint declares a valid ``视角来源`` marker;
2. a same-session preview viewpoint carries the ``⚠ 非独立`` label;
3. the conclusion carries a valid ``状态协议`` value and never cites
   same-session preview output as authority (hard rule 3(b) of the skill);
4. a cross-session independent viewpoint carries **≥N viewpoint blocks, each
   citing original evidence** (the gated-method ④ gate, calibrated in
   ``design.md §10.6 R1``). N is read from each role's
   ``references/role-methods/<key>.md`` so the ratified value stays the single
   source of truth — this file needs no per-role edit when calibration changes.

Usage:

    python3 check_subdoc.py <sub-doc-path> [<sub-doc-path> ...]

Exit codes: 0 clean, 1 one or more violations, 2 unreadable/missing input.
"""

import argparse
import re
import sys
from pathlib import Path

VALID_STATUS = {"DONE", "DONE_WITH_CONCERNS", "BLOCKED", "NEEDS_CONTEXT"}
CROSS_SESSION_MARKER = "跨会话独立Agent"
PREVIEW_MARKER = "同会话SubAgent(低权重)"
ALLOWED_MARKERS = {CROSS_SESSION_MARKER, PREVIEW_MARKER}
# Statuses that *claim* the sub-problem is resolved. They are the only ones the
# non-degradation rule polices: BLOCKED / NEEDS_CONTEXT make no such claim and
# are therefore exempt (a doc honestly reporting "not done" is not degrading).
CLAIMED_STATUS = {"DONE", "DONE_WITH_CONCERNS"}
PREVIEW_LABEL = "⚠ 非独立"

STATUS_ENUM_TEXT = " / ".join(sorted(VALID_STATUS))

VIEWPOINT_RE = re.compile(r"^#{2,3}\s*视角\s*[：:]")
# Labels are written as Markdown bold spanning the colon (`**状态协议：** DONE`),
# so the closing emphasis markers land *after* the colon. Tolerate emphasis and
# backticks on both sides of it.
LABEL_SEPARATOR = r"[*`\s]*"
SOURCE_RE = re.compile(r"视角来源" + LABEL_SEPARATOR + r"[：:]" + LABEL_SEPARATOR + r"(.+)")
STATUS_RE = re.compile(
    r"状态协议" + LABEL_SEPARATOR + r"[：:]" + LABEL_SEPARATOR + r"([A-Za-z_]+)"
)
ROLE_RE = re.compile(r"视角\s*[：:]\s*([^（(]+)")
# Tokens that mark a viewpoint as same-session preview output.
PREVIEW_TOKENS = ("预演", "同会话SubAgent")
# A bare mention is NOT a citation: a conclusion may legitimately *discuss* the
# preview rule ("conclusion 无预演字段"). Only language that leans on the preview
# output counts as citing it, so require a reliance cue on the same line.
RELIANCE_CUES = ("依据", "采纳", "参考", "基于", "来自", "取自", "据")
STRIP_CHARS = " \t`\"'*_\u00a0"

# A viewpoint body is composed of one or more "viewpoint blocks". Each block is
# introduced by a ``#### 观点`` heading or a bold ``**观点`` line, and must carry
# an evidence citation back to the source the Agent Read (gated method ④). The
# delimiter is fence-aware via split_sections (a ``**观点`` line inside a code
# fence is inert).
VIEWPOINT_BLOCK_RE = re.compile(r"^(#{4}\s*观点|\*\*观点)")
# Evidence = a "原文" reference carrying a locator (line / section / paren), e.g.
# "原文 L96", "原文 L118-131", "（原文 L9-13）". This is the canonical form the
# gated method mandates ("发现 字段须能回溯到 Read 到的原文").
EVIDENCE_RE = re.compile(r"原文\s*[L（(]")
ROLE_METHODS_DIR = Path(__file__).resolve().parent.parent / "references" / "role-methods"
# Fallback when a role has no gated-method file (custom / unknown role key).
GATE_N_DEFAULT = 3
GATE_N_RE = re.compile(r"N\s*=\s*(\d+)")


def split_sections(text):
    """Split Markdown into (heading, body) pairs by ATX headings.

    Fence-aware: lines inside a ``` / ~~~ code fence are never treated as
    headings, even if they start with ``#``. This keeps a digest block (or any
    code block) inert to viewpoint/conclusion detection — a digest that echoes a
    ``### 视角：X`` line inside a fence must not be parsed as a real viewpoint
    (see design.md §8 digest-injection PoC).
    """
    sections = []
    heading = None
    body = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            body.append(line)  # a fence delimiter is content of the section
            continue
        if not in_fence and line.startswith("#"):
            if heading is not None:
                sections.append((heading, "\n".join(body)))
            heading = line.strip()
            body = []
        else:
            body.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body)))
    return sections


def _role_of(heading):
    match = ROLE_RE.search(heading)
    return match.group(1).strip() if match else heading


def _check_conclusion(body):
    violations = []
    status = STATUS_RE.search(body)
    if not status:
        violations.append(
            "conclusion 缺少 `状态协议` 字段（须为 {} 之一）".format(STATUS_ENUM_TEXT)
        )
    elif status.group(1).strip() not in VALID_STATUS:
        violations.append(
            "conclusion 的 `状态协议` 取值非法：{}（须为 {} 之一）".format(
                status.group(1).strip(), STATUS_ENUM_TEXT
            )
        )
    for line in body.splitlines():
        if not any(token in line for token in PREVIEW_TOKENS):
            continue
        cues = [cue for cue in RELIANCE_CUES if cue in line]
        if cues:
            violations.append(
                "conclusion 不得引用同会话预演作为权威依据（依据词「{}」紧邻「{}」）".format(
                    cues[0], next(t for t in PREVIEW_TOKENS if t in line)
                )
            )
            break
    return violations


def _check_viewpoint(heading, body):
    """Validate one viewpoint block: source marker, preview label, and the
    gated-method N-gate (cross-session independent viewpoints only)."""
    role = _role_of(heading)
    marker_match = SOURCE_RE.search(body)
    if not marker_match:
        return ["视角 {} 未标注 `视角来源`".format(role)]
    marker = marker_match.group(1).strip(STRIP_CHARS)
    if marker not in ALLOWED_MARKERS:
        return [
            "视角 {} 的 `视角来源` 取值非法：{}（须为 {}）".format(
                role, marker, " / ".join(sorted(ALLOWED_MARKERS))
            )
        ]
    # A same-session preview is explicitly low-weight and is *not* counted as
    # effective coverage, so the N-gate does not apply to it.
    if marker == PREVIEW_MARKER:
        if PREVIEW_LABEL not in body:
            return [
                "视角 {} 是同会话预演视角，缺少 `{}` 标签".format(role, PREVIEW_LABEL)
            ]
        return []
    # Cross-session independent viewpoint → enforce the gated-method N-gate.
    return _check_viewpoint_gate(role, body)


def _split_viewpoint_blocks(body):
    """Split a viewpoint body into viewpoint blocks by their delimiter.

    A block starts at a line matching ``#### 观点`` (h4) or ``**观点`` (bold),
    and runs until the next delimiter or the end of the body. A body with no
    delimiter is treated as a single (likely non-compliant) block.
    """
    blocks = []
    current = []
    for line in body.splitlines():
        if VIEWPOINT_BLOCK_RE.match(line.strip()):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def gate_n_for_role(role_key):
    """Return the gated-method viewpoint count N for a role key.

    N is read from the role's gated-method file (``references/role-methods/
    <key>.md``), so the ratified calibration in ``design.md §10.6 R1`` stays the
    single source of truth — node 1-5 only edits those files, this gate needs
    no code change. Falls back to ``GATE_N_DEFAULT`` when the role file (or an
    ``N =`` line) is absent.
    """
    key = role_key.strip()
    for sep in ("（", "(", "（"):
        if sep in key:
            key = key.split(sep)[0].strip()
    if not key:
        return GATE_N_DEFAULT
    cand = ROLE_METHODS_DIR / "{}.md".format(key)
    if cand.is_file():
        m = GATE_N_RE.search(cand.read_text(encoding="utf-8"))
        if m:
            return int(m.group(1))
    return GATE_N_DEFAULT


def _check_viewpoint_gate(role, body):
    """Enforce gated-method ④: ≥N viewpoint blocks, each citing original evidence.

    Only criteria 1 (count) and 2 (evidence citation) of the gated method are
    mechanically checkable here; criterion 3 (anti-echo / independence) is left
    to the blind-adjudication protocol (roadmap node 1-3 B).
    """
    n = gate_n_for_role(role)
    blocks = _split_viewpoint_blocks(body)
    evidence_blocks = [b for b in blocks if EVIDENCE_RE.search(b)]
    if len(evidence_blocks) < n:
        return [
            "视角 {} 的有效观点（带原文证据引用）仅 {} 条，低于闸门 N={}"
            "（须 ≥N 条带证据引用的观点块：每块以「**观点 N**」或「#### 观点 N」"
            " 起头，并含「原文 Lxx」类证据定位）".format(
                role, len(evidence_blocks), n
            )
        ]
    return []


def _check_non_degradation(conclusion_body, has_cross_session_anchor):
    """Hard rule 3's operational form: a claimed conclusion needs a real anchor.

    The independence ladder is cross-provider > cross-session > same-session.
    Same-session is a floor to pass through, never a place to settle, so a
    conclusion claiming DONE / DONE_WITH_CONCERNS must rest on at least one
    cross-session viewpoint.
    """
    if has_cross_session_anchor:
        return []
    status_match = STATUS_RE.search(conclusion_body)
    status = status_match.group(1).strip() if status_match else None
    if status not in CLAIMED_STATUS:
        return []
    return [
        "非降级红线：「{}」声称已收敛，但本子文档没有任何 `{}` 视角作为锚点"
        "（仅有同会话预演，或根本没有视角）。同会话是下限而非终点——"
        "须重开真隔离会话取得至少一个独立视角后方可标为已结论。".format(
            status, CROSS_SESSION_MARKER
        )
    ]


def check(text):
    """Return the list of violations in one sub-document body."""
    violations = []
    conclusion_body = None
    has_cross_session_anchor = False
    for heading, body in split_sections(text):
        if VIEWPOINT_RE.match(heading):
            violations.extend(_check_viewpoint(heading, body))
            marker_match = SOURCE_RE.search(body)
            if marker_match and marker_match.group(1).strip(STRIP_CHARS) == CROSS_SESSION_MARKER:
                has_cross_session_anchor = True
        elif heading.lower().startswith("## conclusion"):
            conclusion_body = body
    if conclusion_body is None:
        violations.append("缺少 `## conclusion` 段")
    else:
        violations.extend(_check_conclusion(conclusion_body))
        violations.extend(_check_non_degradation(conclusion_body, has_cross_session_anchor))
    return violations


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Enforce zj-discuss sub-document structural invariants."
    )
    parser.add_argument("paths", nargs="+", help="sub-document paths")
    args = parser.parse_args(argv)

    failed = False
    for raw in args.paths:
        path = Path(raw)
        if not path.exists():
            print("missing: {}".format(path), file=sys.stderr)
            failed = True
            continue
        violations = check(path.read_text(encoding="utf-8"))
        if violations:
            failed = True
            print("{}: {} violation(s)".format(path, len(violations)), file=sys.stderr)
            for item in violations:
                print("  - {}".format(item), file=sys.stderr)
        else:
            print("{}: OK".format(path))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

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

# Reuse the generic structural-gate substrate from the zj-doc-collab base skill
# (split_sections, viewpoint-marker / non-degradation checks, block splitting,
# evidence classification). This skill keeps only its domain-specific layer:
# the conclusion status enum, the deposition check, the per-role N-gate, and the
# viewpoint heading vocabulary. The base's defaults already equal this skill's
# vocabulary (跨会话独立Agent / ⚠ 非独立 / 非降级红线 / 原文 evidence), so the
# delegation is behavior-preserving with no per-call overrides needed.
from pathlib import Path as _Path
_BASE_SCRIPTS = _Path(__file__).resolve().parents[2] / "zj-doc-collab" / "scripts"
if str(_BASE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BASE_SCRIPTS))
from gate_core import (
    split_sections,
    _role_of,
    check_non_degradation as _check_non_degradation,
    split_viewpoint_blocks as _split_viewpoint_blocks,
    placeholder_markers_in,
)

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
# NOTE: ROLE_RE now lives in zj-doc-collab/scripts/gate_core (used by _role_of
# there). Kept out of this skill to avoid a second source of truth.
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
# NOTE: VIEWPOINT_BLOCK_RE now lives in zj-doc-collab/scripts/gate_core.
# Evidence = a "原文" reference carrying a locator (file+line / line / section /
# paren), e.g. "原文 L96", "原文 sub-02 L85-88", "原文 SKILL.md L140-144",
# "原文 ## 上下文", "原文 §结论不变式", "（原文 L9-13）", "原文 第9-13行".
# The gated method mandates "发现 字段须能回溯到 Read 到的原文" — a locator,
# not a specific spelling. The previous regex `原文\s*[L（(]` ONLY matched a bare
# `原文 Lxx` and silently rejected the dominant real form `原文 <path> Lxx`,
# which (proven by the improve-zj-discuss meta-run) makes every viewpoint that
# cites by file+line fail the gate → mass false rejections → gate disabled
# (the exact "狼来了" failure mode SKILL.md warns about). The `[\w./\-]+\s+`
# group optionally consumes a path/identifier token between 原文 and the L/§/#
# anchor; the trailing `第` covers the "原文 第9-13行" spelling.
# Up to 2 path/identifier tokens, so a spaced identifier still works: ADR names
# are written `ADR 0008`, and the one-token form rejected `原文 ADR 0008 L28` —
# i.e. the gate would have rejected the very fix it recommends (#165).
EVIDENCE_RE = re.compile(r"原文\s*(?:[\w./\-]+\s+){0,2}[Ll#§（(第]")
# The bare cue: a citation exists but carries no locator. Distinguishing the two
# is what turns "write more viewpoints" into "add a locator" (#165).
CITATION_RE = re.compile(r"原文")
# A viewpoint block can be a *template placeholder*: the generator emits one
# block per declared role, each carrying a fake locator (`原文 L20`) inside
# `<...>`. Old behavior counted those as evidence, so a zero-content stub with
# ≥N placeholder blocks passed the gate — the template bypassed its own gate
# (#166). Placeholders are matched by the marker vocabulary the template uses,
# not by a bare `<...>` regex, so a legitimate `<tag>` in prose is not hit.
# NOTE: PLACEHOLDER_TOKEN_RE / PLACEHOLDER_MARKERS now live in
# zj-doc-collab/scripts/gate_core (defaults already equal this skill's vocab).
ROLE_METHODS_DIR = Path(__file__).resolve().parent.parent / "references" / "role-methods"
# Fallback when a role has no gated-method file (custom / unknown role key).
GATE_N_DEFAULT = 3
GATE_N_RE = re.compile(r"N\s*=\s*(\d+)")


# `split_sections` and `_role_of` are delegated to zj-doc-collab/scripts/gate_core
# (split_sections re-exported via markdown_sections). Local copies removed in the
# base-skill extraction; output is byte-identical.


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
        # 规则陈述句（如「结论不得引用同会话 SubAgent 预演产出作为权威依据」）只是指
        # 出约束，并非把预演当权威依据 —— 跳过，否则闸门会对每篇结论误报，触发
        # SKILL.md 预警的「狼来了」失效模式（闸门被关掉）。
        if "不得引用" in line:
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


def _check_deposition(body):
    """Hard rule 5 closure guard (sub-02 Q3 finding).

    A conclusion that carries a `沉淀指令` block must list at least one
    substantive deposition item; an empty `沉淀指令` (status DONE but nothing to
    deposit / nothing to delete) is a non-loop that slips past the older gate.
    Docs that omit the block entirely are not gated here (legacy / not-yet-using
    the template), so this only fires on the real "claimed loop but empty" case.
    """
    idx = body.find("沉淀指令")
    if idx == -1:
        return []
    tail = body[idx:]
    lines = tail.splitlines()
    # Bound the scan at the status-protocol field; never scan the marker line
    # itself (lines[0]) or the 状态协议 line, or an empty block would falsely pass.
    stop = len(lines)
    for i, line in enumerate(lines):
        if "状态协议" in line:
            stop = i
            break
    for line in lines[1:stop]:
        s = line.strip()
        if not s:
            continue
        if s[0] in "-*" or s.startswith("**"):
            return []
    return [
        "conclusion 含 `沉淀指令` 段但无实质条目（须列至少 1 条改的文档 / 待删临时物），"
        "否则不算闭环（硬规则 5）"
    ]


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


# `_split_viewpoint_blocks` is delegated to zj-doc-collab/scripts/gate_core
# (VIEWPOINT_BLOCK_RE + preamble-drop logic live there now).


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


# `placeholder_markers_in` is delegated to zj-doc-collab/scripts/gate_core
# (PLACEHOLDER_TOKEN_RE + PLACEHOLDER_MARKERS live there as defaults).


def _check_viewpoint_gate(role, body):
    """Enforce gated-method ④: ≥N viewpoint blocks, each citing original evidence.

    Only criteria 1 (count) and 2 (evidence citation) of the gated method are
    mechanically checkable here; criterion 3 (anti-echo / independence) is left
    to the blind-adjudication protocol (roadmap node 1-3 B).

    Two failure shapes this gate must NOT conflate:

    - a **template placeholder block is not evidence** (#166). The template emits
      N blocks per role, each with a fake `原文 Lxx` inside `<...>`; counting them
      lets a zero-content stub claim full coverage.
    - a **missing locator is a format failure, not a count shortage** (#165).
      `原文 ADR 0008` and "I wrote too few viewpoints" have opposite fixes, so
      the report names the reason per block instead of only printing a count.
    """
    n = gate_n_for_role(role)
    blocks = _split_viewpoint_blocks(body)

    placeholder_at = []
    missing_anchor_at = []
    missing_citation_at = []
    evidence = 0
    for position, block in enumerate(blocks, start=1):
        if placeholder_markers_in(block):
            placeholder_at.append(position)
        elif EVIDENCE_RE.search(block):
            evidence += 1
        elif CITATION_RE.search(block):
            missing_anchor_at.append(position)
        else:
            missing_citation_at.append(position)

    if evidence >= n:
        return []

    return [
        "视角 {} 的观点闸门未过：有效观点（带原文证据引用）{} 条，低于闸门 N={}{}。{}".format(
            role,
            evidence,
            n,
            "（另有 {} 个未填占位块不计入）".format(len(placeholder_at)) if placeholder_at else "",
            "；".join(_gate_details(placeholder_at, missing_anchor_at, missing_citation_at)),
        )
    ]


def _gate_details(placeholder_at, missing_anchor_at, missing_citation_at):
    """Per-block reasons, so the fix follows from the report (#165 / #166)."""
    details = []
    if placeholder_at:
        details.append(
            "第 {} 块是未填的模板占位块（`<...>` / `<主题>` 类标记），计 0 条 —— "
            "模板骨架本身不是证据".format(_join_positions(placeholder_at))
        )
    if missing_anchor_at:
        details.append(
            "第 {} 块的「原文」引用缺定位锚点（行号 / 章节）：写法如 `原文 ADR 0008` "
            "须补成 `原文 ADR 0008 L28` 或 `原文 ADR 0008 ## 小节`".format(
                _join_positions(missing_anchor_at)
            )
        )
    if missing_citation_at:
        details.append(
            "第 {} 块没有「原文」引用，「发现」须能回溯到 Read 到的原文".format(
                _join_positions(missing_citation_at)
            )
        )
    if not details:
        details.append(
            "每块须以「**观点 N**」或「#### 观点 N」起头，并含「原文 <file> Lxx / "
            "原文 ## 章节 / 原文 §…」类证据定位（行号或章节锚点均可）"
        )
    return details


def _join_positions(positions):
    return "、".join(str(p) for p in positions)


# `_check_non_degradation` is delegated to zj-doc-collab/scripts/gate_core
# (the 非降级红线 message + CLAIMED_STATUS / CROSS_SESSION_MARKER defaults).


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
        violations.extend(_check_deposition(conclusion_body))
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

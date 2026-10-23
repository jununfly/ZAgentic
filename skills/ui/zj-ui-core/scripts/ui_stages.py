"""Stage runners S1..S4 for the `zj-ui-*` chain.

Each runner takes the **structured request** an agent already extracted from the
conversation (roadmap 1-6-2 decision: the code never parses prose) and returns a
fixed-shape result. The runners are deliberately thin: all semantics that can be
shared — schema, quartet, deny-first, commit, contrast — live in
`ui_skill_core.py`, because two implementations of "unknown" is how the quartet
silently becomes a nullable string.

Effect boundary: nothing here runs code, touches the network or writes remotely.
`store` is an in-memory journal the caller may persist; a stage that reports
`writes: 0` never even reaches `commit()`.
"""

from __future__ import annotations

import ui_skill_core as core

BRIEF_REQUIRED = ("goal_users", "goal_task", "constraints", "success_criteria")
MAX_QUESTIONS = 2


def _content(document: dict, artifact_kind: str) -> dict:
    """Keep only registered fields, in schema order, so revisions are stable."""
    return {field: document[field] for field in core.SCHEMAS[artifact_kind] if field in document}


def _artifact(artifact_kind: str, schema_version_key: str, schema_version: str,
              input_revision: str, content: dict) -> dict:
    body = {
        "artifact_kind": artifact_kind,
        schema_version_key: schema_version,
        "input_revision": input_revision,
        "content": content,
    }
    return {**body, "revision": core.revision_of(body)}


# --------------------------------------------------------------------------- #
# S1 · zj-ui-brief
# --------------------------------------------------------------------------- #


def run_brief(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision")

    if not core.is_filled(input_revision):
        return core.result(
            "zj-ui-brief",
            core.REJECTED,
            reason="缺少 input_revision：无法把 draft 归因到来源",
            rejected=[core.reject("input_revision", "required for provenance")],
        )

    # Deny-first: an unregistered field is a typo or an unratified concept. Either
    # way it must not be quietly dropped (1-2-2 §3).
    problems = core.validate_document(core.BRIEF, candidate)
    if problems:
        return core.result(
            "zj-ui-brief",
            core.REJECTED,
            reason="deny-first：字段未注册或类型不符，未提交 revision",
            rejected=problems,
        )

    gaps = core.stage_gaps("brief", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        questions = [
            f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps[:MAX_QUESTIONS]
        ]
        return core.result(
            "zj-ui-brief",
            core.NEEDS_CONTEXT,
            reason="必填缺口，改为 unknown 四元组后停止，零写入",
            questions=questions,
            unknown=unknown,
        )

    content = _content(candidate, core.BRIEF)
    content.setdefault("unknown", [])
    artifact = _artifact(core.BRIEF, "brief_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store,
        core.BRIEF,
        artifact,
        request.get("idempotency_key") or f"{core.BRIEF}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-brief",
            core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-brief",
        core.OK,
        writes=committed["writes"],
        reason="四类必填齐备，revision 原子提交",
        artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S2 · zj-ui-discover
# --------------------------------------------------------------------------- #


def run_discover(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    brief = request.get("brief") or {}
    brief_revision = request.get("brief_revision") or ""
    budget = int(request.get("question_budget", MAX_QUESTIONS))
    asked = int(request.get("questions_asked") or 0)

    problems = core.validate_document(core.BRIEF, brief)
    if problems:
        return core.result(
            "zj-ui-discover",
            core.REJECTED,
            reason="deny-first：上游 brief 含未注册字段，拒绝继续",
            rejected=problems,
        )

    # Budget is policy, not preference: once spent, the stage stops instead of
    # asking a third question (1-3-1 §2 forbids "追问超过 2 次").
    if asked > budget:
        return core.result(
            "zj-ui-discover",
            core.NEEDS_CONTEXT,
            reason=f"追问预算耗尽（asked={asked} > budget={budget}），零写入",
            questions=[],
        )

    evidence = request.get("evidence") or []
    accepted: dict = {}
    unknown: list = []
    frozen: list = []

    for index, item in enumerate(evidence):
        path = item.get("path")
        if not core.is_filled(path):
            return core.result(
                "zj-ui-discover",
                core.REJECTED,
                reason="证据条目缺少 path，无法归因",
                rejected=[core.reject(f"evidence[{index}].path", "required")],
            )
        value = item.get("value")
        if path in BRIEF_REQUIRED and core.is_filled(brief.get(path)) and brief[path] != value:
            frozen.append(
                core.reject(path, "S2 不得改写 S1 已冻结的必填字段值", "brief/contract owner")
            )
            continue
        if not core.is_attributable(item.get("source")):
            # Insufficient evidence is not a failure: it becomes a quartet. The
            # value is deliberately NOT written anywhere in the artifact.
            unknown.append(
                core.make_unknown(
                    path=path,
                    raw=value,
                    reason="证据不足：无可归因来源，不作猜测写入",
                    source=str(item.get("source") or "missing"),
                )
            )
            continue
        accepted[path] = value

    if frozen:
        return core.result(
            "zj-ui-discover",
            core.REJECTED,
            reason="试图改写上游已冻结字段，拒绝，零写入",
            rejected=frozen,
        )

    # A quartet whose gap the evidence just closed is resolved; keeping it would
    # make the brief permanently "uncertain" and hide real regressions.
    carried = [
        entry
        for entry in (brief.get("unknown") or [])
        if isinstance(entry, dict) and entry.get("path") not in accepted
    ]
    content = {
        field: brief[field]
        for field in core.SCHEMAS[core.BRIEF]
        if field in brief and field != "unknown"
    }
    content.update(accepted)
    content["unknown"] = carried + unknown

    artifact = _artifact(
        core.BRIEF, "brief_schema_version", "1.0.0", brief_revision, content
    )
    committed = core.commit(
        store,
        core.BRIEF,
        artifact,
        request.get("idempotency_key") or f"{core.BRIEF}:{brief_revision}:discover",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-discover",
            core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-discover",
        core.OK,
        writes=committed["writes"],
        reason="缺口按证据等级落定；无来源的证据保留为 unknown",
        unknown=unknown,
        artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S3 · zj-ui-direction
# --------------------------------------------------------------------------- #

CARD_KEYS = ("id", "name", "color", "typography", "density", "motion", "tradeoffs", "reference")


def _card_problems(cards) -> list:
    problems = []
    if not isinstance(cards, list) or not cards:
        return [core.reject("cards", "至少需要一张方向卡")]
    for index, card in enumerate(cards):
        field = f"cards[{index}]"
        if not isinstance(card, dict):
            problems.append(core.reject(field, "方向卡必须是对象"))
            continue
        missing = [key for key in CARD_KEYS if key not in card]
        if missing:
            problems.append(core.reject(field, f"方向卡缺字段：{', '.join(missing)}"))
        reference = card.get("reference")
        if not isinstance(reference, dict):
            problems.append(core.reject(f"{field}.reference", "参考来源必须是对象"))
    return problems


def _licensed(card: dict) -> bool:
    reference = card.get("reference") or {}
    return core.is_attributable(reference.get("license"))


def run_direction(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    cards = request.get("cards") or []
    choice = request.get("human_choice")
    brief_revision = request.get("brief_revision") or ""

    problems = _card_problems(cards)
    if problems:
        return core.result(
            "zj-ui-direction", core.REJECTED, reason="方向卡不完整，未生成候选", rejected=problems
        )

    quarantined = [card["id"] for card in cards if not _licensed(card)]
    usable = [card for card in cards if card["id"] not in quarantined]

    if core.is_filled(choice):
        if choice in quarantined:
            return core.result(
                "zj-ui-direction",
                core.QUARANTINED,
                reason="选定方向依赖 license unknown 的参考，不进默认产物",
                quarantined=quarantined,
                candidates=[card["id"] for card in usable],
            )
        chosen = next((card for card in usable if card["id"] == choice), None)
        if chosen is None:
            return core.result(
                "zj-ui-direction",
                core.REJECTED,
                reason="human_choice 不在可用候选内",
                rejected=[core.reject("human_choice", "unknown direction id")],
                quarantined=quarantined,
                candidates=[card["id"] for card in usable],
            )

        content = {
            "direction_choice": chosen["id"],
            "provenance": {
                "source": chosen["reference"].get("source"),
                "reference": chosen["reference"].get("reference", chosen["id"]),
                "license": chosen["reference"].get("license"),
            },
            "tradeoffs": list(chosen.get("tradeoffs") or []),
            "unknown": [],
        }
        artifact = _artifact(
            core.DESIGN, "design_schema_version", "1.0.0", brief_revision, content
        )
        committed = core.commit(
            store,
            core.DESIGN,
            artifact,
            request.get("idempotency_key") or f"{core.DESIGN}:{brief_revision}:{choice}",
        )
        if committed["conflict"]:
            return core.result(
                "zj-ui-direction",
                core.REJECTED,
                reason="幂等键重放但内容不同，拒绝覆盖",
                rejected=[core.reject("idempotency_key", committed["reason"])],
                quarantined=quarantined,
            )
        return core.result(
            "zj-ui-direction",
            core.OK,
            writes=committed["writes"],
            reason="Human 已选定唯一方向，写入 direction_choice",
            quarantined=quarantined,
            # The compared set stays in the result even after the choice: a review
            # record without the alternatives cannot answer "what was rejected".
            candidates=[card["id"] for card in usable],
            artifact=artifact,
        )

    # human_gate=required: without a signature the stage may not pick, not even by
    # "first card wins" — that is how a taste decision becomes an accident.
    status = core.QUARANTINED if quarantined else core.HUMAN_REVIEW_REQUIRED
    return core.result(
        "zj-ui-direction",
        status,
        reason=(
            "存在 license unknown 的参考，已 quarantine，不进默认产物"
            if quarantined
            else "方向不唯一且 Human 未签，展示候选，零写入"
        ),
        quarantined=quarantined,
        candidates=[card["id"] for card in usable],
    )


# --------------------------------------------------------------------------- #
# S4 · zj-ui-design-system
# --------------------------------------------------------------------------- #


def run_design_system(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    design = dict(request.get("design") or {})
    tokens = request.get("tokens") or design.get("tokens") or {}
    components = request.get("components") or []
    design_revision = request.get("design_revision") or ""

    if not core.is_filled(design.get("direction_choice")):
        return core.result(
            "zj-ui-design-system",
            core.HUMAN_REVIEW_REQUIRED,
            reason="S3 的 direction_choice 尚未由人签署，S4 不得开工",
        )

    problems = core.validate_document(core.DESIGN, design)
    if problems:
        return core.result(
            "zj-ui-design-system",
            core.REJECTED,
            reason="deny-first：设计文档含未注册字段，零写入",
            rejected=problems,
        )

    # Registry is repo-owned: an adapter projects it, it does not extend it.
    unregistered = [
        component.get("name")
        for component in components
        if not isinstance(component, dict)
        or component.get("name") not in core.COMPONENT_REGISTRY
    ]
    if unregistered:
        return core.result(
            "zj-ui-design-system",
            core.BLOCKED,
            reason="组件未在 catalog 注册，阻断，零写入",
            rejected=[
                core.reject(
                    f"components[{name}]",
                    "unregistered component",
                    "direction/design owner",
                )
                for name in unregistered
            ],
        )

    typography = dict(tokens.get("typography") or {})
    if not core.is_attributable(typography.get("license")):
        return core.result(
            "zj-ui-design-system",
            core.QUARANTINED,
            reason="字体 license 不明，quarantine，不进默认产物",
            quarantined=[str(typography.get("family") or "typography")],
        )

    color = dict(tokens.get("color") or {})
    failures = []
    for role, foreground, background in core.contrast_pairs(color):
        ratio = core.contrast_ratio(foreground, background)
        if ratio < core.CONTRAST_MIN:
            failures.append(
                core.reject(
                    f"color.{role}",
                    f"contrast {ratio} < {core.CONTRAST_MIN}（{foreground} on {background}）",
                    "direction/design owner",
                    recoverable=True,
                )
            )
    if failures:
        # No "swap to a nearby colour and call it compliant": that would turn the
        # acceptance criterion into a self-certification.
        return core.result(
            "zj-ui-design-system",
            core.BLOCKED,
            reason="contrast 不达标，阻断，未替换颜色",
            rejected=failures,
        )

    content = {
        "direction_choice": design["direction_choice"],
        "tokens": tokens,
        "typography": typography,
        "color": color,
        "component_principles": list(design.get("component_principles") or []),
        "tradeoffs": list(design.get("tradeoffs") or []),
        "components": [component["name"] for component in components],
        "unknown": list(design.get("unknown") or []),
    }
    if core.is_filled(design.get("provenance")):
        content["provenance"] = design["provenance"]

    artifact = _artifact(
        core.DESIGN, "design_schema_version", "1.0.0", design_revision, content
    )
    committed = core.commit(
        store,
        core.DESIGN,
        artifact,
        request.get("idempotency_key") or f"{core.DESIGN}:{design_revision}:tokens",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-design-system",
            core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-design-system",
        core.OK,
        writes=committed["writes"],
        reason="tokens + catalog 落盘，contrast 达标",
        artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S5 · zj-ui-flow
# --------------------------------------------------------------------------- #

def _flow_id_problems(states, actions, intents) -> list:
    """Hard-fail gates for ui-flow/v1 (contract 1-2-3 §7): duplicate ids and
    dangling references mean a meaning was silently lost or two owners collided.
    """
    problems = []
    state_ids = set()
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            problems.append(core.reject(f"states[{index}]", "state 必须是对象"))
            continue
        sid = state.get("id")
        if not sid:
            problems.append(core.reject(f"states[{index}].id", "state 缺 id"))
            continue
        if sid in state_ids:
            problems.append(core.reject(f"states[{index}].id", f"重复 state id（双 owner / 歧义）: {sid}"))
        state_ids.add(sid)
    intent_ids = {item.get("id") for item in intents if isinstance(item, dict)}
    seen_action_ids = set()
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            problems.append(core.reject(f"actions[{index}]", "action 必须是对象"))
            continue
        aid = action.get("id")
        if aid:
            if aid in seen_action_ids:
                problems.append(core.reject(f"actions[{index}].id", f"重复 action id: {aid}"))
            seen_action_ids.add(aid)
        fs, ts, it = action.get("from_state"), action.get("to_state"), action.get("intent")
        if fs is not None and fs not in state_ids:
            problems.append(core.reject(f"actions[{index}].from_state", f"悬空引用 state（状态丢失）: {fs}"))
        if ts is not None and ts not in state_ids:
            problems.append(core.reject(f"actions[{index}].to_state", f"悬空引用 state（状态丢失）: {ts}"))
        if it is not None and it not in intent_ids:
            problems.append(core.reject(f"actions[{index}].intent", f"悬空引用 intent（intent 丢失）: {it}"))
    return problems


def run_flow(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""

    problems = core.validate_document(core.UI_FLOW, candidate)
    if problems:
        return core.result(
            "zj-ui-flow", core.REJECTED,
            reason="deny-first：未注册字段或类型不符，未提交 revision",
            rejected=problems,
        )
    gaps = core.stage_gaps("flow", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        questions = [f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps[:MAX_QUESTIONS]]
        return core.result(
            "zj-ui-flow", core.NEEDS_CONTEXT,
            reason="六义缺口，转 unknown 四元组后停止，零写入",
            questions=questions, unknown=unknown,
        )
    ref_problems = _flow_id_problems(
        candidate.get("states", []), candidate.get("actions", []), candidate.get("intents", [])
    )
    if ref_problems:
        return core.result(
            "zj-ui-flow", core.REJECTED,
            reason="hard fail：状态/动作/意图丢失或双 owner（重复 id / 悬空引用）",
            rejected=ref_problems,
        )
    content = _content(candidate, core.UI_FLOW)
    content.setdefault("unknown", [])
    artifact = _artifact(core.UI_FLOW, "flow_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.UI_FLOW, artifact,
        request.get("idempotency_key") or f"{core.UI_FLOW}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-flow", core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-flow", core.OK, writes=committed["writes"],
        reason="六义齐全、引用闭合，ui-flow/v1 原子提交", artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S6 · zj-ui-prototype
# --------------------------------------------------------------------------- #

def _human_approved(approval) -> bool:
    return (
        isinstance(approval, dict)
        and core.is_attributable(approval.get("name"))
        and core.is_attributable(approval.get("signed_at"))
    )


def run_prototype(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""

    problems = core.validate_document(core.UI_PREVIEW, candidate)
    if problems:
        return core.result(
            "zj-ui-prototype", core.REJECTED,
            reason="deny-first：未注册字段或类型不符，未生成实现",
            rejected=problems,
        )
    gaps = core.stage_gaps("prototype", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        questions = [f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps[:MAX_QUESTIONS]]
        return core.result(
            "zj-ui-prototype", core.NEEDS_CONTEXT,
            reason="必填缺口，转 unknown 后停止，零写入",
            questions=questions, unknown=unknown,
        )
    components = candidate.get("components") or []
    unregistered = [name for name in components if name not in core.COMPONENT_REGISTRY]
    if unregistered:
        return core.result(
            "zj-ui-prototype", core.REJECTED,
            reason="未注册组件，deny，不生成实现（catalog 不得扩表）",
            rejected=[core.reject("components", f"unregistered component: {unregistered[0]}")],
        )
    # human_gate=required：未签不得产生副作用；远程不可用也不得伪造成功。
    if not _human_approved(candidate.get("human_approval")):
        return core.result(
            "zj-ui-prototype", core.HUMAN_REVIEW_REQUIRED,
            reason="human_gate=required：未签署审批，零写入", questions=[],
        )
    if request.get("remote_available") is False and not request.get("allow_local_fallback", False):
        return core.result(
            "zj-ui-prototype", core.HUMAN_REVIEW_REQUIRED,
            reason="远程 adapter 不可用且未声明本地 fallback，不得伪造成功，零写入",
            questions=[],
        )
    content = _content(candidate, core.UI_PREVIEW)
    content.setdefault("unknown", [])
    artifact = _artifact(core.UI_PREVIEW, "preview_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.UI_PREVIEW, artifact,
        request.get("idempotency_key") or f"{core.UI_PREVIEW}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-prototype", core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-prototype", core.OK, writes=committed["writes"],
        reason="预览切片已发出（非 canonical），人已签", artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S7 · zj-ui-visual-review
# --------------------------------------------------------------------------- #

def run_visual_review(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""

    problems = core.validate_document(core.UI_REVIEW, candidate)
    if problems:
        return core.result(
            "zj-ui-visual-review", core.REJECTED,
            reason="deny-first：未注册字段或类型不符，未产出 review record",
            rejected=problems,
        )
    gaps = core.stage_gaps("visual_review", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        questions = [f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps[:MAX_QUESTIONS]]
        return core.result(
            "zj-ui-visual-review", core.NEEDS_CONTEXT,
            reason="必填缺口，转 unknown 后停止，零写入",
            questions=questions, unknown=unknown,
        )
    # fingerprint 缺失或无法归因 → 隔离，不产出成功结论（契约 1-3 §3 不代签/不伪 PASS）。
    fingerprint = candidate.get("fingerprint")
    if not (isinstance(fingerprint, dict) and core.is_attributable(fingerprint.get("hash"))):
        return core.result(
            "zj-ui-visual-review", core.QUARANTINED,
            reason="fingerprint 缺失或无法归因，隔离，不产出成功结论",
            quarantined=["fingerprint"],
        )
    if not _human_approved(candidate.get("human_signature")):
        return core.result(
            "zj-ui-visual-review", core.HUMAN_REVIEW_REQUIRED,
            reason="human_gate=required：未签署，下游冻结", questions=[],
        )
    content = _content(candidate, core.UI_REVIEW)
    content.setdefault("unknown", [])
    artifact = _artifact(core.UI_REVIEW, "review_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.UI_REVIEW, artifact,
        request.get("idempotency_key") or f"{core.UI_REVIEW}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-visual-review", core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    return core.result(
        "zj-ui-visual-review", core.OK, writes=committed["writes"],
        reason="review record 已提交，人已签", artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S8 · zj-ui-break
# --------------------------------------------------------------------------- #

REQUIRED_VIEWPORTS = frozenset({"390x844", "768x1024", "1440x900"})


def run_break(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""

    problems = core.validate_document(core.UI_BREAK_CELL, candidate)
    if problems:
        return core.result(
            "zj-ui-break", core.REJECTED,
            reason="deny-first：未注册字段或类型不符，未写 receipt",
            rejected=problems,
        )
    cells = candidate.get("cells") or []
    # fixture matrix 缺失 = 没有断言 = 不得用"部分通过"冒充 PASS（契约 1-3 §3）。
    if not cells:
        return core.result(
            "zj-ui-break", core.BLOCKED, writes=0,
            reason="fixture matrix 缺失，无法断言，不得冒充 PASS",
            rejected=[core.reject("cells", "empty fixture matrix")],
        )
    viewports = set(candidate.get("viewports") or [])
    missing_vp = REQUIRED_VIEWPORTS - viewports
    if missing_vp:
        return core.result(
            "zj-ui-break", core.BLOCKED, writes=0,
            reason=f"viewport 覆盖不足（缺 {sorted(missing_vp)}），不得缩小范围通过",
            rejected=[core.reject("viewports", f"missing viewports: {sorted(missing_vp)}")],
        )
    gaps = core.stage_gaps("break", candidate)  # cells 已非空，此处仅兜底
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        questions = [f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps[:MAX_QUESTIONS]]
        return core.result(
            "zj-ui-break", core.NEEDS_CONTEXT,
            reason="必填缺口，转 unknown 后停止，零写入",
            questions=questions, unknown=unknown,
        )
    failing = [cell for cell in cells if isinstance(cell, dict) and cell.get("status") == "FAIL"]
    content = _content(candidate, core.UI_BREAK_CELL)
    content.setdefault("unknown", [])
    artifact = _artifact(core.UI_BREAK_CELL, "break_cell_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.UI_BREAK_CELL, artifact,
        request.get("idempotency_key") or f"{core.UI_BREAK_CELL}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-break", core.REJECTED,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    status = core.BLOCKED if failing else core.OK
    reason = (
        "break cell 记录实测值，含 FAIL（不降级为 warning）"
        if failing else
        "全矩阵 + 三档视口跑完，receipt 记录实测值"
    )
    return core.result("zj-ui-break", status, writes=committed["writes"], reason=reason, artifact=artifact)


# --------------------------------------------------------------------------- #
# S9 · zj-ui-verify
# --------------------------------------------------------------------------- #

VERIFY_CHAIN_FIELDS = ("claim", "threshold", "command", "commit", "fixture_hash", "env_hash", "artifact", "status")

#: 毕业 gate 派生强制门禁（采纳前提）。
#: run_verify 在 request["enforce_gates"]=true 时要求 receipt 的 checks 覆盖全部 4 门禁且每门禁
#: 至少一个 PASS——缺失即验证矩阵不完整（不生成成功 receipt），未通过即下游冻结。
#: 默认关闭：通用 Storybook adapter 产出五维通用 checks（不含 gate 标记），门禁是叠加在
#: 状态机/表单 UI 之上的验收层，由显式 enforce_gates=true 触发，避免误伤既有 adapter 路径。
REQUIRED_VERIFY_GATES = ("G-V1", "G-V2", "G-V3", "G-V4")


def _verify_content(candidate, fingerprint, checks, aggregate, stale) -> dict:
    """The receipt keeps the full chain so it can be audited offline: who ran it,
    what ran, which environment. Dropping any of these is what let a lie become a
    checkbox."""
    return {
        "checks": checks,
        "fingerprint": fingerprint,
        "checked": candidate.get("checked", len(checks)),
        "aggregate_status": aggregate,
        "stale": stale,
        "unknown": list(candidate.get("unknown") or []),
    }


def run_verify(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""
    # 毕业 gate 派生强制门禁（1-9-4 CONDITIONAL_ADOPTION 采纳前提）。默认关闭：通用
    # Storybook adapter 产出的五维通用 checks 不含 gate 标记；门禁是叠加在状态机/表单
    # UI 之上的验收层，由显式 enforce_gates=true 触发，避免误伤既有 adapter 路径。
    enforce_gates = bool(request.get("enforce_gates"))

    # deny-first at the receipt surface: an unregistered top-level field means the
    # contract drifted and the sentence "unknown stays unknown" must not be quietly
    # dropped.
    problems = core.validate_document(core.VERIFICATION_RECEIPT, candidate)
    if problems:
        return core.result(
            "zj-ui-verify", core.REJECTED,
            reason="deny-first：receipt 含未注册字段，未生成 receipt", rejected=problems,
        )

    # 缺基础链路字段（checks/fingerprint）→ 不构成 receipt，零写入，下游冻结。
    gaps = core.stage_gaps("verify", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        return core.result(
            "zj-ui-verify", core.BLOCKED, writes=0,
            reason="receipt 缺基础链路字段，不生成成功 receipt，下游冻结", unknown=unknown,
        )

    # fingerprint 缺失或无法归因 → 隔离，不产出成功结论（与 S7 一致）。
    fingerprint = candidate.get("fingerprint") or {}
    if not (isinstance(fingerprint, dict) and core.is_attributable(fingerprint.get("hash"))):
        return core.result(
            "zj-ui-verify", core.QUARANTINED, writes=0,
            reason="fingerprint 缺失或无法归因，隔离，不生成成功 receipt",
            quarantined=["fingerprint"],
        )

    checks = candidate.get("checks") or []
    # 空证据不放行：checked==0 一律 HUMAN_REVIEW_REQUIRED，不判 PASS（1-5-3 框架兜底）。
    if not checks:
        return core.result(
            "zj-ui-verify", core.HUMAN_REVIEW_REQUIRED, writes=0,
            reason="checked==0：空证据不放行，不判 PASS", questions=[],
        )

    baseline_only = False
    stale = False
    gate_status = {}  # gate id -> [statuses]，仅收集 G-V1..G-V4
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            return core.result(
                "zj-ui-verify", core.REJECTED, writes=0,
                reason=f"checks[{index}] 不是对象",
                rejected=[core.reject(f"checks[{index}]", "check must be an object")],
            )
        missing = [f for f in VERIFY_CHAIN_FIELDS if not core.is_filled(check.get(f))]
        if missing:
            # 缺链路字段 → 不生成成功 receipt（不是"部分通过"）。
            return core.result(
                "zj-ui-verify", core.BLOCKED, writes=0,
                reason=f"check[{index}] 缺链路字段 {missing}，不生成成功 receipt",
                rejected=[core.reject(f"checks[{index}].{f}", "receipt 链路字段缺失") for f in missing],
            )
        # 强制门禁覆盖：把属于 G-V1..G-V4 的 check 收集起来（缺失=矩阵不完整）。
        gate = check.get("gate")
        if gate in REQUIRED_VERIFY_GATES:
            gate_status.setdefault(gate, []).append(str(check.get("status", "")))
        # baseline 冒充新通过：baseline-only 却声称 PASS。
        if check.get("status") == "PASS" and not check.get("evidence_new", True):
            baseline_only = True
        # stale 基线：check 的环境指纹与当前 fingerprint 不一致。
        if core.is_filled(check.get("env_hash")) and check["env_hash"] != fingerprint.get("hash"):
            stale = True

    # 强制门禁 G-V1..G-V4（仅当显式 enforce_gates=true）。缺覆盖=验证矩阵不完整→不生成成功 receipt。
    gate_problems = []
    if enforce_gates:
        missing_gates = [g for g in REQUIRED_VERIFY_GATES if g not in gate_status]
        if missing_gates:
            return core.result(
                "zj-ui-verify", core.BLOCKED, writes=0,
                reason=f"验证未覆盖强制门禁 {missing_gates}（enforce_gates=true），不生成成功 receipt",
                rejected=[core.reject("checks", f"missing gate coverage: {g}", "verification owner") for g in missing_gates],
            )
        bad_gates = [g for g, statuses in gate_status.items() if any(s != "PASS" for s in statuses)]
        gate_problems = [
            core.reject(
                "checks",
                f"强制门禁 {g} 未通过（status={gate_status[g]}），不生成成功 receipt",
                "verification owner",
            )
            for g in bad_gates
        ]

    if baseline_only:
        return core.result(
            "zj-ui-verify", core.BLOCKED, writes=0,
            reason="用 baseline 冒充新通过，不生成成功 receipt",
            rejected=[core.reject("checks", "baseline-only check cannot claim PASS", "verification owner")],
        )

    # stale：旧证据作废为 revalidation_required，仍产出 receipt 但状态非 PASS。
    if stale:
        content = _verify_content(candidate, fingerprint, checks, core.HUMAN_REVIEW_REQUIRED, stale=True)
        artifact = _artifact(core.VERIFICATION_RECEIPT, "receipt_schema_version", "1.0.0", input_revision, content)
        committed = core.commit(
            store, core.VERIFICATION_RECEIPT, artifact,
            request.get("idempotency_key") or f"{core.VERIFICATION_RECEIPT}:{input_revision}",
        )
        if committed["conflict"]:
            return core.result(
                "zj-ui-verify", core.REJECTED, writes=0,
                reason="幂等键重放但内容不同，拒绝覆盖",
                rejected=[core.reject("idempotency_key", committed["reason"])],
            )
        return core.result(
            "zj-ui-verify", core.HUMAN_REVIEW_REQUIRED, writes=committed["writes"],
            reason="stale 基线，旧证据作废为 revalidation_required，下游冻结", artifact=artifact,
        )

    # 正常：聚合各 check 状态；任一 FAIL → BLOCKED（不生成成功 receipt），全 PASS → OK。
    statuses = [str(check.get("status", "")) for check in checks]
    if "FAIL" in statuses:
        aggregate = core.BLOCKED
    elif all(status == "PASS" for status in statuses):
        aggregate = core.OK
    else:
        aggregate = core.HUMAN_REVIEW_REQUIRED
    # 强制门禁未通过 → 叠加 BLOCKED，不生成成功 receipt（门禁优先于普通聚合）。
    if gate_problems:
        aggregate = core.BLOCKED
    content = _verify_content(candidate, fingerprint, checks, aggregate, stale=False)
    artifact = _artifact(core.VERIFICATION_RECEIPT, "receipt_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.VERIFICATION_RECEIPT, artifact,
        request.get("idempotency_key") or f"{core.VERIFICATION_RECEIPT}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-verify", core.REJECTED, writes=0,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    ok_note = "receipt 链路完整、非 baseline 冒充、非 stale"
    if enforce_gates and not gate_problems:
        ok_note += "、强制门禁 G-V1..G-V4 全通过"
    ok_note += " → 成功 receipt"
    return core.result(
        "zj-ui-verify", aggregate, writes=committed["writes"],
        reason=(ok_note if aggregate == core.OK
                else "receipt 聚合出非 PASS 状态或强制门禁未通过，不生成成功 receipt"),
        rejected=(gate_problems if gate_problems else None),
        artifact=artifact,
    )


# --------------------------------------------------------------------------- #
# S10 · zj-ui-handoff
# --------------------------------------------------------------------------- #

def run_handoff(request: dict, store: dict | None = None) -> dict:
    store = {} if store is None else store
    candidate = request.get("candidate") or {}
    receipt = request.get("receipt") or {}
    input_revision = request.get("input_revision") or ""

    problems = core.validate_document(core.HANDOFF, candidate)
    if problems:
        return core.result(
            "zj-ui-handoff", core.REJECTED,
            reason="deny-first：handoff 含未注册字段，未生成 handoff", rejected=problems,
        )

    # 缺任一必填 → handoff incomplete，逐项列缺口，不标记完成（不自行补齐）。
    gaps = core.stage_gaps("handoff", candidate)
    if gaps:
        unknown = core.gaps_as_unknown(gaps, candidate, input_revision)
        return core.result(
            "zj-ui-handoff", core.HUMAN_REVIEW_REQUIRED, writes=0,
            reason="handoff 不完整，逐项列缺口，不标记完成",
            unknown=unknown,
            questions=[f"{field}：{core.GAP_REASONS.get(field, field)}" for field in gaps],
        )

    # receipt 非 PASS → 不产出完整 handoff（可产出缺口清单）。
    if (receipt or {}).get("status") != core.OK:
        return core.result(
            "zj-ui-handoff", core.HUMAN_REVIEW_REQUIRED, writes=0,
            reason="receipt 非 PASS，不产出完整 handoff（可产出缺口清单）",
            questions=["verification receipt 必须 status=OK 才能接手"],
        )

    content = {
        "change_summary": candidate["change_summary"],
        "run_commands": candidate["run_commands"],
        "risks": candidate["risks"],
        "known_limits": candidate["known_limits"],
        "fallback": candidate["fallback"],
        "owner": candidate["owner"],
        "artifacts_revisions": candidate["artifacts_revisions"],
        "commit_sha": candidate["commit_sha"],
        "unknown": list(candidate.get("unknown") or []),
    }
    artifact = _artifact(core.HANDOFF, "handoff_schema_version", "1.0.0", input_revision, content)
    committed = core.commit(
        store, core.HANDOFF, artifact,
        request.get("idempotency_key") or f"{core.HANDOFF}:{input_revision}",
    )
    if committed["conflict"]:
        return core.result(
            "zj-ui-handoff", core.REJECTED, writes=0,
            reason="幂等键重放但内容不同，拒绝覆盖",
            rejected=[core.reject("idempotency_key", committed["reason"])],
        )
    # adapter 不可用也走这条路径：handoff 不依赖任何外部链接，可脱离 adapter 维护。
    return core.result(
        "zj-ui-handoff", core.OK, writes=committed["writes"],
        reason="六项齐全、receipt 已 PASS，handoff 原子提交（不依赖 adapter）", artifact=artifact,
    )


STAGES = {
    "brief": run_brief,
    "discover": run_discover,
    "direction": run_direction,
    "design_system": run_design_system,
    "flow": run_flow,
    "prototype": run_prototype,
    "visual_review": run_visual_review,
    "break": run_break,
    "verify": run_verify,
    "handoff": run_handoff,
}

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


STAGES = {
    "brief": run_brief,
    "discover": run_discover,
    "direction": run_direction,
    "design_system": run_design_system,
}

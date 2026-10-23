"""Deterministic resolver for the `zj-ui-*` chain.

This is the faithful reification of `ui-agent-skills-resolver-contract.md`. The
resolver is a pure function: same inputs -> byte-identical `plan_hash`, same
`next_action`, zero writes, zero hidden state. It never calls a skill, never
touches a canonical artifact, never reads the clock.

Seven fixed steps : R1 schema check -> R2 filter forbidden -> R3 match
required_capabilities -> R4 stage-owner filter -> R5 precedence top (unique) ->
R6 Human gate -> R7 single next_action. Any hard stop freezes the plan with zero
skill invocations .

Frozen terminal statuses :
    PLANNED, WAITING_FOR_HUMAN, FROZEN_CONFLICT, UNSUPPORTED_INPUT,
    AMBIGUOUS, CONFIG_ERROR, INVALID_INPUT
"""

from __future__ import annotations

import hashlib
import json
import unicodedata

import ui_skill_core as core
import ui_registry as reg


# --------------------------------------------------------------------------- #
# Plan statuses (resolver-contract.md )
# --------------------------------------------------------------------------- #

PLANNED = "PLANNED"
WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
FROZEN_CONFLICT = "FROZEN_CONFLICT"
UNSUPPORTED_INPUT = "UNSUPPORTED_INPUT"
AMBIGUOUS = "AMBIGUOUS"
CONFIG_ERROR = "CONFIG_ERROR"
INVALID_INPUT = "INVALID_INPUT"

# Statuses under which the orchestrator MUST NOT execute any skill .
FROZEN_STATUSES = {
    WAITING_FOR_HUMAN,
    FROZEN_CONFLICT,
    UNSUPPORTED_INPUT,
    AMBIGUOUS,
    CONFIG_ERROR,
    INVALID_INPUT,
}

# Gate states . Only APPROVED lets a required-gate skill proceed.
GATE_APPROVED = "APPROVED"
GATE_PENDING = "PENDING"
GATE_REJECTED = "REJECTED"
GATE_EXPIRED = "EXPIRED"
GATE_NOT_REQUIRED = "NOT_REQUIRED"


# --------------------------------------------------------------------------- #
# Canonicalization (resolver-contract.md , N1-N7)
# --------------------------------------------------------------------------- #


def canonical_json(payload) -> str:
    """Byte-stable JSON (delegates to the shared core canonical form)."""
    return core.canonical_json(payload)


def _normalize(value, _in_unknown=False):
    """Apply N2 (unify null/""/[]/{}) and N4 (NFC + strip).

    The `unknown` quartet list is preserved verbatim: its entries carry meaning
    even when a value is null, so collapsing it would destroy information.
    """
    if isinstance(value, dict):
        if _in_unknown:
            return {k: _normalize(v, _in_unknown=True) for k, v in value.items()}
        normalized = {k: _normalize(v) for k, v in value.items()}
        # N2: an empty object collapses to null (but `unknown` lists survive
        # because they are leaf lists, handled below).
        return normalized
    if isinstance(value, list):
        if _in_unknown:
            return [_normalize(item, _in_unknown=True) for item in value]
        if not value:
            return None  # N2: empty list -> null
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        text = unicodedata.normalize("NFC", value).strip()
        return text if text else None  # N2/N4: blank -> null
    if isinstance(value, float):
        # N5: fixed 6-decimal precision, trailing zeros stripped.
        return round(value, 6)
    return value


def canonicalize_request(request: dict, artifact_snapshot: dict) -> dict:
    """ normalization of the request + artifact snapshot, minus `request_id`.

    `request_id` is audit-only and is explicitly excluded from `plan_hash`
    . `unknown` quartets are preserved, never collapsed N2 exception).
    """
    req = dict(request or {})
    req.pop("request_id", None)
    norm_req = _normalize({k: v for k, v in req.items() if k != "unknown"})
    if "unknown" in req:
        norm_req["unknown"] = _normalize(req["unknown"], _in_unknown=True)
    norm_artifact = _normalize(artifact_snapshot or {})
    return {"request": norm_req, "artifact_snapshot": norm_artifact}


# --------------------------------------------------------------------------- #
# Fingerprints + plan hash / )
# --------------------------------------------------------------------------- #


def route_fingerprint(normalized_request: dict, artifact_ref: dict,
                      manifest_version_set: dict, precedence_ver: str,
                      gate_state: str) -> str:
    payload = canonical_json(
        {
            "normalized_request": normalized_request,
            "artifact_ref": artifact_ref,
            "manifest_version_set": manifest_version_set,
            "precedence_version": precedence_ver,
            "gate_state": gate_state,
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_hash(route_fp: str, *, stage: str, owner_skill: str, manifest_version: str,
              candidates: list, eliminated: list, next_action: dict | None,
              gate_state: str, artifact_ref: dict) -> str:
    # candidates / eliminated are sorted so ordering never alters the hash R5).
    payload = canonical_json(
        {
            "route_fingerprint": route_fp,
            "stage": stage,
            "owner_skill": owner_skill,
            "manifest_version": manifest_version,
            "candidates": sorted(candidates),
            "eliminated": sorted(eliminated, key=lambda e: e["skill_id"]),
            "next_action": next_action,
            "gate_state": gate_state,
            "artifact_ref": artifact_ref,
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_artifact_ref(artifact_snapshot: dict) -> dict:
    if not isinstance(artifact_snapshot, dict):
        return {}
    return {
        "artifact_kind": artifact_snapshot.get("artifact_kind"),
        "revision": artifact_snapshot.get("revision"),
        "schema_version": artifact_snapshot.get("schema_version"),
    }


def _stage_artifact_kind(stage: str) -> str | None:
    """The canonical artifact the stage ultimately writes, for owner grouping."""
    return {
        "brief": "UI-BRIEF.md",
        "discover": "UI-BRIEF.md",
        "direction": "UI-DESIGN.md",
        "design_system": "UI-DESIGN.md",
        "flow": "ui-flow/v1",
        "prototype": None,  # emit-only, non-canonical
        "visual_review": "review record",
        "break": "verification receipt",
        "verify": "verification receipt",
        "handoff": "handoff",
    }.get(stage)


# --------------------------------------------------------------------------- #
# Plan builder
# --------------------------------------------------------------------------- #


def _plan(*, status: str, stage: str | None, registry, gate_state: str,
         artifact_ref: dict, eliminated=None, next_action=None, reason: str = "",
         route_fp: str = "", precedence_ver: str = "") -> dict:
    owner_skill = next_action["skill_id"] if next_action else None
    mver = next_action["manifest_version"] if next_action else None
    candidates = [m["skill_id"] for m in registry if stage is None or m["stage"] == stage]
    ph = ""
    if status == PLANNED and next_action and route_fp:
        ph = plan_hash(
            route_fp,
            stage=stage,
            owner_skill=owner_skill,
            manifest_version=mver,
            candidates=candidates,
            eliminated=eliminated or [],
            next_action=next_action,
            gate_state=gate_state,
            artifact_ref=artifact_ref,
        )
    return {
        "plan_id": (
            f"pf-{route_fp[:12]}-{stage}-0" if route_fp else f"pf-{stage}-0"
        ),
        "plan_hash": ph,
        "route_fingerprint": route_fp,
        "stage": stage,
        "owner_skill": owner_skill,
        "manifest_version": mver,
        "precedence_version": precedence_ver,
        "candidates": candidates,
        "eliminated": eliminated or [],
        "next_action": next_action,
        "gate_state": gate_state,
        "artifact_ref": artifact_ref,
        "status": status,
        "reason": reason,
        # The number of skill invocations a frozen plan permits: always 0 .
        "permitted_writes": 0 if status in FROZEN_STATUSES else 1,
    }


# --------------------------------------------------------------------------- #
# The resolver (resolver-contract.md )
# --------------------------------------------------------------------------- #


def resolve(request: dict, artifact_snapshot: dict, registry: list,
            gate_state: str, target_stage: str | None = None) -> dict:
    """Pure routing decision. No writes, no skill calls, deterministic.

    `target_stage` lets the orchestrator name the pipeline position; when absent
    the request's `artifact_kind_hint` is used. Returns a Plan dict.
    """
    artifact_ref = _build_artifact_ref(artifact_snapshot)
    precedence_ver = reg.precedence_version(registry)
    norm = canonicalize_request(request, artifact_snapshot)
    route_fp = route_fingerprint(
        norm,
        artifact_ref,
        {m["skill_id"]: m["manifest_version"] for m in registry},
        precedence_ver,
        gate_state,
    )

    # R1 — schema / artifact check. A request that names a target stage but
    # supplies a malformed artifact snapshot cannot be planned.
    if target_stage is not None and not isinstance(artifact_snapshot, dict):
        return _plan(
            status=INVALID_INPUT, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref,
            reason="artifact_snapshot 不是对象", route_fp=route_fp,
            precedence_ver=precedence_ver,
        )

    # Candidate set: manifests for the target stage (or all if un-targeted).
    if target_stage is None:
        hint = (request or {}).get("artifact_kind_hint")
        candidates = [m for m in registry if m["stage"] == hint] if hint else list(registry)
    else:
        candidates = [m for m in registry if m["stage"] == target_stage]

    if not candidates:
        return _plan(
            status=UNSUPPORTED_INPUT, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref,
            reason="无候选 skill（stage 未注册或 hint 未知）",
            route_fp=route_fp, precedence_ver=precedence_ver,
        )

    eliminated = []
    # R2 — filter forbidden. The orchestrator never sets forbidden_hit in the
    # happy path; a request can declare it to simulate a forbidden trigger.
    forbidden_hit = (request or {}).get("forbidden_hit")
    if forbidden_hit:
        for m in candidates:
            if forbidden_hit in m.get("forbidden", []):
                eliminated.append({"skill_id": m["skill_id"], "reason": f"forbidden:{forbidden_hit}"})

    # R3 — match required_capabilities. Capabilities not in the available set
    # eliminate the candidate; no candidates left -> UNSUPPORTED_INPUT.
    available = set((request or {}).get("available_capabilities") or _all_capabilities(registry))
    for m in list(candidates):
        missing = [c for c in m.get("required_capabilities", []) if c not in available]
        if missing:
            candidates.remove(m)
            eliminated.append(
                {"skill_id": m["skill_id"], "reason": f"missing_capability:{','.join(missing)}"}
            )
    if not candidates:
        return _plan(
            status=UNSUPPORTED_INPUT, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref, eliminated=eliminated,
            reason="候选全部因缺能力被淘汰", route_fp=route_fp,
            precedence_ver=precedence_ver,
        )

    # R4 — stage write-owner filter. For the stage's canonical artifact there
    # must be exactly one write owner; otherwise the plan freezes (FF-ORCH-01).
    artifact_kind = _stage_artifact_kind(target_stage) if target_stage else None
    write_owners = [
        m for m in candidates
        if m["owner_scope"] == "write" and (artifact_kind is None or artifact_kind in m.get("writes", []))
    ]
    if artifact_kind is not None and len(write_owners) != 1:
        return _plan(
            status=FROZEN_CONFLICT, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref, eliminated=eliminated,
            reason=f"BLOCKED_OWNER_CONFLICT: ({target_stage}, {artifact_kind}) 写 owner 数={len(write_owners)}",
            route_fp=route_fp, precedence_ver=precedence_ver,
        )

    # R5 — precedence sort; the top must be unique. A tie is AMBIGUOUS and the
    # chain stops (FF-ORCH-04). When there is exactly one candidate, it wins.
    ordered = sorted(candidates, key=lambda m: m["precedence"])
    if len(ordered) >= 2 and ordered[0]["precedence"] == ordered[1]["precedence"]:
        return _plan(
            status=AMBIGUOUS, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref, eliminated=eliminated,
            reason="precedence 并列，无法消解（禁止 tie-breaker）",
            route_fp=route_fp, precedence_ver=precedence_ver,
        )
    chosen = ordered[0]

    # R6 — Human gate. A required gate not APPROVED freezes the plan. Rejected /
    # expired gates freeze as a conflict; pending / not-required wait for human.
    if chosen["human_gate"] == "required" and gate_state != GATE_APPROVED:
        if gate_state in (GATE_REJECTED, GATE_EXPIRED):
            return _plan(
                status=FROZEN_CONFLICT, stage=target_stage, registry=registry,
                gate_state=gate_state, artifact_ref=artifact_ref, eliminated=eliminated,
                reason="gate rejected/expired，不得自动推进", route_fp=route_fp,
                precedence_ver=precedence_ver,
            )
        return _plan(
            status=WAITING_FOR_HUMAN, stage=target_stage, registry=registry,
            gate_state=gate_state, artifact_ref=artifact_ref, eliminated=eliminated,
            reason="human_gate=required 且未 APPROVED，零写入", route_fp=route_fp,
            precedence_ver=precedence_ver,
        )

    # R7 — a single next_action only.
    next_action = {
        "skill_id": chosen["skill_id"],
        "manifest_version": chosen["manifest_version"],
        "action": chosen["stage"],
        "input_ref": artifact_ref,
    }
    return _plan(
        status=PLANNED, stage=target_stage, registry=[chosen], gate_state=gate_state,
        artifact_ref=artifact_ref, eliminated=eliminated, next_action=next_action,
        reason="route 完成，单一 next_action", route_fp=route_fp,
        precedence_ver=precedence_ver,
    )


def _all_capabilities(registry: list) -> list:
    caps = set()
    for m in registry:
        caps.update(m.get("required_capabilities", []))
    return sorted(caps)

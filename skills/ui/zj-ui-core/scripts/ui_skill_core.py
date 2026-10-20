"""Deterministic core for the `zj-ui-*` chain (S0 base skill of `skills/ui/`).

Why this file exists: every stage skill in `skills/ui/` claims behaviours that are
cheap to write in prose and impossible to falsify — "missing required field becomes
`NEEDS_CONTEXT`", "unregistered field is rejected, never silently dropped",
"unknown keeps its four-part quartet", "the revision is committed atomically with an
idempotency key". Without a single deterministic implementation those claims decay
into adjectives the moment someone edits a SKILL.md.

Division of labour (frozen by roadmap 1-6-2 decision):

* an agent reads the human conversation and produces a **structured request**;
* this module never parses natural language — it validates, refuses, preserves and
  commits. That keeps every fixture byte-reproducible.

Nothing here performs an effect: no network, no credentials, no remote write.
"""

from __future__ import annotations

import hashlib
import json
import re

# --------------------------------------------------------------------------- #
# Statuses
# --------------------------------------------------------------------------- #

OK = "OK"
NEEDS_CONTEXT = "NEEDS_CONTEXT"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
QUARANTINED = "QUARANTINED"
BLOCKED = "BLOCKED"
REJECTED = "REJECTED"

#: Worst-first. A stage that hits several conditions reports the most severe one,
#: so a run can never "pass" by having a mild finding mask a hard one.
STATUS_PRIORITY = (
    REJECTED,
    BLOCKED,
    QUARANTINED,
    HUMAN_REVIEW_REQUIRED,
    NEEDS_CONTEXT,
    OK,
)


def worst(*statuses: str) -> str:
    """Return the most severe status; `OK` when nothing was reported."""
    ranked = [status for status in statuses if status]
    if not ranked:
        return OK
    return min(ranked, key=STATUS_PRIORITY.index)


# --------------------------------------------------------------------------- #
# Canonical artifacts (schema frozen by 1-2-1 / `canonical-schema.md`)
# --------------------------------------------------------------------------- #

BRIEF = "UI-BRIEF.md"
DESIGN = "UI-DESIGN.md"

# field -> (python type name, owner, required, unknown policy)
SCHEMAS = {
    BRIEF: {
        "goal_users": ("list", "brief/contract owner", "yes", "missing -> unknown quartet"),
        "goal_task": ("str", "brief/contract owner", "yes", "missing -> unknown quartet"),
        "constraints": ("list", "brief/contract owner", "yes", "missing -> unknown quartet"),
        "success_criteria": ("list", "brief/contract owner", "yes", "missing -> unknown quartet"),
        "unknown": ("list", "brief/contract owner", "conditional", "quartet preserved"),
        "source_ref": ("dict", "brief/contract owner", "no", "adapter reference only"),
    },
    DESIGN: {
        "direction_choice": ("str", "direction/design owner", "yes", "no source -> human gate"),
        "tokens": ("dict", "direction/design owner", "yes", "contrast fail -> block"),
        "typography": ("dict", "direction/design owner", "yes", "license unknown -> quarantine"),
        "color": ("dict", "direction/design owner", "yes", "contrast fail -> block"),
        "component_principles": ("list", "direction/design owner", "yes", "-"),
        "tradeoffs": ("list", "direction/design owner", "yes", "-"),
        "provenance": ("dict", "direction/design owner", "required-if-external", "unknown source -> quarantine"),
        "unknown": ("list", "direction/design owner", "conditional", "quartet preserved"),
    },
}

#: Which fields each stage is responsible for producing. A stage validates the
#: whole document (deny-first) but only owes its own slice of required fields,
#: because `UI-DESIGN.md` is written by S3 and S4 in two passes.
STAGE_FIELDS = {
    "brief": (BRIEF, ("goal_users", "goal_task", "constraints", "success_criteria")),
    "discover": (BRIEF, ()),
    "direction": (DESIGN, ("direction_choice", "provenance")),
    "design_system": (
        DESIGN,
        ("tokens", "typography", "color", "component_principles", "tradeoffs"),
    ),
}

#: Why a gap exists, in the words the human will read back. Kept next to the
#: schema so a new required field cannot be added without deciding its sentence.
GAP_REASONS = {
    "goal_users": "未声明目标用户",
    "goal_task": "未声明要完成的任务",
    "constraints": "未声明约束（或显式 empty-with-reason）",
    "success_criteria": "未声明成功标准",
    "direction_choice": "未选定方向（Human gate 未签）",
    "provenance": "外部参考缺 provenance",
    "tokens": "未产出 token",
    "typography": "未产出字体规则",
    "color": "未产出色板",
    "component_principles": "未产出组件原则",
    "tradeoffs": "未产出取舍说明",
}

PY_TYPES = {"list": list, "str": str, "dict": dict}

UNKNOWN_KEYS = ("path", "raw", "reason", "source")

#: Component catalog owned by this repository. An adapter may project this list;
#: it may not extend it. Anything outside is "unregistered" and therefore blocked.
COMPONENT_REGISTRY = frozenset(
    {
        "Alert", "Avatar", "Badge", "Breadcrumb", "Button", "Card", "Checkbox",
        "Dialog", "Drawer", "EmptyState", "FieldSet", "Form", "IconButton",
        "Input", "Menu", "Pagination", "Radio", "Select", "Skeleton", "Spinner",
        "Switch", "Table", "Tabs", "Tag", "Textarea", "Toast", "Tooltip",
    }
)

CONTRAST_MIN = 4.5


class CoreError(ValueError):
    """Raised for a programming-level misuse, never for a fixture outcome."""


# --------------------------------------------------------------------------- #
# Canonical form, revisions, idempotent commit
# --------------------------------------------------------------------------- #


def canonical_json(payload) -> str:
    """Byte-stable JSON: sorted keys, no incidental whitespace, UTF-8 kept."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def revision_of(payload) -> str:
    """`revision` = sha256 of the canonical content (schema version 1-2-1 rule)."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def commit(store: dict, artifact_kind: str, payload, idempotency_key: str) -> dict:
    """Commit a revision atomically and idempotently.

    `store` is any dict-like journal; the caller owns persistence. Replaying the
    same `(artifact_kind, idempotency_key)` with identical content must not write
    twice — that is `FF-ORCH-03`'s "100 replays, one effective write". Replaying
    the same key with **different** content is a conflict, not a silent overwrite.
    """
    if not idempotency_key:
        raise CoreError("idempotency_key is required for an atomic commit")

    revision = revision_of(payload)
    key = (artifact_kind, idempotency_key)
    previous = store.get(key)

    if previous is not None:
        if previous["revision"] != revision:
            return {
                "committed": False,
                "revision": previous["revision"],
                "writes": 0,
                "conflict": True,
                "reason": "idempotency key replay with different content",
            }
        return {"committed": False, "revision": revision, "writes": 0, "conflict": False}

    store[key] = {"revision": revision, "payload": payload}
    return {"committed": True, "revision": revision, "writes": 1, "conflict": False}


# --------------------------------------------------------------------------- #
# unknown quartet
# --------------------------------------------------------------------------- #


def make_unknown(path: str, raw, reason: str, source: str) -> dict:
    """A quartet, never a collapsed empty value.

    `raw` is allowed to be `None` — "we were told nothing" is information. What is
    forbidden is dropping the key or substituting a plausible value to make the
    document look complete.
    """
    return {"path": path, "raw": raw, "reason": reason, "source": source}


def validate_quartets(entries) -> list:
    """Return rejection records for anything that is not a four-key quartet."""
    problems = []
    if not isinstance(entries, list):
        return [reject("unknown", "unknown must be a list of quartets")]
    for index, entry in enumerate(entries):
        field = f"unknown[{index}]"
        if not isinstance(entry, dict):
            problems.append(reject(field, "unknown entry is not an object"))
            continue
        missing = [key for key in UNKNOWN_KEYS if key not in entry]
        extra = [key for key in entry if key not in UNKNOWN_KEYS]
        if missing:
            problems.append(reject(field, f"unknown entry missing keys: {', '.join(missing)}"))
        if extra:
            problems.append(reject(field, f"unknown entry has unregistered keys: {', '.join(extra)}"))
        if isinstance(entry.get("reason"), str) and not entry["reason"].strip():
            problems.append(reject(field, "unknown reason must not be blank"))
        if isinstance(entry.get("path"), str) and not entry["path"].strip():
            problems.append(reject(field, "unknown path must not be blank"))
    return problems


def reject(field: str, reason: str, suggested_owner: str = "", recoverable: bool = False) -> dict:
    """Uniform deny-first reply (1-2-2 §3). Never downgraded to a warning."""
    return {
        "field": field,
        "reason": reason,
        "suggested_owner": suggested_owner,
        "recoverable": recoverable,
    }


# --------------------------------------------------------------------------- #
# deny-first validation
# --------------------------------------------------------------------------- #


def validate_document(artifact_kind: str, document) -> list:
    """Reject unregistered fields and type violations. Returns rejection records.

    Unknown keys are **not** dropped: silently discarding them would let a typo
    (`success_criteria` vs `successCriteria`) look like a resolved document.
    """
    schema = SCHEMAS.get(artifact_kind)
    if schema is None:
        raise CoreError(f"unknown artifact kind: {artifact_kind}")
    if not isinstance(document, dict):
        return [reject(artifact_kind, "document must be an object")]

    problems = []
    for field, value in document.items():
        spec = schema.get(field)
        if spec is None:
            problems.append(
                reject(field, f"unregistered field for {artifact_kind}", spec_owner(artifact_kind))
            )
            continue
        expected = spec[0]
        if not isinstance(value, PY_TYPES[expected]):
            problems.append(
                reject(field, f"type mismatch: expected {expected}, got {type(value).__name__}")
            )
    if "unknown" in document:
        problems.extend(validate_quartets(document["unknown"]))
    return problems


def spec_owner(artifact_kind: str) -> str:
    schema = SCHEMAS[artifact_kind]
    owners = {spec[1] for spec in schema.values()}
    return owners.pop() if len(owners) == 1 else ""


def is_filled(value) -> bool:
    """`filled` means: present and carrying meaning. An empty list is a gap."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def stage_gaps(stage: str, document) -> list:
    """Fields this stage owes but the document does not fill, in schema order."""
    if stage not in STAGE_FIELDS:
        raise CoreError(f"unknown stage: {stage}")
    _, required = STAGE_FIELDS[stage]
    if not isinstance(document, dict):
        return list(required)
    return [field for field in required if not is_filled(document.get(field))]


def gaps_as_unknown(gaps, document, source: str) -> list:
    """Turn each gap into a quartet instead of inventing a value."""
    return [
        make_unknown(
            path=field,
            raw=(document or {}).get(field),
            reason=GAP_REASONS.get(field, f"缺少必填字段 {field}"),
            source=source,
        )
        for field in gaps
    ]


# --------------------------------------------------------------------------- #
# evidence attribution
# --------------------------------------------------------------------------- #

_NON_SOURCES = {"", "unknown", "n/a", "na", "none", "assumed", "guess", "猜测"}


def is_attributable(source) -> bool:
    """A claim counts as evidence only when its origin can be named."""
    if not isinstance(source, str):
        return False
    return source.strip().lower() not in _NON_SOURCES


# --------------------------------------------------------------------------- #
# WCAG contrast
# --------------------------------------------------------------------------- #

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _linear(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    if not isinstance(color, str) or not _HEX.match(color):
        raise CoreError(f"not a hex colour: {color!r}")
    digits = color.lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    red, green, blue = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.x relative-luminance ratio, rounded to 3 decimals."""
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return round((light + 0.05) / (dark + 0.05), 3)


def contrast_pairs(color: dict) -> list:
    """The two pairs the design schema actually promises readability for."""
    pairs = []
    for fg, bg, role in (
        ("on_surface", "surface", "body"),
        ("on_primary", "primary", "primary-action"),
    ):
        if is_filled(color.get(fg)) and is_filled(color.get(bg)):
            pairs.append((role, color[fg], color[bg]))
    return pairs


# --------------------------------------------------------------------------- #
# result envelope
# --------------------------------------------------------------------------- #


def result(skill_id: str, status: str, *, writes: int = 0, reason: str = "",
           questions=None, unknown=None, rejected=None, quarantined=None,
           artifact=None, candidates=None) -> dict:
    """Fixed-shape reply so fixtures assert a contract, not whatever was emitted."""
    return {
        "skill_id": skill_id,
        "status": status,
        "writes": writes,
        "reason": reason,
        "questions": list(questions or []),
        "unknown": list(unknown or []),
        "rejected": list(rejected or []),
        "quarantined": list(quarantined or []),
        "candidates": list(candidates or []),
        "artifact": artifact,
    }

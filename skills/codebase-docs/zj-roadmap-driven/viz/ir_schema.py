"""Frozen view-ir schema (S1 exit criterion).

The schema is a published contract, not a description of today's code: any
field added, removed or renamed makes ``validate_view`` fail. Changing it
requires an explicit version bump *and* an update of these frozen sets.
"""
from __future__ import annotations

VIEW_IR_SCHEMA_VERSION = "zj-roadmap-view-ir/v1"

TOP_LEVEL_KEYS = frozenset({
    "envelope", "selection", "rest", "expanded_set", "cards", "presets",
})
ENVELOPE_KEYS = frozenset({
    "view_kind", "carrier_stem", "node_uid", "carrier_revision", "focus",
    "theta", "generated_by", "authority", "schema",
})
SELECTION_KEYS = frozenset({
    "shown", "lod", "compressed", "theta", "theta_folded", "budget_folded",
    "budget_overflow", "used", "budget", "mandatory", "pdepth", "fp",
})
CARD_KEYS = frozenset({
    "id", "uid", "label", "status", "mode", "rounds", "parent", "layer",
    "notes", "decisions", "exit_criteria", "budget", "lod", "doi",
    "debt_level", "debt_hits", "is_focus", "is_block_pred", "is_sibling",
})


def validate_view(view: dict) -> list[str]:
    """Return schema violations; empty means the frozen contract still holds."""
    errors: list[str] = []

    def check(label: str, actual, expected: frozenset[str]) -> None:
        got = frozenset(actual)
        if got != expected:
            missing = sorted(expected - got)
            extra = sorted(got - expected)
            errors.append(f"{label}: missing={missing} extra={extra}")

    check("view", view, TOP_LEVEL_KEYS)
    if view.get("envelope", {}).get("schema") != VIEW_IR_SCHEMA_VERSION:
        errors.append(f"envelope.schema must be {VIEW_IR_SCHEMA_VERSION!r}")
    check("envelope", view.get("envelope", {}), ENVELOPE_KEYS)
    check("selection", view.get("selection", {}), SELECTION_KEYS)
    cards = view.get("cards", {})
    items = cards.items() if isinstance(cards, dict) else enumerate(cards)
    for card_id, card in items:
        check(f"card[{card_id}]", card, CARD_KEYS)
    return errors


def assert_frozen(view: dict) -> None:
    errors = validate_view(view)
    if errors:
        raise ValueError("view-ir schema drift: " + "; ".join(errors[:3]))

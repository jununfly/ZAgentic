"""Delta re-entry receipt (C::09 / INV::11 / RE::v1). Read-only projection.

The receipt is a separate, Human-addressed artifact in a gitignored isolated
zone. It never enters the carrier, never participates in view-ir computation,
and a missing/corrupt receipt fails closed to a full view with an explicit note.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RECEIPT_VERSION = "zj-roadmap-view-receipt/v1"
RECEIPT_FIELDS = frozenset({
    "version", "anchor", "carrier_revision", "theta", "seen_item_hashes",
})
DELTA_KINDS = ("added", "changed", "removed", "stable-folded")
HASHED_NODE_FIELDS = (
    "label", "status", "mode", "notes", "decisions", "exit_criteria", "rounds",
)


def item_hashes(graph, ids: list[str]) -> dict[str, str]:
    """Stable per-item content hashes; view LOD / θ deliberately excluded."""
    hashes: dict[str, str] = {}
    for nid in sorted(ids):
        node = graph.nodes.get(nid, {})
        payload = {field: node.get(field) for field in HASHED_NODE_FIELDS}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               default=str)
        hashes[nid] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return hashes


def load_receipt(path: str | Path) -> tuple[dict | None, str | None]:
    """Return (receipt, warning). Corrupt or missing never raises to the view."""
    target = Path(path)
    if not target.is_file():
        return None, f"receipt 不存在，fail-closed 回退全量：{target.name}"
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"receipt 损坏，fail-closed 回退全量：{exc}"
    if not isinstance(data, dict) or frozenset(data) != RECEIPT_FIELDS:
        return None, "receipt 字段不符，fail-closed 回退全量"
    if data.get("version") != RECEIPT_VERSION or not isinstance(
        data.get("seen_item_hashes"), dict
    ):
        return None, "receipt 版本/哈希结构不符，fail-closed 回退全量"
    return data, None


def write_receipt(path: str | Path, *, anchor: str, carrier_revision: str,
                  theta: float, hashes: dict[str, str]) -> None:
    """Write only to a path the Human explicitly supplied (ADR 0010)."""
    payload = {
        "version": RECEIPT_VERSION,
        "anchor": anchor,
        "carrier_revision": str(carrier_revision),
        "theta": float(theta),
        "seen_item_hashes": dict(sorted(hashes.items())),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n", encoding="utf-8")


def full_fallback(ids: list[str], warning: str) -> dict:
    """Explicit full view; never silently pretend an increment was computed."""
    return {
        "mode": "full-fallback",
        "added": sorted(ids),
        "changed": [],
        "removed": [],
        "stable-folded": 0,
        "warning": warning,
    }


def compute_delta(current: dict[str, str], baseline: dict | None,
                  warning: str | None) -> dict:
    if baseline is None or warning:
        return full_fallback(list(current), warning or "无 baseline，输出全量")
    previous: dict[str, str] = baseline["seen_item_hashes"]
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    changed = sorted(k for k in set(current) & set(previous)
                     if current[k] != previous[k])
    stable = len(set(current) & set(previous)) - len(changed)
    return {
        "mode": "delta",
        "added": added,
        "changed": changed,
        "removed": removed,
        "stable-folded": stable,
        "warning": None,
    }

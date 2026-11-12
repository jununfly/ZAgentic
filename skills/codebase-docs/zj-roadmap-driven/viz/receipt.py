"""Delta re-entry receipt (C::09 / INV::11 / RE::v1 + S1b portability).

The receipt is a separate, Human-addressed artifact in a gitignored isolated
zone. It never enters the carrier, never participates in view-ir computation,
and a missing/corrupt/expired receipt fails closed to a full view with an
explicit note.

A receipt is a *disposable derived cache*, not authoritative state. v2 adds a
device identity and a TTL so a receipt produced on one machine can be carried
to another by an explicit Human-chosen path. There is no network protocol and
no distributed consensus: if two receipts cannot be safely merged, the caller
falls back to a full view (see merge_baselines).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

RECEIPT_VERSION_V1 = "zj-roadmap-view-receipt/v1"
RECEIPT_VERSION_V2 = "zj-roadmap-view-receipt/v2"
# Backwards-compatible alias: S1 code and guards refer to RECEIPT_VERSION.
RECEIPT_VERSION = RECEIPT_VERSION_V1
SUPPORTED_VERSIONS = frozenset({RECEIPT_VERSION_V1, RECEIPT_VERSION_V2})
RECEIPT_FIELDS = frozenset({
    "version", "anchor", "carrier_revision", "theta", "seen_item_hashes",
})
RECEIPT_FIELDS_V2 = RECEIPT_FIELDS | {
    "device_id", "generated_at", "ttl_seconds",
}
DELTA_KINDS = ("added", "changed", "removed", "stable-folded")
HASHED_NODE_FIELDS = (
    "label", "status", "mode", "notes", "decisions", "exit_criteria", "rounds",
)


def _fields_for(version: str) -> frozenset[str] | None:
    if version == RECEIPT_VERSION_V1:
        return RECEIPT_FIELDS
    if version == RECEIPT_VERSION_V2:
        return RECEIPT_FIELDS_V2
    return None


def _valid_hashes(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    )


def is_expired(receipt: dict | None, *, now: float | None = None) -> bool:
    """A v1 receipt never expires; a v2 receipt expires after its TTL.

    Malformed v2 timing fields are treated as expired (fail-closed). `now` is
    injectable so expiry can be asserted without sleeping.
    """
    if not isinstance(receipt, dict):
        return True
    if receipt.get("version") == RECEIPT_VERSION_V1:
        return False
    generated = receipt.get("generated_at")
    ttl = receipt.get("ttl_seconds")
    if not isinstance(generated, (int, float)) or isinstance(generated, bool):
        return True
    if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl <= 0:
        return True
    clock = time.time() if now is None else now
    return clock > float(generated) + float(ttl)


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


def load_receipt(path: str | Path, *, now: float | None = None
                 ) -> tuple[dict | None, str | None]:
    """Return (receipt, warning). Corrupt/missing/expired never raises to view."""
    target = Path(path)
    if not target.is_file():
        return None, f"receipt 不存在，fail-closed 回退全量：{target.name}"
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"receipt 损坏，fail-closed 回退全量：{exc}"
    if not isinstance(data, dict):
        return None, "receipt 字段不符，fail-closed 回退全量"
    expected = _fields_for(str(data.get("version", "")))
    if expected is None or frozenset(data) != expected:
        return None, "receipt 字段不符，fail-closed 回退全量"
    if not _valid_hashes(data.get("seen_item_hashes")):
        return None, "receipt 版本/哈希结构不符，fail-closed 回退全量"
    if data["version"] == RECEIPT_VERSION_V2:
        if not isinstance(data.get("device_id"), str) or not data["device_id"]:
            return None, "receipt 设备标识缺失，fail-closed 回退全量"
        if is_expired(data, now=now):
            return None, "receipt 已过期，fail-closed 回退全量"
    return data, None


def write_receipt(path: str | Path, *, anchor: str, carrier_revision: str,
                  theta: float, hashes: dict[str, str],
                  device_id: str | None = None,
                  ttl_seconds: float | None = None,
                  now: float | None = None) -> None:
    """Write only to a path the Human explicitly supplied (ADR 0010).

    Without device_id / ttl_seconds this emits the S1 v1 format byte-for-byte.
    Passing either one opts into the portable v2 format; both are required.
    """
    v2 = device_id is not None or ttl_seconds is not None
    if v2 and (not isinstance(device_id, str) or not device_id
               or not isinstance(ttl_seconds, (int, float))
               or isinstance(ttl_seconds, bool) or ttl_seconds <= 0):
        raise ValueError("v2 receipt requires a device_id and a positive ttl_seconds")
    payload = {
        "version": RECEIPT_VERSION_V2 if v2 else RECEIPT_VERSION_V1,
        "anchor": anchor,
        "carrier_revision": str(carrier_revision),
        "theta": float(theta),
        "seen_item_hashes": dict(sorted(hashes.items())),
    }
    if v2:
        payload.update({
            "device_id": device_id,
            "generated_at": time.time() if now is None else float(now),
            "ttl_seconds": ttl_seconds,
        })
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n", encoding="utf-8")


def merge_baselines(local: dict | None, remote: dict | None, *,
                    now: float | None = None) -> tuple[dict | None, str | None]:
    """Merge two devices' receipts into one baseline for compute_delta.

    A receipt is a disposable cache, so the only safe merge is a union of
    per-item hashes under identical view context. Any mismatch, expiry,
    version skew or hash conflict fails closed: the caller must render a full
    view rather than trust a partial increment.
    """
    def reject(reason: str) -> tuple[None, str]:
        return None, f"receipt {reason}，fail-closed 回退全量"

    if (not isinstance(local, dict) or not isinstance(remote, dict)
            or frozenset(local) != RECEIPT_FIELDS_V2
            or frozenset(remote) != RECEIPT_FIELDS_V2):
        return reject("不是合法 v2 收据")
    version = local["version"]
    if version != remote["version"] or version not in SUPPORTED_VERSIONS:
        return reject("版本不一致或不支持")
    if is_expired(local, now=now) or is_expired(remote, now=now):
        return reject("已过期")
    if not _valid_hashes(local["seen_item_hashes"]) or not _valid_hashes(
        remote["seen_item_hashes"]
    ):
        return reject("哈希结构不符")
    if local["device_id"] == remote["device_id"]:
        # Same device: re-reading its own receipt is not a cross-device merge.
        return {"seen_item_hashes": dict(local["seen_item_hashes"])}, None
    for key in ("anchor", "carrier_revision", "theta"):
        if local[key] != remote[key]:
            return reject(f"{key} 上下文不一致")
    left, right = local["seen_item_hashes"], remote["seen_item_hashes"]
    if any(left[key] != right[key] for key in set(left) & set(right)):
        return reject("条目 hash 冲突")
    union = dict(right)
    union.update(left)
    return {"seen_item_hashes": dict(sorted(union.items()))}, None


def merge_baseline_chain(local: dict | None, peers: list[dict], *,
                         now: float | None = None
                         ) -> tuple[dict | None, str | None]:
    """Merge one local receipt with any number of peer receipts.

    Every peer must match the *original* view context and be unexpired; a
    single bad peer fails the whole chain closed (no partial increment).
    Returns a baseline for compute_delta, never a writable receipt.
    """
    if not isinstance(local, dict) or frozenset(local) != RECEIPT_FIELDS_V2:
        return None, "receipt 不是合法 v2 收据，fail-closed 回退全量"
    current = dict(local)
    # A synthetic identity keeps the accumulated union distinct from any real
    # peer, so merge_baselines never takes its same-device shortcut.
    current["device_id"] = str(local["device_id"]) + "+chain"
    for peer in peers:
        merged, warning = merge_baselines(current, peer, now=now)
        if warning:
            return None, warning
        current["seen_item_hashes"] = merged["seen_item_hashes"]
    return {"seen_item_hashes": dict(sorted(current["seen_item_hashes"].items()))}, None


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

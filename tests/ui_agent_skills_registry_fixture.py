"""Resettable registry fixture for AdapterBoundary tests (roadmap 1-7-5).

Why this exists
---------------
In AdapterBoundary, ``removal`` is a *transient* operation: after a removal test
an adapter simply disappears from the registry and no ``removed`` state bit is
persisted (adapter-boundary-v1.md §6.1). The 1-7-5 boundary orchestration layer
will mutate a registry to exercise the R1–R5 removal invariants and the
fallback / quarantine transitions. Those mutations must never leak into the
production "main registry".

``ResettableRegistryFixture`` closes that risk:

* It is constructed from an **immutable base snapshot** — a JSON file that
  captures the main registry at a point in time, or an in-memory dict. The
  snapshot is *read-only* by contract: this module never writes it back.
* Every test works against a **deep-copied working registry** so mutations are
  isolated.
* ``reset()`` restores the working registry to the base snapshot *exactly*
  (recursively, not by reference).
* Reads (``get`` / ``all``) return deep copies, so callers cannot accidentally
  mutate the working store through a returned object.
* A context manager (``with fixture.scope():``) auto-resets on exit — even on
  exception — so a failed test cannot leave the next test pre-polluted.

There is deliberately **no production singleton** in this module. The boundary
orchestration layer injects the registry it wants tested; the fixture only ever
touches its own copies.
"""
from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Union

Snapshot = Dict[str, Any]  # registry shape: adapter_id -> manifest dict

VALID_LIFECYCLE = ("active", "degraded", "disabled", "quarantine")


class ResettableRegistryFixture:
    """An isolated, resettable copy of an adapter registry for tests.

    Parameters
    ----------
    base:
        Either a dict in registry shape (``adapter_id -> manifest``) or a path to
        a JSON file containing such a dict. The source is treated as immutable;
        it is deep-copied and never written back.
    """

    def __init__(self, base: Union[Snapshot, str, Path]) -> None:
        if isinstance(base, (str, Path)):
            self._base_path = Path(base)
            raw = json.loads(self._base_path.read_text(encoding="utf-8"))
        else:
            self._base_path = None
            raw = base
        if not isinstance(raw, dict):
            raise TypeError(
                "registry snapshot must be a dict (adapter_id -> manifest), "
                f"got {type(raw).__name__}"
            )
        # The immutable source. Never mutate this object.
        self._base: Snapshot = copy.deepcopy(raw)
        # The mutable working copy tests operate on.
        self._working: Snapshot = copy.deepcopy(self._base)

    # -- snapshot source ---------------------------------------------------
    @property
    def source_path(self) -> "Path | None":
        return self._base_path

    # -- reads (always return copies) -------------------------------------
    def get(self, adapter_id: str) -> "Dict[str, Any] | None":
        """Return a deep copy of one adapter's manifest, or ``None`` if absent."""
        entry = self._working.get(adapter_id)
        return copy.deepcopy(entry) if entry is not None else None

    def all(self) -> Snapshot:
        """Return a deep copy of the whole working registry."""
        return copy.deepcopy(self._working)

    def ids(self) -> list:
        """Return the adapter ids currently in the working registry."""
        return list(self._working.keys())

    def has(self, adapter_id: str) -> bool:
        return adapter_id in self._working

    # -- mutations (working copy only) ------------------------------------
    def set_lifecycle(self, adapter_id: str, state: str) -> None:
        if adapter_id not in self._working:
            raise KeyError(f"no such adapter in registry: {adapter_id}")
        if state not in VALID_LIFECYCLE:
            raise ValueError(
                f"invalid lifecycle {state!r}; expected one of {VALID_LIFECYCLE}"
            )
        self._working[adapter_id]["lifecycle"] = state

    def set_field(self, adapter_id: str, field: str, value: Any) -> None:
        if adapter_id not in self._working:
            raise KeyError(f"no such adapter in registry: {adapter_id}")
        self._working[adapter_id][field] = value

    def add(self, manifest: Dict[str, Any]) -> None:
        adapter_id = manifest.get("id")
        if not adapter_id:
            raise ValueError("manifest must carry an 'id' to be added to the registry")
        self._working[adapter_id] = copy.deepcopy(manifest)

    def remove(self, adapter_id: str) -> Dict[str, Any]:
        """The transient removal operation. Returns the removed manifest, or
        raises ``KeyError`` if it was already absent."""
        if adapter_id not in self._working:
            raise KeyError(f"cannot remove absent adapter: {adapter_id}")
        return self._working.pop(adapter_id)

    # -- reset / isolation ------------------------------------------------
    def reset(self) -> None:
        """Restore the working registry to the base snapshot exactly."""
        self._working = copy.deepcopy(self._base)

    @contextmanager
    def scope(self) -> Iterator["ResettableRegistryFixture"]:
        """Context manager: yields self, then resets on exit (even on error)."""
        try:
            yield self
        finally:
            self.reset()

    # -- provenance guard --------------------------------------------------
    def base_equals(self, other: Snapshot) -> bool:
        """Deep-equality check used by tests to prove the base was untouched."""
        return copy.deepcopy(self._base) == copy.deepcopy(other)

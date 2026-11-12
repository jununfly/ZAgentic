"""C::05 — view-kind to output-shape routing, as an independent literal.

The spec's `view-contracts` are the requirement; this table is a hand-kept
*second source* that the contract test compares against. A Human (or the CLI)
chooses a view-kind explicitly; the renderer is never chosen by an LLM and
never inferred from the data. Each route names the CLI flags that actually
produce that shape, so the table cannot drift into a wish list.
"""
from __future__ import annotations

# id -> (kind, format, CLI flags that emit this view)
VIEW_CONTRACT_ROUTES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "VC::01": ("intermediate-representation", "json", ("--ir", "--json")),
    "VC::02": ("human-readable", "mermaid|html", ("--out", "--mermaid")),
    "VC::03": ("human-readable", "mermaid|dot",
               ("--dependency", "--dependency-mermaid")),
    "VC::04": ("side-loaded", "json|details-block", ("--context",)),
    "VC::05": ("human-readable", "mermaid|html|text",
               ("--theta", "--out", "--mermaid")),
    "VC::06": ("incremental", "text|json", ("--delta", "--receipt")),
    "VC::07": ("human-readable", "mermaid|svg|html",
               ("--mermaid", "--out")),
    "VC::08": ("human-readable", "html|text", ("--out", "--json")),
}

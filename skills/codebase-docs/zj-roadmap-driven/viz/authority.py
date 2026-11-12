"""Shared process-state authority marker for every public view (INV::05)."""

AUTHORITY_ENVELOPE = "zj-roadmap-authority/v1"


def mermaid_header() -> str:
    """Mermaid comment line carrying the same marker as the JSON envelopes."""
    return f"%% {AUTHORITY_ENVELOPE}\n"

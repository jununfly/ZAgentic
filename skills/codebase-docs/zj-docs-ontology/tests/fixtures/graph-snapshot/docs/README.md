# Team docs map

> Context: see [the overview](designs/overview.md) before reading this map.

- [Overview](designs/overview.md) — primary entry; role: primary; authority-id: `graph.overview`; relations: supports: graph.detail, derived-from: designs/detail.md
- [Detail](designs/detail.md) — has inbound edges; role: supporting; authority-id: `graph.detail`
- [Orphan](prds/orphan.md) — declared supporting, no inbound edges; role: supporting
- [Plain page](prds/plain.md) — no role declared, no edges
- `Entity —relatesTo→ Entity` (navigation shorthand, no page)

Derived decomposition context lives in [detail](designs/detail.md) prose only.

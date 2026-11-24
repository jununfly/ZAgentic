# Architecture concept map (B)

<!-- CONCEPT_MAP_START -->
```json
{
  "nodes": [
    {"id": "billing-owner", "kind": "durable-owner", "anchor": "src/billing/engine.rs", "owner": "architecture.subsystem.billing"},
    {"id": "dangling-edge", "kind": "extension-seam", "anchor": "src/hooks/unknown.rs", "owner": null},
    {"id": "loose-policy", "kind": "effect-policy", "anchor": "src/billing/engine.rs", "owner": "architecture.subsystem.billing"}
  ],
  "edges": []
}
```
<!-- CONCEPT_MAP_END -->

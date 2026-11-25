# Architecture concept map (B) — malformed: the fenced block is never closed.

<!-- CONCEPT_MAP_START -->
```json
{
  "nodes": [
    {"id": "broken-owner", "kind": "durable-owner", "anchor": "src/broken.rs", "owner": "architecture.subsystem.broken"}
  ],
  "edges": []
}

## Trailing prose after the open block

Body content the reader must NOT swallow into the JSON region when the block
is left unclosed. There is deliberately no closing ``` fence and no
CONCEPT_MAP_END marker below.

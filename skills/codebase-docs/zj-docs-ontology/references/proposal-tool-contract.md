# Proposal tool contract

`docs_governance.py` is a read-only inventory. `--proposal` emits JSON with the
map decision, categories found by path, root context entries, process material,
evidence-surface paths, and an empty `mutations` list. It never creates,
moves, rewrites, or deletes a target.

`--validate` adds mechanical map-link diagnostics. It reads only the selected
map and root rule files needed for discovery; category inventory uses path
metadata. Architecture page contracts stay with `zj-docs-architecture`.

Run regression coverage with:

```sh
python3 skills/codebase-docs/zj-docs-ontology/tests/test_governance.py
```

The fixtures cover greenfield detection, an existing compatible map, map-link
drift, and an unread process file. The report's `mutations` must remain empty
in every case.

# Global Initiative Roadmap maintenance rules

Read this file before changing `global-initiative-roadmap.json`. That JSON is a cross-repository navigation index with a fixed three-level hierarchy; it is not a `zj-roadmap-driven` execution roadmap.

## Model

The hierarchy is exactly:

```text
Initiative Node
└── Spec Node
    └── Plan Node
```

- An Initiative Node identifies one independently owned Initiative and its repository-relative directory.
- A Spec Node identifies one approved or actively designed PRD/spec owned by that Initiative.
- A Plan Node identifies one executable roadmap-plan JSON owned by that spec.

The file stores navigation only. Status, focus, decisions, notes, dependencies, work items, and completion evidence belong in the referenced roadmap-plan-file. Read that plan with `zj-roadmap-driven` when entering the Initiative.

## Required fields

Every node has stable `id`, literal `type`, human-readable `label`, and POSIX `path` relative to the directory containing `global-initiative-roadmap.json`.

| Node | Required child field | Path target |
|---|---|---|
| `initiative` | `specs` | Initiative repository or owned project directory |
| `spec` | `plans` | Existing file under the Initiative's `docs/prds/` directory |
| `plan` | none | Existing JSON roadmap-plan-file under the Initiative's `docs/plans/` directory |

Use globally unique kebab-case IDs. IDs survive label and path changes; rename an ID only when the represented Initiative, spec, or plan changes identity.

An empty `specs` or `plans` array is a valid transitional state. It means the Initiative is registered but has no indexed spec, or the spec exists but has no executable plan. Do not create placeholder files only to fill an array.

## Maintenance workflow

1. Locate the owning Initiative repository and read its instructions.
2. Create or update the spec in that Initiative's `docs/prds/` directory.
3. Create or update each execution roadmap in that Initiative's `docs/plans/` directory with `zj-roadmap-driven`.
4. Update this index only after the target paths exist.
5. Resolve every path from this file's directory and verify its target type and owning directory.
6. Confirm the hierarchy contains only Initiative, Spec, and Plan Nodes and that every ID is unique.
7. Run JSON parsing and repository `diff --check` before handing off.

When a spec or plan moves, update its owning repository and this path in the same change. When it is retired, remove the Plan Node first; remove an empty Spec Node only when it no longer provides useful navigation. Keep an Initiative Node while its Initiative remains part of the workspace, even when `specs` is empty.

## Compatibility

Do not run `roadmap_cli.py` against `global-initiative-roadmap.json`; its generic `nodes`, status propagation, decisions, focus, and Markdown renderer implement a different model. Run the CLI only against the Plan Node targets.

Do not create a same-name rendered Markdown view. Human and Agent navigation use the JSON directly, while `global-initiative-landscape.md` explains stable cross-Initiative relationships without copying execution state.

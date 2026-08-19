# Command reference

The bundled wrapper takes `--registry-repo` and `--registry-path` before its operation. The URL must match the checkout's `origin` after normalizing an optional `.git` suffix.

## Read and validate

```bash
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH show ID
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH compile
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH validate
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH check-drift --workspace-root /path/to/workspaces
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH closeout-check --workspace-root /path/to/workspaces
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH semantic-diff --against FILE
```

## Register

Pass remaining arguments exactly as accepted by the Registry repository's `registry_admin.py`:

```bash
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH register initiative --id ID --label LABEL --kind product --repository INITIATIVE_URL --owner OWNER
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH register spec --id ID --initiative-id INITIATIVE --label LABEL --kind product-spec --path docs/prds/FILE.md
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH register plan --id ID --initiative-id INITIATIVE --spec-id SPEC --label LABEL --path docs/plans/FILE.json
```

## Remove

Removal is destructive and requires both Human confirmation and the CLI flag:

```bash
python scripts/initiative_registry.py --registry-repo URL --registry-path PATH remove plan --id ID --confirm
```

## Git handoff

`sync`, `create-branch`, and `publish-plan` delegate to `git_workflow.py`. They default to dry-run output; pass `--execute` only after reviewing the target and ensuring the worktree is clean. Publication never force-pushes.

`closeout-check` reads registered Plan JSON files from Initiative checkouts. A completed Plan prints a Human closeout reminder; a blocked Plan prints a Human decision reminder. The command is read-only and does not delete manifests, compact history, or modify source repositories. Use `--format json` for Agent-readable output.

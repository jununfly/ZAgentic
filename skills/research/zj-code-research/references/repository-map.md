# Repository Map implementation

`repository_map.py` creates an immutable, commit-scoped Repository Map bundle.
The bundle is the fact source; Markdown and HTML are generated reading views.

## Scan

Run from the `zj-code-research` skill directory:

```sh
python scripts/repository_map.py scan /path/to/repository /path/to/map-bundle
```

The scanner reads the current working tree at `HEAD` (or `--ref`). A dirty
tree is valid, but the manifest records both the commit and a content
fingerprint. A non-Git directory uses the fingerprint as its source identity.
The requested ref must resolve to the current `HEAD`; the scanner never claims
to have read a ref whose files are not checked out.

The output directory is write-once. It contains a small `manifest.json`,
independently readable `facts/*.json` or `facts/*.jsonl` shards,
`navigation/targets.json`, and generated `views/map.md` / `views/map.html`.
The default exclusions are `.git` and the output bundle when it is inside the
repository. Add another directory with repeated `--exclude` options.

## Bounded views

Read only the requested section and a bounded number of records:

```sh
python scripts/repository_map.py view /path/to/map-bundle \
  --section targets --limit 40 --format markdown
python scripts/repository_map.py view /path/to/map-bundle \
  --section packages --limit 20 --format html --output packages.html
```

`summary`, `targets`, `packages`, `integrations`, `workflows`, and `tree` are
separate views. Use `validate` before handing the bundle to Architecture Study:

```sh
python scripts/repository_map.py validate /path/to/map-bundle
```

Validation checks every manifest-declared shard/view hash, snapshot identity,
summary, and navigation target document. It does not infer architecture or
turn an unobserved capability into an absence claim.

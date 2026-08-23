# Architecture Study implementation

`architecture_study.py` is the depth-pass seam after Repository Map. It reads
the selected source paths, records line-addressable evidence, and emits a
write-once `architecture-study` bundle. It describes the current source; it
does not choose a technical solution.

## Map-bound study

Select a target ID from `navigation/targets.json`:

```sh
python scripts/architecture_study.py study /path/to/repository /path/to/study \
  --map /path/to/map-bundle \
  --target top-level-<target-id> \
  --max-files 120 --max-bytes 2000000
```

The repository must still match the map's commit and working-tree
fingerprint. The study records the map snapshot ID, selected target IDs, and
map manifest hash. It refuses a stale map rather than silently mixing source
versions.

## Direct study

When no map exists, give an explicit relative path. The study records the
conversion as a `decision` and keeps the absence of a map visible:

```sh
python scripts/architecture_study.py study /path/to/repository /path/to/study \
  --target src/feature
```

Every research record uses exactly one kind: `observed`, `inferred`, `unknown`,
or `decision`. Evidence records carry source path, commit or working-tree
fingerprint, SHA-256, and line range. Critical claims must reference evidence
IDs. The bundle includes independent shards for scope, evidence,
relationships, runtime flows, claims, unknowns, risks, diagrams, and follow-up
targets, plus generated Markdown/HTML views.

Validate before handing the study to technical report research:

```sh
python scripts/architecture_study.py validate /path/to/study
python scripts/architecture_study.py view /path/to/study \
  --section unknowns --limit 30
```

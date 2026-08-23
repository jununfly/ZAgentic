---
name: zj-code-research
description: >-
  Research a code repository through two complementary passes: build a
  commit-scoped Repository Map for breadth, then perform an evidence-linked
  Architecture Study for selected modules or flows. Use for repository
  orientation, architecture deep-reads, and codebase comparisons; use
  zj-tech-research-report when the result must select or recommend a technical
  solution.
---

# Code-repository research

Use a breadth-first map to choose a bounded depth-first study. The method
produces research artifacts, not a generic code tour or a final solution
recommendation.

```text
Repository Map
  → navigation targets
  → Architecture Study
  → optional technical solution research report
```

## Repository Map

Bind the scan to a repository ref and commit, or record an explicit working-tree
fingerprint. Record scope, exclusions, skipped/failed paths, measured inventory,
stable node identities, and unknowns. Write an immutable snapshot artifact bundle
with a small `manifest.json`, independently readable fact shards, deterministic
navigation targets, and generated Markdown/HTML views. Treat caches and indexes
as disposable.

Read [the Repository Map reference](references/repository-map.md), then run the
single implementation seam from this skill directory:

```sh
python scripts/repository_map.py scan <repository> <new-map-bundle>
python scripts/repository_map.py validate <map-bundle>
python scripts/repository_map.py view <map-bundle> --section targets --limit 40
```

Use one new output directory per source snapshot. A dirty tree is allowed only
when its commit and working-tree fingerprint are recorded. Keep the first read
bounded with `view`; do not turn the complete tree shard into an unbounded
conversation dump. The map identifies where to study next; it does not claim
architecture, capability absence, or a solution recommendation.

Completion criterion: `validate` passes, the manifest source identity and
exclusions are explicit, and the handoff names bounded navigation targets for
the next Architecture Study.

## Architecture Study

Start from `navigation/targets.json` unless the user supplied an explicit scope;
in the latter case, convert that scope to equivalent targets and record why no
map was used. Bind the study to the map snapshot whenever one exists.

Read [the Architecture Study reference](references/architecture-study.md), then
run the depth-pass seam:

```sh
python scripts/architecture_study.py study <repository> <new-study-bundle> \
  --map <map-bundle> --target <map-target-id> --max-files 120
python scripts/architecture_study.py validate <study-bundle>
python scripts/architecture_study.py view <study-bundle> --section claims --limit 40
```

Without a map, provide an explicit repository-relative `--target`; the bundle
records that direct scope conversion as a `decision`. Keep the depth pass
bounded by target, file count, and bytes. A changed commit or working-tree
fingerprint invalidates the map binding and requires a new study input.

Separate every record as exactly one of:

- `observed` — directly read from the pinned source;
- `inferred` — derived from observed evidence;
- `unknown` — not established by the current evidence;
- `decision` — a research-scope or follow-up choice, not a source fact.

Cover only the selected scope: module relationships, interfaces, runtime and
data flows, persistence, execution and sandbox/security, extension points,
external dependencies, ownership, design choices, risks, unknowns, diagrams,
and follow-up targets. Every critical claim carries an evidence ID, commit,
source path, and line range.

## Quality and handoff

Read [the code-research quality contract](references/code-research-quality.md)
when the output will be used to compare research quality or tune the method.
Run the local mechanical hard gates before semantic evaluation:

```sh
python scripts/code_research_quality.py validate-assets \
  research/evaluation/code-research-quality-v1
python scripts/code_research_quality.py validate-map <map-bundle>
python scripts/code_research_quality.py validate-study <study-bundle> --map <map-bundle>
```

Then evaluate against a controlled case with `evaluate`. `landscape/v1`
evaluates Repository Map coverage and navigability; `deep-read/v1` evaluates
Architecture Study fidelity and evidence-linked interpretation. Keep the
dimensions separate. A failed hard gate or calibration is a failed quality
result, not a low semantic score.

When the study exposes a technical decision, hand its cited findings, ledger,
and decision brief to `zj-tech-research-report`. Do not make the Architecture
Study itself the final option recommendation.

Completion means the selected scope is explicit, the source identity is pinned,
the bundle references are valid, unknowns remain visible, and critical claims
are traceable to evidence.

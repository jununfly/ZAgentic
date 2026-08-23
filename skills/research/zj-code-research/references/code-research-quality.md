# Code-research quality contract

`zj-code-research` owns two independent quality dimensions:

- `landscape/v1` — Repository Map coverage, inventory, deterministic
  navigation, degradation disclosure, and usefulness as a deep-read handoff.
- `deep-read/v1` — Architecture Study target adherence, line-addressable
  evidence, certainty separation, runtime/ownership/risk coverage, and follow-up
  navigation.

The quality result is dimensional. It does not collapse landscape and
deep-read into one score, and it does not turn an unknown into an absent
capability.

## Mechanical hard gate

Run the hard gate before reading semantic scores:

```sh
python scripts/code_research_quality.py validate-assets \
  research/evaluation/code-research-quality-v1
python scripts/code_research_quality.py validate-map <map-bundle>
python scripts/code_research_quality.py validate-study <study-bundle> --map <map-bundle>
```

The gate checks source pinning, explicit scope/exclusions, shard hashes, tree
and inventory consistency, stable target binding, evidence coordinates, record
kinds, unique IDs, critical-claim evidence, unknowns, risks, diagrams, flows,
and follow-up targets.

## Controlled fixtures and calibration

The fixture corpus is separate from technical-report assets:
`research/evaluation/code-research-quality-v1/`. It contains balanced and
sparse landscape cases plus runtime and insufficient-evidence deep-read cases.
The annotations describe required properties, not golden prose.

Calibrate the blinded Judge baseline before using semantic results:

```sh
python scripts/code_research_quality.py calibrate \
  research/evaluation/code-research-quality-v1
python scripts/code_research_quality.py evaluate <bundle> \
  --case <case-id> \
  --assets research/evaluation/code-research-quality-v1 \
  --map <map-bundle>
```

`evaluate` returns the hard-gate result, per-rubric dimensions, and calibration
status. A failed hard gate or failed calibration is not a passing quality
result. The shared `zj-research` runtime remains responsible for compiler and
technical-report evaluation; this local contract avoids changing the
`zj-research-eval-cli/v1` protocol merely to add code-research families.

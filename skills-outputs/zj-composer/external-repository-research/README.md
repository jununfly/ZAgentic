# External repository research fixture v1

This deterministic Composer fixture uses the pinned
`michael-denyer/pstack-claude` commit `3b0bc62e13f507c426997ba472e3430dd3e4ef05`.
It represents a read-only research request; it does not clone, modify, publish,
or execute anything in the external repository.

- `input.json` freezes the repository, questions, evidence requirements,
  permission boundary, Plan id, and catalog snapshot.
- `oracle.json` freezes the expected capability order and scenario checks.
- `plan.md` is the Composer output artifact.
- `validation.json` is the Plan validator output.
- `oracle-result.json` is the scenario oracle output.

Run the fixture oracle from the repository root:

```bash
python skills/productivity/zj-composer/scripts/evaluate_fixture.py \
  skills-outputs/zj-composer/external-repository-research
```

The fixture uses existing commit-pinned evidence as context. It does not make a
live GitHub request during validation.

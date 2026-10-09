# Tool combination design fixture v1

This deterministic Composer fixture asks for a bounded combination of existing
skills that turns a product request into a reviewable brief, design review, and
roadmap handoff. It deliberately retains one unresolved capability gap so the
Composer gap protocol is observable.

- `input.json` freezes the goal, constraints, desired output, permission
  boundary, exact gap line, expected Plan id, and catalog snapshot.
- `oracle.json` freezes the expected capability order and scenario checks.
- `plan.md` is the Composer output artifact.
- `validation.json` is the Plan validator output.
- `oracle-result.json` is the scenario oracle output.

Run the fixture oracle from the repository root:

```bash
python skills/productivity/zj-composer/scripts/evaluate_fixture.py \
  skills-outputs/zj-composer/tool-combination-design
```

The fixture reads local catalog metadata only. It does not start a router,
executor, network publication, or consuming execution chain.

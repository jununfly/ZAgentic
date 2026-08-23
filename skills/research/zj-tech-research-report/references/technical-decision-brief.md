# Technical decision brief

`technical-decision-brief/v1` is the alignment input before options are ranked.
It is separate from the Report IR: the brief captures the decision frame, and
the Report IR records evidence-backed synthesis.

Use this shape:

```json
{
  "schema": "technical-decision-brief/v1",
  "user": {"actor": "...", "job": "..."},
  "baseline": {"workflow": "...", "failureModes": ["..."]},
  "targetOutcome": "...",
  "goals": ["..."],
  "nonGoals": ["..."],
  "constraints": [{"id": "latency", "statement": "..."}],
  "assumptions": ["..."],
  "stage": "experience-version",
  "decisionScope": "...",
  "options": [{"id": "option-a", "name": "..."}]
}
```

`stage` is one of `problem-discovery`, `experience-version`,
`usefulness-validation`, `dogfood`, or `release`. The brief must state what
the current workflow is, what useful change is observable, what is out of
scope, and which options are actually in the decision. Assumptions are not
silently promoted to facts.

The technical publisher validates this brief together with the sealed ledger
and `technical-c4/v1` Report IR before invoking the shared compiler. A failed
gate creates no publication artifact. A successful receipt records the
`technical-research-quality-gate/v1` result separately from this brief.

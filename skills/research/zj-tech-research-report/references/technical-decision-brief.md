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

## KEP-753 steps 7–8 mapped to Report IR lifecycle conditions

`stage` does not stay inside the brief. The publisher maps it onto two
`technical-c4/v1` Report IR fields, mirroring steps 7–8 of the pinned
Kubernetes KEP-753 exemplar (see
[the technical proposal exemplar](technical-proposal-exemplar.md), commit
`fc09a26`):

- **Step 7 — Graduation criteria.** For every stage except
  `problem-discovery`, the Report IR must carry `graduationCriteria` as a
  list of `{condition, threshold}` entries — one observable exit condition
  per entry, with the threshold that makes it checkable (`metric` and
  `promoteTo` extend an entry with its measurement and next lifecycle stage).
  Merged code is not completion; the condition-plus-threshold pair is what
  the gate counts. A non-discovery report with an empty list, or an entry
  missing either field, fails publication.
- **Step 8 — Upgrade, downgrade, and version skew.** `versionSkew` is
  omitted for `problem-discovery`, `experience-version`, and
  `usefulness-validation` — an experience-version report carries no
  mixed-version obligations. It appears only for `dogfood` and `release`
  stages, as `{upgrade, downgrade, versionSkewRisks}` stating how the
  recommended choice behaves during upgrade, downgrade, and version skew
  against adjacent components. A dogfood/release report missing any of the
  three fields fails publication.

The gate that enforces this is
[scripts/validate_technical_report.py](../scripts/validate_technical_report.py):
it reads `stage` from this brief and applies the two stage conditions above.
The publication receipt echoes the outcome as
`counts.graduationCriteria` (entry count) and `counts.versionSkew` (`false`
when omitted), so each published report carries auditable evidence of which
lifecycle conditions were satisfied.

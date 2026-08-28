# Technical proposal exemplar: Kubernetes KEP-753

Primary source: [KEP-753: Sidecar containers](https://github.com/kubernetes/enhancements/blob/fc09a26d4236305d3f282377ca92bdfb2b1fb03c/keps/sig-node/753-sidecar-containers/README.md), pinned to commit `fc09a26d4236305d3f282377ca92bdfb2b1fb03c`.

## Why this is a useful exemplar

KEP-753 is not only a description of an implementation. It connects a user-visible problem to a bounded proposal, rejected alternatives, operational risks, tests, release gates, and rollback. Its table of contents makes the decision surface inspectable before reading the details.

At the pinned commit the KEP carries eleven top-level sections: Release Signoff Checklist, Summary, Motivation, Proposal, Design Details, Production Readiness Review Questionnaire, Implementation History, Drawbacks, Future use of `restartPolicy` field, Alternatives, and Infrastructure Needed (Optional). Test Plan, Graduation Criteria, and Upgrade/Downgrade/Version Skew Strategy sit inside those sections as subsections.

The sequence below is this skill's decision chain distilled from that structure. It is not a one-to-one copy of the KEP's headings; it exists so a report can be checked step by step without importing Kubernetes' production scale.

1. **Summary and motivation** — state the user problem and why existing primitives are insufficient.
2. **Goals and non-goals** — prevent a local fix from silently becoming a general platform.
3. **Proposal** — describe the intended behavior before committing to implementation details.
4. **Risks and mitigations** — enumerate failure scenarios and the mechanism or policy that contains each one.
5. **Design details** — cover compatibility, resource effects, lifecycle behavior, and dependent components.
6. **Test plan** — map unit, integration, end-to-end, resource, upgrade, downgrade, and failure tests to the proposal.
7. **Graduation criteria** — define what must be true for alpha, beta, and GA; do not treat code merged as completion.
8. **Upgrade, downgrade, and version skew** — state how the design behaves during mixed-version operation.
9. **Production readiness** — cover enablement, rollback, rollout, monitoring, dependencies, scalability, and troubleshooting when the lifecycle requires it.
10. **Drawbacks and alternatives** — explain why plausible alternatives were not selected, including the constraint that rejected each one.
11. **Implementation history and infrastructure** — preserve what was learned and what operational support the design requires.

## Executable check items for the eleven steps

Run these before publication. A failing item is a missing decision, not a style defect. Steps 7 and 8 also have a mechanical contract in the Report IR; that contract lives in [the technical decision brief](technical-decision-brief.md) and is the authority whenever the two disagree.

| # | Step | Pass condition | Fails when |
|---|---|---|---|
| 1 | Summary and motivation | The report names the actor, the job, and a baseline failure mode, and says why existing primitives cannot absorb it. | Motivation is a feature description with no failing workflow, or the baseline is asserted without a cited source. |
| 2 | Goals and non-goals | `goals` and `nonGoals` are both non-empty, and each non-goal names a capability a reader would otherwise assume is included. | Non-goals restate goals, or the only boundary is the phrase "out of scope". |
| 3 | Proposal | Intended behavior is described as an observable state change before any API, format, or component is named. | The first concrete statement is an interface, or the proposal is only a component list. |
| 4 | Risks and mitigations | Each risk carries trigger, impact, mitigation, residual risk, and owner. | A risk has no owner, or the mitigation restates the risk. |
| 5 | Design details | Compatibility, resource or state effects, lifecycle behavior, and dependent components are each covered or deferred with a stated reason. | Backward compatibility is never mentioned. |
| 6 | Test plan | Every important claim maps to a reproducible scenario with an expected observation and a threshold. | Only the happy path is tested, or no claim-to-scenario mapping exists. |
| 7 | Graduation criteria | Beyond `problem-discovery`, `graduationCriteria` is a list of `{condition, threshold}` entries; `metric` and `promoteTo` extend an entry. | Merged code is treated as completion, or an entry lacks either required field. |
| 8 | Upgrade, downgrade, version skew | A `dogfood` or `release` report carries `versionSkew` with `upgrade`, `downgrade`, and `versionSkewRisks`; the three earlier stages omit it by convention. | A dogfood/release recommendation has no stated downgrade path. |
| 9 | Production readiness | For `dogfood` and `release`, enablement, rollback, rollout, monitoring, dependencies, scalability, and troubleshooting are each covered. | An early-stage report imports these without evidence, or a release report omits one. |
| 10 | Drawbacks and alternatives | Every serious alternative states the constraint that rejected it. | Alternatives are strawmen, or a rejection gives no constraint. |
| 11 | Implementation history and infrastructure | What was learned and what operational support the design requires are recorded; a section with nothing in it is recorded as empty. | A known gap is omitted instead of recorded. |

Two of these are visible in the exemplar itself: KEP-753 ships an empty Drawbacks section and an empty Infrastructure Needed section at the pinned commit. The KEP still lists both headings. An empty section that keeps its heading is a stronger statement than a missing one, because a reader can see the gap was considered.

## What to transfer to a research report

Do not copy KEP-753's production depth into every early-stage report. Scale the sequence to the product lifecycle. The rows below give the minimum evidence per stage; `promotes when` is the exit condition and `fails when` is the smallest defect that blocks the stage.

| Stage value | Minimum evidence | Promotes when | Fails when |
|---|---|---|---|
| `problem-discovery` | User, current workflow, baseline with failure modes, falsifiable hypothesis, goals, non-goals, alternatives, and the evidence that ends discovery. | The hypothesis survives contact with the baseline and one option is cheap enough to build as a slice. | No baseline failure mode is named, or only one option was ever considered. |
| `experience-version` | One vertical slice, minimum product contract, failure categories, test fixtures, success thresholds, and a discardable implementation boundary. | The slice meets its thresholds on the agreed fixtures. | The slice has no discard boundary, or thresholds were set after the results were seen. |
| `usefulness-validation` | Baseline comparison, repeated experiments, value metrics, failure frequency, and the continue/revise/stop decision. | The margin over the baseline repeats across runs. | A single run is presented as validation, or no stop condition exists. |
| `dogfood`, `release` | Rollout, rollback, monitoring, upgrade compatibility, support, and data handling. | Rollback has been exercised and the monitoring signals are within the stated thresholds. | Rollback is designed but never executed, or no one owns support. |

## Invariants

The invariant is the decision chain, not the document length:

```text
user problem → target outcome → constraints → options
→ evidence → semantic fit → ownership/risk
→ validation/exit criteria → recommendation
```

When a report compares open-source projects, treat each candidate as an option, not as a conclusion. Distinguish `native`, `adapted`, `absent`, and `unknown`; an unobserved capability is not proof of absence. Keep product semantics, reusable unit capabilities, and inherited ownership responsibilities in separate columns.

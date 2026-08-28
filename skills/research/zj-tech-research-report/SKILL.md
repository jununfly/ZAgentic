---
name: zj-tech-research-report
description: Produce evidence-backed technical-solution research reports from cited findings and sealed ledgers, covering decision framing, alternatives, capability fit, ownership risks, validation gates, and recommendations. Use after zj-research for technical architecture decisions, technology comparisons, open-source selection, and prototype planning; do not use it as a generic domain-report skill.
---

# Technical solution research report

Produce a decision instrument, not a catalog of project descriptions. The invariant is:

```text
user problem → target outcome → constraints → options
→ evidence → semantic fit → ownership/risk
→ validation/exit criteria → recommendation
```

Read [the technical decision brief](references/technical-decision-brief.md) before ranking options, and read [the technical proposal exemplar](references/technical-proposal-exemplar.md) before a solution-design or multi-repository comparison. The brief fixes the decision frame; the exemplar distills the decision structure of Kubernetes KEP-753 without importing its production-scale depth into early-stage work.

## 1. Route the task and scale the depth

Classify the request before collecting evidence:

- **Problem discovery** — establish user, current workflow, baseline, falsifiable hypothesis, goals, non-goals, and evidence needed to exit discovery.
- **Experience Version / prototype** — define one vertical slice, minimum product contract, failure categories, test fixtures, success thresholds, and a discardable implementation boundary.
- **Usefulness validation** — compare against the current alternative with repeated experiments, value metrics, failure frequency, and continue/revise/stop criteria.
- **Dogfood or release** — add rollout, rollback, monitoring, upgrade compatibility, support, and data handling in proportion to the promised scope.

Do not pull later-stage production readiness into an early report unless current evidence requires it. Do not omit lifecycle, validation, or rollback when the recommendation makes a durable operational commitment.

For technical comparisons, architecture proposals, and open-source selection,
use `family: "technical-c4/v1"`. This family renders the Key-Value index, C4
landscape, candidate table, deep-read cards, comparison analysis, metric matrix,
and recommendation path. The low-level publisher retains `zj-draft/v1` only for
the existing shared-compiler compatibility contract; do not use that family
for a new `/zj-tech-research-report` run or as a generic domain-report path.

## 2. Establish the decision frame before reading options

Write these facts into a `technical-decision-brief/v1` before ranking candidates:

1. **User and job** — who is trying to do what, in which workflow?
2. **Current baseline** — what happens today, including Human actions, cost, latency, and failure modes?
3. **Target outcome** — what observable behavior would make the change useful?
4. **Goals and non-goals** — what this decision must solve and what it deliberately does not solve.
5. **Constraints and assumptions** — data, devices, runtime, license, security, team capacity, lifecycle stage, and exit conditions.
6. **Decision scope** — whole product, architecture, integration, or one reusable unit capability.

If the user has not supplied these, state assumptions and mark them as alignment items; do not hide them inside a recommendation.

Validate the brief against the sealed ledger and Report IR before publication. A
technical report is not ready to compile when the decision frame, evidence
links, candidate scores, critical claims, diagrams, comparisons, metrics, or
unknown follow-ups are incomplete.

## 3. Build the evidence chain

Require a cited findings file. For a technical multi-repository run, also
require the sealed ledger produced by `zj-research`. Read the shared runtime
reference at `../zj-research/references/research-cli.md` when the sibling skill
is present; an independently installed report skill uses
`ZJ_RESEARCH_RUNTIME=<path-to-zj-research>`. The publisher resolves the
canonical adapter through that runtime pointer and stops with its setup
instruction when the runtime is unavailable or incompatible.

Trace every non-trivial conclusion through:

```text
Evidence → Claim → Comparison/implication → Recommendation or test
```

Keep these labels separate:

- `native` — the source proves the candidate provides the capability;
- `adapted` — the capability is possible only through a specified adapter;
- `absent` — a primary source explicitly says it is not provided or is retired;
- `unknown` — this run lacks enough evidence; never convert it into absent.

Separate popularity, topic relevance, product fit, semantic match, composition feasibility, evidence strength, and ownership cost. Never use Stars, README length, or feature count as a capability score.

## 4. Required technical analysis

For a technical report, cover the following in the Report IR. Encode each as a `concept`, `card`, `claim`, `comparison`, `recommendation`, or `metric` so the compiler can render and trace it.

### Problem and product fit

- current user workflow and baseline;
- target vertical slice and success condition;
- goals, non-goals, assumptions, and constraints;
- product semantics that must remain owned by the target base.

### Option and alternative analysis

For every serious option, state:

- what problem it solves and at which layer;
- capability coverage by requirement;
- semantic mismatches and hidden assumptions;
- integration seams and data/state translation;
- operational, security, upgrade, and exit responsibilities;
- why it is preferred, tied, deferred, or rejected.

Every alternative comparison must follow `constraint → option → evidence → tradeoff → decision`. Include plausible alternatives, not strawmen, and state the constraint that rejects each one.

### Architecture and unit-capability composition

Distinguish whole-product adoption from unit-capability reuse. Keep a matrix for product semantics, state/context, identity/scope, execution/sandbox, transport/API, observability, deployment, and lifecycle ownership. Mark each cell `native / adapted / absent / unknown` and identify the owner after integration.

### Risk and validation

Encode the risk register as the top-level `riskRegister` field — see section 5 for the contract the quality gate enforces; a risk described only in prose does not satisfy it. Include a validation plan mapping each important claim to a reproducible scenario, expected observation, threshold, and lifecycle exit decision. Include upgrade/rollback/version-skew tests only when the proposed scope creates those obligations.

For systems executing model-generated code, always include a security/sandbox theme: credentials, approvals, dangerous operations, isolation, provenance, and recovery.

## 5. Technical Report IR requirements

Construct complete `zj-research-report-ir/v1` with `family: "technical-c4/v1"` for technical runs:

- `concepts`: include the decision frame, fit model, ownership model, and lifecycle stage;
- `diagrams`: include at least one landscape and one container/topic diagram showing user, system boundary, options, and chosen seams;
- `candidates`: copy `stars` and `topicMatch` exactly from the sealed ledger and attach only sealed Evidence IDs;
- `cards`: one deep-read card per serious option with role, strongest capability, main gap, and evidence strength;
- `claims`: cite every non-trivial finding and critical claim;
- `comparisons`: include role families, alternatives, capability composition, ownership/risk, and evidence gaps;
- `recommendations`: include overall choice, constraint→choice table in prose, phased landing path, paths to avoid, and remaining risks;
- `metrics`: define measurable fit, health, validation, and ownership indicators with unit,  method, condition, and expected value.
- `riskRegister`: a non-empty list of the risks that survive the recommendation, each encoded as `{risk, trigger, impact, mitigation, residualRisk, owner}` with all six fields required and non-empty. This is KEP-753 step 4 (Risks and mitigations). A mitigation that merely restates the risk is rejected — it must name the mechanism or policy that contains it. `owner` must name the role or party that carries the residual risk, not "TBD"; placeholders (`TBD`, `N/A`, `unknown`, `待定`, and similar) are rejected in **all six** fields, because a non-empty string that names nothing is not content. Prose risk discussion inside `recommendations` is not sufficient on its own; the structured list is the contract the quality gate enforces.
- `graduationCriteria`: for any stage beyond `problem-discovery`, list the observable exit conditions that promote the recommended option to the next lifecycle stage (`experience-version` → `usefulness-validation` → `dogfood` → `release`). Encode each as `{condition, threshold}` — the two fields the machine-checked gate requires — and extend an entry with `metric` (how the condition is measured) and `promoteTo` (the next lifecycle stage) when they are meaningful. `promoteTo` has nothing left to name at the last stage in the chain, so an entry that names no successor is not incomplete; the list itself must be non-empty. This is KEP-753 step 7 (Graduation criteria), kept separate from the validation plan so the promotion chain is explicit and machine-checkable.
- `versionSkew`: for `dogfood` and `release` stages, state how the recommended choice is upgraded, downgraded, and how version skew between it and adjacent components is handled — `{upgrade, downgrade, versionSkewRisks}` — this is KEP-753 step 8 (Upgrade/downgrade and version skew). Omit only when the scope never reaches those stages.

For `technical-c4/v1`, record information-gap status in a non-empty structured top-level `informationGaps` field — `{"status": "has-gaps" | "no-gaps", "rationale": "<explicit gap/no-gap statement>"}` — with both fields required, cross-checked against the sealed ledger's `unknownCriteria`. The `informationGaps.status` must be `no-gaps` exactly when the ledger lists no unknown criteria, and `has-gaps` otherwise; do not treat `unknownCriteria: []` as "no information gaps." Free-text gap mentions inside `recommendations` are not sufficient on their own — the structured field is the contract the quality gate enforces.

## 6. Compile and publish

Run:

```sh
python scripts/publish_report.py \
  <report-ir.json> <ledger-response.json> \
  research/<topic>/<YYYY-MM-DD>-draft.md \
  --receipt research/<topic>/<YYYY-MM-DD>-receipt.json \
  --brief <technical-decision-brief.json>
```

For `technical-c4/v1`, the helper runs the technical research quality gate
before invoking the shared compiler. It then compiles authoritative Markdown,
derives HTML from that exact Markdown, creates all files without overwrite,
evaluates application-owned publication facts, and fails when either gate is
unhealthy. The receipt records both the compiler evaluation and the
`technical-research-quality-gate/v1` result. Never hand-author or edit a
competing Markdown or HTML version. Verify JSON, evidence IDs, ledger
fingerprint, candidate scores, trailing whitespace, and the receipt before
reporting completion.

If the task is non-technical or needs a domain-specific cleaning and analysis
method, hand the cited findings to the owning domain skill instead of widening
this technical report skill.

## 7. Anti-patterns

- starting with a candidate ranking before defining the user's job and baseline;
- listing features without semantic fit, ownership, alternatives, or rejection reasons;
- treating unobserved behavior as absent;
- recommending a whole platform when only one unit capability is needed;
- copying production readiness, HA, RBAC, or dashboard design into an Experience Version without evidence;
- hiding assumptions or unresolved choices inside prose;
- claiming “healthy” from a report that has not passed the compiler receipt.

## 8. Self-evaluation

Before completion, record:

| Criterion | Pass condition |
|---|---|
| Citation accuracy — hard gate | Every finding and synthesis claim is re-verifiable; every citation appears in the source list. |
| Decision usefulness | The report makes user value, option tradeoffs, ownership, and next validation step clearer than a source skim. |
| Lifecycle proportionality | The report includes the depth required by the current stage and explicitly defers later-stage work. |
| Incremental editability | The user can revise assumptions, alternatives, thresholds, and recommendation without rewriting the report. |

Completion criterion: the evidence/citation gate passes; the technical IR uses the correct family; Markdown, HTML, and receipt paths are reported; and the receipt records `healthy: true` with the compiler-returned report hash.

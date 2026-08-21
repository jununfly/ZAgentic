---
name: zj-tech-design-review
description: Guide an evidence-backed technical design review from problem framing through architecture, metrics, risk, rollout, testing, and follow-up. Use when the user asks for a design doc, technical proposal, architecture review, launch review, or a structured critique of a proposed change.
---

# Technical design review

Produce a reviewable decision document, not an implementation plan disguised as prose. Keep the chain visible:

```text
user problem → target outcome → constraints → design options
→ evidence → risks/ownership → validation → rollout decision
```

## Workflow

1. **Frame the decision.** Record the user/job, current baseline, target outcome, goals, non-goals, assumptions, constraints, affected code or systems, and decision owner. If facts are missing, label them as questions or assumptions.
2. **Write the one-page overview.** Include a 1–3 sentence summary, platforms/environments, team/contact, tracking item, and broad code or data surfaces. A reader should know what is changing and why without reading the rest.
3. **Describe the design.** Explain motivation, alternatives considered, major modules and seams, data/control flow across processes, threads, storage, and network, compatibility, and ownership after launch. Prefer diagrams or short flows when they remove ambiguity.
4. **Review the principles.** Address performance (speed, memory, power), user and operational simplicity, security/threat model, privacy/data handling, accessibility where relevant, and lifecycle cost. Explicitly say “no material impact” with a reason when a section does not apply.
5. **Define evidence and gates.** For each important claim, name the source or experiment, expected observation, threshold, owner, and decision it unlocks. Separate observed, inferred, and unknown. Unknown is not absent.
6. **Plan rollout and recovery.** State waterfall, staged rollout, experiment, feature flag, or other strategy; monitoring and regression metrics; pause/rollback conditions; migration and version-skew handling; and cleanup or follow-up work.
7. **Run the review.** Ask reviewers to challenge the problem, alternatives, ownership, failure modes, security/privacy, metrics, and exit criteria. Resolve each objection in the document or record it as an explicit open decision.

## Required document shape

Use the headings and prompts in [REVIEW-TEMPLATE.md](REVIEW-TEMPLATE.md). Keep the overview concise; put detailed rationale and evidence behind it. For an existing design, preserve the author's intent while marking unsupported claims and stale assumptions.

## Review standards

- Every recommendation names the constraint and trade-off that led to it.
- Alternatives are plausible and rejected for stated reasons; do not use strawmen.
- Product semantics, identity/scope, state, execution/sandbox, observability, deployment, and lifecycle ownership have named owners.
- Designs that execute untrusted or model-generated code include credentials, approvals, isolation, dangerous operations, provenance, and recovery.
- Metrics include unit, collection method, baseline, target or threshold, and regression signal.
- Testing covers normal paths, failure paths, platform conditions, migration/version skew, and rollback when those obligations exist.
- Open questions have an owner and a next action; do not silently turn uncertainty into confidence.

## Deterministic quality gate

Run `python scripts/validate_review.py <review.md>` to check the mechanical contract. The validator requires the template sections, goals/non-goals, alternatives, named owners, metric baseline/unit/method and target or threshold, a reproducible scenario, rollout/rollback, blocking and non-blocking labels, a decision state, and an evidence pointer. It also rejects unknown-as-absent language, unsupported `approve`, and unmarked Chromium-specific guidance. It does not judge prose quality; use the three valid and three invalid fixtures under `tests/fixtures/` as regression examples, then apply the human short-read gate.

## Output

Return the draft plus a short review summary: decisions made, blocking gaps, assumptions needing confirmation, and the next validation step. Do not implement code unless the user separately asks for implementation.

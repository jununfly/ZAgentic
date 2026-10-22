# Graduation Gate Decision — ui-agent-skills paired-run cohort (R2+R3+R4)

- **Decision authority**: zj (Human sign-off; run owner does not self-adjudicate — ev-metrics sub-06 P4)
- **Date**: 2026-10-22
- **Status**: `CONDITIONAL_ADOPTION` (pilot + enforced verification gates)
- **Cohort**: R2+R3+R4 (R1 excluded per DEV-4: mid-run instruction change)
- **Config hash**: `404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce` (budget guardrail 80, per DEV-5)
- **Evidence packet**: `SYNTHESIS-R2R3R4.md`, `CROSS-RUN-TABLE-R2R3R4.json`, `R4/*`, `RENDER-LAYER-COHORT.md`, `_tools/render-layer-report.json`, `_tools/render_layer_check.mjs`

## Decision

**Accept conditional adoption of `skills-path` (the `zj-ui-*` S1→S9 chain) into pilot/observational status**, conditional on the four mechanical verification gates below being enforced in `zj-ui-verify` before any skills-path output is accepted as PASS.

This supersedes the controller's earlier `NOT_GRADUATED_as_quality_win` recommendation. The render-layer evidence (BLK-3, full cohort, real Chromium 155) revised the picture from "pure parity" to "consistent narrow a11y edge at persistent cost premium", which changes the optimal action from rejection to floor-raising.

## Evidence basis

### Contract layer (AI-operator, escaped-defect view)
| metric | skills-path | direct-prompt | Δ |
|---|---|---|---|
| weighted defects (mean) | 8.0 | 13.33 | −40% |
| high defects (mean) | 1.67 | 3.67 | −54.5% |
| critical (mean) | 0.0 | 0.33 | −100% |
| rework_fail (mean) | 1.33 | 0.33 | +303% |
| wallclock min (mean) | 17.57 | 3.84 | +357% |
| tool_calls (mean) | 47.33 | 32.0 | +48% |

Direction consistency: skills better in 2/3 runs on weighted/high/critical, tied 1/3, never worse. Cost: skills worse on all 3 cost axes in 3/3 runs.

### Render layer (BLK-3, real Chromium 155, 6 lanes × 7 assertions A1–A7)
- A1 boot / A2 DOM / A5 keyboard-approve / A6 failure≠success / A7 timeout≠fake-success: **18/18 pass (full parity)**.
- Only differentiator: **A3/A4 `aria-describedby` linkage** — direct 0/3 fail, skills 2/3 pass (R3-h8 missed), direction `skills ≥ direct` in 3/3 runs (2 wins, 1 tie).
- Conclusion: skills-path has a consistent but single-dimensional a11y edge; it is itself only 2/3 reliable on that dimension.

### Interpretation
The quality advantage is (a) narrow (one a11y dimension), (b) not robust (skills missed it once), and (c) bought at a persistent, large cost premium. The correct lever is therefore **not** to reject skills-path, nor to adopt it blindly, but to **raise the verification floor** so both lanes are held to the same hard standard — which closes the observed gap at the verification layer and reduces the adoption decision to a pure cost trade-off.

## Conditions of adoption

1. **Four mechanical gates enforced in `zj-ui-verify`** (see `GRADUATION-GATES` below) before any skills-path output is accepted as PASS. Sign-off on this decision is contingent on gate G-V1..G-V4 landing.
2. **Pilot status**: skills-path remains observational. Track two pilot metrics per run: cost premium (rework / wallclock / calls) and a11y-gate pass rate. No promotion to default/production path until pilot metrics stabilize.
3. **Known limitations recorded (non-blocking)**: BLK-2 (token metering — cost measured via audited steps/wallclock, not true token count); blindness not proven (probe hit 4/6, double-blind not claimable). These are noted as open, not as blockers to the conditional adoption.
4. **Re-evaluation trigger**: if, after gates are enforced, pilot shows skills-path a11y-gate pass rate ≤ direct (i.e., gates do not close the gap), escalate to a fresh gate review.

## GRADUATION-GATES (to be wired into zj-ui-verify)

- **G-V1 state-transition UI reachability** — every legal transition in the contract state machine must have a UI-reachable entry/control. State reachable in the machine but with no UI control = verification failure. (cohort §6 blind spot #1)
- **G-V2 no fake success / no silent data loss** — any `error`/`failed` terminal state must not be rendered or reported as `success`; persistence/submit failure must surface an explicit error, never a silent empty success. (cohort §6 blind spot #2)
- **G-V3 illegal-transition return checked** — the return value of an illegal/undefined transition must not be silently discarded; it must be explicitly validated and rejected. (cohort §6 blind spot #3)
- **G-V4 required-input aria-describedby linkage** — every required input, on validation failure, must associate its error region via `aria-describedby`; missing linkage = verification failure (a11y). (render-layer A3/A4: direct 0/3, skills 2/3 missing)

## Sign-off

- **Decision**: CONDITIONAL_ADOPTION (pilot + gates)
- **Signed by**: zj — 2026-10-22 (this record; run owner did not self-adjudicate per ev-metrics sub-06 P4)
- **Next**: wire G-V1..G-V4 into `zj-ui-verify`; begin pilot tracking; leave roadmap node 1-9-4 `completed`, node 1-9 remains open pending 1-9-5 (persistence/replay gate write-back G-19..G-25).

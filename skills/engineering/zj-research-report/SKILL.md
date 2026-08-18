---
name: zj-research-report
description: Compose a draft research report from cited findings, adding analysis, tradeoffs, gaps, and a recommendation for selection topics. Use after zj-research, especially for technical comparisons and execution-capable agent systems.
---

# Research report

Require a cited findings file. For a technical multi-repository run, also require the sealed ledger produced by `zj-research`; use its sibling `scripts/research_cli.py` adapter and read `../zj-research/references/research-cli.md`. A missing or incompatible compiler stops the run with the adapter's setup instruction.

Build these sections top-down:

1. **Executive summary** — 3–5 conclusion-first bullets; every point is substantiated later.
2. **Key findings** — group by theme, cite every non-trivial claim, and add a security/sandbox theme for systems that execute model-generated code.
3. **Analysis & synthesis** — state meaning, tradeoffs, silent assumptions, and risks that a source skim would miss.
4. **Recommendation** — only for selection intent; give the overall judgment, constraint→choice decision table, phased landing path, paths to avoid, and remaining risks. State a tie when evidence does not decide.
5. **Information gaps & next steps** — table with gap, nature (`fog`, `unverified`, or `absent`), and a concrete next action.
6. **Source list** — every cited primary source and its re-verifiable location.

For technical runs, construct complete `zj-research-report-ir/v1` with `family: "zj-draft/v1"`. Copy candidate stars and topic match from the sealed ledger and preserve Evidence → Claim → Comparison → Recommendation references. Run `python scripts/publish_report.py <report-ir.json> <ledger-response.json> research/<topic>/<YYYY-MM-DD>-draft.md --receipt research/<topic>/<YYYY-MM-DD>-receipt.json`. The helper compiles authoritative Markdown, derives HTML from that exact Markdown, creates both files without overwrite, evaluates application-owned publication facts, and fails when health is false. Never author or edit a competing Markdown or HTML version.

For non-technical findings without a sealed ledger, write the same six-section draft directly and retain `zj-research` citations.

Append this self-evaluation:

| Criterion | Pass condition |
|---|---|
| Citations accurate — hard gate | Every finding and synthesis claim is re-verifiable; every citation appears in the source list. |
| Synthesis saves time | Analysis adds grounded implications rather than paraphrasing findings. |
| Incrementally editable | The user can revise the draft instead of rewriting it; selection and sandbox branches appear when triggered. |

Completion criterion: the citation gate passes; the Markdown, HTML, and receipt paths are reported; and the receipt records `healthy: true` with the compiler-returned report hash.

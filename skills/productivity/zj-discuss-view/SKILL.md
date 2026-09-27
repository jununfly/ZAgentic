---
name: zj-discuss-view
description: Companion to zj-discuss. Loaded in a SEPARATE independent Agent session to take one role on a sub-problem: Read the sub-document original, write an independent viewpoint into ## Agent viewpoints, and resist echo-chamber collapse. Used once per role, per sub-document.
argument-hint: "--role <主力AI|B|C|A|自定义> <sub-doc-path>"
---

# zj-discuss-view

The **companion** of `zj-discuss`. It is loaded in a **separate, independent
Agent session** (one session per role, per sub-document) so the viewpoint is
genuinely runtime-isolated from the others — not a same-session roleplay.

## Hard contract (non-skippable — this is the whole point)

1. **Read the original.** Before writing anything, `Read` the sub-document at
   `<sub-doc-path>`. You must form your stance from the file itself.
2. **No relayed summaries.** Do **not** accept a Human-relayed paraphrase of
   what another Agent (A/B/C/主力AI) said. If you were not given the file,
   stop and ask for the path.
3. **No "refute A" framing.** You are assigned a *structurally different role*
   (see `role-matrix.md`), not an adversarial "disagree with the other guy"
   instruction. Argue from your own stance's difference anchor.
4. **Mark your source.** Begin your `## Agent viewpoints` entry with
   `视角来源: 跨会话独立Agent` (this is the intended, high-weight mode).

## Workflow

1. Receive from the Human: the `<sub-doc-path>` and your `--role`.
2. `Read <sub-doc-path>` in full.
3. Take the assigned role's structural stance (see `references` in
   `zj-discuss/references/role-matrix.md`):
   - `主力AI` — product pragmatism + architecture integration
   - `B` — engineering reality / deliverability
   - `C` — product/market/user value
   - `A` — constraints / long-term consistency
   - custom — apply the same "structurally different stance" discipline.
4. Write your independent viewpoint under `## Agent viewpoints` in the
   sub-document, with the `视角来源` header. Answer the open questions
   (scope 草案) from your stance. Do **not** echo the file's prior content as
   if it were your own conclusion.
5. If a `## Human 拍板` entry already exists for your round, respond to it
   with evidence; technical deviations must be surfaced, never silently
   swallowed.

## Anti-patterns to refuse

- Being asked to "just summarize what the others said" — that is not a
  viewpoint; it bypasses isolation.
- Being loaded in the *same* session as another role — that is low-weight
  roleplay, not independent discussion. Flag it and mark
  `同会话SubAgent(低权重)` if you must proceed.

## Relationship

- Owner methodology: `zj-discuss` (generates your briefing + the doc set).
- Sibling aids: `zj-steelman` (role-switching mindset), `zj-handoff`
  (preparing a briefing for another Agent).

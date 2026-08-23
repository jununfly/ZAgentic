# Dual-mode carrier and skill-pair relationship

Read this reference when choosing the roadmap carrier or handing work from `zj-wayfinder` to `zj-roadmap-driven`.

## Dual-mode carrier

`zj-roadmap-driven` is the natural **local/self-contained carrier** in the pair:
ordinary roadmaps use one local JSON source of truth, while large roadmaps use
an explicit sharded bundle with a small manifest and bounded views. It also
consumes the route planned by wayfinder's **tracker mode**. `zj-roadmap-driven`
does not plan on the tracker; it consumes wayfinder's decision map through
`zj-to-tickets`, which exports decision tickets with blocking edges (local
`.scratch/.../issues/<NN>.md` files or tracker issues), then materializes the
route in the selected local storage mode.

Both uses share one mental model — map/route plus decision records — while the physical carrier differs:

- **Local/self-contained:** when one person has full control or works offline, use single-file JSON for ordinary routes; explicitly choose a bundle when node/decision/history artifacts are large, then render the bounded Markdown view.
- **Tracker planning → roadmap tracking:** when collaborating or running multiple agents, plan in wayfinder's tracker mode, export decision tickets with `zj-to-tickets`, then consume that route here.

Switching guide: collaboration or multiple agents → tracker (wayfinder) + export (`zj-to-tickets`); personal exploration, offline work, or full control → local carrier (wayfinder local mode + this skill). The mental model stays the same, so switching carriers does not redo decisions.

## Combining with `zj-wayfinder`

`zj-roadmap-driven` and `zj-wayfinder` are a designed **skill pair**: plan first, track second. wayfinder plans on either carrier; this skill tracks through local JSON and consumes tracker-planned routes. `zj-to-tickets` is the seam that converts wayfinder's decision map into blocking-edge tickets and then into roadmap JSON.

- **wayfinder plans, roadmap-driven tracks.** When a loose idea is too large for one session, run `/zj-wayfinder` (tracker or local), settle its decision tickets, export them with `zj-to-tickets`, and follow the resulting roadmap here by recording decisions, updating status, and rendering progress.
- **The seam is the converter.** wayfinder's route becomes roadmap input (nodes plus decisions) through `zj-to-tickets`; shared vocabulary, ADRs, and conventions cross the seam without a rewrite.
- **Choose by phase and carrier.** A clear, sized route can use this skill directly. Foggy scope or a large blast radius calls for wayfinder first. Team work uses tracker planning; personal/offline work uses the local carrier. The two layers remain separate and switchable.
- **Human owns destination and decisions; Agent owns planning, parsing, and tracking.** During planning the Human sees wayfinder's map; during execution the Human sees roadmap-driven progress.

The design is documented in `ZAgentic/docs/designs/zj-wayfinder-roadmap-dual-mode.md`.

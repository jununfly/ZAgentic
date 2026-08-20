---
name: zj-wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets, and resolve them one at a time until the way to the destination is clear. Dual-mode: a tracker-dependent carrier (teamwork, multi-agent) or a self-contained local-markdown carrier (context-complete, offline). Designed as a skill pair with zj-roadmap-driven (plan → track); zj-to-tickets is the seam converter.
disable-model-invocation: true
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its **decision tickets** — questions whose resolution is a decision, not slices of a build to execute — one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off. An effort can override this in its **Notes** — carrying execution into the map itself — but absent that, produce decisions, not deliverables.

## Carrier modes

Wayfinder is **one skill with two switchable carriers** — the planning logic is identical; only the physical home of the map, tickets, blocking, and frontier changes. Pick by scenario, not preference:

- **Tracker mode (teamwork).** The map and its child tickets live on the repo's issue tracker (GitHub/GitLab/…). Wins: multi-agent concurrency via `claim` + native blocking edges, and the human sees the frontier rendered in the tracker's own UI. Needs: a configured tracker — run `/zj-agents-init` if none is provided.
- **Local mode (self-contained).** The entire map — Destination, Notes, Decisions-so-far, Not-yet-specified, Out-of-scope, and the decision tickets — lives in a **single local markdown file** (the "local-markdown tracker"). Wins: context-complete (the human sees the whole map in one session), offline, zero external dependency, single-writer-simple. This is the **default** when no tracker is configured.

**Same mental model either way.** Both modes expose the same primitives — `destination`, `notes`, `decisions`, `fog`, `scope`, and `tickets` with `blocking edges` + a `frontier`. So migrating from local exploration to teamwork (or back) changes the carrier, not the cognition: the map you charted locally drops onto a tracker without re-deciding anything.

> This dual-mode design is the planning half of a deliberate pairing with `zj-roadmap-driven` (see [Combining with zj-roadmap-driven](#combining-with-zj-roadmap-driven)): wayfinder owns *planning* in either carrier; roadmap-driven owns *tracking*, with the same two-mode shape.

## Refer by name

Every map and ticket has a **name** — its title (tracker mode) or its numbered heading in the local markdown file (local mode). In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. In tracker mode a name wraps its issue link; in local mode a name wraps its file-section anchor. The id/URL (tracker) or section number (local) don't vanish — they ride _inside_ the name, never stand in for it.

## The Map

In **tracker mode** the map is a single issue on the repo's issue tracker, labelled `wayfinder:map`; its tickets are child issues of the map. In **local mode** the map is a single local markdown file (e.g. `docs/plans/big-map.md`) — the canonical artifact; its tickets are top-level numbered sections of that file.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

**Where the map, its child tickets, blocking, and frontier queries physically live is carrier-specific** — see [Carrier modes](#carrier-modes). In **tracker mode** the issue tracker should have been provided to you (run `/zj-agents-init` if not; consult its "Wayfinding operations" section for how _this_ repo expresses them). In **local mode** — the default when no tracker is configured — everything lives in one local markdown file you create.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

In **tracker mode** each ticket is a **child issue** of the map; the tracker's issue id is its identity. In **local mode** each ticket is a numbered top-level section of the map file (e.g. `## A1 — …`), and that number is its identity. Either way, the ticket body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

In **tracker mode** each ticket carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task` (see [Ticket Types](#ticket-types)). In **local mode** the type is written into the ticket heading (e.g. `## A1 … [R]`), using `R`/`G`/`P`/`T` from [Ticket Types](#ticket-types).

A session **claims** a ticket before any work. In **tracker mode** that means assigning the issue to the dev driving the map (an open, unassigned issue is unclaimed). In **local mode** that means writing a `🔒` (claimed) marker and the claimer's name on the ticket heading; an open ticket with no `🔒` is unclaimed.

In **tracker mode**, blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier _visually_ in the tracker's own UI. In **local mode**, blocking is a body convention: a ticket lists `⛔ blocked by: <ticket numbers>`; the dependency renders as you read the file. Either way a ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed tickets — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Every ticket is either **HITL** — human in the loop, worked _with_ a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it (a grilling agent that answers its own questions has broken this).

- **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases to surface a fact a decision waits on. Resolved by a `/zj-research` **subagent**. Use when knowledge outside the current working directory is required.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code via the /zj-prototype skill. Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): Conversation. The default case. Always invoke the /zj-grilling and /zj-domain-modeling skills.
- **Task** (HITL or AFK): Manual work that must happen before a _decision_ can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that _does_ rather than decides — and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later tickets depend on.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war** — the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination — everything here is in scope, just not sharp enough to ticket. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination — mis-scoped in while charting, or exposed by a resolution — **close it** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked — a scope boundary isn't a step on it.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session** — with the exception of research tickets.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Run a `/zj-grilling` and `/zj-domain-modeling` session to pin down what this map is finding its way to — the spec, decision, or change. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** — the way to the destination is already clear, the whole journey small enough for one session — you don't need a map. Stop and ask the user how they'd like to proceed.
3. **Create the map.** In **tracker mode** create an issue labelled `wayfinder:map`; in **local mode** create the single local markdown file. Either way: Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**.
4. **Create the tickets you can specify now.** In **tracker mode** create them as child issues; in **local mode** create them as numbered top-level sections. Wire blocking edges in a **second pass** — in tracker mode the issues need ids before they can reference each other; in local mode write `⛔ blocked by:` lines. Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog — the **Not yet specified** section.
5. **Fire the research subagents.** For each `research` ticket you just created, spin up a `/zj-research` subagent to resolve it in parallel, capturing its findings on a throwaway `research/<name>` branch with a context pointer from the ticket.
6. Stop — charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional** — without one, you pick the next decision, not the user.

1. Load the **map** — the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it** before any work — in tracker mode assign the issue to yourself; in local mode add the `🔒` marker + your name to the heading (see [Tickets](#tickets)).
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed ticket on demand; invoke the skills the `## Notes` block names. If in doubt, use `/zj-grilling` and `/zj-domain-modeling`.
4. Record the resolution. In **tracker mode** post the answer as a **resolution comment** and **close** the issue. In **local mode** write the answer under the ticket section and mark it `✅`. Either way **append a context pointer** to the map's Decisions-so-far.
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket. If the answer reveals a ticket — this one or another — sits beyond the destination, **rule it out of scope** rather than resolving it on the route. If the decision invalidates other parts of the map, update or delete those tickets.

In **tracker mode** the user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently. In **local mode** the map is single-writer — resolve one ticket per session and commit the file before the next, since two agents editing one markdown map collide.

## Combining with zj-roadmap-driven

`zj-wayfinder` and `zj-roadmap-driven` are **one designed pair**, not two adjacent tools: **plan, then track**. Wayfinder turns a foggy, too-big idea into a clear map of decision tickets; roadmap-driven then navigates and tracks the work along a defined route while keeping the human aligned at every step. The pairing is built on two commitments:

- **Dual-mode on both sides, but the two skills play different roles.** Wayfinder *produces* a plan in either carrier (tracker / local). Roadmap-driven is the canonical *local / self-contained* carrier (JSON source-of-truth + markdown lightweight view) and, on the tracker side, *consumes* a tracker-planned route — it does not itself plan on a tracker. The mental model — map/route + decisions — is identical across modes, so a plan made in either carrier lands in roadmap-driven's JSON without re-deciding.
- **The seam is a converter, not a rewrite.** `zj-to-tickets` is the bridge: it takes wayfinder's resolved decision map (or any plan/spec) and emits tracer-bullet tickets *with their blocking edges* — as local `.scratch/.../issues/<NN>.md` files or tracker issues, never a roadmap JSON directly. The agent then runs `roadmap_cli.py init/add/decide` to carry those tickets into the roadmap JSON. Hand that JSON to `/zj-roadmap-driven`; don't re-chart it by hand.
- **Choose by phase, not by preference.** Fog (no visible path, big blast radius) → start with wayfinder. A clear, sized route → skip to roadmap-driven. Both respect the same carrier choice, so the switch is seamless.
- **Shared context crosses the seam.** Keep both in the same repo so the domain glossary, ADRs, and conventions carry from planning into tracking.

Human + Agent get both views: the map at planning time (wayfinder) *and* live progress at execution time (roadmap-driven) — alignment holds across the whole effort.

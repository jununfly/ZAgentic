# Documentation governance contract

## Discovery and map choice

Read root `AGENTS.md`, `CLAUDE.md`, and `README.md` for an exact
`docs-map: <repo-relative Markdown path>` pointer. One valid pointer wins.
Without it, use existing `docs/README.md`. With neither, one `*-map.md`
candidate under `docs/` is a proposal; several candidates are an ambiguity;
no candidate is a greenfield proposal. Compatibility discovered in a target
repository wins over this convention.

## Categories

| Lifecycle | Categories |
| --- | --- |
| Long-lived | `methods`, `prds`, `architecture`, `agreements`, `designs`, `testing`, `benchmarks`, `references`, `zj-adr`, `ontology` |
| Process | `plans`, `zj-retros` |

`ontology` is the unified documentation ontology home (ZAgentic-local): the T-Box
(`ONTOLOGY.md` + `ontology.schema.json`) and the product-domain extraction /
validation (`extract.py` + `validate.py`). It is long-lived but ZAgentic-specific;
other repos do not carry it. The governance layer (this skill's `doc-kind` /
`authority` / lifecycle categories, plus `MAP_*`) is the contract's **Module G**;
the product-domain model (platform / bucket / skill / pipeline / validator) is
**Module P**. Both share one vocabulary defined in that repository's ontology
schema file.

Fixture documentation can live beside its fixture and is registered by the
map. Code, tests, fixtures, raw benchmark profiles, logs, research packages,
and evaluations are evidence surfaces rather than durable documentation pages.
`ZJ-CONTEXT.md` and `ZJ-CONTEXT-MAP.md` remain root-level external entries.

## One home per fact

One rule or explanation has exactly one authoritative position in the
documentation system; every other mention links to it. Duplication is a
contract problem rather than a style problem: two copies drift, and once they
disagree no reader can recover which one was true.

Each `doc-kind` is therefore placed by a tier description with two halves —
what it holds (`Job`) and what it refuses (`Does NOT belong there`). The
refused half is what actually prevents drift; a kind defined only by what it
holds will absorb whatever lands beside it. The full mapping is
[kind-templates.md](kind-templates.md), and it is kept 1:1 with the vocabulary
below: a `doc-kind` without a row is a kind that has not been placed.

Placement follows the nearest owner — a package contract sits beside the
package code, and `docs/` carries what crosses packages. When a fact could sit
in two places, the tie-breaker is which page a reader would blame when the fact
goes stale.

## Page and authority contract

`doc-kind` is one of `method`, `prd`, `architecture-map`,
`architecture-overview`, `architecture-layers`, `architecture-subsystem`,
`architecture-flow`, `architecture-cross-cutting`, `agreement`, `design`,
`testing`, `benchmark`, `reference`, `adr`, `plan`, `retro`, or
`fixture-documentation`. `authority` is `primary`, `supporting`, `historical`,
`process`, or `external`; a primary page has one `authority-id`, which the map
binds to one page and bounded question. Navigation order is not global truth
precedence: two pages that answer the same question *differently* are a
Human-review signal, because settling conflicting normative claims needs
judgment about content. A binding is different in kind — which page the map gave
an id to is a fact, not a reading — so its conflicts are mechanical.

The two layers have separate owners:

| Layer | Question | Owner | Codes |
| --- | --- | --- | --- |
| Binding | Does the map give one id to more than one page? | this skill | `MAP_AUTHORITY_CONFLICT` |
| Declaration | Do two pages claim the same id, and do map and page agree? | `zj-docs-architecture` | `AUTHORITY_ID_DUPLICATE`, `AUTHORITY_ID_MISSING`, `AUTHORITY_MAP_BINDING` |

Both can fire on one id, and that is two defects rather than one reported twice:
the map bound it to two pages *and* the pages declared it. Neither tool claims
the other's layer, and neither suppresses the other.

The binding is what the governance tool checks. One `authority-id` appearing on
two map entries is `MAP_AUTHORITY_CONFLICT`, reported against the map and
reflected in a non-zero exit — two pages answering the same bounded question is
a decision the Human has to make, and a report that exits zero would present it
as settled. The tool reads the map only; a page's own `authority` front matter
is `zj-docs-architecture`'s contract to enforce.

## Page form: tutorial or reference

Every page declares one of two shapes before it is written, because the two
shapes fail in opposite ways.

- **tutorial** — an ordered path with one goal, introducing at each step only
  what that step needs.
- **reference** — a lookup surface for current behavior: complete, flat, and
  with no teaching sequence.

A page that mixes them hides the lookup inside the lesson and the lesson inside
the lookup. Mixed on a large scale, split it; mixed on a small scale, label the
sections so a reader can skip one. `Page form` in
[kind-templates.md](kind-templates.md) records the default per kind.

The authoring order is fixed: locate the audience → decide how much detail is
allowed here → pick tutorial or reference → order by prerequisite and
difficulty → push child-level detail to the page that owns it → replace
low-level explanation with a link.

## Page content contract

A page describes the **current state**. History belongs to the commit, the PR,
the `adr`, or the process closeout that produced it; carrying it forward makes
the page longer without making it truer.

Implementation-status annotations are banned from every kind except `plan` and
`design`, where stating status is the job: "implemented!", "not yet wired",
"future: …", and equivalent hedges are true when written and stale within a
week, and a reader cannot tell which. Shipped state is written in the present
tense as a description of reality; unshipped state lives in a proposal.

Scope comes from the topic and the page's position in the tree: a parent gives
purpose, responsibility and high-level behavior, and links the owning
descendant for anything lower. Freshness — whether a page still matches the
source it maps to — is the architecture layer's concern (`SOURCE_*` in
`zj-docs-architecture`); this contract only governs which pages exist and what
they own.

## Evidence: run the facts

Every command, flag, configuration value and default that a page states has
been executed at least once by whoever wrote it. A fact that cannot be
reproduced is deleted rather than copied from memory or by analogy.

Owner is the page's author, and the Human confirming a governance pass may ask
for the run. Two exemptions only: a value quoted from an external system is
cited with that system's version, and a `design` or `plan` may describe a
future state if it says so explicitly.

## Generated regions

Some blocks are maintained by a generator — a directory listing, an API
surface, a derived index. Such a block is marked as generated in the page and
is never hand-edited; a correction belongs in the generator's input, or in
prose outside the marked region. A derived file that is not checked in is
not documentation at all, and a governance pass names it as an evidence
surface rather than a page.

## Migration and lifecycle

Every migration has two stages:

1. A read-only inventory and proposal identifies classification, conventions,
   moves, broken links, authority synthesis, and deletion candidates.
2. The Human confirms each named mutation. Preserve meaning by default; use
   `git mv` for a tracked move. Rewrites, merges, and deletion need their own
   confirmation.

Three rules hold across the whole lifecycle:

1. **Documentation moves with the change.** A change that makes a page wrong
   updates that page in the same commit; a doc-only follow-up is a second
   chance to forget it.
2. **Prune like a bonsai.** A small set of fresh, accurate pages beats a large
   set of broken ones. The intent is freshness, and the means here is always a
   proposal — pruning never authorises an unconfirmed rewrite or removal.
3. **Implementation state decides the home.** Something that exists is
   documented where a user would look for it; a discussion about something that
   does not exist stays outside the durable tree until it does.

A move is **atomic**: every inbound link is repaired in the same change. A move
that leaves broken links behind has not moved the page, it has duplicated the
problem.

The lifecycle is `process material → durable extraction → authority audit →
retirement → inbound references zero → deletion proposal → Human confirmation →
deletion`. `/zj-debrief` produces process material, and `/zj-neat-freak`
governs drift; neither is an event hook.

Default: preserve meaning. Deletion is a named action with its own
confirmation, never a default that fires because a page looks unused.

## Retirement

A page leaves service in stages, because deleting content and deleting inbound
references are different acts and only the second one is safe last.

1. **Retire.** The page stops being authoritative; its `authority` becomes
   `historical` and the map binding is released.
2. **Tombstone.** If anything still points at it, the content is replaced by a
   short page naming the new location (or what replaced it). A tombstone is the
   third option between keeping a stale page and breaking every link to it.
3. **Drain.** Inbound references are repointed. Only once they reach zero is
   the page a deletion candidate.
4. **Propose and confirm.** Deletion is proposed by name and confirmed by the
   Human, like any other mutation.

A page whose subject never existed is not retired — it is process material and
takes the process-material path.

## What a green run does not mean

A mechanical check that exits zero proves one thing: on this content, the
assertions it makes were confirmed consistent. It does not prove the
confirmation itself was right. Whether a page says something true, whether two
pages agree in substance, and whether a proposed move preserves meaning are
semantic questions, and they stay with review and the Human. A gate is a floor,
not a verdict — and a report must never present a green run as settled truth.

## Composition

`zj-docs-architecture` maintains the handbook layer. `zj-domain-modeling`
resolves terminology, `zj-debrief` captures process closeout, and
`zj-neat-freak` reconciles broader knowledge drift. `zj-repo-init` configures
tracker/triage entrypoints only after a selected map exists; it never invokes
this skill.

### Layering: this skill is the governance layer

A consuming repository may express its documentation system as one unified
ontology with **two concern layers**. This skill owns the **governance layer
(Module G)**: the `doc-kind` vocabulary, `authority` levels, lifecycle
categories, and the `docMapBinds` 1:1 rule that drives `MAP_AUTHORITY_CONFLICT`.
The product-domain layer (Module P: for example platform / bucket / skill /
pipeline / validator entities) is that repository's own extension and is **not**
part of this installed skill — it lives in that repository's documentation
ontology, not inside the skill directory. A single combined check in that repo
composes this skill's `docs_governance.py --validate` with the product-domain
rules so one run covers both layers. The two layers share one vocabulary, so
there is no naming collision, and the governance logic stays portable
(installable into any repo) while the product-domain logic stays local —
consistent with this contract's tolerance of skill-local copies over cross-skill
imports.

### What overlaps with `zj-docs-architecture`, and who owns it

Both skills run against the same repository, and both have to select a map
before they can do anything else. Three codes therefore exist under the same
name in both: `MAP_POINTER_BROKEN`, `MAP_AMBIGUOUS`, and `MAP_LINK_BROKEN`.
When the two run together they are one condition seen twice, not two defects —
de-duplicate on `(code, path)`. They are owned here: this skill governs the
whole map, while `zj-docs-architecture` re-derives them only to reach the
architecture pages it is responsible for. Everything that needs a page's
contents (`PAGE_*`, `AUTHORITY_ID_*`, `SOURCE_*`, `ADR_*`) is its alone.

The duplication is tolerated on purpose. Removing it would mean a shared
module, and a skill is installed by copying its directory — a cross-skill import
breaks at install time, while carrying a private copy just moves the same code
and adds a rule that the two must be kept in step.

## Rejected defaults

Decisions that were considered and not taken, recorded so they are not
re-litigated in a later pass.

- **Delete-dead-docs-by-default** (distilled from chromium): rejected. The
  intent — few fresh pages beat many broken ones — is adopted above as bonsai
  pruning, but the means is not. This skill runs in repositories it does not
  own, and a default that removes content without a named confirmation is an
  irreversible act delegated to a machine. Deletion stays the last stage of
  retirement and always needs its own confirmation.
- **A mechanical health-score gate** (page size budget, freshness scoring,
  orphan scoring): rejected for now. The target repository has no manifest and
  no uniform source-map timestamp, so any score would be invented. It is
  carried as a capability gap rather than built on a missing fact source.
- **Banning metaphorical vocabulary** (gate, vocabulary, surface): rejected.
  Those words are load-bearing here, and renaming them would break every
  contract that names them.

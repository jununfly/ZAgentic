# Document slop checklist

Nine classes of documentation rot that a reader can spot by eye. This is an
**audit list, not a gate**: it adds no diagnostic code, it changes no exit
code, and it is not run by `docs_governance.py --validate`. It exists because
"the map is correct" and "the pages are healthy" are different claims — the
map diagnostics in `docs_governance.py` cover the first and say nothing about
the second.

Run it on the pages a governance pass is about to propose changes to. A hit is
a proposal item, never a silent rewrite: it needs its own named confirmation
like any other mutation.

## duplicate-rule

The same rule or explanation stated in two places. It is the most expensive
class because the two copies drift, and then no reader can tell which one is
true.

- **Detect:** search the candidate rule's distinctive phrasing; if it appears in more than one page, and neither page links the other, it is duplicated.
- **Fix:** pick the home by [one home per fact](governance-contract.md#one-home-per-fact), keep it there, and replace the other with a pointer.
- **Scope:** all long-lived categories; a `reference` restating a `method` step is the usual case.

## history-leak

The page narrates how it got here — migration notes, old names, "previously
we…". History has a better home and a longer memory.

- **Detect:** past-tense narrative about the document's own evolution, or about a state that no longer exists.
- **Fix:** move it to the commit, PR, `adr`, or process closeout that produced it; leave the current state only.
- **Scope:** all pages; most common in `architecture-overview` and `method`.

## status-annotation

Inline notes about implementation state: "implemented!", "future: …",
"TODO", "not yet wired". They are true when written and stale within a week,
and a reader cannot tell which.

- **Detect:** grep for the annotation vocabulary and modal hedges attached to a feature rather than a proposal.
- **Fix:** delete it. Shipped state belongs in the page's present-tense description; unshipped state belongs in a `plan` or `design`, not in an annotation.
- **Scope:** every page except `plan` and `design`, where stating status is the job.

## hand-copied-restatement

Prose that restates something a generator or a source of truth already emits:
a directory listing, an API surface, a schema, a table of counts.

- **Detect:** the paragraph would go stale if the source changed, and no tool would tell anyone.
- **Fix:** replace with a link to the source, or mark the block as a [generated region](governance-contract.md#generated-regions) and let the generator own it.
- **Scope:** `reference`, `architecture-layers`, any page containing counts or enumerations.

## reasoning-aside

The page shows the author's thinking — "we considered…", "one might wonder…",
"the reason this is subtle is…" — where the reader needed the conclusion.

- **Detect:** first-person plural reasoning that does not end in a stated decision or fact.
- **Fix:** keep the conclusion; move the reasoning to the `design` or `adr` that owns it.
- **Scope:** `method`, `reference`, `architecture-*`.

## rationale-repeat

The same justification appears in both the decision record and the page
describing the outcome. Readers then maintain two versions of a reason.

- **Detect:** a "because" clause that also appears verbatim in an `adr` or `design`.
- **Fix:** state the outcome on the page and link the record for the why.
- **Scope:** `architecture-*`, `method`.

## paragraph-wall

A block of prose that carries several facts and no structure, so no single
part of it can be linked, scanned, or corrected.

- **Detect:** a paragraph longer than about eight lines, or one that answers more than one question.
- **Fix:** split by question; give each part a heading or a list item that can be pointed at.
- **Scope:** all pages; matters most where agents read the page, because a wall cannot be loaded selectively.

## emphasis-inflation

Bold, italics, or callouts on so much text that emphasis stops discriminating,
and the reader has to re-read everything to find what actually matters.

- **Detect:** emphasis density high enough that a skim finds no unmarked text.
- **Fix:** mark only the constraint or the failure mode; let the rest be plain.
- **Scope:** all pages; especially `method` steps and anything consumed by an agent.

## spec-speak

Normative language used loosely — "should", "must", "always", "never" — where
no one can say what happens if it is violated, or who checks.

- **Detect:** a modal with no owner, no exception, and no consequence.
- **Fix:** either make it a real rule with an owner and a consequence, or downgrade it to guidance and say so.
- **Scope:** `agreement`, `reference`, `architecture-cross-cutting`.

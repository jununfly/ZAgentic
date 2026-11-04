---
name: zj-review-findings
description: Triage and respond to review findings on your own change — confirm which ref the reviewer read, verify before accepting or refuting, prove a "covered" claim with a targeted mutation test, and draw the machine-check vs review-responsibility boundary. Use when Standards/Spec findings arrive on a branch or PR, or when a reviewer says something is "not implemented", "not covered", or "not visible".
source: zagentic
---

# Review findings: the response protocol

`zj-code-review` produces findings along two axes; design review, CI gates, and
research/diagnosis reviews produce the same shape. This skill is the response
protocol for all of them — what to do when findings land on your desk.
`zj-code-review` is the most common trigger, but not the only one. It exists
because the expensive failures happen here, not in the review — accepting a
false finding creates duplicate work, and refuting a true one ships a defect.

## Step 1 — Confirm the ref before you touch anything

A finding of the form "X is not implemented / not covered" is often **true on the
ref the reviewer read and false on the one you worked on**.

```sh
git rev-parse --abbrev-ref HEAD
git show main:<path>   | grep -c <marker>   # what the reviewer probably read
git show <branch>:<path> | grep -c <marker> # what you actually changed
git branch --merged main | grep <branch>    # is it merged at all?
```

If the fix exists on your branch but not on `main`, say so in one line and give
the reviewer the branch name. **Do not merge just to make the finding go away**
— merging may destroy a deliberate isolation boundary (two-arm experiments,
parallel implementation branches). Either re-point the review at the branch, or
mark the item `deferred-until-merge` with an owner.

## Step 2 — Verify, then either accept or refute

Never respond to a finding from memory. Produce file:line evidence for both
directions:

- **To refute**: the implementation line, the test that covers it, the contract
  text that specifies it, and the commit that shipped it. Four citations, no
  adjectives.
- **To accept**: name the root cause in one sentence, not the symptom. "Only
  exact string equality" beats "the check is weak" — the root cause tells you
  what to fix.

## Step 3 — Prove the assertion is not vacuous (mutation test)

"Tested" means nothing if the test would pass with the check removed. Before you
claim coverage — and after you add a test — disable **only the target branch**
and confirm the specific test fails:

```python
original = src.read_text(encoding="utf-8")
patched  = original.replace(ANCHOR_LINE, NEUTRALISED_LINE, 1)
assert patched != original          # the anchor must exist, else the test lies
try:
    src.write_text(patched, encoding="utf-8")
    run the suite -> must be non-zero, and the message must name your case
finally:
    src.write_text(original, encoding="utf-8")
assert src.read_text(encoding="utf-8") == original
```

Rules that make this worth doing:

- Change **one** branch. Killing the whole check only proves the suite notices
  something; it does not prove *your* assertion fired.
- Assert on the failure **message**, not just the exit code, so you know which
  case caught it.
- Always restore in a `finally`, then verify the working tree is clean.

## Step 4 — Draw the machine-check boundary, then write it down

Most "the gate doesn't catch X" findings are really "X is not machine-checkable
without unacceptable false positives". Decide with **asymmetric cost**:

| | Cost when wrong |
|---|---|
| Machine check too strict | false rejection — usually blocks a build or a publication |
| Machine check too loose | the defect escapes to human review, which exists to catch it |

When the strict side is worse, keep the check exact and assign the rest to the
review layer. **Then add a positive test that pins the boundary** — a legitimate
input that a stricter rule would reject — so a future "let's tighten this"
change fails loudly instead of silently breaking valid inputs.

## Step 5 — Never let a boundary live only in conversation

If a contract's guarantee is narrower than it looks, write the narrowing into
the contract text itself, in every place a reader could form the wrong
assumption:

- the spec / `SKILL.md` / standard that states the requirement;
- the vocabulary or glossary entry, if the repo keeps one (a new term without a
  glossary entry is its own finding);
- the code comment at the check, explaining why it is deliberately exact.

Two recurring shapes worth naming explicitly:

- **Required ≠ non-empty.** "Must name an owner" is not enforced by
  `value.strip() != ""` — `"TBD"` passes. Keep an explicit placeholder
  rejection set.
- **Gate pass ≠ user-visible.** A field can be validated and enforced while the
  renderer never prints it. Check where rendering lives before promising
  visibility — it may be a pinned external artifact in another repository, which
  turns the finding into an upstream dependency, not a local fix.

## Step 6 — Separate "artifact exists" from "the condition is proven"

Closing a checklist item is not the same as satisfying what it was checking.
When an acceptance item names several things, report them one by one:

| sub-item | state |
|---|---|
| changed files recorded | done |
| test commands and results recorded | done |
| commit SHA | **missing — commit is a Human gate in this repo** |

And when the deliverable finally exists, do not let it imply more than it does:
having a merged commit proves the change landed, not that the behaviour it was
meant to produce was measured. Say both halves in one sentence.

## Output shape

Per finding, one short block:

- **Verdict** — accept / refute / accept-in-part, one line.
- **Evidence** — the citations (accept) or the four citations (refute).
- **Fix** — what changed, or why no in-scope fix exists.
- **Deferred to** — the owner and the dependent change, if you are deferring.

Keep the "no in-scope fix" case explicit and evidenced. A finding closed as
"out of scope" with no evidence of *why* is a defect waiting to be reopened.

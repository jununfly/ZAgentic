---
name: zj-research
description: Investigate a question against high-trust primary sources and capture cited findings in the repo. Use for documentation or API reading legwork and for multi-repository technical comparisons that need commit-pinned GitHub evidence.
---

`zj-research` is the domain-neutral evidence seam. It produces re-verifiable
findings, provenance, sealed ledgers, and explicit unknowns for a downstream
domain method. It does not clean domain material, write a finished report,
rank options, or make the technical recommendation; those decisions belong to
the consuming research skill.

Choose one branch.

## Primary-source reading

Spin up a background agent so the parent can keep working. Give it the question and output path, but not an intended answer. It must follow every claim to official documentation, source code, a specification, or a first-party API; write one cited Markdown findings file; and match the repository's existing research-note location.

Completion criterion: every non-trivial finding names a re-verifiable primary source, and the parent reports the saved path.

## Multi-repository technical comparison

Read [references/research-cli.md](references/research-cli.md), then:

1. Write one complete `zj-research-brief/v1` request with the same criteria for every repository. Include explicit repositories, deterministic GitHub discovery, or both. Separate popularity from topic relevance.
2. Run `python <this-skill>/scripts/research_cli.py request.json --output ledger-response.json`.
3. Save the response's sealed ledger beside the findings. Use only its canonical evidence for GitHub claims.
4. Write the cited findings from the ledger. Each `unknownCriteria` entry remains unknown; it is not a negative capability claim.

Completion criterion: every selected repository is pinned to a commit, stars and topic match come from the sealed ledger, each claim traces to an Evidence ID, and every uncovered repository/criterion pair is explicit.

## Shared compiler runtime

The compiler and evaluation adapters under `scripts/` are the canonical shared
runtime for the research bucket. Keep their protocol and artifact-lock logic
here so independently installed consumers can point at this skill rather than
copying an adapter. Read [the runtime reference](references/research-cli.md)
when a downstream skill needs collection, compilation, rendering, or evaluation.

Completion criterion: the saved evidence names its source or sealed ledger,
its unknowns remain explicit, and any compiler-backed operation was run through
this canonical runtime.

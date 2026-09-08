# Explicit `/zj-repo-init` pointer only for hard dependencies

Engineering skills depend on per-repo collaboration config (issue tracker and triage vocabulary) seeded by `/zj-repo-init`. Documentation-system discovery is separately owned by `/zj-docs-ontology`. Some skills cannot meaningfully function without tracker config — they have to publish to a specific issue tracker or apply a specific label string. Others only use documentation to sharpen output and degrade gracefully without it.

We split these into **hard-dependency** and **soft-dependency** skills:

- **Hard dependency** (`zj-to-tickets`, `zj-to-spec`, `zj-triage`) — include an explicit one-liner: _"… should have been provided to you — run `/zj-repo-init` if not."_ Without the mapping, output is wrong, not just fuzzy.
- **Soft dependency** (`zj-diagnosing-bugs`, `zj-tdd`, `zj-improve-codebase-architecture`) — reference "the project's domain glossary" and "ADRs in the area you're touching" in vague prose only. If the docs aren't there, the skill still works; output is just less sharp.

The split keeps soft-dependency skills token-light and avoids cargo-culting the setup pointer into places where it isn't load-bearing.

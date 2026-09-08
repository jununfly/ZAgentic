---
name: zj-docs-architecture
description: "Maintains and validates a codebase's multi-view architecture handbook: map, layers, subsystems, flows, and cross-cutting rules. Use when creating, reviewing, migrating, or validating architecture documentation and its source maps."
---

# Architecture Handbook

Keep one architecture map that routes readers to complementary views; never use
the map to repeat those views. This skill owns handbook shape, not domain
terminology (`/zj-domain-modeling`), hard-to-reverse decisions
(`/zj-grill-with-docs` and ADR work), or a repository's whole documentation
governance (`/zj-docs-ontology`).

## Workflow

1. **Discover, read-only.** Run the discovery command below. Follow an explicit
   `docs-map: <repo-relative Markdown path>` pointer in root `AGENTS.md`,
   `CLAUDE.md`, or `README.md`; otherwise use `docs/README.md`; otherwise
   report one compatible candidate or an ambiguity. Do not create a second map.
2. **Classify the gap.** Route readers to a system overview, layers, subsystem,
   flow, or cross-cutting page. A rule or explanation has one durable owner;
   link from other views rather than copying it.
3. **Propose before mutation.** For greenfield, propose the smallest map and
   only needed pages. For existing material, inventory paths, contracts,
   authority conflicts, moves, link repairs, and synthesis decisions. Wait for
   explicit Human confirmation before creating, moving, rewriting, or deleting.
4. **Write the confirmed slice.** Apply the page contract and source-map
   evidence. Label each statement as target architecture, implemented behavior,
   inference, or explicit unknown; do not turn inference into fact.
5. **Validate.** Run the validator and resolve mechanical failures. Present
   duplicate/ambiguous ownership as a Human-review signal, never an automatic
   winner.

```sh
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py .
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py . --discover
```

Read [architecture-contract.md](references/architecture-contract.md) before
proposing pages or migration. Read
[validator-contract.md](references/validator-contract.md) when interpreting a
diagnostic, changing the validator, or adding a fixture.

## Completion

Finish a handbook slice only when its selected map routes to the intended
views, each primary view has one mapped `authority-id`, source-map targets
exist, and the validator exits successfully. A migration stays a proposal until
the Human confirms its named moves, rewrites, and deletions.

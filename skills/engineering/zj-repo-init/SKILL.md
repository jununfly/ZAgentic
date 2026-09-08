---
name: zj-repo-init
description: "Configures a repository's collaboration entrypoints: issue tracker, triage vocabulary, and concise Agent rules. Use when tracker or triage setup is needed before `zj-to-tickets`, `zj-to-spec`, `zj-triage`, or `zj-wayfinder` can operate correctly."
disable-model-invocation: true
---

# Initialize Repository Collaboration

Configure the collaboration surfaces that tracker-dependent skills assume:

- **Issue tracker** — where issues live
- **Triage labels** — the strings used for the five canonical triage roles
- **Agent entrypoint** — concise pointers to the selected document map and the
  agreements below

This is a prompt-driven skill. Discover, present a bounded proposal, obtain
confirmation, then write. `/zj-docs-ontology` owns documentation-system
creation, migration, and repair; this skill never invokes it or creates docs
implicitly.

## Process

### 1. Discover

Read the remote, root `AGENTS.md` / `CLAUDE.md`, existing Agent-skills block,
`.scratch/`, `docs/agreements/agent-workflow/`, and one documentation-map
candidate: an explicit active pointer or `docs/README.md`.

If no selected document map exists, stop before proposing writes. Tell the
Human to run `/zj-docs-ontology` to discover or establish one, then return
here. Do not create a docs map, category, root context file, ADR layout, or
migration proposal.

### 2. Ask and propose

Summarise what is present, then ask one decision at a time:

1. **Issue tracker.** Propose GitHub for a GitHub remote, GitLab for a GitLab
   remote, otherwise GitHub, local Markdown, or the Human's described tracker.
2. **Triage labels.** Map `needs-triage`, `needs-info`, `ready-for-agent`,
   `ready-for-human`, and `wontfix` to the actual tracker labels. Default each
   string to its canonical role.

Show a draft of the Agent-skills block and of the two agreements before writing.

### 3. Write after confirmation

Edit the existing `CLAUDE.md`, otherwise existing `AGENTS.md`; when neither
exists, ask which file to create. Update a pre-existing `## Agent skills` block
in place. It must point to:

```markdown
### Issue tracker

[summary]. See `docs/agreements/agent-workflow/issue-tracker.md`.

### Triage labels

[summary]. See `docs/agreements/agent-workflow/triage-labels.md`.

### Documentation and agreements

[selected map path]. See `docs/agreements/agent-workflow/domain-docs.md`.
```

Write these target-repository agreements using the bundled templates:

- `docs/agreements/agent-workflow/issue-tracker.md` from the matching
  `issue-tracker-*.md` template, or from the Human's tracker description;
- `docs/agreements/agent-workflow/triage-labels.md` from `triage-labels.md`;
- `docs/agreements/agent-workflow/domain-docs.md` from `domain.md`, adjusted
  only to name the selected map.

### 4. Finish

Report the configured tracker and triage vocabulary, the Agent-rule file, and
the selected map. Agreement changes may be made directly later; documentation
system changes remain an explicit `/zj-docs-ontology` task.

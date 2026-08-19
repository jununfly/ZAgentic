---
name: zj-initiative-registry
description: Manage an Initiative → Spec → Plan registry stored in a user-specified GitHub repository, including registration, validation, drift checks, semantic diffs, and safe cross-device Git handoff. Use when creating or maintaining a global Initiative map, registering PRDs or roadmap files, resolving work across repositories, or synchronizing that navigation between devices and Agents.
---

# Initiative Registry

Treat the user-specified GitHub repository as the shared Registry fact source. Require its URL on first use; never infer a writable remote from the current repository.

## Workflow

1. Resolve the Registry URL and local checkout. Use an existing checkout map or ask for a local path; clone only after explicit authorization.
2. Read the Registry repository's `AGENTS.md` and protocol Spec before changing manifests or generated files.
3. Classify the request as query, validation, registration, removal, drift check, or publication.
4. For registration or ownership changes, present the proposed Initiative, Spec, and Plan relationship and obtain Human confirmation.
5. Change only the owning manifest through the Registry's deterministic admin script; compile and validate before publication.
6. Show the semantic diff. Use a scoped branch and pull request by default; direct default-branch publication requires explicit authorization.
7. Report the Registry repository URL, commit or branch, changed IDs, validation result, and unresolved warnings.

## Commands

Use the bundled wrapper so the Registry checkout remains an injected Adapter:

```bash
python scripts/initiative_registry.py \
  --registry-repo https://github.com/OWNER/REPO \
  --registry-path /path/to/checkout \
  validate
```

The wrapper delegates to the versioned scripts in the Registry repository. Run `show`, `compile`, `validate`, `register`, `remove`, `semantic-diff`, `sync`, `create-branch`, or `publish-plan`; see [command reference](references/COMMANDS.md) when composing mutation arguments.

## Ownership rules

- Registry manifests own navigation metadata; Initiative repositories own PRD and Plan contents.
- Paths are repository-relative and contain no device-local absolute paths.
- Plan status, decisions, and focus stay in the Plan JSON and are managed by `zj-roadmap-driven`.
- Broken registered references are errors; unregistered repository documents are warnings.
- Remote movement, dirty publication state, validation failure, or ambiguous ownership stops publication.
- Credentials stay in the user's Git/GitHub credential store and never enter Registry files or logs.

## Completion

Finish only when every changed manifest compiles into JSON, Markdown, and Mermaid projections; Registry validation passes; semantic diff names every added, changed, or removed ID; and the Human-approved Git handoff is complete or explicitly left as a local branch.

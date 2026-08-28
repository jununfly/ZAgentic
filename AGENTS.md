Public skills are organized into bucket folders under `skills/`; private skills
live in the separate root-level `personal/` tree:

- `engineering/` — daily code work
- `productivity/` — daily non-code workflow tools
- `misc/` — kept around but rarely used
- `research/` — evidence production and domain-specific research methods
- `personal/` — tied to my own setup, installable but not promoted or plugin-registered

Before adding, moving, or removing an Initiative, spec, or roadmap plan in `docs/plans/global-initiative-roadmap.json`, read [its maintenance rules](docs/plans/global-initiative-roadmap.agent.md); the global index uses a fixed three-level model that differs from `zj-roadmap-driven` execution roadmaps.

Material placement is purpose-based: put shared input material in
`skills-inputs/<topic>/`; put artifacts produced by a skill in
`skills-outputs/<skill>/<topic>/`.

## ZAgenticOPN activation pointer

When Human sends the exact alias `检查 shared context` in this repository,
follow the sibling `../ZAgenticOPN/skills/zj-opn-activation/SKILL.md` before
producing a repository summary. Use a host-provided receipt when the host
already activated the request; otherwise bind this repository to the canonical
scope `jununfly/ZAgentic/zj-research-report`, use a fresh `activation_id` and
the host's stable Agent profile, and route one activation through the
canonical runner `python -m zagentic_opn.activation_runner`, which reads one
JSON-Call on stdin and prints one receipt on stdout:

```sh
cd ../ZAgenticOPN
AID=$(uuidgen | tr 'A-Z' 'a-z')
cat <<EOF | python3 -m zagentic_opn.activation_runner
{
  "schema_version": "zagenticopn.activation.v1",
  "intent_id": "zagenticopn.activation.check_shared_context.v1",
  "activation_id": "$AID",
  "scope": "jununfly/ZAgentic/zj-research-report",
  "agent_profile": {
    "agent_id": "${ZAGENTICOPN_AGENT_ID:-workbuddy-01}",
    "device_id": "${ZAGENTICOPN_DEVICE_ID:-device-a}",
    "capabilities": ["${ZAGENTICOPN_CAPABILITIES:-technical-writing}"],
    "permissions": ["${ZAGENTICOPN_PERMISSIONS:-zagentic-skill-write}"],
    "can_review": false
  },
  "host_capabilities": ["pre_model_handoff_injection"]
}
EOF
```

The environment values above are the host's stable profile; override them when
the host identity differs. `activation_id` must be freshly generated for every
activation. The store path comes from the host runtime config
(`~/Library/Application Support/zagenticopn/runtime.json`), never from the
request. Do not run a second activation when a valid receipt is already
present. The activation selects work through discovery; it receives no Work
Item id.

Do not call `../ZAgenticOPN/scripts/activate_agent.py`. It bypasses the
versioned contract: no `host_capabilities` check, no rejection event recorded,
and its stdout is the raw adapter result rather than a
`zagenticopn.activation.receipt.v1` receipt.
For a `claimed` receipt, continue the returned handoff within the same
activation. For `no_eligible_work`, `claim_conflict`, `unsupported_host`,
`scope_unbound`, `handoff_delivery_failed`, `invalid_contract`, or
`invalid_runtime_config`, report the receipt's status and its
`next_action`/`repair_action`, then stop. Other requests follow the ordinary
repository instructions.

Every skill in `engineering/`, `productivity/`, `misc/`, or `research/` must have a reference in the top-level `README.md` and participate in the recursive `./skills/` plugin discovery. Skills in the root-level `personal/` tree must not appear in either.

Each skill entry in the top-level `README.md` must link the skill name to its `SKILL.md`.

Each public bucket folder has a `README.md` that lists every skill in the bucket with a one-line description, with the skill name linked to its `SKILL.md`. The root-level `personal/` tree has the same local index but is excluded from public indexes.

## PR checklist (1-3-3-1 A-only 3 rule)

Every skill-touching PR must satisfy all three:

1. **Plugin registration** — if `skills/` changed, verify the new/changed skill participates in the recursive `./skills/` plugin discovery (bucket `README.md` + top-level `README.md`). `.codex-plugin/plugin.json` is a legacy slot and is no longer required; see `zj-triage` A-ONLY Rule 1. Skills not registered are invisible to the harness.
2. **Safe git operations** — all git operations go through `./scripts/zj-git` (or `env -u NODE_OPTIONS git`). The WorkBuddy safe-delete shim corrupts `.git/` on Windows Git Bash; see `skills/engineering/zj-git-bypass-safe-delete/`.
3. **Vocabulary sync** — any new domain term introduced in the PR must be added to `ZJ-CONTEXT.md` before merge. Skills that "make up" vocabulary break downstream skills that consume it.

## Cross-stage skills (1-6)

Three skills live in `engineering/` but are not A↔B-specific — they are the meta-capabilities of any skill-pair workflow:

- `zj-steelman` — pre-plan defense (before grilling)
- `zj-dry-run` — pre-commit rehearsal (mid-plan)
- `zj-debrief` — post-task close-out (after completion)

Use them. See `docs/designs/zj-cross-stage-skills.md` for the complementarity matrix.

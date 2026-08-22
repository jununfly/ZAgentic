Public skills are organized into bucket folders under `skills/`; private skills
live in the separate root-level `personal/` tree:

- `engineering/` — daily code work
- `productivity/` — daily non-code workflow tools
- `misc/` — kept around but rarely used
- `personal/` — tied to my own setup, installable but not promoted or plugin-registered

Every skill in `engineering/`, `productivity/`, or `misc/` must have a reference in the top-level `README.md` and an entry in `.claude-plugin/plugin.json`. Skills in the root-level `personal/` tree must not appear in either.

Each skill entry in the top-level `README.md` must link the skill name to its `SKILL.md`.

Each public bucket folder has a `README.md` that lists every skill in the bucket with a one-line description, with the skill name linked to its `SKILL.md`. The root-level `personal/` tree has the same local index but is excluded from public indexes.

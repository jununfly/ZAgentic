# Skill-pair merge side-effect checklist

Reverse-engineered from 1-3 commits `8fbf5c5` through `a895f47`. Cover every applicable class when planning one merge.

| # | side effect | when to apply |
|---|---|---|
| 1 | Add new skill SKILL.md (verbatim from source) | `adopt`, `replace`, `strict-align` |
| 2 | Add `agents/openai.yaml` if source has it | when B has sidecar |
| 3 | Delete old skill directory | `replace`, `reject` |
| 4 | `git mv` old → new path for renames | `adopt` where A is renamed to B's name |
| 5 | Cross-skill reference updates (other skills' SKILL.md referring to old name) | any name change |
| 6 | Top-level `README.md` skill list update | any add/remove/rename |
| 7 | `skills/engineering/README.md` or `skills/productivity/README.md` update | any add/remove/rename in that bucket |
| 8 | `zj-agents-init/issue-tracker-*.md` and `domain.md` template update | when hard-dependency list changes |
| 9 | `ZJ-CONTEXT.md` term table update | when new domain terms are introduced or renamed |
| 10 | `docs/zj-adr/*.md` cross-reference update | when ADR text mentions old skill name |
| 11 | Copy supporting source files (CONTEXT-FORMAT.md, ADR-FORMAT.md, sub-skill docs...) | when source dir has them |
| 12 | Delete supporting old files | when old skill had them and they don't survive rename |

## Files this skill touches (per merge)

- `skills/<bucket>/zj-<name>/...` (the skill body)
- `README.md` (top-level)
- `skills/engineering/README.md` or `skills/productivity/README.md`
- `skills/engineering/zj-agents-init/issue-tracker-*.md` (if hard-deps changed)
- `skills/engineering/zj-agents-init/domain.md` (if domain terms changed)
- `ZJ-CONTEXT.md` (if domain terms changed)
- `docs/zj-adr/*.md` (if ADR refs old name)
- `docs/plans/roadmap-<wave>.json` (the active wave's roadmap JSON, when human runs `update` after)

Never touches: scratch dirs, source dirs (read-only), `~/.workbuddy/` (out of repo).

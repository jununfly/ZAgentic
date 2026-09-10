# Roadmap data model

Use this reference when creating, inspecting, renaming, or updating roadmap nodes.

## Node fields

| Field | Type | Meaning |
|------|------|---------|
| `id` | string | Number such as `1`, `1-1`, `1-1-1` |
| `label` | string | Node name |
| `status` | string | `pending` / `in_progress` / `completed` / `blocked` |
| `mode` | string | `explore` / `exploit` |
| `parent` | string\|null | Parent node id; `null` for the root |
| `children` | list | Child node ids |
| `decisions` | list | Decision records `[{q, answer, note}]` |
| `notes` | string | Free-form notes |
| `budget` | dict | Structural cap `{max_children, max_rounds}`; absent or missing sub-key = unlimited |
| `exit_criteria` | list | Checkable completion conditions (strings) |
| `rounds` | int | How many times the node has been started (entered `in_progress`) |

## Budget and exit criteria

`mode: explore` says "there is unknown here"; `budget` says how far the
exploration may go, and `exit_criteria` says when an `exploit` node is done.

- `max_children` — how many children this node may grow. `add` under a node at
  its cap fails with `E_BUDGET_EXCEEDED` (exit code 3) and changes nothing.
  Shrinking the cap does not reject children that already exist.
- `max_rounds` — how many times the node may be **started**. A start is any
  transition into `in_progress`; the first one writes `rounds: 1`. Reopening a
  node past its cap fails the same way. A node created by `init` counts as
  already started.
- Units are structural, never tokens: token counts are not comparable across
  models and cannot be estimated while planning. Use `--fields` / `--format`
  for token economy instead.
- `exit_criteria` is stored and returned, never evaluated — the CLI cannot judge
  natural language, and an unmet criterion does not block completion. Treat it
  as the checklist a Human or Agent reads before ticking `[x]`.

```bash
python roadmap_cli.py update roadmap.json 1-2 --max-children 3 --max-rounds 2
python roadmap_cli.py update roadmap.json 1-2 --exit-criteria "三项对比跑完" --exit-criteria "结论写进 decisions"
python roadmap_cli.py update roadmap.json 1-2 --clear-budget --clear-exit-criteria
```

Neither `budget` nor `exit_criteria` appears in the Markdown view by default;
they live in the fact source and in `get` output.

## Status and mode display

| Status | Icon | Meaning |
|--------|------|---------|
| `pending` | `[ ]` | Not started |
| `in_progress` | `[~]` | In progress |
| `completed` | `[x]` | Completed |
| `blocked` | `[!]` | Blocked |

| Mode | Tag | Meaning |
|------|-----|---------|
| `explore` | `[X+]` | Direction, scope, or priority is still being explored |
| `exploit` | `[Y+]` | Direction is settled and work is being deepened |

Tree output uses `[status icon][mode tag] id. label`.

## Node naming

Node names must be **self-explainable**: the name alone should say what will be done. Use the parent as context for the complete scope.

- Good: `文章处理后端流水线`, `数据库层异步IO重构`, `用户认证OAuth2集成`
- Avoid generic names such as `优化`, `重构`, `修复`, `处理`, or `完成`.

When using `add` or `update --label`, check that the name is self-explainable. Warn the Human about a generic name, but may continue.

## Safe label changes

When `update --label` changes the meaning of a node (not just its wording), ask:

> "`node({id}. {旧name})` 将更新为 `node({id}. {新name})`，是否要新建 sub-node 对应偏差，避免跟踪遗漏？"

After the Human answers:

1. If yes, run `update --label`, then immediately `add` a child with the old name and `pending` status.
2. If no, run `update --label` without an extra node.

Meaning shift examples:

- Triggers: `文章+视频处理` → `文章处理` (scope narrowed); `日志系统` → `文档系统` (subject replaced).
- Does not trigger: `文章处理` → `文章处理流水线` (wording refined).

## Parent status synchronization

After `update --status`, `add`, or `delete`, the system synchronizes status upward:

- All children `completed` → parent becomes `completed`.
- Any child is not `completed` → parent cannot remain `completed` and is downgraded to `in_progress`.

The cascade continues through ancestors to the root.

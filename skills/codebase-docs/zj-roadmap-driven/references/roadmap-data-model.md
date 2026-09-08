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

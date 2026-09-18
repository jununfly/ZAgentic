# Slice 1 · 知识复利工具 Phase 0 最小闭环 — ready-for-agent tickets

- **编排源**：`ZKnowledgeCompounding/docs/prds/知识复利工具_roadmap_slice1.json`
- **Spec**：`ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md`

这些 ticket 是 Slice 1（FR-012 + FR-001~006 + FR-008）的实现切片，按 `zj-to-tickets`
拆成 tracer-bullet 垂直切片，每个标 `Status: ready-for-agent`，构成从 utopia 地基到
消费侧闭环的可验证链路。

## 依赖顺序（Blocked by）

| Ticket | FR | Blocked by |
|--------|----|-----------|
| 01-utopia-base | FR-012 | — |
| 02-ingest-local-vector-index | FR-001 | 01 |
| 03-decompose-retrieve-cite-report | FR-002 / 003 / 004 | 02 |
| 04-groundedness-check-loop | FR-005 | 03 |
| 05-semi-auto-reflow-utopia | FR-006 | 01, 04 |
| 06-zj-active-query-hit-history | FR-008 | 01, 05 |
| 07-seam-e2e-acceptance | 验收（§9.1 MVP） | 04, 05, 06 |

## 验收门禁（三项同时达标）

- **Seam 1**：引用可回溯率 ≥ 90% 且 groundedness ≥ 0.8
- **Seam 2**：回流率 ≥ 50% 且消费侧 recall ≥ 50%

## 发布说明

- 因 ZAgentic 的 `zj-repo-init` 未跑、且当前 GitHub MCP 集成缺少此仓库的 issue 写权限
  （POST issues → 403），本批以 `.scratch` 文件形式发布到 GitHub（zj-to-tickets 的本地形态），
  而非 GitHub issues。
- 待 `zj-repo-init` 补齐 canonical labels（含 `ready-for-agent`）+ MCP 重连获得写权限后，
  可一键将这些 ticket 转为带 `ready-for-agent` label 的 GitHub issues。

# Slice 1 · 知识复利工具 Phase 0 最小闭环 — ready-for-agent tickets（技能层）

- **编排源**：`ZKnowledgeCompounding/docs/prds/知识复利工具_roadmap_slice1.json`
- **Spec**：`ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md`

本目录现在只保留 **技能层** tickets（方案 B：按层拆）。知识复利工具 Slice 1 拆为两层：

## 仓库分层（方案 B：按层拆）

- **ZAgentic（本目录，技能层）**：`zj-deep-research` skill 内部管线。
  - `02` ingest-local-vector-index（FR-001）
  - `03` decompose-retrieve-cite-report（FR-002/003/004）
  - `04` groundedness-check-loop（FR-005）
- **ZKnowledgeCompounding（产品层）**：utopia 持久层基建 + 产品编排 / 消费侧。
  - `01` utopia-base（FR-012）
  - `05` semi-auto-reflow-utopia（FR-006）
  - `06` zj-active-query-hit-history（FR-008）
  - `07` seam-e2e-acceptance（验收）
  - 路径：`ZKnowledgeCompounding/.scratch/knowledge-compounding-slice1/`

## 依赖顺序（技能层内；跨仓库依赖见产品层 tickets）

| Ticket | FR | Blocked by |
|--------|----|-----------|
| 02-ingest-local-vector-index | FR-001 | — |
| 03-decompose-retrieve-cite-report | FR-002/003/004 | 02 |
| 04-groundedness-check-loop | FR-005 | 03 |

## 验收门禁（三项同时达标，由产品层 T07 执行）

- **Seam 1**：引用可回溯率 ≥ 90% 且 groundedness ≥ 0.8
- **Seam 2**：回流率 ≥ 50% 且消费侧 recall ≥ 50%

## 发布说明

- 因 `zj-repo-init` 未跑、且当前 GitHub MCP 集成缺少此仓库的 issue 写权限（POST issues → 403），本批以 `.scratch` 文件形式发布到 GitHub（zj-to-tickets 本地形态）。
- 技能层 tickets（02/03/04）留在本仓库；产品层 tickets（01/05/06/07）已迁至 ZKnowledgeCompounding（见上）。

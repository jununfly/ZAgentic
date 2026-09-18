# 03 — Decompose + Retrieve + Cite + Report（FR-002/003/004）

**Status:** ready-for-agent
**Blocked by:** 02 — Ingest 摄入与本地向量索引
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-002/003/004, Impl Decisions: 管线选型 / 检索与引用)

## What to build

在 `zj-deep-research` skill 中实现 research-agent 的核心管线三段：

1. **Decompose（FR-002）**：把用户的研究目标拆成若干可独立检索的子问题。
2. **Retrieve + Cite（FR-003）**：每个子问题独立检索——先查 T02 建好的私有库（本地向量索引），再按需联网；用 cross-encoder 重排结果；**强制 `[DOC_ID]` 引用**，每句论断都指向可追溯的来源；采用 STORM 式大纲先行，防止写作漂移。
3. **Report（FR-004）**：聚合所有子问题的检索结果，产出带内联引用的报告（markdown / 可导出）。

这是「研究能力」本身——产出带引用、可审计的报告，为后续 groundedness 校验（T04）与回流（T05）提供输入。

## Acceptance criteria

- [ ] 给定「目标 + 私有材料」，管线产出一份带 `[DOC_ID]` 引用的报告
- [ ] 报告中的论断可经 `[DOC_ID]` 回溯到具体来源（私有材料页级 / 联网来源 URL）
- [ ] 子问题拆解可见、可复核（不是黑箱一次性产出）
- [ ] 引用可回溯率作为可观测指标可测（具体阈值在 T07 验收）
- [ ] 管线优先走本地 LLM / 自托管，不强制联网；联网仅用于私有库不足的检索补足

## Key interfaces / decisions (from spec)

- **管线选型**：gpt-researcher / STORM 式自托管，可接本地 LLM；备选 paperqa2 偏学术不首选
- **检索与引用**：每子问题独立检索私有库 + 联网；cross-encoder 重排；强制 `[DOC_ID]` 引用；引用可回溯率低于阈值触发重检索
- **防漂移**：STORM 式大纲先行

## Out of scope

- groundedness 校验环（T04）
- 回流与消费侧 query（T05 / T06）
- Agent 被动注入 / 自动 recall（FR-007 / FR-009，后续切片）

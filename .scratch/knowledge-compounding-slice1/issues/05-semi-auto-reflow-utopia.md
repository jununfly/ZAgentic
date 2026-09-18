# 05 — 半自动回流 utopia 知识沉淀层（FR-006）

**Status:** ready-for-agent
**Blocked by:** 01 — 起 utopia 持久层地基；04 — Groundedness 后端校验环
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-006, Impl Decisions: 回流方式)

## What to build

把 T03/T04 产出的、已通过 groundedness 校验的报告（及其提炼的元认知：结论、方法论、反驳点、适用边界）**写回 utopia 知识沉淀层**。Phase 0 采用**半自动**方式：系统生成回流建议，经用户审阅/确认后写入——而不是全自动盲写。这是「复利闭环」的关键回边：知识第一次从一次性报告变成可累积的资产。

## Acceptance criteria

- [ ] 一份已校验报告可被提炼为「元认知条目」（结论/方法论/反驳/边界）并生成回流建议
- [ ] 用户在审阅后确认，条目写入 utopia 知识沉淀层，可后续检索
- [ ] 回流是「半自动」：未经确认不写入（Phase 2 再升自动）
- [ ] 回流率作为可观测指标可测（具体阈值在 T07 验收）
- [ ] 回流内容带来源 `[DOC_ID]` 引用，与原报告可追溯关联

## Key interfaces / decisions (from spec)

- **回流方式**：半自动（可审阅后确认）写回 utopia 知识沉淀层；Phase 2 升自动

## Out of scope

- 全自动回流（Phase 2）
- Agent 被动注入 / 自动 recall（FR-007 / FR-009，后续切片）
- zj 主动 query 的检索实现（T06）

# 06 — zj 主动 query 命中历史沉淀（FR-008）

**Status:** ready-for-agent
**Blocked by:** 01 — 起 utopia 持久层地基；05 — 半自动回流 utopia 知识沉淀层
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-008, Impl Decisions: 消费侧本切片范围 / 反向连接 R2b)

## What to build

实现消费侧的**主动 query** 闭环：zj 向系统提问（例如「我之前沉淀过哪些关于 X 的方法论/结论？」），系统从 utopia 知识沉淀层检索历史回流的元认知，返回**带引用**的答案，命中此前研究沉淀的内容。

这是证明「复利闭环成立」的最小消费形态——一次研究的结果，能在此后被主动召回并复用。

## Acceptance criteria

- [ ] zj 用自然语言提问，系统从知识沉淀层返回带 `[DOC_ID]` 引用的答案
- [ ] 二次 query 能命中首次研究回流的元认知（证明沉淀被复用）
- [ ] 答案附带可点击/可核对的来源回溯
- [ ] 消费侧 recall 作为可观测指标可测（具体阈值在 T07 验收）
- [ ] 当无相关沉淀时，明确返回「无命中」，不编造

## Key interfaces / decisions (from spec)

- **消费侧本切片范围**：仅 zj 主动 query 打通证闭环；Agent 被动注入 (FR-007) 与自动 recall (FR-009) 留后续
- **反向连接 R2b**：research-agent 产出新报告时轻量回溯已有元认知留雏形；完整自动 recall 留 Phase 2

## Out of scope

- Agent 被动注入经 MCP 检索共享记忆（FR-007，后续切片）
- 完整自动 recall / 反向引用（FR-009，Phase 2）
- 多设备 query 同步（FR-014，后续切片）

# 07 — Seam 1 + Seam 2 端到端验收（门禁）

**Status:** ready-for-agent
**Blocked by:** 04 — Groundedness 后端校验环；05 — 半自动回流 utopia 知识沉淀层；06 — zj 主动 query 命中历史沉淀
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (Testing Decisions / §9.1 MVP 验收列)

## What to build

建立 Slice 1 的两道最高层测试 seam，并作为**发布门禁**——三项指标**同时达标**才算 Slice 1 通过。

- **Seam 1（端到端管线）**：给定「目标 + 私有材料」→ 产出带 `[DOC_ID]` 引用的报告；断言 **引用可回溯率 ≥ 90%** 且 **groundedness ≥ 0.8**。
- **Seam 2（回流/查询往返）**：首次报告 → 半自动回流 utopia → 二次 zj query 命中历史沉淀并返回带引用答案；断言 **消费侧 recall ≥ 50%**（回流率 ≥ 50% 半自动口径下达标）。

只测**外部行为**（输入 → 可观测输出），不测实现细节（chunk 大小 / 重排模型 / LLM 供应商）。

## Acceptance criteria

- [ ] Seam 1 自动化通过：引用可回溯率 ≥ 90% 且 groundedness ≥ 0.8
- [ ] Seam 2 自动化通过：回流率 ≥ 50% 且消费侧 recall ≥ 50%
- [ ] 三项指标（可回溯率 / groundedness / recall）在仪表盘可见、可复跑
- [ ] 测试只依赖外部行为契约；更换 LLM 供应商 / 重排模型不需要改测试
- [ ] 任一指标不达标时，门禁明确失败并报告缺口

## Key interfaces / decisions (from spec)

- **好测试标准**：只测外部行为（输入→可观测输出），不测实现细节
- **复利度量埋点**（最小集）：跨任务引用复用率、知识体增厚速率、维护负担指数、回流采纳率、冲突/漂移检出率；至少打通 Seam 2 所需最小仪表盘
- **验收口径**：Metrics→Benchmarks 分离，三项指标同时达标才算通过

## Out of scope

- 全量回归 / 性能压测（后续 Phase）
- 多 Agent / 多人场景的验收（FR-013 / FR-014，后续切片）

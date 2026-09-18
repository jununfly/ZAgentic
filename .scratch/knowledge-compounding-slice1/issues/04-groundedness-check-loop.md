# 04 — Groundedness 后端校验环（FR-005）

**Status:** ready-for-agent
**Blocked by:** 03 — Decompose + Retrieve + Cite + Report
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-005, Impl Decisions: Groundedness 如何做)

## What to build

在 `zj-deep-research` 管线末端加一个**后端校验环**：在报告交付前，后端独立校验每句论断是否真的被其 `[DOC_ID]` 引用支撑；整体 **groundedness ≥ 0.8** 才放行报告，否则打回重检索/重写。这是 commerical deep research 普遍缺失的环节（其 groundedness 仅 0.3–0.6），是知识复利工具可信赖的前提。

## Acceptance criteria

- [ ] 报告在 groundedness ≥ 0.8 时才被放行交付
- [ ] 低于阈值的报告被拦截并触发重检索/重写（不静默放行）
- [ ] 校验在「后端」独立进行，不依赖前端/用户肉眼检查
- [ ] groundedness 分数作为可观测指标可测、可记录
- [ ] 虚构/无支撑的引用被识别并剥离或标注

## Key interfaces / decisions (from spec)

- **Groundedness 如何做**：后端校验环，≥0.8 才放行报告；商用 deep research 仅 0.3–0.6，必须加

## Out of scope

- 回流与消费侧 query（T05 / T06）
- 自动 recall / 反向引用（FR-009，Phase 2）
- 多 Agent 协同校验（FR-013，后续切片）

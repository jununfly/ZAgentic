---
doc-kind: design
authority: primary
authority-id: design.roadmap-radial-render
model-elements: [entity.design]
---

# Roadmap 轻量视图：焦点辐射渲染设计（zj-roadmap-driven）

## Question

`render` 的轻量 Markdown 视图如何在不膨胀 Human 屏幕、不引入新存储原语的前提下，
同时回答「我在哪（上下文）」与「现在干什么（焦点 + 下一步）」？

## Scope

本文拥有轻量视图的辐射渲染不变式：焦点辐射（祖先链必现 + 焦点子树下钻 + 非焦点兄弟
折叠计数）、异常折叠（completed 折叠 / in_progress·blocked·open_question 强制展开）、
ready 小节进 md，以及配套的 `tree --anchor` CLI 语义。命令语法与实现以
[CLI 参考](../../../skills/codebase-docs/zj-roadmap-driven/references/roadmap-cli.md)
与 `skills/codebase-docs/zj-roadmap-driven/scripts/roadmap.py` 为准；视图的产品定位与同源多投影由
[Human 视图产品设计方案](visual-review-product.md)拥有，本文只沉淀渲染层的设计决策与理由。

> 上游过程计划：`skills/codebase-docs/zj-roadmap-driven/references/radial-render-plan.md`（D1–D4 于 2026-09-16 拍板落地的
> 改造 PR 计划，仍随 skill 入库以保留改造现场）。本页只抽取其 durable 设计决策、替代方案与
> 不变式；评审记录 / 验收矩阵 / 提交策略 / 带日期的 issue 映射均属产生它们的 commit / PR，
> 不在本页复述（一处事实一个家）。

## 要治的病

旧 `render_light_section` 把两个正交旋钮硬拼成一个视图：全局常量 `depth=2` 从根展开，
焦点单独在下方 `focus_detail` 补一刀。焦点在第 1 层时整棵树摊开、浅路线图信息过载；
焦点在第 5 层时根树根本到不了焦点，只能靠下方单独展开 →「焦点在树里找不到、只在下方
出现」。Human 要同时理解「我在哪」和「现在干什么」，固定 depth 只解决后者的一半。
`ready` 就绪集又只活在 CLI（`ready` / `next`），不进 md，是 Human readiness 的真实缺口。

解法不是加更多图，而是用数据模型**已具备**的辐射原语重新组合渲染：`get_path`（祖先链）、
`get_tree(root_id, max_depth)`（子树）、`get_siblings`、`get_current_focus`、`ready_nodes`、
`next_nodes`。无需新增任何存储字段。

## 核心决策（均已拍板）

- **D1 — CLI 用 `--anchor <id>` 而非 `--focus`**：`focus` / `context` 已是独立顶层命令，
  给 `tree` 加 `--focus`/`--context` 会与之撞名、造成文档歧义。`--anchor` 语义 =「以该节点
  为锚渲染辐射视图」。缺省值 = `get_current_focus()`，裸 `--anchor` 等价于锚定当前焦点。
  `--context` 不加到 `tree`：祖先链本身就是 context，深一层的来龙去脉仍走 `context <node>`，
  两者组合已覆盖需求。
- **D2 — 无焦点回退 depth=2**：`get_current_focus()` 为空时回退 `get_tree(max_depth=2)`，
  与历史快照**逐字节一致**，保住所有无焦点控制测试与「无状态 md 不变」的前提。
- **D3 — ready 小节进 md**：轻量视图尾部加「下一步可开工（ready 前 3）」，补齐 Human
  readiness 缺口；ready 为空时整节不输出（守住空状态不变量）。全量视图（`section --all`）
  不受影响。
- **D4 — 计划文档纳入 PR 并 enrich**：原始 PR 计划随代码入库以留现场，durable 设计再沉淀到
  本页。

## 辐射视图不变式

1. **祖先链必现**：从根到焦点的 `get_path(focus_id)` 全展开（回答「我在哪」）。
2. **焦点子树下钻**：焦点自身按 `focus_subtree_depth` 下钻（回答「这摊事多深」）。
3. **非焦点兄弟折叠计数**：每个祖先层的非焦点兄弟折成一行计数（「该层还有 K 个兄弟，
   M 个 in_progress ▸」），不展开。
4. **异常折叠**：某节点全部子孙 `completed` → 折叠为一行「已完成（折叠 N 项）▸」；
   `in_progress` / `blocked` / 含 `open_question` → 强制展开到叶子或 N 层；过深 pending 子树
   截断并提示 `run tree {nid} --depth 2 for full view`。
5. **未知 `focus_id` 优雅降级**：返回「(节点 {id} 不存在)」，不崩。

## 与同源多投影 / 跨载体的一致性

- **模板只写一份契约**：径向视图复用 `nodes / edges / blocks / debts / owners` 数据访问器，
  与全量视图同款模板，因此两 carrier（单文件 JSON / SQLite）的 `render_light_section()` 与
  `get_tree_radial()` 输出**逐字节相等**。这条跨载体字节相同是硬约束，由 skill 侧测试
  `test_radial_render.py`（`RadialCrossCarrier`）与既有 `test_cross_carrier_render.py` 共同钉住。
- **不进主视图的东西守边界**：边（依赖 / 上下文）默认不进 md，只服务调度或 Agent 上下文
  ——与「树 = Human 主视图；carrier = 事实源；md = 只读派生视图」的核心不变式一致
  （见 [并发与依赖模型](concurrency-model.md)）。
- **`datetime.now()` 的 `updated` 字段**跨载体测试可容忍，非渲染层的权威输出，不纳入
  径向改动。

## 参考

- [Roadmap skill](../../../skills/codebase-docs/zj-roadmap-driven/SKILL.md) 核心原则 #2
- [Human 视图产品设计方案](visual-review-product.md) — 辐射视图的产品定位与场景锚定
- [并发与依赖模型](concurrency-model.md) — 视图护栏与不进 md 的元素
- 原始 PR 现场：`skills/codebase-docs/zj-roadmap-driven/references/radial-render-plan.md`（已落地的改造计划，未迁移）

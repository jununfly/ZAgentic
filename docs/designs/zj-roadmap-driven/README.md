---
doc-kind: design
authority: supporting
authority-id: design.roadmap-driven-index
model-elements: [entity.design]
---

# zj-roadmap-driven 设计文档索引

本目录集中 `zj-roadmap-driven` 的 durable 设计权威页。运行时行为、命令语法与数据模型仍以
skill 内的 SKILL.md 与 `references/` 为准（runtime closure：skill 运行期只读自家块，不回链
本目录）；本目录只回答「为什么这样设计、替代方案与代价、当前不变式」。使用层细节与代码
实现不在这里复述（一处事实一个家）。

## 设计分册

| 文档 | 拥有的问题 | authority-id |
| --- | --- | --- |
| [并发与依赖模型](concurrency-model.md) | 多 Agent 并发写、依赖边、租约、carrier 演进、错误码/退出码纪律 | `design.roadmap-concurrency-model` |
| [执行图（trace layer）](execution-graph.md) | 执行期涌现的发现/上下文如何记录而不膨胀 Human 视图、不污染地图 | `design.roadmap-execution-graph` |
| [reconciliation 与原子 ChangeSet](reconciliation.md) | 六概念压在单一 children 结构的去重/原子提交/拓扑改动 | `design.roadmap-reconciliation` |
| [焦点辐射渲染](radial-render.md) | 轻量视图如何同时回答「我在哪」与「现在干什么」 | `design.roadmap-radial-render` |
| [Human 视图产品设计方案](visual-review-product.md) | 可视化阅读/焦点对齐的产品层四场景与同源多投影 | `design.roadmap-visual-review-product` |
| [Human 视图技术设计方案](visual-review-technical.md) | 由确定性脚本从机器可读 SoT 生成的技术层切片（**勿手改**） | `design.roadmap-visual-review-technical` |
| [机器可读 SoT](visual-review.spec.json) | 产品/技术视图的单一事实源，technical 页由此再生 | —（非 design 页，generator 输入） |
| [Wayfinder↔roadmap carrier seam](dual-mode.md) | plan→track 配对、载体选择、phase handoff 接缝 | `design.wayfinder-roadmap-carrier-seam` |

## 阅读顺序建议

1. 想理解整体不变式（树=主视图、carrier=事实源、md=派生视图）→ 并发与依赖模型。
2. 想理解执行期图模型与投影 → 执行图。
3. 想动 render/tree 视图 → 焦点辐射渲染 + Human 视图产品设计方案。
4. 想改可视化投影 → 先改机器可读 SoT，再 `render`+`verify`，技术设计页随之再生。
5. 与 wayfinder 的配对/交接 → dual-mode。

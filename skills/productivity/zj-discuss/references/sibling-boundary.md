# 兄弟技能集成与外部能力边界

> 本文件从 `SKILL.md` 下沉而来，是 discuss 与兄弟技能 / 外部能力的复用边界规范。
> SKILL.md 仅保留指针。

## Integration with sibling skills

> 边界原则：**引用而非重做。** discuss 做薄编排层，凡兄弟技能已覆盖的能力一律调用，
> 不在 discuss 内重实现（防逻辑漂移）。

- **`zj-steelman`（辩护）vs `zj-discuss-view`（结构错位）—— 不变式互斥，禁止共享实现。**
  discuss-view 的 role 视角 = **协作式结构错位**（丰富讨论：B 问排期/风险、C 问用户/价值、
  A 问边界/不变式，互补而非对抗）；zj-steelman = **防御式辩护**（检验提案可辩护性，判
  Strong/Adequate/Weak）。前者永不攻击、后者专司辩护。故 **discuss-view 不得内置 defend 逻辑**；
  对「提案是否站得住」类子问题，discuss 改调 `zj-steelman` 取其判定。

- **`zj-handoff`（压缩契约）⊇ `discuss-briefing`（受控切片）。** briefing := handoff 输出契约
  （引用不重复 + suggested-skills + 落 temp 目录）＋ `[role-stance 章]` ＋ `[强制 Read 原文令]`。
  discuss **不重造压缩逻辑**，handoff 契约为其基础子集；仅追加 discuss 专属两行头。

- **`zj-docs-ontology`（Human-owned 治理）— discuss 阶段 2 只吐指针，绝不自行分类/迁移。**
  discuss 阶段 2 仅产出 `<conclusion>` + `<suggested-category>` + `<pointer>`，随即移交
  `zj-docs-ontology`；**分类、提案迁移、链接/权威校验一律由 docs-ontology 在其 Human 确认闭环内
  完成。discuss 不得运行 docs_governance.py，不得决定最终分类。**

- `zj-grilling` — use beforehand to sharpen the core problem framing.

## 外部能力集成边界（选择性复用）

> 全局决策 = **C（选择性复用）**：外部范式只作**结构借鉴**，
> `zj-discuss` 方法体系始终是自有主体。边界写进 SKILL 而不只写进 design 文档，
> 是为了防止「顺手引一个依赖」把方法所有权让渡出去。

| 外部能力 | 边界 | 为何这样划定 |
| --- | --- | --- |
| 跨 provider 评审（如外部 `/codex` 式范式） | **组件引用** —— 推荐更强隔离时使用；discuss 内不实现 provider 路由 | 引入路由即引入运行时，会把方法论变成编排器 |
| learnings / 经验持久化 | **薄层复用** —— 可借鉴其机制，但必须是可移除薄层 | 任何承载方法状态的适配层都等于拥有了主体 |
| 上游 digest（如 2KB digest） | **voice-only** —— 只覆盖表达语气，不覆盖方法体系 | 它不表达结构立场 / R×O，覆盖不到本方法的语义点 |

**否决项（不再复议）：** 会话编排运行时 / router / suite 化 —— 会让适配层拥有主体方法
状态，按决策模型重分类为 D。`scripts/launch_pack.py` 是这条红线的产物边界：它写文件，
不发起会话。

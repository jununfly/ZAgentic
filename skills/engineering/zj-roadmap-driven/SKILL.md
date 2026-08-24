---
name: zj-roadmap-driven
title: "zj-roadmap-driven"
description: "路线图驱动开发与验收——以树形 roadmap 和决策记录帮助 Agent 与 Human 保持共享地图；在节点执行前区分产品实现路线与 legacy/技能验收路线，避免把验收场景误当成项目开发。支持本地 JSON 与 roadmap bundle，并与 zj-wayfinder、zj-to-tickets 配合。"
triggers:
  - 路线图驱动
  - roadmap driven
  - 导航式开发
---

# zj-roadmap-driven — 路线图驱动开发

**目标：** 在复杂任务场景中，用路线图（树形节点 + 决策记录）作为 Agent 和 Human 的共享心智模型。避免持续对话导致的目标偏离——每一步都在地图上留下足迹。

**核心原则：**
1. **存储载体决定事实源**——普通路线图使用单 JSON；大型路线图显式使用 roadmap bundle，由 manifest、节点/决策 shards 和 append-only history 共同构成事实源。Agent 必须通过 CLI 读写，禁止直接编辑这些文件。
2. **Markdown 是轻量渐进式视图**——只暴露树形概览（depth=2）+ 当前施工焦点。Human 一眼看清进度，不占满上下文；Markdown 永远不能反向导入事实源。
3. **每个节点有编号**（1, 1-1, 1-1-1, …），方便 Human 和 Agent 快速定位
4. **每个节点有状态 checkbox**（[ ] / [~] / [x] / [!]），一眼识别进度
5. **决策随节点落盘**（JSON 中），形成可追溯的决策历史。md 只展示焦点节点的决策。

## 工作流

```
Human 提方向 → Scope gate → Agent 建/读 roadmap → Agent 渲染轻量 section 到 md
    ↓
Agent 每做一个决策 → 调用 `decide` 写入节点 → 调用 `render` 更新 md
    ↓
Human 看 md 里的树 + 当前焦点 → 确认或纠正 → Agent 继续
    ↓
Agent 完成一个子任务 → 调用 `update` 打勾 → 调用 `render` 更新 md
    ↓
Agent 需要局部 → 调 `tree` / `get` / `focus` / node-scoped `decisions`
Agent 需要全貌 → 调 `section --all`（显式导出）
Agent 需要选择载体 → 调 `recommend-storage`（只读建议，不自动迁移）
```

## Scope gate — before any node write or project edit

先判断当前 roadmap 的角色，再把节点置为 `in_progress` 或修改项目文件：

- **Product execution**：Human 明确要求实现、交付或发布目标项目；节点执行可以在项目规则允许的范围内修改目标项目。
- **Acceptance/evaluation**：Human 将 roadmap 说成 legacy、probe、test、技能验收，或明确项目不继续完成/发布；节点是验证技能的场景。可以按请求更新 roadmap 元数据，但目标项目代码、依赖和产品文档保持只读，除非另有明确授权。
- **Unclear/mixed**：在任何写操作前只问一个范围问题，不靠节点 label 猜授权。

`开始 1-3-1` 只表示操作该节点；只有完成 scope gate 后，才决定它是否包含目标项目实现。Agent 在 commentary 中声明分类，并把分类对应的 artifact 作为完成标准。

Acceptance/evaluation 路线按以下顺序运行：

1. 明确被验收的 artifact（skill、CLI、rendered view 或临时 fixture）。
2. 尽量在隔离/临时 fixture 上执行命令，保留可复核输出。
3. 将 roadmap 试验结果与目标项目完成度分开报告；probe 通过不等于项目已实现或可发布。

**关键规则：**
- **Agent 每次完成实质工作后，必须 `render` 更新 md 文件。** 这是 Human 看到进度的唯一窗口。
- **Agent 做任何方向性决策前，先 `decide` 记录。** 决策不落盘 = 没发生。
- **Human 随时可以通过 `tree` + `decisions` 了解全貌，无需翻对话历史。**
- **Agent 禁止直接 Read/Edit md 的路线图 section。** 只能通过 CLI 操作 JSON，再 render 输出。
- **Agent 禁止并行执行同一 JSON 的写类命令。** CLI 会用 per-roadmap lock 串行化写入并等待最多 10 秒，但 Agent 仍应按顺序调用 `init/add/update/delete/decide/render/link`。

## 按需参考

加载本 skill 后，先按当前分支读取对应 reference，避免把所有资料一次性带入上下文：

- 需要理解节点字段、状态/模式、命名或父子同步 → [路线图数据模型](references/roadmap-data-model.md)
- 需要执行 CLI、查看示例、定位脚本或检查锁行为 → [CLI 参考](references/roadmap-cli.md)
- 需要选择本地/tracker 载体或理解 wayfinder 衔接 → [双模式与组合关系](references/dual-mode.md)

## 与 zj-grilling 配合

`zj-roadmap-driven` 是 `zj-grilling` 的搭档：
- `zj-grilling` 负责逐层拷问，到达决策树叶子节点
- `zj-roadmap-driven` 负责把每层决策沉淀到路线图 JSON + md section
- 两者交替：grill 一个 Q → roadmap 记录决策 → grill 下一个 Q

## Notes

- 单文件模式的 JSON、bundle 模式的 canonical shards 都是事实源。所有数据操作必须通过 CLI，**禁止 Agent 直接 Read/Edit 它们或 md 的路线图 section。**
- md section 由 `render` 命令完全重写，手动修改会被覆盖。
- CLI 写类命令按顺序执行；其余数据模型、命令和锁细节见对应 reference。
- 如果路线图 JSON 不存在，Agent 应先用 `init` 创建；无 `import` 命令，md 不能反导回 JSON。
- `recommend-storage` 只读取事实源和派生文件，输出 `keep-single`、
  `consider-bundle`、`recommend-bundle` 或 `keep-bundle`；它不会写入索引、
  迁移载体或改写 Markdown。需要转换时，仍必须显式调用 `migrate --to bundle`。

---
name: zj-roadmap-driven
title: "zj-roadmap-driven"
description: "路线图驱动开发与验收——以树形 roadmap 和决策记录帮助 Agent 与 Human 保持共享地图；在节点执行前区分产品实现路线与 legacy/技能验收路线，避免把验收场景误当成项目开发。支持单文件 JSON 与 SQLite 两种载体（bundle 已弃用 #140，仅可经 migrate 迁出），并与 zj-wayfinder、zj-to-tickets 配合。"
triggers:
  - 路线图驱动
  - roadmap driven
  - 导航式开发
---

# zj-roadmap-driven — 路线图驱动开发

**目标：** 在复杂任务场景中，用路线图（树形节点 + 决策记录）作为 Agent 和 Human 的共享心智模型。避免持续对话导致的目标偏离——每一步都在地图上留下足迹。

**核心原则：**
1. **存储载体决定事实源**——普通路线图使用单文件 JSON；大型路线图使用 SQLite（分片 + 稳健的并发/读放大治理），由 manifest、节点/决策 shards 和 append-only history 共同构成事实源。Agent 必须通过 CLI 读写，禁止直接编辑这些文件。bundle 已弃用（#140），现存 bundle 只能经 `migrate --to sqlite|single` 迁出，禁止新创建。
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
Agent 需要选择载体 → 调 `recommend-storage`（只读建议，只给出命令，不自动迁移）
Agent 需要换载体 → 调 `migrate --to single|sqlite`（显式；源文件不动，目标已存在则拒；`--to bundle` 已禁用，bundle 为弃用 carrier #140）
Agent 需要表达依赖 → 调 `edge add --type blocks|informs|supersedes|derives-from`
Agent 需要取活/看最长未完工链/看改动波及 → 调 `ready` / `critical-path` / `impact`（只读，不拿锁）

依赖是树之外的一层正交边：`blocks` 是硬依赖（不许成环，会返 `E_CYCLE`），
`informs` / `derives-from` 只是上下文与来源追溯，允许成环。删节点会级联删掉
触及它的边并报告条数——边不能比它的节点活得久。

`blocked` / `blocked_reason` 是**读取时从 `blocks` 边派生的，永不落盘**：
`get <node>` 在有未完成前驱时附带这两个字段（reason 是阻塞它的边 id 列表），
前驱一完成或边一删，同一次读里就消失；`tree` / md 渲染里同一个节点显示 `[!]`，
Human 视图与 Agent 视图不会对同一事实给出两个答案。`--status blocked` 被拒并返
回 `E_INVALID_STATUS`（退出码 1）——人写的 blocked 会与边推导出的 blocked 打架。

树的一行只装得下一个图标，装不下"被谁挡住"。所以当**有东西被阻塞**时，md 两个
视图都多出一小节阻塞链，每条说清哪个节点被哪几条边挡住（含边 id 与前驱）：
`render` 写进关联 md 文件时把它折进 `<details>`（依赖图不占视线），`section`
把它打平成 `### 阻塞链`（那是给管道用的）。最多列 5 个节点，其余写明数量不静默
丢掉。**没有任何东西被阻塞时，两个视图的输出一个字节都不变**——这条有控制例守着，
不是"应该差不多"。

调度查询（#81，`ready` / `critical-path` / `impact`）是**读取时从 `blocks` 边派生**的，
只读、不拿整图锁：`ready` 是"现在能开工哪些节点"（pending 且无未完成 `blocks` 前驱，
`in_progress` 不算），`critical-path` 是"最长的未完工 `blocks` 链"（已完成节点不计入、
平局取最小起点 id），`impact <node>` 是"改这个节点会波及哪些下游"（只沿 `blocks` 顺流、
不含自身、含已完成下游以预警返工）。三者边界与 `blocked` 一致——只有 `blocks` 参与；
三个载体输出逐字节相同。

两个载体（single-file JSON、sqlite）对边的行为完全一致，同一套验收跑两遍（bundle 已弃用 #140，仅作迁出源）。
bundle（已弃用 #140）把边存在 `edges/<id>.json`（索引 `index.json` 只有 from/to 邻接表，是纯冗余，
不是事实源），节点分片里不反向存边 id，`migrate --to <carrier>` 会把边一起带走。
三个载体的两个 Markdown 视图（`render` 写进 md 的轻量视图与 `section` 的导出视图）
共用同一份模板，逐字节相同——模板曾各抄一份并漂移，抄两份本身就是缺陷。
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
- **Agent 每次完成实质工作后，必须自动 `render` 更新 md 文件。** 这是 Human 看到进度的唯一窗口，也是 sqlite carrier 下「源不可读但 md 可审」的硬保证——**自动 render 是默认且必需**，human 手动触发 `render` 仅作补充 / 兜底手段，**不可作为主依赖**。
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

- 单文件模式的 JSON、SQLite 的存储都是事实源（bundle 模式已弃用 #140，其 shards 仅作迁出源）。所有数据操作必须通过 CLI，**禁止 Agent 直接 Read/Edit 它们或 md 的路线图 section。**
- 探索型节点（`mode: explore`）应设**结构预算**：`--max-children N` 限它能长出几个子节点，`--max-rounds N` 限它能被开工几次。触顶时 `add` / 重开以 `E_BUDGET_EXCEEDED`（退出码 3）失败且不落盘——这是"探索无界"的刹车，不是错误。`--exit-criteria "判据"` 记录完成判据（可重复追加），CLI 只存不判，检查由 Human/Agent 对照执行。
- md section 由 `render` 命令完全重写，手动修改会被覆盖。
- CLI 写类命令按顺序执行；其余数据模型、命令和锁细节见对应 reference。
- 如果路线图 JSON 不存在，Agent 应先用 `init` 创建；无 `import` 命令，md 不能反导回 JSON。
- `recommend-storage` 只读取事实源和派生文件，**但从不动手**：它输出 `keep-single`、
  `consider-sqlite`、`keep-sqlite` 或 `deprecate-bundle`（现存 bundle 时附 `migrate <path> --to sqlite` 命令）
  `keep-sqlite`，不写索引、不迁 carrier、不改写 Markdown。给出迁移目标的那些档会
  在 `recommendation.command` 里附上**那条显式命令**（`migrate <path> --to <carrier>`）
  让人去跑——把命令写出来 ≠ 替人跑。
- 换 carrier 只能靠 `migrate <path> --to single|sqlite`（`--to bundle` 已禁用，bundle 为弃用 carrier #140）：源文件一个字节都不改，
  目标已存在或与源同 carrier 都直接拒绝。**没有任何命令会自动替你换事实源**，所以
  "现在哪个产物是事实源"永远是你上一次显式做出的那个。租约与它的审计事件会跟着一
  起走（带过去的那把锁在新 carrier 上仍然生效）。

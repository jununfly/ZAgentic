---
name: zj-roadmap-driven
description: >-
  路线图驱动开发与验收：以树形 roadmap（编号节点 + 状态 checkbox）和随节点落盘的决策记录，
  作为 Agent 与 Human 的共享地图；施工进度靠 `render` 出的 md 视图回看。节点执行前先做 scope gate，
  区分产品实现路线与 legacy/技能验收路线，避免把验收场景误当成项目开发。
  Use when 用户提到 路线图驱动 / roadmap driven / 导航式开发 / 进度地图 / 节点推进 / plan tree，
  或需要把长任务拆成可追踪的树形计划并沉淀决策。载体支持单文件 JSON 与 SQLite，
  与 zj-wayfinder（规划）、zj-to-tickets（转换）配合。
triggers:
  - "路线图驱动"
  - "roadmap driven"
  - "导航式开发"
  - "进度地图"
  - "节点推进"
  - "plan tree"
source: zagentic

---

# zj-roadmap-driven — 路线图驱动开发

## Quick start

```bash
# carrier 落在 docs/plans/（ADR 0010：过程/计划类产物区）；ROADMAP.md 与之同目录。
python "$SKILL_DIR/roadmap_cli.py" init docs/plans/roadmap.json --title "项目名" --md-file "ROADMAP.md"
python "$SKILL_DIR/roadmap_cli.py" add docs/plans/roadmap.json 1 "第一步" --status in_progress
python "$SKILL_DIR/roadmap_cli.py" decide docs/plans/roadmap.json 1 "后端用什么？" "Python + FastAPI"
python "$SKILL_DIR/roadmap_cli.py" update docs/plans/roadmap.json 1-1 --status completed
python "$SKILL_DIR/roadmap_cli.py" render docs/plans/roadmap.json   # 每次实质工作后必跑：md 是 Human 唯一窗口
```

> 落盘约定（ADR 0010）：carrier + `ROADMAP.md` 留在 `docs/plans/`（git 跟踪、计划 close-out 后清理）；
> 租约侧车（`<carrier>.leases.json`）与 per-roadmap lock 目录属"余物"，自动落到
> `<proj>/tmp/skills-outputs/roadmap-driven/<stem>/`（gitignore 覆盖，不进提交）。`--md-file` 缺省即 `ROADMAP.md`。

`add` 的父节点是根 `1`，子节点按 `1-1`、`1-1-1` 自动编号。完整命令见 [CLI 参考](references/roadmap-cli.md)。

当前 reconciliation preview 只接受显式 `obligation_key`：先用确定性 key
匹配全图 plan 节点，再输出 `covered`、`refine`、`reshape`、`novel`、
`dismiss` 或 `unresolved` proposal。`novel` 必须由 trace 的 `evidence`
支撑；多个 exact match 只提出 Human 问题，不自动创建 WorkItem。Human
答案通过 inline JSON 传给 `--answer`：`dismiss` 必须有 reason，完成项的
`refine` 支持 reopen/supersede/noop，`reshape` 携带闭合 ChangeSet changes。
可以用重复的 `--trace` 一次生成批量 preview；`reconcile` 本身只读，单条
ChangeSet 经 digest 审批后显式 `apply`，重复 obligation 的 Trace 批次经
`apply-batch` 合并为一个 WorkItem 并保留所有来源。

Placement 迁移也是显式的：
`migrate-placements <source> --output <target>` 按目标扩展名选择 JSON 或
SQLite carrier，把旧的 ordered `parent`/`children` 投影成 primary
Placement，并保留源文件字节不变。`placement list <roadmap>` 只显示
Placement 及其 Work/parent 的 display-id 投影；`outline_rank` 只表达展示顺序，
不表达调度或因果关系。已有 roadmap 可用 `placement add-reference` 添加共享
Work 的第二个 outline context，用 `placement move` 移动 Placement；这两者不复制
WorkItem 的状态、决策或租约。

通用拓扑 ChangeSet 可用 `changeset preview/apply` 走同一套候选状态校验，
支持 `work.create/patch/coalesce/supersede`、Placement put/move/reference、
Edge put/remove/replace、Decision append 和 Trace disposition。已迁移的
roadmap 可用 `migrate-types --output` 将带 children 的 plan 节点分类为
`group`、叶节点分类为 `work`；有 Placements 时 `tree`、`section`、`render`
从 Placement 事实投影，并以文本 `↪ reference (same WorkItem, not a copy):` 显示引用上下文（`↪` 仅为冗余视觉提示，语义由文字承载）。
ChangeSet 也可带 `--scope <node_uid>`；preview 会展开 Edge/Placement 的
不透明引用并拒绝所有越出该子树的 Work、Decision、Trace 或拓扑端点，scope
同时进入 approved digest。

**目标：** 在复杂任务场景中，用路线图（树形节点 + 决策记录）作为 Agent 和 Human 的共享心智模型。避免持续对话导致的目标偏离——每一步都在地图上留下足迹。

**核心原则：**
1. **存储载体是过程状态的事实源**——普通路线图使用单文件 JSON；大型路线图使用 SQLite（节点 / 决策 / 边 / 租约 / history 各归一表，WAL 并发）。它权威回答当前计划、进度和下一步，不回答产品行为、架构、发布或正确性。Agent 必须通过 CLI 读写，禁止直接编辑这些文件。
2. **Markdown 是轻量渐进式视图**——焦点辐射：有焦点时「祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数」，无焦点回退根树 depth=2；completed 子树折叠、in_progress/blocked/open_question 强制展开；尾部含 ready 小节。Human 一眼看清进度与下一步，不占满上下文；Markdown 永远不能反向导入事实源。
3. **每个节点有编号**（1, 1-1, 1-1-1, …），方便 Human 和 Agent 快速定位
4. **每个节点有状态 checkbox**（[ ] / [~] / [x] / [!]），一眼识别进度
5. **决策随节点落盘**（JSON 中），形成可追溯的决策历史。md 只展示焦点节点的决策。

## 权威边界 — process-state only

Roadmap 可以决定接下来执行什么；产品行为、架构、发布状态和正确性必须由代码、测试、运行时结果、契约、design 或 ADR 建立。节点打勾只表示过程状态，不是这些长期事实的证据。

当 roadmap 中的结论需要进入代码或长期文档时，先把结论和独立证据提炼到 ADR、design、contract 或 runtime evidence，再让代码/长期文档引用该持久权威。依赖方向保持 `roadmap → 持久权威 → code/docs`。

`render` 与 `section` 会在所有 Markdown 视图中写入 `zj-roadmap-authority/v1` 权威信封。close-out 和 CI 运行：

```bash
python "$SKILL_DIR/roadmap_cli.py" authority-check <project-root> [--exclude <path>]...
```

命令以稳定的 `E_PROCESS_AUTHORITY_LEAK path:line` 拒绝代码/长期文档直接引用过程产物，以及把节点完成状态直接写成 proof/evidence。治理文档确需展示反例时，只在该行使用 `roadmap-authority-allow: governance-example`；该例外不跨行生效。

扫描对象只限**可能承载长期事实的文件**。过程态自身不是泄漏：默认跳过 `docs/plans/`、`.git/`、`.workbuddy/`（append-only 记忆日志）、`node_modules/`、`tmp/`，以及 Roadmap carrier 事实源自身和带 `zj-roadmap-authority/v1` 信封的 Markdown 视图。项目若还有自己的过程态目录，用可重复的 `--exclude <path>` 声明（相对 project-root，可指向本次 checkout 尚不存在的路径）；它只覆盖声明的文件/目录，不能指向项目根或根之外，其余路径照常报错。**排除只改扫描范围，判定语义不放宽。**

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
Agent 需要换载体 → 调 `migrate --to single|sqlite`（显式；源文件不动，目标已存在则拒）
Agent 需要表达依赖 → 调 `edge add --type blocks|informs|supersedes|derives-from`
Agent 需要取活/看最长未完工链/看改动波及 → 调 `ready` / `critical-path` / `impact`（只读，不拿锁）
Agent 需要建议接下来开工哪个 → 调 `next`（只读；关键路径优先的就绪建议）
Agent 需要判断「现在要不要编排」 → 调 `signals`（只读编排信号；render 视图尾部也会折成摘要）

依赖是树之外的一层正交边：`blocks` 是硬依赖，`supersedes` 表示取代关系，
两者各自不许成环并会返 `E_CYCLE`。plan→plan 的 `informs` / `derives-from`
只是上下文与来源追溯，允许成环。trace 因果边另有更严格的层方向与无环规则：
`mainline`、`prompted-by`、跨层 `derives-from` 共同构成无环因果图，`reference`
允许成环。删节点会级联删掉触及它的边并报告条数——边不能比它的节点活得久。

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

调度查询（`ready` / `critical-path` / `impact`）是**读取时从 `blocks` 边派生**的，
只读、不拿整图锁：`ready` 是"现在能开工哪些节点"（pending 且无未完成 `blocks` 前驱，
`in_progress` 不算），`critical-path` 是"最长的未完工 `blocks` 链"（已完成节点不计入、
平局取最小起点 id），`impact <node>` 是"改这个节点会波及哪些下游"（只沿 `blocks` 顺流、
不含自身、含已完成下游以预警返工）。三者边界与 `blocked` 一致——只有 `blocks` 参与；
两个载体输出逐字节相同。

两个载体（single-file JSON、sqlite）对边的行为完全一致，同一套验收跑两遍：`migrate --to <carrier>` 会把边一起带走。
两个载体的两个 Markdown 视图（`render` 写进 md 的轻量视图与 `section` 的导出视图）
共用同一份模板，逐字节相同——模板曾各抄一份并漂移，抄两份本身就是缺陷。
```

**编排信号（只读，#245 切片 1）：** 初始 roadmap 就绪后，`signals` 与 md 尾部的
折叠小节负责让「现在可能需要编排」成为可发现、可确认的信号，而不是靠 Human
记得去触发。它只报 roadmap 自身可机械判定的结构状态（`completed` 仍挂
`open_question`、探索预算触顶、判据被显式清空），**不推断产品事实或外部证据**——
后者属于 process-state 权威边界之外。`signals` 不写入、不产出 ChangeSet；
`suggested_action` 只给可确认的 next-action 文本，**把命令写出来 ≠ 替人跑**，
决策仍用 `decide` 落盘、结构变更仍走 `changeset preview/apply`。
无信号时两个 Markdown 视图逐字节不变。命令细节见 [CLI 参考](references/roadmap-cli.md)。

**信号 → 候选 ChangeSet（#245 切片 2）：** `signals --as-changeset` 把信号转成**候选**
ChangeSet（仍是只读输出，不落盘）：每条信号先落一条 `decision.append`，`cleared_exit_criteria`
信号在显式给出 `--criterion <文本>` 时再补 `work.patch(exit_criteria)`。Human 拿到候选后
按需编辑（尤其判据内容，绝不替人猜），再走 `changeset preview/apply` 一次确认——复用既有
digest / `--idempotency-key` / `--scope`，不开第二套写入命令。该 flag 不增命令数。

## 只读可视化（viz/ 包，S0/S2 + S3/S4 切片）

把 roadmap carrier **只读**投影成同一份 view-ir 派生的多张视图：自包含 HTML（局部 DAG + 信息卡片 +
交互 + 边回溯）、Mermaid 文本等价物、S3 dependency 投影、S4 context 侧载包。**绝不回写 carrier**——
只消费 `nodes` / `edges`(blocks) / `debts` / `context` / `metadata.updated`，不修改任何传入数据
（只读不变式由 S0/S2 与 S3/S4 两组单测共同钉住，见 `tests/test_viz.py::TestS0ReadonlyContract`）。

设计要点：

- **确定性 DOI 选择**（非 LLM）：六权重加权 `T1 图邻近 0.30 / T2 阻塞关键 0.25 / T3 共享上下文 0.15 /
  T4 债务严重度 0.15 / T5 新鲜度 0.10 / T6 稳定性惩罚 0.05`（sum=1.0）。焦点自身 DOI=1.0；低于 θ 直接折叠。
- **θ 单一旋钮**（A 方案）：θ = 最低可见 DOI 下限；运行时按焦点下非强制项 DOI 分布取百分位
  （0.85/0.50/0.15）校准三档预设（overview/neighborhood/expand），避免写死阈值在部分焦点退化成等价。
- **三档 LOD + 阅读预算**：L2(4行)/L1(2行)/L0(1行)，预算硬上限 40 行；预算溢出**不静默**——
  `budget_folded` 显式报数，且 LOD 对 DOI **严格单调**（同 DOI 整桶一起升级，升不动即停手，禁止更低 DOI 越级）。
- **三类必备项强制可见**：焦点 + 阻塞前驱 + 后继 + 高严重度债务必进可见集 V，非焦点必备项恒为 L1。
- **债务一等建模**：显式 `debts` 优先；文本启发仅认 gap/todo/risk/sweep 一类关键词，**不把「有 notes」误判为债务**。
- **局部 DAG 渲染**：vendored `@dagrejs/dagre@3.1.3` UMD 提供分层坐标，自研 SVG 渲染；交互含多行标签、
  点击展开折叠项、重置视图、θ 滑块。几何经 `verify_geometry.mjs` 校验：全焦点零重叠、零裁切、复合节点界内。
- **anchor 信封**：`zj-roadmap-visual-review/v1` 携带 view-kind + carrier-stem + node-uid + carrier-revision，
  视图可追溯到源 carrier 而不污染 carrier。S4 起另有 `zj-roadmap-anchor/v1` 单行 token
  （CLI 输出、可复制、可解析），显示 id 从不作锚点。
- **S3 dependency 投影**：阻塞链取自 `doi.rev_bfs`（与 S1 view-ir 的 `selection.pdepth` 同一函数），
  `impact` / `critical-path` 与 `roadmap_cli.py` 同名查询逐行等价，测试直接 import `roadmap` 交叉断言。
  每条 blocks 边带 `edge_id`（carrier uid，缺失时确定性派生）与 `source`（edges 下标 + evidence-ref，
  缺失显式 `unknown`）；HTML 点击边回溯，Mermaid 等价物用边标签写 id。
- **S4 context side-pack**：单节点的决策 / trace / 边 / 证据引用 / 影响闭包打成独立 JSON，
  每条带 `source` 与 `evidence-ref`。主视图只内嵌展示字段白名单并留一个恒定入口，
  **上下文条目增长时 HTML 逐字节不变**。`revision` 不符时显式 stale 并写出刷新命令，
  `auto_refresh=false`——绝不执行、不静默重绘、不回写 carrier。

用法（不新增 `roadmap_cli.py` 命令，独立 `viz/` 包，避免触碰已冻结的 CLI 命令清单）：

```bash
# 主视图 + 可选 Mermaid / dependency 投影 / context 侧载包
# --dependency / --context 必须显式给路径（ADR 0010），不设默认、不落 cwd
python -m viz.cli <roadmap.json> --out X.html [--mermaid X.mmd] \
    [--dependency X.dependency.json] [--dependency-mermaid X.dependency.mmd] \
    [--context X.context.json] \
    [--focus <节点id>] [--theta 0.45] [--expand] [--json] \
    [--anchor <token>] [--expect-revision <rev>] [--context-radius 2]

# 拿旧 anchor 请求新视图：revision 不符时打印 STALE + 刷新命令（只写出、不执行）
python -m viz.cli <roadmap.json> --anchor 'zj-roadmap-anchor/v1|...' --context X.context.json

# 几何硬校验（Node）：加载真实 HTML，DOM 桩跑内嵌运行时，全焦点零重叠零裁切
node viz/verify_geometry.mjs X.html

# 出口判据 + 只读不变式单测（anaconda3 python3）
python -m unittest viz.tests.test_viz viz.tests.test_s3_s4 -v
```

演示语料：`demos/roadmap_viz_sample.json`（21 节点 + 15 条 blocks 边 + 3 条一等债务）。

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

- 单文件模式的 JSON、SQLite 的存储都是事实源。所有数据操作必须通过 CLI，**禁止 Agent 直接 Read/Edit 它们或 md 的路线图 section。**
- 探索型节点（`mode: explore`）应设**结构预算**：`--max-children N` 限它能长出几个子节点，`--max-rounds N` 限它能被开工几次。触顶时 `add` / 重开以 `E_BUDGET_EXCEEDED`（退出码 3）失败且不落盘——这是"探索无界"的刹车，不是错误。`--exit-criteria "判据"` 记录完成判据（可重复追加），CLI 只存不判，检查由 Human/Agent 对照执行。
- md section 由 `render` 命令完全重写，手动修改会被覆盖。
- CLI 写类命令按顺序执行；其余数据模型、命令和锁细节见对应 reference。
- 如果路线图 JSON 不存在，Agent 应先用 `init` 创建；无 `import` 命令，md 不能反导回 JSON。
- `recommend-storage` 只读取事实源和派生文件，**但从不动手**：它输出 `keep-single`、
  `consider-sqlite` 或 `keep-sqlite`，不写索引、不迁 carrier、不改写 Markdown。给出迁移目标的那些档会
  在 `recommendation.command` 里附上**那条显式命令**（`migrate <path> --to <carrier>`）
  让人去跑——把命令写出来 ≠ 替人跑。
- 换 carrier 只能靠 `migrate <path> --to single|sqlite`：源文件一个字节都不改，
  目标已存在或与源同 carrier 都直接拒绝。**没有任何命令会自动替你换事实源**，所以
  "现在哪个产物是事实源"永远是你上一次显式做出的那个。租约与它的审计事件会跟着一
  起走（带过去的那把锁在新 carrier 上仍然生效）。

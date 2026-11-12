---
name: zj-roadmap-driven
description: >-
  Maintain a decision-carrying execution roadmap as a shared map between Agent
  and Human, with a scope gate that keeps acceptance scenarios from being
  mistaken for product delivery. Use when the user asks for 路线图驱动 /
  roadmap driven / 导航式开发 / 进度地图 / 节点推进 / plan tree, or needs a long
  task split into a trackable tree with decisions recorded at each node.
source: zagentic

---

# zj-roadmap-driven — 路线图驱动开发

## Quick start

> **路径基准（安装态唯一约定）**：SKILL_ROOT 指**本 SKILL.md 所在目录的绝对路径**，
> 由加载本 skill 的 Agent 在装载时解析，再展开成下文的 `$SKILL_ROOT`。skill 是自包含
> 发布单元、安装位置不固定，而命令的 cwd 是目标项目（carrier 落在它的 `docs/plans/`）——
> **绝不假设 cwd 就是 skill 目录，也不依赖宿主注入未声明的环境变量**。
> 脚本一律以 `$SKILL_ROOT` 为前缀；`python -m viz.cli` 另需 `PYTHONPATH="$SKILL_ROOT"`。
> 同一约定适用于 [CLI 参考](references/roadmap-cli.md) 与 [viz 供应商说明](viz/VENDOR.md)。

```bash
# carrier 落在 docs/plans/（ADR 0010：过程/计划类产物区）；ROADMAP.md 与之同目录。
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" init docs/plans/roadmap.json --title "项目名" --md-file "ROADMAP.md"
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" add docs/plans/roadmap.json 1 "第一步" --status in_progress
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" decide docs/plans/roadmap.json 1 "后端用什么？" "Python + FastAPI"
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update docs/plans/roadmap.json 1-1 --status completed
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" render docs/plans/roadmap.json   # 每次实质工作后必跑：md 是 Human 唯一窗口
```

> 落盘约定（ADR 0010）：carrier + `ROADMAP.md` 留在 `docs/plans/`（git 跟踪、计划 close-out 后清理）；
> 租约侧车（`<carrier>.leases.json`）与 per-roadmap lock 目录属"余物"，自动落到
> `<proj>/tmp/skills-outputs/roadmap-driven/<stem>/`（gitignore 覆盖，不进提交）。`--md-file` 缺省即 `ROADMAP.md`。

`add` 的父节点是根 `1`，子节点按 `1-1`、`1-1-1` 自动编号。完整命令见 [CLI 参考](references/roadmap-cli.md)。

> **landing guard 锁定的纪律（不可下沉）**：本文件是仓库根
> tests/test_zj_roadmap_driven_landing.py 锁定的技能交付物。`权威边界`、
> `Scope gate`、`关键规则`（尤其自动 render、先 decide、禁直读 md、禁并行写）
> 与 `核心原则` **必须活在本 SKILL.md**，不得下沉到 references/。先例：
> zj-discuss 两次回归（#153、#167）——下沉后脚本层全绿、纪律静默丢失。
> `zj-write-a-skill` 的「顶文件 ≤100 行」对本方法论 skill 不可达，
> **纪律正确性优先于行数指标**；可下沉的只有设计与命令细节，它们已落到
> [可视化设计要点](references/viz-design.md) 与 [CLI 参考](references/roadmap-cli.md)。

高级拓扑（reconciliation / Placement / ChangeSet）与编排信号的语义见
[CLI 参考](references/roadmap-cli.md)；有 Placements 时树视图用
`↪ reference (same WorkItem, not a copy):` 标注共享 Work 的引用上下文，
不复制状态、决策或租约。需要时再读，不随本文件常驻上下文。

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
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" authority-check <project-root> [--exclude <path>]...
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

```

依赖边、`blocked` 派生、调度查询与双载体一致性的语义见 [路线图数据模型](references/roadmap-data-model.md)。


**编排信号（只读）：** `signals` 只报可机械判定的结构状态，不推断产品事实；不写入、
不产出 ChangeSet，**把命令写出来 ≠ 替人跑**。`--as-changeset` 只给候选，Human 编辑后
仍走 `changeset preview/apply` 确认。细节见 [CLI 参考](references/roadmap-cli.md)。

## 只读可视化（viz/ 包，S0/S2 + S3/S4 切片）

把 roadmap carrier **只读**投影成自包含 HTML（局部 DAG + 信息卡片 + 交互 + 边回溯）、
Mermaid 文本等价物、S3 dependency 投影与 S4 context 侧载包。**绝不回写 carrier**，
只读不变式由 S0/S2 与 S3/S4 两组单测钉住。设计要点（DOI 六权重 / θ / LOD 预算 /
anchor / S3 / S4）按需读 [可视化设计要点](references/viz-design.md)。

用法（独立 `viz/` 包，不新增 CLI 命令，避免触碰已冻结的 CLI 命令清单）：


```bash
# 主视图 + 可选 Mermaid / dependency 投影 / context 侧载包
# --out / --dependency / --context 一律显式给路径（ADR 0010），不设默认、不落 cwd；不传 --out 则不写 HTML
PYTHONPATH="$SKILL_ROOT" python3 -m viz.cli <roadmap.json> --out X.html [--mermaid X.mmd] \
    [--dependency X.dependency.json] [--dependency-mermaid X.dependency.mmd] \
    [--context X.context.json] \
    [--focus <节点id>] [--theta 0.45] [--expand] [--json] \
    [--anchor <token>] [--expect-revision <rev>] [--context-radius 2]

# 拿旧 anchor 请求新视图：revision 不符时打印 STALE + 刷新命令（只写出、不执行）
PYTHONPATH="$SKILL_ROOT" python3 -m viz.cli <roadmap.json> --anchor 'zj-roadmap-anchor/v1|...' --context X.context.json

# 几何硬校验（Node）：加载真实 HTML，DOM 桩跑内嵌运行时，全焦点零重叠零裁切
node "$SKILL_ROOT/viz/verify_geometry.mjs" X.html

# 出口判据 + 只读不变式单测（在 skill 目录外也要带上模块搜索基准）
PYTHONPATH="$SKILL_ROOT" python3 -m unittest viz.tests.test_viz viz.tests.test_s3_s4 -v
```

演示语料：`demos/roadmap_viz_sample.json`（21 节点 + 15 条 blocks 边 + 3 条一等债务）。

S1 只读入口：`--ir`（冻结 view-ir）、`--receipt`（Δ 重入，fail-closed）、`--delta`（增量清单），
路径一律显式给；`roadmap` 参数也接受 SQLite carrier。命令细节见 [CLI 参考](references/roadmap-cli.md)。

S1b 跨设备收据：`--device-id` + `--receipt-ttl` 同时给出才写 v2（否则沿用 v1 字节兼容），
`--merge-receipt` 导入对方收据；**receipt 是可丢弃的派生缓存**，上下文/hash 冲突或过期一律
fail-closed 全量回退，同步介质由 Human 显式给路径，不含网络协议。
S1c：`--merge-receipt` 可重复给多次导入多个 peer，任一不合格则整链 fail-closed；
后台自动同步调度按 RD::14 明确拒绝，不实现。

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
- 需要理解或修改只读可视化的信息选择/投影 → [可视化设计要点](references/viz-design.md)

## 与 zj-grilling 配合

`zj-roadmap-driven` 是 `zj-grilling` 的搭档：
- `zj-grilling` 负责逐层拷问，到达决策树叶子节点
- `zj-roadmap-driven` 负责把每层决策沉淀到路线图 JSON + md section
- 两者交替：grill 一个 Q → roadmap 记录决策 → grill 下一个 Q

## Notes

- 单文件 JSON / SQLite 都是事实源；所有数据操作必须通过 CLI，**禁止 Agent 直接 Read/Edit 它们或 md 的路线图 section。** md section 由 `render` 完全重写。
- 探索型节点（`mode: explore`）用 `--max-children` / `--max-rounds` 设结构预算，触顶以 `E_BUDGET_EXCEEDED`（退出码 3）失败且不落盘；`--exit-criteria` 只存不判，检查由 Human/Agent 对照执行。
- 写类命令按顺序执行；无 `import` 命令，md 不能反导回 JSON。`recommend-storage` 只读、只给命令，换 carrier 只能显式 `migrate`（源文件一个字节不改）——**没有任何命令会自动替你换事实源**，把命令写出来 ≠ 替人跑。
- CLI 语义、锁与载体细节见 [CLI 参考](references/roadmap-cli.md) 与 [路线图数据模型](references/roadmap-data-model.md)。

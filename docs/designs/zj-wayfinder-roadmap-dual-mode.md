# 双模式载体抽象：wayfinder ↔ roadmap-driven 组合技能对设计

> 状态：**done（已落地进技能本体）**
> 说明：本设计由 2026-08-11 起的前期预研笔记整合沉淀而来；预研稿已合并入本文并删除。
> 创建：2026-08-11 · 落地：2026-08-20

## 背景

`zj-wayfinder` 与 `zj-roadmap-driven` 是 ZAgentic 中两个互补的工程 skill（前者规划、后者跟踪）。在 2026-08-20 之前，两者的"底层事实"不对称：

- **`zj-wayfinder` 依赖 issue-tracker**。它把地图、决策票、阻塞边、frontier 查询放在 issue-tracker 上（GitHub/GitLab/本地 md），通过 `/zj-agents-init` 配置的 `Wayfinding operations` 段工作。优势是**便于 teamwork**（多 Agent 并发靠 claim + 原生 blocking 避让、人类在 tracker UI 可视化看到前沿），劣势是**依赖外部载体**、单点上下文分散在 tracker 上。
- **`zj-roadmap-driven` 无三方依赖**。它以本地单 JSON（普通路线图）或显式 sharded bundle（大型路线图）为事实源 + 纯 Python stdlib CLI，完全独立。优势是 **context 完整、Human 能通盘把握**（md 轻量视图 + 按需 bounded 查询），劣势是单写者、不擅长多 Agent 并发。

这一不对称，使得同一类"规划/跟踪"工作，在两种工作方式（团队协作 vs 个人全盘掌握）下不得不各用各的 skill，而无法在同一个 skill 内无缝切换。

## 目标

为了保持整个项目的一致性、完整性，**`zj-wayfinder` 和 `zj-roadmap-driven` 都应该同时支持两种情形**：

1. **依赖 issue-tracker（方便 teamwork）** —— 地图/路线/决策票落在 tracker 上，多人、多 Agent 共享、可视化、并发避让。
2. **不依赖 issue-tracker（方便 context 完整 + Human 通盘把握）** —— 以本地文件为事实源，普通模式用 JSON，大型模式用 bundle；Human 能离线按需纵览全貌、完全自包含。

两种模式应是**同一 skill 的两个可切换载体**，而非两个割裂的 skill。同时，wayfinder（规划）与 roadmap-driven（跟踪）应被显式设计为**一对组合技能（skill pair）**，由 `zj-to-tickets` 在缝上做转换器。

## 设计要点

- **抽象一层"载体（carrier）"**：把 wayfinder 的地图/票/阻塞/frontier，与 roadmap-driven 的树节点/决策/状态，统一为同一个心智模型——`地图/路线 + 决策记录 + 阻塞边 + frontier`。背后可由 issue-tracker 或本地文件实现，skill 的流程逻辑与载体解耦。
- **模式选择**：由场景决定（团队协作 → tracker 载体；个人全盘掌握/离线 → 本地载体），并在文档中给出切换指引。
- **一致性（跨模式不变）**：两种模式产出同样的心智模型，只是物理载体不同——这样跨模式迁移（从个人探索转为团队协作）时，认知模型不变，不重做决策。
- **组合技能对（seam）**：wayfinder 负责规划、roadmap-driven 负责跟踪；两者共享同一心智模型，由 `zj-to-tickets` 把规划地图导出为带阻塞边的工单，作为跟踪侧的输入。seam 是"转换器"而非"重写"。
- **配置**：复用 `/zj-agents-init` 的配置通道承载载体选择（见落地实现中的简化说明）。

## 落地实现（2026-08-20）

双模式与组合技能对已落地进两个技能本体（仓库内 `skills/engineering/zj-wayfinder` 与 `skills/engineering/zj-roadmap-driven`）：

- **wayfinder — `## Carrier modes` 双模式专节**：声明 tracker mode（issue-tracker，claim + 原生 blocking）与 local mode（单 markdown 文件承载整张地图，默认当无 tracker 配置时）。操作流程（`Refer by name` / `The Map` / `Tickets` / `Invocation`）全部加了 `In tracker mode / In local mode` 分支——local 下 map=单个 md 文件、ticket=文件内编号段、claim=`🔒` 标记、blocking 走 body `⛔ blocked by:` 约定、单写者串行。
- **roadmap-driven — `## 双模式载体（与 wayfinder 配对的一半）`**：明确其天然是**本地/自包含载体**（JSON SoT + md 视图），并在 tracker 一侧**消费** wayfinder 的规划路线（经 `zj-to-tickets` 导出带阻塞边工单，由 Agent 用 `roadmap_cli.py init/add/decide` 落成路线 JSON）；本 skill **不在 tracker 上自行规划**。
- **组合声明**：两个 SKILL.md 互相声明为"设计好的 skill pair"，均点名 `zj-to-tickets` 为缝上的转换器，均断言心智模型跨模式一致。原"先规划后跟踪"的衔接关系写入 `## Combining with zj-roadmap-driven` / `## 与 zj-wayfinder 组合（推荐，设计为组合技能对）`。

### 载体选择的实现方式（与原设计的偏差，需显式记录）

原设计待办之一为"复用 `/zj-agents-init` 增加'载体模式'配置维度"。实际落地时**未新增独立的配置键**，而是复用既有的"tracker 是否配置"作为隐式选择：

- 配置了 tracker（经 `/zj-agents-init`）→ 走 tracker 载体；
- 未配置 → local 载体（默认回退）。

即载体选择是**隐式**的，不是显式的"载体模式"开关。这是可接受的简化，但**不等同于**原设计设想的显式配置维度——若未来要支持"强制 local 即便有 tracker"或"多 tracker 切换"，才需要补显式配置键。

### 关键不变量

1. 心智模型（地图/路线 + 决策 + 阻塞边 + frontier）跨模式一致——迁移只换载体，不重做决策。
2. seam 是转换器（`zj-to-tickets`），不是重写；规划地图不应在跟踪侧手搓重建。
3. wayfinder 不跟踪执行进度（只产决策），roadmap-driven 不重新决策（只沿既定路线导航）——两层不越界。

## 状态对照（原 todo → 落地）

| 原待办 | 状态 | 说明 |
|---|---|---|
| 定义"shared workspace / carrier"原语抽象（地图/票/节点/决策/阻塞/frontier 最小公共接口） | **done（概念层）** | 落地为统一心智模型 + 两种载体；**未**抽独立代码/接口层，靠两 SKILL.md 的约定对齐，符合当前两个独立技能的现实 |
| 为 `zj-wayfinder` 设计 tracker ↔ 本地双后端 | **done** | `## Carrier modes` + 操作流程 dual-mode 分支 |
| 为 `zj-roadmap-driven` 设计 tracker ↔ 本地双后端 | **done** | `## 双模式载体`：天然本地 + 消费 tracker 规划 |
| 复用 `/zj-agents-init` 增加"载体模式"配置维度 | **partial** | 简化为"tracker 是否配置"隐式选择，未新增显式配置键 |
| 文档化两种模式的切换指引与适用场景 | **done** | 已写入两 SKILL.md 的 Carrier modes / 双模式载体 节 |
| （高阶，future）multi-agent & multi-human & multi-device 基于 shared context 的 co-design & co-work | **open** | 见高阶展望 |

## 高阶展望（future，未解锁）

如果未来有机会解决 **multi-agent & multi-human & multi-device 基于 shared context 的 co-design & co-work** 问题（多个 Agent、多个 Human、跨设备，共同基于一份共享上下文做联合设计与联合工作），上述"双模式 + 载体抽象"还能进一步解锁高阶用法：

- 多 Agent 各自认领决策票/节点，基于同一份 shared context 并发推进，冲突由 shared workspace 的并发原语（claim/lock/blocking）解决。
- 多 Human 跨设备看到同一张实时地图/路线，各自补充上下文，Human 的决策与 Agent 的跟踪在同一真相源上汇合。
- co-design（联合设计）与 co-work（联合工作）共享同一份 shared context，规划期（wayfinder）与执行期（roadmap-driven）无缝衔接。

**这要求先把"载体抽象 + 双模式"做扎实**，作为 multi-agent/multi-human 协作的基础设施——本设计已将其落到技能本体，但仍是"概念层抽象"，未抽独立 carrier 接口层（见状态对照）。

## 写给未来

- 若要抽真正的 carrier 接口层（让 wayfinder/roadmap 共享代码而非仅约定），从状态对照第一行的"概念层抽象"起步——先定义 `map / ticket / blocking / frontier` 的最小公共操作集，再为 tracker 与 local 各写实现。
- 若要多 tracker 切换或强制 local，回到"配置维度"那一项补显式键（partial 项）。
- 组合技能对的心智模型已在两 SKILL.md 固化，新增第三个 skill 进入"规划→跟踪"流水线时，必须复用同一心智模型，否则会重新引入本次设计要消灭的"底层事实不对称"。

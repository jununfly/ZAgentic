---
doc-kind: design
authority: primary
authority-id: design.roadmap-visual-review-product
---

# Roadmap Human 视图：产品设计方案（zj-roadmap-driven）

> 本页是**手写的产品论证**（Know Why / Do What / Trade-off / Who / How）。所有可机械校验的
> 规格事实——场景集、差异条目、能力规格、视图契约、不变量、切片——都在同目录
> [机器可读 SoT](zj-roadmap-visual-review.spec.json)，其派生视图是
> [技术设计方案](zj-roadmap-visual-review-technical.md)。本页不重述那些事实（一处事实一个家）。

## Question

`zj-roadmap-driven` 如何在不膨胀 Human 主视图、不破坏 process-state 权威边界的前提下，
向 Human 提供可视化阅读、理解、焦点对齐与基于 roadmap 的完整上下文对齐能力？

## Know Why：先纠正问题定义

「可视化能力弱」这个判断需要拆开，否则会把投入引向错误的方向。查本仓实物：

- [SKILL.md](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md) 核心原则 #2 已经把
  **焦点辐射**（祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数 + 异常折叠 + ready 小节）
  写成了 Human 主视图的既定形态，并有 `get_tree_radial` 与跨 carrier 字节相同的守卫测试。
  也就是说「方便阅读」的**信息架构**已经有了。
- [radial-render-plan.md](../../skills/codebase-docs/zj-roadmap-driven/references/radial-render-plan.md)
  §1 当年诊断过「ready 只在 CLI、不进 md 是 Human readiness 的真实缺口」，后来补上了
  ready 前 3；但**调度信息仍以纯文本 `<details>` 阻塞链呈现**，没有视觉化的依赖来龙去脉。
- [执行图设计](zj-roadmap-execution-graph.md) 把「trace 可自由增殖，但 md 行数不允许随之增长」
  钉成硬判据，并明确「解法不是加更多图，而是从同一 carrier 派生不同投影」。

**结构性诊断**：当前 Human 视图是一条**单通道缩进文本流**，把四类不同性质的信息挤在一起：

| 类别 | 例子 | 现在的载体 |
| --- | --- | --- |
| 结构 | 父子、层级 | 缩进 |
| 状态 | `[ ]` / `[~]` / `[x]` / `[!]` | 行首图标 |
| 调度 | `blocks` / `ready` / `critical-path` / `impact` | CLI 命令 + 纯文本折叠块 |
| 上下文 | decisions / trace / 证据 / 来龙去脉 | 几乎不进 Human 视图（被硬判据挡住） |

所以四个能力缺口不是同一种「渲染不够漂亮」：

1. **方便阅读**：信息架构已在，缺的是**可导航的视觉锚**（折叠/缩放/平移、状态双编码）。
2. **方便理解**：缺的是把**调度拓扑**从 CLI 搬进 Human 视图，且保持与 `ready` / `impact` 同源。
3. **对齐焦点**：缺的是**双方可引用的稳定锚点 token**。现在只有 `focus` 显示 id；显示 id 会随
   重排漂移，不能作持久引用。「双方都看着同一个节点」不等于「双方能引用同一个锚点」。
4. **完整上下文对齐**：这是**被硬判据主动切断**的，不是遗漏。缺的是一个**侧载出口**——
   上下文可按需展开、每条可追溯，但默认不占主视图一行。

结论：**不是加一张更漂亮的图，是拆投影 + 定锚点协议 + 开侧载出口**。这也正好是把
执行图设计里那句「从同一 carrier 派生不同投影」从 trace 层推广到 Human 视图层。

## Do What：调研得来的六条可迁移设计律

调研对象为 GitHub 上六类形态的代表项目（项目清单、版本 pin、24 条场景锚定的差异条目、
一手材料摘句全部列在[技术设计方案](zj-roadmap-visual-review-technical.md) 的证据层，
此处只给可迁移的结论，不复述清单）：

| 律 | 从哪来 | 可迁移的内容 | 落到哪个能力 |
| --- | --- | --- | --- |
| L1 图由事实源算出，不是手工维护的文档 | [Nx Graph](https://nx.dev/docs/features/explore-graph) 明说 "It always stays up to date without having to actively maintain a document as it is calculated by analyzing your source code" | 视图必须从 carrier 确定性派生，禁止让模型自由绘制 | 全部（`view-ir`） |
| L2 焦点与邻近度是可控旋钮，不是固定 depth | Nx `--focus` + proximity + composite nodes；[Markmap](https://github.com/markmap/markmap) 的 fold / frontmatter `foldLevel` | 复合节点折叠计数、按层级缩放，避免 50+ 节点平铺 | `C::01` |
| L3 边即上下文 | [Cognograph](https://github.com/skovalik/cognograph/blob/master/FEATURES.md) 用入边 BFS 组装上下文、显示 context scope badge 与 BFS 半径 | 把 roadmap 已有的 `reference` / `context --include` 路径**给人看**，并标出遍历半径 | `C::04` |
| L4 上下文按需展开，不铺进主视图 | Markmap 让段落/代码留在分支的 note popover；[Overture](https://github.com/SixHq/Overture) 把 files/docs/keys 挂在**节点级作用域** | 这是「完整上下文对齐」与「主视图不膨胀」两个约束的唯一交集 | `C::04` |
| L5 共享可引用锚点 | [inplan](https://github.com/melly-lgtm/inplan) 人机共编同一份文档、批注锚到具体句子；Nx 的 `--focus`；Cognograph 的 session→node 映射 | 锚点必须是可复制的文本 token，绑定不可变 uid 与 revision | `C::03` / `C::06` |
| L6 视觉面按内容选择 | [BuilderIO `/visual-plan`](https://github.com/BuilderIO/skills) 的 Visual Surface Choice：架构类纯文档、UI 类才上画布 | 结构/调度用图、长文本决策用文档、上下文用侧载；不由模型每次决定 | `C::05` |

补充旁证（不作为 `native` 判定的唯一依据，见技术页证据完整性声明）：
[OpenSpec](https://github.com/Fission-AI/OpenSpec) 的 proposal/specs/design/tasks 分层与
「one source of truth every coding agent can read」、
[Spec Kit](https://github.com/github/spec-kit) 的单向读写链与「勾选权归人」、
[Kanvas](https://github.com/XMihura/Kanvas) 的「颜色即状态、箭头即依赖、CLI 禁止 agent 直改画布 JSON」、
以及 [Plans](https://github.com/yrangana/plans) 的 `roadmap.html` 从自动生成的 JSON 渲染 +
`/plans sync` 用 git log 检测计划与现实漂移。

**两处明确不采纳**：① 引入 MCP server / 托管审阅服务（Overture、/visual-plan 的 hosted 模式）
——数据出域、依赖常驻服务，违反 [ADR 0010](../zj-adr/0010-local-file-persistence-convention.md)
与 [skill runtime closure](zj-skill-runtime-closure.md)；② 让 Agent 直改画布或让模型自由产出
HTML——破坏确定性、两 carrier 字节相同与可回归性。离线单文件产物即可拿到绝大部分收益。

## 四个场景 → 四个能力（规格以技术页为准）

| 场景 | 能力 | Human 拿到什么 |
| --- | --- | --- |
| 方便阅读 | `C::01 radial-overview` | 一屏内同时看到焦点锚点与折叠后的全局分区计数，可折叠/缩放/平移 |
| 方便理解 | `C::02 dependency-lens` | 选中节点即见「被谁挡住 / 挡住谁 / 改动波及谁」，点边回溯边 id 与来源 |
| 对齐焦点 | `C::03 anchor-envelope` + `C::06 revision-staleness` | 一个可复制的 `zj-roadmap-anchor/v1` token，Human 贴回对话、Agent 用它请求同一局部视图；revision 不符时显式 stale |
| 完整上下文对齐 | `C::04 context-pack` + `C::05 surface-choice` | 主视图只留一个入口，展开后是带来源、BFS 半径与条目数的侧载包；条目增长时主视图字节不变 |

> 第二轮锐化另增 `C::07 doi-layering` / `C::08 debt-lens` / `C::09 delta-reentry`，第三轮另增
> `C::10 presentation-surfaces`（见下两节）。场景集始终保持四个口述维度不变，新增的是
> 负载条件、选择机制与呈现形态。

## 交互骨架（文字化，便于逐轮迭代）

```text
┌ zj-roadmap-anchor/v1 · view=overview · uid=... · rev=...   [复制锚点]
│  当前焦点 1-2-3-4  接入 SQLite carrier        [stale? 显示刷新命令]
├ 祖先链（必现）
│  1 [x] 基础设施  ·  该层还有 2 个兄弟 ▸
│   1-2 [~] 多载体  ·  该层还有 1 个兄弟 ▸
│    1-2-3 [~] carrier 迁移
│     1-2-3-4 [~] 接入 SQLite          ← 焦点
│       └ 1-2-3-4-1 [ ] 租约迁移
├ 折叠分区计数（默认不展开）
│  1-1 整支 completed → 折叠 N 项 ▸
├ 上下文入口（默认只占一行）
│  ⓘ 该节点上下文 7 项 · 半径 2  [展开]   ← 展开走侧载包，不撑高主视图
└ 视图切换  [overview] [dependency] [context]   ← 同一 IR 的不同投影
```

关键交互约定：

- **锚点条在最上、永远可见**：它是 Human 与 Agent 的共同坐标系，不是装饰。
- **状态用颜色 + 形状双编码**：不依赖颜色单独承载语义（可访问性）。
- **切换视图不改变锚点**：`view-kind` 变，`node-uid` 不变；这样「对齐焦点」在四个场景下都成立。
- **展开上下文 ≠ 改图**：侧载包只读，不产生 ChangeSet、不改拓扑、不回写 carrier。
- **stale 是显式状态**：revision 不符时给出刷新命令，把命令写出来不等于替人跑。

## 补强：完整上下文足够大时的信息选择（第二轮问题锐化）

第二轮把问题钉得更准，也暴露了上面方案的覆盖缺口，先如实列出：

| 指出的问题 | 上一轮方案的状态 |
| --- | --- |
| 快速俯瞰全貌、多次中途离开后回来继续 | **未覆盖**（只有 revision stale 标记，没有增量重入） |
| 抓到焦点的关键阻塞事项以明确顺序依赖 | **半覆盖**（dependency-lens 只沿 `blocks`，没进主视图的优先排序） |
| 高亮与焦点高度耦合的事项，界定应整体处理的 scope | **未覆盖**（没有耦合度度量，只有拓扑邻居） |
| 动态执行中发现的 GAP / TODO / 风险 / sweep 债务 | **未覆盖**（散落在 open_question / signals / trace，无一等模型） |
| smart 压缩降低阅读成本、smart 拓展协助理解 scope | **未覆盖**（只有与焦点无关的固定折叠） |

### 结构性矛盾

信息总量 S 随执行单调增长；Human 一次能处理的阅读量 C 是常数；且 S 在离开期间仍在变
（Agent 继续执行 / 多设备），所以**重入时不能复用上次的心智模型**。于是：

- 全量展示：重读成本 `f(S)=S`，随规模线性恶化；
- 必要的折叠：切分规则与当前焦点无关，焦点邻域可能恰好被折掉，且被折掉多少不可见；
- 纯文字化骨架：即使信息选对了，也没有空间编码来表达「高耦合 / 阻塞 / 债务」的强度差异。

要解的只有一个式子：给定锚点 A，确定性选出可见子集 `V(A, θ)`，使 `|V| ≤ C`，且 V
**必须包含** 必备项（焦点 + 阻塞前驱闭包 + 后继 + 高严重度债务，对应 spec `IS::mandatory::v1`）；重入时输出
`Δ(A, t, t₀)` 而非全量。

### 四个机制

1. **确定性 DOI，而不是模型判断**。`DOI(n|A)` 是六项加权和：图邻近度 0.30、阻塞关键性 0.25、
   共享上下文 0.15、债务严重度 0.15、新近变化 0.10、稳定抑制 0.05。权重与阈值是 skill 内的
   脚本常量，同 carrier + 同 anchor + 同 θ + 同 baseline 必须逐字节可复算。
   **smart 在这里的含义是「相关度函数 + 显式阈值」，不是让 LLM 每次挑重点**——后者会同时
   破坏确定性、两 carrier 字节相同和可回归性。
2. **压缩与拓展是同一个旋钮**。θ 上移压缩、下移拓展，共用同一排序与同一套模板；三档预设
   （overview 0.75 / neighborhood 0.45 / expand 0.20）只是取三个 θ 值。做成两套界面必然漂移，
   本仓在「模板抄两份」上已经翻过车。注意：这三个数是**声明的兜底阈值**；运行时由
   `DOI::theta-calib::v1` 按当前焦点下非必备项的 DOI 分布取百分位（overview P85 / neighborhood P50 /
   expand P15）覆盖，保证三档在任意焦点下都可区分——DOI 是焦点相对量，写死阈值会在部分焦点退化成等价。
   只有当候选为空（图极小）时才退回声明值。
3. **债务一等建模、旁挂不改图**。GAP / 风险 / TODO / sweep 有 kind、severity、
   `discovered-revision`（诞生即写，事后补不回来）、anchor-ref、evidence-ref、state；按
   `debt-severity` 项进 DOI，高严重度在预算内优先可见。但**不进 plan tree 的 children、
   不进 ready 遍历集、不自动变成 WorkItem**——晋升仍走既有 `promote` 的
   proposal → Human 审核 → accept，沿用执行图设计的图膨胀防线。
4. **增量重入**。视图 receipt 记 `(anchor, revision, θ, seen-item-hashes)`，落在 gitignored
   隔离区，**绝不进 carrier**。每个可见条目带稳定 id + content hash，重入只输出
   added / changed / removed / stable-folded 四类，稳定项折成「其余 N 项未变」一行。
   receipt 缺失或损坏则 fail-closed 回退全量并显式提示，不猜上次读到哪。

### 与既有不变量怎么共存

关键在**把 baseline 做成显式输入，而不是藏在事实源里**：`view-ir` 只由 carrier 计算，
receipt 不参与；`baseline=None` 时输出全量视图，两 carrier 逐字节相同；给定 baseline 时
字节相同性针对「同一 ir + 同一 baseline」成立。这样增量重入不会偷偷引入第二个事实源。

阅读预算（40 行）是硬上限：超出时按 DOI 截断，并**显式报告被压缩条目数与其中高 DOI
未显示数**，不允许静默丢失——沿用阻塞链「最多列 5 个，其余写明数量」的既有纪律。
固定场景集仍是 Human 口述的四维度；本轮的负载条件是**约束**，不是新场景，不得由 Agent
扩充（CHK-04）。这一条已写进 SoT 并由闸门 R12 机械钉住。

## 呈现形态：信息卡片与局部 DAG（第三轮锐化）

第三轮指出演示的 UI/UX 不够优雅，问信息卡片 + DAG 是不是更好。**采纳，但带约束地采纳**，
并且先认一个错：第二轮那个「单一文本列表 + θ 滑块 + 文字状态条」的演示，用一套界面
演示了所有场景，恰好违反了本设计自己写的 `C::05 Visual Surface Choice`。

### 为什么它不只是「更好看」

- DAG 用空间位置与边方向表达**顺序依赖**，缩进树做不到「谁挡谁、改了波及谁」；
- 卡片用分组与视觉层次承载**单节点的完整上下文与债务**，避免长列表平铺；
- DOI 可用尺寸 / 饱和度 / 景深**连续编码**，比文字标注「必备」更快被感知；
- 重入增量可作独立横条，不占主区视线。

所以这是把上一轮的 DOI 选择结果**做空间编码**，不是换一层皮：θ、阅读预算、债务旁挂、
增量重入全部保持不变，只是承载它们的面换了。

### 三区加一条

| 区 | 职责 |
| --- | --- |
| 锚点条（常驻） | anchor token + θ 旋钮 + 阅读预算指示 + 重入入口；高度固定，不随 S 增长 |
| 左区 局部 DAG | 只画 DOI≥θ 的节点与必备项，边语义用线型区分 |
| 右区 信息卡片列 | 焦点卡 / 耦合卡 / 债务卡，三级 LOD，点击展开不撑高左区 |
| 底部增量横条 | added / changed / removed / stable-folded，重入时先入眼 |

### 三个必须避开的坑

1. **全量 DAG 平铺**：Overture 作者自己把「50+ 步图谱可读性未验证」列为开放问题。必须画
   DOI 裁剪后的局部 DAG，非焦点子树折成复合节点计数（借 Nx composite nodes）。
2. **卡片墙**：卡片比文本行更占视觉面积，会让瞬时阅读量**比文字列表更大**——正好加重
   上一轮要治的病。所以卡片受同一 40 行预算，并走三级 LOD：L0 色块 + 分类计数 /
   L1 标题 + 徽标 + DOI / L2 完整内容 + 证据引用（借 Cognograph 的 5 级 LOD 与 Markmap
   的 note popover）。
3. **随机布局**：force-directed 每次坐标不同，直接破坏确定性与两 carrier 字节相同。必须用
   确定性分层布局（dagre / Sugiyama 或固定坐标），且 **Mermaid / DOT 文本等价物必现**——
   它既是可 git diff 的审阅面，也是逐字节回归的抓手。

### 编码规则

| 对象 | 编码 |
| --- | --- |
| 节点 | 尺寸与饱和度随 DOI 连续变化；焦点最大且描边加粗；非焦点子树折成复合节点「K 项」 |
| 边 | `blocks` 粗实线（最高权重）/ `informs` 细虚线 / `derives-from` 点线；点击显示边 id 与证据 |
| 债务 | **是卡片不是 DAG 节点**，不进拓扑、不进 ready |
| DOI | 尺寸 / 饱和度 / 景深三通道，**不单靠颜色**，保证灰度可打印与可访问性 |

θ 同时驱动 DAG 裁剪与卡片 LOD，两者共用同一 DOI 排序与同一套模板——这是 `INV::10` 与
`RD::10` 在视觉层的落地，不是新开一套界面。

## Who：Human 与 Agent 的边界

沿用执行图设计已确立的口诀「**Agent 拥有它的过程记录，Human 拥有地图**」：

| 动作 | Human | Agent |
| --- | --- | --- |
| 复制 / 粘贴锚点、切换视图、展开上下文 | ✅ | ✅ |
| 从 carrier 派生只读投影 | ✅ | ✅（自动 render 仍是默认且必需） |
| 新增 / 删除 / 移动节点、跨层晋升 | ✅ | ❌（需 Human 审核 proposal） |
| 把视图状态当作正确性证据 | ❌ | ❌（process-state 权威边界） |

Anchor token 是**双方共享引用**，不是 Agent 单方面的解释权。视图永远只读，
不可反向导入事实源；这也是 [SKILL.md](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md)
「Agent 禁止直接 Read/Edit md 的路线图 section」在可视化形态下的等价约束。

## Trade-off

- **收益**：四个能力缺口各自有独立出口，不再互相挤压；调度与上下文第一次进入 Human 视野，
  同时保住「主视图不膨胀」硬判据；锚点让跨会话 / 跨设备讨论有了稳定坐标系。
- **代价**：多一套 IR 与投影契约，命令面、模板与守卫测试都要扩；Mermaid 文本图在超大图上
  仍有可读性上限，必须靠折叠分区计数而非平铺全图兜住。
- **放弃**：实时协同编辑、托管批注、AI 自动重排布局、把可视化状态接进验收证据链。
  前三者引入服务与不确定性，第四者越过权威边界。
- **不升格为门禁**：视图质量 / doc-slop 只作审计清单，不新增扫描全仓报诊断的运行时门禁
  （[ADR 0011](../zj-adr/0011-docs-governance-quality-contract-and-rejected-defaults.md)
  与 `zj-doc-health` 已把机械 health gate 列为 rejected default）。机械钉住的是**规格与不变量**，
  不是文风。

## How：落地顺序与本次交付边界

**S0 前置**：DOI 函数 + 阅读预算 + 债务 schema + 视图 receipt 契约——这是第二轮问题定义的
机器可读落点，必须在任何投影之前冻结。然后 S1 `view-ir` + 锚点契约 → S2 `overview` 投影 →
S3 `dependency` 投影 → S4 `context` 侧载与 stale 标记；S2/S3/S4 都从 S1 投影，顺序不可换。
每片的完成判据、依赖与不变量守卫见[技术设计方案](zj-roadmap-visual-review-technical.md)。

**本次交付边界**（重要）：只落

1. 产品设计方案（本页）；
2. 机器可读 SoT（场景集 / 24 条差异条目 / 能力 / 视图契约 / 不变量 / 切片 / 一手材料）；
3. 由确定性脚本维护的[技术设计方案](zj-roadmap-visual-review-technical.md)：
   `validate` 机械闸门、`render` 生成、`verify` 逐字节复核；
4. 根 `tests/` 回归守卫与 doc-map 登记。

**不改 skill 运行时实现**：不新增 CLI 命令、不动 `roadmap.py`、不改 SKILL.md 的既有纪律。
S0—S4 是后续切片，须各走分支与显式审批。

第二轮锐化额外落了：问题锐化与 4 条负载条件、确定性 DOI 函数与 40 行阅读预算、债务一等
schema、增量重入 receipt 契约，以及对应的 R12—R15 机械闸门与双向验。第三轮再落：局部 DAG
与信息卡片的呈现分工、三区加一条的信息架构、编码规则、确定性布局与文本等价物，以及
`R16` 闸门。这些全部进 SoT，技术页由脚本重生成（257 → 377 → 460 行），手写页不含任何生成内容。

这里有一处自应用值得点明：**技术方案页本身就是它设计的那种派生视图**——
SoT 是 JSON，人是读投影，脚本保证逐字节一致，手写页不得夹带生成标记。
L1 律不是只对 roadmap 成立，它先在本设计里成立。

## 边界与证据声明

- 固定场景集是**对 Human 口述四能力维度的 Agent 转写**，`human-independent-pin=false`。
  按 `zj-graphical-cross-comparison` 的范围闸门 2，本次**不签发正式横比报告**；
  24 条差异条目是可追溯的**过程材料**，`metrics` 恒为 `display-only`。
  若 zj 独立给定带版本 pin 的场景集并补齐各源 commit sha，可提升为正式报告输入。
- `unknown` 是证据缺口，不是「产品不支持」。本次未采集到任何显式否定陈述，故
  `unsupported` 计数为 0；5 条 `unknown` 各带验证计划。
- 摘要指标（覆盖率、分布）不参与排序、裁决、回灌或优先级——这是横比模型的硬纪律。

## Related authority

- [Roadmap 执行图（trace layer）](zj-roadmap-execution-graph.md) — 硬判据与「同源多投影」判决的来源
- [Roadmap 并发与依赖模型](zj-roadmap-concurrency-model.md) — 调度边的语义归口
- [Skill runtime closure](zj-skill-runtime-closure.md) — 安装态自包含约束
- [ADR 0010 本地文件持久化约定](../zj-adr/0010-local-file-persistence-convention.md)
- [ADR 0011 文档治理质量契约与 rejected defaults](../zj-adr/0011-docs-governance-quality-contract-and-rejected-defaults.md)
- [文档地图](../README.md) — 本页的 authority-id 绑定

## Amendment (2026-11-12)

上文 :264–:273 的交付边界是 #255 的 docs 提交当时的快照。之后 zj 明确「选 C 路径」，
批准把 S0/S2 落成 `zj-roadmap-driven` 的真实只读包，并分别走分支与显式审批
（PR #255 / #256）；#257 又收敛了安装态路径基准、skill 结构与门禁覆盖。
本 Amendment **不推翻上文的切片顺序判决**，只更正「已落地范围」这一事实。

### 当前状态

- 已落地：S0（DOI / 预算 / 债务 schema）、S2（overview + Mermaid 文本等价物）、
  S3（dependency 投影与边回溯）、S4（context side-pack 与 stale 标记）。
  各公开视图已携带 `zj-roadmap-authority/v1` 权威信封（INV::05）。
- **deferred（S1，未获批，不得假完成）**：view-ir / anchor-envelope 只读命令、
  两 carrier 同 anchor 输出逐字节相同、Δ 增量重入的条目级 hash receipt
  （含 fail-closed 回退与 gitignored 落盘）。
- S2/S3/S4 的 `depends-on: ["S1"]` 保持原样：这是**已知的规格债**，由
  `tests/test_roadmap_visual_review_governance.py` 钉住 S1 判据未被删除，
  不靠改 depends-on 把它抹平。

### Why

S1 涉及两 carrier 归一化与跨设备 receipt 状态，属独立功能切片，须 Human 显式批准，
不能在一次 cleanup 里顺手实现。把状态写清楚，避免派生页与实现各说各话；
需要推进时另开分支与切片，不改写本页历史论证。

## Amendment (2026-11-12, S1 delivered)

上一条 Amendment 把 S1 标为 deferred。zj 随后显式批准「开 S1 切片」，本 Amendment
只更新状态，**不改写上文任何判决**。

### 交付内容

- `viz/ir_schema` 模块：冻结 `zj-roadmap-view-ir/v1` 的字段集合并在运行期断言；改结构须显式升版。
- `viz/carrier` 模块 与 `graph.load()`：JSON / SQLite 走同一份归一化数据；SQLite carrier 补齐
  `debts` 无损迁移、容忍语义化 version 字符串。
- `graph.revision` 改为内容派生短码（排除 `metadata.updated` 写入时间戳与 carrier 派生字段），
  使同内容两 carrier 的 envelope 一致。
- `viz/receipt.py`：条目级 content hash、added / changed / removed / stable-folded、
  receipt 损坏时 fail-closed 全量回退、路径显式给、不进 carrier 也不参与 view-ir 计算。
- HTML 的 Δ 区块从「按 status 数状态」换成真实增量数据（baseline=None 为确定性全量回退）。

### 判据核对

S1 的「IR schema 冻结 / 两 carrier 同 anchor 输出逐字节相同 / 权威信封必现」与
INV::11「receipt 不进 carrier、baseline=None 全量视图两 carrier 逐字节相同」，
均由 viz 包的 S1 单测套件机械断言（六类公开视图逐字节比对）。

## Amendment (2026-11-12, S1b delivered)

Human 于 2026-11-12 显式批准「解决待办 4」，把下面这项从 open 转为 delivered。
只更新状态，**不改写上文任何判决**，也不回头修改 spec 的 invariants / capabilities
集合（S1b 是 S1 之上的后续增量，不是原 spec 的新判据）。

### 领域判决

receipt 是**可丢弃的派生缓存**，不是权威状态。因此跨设备同步不需要分布式一致性
协议（那是投机性通用性）：视图上下文一致且条目 hash 无冲突才合并取并集，任何
冲突 / 版本不一致 / 上下文不一致 / TTL 过期一律 fail-closed 回退全量视图。
同步介质由 Human 决定（显式路径搬运收据文件），本切片只保证收据
**可移植、可合并、可过期**，不引入网络依赖，也不做 last-write-wins。

### 交付内容

- v2 receipt：在 v1 五字段之外增加 `device_id` / `generated_at` / `ttl_seconds`；
  不传设备信息时仍写 v1，保持 S1 字节兼容。v1 收据可继续读，但不可跨设备合并。
- 合并：版本、anchor、carrier revision、θ 一致 + 双方未过期 + 条目 hash 无冲突
  → 取并集作为 baseline；否则返回显式 fail-closed warning。
- 过期：`now > generated_at + ttl_seconds` 视为过期，与「缺失 / 损坏」共用同一条
  全量回退路径；TTL 非正数在写入时即拒绝。
- CLI 三个显式入口：`--device-id` / `--receipt-ttl` / `--merge-receipt`，全部要求
  Human 给路径或值（ADR 0010）。`roadmap_cli` 冻结命令清单未动。
- 机械守卫：viz 包的 S1b 单测套件覆盖便携性、v1 兼容、合并并集、四类上下文不一致、
  hash 冲突、混合版本、过期边界、CLI 端到端、合并产物不进 carrier / view-ir。

### 仍 open（范围外，非缺陷）

跨设备**传输介质与自动同步调度**不属于本切片：本切片只定义收据本身的可移植契约，
不提供网络协议、设备发现或后台同步。

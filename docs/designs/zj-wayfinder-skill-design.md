---
doc-kind: design
authority: primary
authority-id: design.wayfinder-skill
model-elements: [entity.design]
---

# zj-wayfinder 设计文档（与实现对齐）

> 本页回答「wayfinder 为什么这样设计、不变式与取舍」，**不是操作指南**。运行时行为、调用步骤
> 以 `skills/codebase-docs/zj-wayfinder/SKILL.md` 为唯一权威（runtime closure：skill 运行期只读
> 自家块，不回链本页）。所有设计断言挂 `SKILL.md:NN` 行锚，执行前逐条回源核对。

## 1. 定位：规划型 skill，产决策而非交付

wayfinder 处理的是「比一次 agent 会话更大、且裹在雾里」的工作：从这里到**目的地**的路还没显形
（`SKILL.md:10`）。它的解法不是切任务、赶进度，而是先把路画成一张**共享地图**，把路上的开放问题
拆成**决策工单**——一次解一张，直到路清晰（`SKILL.md:4,10`）。

> **[定稿] 决策工单 vs build slices 是整条脊柱。** 一张工单是「resolution 为一个*决策*的问题」，
> 不是「一段待执行的工作」。把工单当 build slice 就退化成 roadmap——把执行编排交给 roadmap-driven，
> 跨载体的交接（plan → track）由 `design.wayfinder-roadmap-carrier-seam` 拥有（见 §9 Related authority），
> 本页不复述。

- **plan, don't do（默认，非交付）**：地图完成 = 抵达目的地、没有决策剩下要拍板（`SKILL.md:14-16`）。
  「忍不住想直接干」通常是信号——你已摸到地图边缘、该 handoff 了。一个 effort 可在地图 **Notes** 段
  显式覆写、把执行也纳入地图（`SKILL.md:16`）；这是约定层例外，不是默认。
- **domain-agnostic**：目的地可以是待交接迭代的 spec、规划前要先锁的决策、或就地变更（如数据结构迁移）；
  地图形状不绑定工程域（`SKILL.md:12`）。

## 2. 四条核心不变式

1. **地图是索引，不是存储。** 它列出已做的决策并指向持有细节的工单；一条决策只活在**恰好一处**——
   它的工单——所以地图从不重述，只 gist + link（`SKILL.md:37`）。地图 body 是固定五段：Destination /
   Notes / Decisions so far / Not yet specified / Out of scope（`SKILL.md:41-67`）。开放工单**不列**在地图里，
   由查询取（`SKILL.md:43`）。
2. **目的地先于一切，因为它 fixes scope。** 命名目的地是 charting 的第一动作，塑造每张工单（`SKILL.md:12`）；
   先定目的地，再摸前沿（`SKILL.md:125`）。
3. **每会话只解一张工单，`research` 是唯一例外。** （`SKILL.md:119`）research 的 AFK 性质允许 chart 会话并行
   发多个 `/zj-research` subagent（`SKILL.md:129`）。
4. **越界工单：关闭，留一行入 Out of scope，不进 Decisions so far。** Decisions so far 记的是*实际走过的路*，
   而 scope 边界不是路上的一步（`SKILL.md:115`）。

## 3. 目的地决定地图的终态

「路清晰」= 没有工单剩下、也没有无法 ticket 的雾——此时该 handoff，而不是继续 chart
（`SKILL.md:98,126`）。charting 时若 breadth-first 摸底**没发现任何雾**、整段旅程一次会话装得下，
就**不需要地图**：停下、问用户怎么走（`SKILL.md:126`）。

## 4. 战争迷雾：三个不同集合

地图**刻意**不完整——画不出来的不画。地图之外有三种状态，判据与毕业规则各不相同：

| 状态 | 判据 | 毕业去向 | 是否可解 |
| --- | --- | --- | --- |
| **Ticket** | 现在能否把问题**措辞**清楚 | 进 frontier 或 blocked 集 | 是 |
| **Not yet specified**（fog） | 现在**还不能**措辞到 ticket 那么清晰 | 前沿推进时按片毕业成新 ticket | 是（未来） |
| **Out of scope** | 越过目的地，不在本 effort 范围内 | **永不**毕业 | 否 |

> **[定稿] fog/ticket 的判据是 sharpness，不是 solvability。** 判据是「此刻能否*精确说出这个问题*」——
> 而非「能否*回答*它」。问题已锋利就 ticket（哪怕被阻塞、现在动不了）；还说不利索就留在 fog
> （`SKILL.md:102-105`）。不要提前把 fog 切成 ticket 尺寸：它比 ticket 更粗，一片 fog 到达时可能毕业成
> 多张 ticket，也可能一张都不是（`SKILL.md:105`）。

- **fog 只朝目的地聚集**：in-scope，只是还不够锋利；它是「未探明的前沿」，写给协作者当路标（`SKILL.md:96-100`）。
- **Out of scope 与 fog 对偶**：由 destination 固定的**范围**（非 sharpness）决定归属（`SKILL.md:111`）。
  越界工作不 graduate——前沿停在目的地；只有目的地被重新划定才会以**新 effort**（而非续作）出现（`SKILL.md:113`）。
- Not yet specified 排除：已决（Decisions so far）、已在票（live ticket）、越界（Out of scope）（`SKILL.md:107,115`）。

## 5. 双载体：心智模型不变，只换物理存储

wayfinder 是「**一个 skill、两种可切换载体**」：规划逻辑完全相同，只有地图/工单/阻塞/前沿的**物理之家**
变（`SKILL.md:20`）。按场景选，不按偏好选（`SKILL.md:18-27`）。

- **Tracker 模式（teamwork）**：地图与其 child 工单活在仓库 issue tracker 上；胜在 `claim` + native blocking
  支撑多 agent 并发，且人类在 tracker 自己的 UI 里直接看到 frontier。需要已配置的 tracker（否则跑 `/zj-repo-init`）（`SKILL.md:22`）。
- **Local 模式（self-contained）**：整张地图——Destination、Notes、Decisions、Not yet specified、Out of scope
  及各工单——活在**单个本地 markdown 文件**（"local-markdown tracker"）；胜在上下文完备、离线、零外部依赖、
  单写者简单。无 tracker 配置时这是**默认**（`SKILL.md:23`）。

### 5.1 同一心智模型

两种载体暴露**同一套原语**：`destination`、`notes`、`decisions`、`fog`、`scope`，以及带 `blocking edges` +
`frontier` 的 `tickets`（`SKILL.md:25`）。所以从 local 探索迁到 teamwork（或反向）只换载体、不换认知：
本地画的地图落到 tracker 上，**不重决策任何东西**（`SKILL.md:25`）。

### 5.2 工单表示在两种载体下的物理编码

本节只述**表示不变式**（身份/状态记号如何落在物理载体上）；「何时选 tracker vs local」与 roadmap JSON 侧
的接缝归 `design.wayfinder-roadmap-carrier-seam`，此处不裁定。

| 概念 | tracker 模式 | local 模式 | 依据 |
| --- | --- | --- | --- |
| 地图 | 一条 labelled `wayfinder:map` 的 issue | 单个本地 markdown 文件（canonical 工件；落点见 §9 / ADR 0010） | `SKILL.md:35` |
| 工单身份 | child issue，issue id 即身份 | 编号顶级 section（`## A1 — …`），编号即身份 | `SKILL.md:71` |
| 类型记号 | label `wayfinder:<type>`，取 `research`/`prototype`/`grilling`/`task` | 写进标题短码 `R`/`G`/`P`/`T` | `SKILL.md:79` |
| 认领 | assign issue 给驱动者；open+unassigned = unclaimed | 标题加 `🔒` + 认领人名；无 `🔒` = unclaimed | `SKILL.md:81` |
| 阻塞 | tracker **native** 依赖关系（故能在 UI 里可视化 frontier） | body 约定 `⛔ blocked by: <numbers>`（读文件时呈现） | `SKILL.md:83` |
| 解决 | 张贴 resolution comment + close issue | 工单 section 下写答案 + 标 `✅` | `SKILL.md:139` |

两种模式都：一张工单当**阻塞它的票全部关闭**时算 unblocked；**frontier = open + unblocked + unclaimed** 的票，
即「已知边缘」（`SKILL.md:83`）。答案不属于 body——在 resolution 时记录（`SKILL.md:85`）。

### 5.3 单写者不变式

local 模式一张地图一个文件，两个 agent 同写会撞车：**每会话解一票、解完提交文件再下一票**；tracker 模式
则可能多个会话并发编辑 tracker，靠 claim 协调（`SKILL.md:142`）。

## 6. 工单类型：HITL / AFK 分类学

每张工单要么 **HITL**（人在环，由**为自己说话的人类**参与解决），要么 **AFK**（agent 独自推进）（`SKILL.md:89`）。

> **[定稿] HITL 不变式：agent 永不替人作答。** 一张 HITL 票只通过那场实时交流来解；替人类回答
> 就等于破坏工单语义——「一个自问自答的 grilling agent 已经坏了这条」（`SKILL.md:89`）。这条钉在
> 类型语义上，不靠 prompt 提醒。

| 类型 | 归属 | 触发/含义 | 如何解 | 依据 |
| --- | --- | --- | --- | --- |
| **Research** | AFK | 读外部文档、第三方 API、本地知识库等，翻出一个待决事实 | `/zj-research` **subagent** 解；当知识在当前工作目录之外时用 | `SKILL.md:91` |
| **Prototype** | HITL | 用低成本粗工件（提纲/粗略尝试/stub/经 `/zj-prototype` 的 UI·logic 代码）抬高讨论保真度 | 工件链接作 asset；当「该长什么样/怎么表现」是关键问题时用 | `SKILL.md:92` |
| **Grilling** | HITL | 对话。**默认类型**；始终调用 `/zj-grilling` 与 `/zj-domain-modeling` | live exchange | `SKILL.md:93` |
| **Task** | HITL 或 AFK | 必须先做的手工前置（注册服务、开通访问、搬数据以观其形）——四类里唯一「*做*而非*决定*」 | 做完即解；answer 记录做了什么与产出事实（凭证位置/新 URL/行数）；靠「解锁一个决策」而非「交付目的地」挣得存在权 | `SKILL.md:94` |

## 7. refer-by-name 纪律

每张地图与工单都有**名字**——tracker 模式是 title，local 模式是文件里的编号标题。凡是人类读到的文本
（叙述、地图的 Decisions-so-far）都用名字指称，**绝不用裸 id / 编号 / slug**（`SKILL.md:31`）。

`#42, #43, #44` 是一堵不可读的字墙；名字一眼可读。id/URL（tracker）或 section 号（local）**骑在名字里**
（issue link / 文件锚点），绝不替代名字（`SKILL.md:31`）。这条纪律属于**人类界面层**，不属数据模型——
底层身份仍以 issue id / `## A1` 编号为准。

## 8. 会话模型与交接

**Chart the map**（用户带松散想法来）——六步：
1. 命名目的地（`/zj-grilling` + `/zj-domain-modeling`；目的地 fixes scope，最先定）（`SKILL.md:125`）。
2. 再 grill 一轮、**breadth-first** 摸 frontier：横扫全空间找开放决策与可即时着手的第一步。**若无雾冒出**、
   整段旅程一小会话装得下 → 不需地图，停下问用户（`SKILL.md:126`）。
3. 建地图：tracker 建 `wayfinder:map` issue / local 建单 markdown 文件；填 Destination + Notes，Decisions 空，
   雾草拟进 Not yet specified（`SKILL.md:127`）。
4. 建现在可 spec 的工单；**second pass** 再连 blocking edges（tracker 需先有 id；local 写 `⛔ blocked by:`）。
   连边即把票分成 frontier 与 blocked；说不出来的留在 fog（`SKILL.md:128`）。
5. 为每张新建 `research` 票并行发 `/zj-research` subagent 去解（`SKILL.md:129`）。
6. **停**——charting 是一会话的活，一张都不亲手解（`SKILL.md:130`）。

**Work through the map**（用户带地图 URL 或编号来，工单可选）——五步：
1. 载入**地图**（低分辨率视图，不是每张工单正文）（`SKILL.md:136`）。
2. 选票：用户指定就用它，否则取 frontier 里第一张。**先 claim** 再动工（`SKILL.md:137`）。
3. 解它——按需 zoom：拉相关/已闭工单全文、调 Notes 点名的 skill；拿不准就 `/zj-grilling` + `/zj-domain-modeling`（`SKILL.md:138`）。
4. 记录 resolution：tracker 贴 resolution comment + close / local 在 section 下写答案 + 标 `✅`；两种都往 Decisions-so-far **追加一个 context pointer**（`SKILL.md:139`）。
5. 加新冒出的工单（create-then-wire）；把被答案变可 spec 的雾**毕业**成新票，并从 Not yet specified 清掉每一片
   毕业出去的雾（`SKILL.md:140`）。若某票被证明越过目的地 → **判 out of scope**，而非在途中解（`SKILL.md:140`）。

> **[定稿] charting 与 work-through 互斥于「一张都不解」/「只解一张」的分工。** chart 会话只画不发（`SKILL.md:130`），
> work-through 会话只解一票并把雾推进 frontier（`SKILL.md:119,137-140`）。这条节奏分工是「每会话一票」不变式的展开。

## 9. 与实现的关系

- **单一权威（SSOT）**：所有运行时事实以 `skills/codebase-docs/zj-wayfinder/SKILL.md` 为准。本 skill
  **无 `scripts/`、无 `references/`**——设计意图与操作行为是同一份 SKILL.md 的两面（durable「为什么」→ 本页；
  运行时「怎么做」→ SKILL.md）。
- **runtime closure**：SKILL.md 不回链本设计页；本页只给 reviewer 留 durable 决策与不变式，不作运行时依赖。
- **载体接缝与 plan→track 配对**：由 `design.wayfinder-roadmap-carrier-seam`（`docs/designs/zj-roadmap-driven/dual-mode.md`）拥有，本页只在 §1/§5 引它、不复述。
- **落点**：local 模式地图文件的存储约定（`docs/plans/<skill>/...`、close-out 后清理）归 [ADR 0010](../zj-adr/0010-local-file-persistence-convention.md)。

> **[未决]（诚实标记，非本页裁定）** 两处 SKILL.md 只给了约定、未形式化：① Notes 段「覆写 plan-don't-do、把执行纳入地图」的**结构**未定义（`SKILL.md:16` 只说"can override"）；② local 模式单文件 markdown schema（`🔒`/`⛔ blocked by`/`✅`/编号即身份，`SKILL.md:71-83`）目前是**书写约定**而非可校验契约。若要收紧，须回到 SKILL.md 侧定义，再回灌本页。

## Source map

- [zj-wayfinder SKILL.md](../../skills/codebase-docs/zj-wayfinder/SKILL.md) — 唯一运行时权威；本页每条断言的行源。
- [zj-roadmap-driven SKILL.md](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md) — plan → track 的下游 tracker。
- [zj-to-tickets SKILL.md](../../skills/engineering/zj-to-tickets/SKILL.md) — 把已决地图转成 blocking-aware 工单的 seam converter。

## Related authority

- [Wayfinder and roadmap carrier seam](zj-roadmap-driven/dual-mode.md) — `design.wayfinder-roadmap-carrier-seam`：载体选择与 plan→track 交接的权威页。

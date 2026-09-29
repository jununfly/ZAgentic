# 子问题：触发机制与自动派发（减 human 补位）

> 本文件对应复杂问题主文档（MASTER.md）索引中的一项，按「一事一议」原则独立讨论与求解。
> 由 `zj-discuss` 方法论 + `zj-discuss-view` companion 维护。

## 上下文

- **所属主文档：** [../MASTER.md](../MASTER.md)
- **本子问题独立性：** 聚焦「AI 如何发现并启动 zj-discuss」与「Phase 2 角色派发能否自动化」，
  与子2（质量护栏 / 体验）边界清晰，但共享「否决项」前提。
- **成功判据：** 给出 (1) 触发 / 可发现性改进方案；(2) 不踩否决项红线的薄派发层方案
  （含是否可用 Agent 工具 fresh-context 一次性 spawn 替代人肉开 N 会话）；
  (3) 自动派发下隔离性仍满足独立性阶梯 + `check_subdoc.py` 第 4 项的论证。
- **声明必需角色集：** B,C,A

## 待讨论问题（scope 草案）

- **Q1（触发失败根因）：** 为何 AI 未自动触发 zj-discuss？本次实测：`Skill` 工具报
  `Can not find skill: "zj-discuss"`，因它只索引 `~/.workbuddy/skills/` 的 user-level skill，
  不索引项目级 `skills/` 方法论文档。如何改进触发 / 可发现性（注册、递归发现、或 AI 决策时主动读 `skills/`）？
- **Q2（自动派发可行性）：** Phase 2「Human 复制到跨会话独立 Agent / 非自动分发」能否用
  `Agent` 工具 fresh-context 子 Agent 替代？r1-closure 节点 1-4 已用 `Agent` 工具 fresh-context
  子 Agent 验证 Cohen κ=0.667，满足独立性阶梯——薄派发层应长什么样？是否违反
  「否决项（会话编排运行时 / router / suite）」？
- **Q3（并发隔离）：** 自动派发下，多个角色视角并发写入如何避免竞态？隔离性（跨会话锚点）
  是否仍被 `check_subdoc.py` 第 4 项机械认可？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

> 每个视角必须由 **独立 Agent 会话** `Read` 本文件原文后撰写，禁止接受 Human 转述口径、
> 禁止「请反驳 A」式对抗指令。视角来源须显式标注 `视角来源: 跨会话独立Agent`。
> 独立视角 = 本子文档**声明必需集**中的角色（B,C,A）。
>
> **观点块 + 证据闸门（gated method ④）：** 每个独立视角须产出 **≥N 条带证据引用的观点块**
> （N 见各角色 `references/role-methods/<key>.md` 闸门段，base B/A = N=3，C 在 solo 场景 N=2）。
> 每条观点块须以 `**观点 N**` 起头，含「发现 / 影响 / 建议」三字段；「发现」须带回溯到原文的
> **证据定位**（如 `原文 Lxx`）。

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

**观点 1** — Q1 触发失败根因在平台索引边界，仓库内确定性触发才是可落地解法
- 发现：原文 L18-20 实证 `Skill` 工具报 `Can not find skill: "zj-discuss"`，原因是它只索引 `~/.workbuddy/skills/` 的 user-level skill、**不索引项目级 `skills/`**。根因落在平台工具索引范围，不在本仓库方法论本身。
- 影响：可改面被平台边界卡死——原文 L20 末句设想的"AI 主动读 `skills/`"属启发式，无确定性触发，等于把整个 zj-discuss 入口押在 AI 的"自觉"上，会再次静默失败（与本次实测同因）。依赖链是单向的：平台 Skill 索引不可控 → 自研 workaround 是唯一能排期、能验收的项。
- 建议：落地路径锁定为「仓库内确定性触发」二选一即可：(a) 项目级 `skills/` 经符号链接/注册进 user-level 索引（一次性、零运行时依赖）；(b) 提供非 Skill 入口（`launch_pack.py` 直接 `Read` 子文档+方法文件）。验收口径：在干净环境（无手动 `Skill` 调用）下完整跑通一次子文档触发，作为 DONE 证据。`谁来做`：仓库维护者；`排期`：≤0.5 人日；`风险`：若两条都不做、只靠启发式，则触发可靠性回到本次失败水平。

**观点 2** — Q2 用 `Agent` 工具 fresh-context 替代「人肉开 N 会话」会击穿独立性阶梯，薄派发层应只产静态 artifact
- 发现：原文 L22-24 称 r1-closure 节点 1-4 已用 `Agent` 工具 fresh-context 子 Agent 验证 Cohen κ=0.667，并问薄派发层是否违反「否决项（会话编排运行时 / router / suite）」。但本仓库 role-matrix L83-84、L88-90 明确：`Agent` 工具在编排会话内 spawn 的是「同会话 SubAgent(低权重)」，**不等于**跨会话独立 Agent，且明示"同会话角色扮演 ≠ 运行期隔离""易退化成回声室"。
- 影响：若把 `Agent` 工具 fresh-context 当成"替代人肉开 N 会话"的自动派发，测得的 κ 是在**非真隔离**条件下取得的——这与方法论自身守护的独立性不变式自相矛盾，等于用被否定的手段去满足被否定的断言。同时任何"运行时自动 spawn 并回收 N 个上下文"的做法即踩中否决项（会话编排运行时 / router / suite），因为它在运行时编排讨论流。
- 建议：薄派发层定义收缩为「纯静态生成器」：`launch_pack.py` 为每个角色产出一份带立场+强制 Read 原文令的 briefing 文件（原文 L63-65 已有雏形），**不**在运行时 spawn/回收 agent、不做 router。自动化的上限是"产出 N 份 briefing + 一份 Human 复制清单"，真正写视角的仍是 N 个跨会话独立会话。`谁来做`：复用现有 `launch_pack.py` 改造；`排期`：≤1 人日；`验收`：脚本输出 B/C/A 三份 briefing 且源码不含任何 Agent 编排调用；`回退`：保留手工开会话通道，脚本失败不影响主流程。

**观点 3** — Q3 并发写竞态在「每角色独立文件」约定下本不存在，合并须单写者串行化
- 发现：原文 L25-26 问自动派发下多角色并发写入如何避免竞态、隔离性是否仍被 `check_subdoc.py` 第 4 项机械认可。但本次任务的输出契约（写入 `viewpoints/sub-01-trigger-dispatch-B.md` 等独立文件）已是**每角色独立文件**，且子文档 L39-52 的视角块是主会话合并阶段产物。
- 影响：竞态仅可能发生在"多角色同时原地改同一子文档"之时；一旦强制"每角色写专属文件、子文档视角块由主会话串行合并"，写冲突在数学上消除，`check_subdoc.py` 第 4 项（跨会话独立视角 ≥N 带证据观点块）在单写者文件上可被机械判定，隔离性天然满足。真正工程风险是有人图省事把多角色视角直接 inline 进子文档同一文件并发编辑——必须明文禁止。
- 建议：把"每角色独立输出文件、合并单写者串行"作为不变式写进 SKILL.md 派发章节（沉淀项）；`check_subdoc.py` 第 4 项验证改为可针对 `viewpoints/*-<role>.md` 逐个扫描。`谁来做`：方法论维护者；`排期`：≤0.5 人日；`验收`：同时跑 N 个独立会话并发写各自文件，子文档合并零冲突且脚本零违例。

**观点 4** — 跨 Q1/Q2/Q3 的工程收敛：把"能说"逼成"能做"的最小可验收切片
- 发现：原文 L11-13 成功判据要求产出 (1) 触发改进方案 (2) 不踩否决项的薄派发层 (3) 自动派发隔离性论证，声明必需集为 B,C,A（L14）。三问都停留在"方案/论证"层，缺量化排期与验收口径。
- 影响：不补排期与验收，讨论会悬空——role-matrix L91-92 已记"结论必须给可执行沉淀指令否则不算闭环"。Q1/Q2/Q3 可落地代价合计约 2 人日，全部是现有脚本（launch_pack.py / check_subdoc.py）改造，机会成本极低，不应因"方案已谈妥"而跳过落地排期。
- 建议：定义最小闭环切片——(a) Q1 符号链接注册或 launch_pack 入口（0.5 人日）；(b) Q2 launch_pack 改为纯静态 briefing 生成器（1 人日）；(c) Q3 把每角色独立文件+串行合并写进 SKILL.md 并扩展 check_subdoc 扫描路径（0.5 人日）；三者完成后由 Human 在 conclusion 填 DONE + 沉淀指令。`风险/回退`：若平台侧后续开放项目级 Skill 索引，Q1 的 workaround 可整体删除，不增加长期负担。

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1** — 触发失败是「激活能量」问题，而非能力问题：编排者的根本痛点是「AI 不知道 zj-discuss 存在」，这比派发质量更前置
- 发现：原文 L18-20 实测 `Skill` 工具报 `Can not find skill: "zj-discuss"`，根因是它只索引 `~/.workbuddy/skills/`（user-level），不索引项目级 `skills/` 方法论文档——这是可发现性缺口，不是功能缺口；成功判据 L11 把"触发/可发现性改进方案"列在第一位。
- 影响：一个 AI 无法触发的讨论框架 = 0 使用率。无论 Q2/Q3 派发多优雅，触发失败的边际价值恒为 0。优先级上 Q1 是 Q2/Q3 的前置 gate：无可发现性则后续全无意义。量化：本次实测触发成功率 0/1（报错即 0% 激活），是整条链路上唯一的全有全无单点。
- 建议：按"用户愿不愿意用（最低摩擦优先）"排两条并存路径，均可验收：(a) 注册路径——提供 `zj-discuss install` 或软链到 `~/.workbuddy/skills/`，让宿主 `Skill` 索引命中；验收：在干净环境执行 `Skill(zj-discuss)` 返回命中而非 `Can not find skill`。(b) 约定路径（更低摩擦、不依赖宿主索引）——文档固化固定相对路径 `skills/productivity/zj-discuss/`，让 AI 在"是否启动讨论"的决策点主动 `Read`，把可发现性从"索引依赖"改为"约定依赖"；验收：在宿主索引缺失场景下，AI 仍能凭约定路径启动讨论。优先推 (b)，因它消除了对整个宿主索引机制的耦合。

**观点 2** — 自动派发必须保留「人拍板」作为愿用性闸门；κ=0.667 是信任阈值而非自动化通行证
- 发现：原文 L21-24 当前 Phase 2 是「Human 复制到跨会话独立 Agent」，r1-closure 已用 `Agent` 工具 fresh-context 子 Agent 验证 Cohen κ=0.667；原文 L67-74 仍保留 Human 拍板表。Q2 追问薄派发层是否违反「否决项（会话编排运行时/router/suite）」。
- 影响：从"开 N 会话手动复制"到"`Agent` 工具一次性 spawn 子 Agent"，human 补位成本下降约一个量级，直接命中本子问题标题"减 human 补位"。但 κ=0.667 仅属"中等一致"，用户对自动化产出的信任度与一致性正相关；在 κ 未达高一致（建议 ≥0.8）前把派发全自治化，等于"省了步骤却丢了信任"，反而降低编排者愿意采用的置信度。
- 建议：(1) 薄派发层严格定位为"调用编排"（spawn fresh-context 子 Agent 并收集输出），不引入 router/suite、不持有跨角色常驻状态，因此不踩否决项；验收：派发层代码审查确认无跨角色状态、无常驻 runtime。(2) 将 Human 拍板（原文 L67）设为 κ<0.8 时的强制闸门而非默认旁路——自动派发结果进入"待拍板"队列，主力AI 只产出"待拍板摘要"，不自动写入 conclusion；验收：自动派发后主会话输出含"待拍板"标记、conclusion 区保持空白待 Human 填。(3) 设可证伪里程碑：连续 3 个子问题自动派发 κ≥0.8，才将 Human 拍板降级为抽检；否则维持闸门。

**观点 3** — 并发隔离的产品真相：靠「分文件写」消除竞态，比「机械检测竞态」更可信；check_subdoc 第 4 项必须验收独立性而非事后发现
- 发现：原文 Q3（L25-26）追问"多角色并发写入如何避免竞态、隔离性是否仍被 check_subdoc.py 第 4 项机械认可"；而本任务的硬契约已要求"只写各自 output 文件、不编辑 sub-doc"——即隔离由写入目标分离实现（每个角色落到独立的 `sub-01-...-C.md`），sub-doc 仅在聚合阶段被人/主力AI 处理。
- 影响：编排者最怕"自动派发后角色互相覆盖写、结论被静默丢失"。若 check_subdoc 第 4 项只在事后识别竞态，等于"撞了才报警"，产品信任成本极高；真正的用户价值来自"结构上不可能竞态"——分文件即天然无锁，无需事后检测。
- 建议：(1) 将 Q3 隔离策略固化为规范：每个角色视角写独立 `viewpoints/<sub>-<role>.md`，任何角色 Agent 不直写 sub-doc，sub-doc 仅由 Human/主力AI 在结论阶段聚合；验收：grep sub-doc 确认无角色 Agent 写入痕迹，仅含聚合区块。(2) check_subdoc.py 第 4 项从"检测覆盖"升级为"验证独立性锚点"——逐文件校验每个 viewpoint 含 `视角来源: 跨会话独立Agent` 标记且路径/mtime 隔离；验收：构造"两角色同写一文件"的反例，第 4 项应判失败而非通过。可证伪性：若该反例仍通过，则第 4 项失效、需重新设计，这本身就是一个可被一次测试推翻的验收点。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

**观点 1** — Q1 触发边界：项目级 skill 不可发现性是 host 索引契约的硬边界，不能用"AI 主动读 skills/"兜底
- 发现：原文 L18-20 实测 `Skill` 工具只索引 `~/.workbuddy/skills/`（user-level），不索引项目级 `skills/`，故报 `Can not find skill`。这是宿主索引的边界，不是 zj-discuss 自身缺陷。
- 影响：若把"AI 决策时主动读 `skills/`"当作触发兜底，等于把"触发"这一不变式下沉为 LLM 的隐式推理，破坏了可机械判定的触发契约。耦合点从"Skill 工具注册"漂移成"AI 猜测项目结构"，宿主一旦改索引行为，zj-discuss 能否被唤起就无法预见——长期不可维护，且无法向后兼容旧安装方式。
- 建议：定义 host-agnostic 的发现清单（manifest）：在 zj-discuss `SKILL.md` 固定可被项目根递归命中的入口路径；保留 `Skill` 工具注册用于 user-level 安装（向后兼容不变），新增准备阶段用 `Glob` 递归扫描 `**/skills/**/SKILL.md` 作为项目级 fallback。触发必须靠可枚举的文件定位，不靠 LLM 推理。验收：在 user-level 无该 skill 的干净仓库中，`Glob **/skills/**/SKILL.md` 能定位项目级入口；既有 user-level `Skill: zj-discuss` 路径仍可用。

**观点 2** — Q2 否决项红线：用 `Agent` 工具 fresh-context 做自动派发 = 会话编排运行时，踩中否决项
- 发现：原文 L22-24 把"用 Agent 工具 fresh-context 子 Agent 替代人肉开 N 会话"列为候选，并明确询问是否违反"否决项（会话编排运行时 / router / suite）"；原文 L24 自己点名 veto 项含"会话编排运行时"。
- 影响：任何"薄派发层"若负责 spawn N 个角色子 Agent 并回收视角，它本身就是会话编排运行时 / router，与否决项字面冲突。更隐蔽的耦合：把派发逻辑写进 zj-discuss，会把编排生命周期与方法论耦合，使方法论无法脱离宿主的 Agent 工具实现——直接破坏 role-matrix L83 要求的"cross-provider 为最高隔离级"这一跨系统不变式。
- 建议：把"派发 / 编排"显式划出 zj-discuss 边界：zj-discuss 只产出 briefing（视角立场 + 强制 Read 原文令），不 spawn。派发由 Human 或独立编排工具（非 zj-discuss 内部）完成。在 role-matrix / SKILL.md 新增一条冻结不变式："zj-discuss 内部不得持有 Agent spawn 调用"。验收：`grep -n "Agent(" SKILL.md references/` 除文档举例外为零；否决项清单中"会话编排运行时"仍列于 zj-discuss 禁区内。

**观点 3** — Q2/Q3 术语漂移：`Agent` 工具 fresh-context 在 gate 语义下是 same-session，而非 Q2 声称的"满足独立性阶梯"
- 发现：原文(check_subdoc.py L228-248) 的独立性阶梯为 cross-provider > cross-session > same-session，且"same-session 是下限而非终点"，结论标 DONE 须至少有一个 `跨会话独立Agent` 锚点；原文(check_subdoc.py L153-158) 对 `同会话SubAgent(低权重)` 标记**不**施加 N 闸门。而原文 L22 称 r1-closure 用 `Agent` 工具 fresh-context 已"满足独立性阶梯"。
- 影响：存在致命的语义漂移——r1 PoC 的"独立"= fresh-context 子 Agent（同一宿主会话树内），而 gate 的"有效覆盖锚点"= `跨会话独立Agent`（不同会话）。若自动派发走 Agent 工具，产出的视角会被标 `同会话SubAgent(低权重)`，不计入 N 闸门，于是 Q3 问的"check_subdoc 第 4 项是否仍认可隔离性"答案是否定的：它只把它们当预演。Q2 的"满足阶梯"与 Q3 的"被第 4 项认可"两个前提互相矛盾，不能同真。
- 建议：在 design.md / role-matrix 统一"独立"的定义：明确 `Agent` 工具 fresh-context 属 same-session 层（仅用于分解/合成辅助、低权重），真隔离必须是 cross-session（独立会话，如本任务指示我写入独立 output 文件）。修正 Q2 措辞，删除"Agent 工具可替代跨会话独立 Agent"的误导；把 Cohen κ=0.667 仅定位为"方法可行性预验"，而非"可自动化派发的授权"。验收：gate 对 fresh-context 视角输出判为 same-session（非 cross-session 锚点），文档不再混用"独立"一词。

**观点 4** — Q3 写入隔离：check_subdoc.py 第 4 项只扫描单个 sub-doc 文件，跨文件 viewpoint 写入会令闸门机械失效
- 发现：原文(check_subdoc.py L251-269) 的 `check()` 仅对传入的 sub-doc 路径 `split_sections`，在文件内找 `### 视角` 与 `**观点` 块；`gate_n_for_role` 按角色读 N，`_check_viewpoint_gate` 统计的 evidence_blocks 全部来自该单文件 body。而本任务 HARD CONTRACT 要求各角色写到独立 output 文件 `viewpoints/sub-01-trigger-dispatch-A.md`，而非 sub-doc 内联；原文 L49-52 的子文档内 `### 视角：A` 仅为空占位。
- 影响：若自动派发改为"每角色写独立 viewpoint 文件"、而 sub-doc 内只留空占位，则 check_subdoc 在 sub-doc 内数到的有效观点 = 0 < N=3 → 第 4 项判 FAIL。即 Q3 的"隔离仍被第 4 项机械认可"在当前实现下不成立，除非 sub-doc 同步内联观点，或 gate 扩展为 glob `viewpoints/`。这是并发写入隔离与机械闸门之间的耦合缺口，必须显式闭合。
- 建议：二选一固化，禁止"写完独立文件就当闭环"：(a) 仍以 sub-doc 内联为唯一真源，独立文件仅作中转，最终由编排侧把观点回流到 `### 视角` 段（gate 不变）；或 (b) 扩展 check_subdoc 入口，接受目录 / glob `viewpoints/<sub>-<role>.md` 合并后再判 N。验收：对当前 sub-01 跑 `python3 check_subdoc.py`，若角色视角落在独立文件，gate 必须要么合并识别、要么显式失败，不许静默通过。

**观点 5** — 向后兼容护栏：任何触发 / 派发改动都不得破坏现有"Human 复制到跨会话独立 Agent"主路径
- 发现：原文 L21-22、L50-52 当前已验证主路径是 Human 把 briefing 复制到跨会话独立 Agent，子文档预留 `### 视角：A` 段并由 gate 判定。这是已跑通的可运行契约。
- 影响：Q1/Q2/Q3 引入新触发或新派发时，最大向后兼容风险是旧路径（人肉派发 + 内联视角 + 现有 gate）在改完后反而 broken，或新约定引入后无人回填 sub-doc，触发 gate 非降级红线（原文 check_subdoc.py L228-248）或静默降级，使"以前能用"变成"现在不可证"。
- 建议：把"已验证人肉派发主路径"列为冻结不变式写入 ADR；任何新方案须 100% 兼容它（仍可纯人肉派发并令 gate 通过）。递归发现 / briefing 生成仅为增量，不作替换。在 MASTER.md 跨子文档约束登记："触发/派发改进不得违反已验证人肉派发契约"。验收：改动落地后，一条纯人肉派发的 regression 用例 gate 仍 OK，证明未破坏旧契约。

> 覆盖**声明必需集**后即停加视角。动态议程可能为未解问题或尖锐分歧增派聚焦轮，但不为凑数加视角。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`
本次 meta 跑通暴露核心张力：触发失败在宿主 Skill 索引边界（非方法论缺陷）；用 Agent 工具 fresh-context 派发被 A 视角证伪为 same-session 低权重层——不满足非降级锚点、且踩中「否决项（会话编排运行时）」；并发靠「每角色独立文件 + 单写者串行合并」消除。编排者倾向：派发自动化上限 = 静态 briefing 生成器（launch_pack.py），真隔离仍须 Human 开跨会话会话；触发改双通路（user-level 注册 + Glob 项目级 fallback）。对 Q1/Q2/Q3 收敛见 conclusion。

## 视角 briefing（临时脚手架，阶段 2 删除候选）

> 生成方式（静态，非运行时）：
> `python3 <skill>/scripts/launch_pack.py sub-01-trigger-dispatch.md --out briefings`
> 启动包落点：`briefings/sub-01-trigger-dispatch-launchpack-<role>.md`。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- |
| 1 | B | <采纳 / 修正 / 否决 + 理由> | 否 | 允许主力 AI 凭证据 challenge |
| 2 | C | <…> | 否 | 技术偏差不静默吞 |
| 3 | A | <…> | 否 | |
| … | … | … | … | … |

## conclusion（含沉淀指令）

> 结论必须给出**可执行沉淀指令**，否则不算闭环。结论不得引用同会话 SubAgent 预演产出作为权威依据。

- **子问题结论：** 触发失败根因在宿主 Skill 索引边界（非方法论缺陷）；「用 Agent 工具 fresh-context 替代人肉派发」被证伪——它在独立性阶梯里属 same-session 低权重层，不满足非降级锚点，且踩中「否决项（会话编排运行时）」；并发隔离靠「每角色独立文件 + 单写者串行合并」消除，但 gate 须能扫描合并后的内联视角。
- **解法：**
  - Q1 触发/可发现性：双通路——(a) user-level 注册/软链（向后兼容）；(b) 项目级 fallback：准备阶段用 `Glob **/skills/**/SKILL.md` 定位入口，不依赖 LLM 推理。
  - Q2 派发自动化边界：zj-discuss 内部只产静态 briefing（launch_pack.py），不 spawn Agent；「用 Agent 工具做自动派发」= 会话编排运行时，明确列入否决项禁区。此前「r1-closure 节点 1-4 的 κ=0.667 满足独立性」是误读——该测量在 same-session 条件下取得，仅作方法可行性预验，不作自动化授权。
  - Q3 并发写入：固化「每角色写独立文件、子文档仅由主力AI/Human 在结论阶段串行聚合」；若保留独立文件，check_subdoc 须接受目录/glob 合并扫描，否则第 4 项机械失效（本次已合并内联以保 gate 有效）。
- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：`SKILL.md` 在「外部能力集成边界/否决项」处补「zj-discuss 内部不得持有 Agent spawn 调用」冻结不变式 + 明确「Agent 工具 fresh-context = same-session 层」；`docs/designs/zj-discuss/architecture.md` 补触发双通路设计；`role-matrix.md` 统一「独立」定义（cross-session ≠ same-session）。
  - 跨子文档约束登记：回填 MASTER.md 跨子文档约束（否决项语义已核实：Agent 工具派发踩红线）。
  - 待删临时脚手架：briefings/（阶段 2 删除候选）。
- **状态协议：** DONE_WITH_CONCERNS（「减 human 补位」目标与独立性闸门存在结构性张力，已澄清但未消除；是否放宽阶梯待 zj 决策）

## AI 上下文 digest（可选，voice-only）

```text
<在此粘贴本子问题的 voice-only digest：zj-discuss 的立场/语气简述，或留空>
```

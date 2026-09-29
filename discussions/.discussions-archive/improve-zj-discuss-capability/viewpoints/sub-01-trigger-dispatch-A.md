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

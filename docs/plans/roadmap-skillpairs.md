<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `roadmap-skillpairs.json` | 最后更新: 2026-08-14 17:35:15

[~][X+] 1. A↔B skill-pair 对比与处理
├── [x][X+] 1-3. 同源对逐个吸收B优点(zj-tdd/diagnose/triage/to-issues/to-prd/grill-with-docs/grill-me/prototype/improve-arch/setup/write-a-skill)
│   ├── [x][X+] 1-3-1. zj-tdd ↔ tdd: 吸收『测试只落预商定 seam』纪律
│   ├── [x][X+] 1-3-2. zj-diagnose ↔ diagnosing-bugs: 吸收『Redact 脱敏纪律』
│   ├── [x][X+] 1-3-3. zj-triage ↔ triage: 完整移植 B 含 PR-as-request-surface 维度
│   ├── [x][X+] 1-3-4. zj-to-issues ↔ to-tickets: 采纳 B 的 to-tickets 为 zj-to-tickets, 删除 zj-to-issues
│   ├── [x][X+] 1-3-5. zj-to-prd ↔ to-spec: 强化 seam 确认环节
│   ├── [x][X+] 1-3-6. zj-grill-with-docs: 删除(内容并入 zj-grilling + zj-domain-modeling), 统一 ZJ- 文档命名
│   ├── [x][X+] 1-3-7. zj-grill-me ↔ grilling: 吸收 B『frontier/rounds 机制』
│   ├── [x][X+] 1-3-8. zj-prototype ↔ prototype: 删除原 zj-prototype, 吸纳 B prototype 为 zj-prototype
│   ├── [x][X+] 1-3-9. zj-improve-codebase-architecture ↔ B: 吸收『scope before scan』
│   ├── [x][X+] 1-3-10. zj-setup-skills ↔ setup-matt-pocock-skills: 核对微调
│   └── [x][X+] 1-3-11. zj-write-a-skill ↔ writing-for-agents: 深度吸收 B 元方法论
├── [x][X+] 1-4. B独有评估移植进A(code-review/research/wayfinder/teach/wait-what/to-questionnaire等)
│   ├── [x][X+] 1-4-1. code-review (B独有): 评估移植进 A
│   ├── [x][X+] 1-4-2. research (B独有): 吸纳为 zj-research
│   ├── [x][X+] 1-4-3. wayfinder (B独有): 移植为 zj-wayfinder
│   ├── [x][X+] 1-4-4. teach (B独有): 评估移植进 A
│   ├── [x][X+] 1-4-5. wait-what (B独有): 评估移植
│   ├── [x][X+] 1-4-6. to-questionnaire (B独有): 评估移植
│   └── [x][Y+] 1-4-7. wizard/implement/ask-matt/resolving-merge-conflicts (B独有 4 合一): 评估移植
├── [x][X+] 1-5. A独有保留维护(roadmap-driven/caveman/zoom-out/edit-article/obsidian-vault)
│   ├── [x][X+] 1-5-1. zj-roadmap-driven (A独有): 保留 + 修 Windows lock 清理 bug
│   ├── [x][X+] 1-5-2. zj-caveman (A独有): 保留
│   ├── [x][X+] 1-5-3. zj-zoom-out (A独有 engineering): 保留 + sidecar 补齐
│   └── [x][X+] 1-5-4. zj-edit-article + zj-obsidian-vault (A独有 personal): 保留
└── [ ][X+] 1-6. 跨阶段 skill 抽象 (中性, 不属于 A 也不属于 B, 但工程需要)
    ├── [x][X+] 1-6-1. 回顾反思型: zj-debrief (完工后复盘, 沉淀 ZJ-CONTEXT.md)
    ├── [~][X+] 1-6-2. 自我质疑型: zj-steelman (先帮方案找最强论据, 避免早期被否)
    └── [ ][X+] 1-6-3. 预演型: zj-dry-run (推演 N 步后卡点, 提前定位决策瓶颈)

### 当前施工：1-6-2. 自我质疑型: zj-steelman (先帮方案找最强论据, 避免早期被否)

1-6-2 实现启动: 17:35 8/14, 按 handoff 顺序, 1-6-1 zj-debrief 已完成 (commit 8473463), 现在动 zj-steelman。grilling 4 决策已齐, 复用原文, 不重 grill

**决策：**
- Q: 互补关系分析 → 待评估: steelman ↔ grilling + handoff (**互补对象**: zj-grilling (主动挑战) + zj-handoff (交接总结)。**互补点**: 方向互补 — grilling 是'找方案的弱点' (反向), zj-steelman 是'找方案的强点' (正向)。两者并用 = 全面 stress test。**潜在能力**: 1) 列方案的核心假设, 逐条写最强支持论据 (steelman 本身); 2) 如果最强论据都不强, 才建议 grill; 3) 把最强论据写进 /zj-handoff 或 /zj-prototype 备注里。**落点**: 探索中 — 可能做成 zj-grilling 的 flag/前置段, 而非独立 skill。**待评估**: A 仓是否需要独立 skill? 'steelman 失败则 grill' 是 1 步动作, 不一定需要包装成 skill。需 1-6-2 explore 进一步确认是否独立还是作为 flag 合并到 zj-grilling。)
- Q: Q1: zj-steelman 是独立 skill 还是 zj-grilling 的 flag/前置段? → A. 独立 skill — steelman 有自己的触发时机, 不一定紧接着 grill (**理由**: steelman 和 grilling 心智模型相反 (辩护 vs 攻击)。混在一起 agent 角色冲突。独立 skill 让用户明确选择'我现在要确认方案 (steelman) 还是要质疑方案 (grilling)'。steelman 失败后建议 grill 是路由不是合并 — 就像 zj-triage 失败后建议 zj-to-tickets 一样, 不意味着 triage 要吞掉 to-tickets。steelman 成功 = 方案有底气可继续推进; steelman 失败 = 才调 /zj-grilling 深入质疑。)
- Q: Q1: zj-steelman 是独立 skill 还是 zj-grilling 的 flag/前置段? → A. 独立 skill — steelman 有自己的触发时机, 不一定紧接着 grill (**理由**: steelman 和 grilling 心智模型相反 (辩护 vs 攻击)。混在一起 agent 角色冲突。独立 skill 让用户明确选择'我现在要确认方案 (steelman) 还是要质疑方案 (grilling)'。steelman 失败后建议 grill 是路由不是合并 — 就像 zj-triage 失败后建议 zj-to-tickets 一样, 不意味着 triage 要吞掉 to-tickets。steelman 成功 = 方案有底气可继续推进; steelman 失败 = 才调 /zj-grilling 深入质疑。)
- Q: Q2: steelman 产出什么、写到哪里? → A. 就地输出最强论据清单 — 不写文件, 最轻量 (**理由**: steelman 的核心价值是即时判定方案站不站得住, 用户看完就知道该推进还是该 grill。论据清单本身是过程产物, 不是需要持久化的档案。如果用户觉得论据有用想留存, 可手动追加到 handoff/prototype, 但 skill 不强制写文件。原文提到'把最强论据写进 /zj-handoff 或 /zj-prototype 备注'作为可选能力, 不作为默认产物落点。)
- Q: Q2: steelman 产出什么、写到哪里? → A. 就地输出最强论据清单 — 不写文件, 最轻量 (**理由**: steelman 的核心价值是即时判定方案站不站得住, 用户看完就知道该推进还是该 grill。论据清单本身是过程产物, 不是需要持久化的档案。如果用户觉得论据有用想留存, 可手动追加到 handoff/prototype, 但 skill 不强制写文件。原文提到'把最强论据写进 /zj-handoff 或 /zj-prototype 备注'作为可选能力, 不作为默认产物落点。)
- Q: Q3: steelman 是交互式多轮还是单次输出? → A. 单次输出 — 用户给方案, steelman 一次性产出假设清单+最强论据+强度判定+路由建议 (**理由**: 原文'先帮方案找最强论据'的'先'字暗示快速一步动作。steelman 价值是快速给方案底气判定, 做成多轮交互就跟 grilling 一样重, 失去差异化。假设错了用户会纠正, 但不需要设计成交互流程。复用原文定位, 不额外发挥。)
- Q: Q3: steelman 是交互式多轮还是单次输出? → A. 单次输出 — 用户给方案, steelman 一次性产出假设清单+最强论据+强度判定+路由建议 (**理由**: 原文'先帮方案找最强论据'的'先'字暗示快速一步动作。steelman 价值是快速给方案底气判定, 做成多轮交互就跟 grilling 一样重, 失去差异化。假设错了用户会纠正, 但不需要设计成交互流程。复用原文定位, 不额外发挥。)
- Q: Q4: 其余设计维度 (桶归属/触发时机/核心动作) 复用原文 → 复用原文 — 不额外 grilling (**原则**: 1-6 下三个 skill 的 grilling 只问需要用户拍板的问题 (主要是文件归置), 其余维度直接引用原文。1-6-2 的文件归置已在 Q2 解决 (就地输出不写文件)。**原文覆盖的维度**: (1) 桶=engineering (与 zj-grilling 同属自我质疑型, 同桶); (2) 触发时机=方案早期, 避免过早否定; (3) 核心动作=列核心假设→逐条写最强支持论据→判定论据强度→不强才建议 grill; (4) 互补关系=与 grilling 方向互补 (辩护 vs 攻击), steelman 失败路由到 grill。)
- Q: Q4: 其余设计维度 (桶归属/触发时机/核心动作) 复用原文 → 复用原文 — 不额外 grilling (**原则**: 1-6 下三个 skill 的 grilling 只问需要用户拍板的问题 (主要是文件归置), 其余维度直接引用原文。1-6-2 的文件归置已在 Q2 解决 (就地输出不写文件)。**原文覆盖的维度**: (1) 桶=engineering (与 zj-grilling 同属自我质疑型, 同桶); (2) 触发时机=方案早期, 避免过早否定; (3) 核心动作=列核心假设→逐条写最强支持论据→判定论据强度→不强才建议 grill; (4) 互补关系=与 grilling 方向互补 (辩护 vs 攻击), steelman 失败路由到 grill。)
<!-- ROADMAP_SECTION_END -->

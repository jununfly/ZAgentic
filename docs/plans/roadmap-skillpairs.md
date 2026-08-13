<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `roadmap-skillpairs.json` | 最后更新: 2026-08-13 20:08:45

[~][X+] 1. A↔B skill-pair 对比与处理
├── [ ][X+] 1-3. 同源对逐个吸收B优点(zj-tdd/diagnose/triage/to-issues/to-prd/grill-with-docs/grill-me/prototype/improve-arch/setup/write-a-skill)
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
├── [ ][X+] 1-4. B独有评估移植进A(code-review/research/wayfinder/teach/wait-what/to-questionnaire等)
│   ├── [x][X+] 1-4-1. code-review (B独有): 评估移植进 A
│   ├── [x][X+] 1-4-2. research (B独有): 吸纳为 zj-research
│   ├── [x][X+] 1-4-3. wayfinder (B独有): 移植为 zj-wayfinder
│   ├── [x][X+] 1-4-4. teach (B独有): 评估移植进 A
│   ├── [x][X+] 1-4-5. wait-what (B独有): 评估移植
│   ├── [x][X+] 1-4-6. to-questionnaire (B独有): 评估移植
│   └── [ ][X+] 1-4-7. wizard/implement/ask-matt/resolving-merge-conflicts (B独有): 评估
└── [ ][X+] 1-5. A独有保留维护(roadmap-driven/caveman/zoom-out/edit-article/obsidian-vault)
    ├── [x][X+] 1-5-1. zj-roadmap-driven (A独有): 保留 + 修 Windows lock 清理 bug
    ├── [ ][X+] 1-5-2. zj-caveman (A独有): 保留
    ├── [ ][X+] 1-5-3. zj-zoom-out (A独有): 保留
    └── [ ][X+] 1-5-4. zj-edit-article + zj-obsidian-vault (A独有 personal): 保留

### 当前施工：1. A↔B skill-pair 对比与处理

1-3 同源对 11/11 完成; 1-4 已处理 1-4-1/2/3/4/5/6 (剩 1-4-7 wizard/implement/ask-matt/resolving-merge-conflicts 4 合一); 1-5 已处理 1-5-1 (剩 1-5-2/3/4)。⚠️ 1-3 复查: 1-3-10(setup) + 1-3-3(triage) PR flag 联动 + Q4=D + 1-3-6/7 误删恢复 (zj-grill-me + zj-grill-with-docs 已恢复, commit 7227350)。下一步: 1-4-7 评估。

**决策：**
- Q: 调研基线 → A是B的中文化派生: engineering同源对几乎逐字对应, misc四对diff=0。B优势在架构拆细(grilling/domain-modeling/codebase-design独立可组合)与元方法论(writing-for-agents)
- Q: 处理策略 → 以skill-pair为颗粒度依次处理: 同源对吸收B优点; B独有评估移植; A独有保留维护

**当前子树：**
├── [ ][X+] 1-3. 同源对逐个吸收B优点(zj-tdd/diagnose/triage/to-issues/to-prd/grill-with-docs/grill-me/prototype/improve-arch/setup/write-a-skill)
│   ... 11 more child nodes; run tree 1-3 --depth 2 for full view
├── [ ][X+] 1-4. B独有评估移植进A(code-review/research/wayfinder/teach/wait-what/to-questionnaire等)
│   ... 7 more child nodes; run tree 1-4 --depth 2 for full view
└── [ ][X+] 1-5. A独有保留维护(roadmap-driven/caveman/zoom-out/edit-article/obsidian-vault)
    ... 4 more child nodes; run tree 1-5 --depth 2 for full view
<!-- ROADMAP_SECTION_END -->

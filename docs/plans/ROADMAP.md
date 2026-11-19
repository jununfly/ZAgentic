<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

<!-- zj-roadmap-authority/v1
role: process-state
durable-citation: forbidden
promote-via: ADR|design|contract|runtime-evidence
-->

> 数据文件: `roadmap.json` | 最后更新: 2026-11-19 21:12:19

[~][X+] 1. Issue #275 一步到位修复（zj-docs-ontology / zj-docs-architecture）
├── [x][X+] 1-1. PR1 工具正确性：Fix 2+3+6（witness 单基准 / moves 可注入 / 输出锚定）
│   ├── [x][X+] 1-1-1. Fix 2 witness 路径单基准：emit 写纯文件名、inspect 统一 case_dir、删 root 基准（TDD 红→绿，修 L1/L2 断言）
│   ├── [x][X+] 1-1-2. Fix 3 moves 注入 + rename 三级判定：git 原生检测→pending_moves(signal)→确认豁免；删 stub workaround
│   └── [x][X+] 1-1-3. Fix 6 DEFAULT_OUT 锚定 {repo-root}/tmp/skills-outputs/zj-docs-ontology
├── [ ][X+] 1-2. PR2 CLI 表面积 + SKILL.md：Fix 1（作用对象一等声明 / 能力边界）
│   ├── [ ][X+] 1-2-1. Fix 1a --object 作用对象声明 + report 拆 object_of_governance / pass_topic 两字段
│   ├── [ ][X+] 1-2-2. Fix 1b capability_boundary 块 + CAPABILITY_NOT_COVERED（signal，指向替代能力）
│   └── [ ][X+] 1-2-3. Fix 1c SKILL.md description 重写为能力边界声明（L5）
├── [ ][X+] 1-3. PR3 跨 skill：Fix 4+5（role 显式声明 / one-home 信号）
│   ├── [ ][X+] 1-3-1. Fix 4 map 条目 role: primary|supporting 替代路径子串判定；删 /architecture/ 子串；fail-open + PAGE_ROLE_UNDECLARED（L4）
│   ├── [ ][X+] 1-3-2. Fix 5 duplicate_fact_scan + PARALLEL_ONTOLOGY_SUSPECTED（signal-only，n-gram 粗筛不评分）
│   └── [ ][X+] 1-3-3. L7 边界钉住：扫描只产 signal 不改 exit 语义，测试显式断言（对齐 doc-slop 非门禁裁决）
└── [!][X+] 1-4. 收尾：legacy 裁决记录 + docs 同步 + 三副本删重装 + 门禁双向验
    ├── [ ][X+] 1-4-1. L3/L8 Ruling v7 修订 + tombstone 语义回归：ADR amendment 留痕
    ├── [ ][X+] 1-4-2. docs 桶描述同步 + 三副本 git archive+rsync 删重装
    └── [ ][X+] 1-4-3. CI 门禁双向验 + issue #275 验收对照报告并关闭
<details><summary>阻塞链：1 个节点被阻塞</summary>

- 1-4. 收尾：legacy 裁决记录 + docs 同步 + 三副本删重装 + 门禁双向验 ← e3: 1-2. PR2 CLI 表面积 + SKILL.md：Fix 1（作用对象一等声明 / 能力边界） [ ], e4: 1-3. PR3 跨 skill：Fix 4+5（role 显式声明 / one-home 信号） [ ]

</details>


### 下一步可开工（ready 前 3）

- 1-2. PR2 CLI 表面积 + SKILL.md：Fix 1（作用对象一等声明 / 能力边界） [ ]
- 1-2-1. Fix 1a --object 作用对象声明 + report 拆 object_of_governance / pass_topic 两字段 [ ]
- 1-2-2. Fix 1b capability_boundary 块 + CAPABILITY_NOT_COVERED（signal，指向替代能力） [ ]
<!-- ROADMAP_SECTION_END -->

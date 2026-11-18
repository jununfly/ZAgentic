<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

<!-- zj-roadmap-authority/v1
role: process-state
durable-citation: forbidden
promote-via: ADR|design|contract|runtime-evidence
-->

> 数据文件: `roadmap.json` | 最后更新: 2026-11-19 00:09:24

[~][X+] 1. codebase-docs 契约可执行性与 bucket 重构
├── [x][X+] 1-1. P0 Ruling 1：canonical-preset 单一源与双层参照系
│   ├── [x][X+] 1-1-1. 新建 canonical-preset.json 并将两张值域表降为指针
│   ├── [x][X+] 1-1-2. 编写 P1a 红测：首启空 HEAD、词表违反、合法分歧、单一源、rename 三组
│   ├── [x][X+] 1-1-3. 实现诊断码接线并删除 LONG_LIVED/PROCESS 硬编码常量
│   └── [x][X+] 1-1-4. 验证 5 ERROR + 6 signal 逐码退出码断言
├── [x][X+] 1-2. 共享规则单一权威源与发布期 inline 机制
│   ├── [x][X+] 1-2-1. 新建 docs/skill-conventions/ JSON 规则源
│   ├── [x][X+] 1-2-2. 修订 ADR 0007 与 ontology.schema.json 指向新权威源
│   ├── [x][X+] 1-2-3. 为消费 skill 加 consumes/extensions 声明
│   ├── [x][X+] 1-2-4. 实现 repo-root generator 幂等内联 BASE_RULES 块
│   ├── [x][X+] 1-2-5. architecture validator 删除硬编码枚举改读内联值域
│   ├── [x][X+] 1-2-6. 实现三道检查：closed schema、byte-equal re-render、canary mutation
│   └── [x][X+] 1-2-7. 将一致性 gate 作为 job 并入 skill-closure-lint
├── [ ][X+] 1-3. bucket 重排裁决落地
│   ├── [ ][X+] 1-3-1. 删除 zj-grill-with-docs 及 skills-list 条目
│   └── [ ][X+] 1-3-2. 记录 bucket 外两个 base skill 的 portability caveat
└── [ ][X+] 1-4. 收尾与 close-out
    ├── [ ][X+] 1-4-1. 处置 issue #264 状态
    ├── [ ][X+] 1-4-2. 归档 durable conclusions 到 ADR、bucket README、SKILL.md、ZJ-CONTEXT.md
    └── [!][X+] 1-4-3. 清理 docs/plans/ 过程材料
<details><summary>阻塞链：1 个节点被阻塞</summary>

- 1-4-3. 清理 docs/plans/ 过程材料 ← e9: 1-4-2. 归档 durable conclusions 到 ADR、bucket README、SKILL.md、ZJ-CONTEXT.md [ ]

</details>


### 下一步可开工（ready 前 3）

- 1-3. bucket 重排裁决落地 [ ]
- 1-3-1. 删除 zj-grill-with-docs 及 skills-list 条目 [ ]
- 1-3-2. 记录 bucket 外两个 base skill 的 portability caveat [ ]
<!-- ROADMAP_SECTION_END -->

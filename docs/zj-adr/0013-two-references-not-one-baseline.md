---
doc-kind: adr
authority: historical
status: accepted
issue: "264"
---
> 时点说明：本页记录 2026-11-17 → 2026-11-18 `zj-docs-ontology` 治理制门工作（issue #264，
> PR #265/#266/#271）形成的一项架构决策。原裁决过程见当时的 process material（已按 ADR 0010
> 在 close-out 清理）；本页是它的长期权威，路径与码名以本页为准。

# 两个参照系，而非一个 baseline：canonical preset + HEAD 快照

## Context

issue #264 要求把 `zj-docs-ontology` 的执行协议从"靠 agent 自觉报告"升级为"靠机械制门暴露"
——跳过必跑步骤、绕过 retirement 删除、把绿灯当成内容正确，都要能被机械结果揭露。

实现 `UNDECLARED_RETIREMENT` 制门时需要回答一个看似简单的问题：**跟什么比，才算"一个已跟踪
页面未经声明就消失了"？** 这个"基线"概念经四次修订才定稿，每次都被一个反例推翻：

1. v1：`git show HEAD:<map>`（对比上一版 doc-map）。错——map 只是导航层，看不见 evidence
   与其他长期页面，删除它们不会在 map diff 里出现。
2. v2：全部 `git HEAD` 跟踪文件清单（roster）。比 v1 完整，但仍把两个不同的问题压进一个词。
3. v3：v2 被 zj 的两个反例打破——(a) 首次 setup 时 HEAD 里没有 docs，roster 为空，执行者只能
   临场发挥，没有一个真实的"应该是什么"作参照；(b) 若上一版状态被错误归档或质量低劣，以它为
   基线等于把坏状态传播下去。根因：**"baseline"一词同时承载了"应该存在什么"（规范性）与
   "上次存在什么"（观测性）**，二者必须拆成两个独立参照系。
4. v4（Human 裁决，Option B）：规范性参照系的载体定为随 skill 发布的机器可读
   `skills/codebase-docs/zj-docs-ontology/references/canonical-preset.json`；
   `governance-contract.md` / `kind-templates.md` 降为指向它的 reference，不再人肉镜像其内容。
5. v5（Human 裁决）：单个 `PRESET_DRIFT` 码 conflate 了两类偏差，拆为机械可判定的
   `PRESET_VOCABULARY_VIOLATION`（ERROR）与允许分歧的 `PRESET_DIVERGENCE`（signal），
   `PRESET_DRIFT` 作为含糊码退役。

## Decision

**存在两个不同的参照系，把它们混为一谈就是缺陷本身。**

| 参照系 | 回答的问题 | 来源 | 用途 |
|---|---|---|---|
| **Canonical preset**（规范性 normative） | "一个健康的文档系统*应该*包含什么？" | 随 skill 发布：`skills/codebase-docs/zj-docs-ontology/references/canonical-preset.json` 是唯一机器可读源；`doc-slop-checklist.md` 与 fixture 样例仅为人工审计材料 | 首启 setup；对既有树的质量判断 |
| **HEAD 快照**（观测性 observed） | "上次提交的状态*实际*包含什么？" | `git ls-tree -r --name-only HEAD` | **仅**用于漂移/消失检测 |

两条不可混淆的规则：

- **首启（HEAD 为空）**：以 canonical preset 为基线，不以空 roster 为基线。工具不发空壳、
  不让执行者临场发挥，而是发出一个类别集与 kind 骨架均取自 `canonical-preset.json` 的
  `bootstrap` proposal；HEAD 快照在此情形**不适用**，发 `BASELINE_NOT_APPLICABLE` signal，
  且不对空 roster 触发 `UNDECLARED_RETIREMENT`。setup 质量按 preset 判断，不按 git 判断。
- **上一版状态错位或质量低劣**：HEAD 快照只记录"存在过什么"，**永远不是"应该是什么"的质量
  标尺**。质量按 canonical preset 判断（preset 每个 kind 的 `Job` / `Does NOT belong` /
  `Must-write sections` 字段，加 `doc-slop-checklist.md` 作审计材料）。据此拆出三种结果：
  - 封闭词表违反（如 `doc-kind` 超出值域、声明的 kind 在 templates 无对应、primary 的
    `authority-id` 数不为 1）→ `PRESET_VOCABULARY_VIOLATION`，ERROR（退出非零）。证据是
    对固定枚举的机械事实，不依赖执行者叙述。
  - 契约允许的分歧（如缺少某些 long-lived 类别、覆盖 `Must-write sections`、目标仓兼容性
    胜出约定）→ `PRESET_DIVERGENCE`，signal（退出零）。机械无法将其与缺陷区分，升级会惩罚
    每一次合法定制；报告点名具体 preset key，永不自动修复。
  - 语义/质量漂移（内容单薄、断言过时、focused check 未真跑）→ preset 的 focused checks 是
    **审计清单而非门禁**，报 signal、绝不退出非零、无诊断码。

消失检测仍使用 HEAD roster，但被明确收窄为**仅**回答"一个已跟踪文件是否未经声明就消失"——
它对被删文件的质量不作任何断言，也绝不负责填补"应该有什么"（那是 preset 的职责）。

来源单一：`canonical-preset.json` 是类别集与每-kind 词表的唯一机器可读源；两张 Markdown 表
降为指向它的指针，不保留人肉副本；`docs_governance.py` 删除硬编码 `LONG_LIVED`/`PROCESS`
常量改为加载该 JSON。JSON 随 skill 安装、是脚本同级文件，路径按 skill root 解析（非 CWD、
非 repo root）——符合 skill runtime closure。JSON 缺失发 `PRESET_UNAVAILABLE` signal（退出零）
且不发起任何 bootstrap/preset 断言，绝不静默回退到旧常量。

## Consequences

- **ERROR 与 signal 的边界由证据性质决定**：能用机械事实对着固定枚举/HEAD roster 判定的
  违反才是 ERROR（非零）；需要判断"应该是什么"或依赖执行者自述的一律 signal（零）或审计清单。
  这是 `PRESET_VOCABULARY_VIOLATION` / `UNDECLARED_RETIREMENT` 与 `PRESET_DIVERGENCE` /
  `BASELINE_NOT_APPLICABLE` / `PRESET_UNAVAILABLE` 分道的根本原因，也由退出码契约固定。
- **"绿灯 ≠ 内容正确"落到结构里**：机械检查只确认内容在这些维度上自洽，语义正确性始终
  留给 review。裸 `--validate`（无 pass topic）只能做 shape-only 检查，发
  `EXEC_CHECKLIST_NOT_DECLARED` signal 声明自己不是一次完整 pass。
- **rename 的 fail-closed 规则**：`git mv` 在 HEAD roster diff 里表现为"删+增"。唯一可接受的
  豁免是已确认 proposal 中的 `moves` 条目（携带同一 `confirmation_id`）；验证时从
  `(HEAD − current)` 减去被点名的旧路径。不做哈希配对。未点名的消失一律触发
  `UNDECLARED_RETIREMENT` 非零，并提示若为 rename 则补 `moves` 重跑。
  （该规则即后续口头称呼的 "Ruling v7"；2026-11-20 已由 issue #275 修订为三级判定——
  git 原生 rename 证据进 `pending_moves` 降级 signal，见文末 Amendment。）
- **范围边界**：roster 看不见未跟踪文件，报告须声明该边界；`docs/plans/`、`docs/zj-retros/`
  等过程目录豁免。
- **持久化**：本决策此前只存活于 gitignored 的 process material 与代码/测试；该 process 在
  close-out 清理后，本页成为它的长期权威。相关的机械语义由
  `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md`、
  `skills/codebase-docs/zj-docs-ontology/references/proposal-tool-contract.md` 与
  `zj-docs-ontology/tests/` 中的回归测试持有；本页不复述其实现细节。

## Amendment (2026-11-20)：rename fail-closed 规则修订 + tombstone 语义回归（issue #275）

issue #275（PR #277/#278/#279，merge `ddab5d3`）实证了上文 Consequences「rename 的
fail-closed 规则」（Ruling v7）的一条执行裂缝：CLI 没有任何 `moves` 注入途径，
`UNDECLARED_RETIREMENT` 的修复提示指向一条不存在的路——合规 `git mv` 在机械层面无法豁免，
执行者只能靠"留一个无内容的 stub 让原路径存在"过门禁。stub 既非 tombstone 也无
`retired-to:`，不是 rename 的准确表达，只是满足观察边界的空壳。

修订如下（只改 rename 豁免的证据来源集；本页 Decision——两个参照系、消失检测用 HEAD roster
的收窄边界、不做哈希配对——全部维持）：

1. **三级判定**替代"proposal-named moves only"：
   - 消失路径命中已确认 proposal 的 `moves` → 完全豁免（原路径不变）；
   - 命中 git 原生 rename 证据（`git status --porcelain=v1 -z` 的 staged rename +
     `git diff --name-status -M HEAD` 的 unstaged rename）→ 进报告 `pending_moves`，降级为
     signal `RENAME_AWAITING_CONFIRMATION`（退出零），等 Human 在 proposal 中确认；
   - 无任何 rename 证据的消失 → `UNDECLARED_RETIREMENT` 仍为 ERROR，不变。
   证据来源是 git 自己的两类声明，不是内容哈希配对——v7 反对 hash-pairing 的理由
   （内容相同≠移动）继续成立，且更彻底。
2. **tombstone 语义回归**（legacy 冲突表 L8）：删除"无内容 stub 过门禁"的 workaround 语义。
   rename 不再需要任何 tombstone stub；tombstone 回归 Retirement 生命周期本义——
   内容被一个指认新位置的短页替代，属 retire 阶段在"留旧页"与"断链"之间的第三选项，
   不是为了让观察边界通过而存在的空壳。现行陈述见
   `zj-docs-ontology` SKILL.md lifecycle 第 4 条与 `governance-contract.md` Retirement 节。

机械语义由 `docs_governance.py` 的 `detect_pending_moves` 与
`skills/codebase-docs/zj-docs-ontology/tests/test_issue275_moves.py` 持有；
本页不再复述实现细节。

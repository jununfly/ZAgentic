**观点 1** — bug1 的修复必须做成脚本强制，而非给提示词补一句
- 发现：原文 L16-18 明确根因是「该步靠 AI 自觉，无强制」，并承认 launch_pack 启动包已带 intro，但「准备阶段清单未强制」。也就是说失败点正是 AI 自由生成的那段角色推荐清单，目前没有任何脚本形态的产物约束它。
- 影响：若把修复做成「准备阶段提示词加一句请带出简介」，是用新的「靠自觉」修旧的「靠自觉」，根因未消除、复发率≈100%。这是典型的 on-call 式隐性故障：平时不报错，只在 Human 选错角色、后续讨论错位时才暴露，定位成本极高（O.md ② 清单首项即「部署与监控可行性是否验证」）。
- 建议：把「准备阶段角色清单」也纳入发射器产出——扩展 `launch_pack.py`（或新增 prep 生成步骤）从 `role-matrix.md` 直接渲染「key + 一句话简介 + 推荐理由」表格，让 Human 看到脚本产物而非 AI 草稿；并加轻量校验：若 sub-doc 准备阶段清单缺任一已声明角色的 intro，则在后续 `check_subdoc.py` 报违例。验收：用本 sub-02 的声明集跑一遍，确认输出表格每项都带 intro。

**观点 2** — 质量护栏的证据正则过窄，存在误伤摩擦（运维摩擦成本）
- 发现：原文 L19-21 把 check_subdoc.py 四不变式列为质量护栏。读 `check_subdoc.py` L67 可知证据判定正则 `EVIDENCE_RE = "原文\s*[L（("` 只接受「原文 Lxx / 原文（…）」形态；任何「原文 第9-13行」「原文 §2」等非 L 形态引用都会被判「无证据」拒收。
- 影响：误伤率直接转化为运维摩擦——被拒收→Human 改写法→闸门通过率靠格式而非内容。摩擦累积后真实风险是 Human 学会绕过闸门或随便塞一个 `原文 L1` 凑数，护栏可靠性归零。这是 SRE 最警惕的「告警疲劳」式退化（O.md ②「可靠性与线上运维成本是否量化」）。
- 建议：放宽证据正则，接受「原文」+ 任意定位符（行号/区段/章节/小标题），如 `原文\s*(L|第|§|章节|—)` 并容忍中文数字；同时在 `scripts/tests/` 增误伤回归用例（一条用「原文 第9-13行」的观点块必须判通过）。验收：新增用例跑 `python3 scripts/check_subdoc.py` 退出码 0。

**观点 3** — 状态协议只校验「存在」不校验「健康」，缺 on-call 触发
- 发现：原文 L19-21 提到状态协议枚举 DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT。读 `check_subdoc.py` L110-134 的 `_check_conclusion`，它只校验「字段存在 + 取值合法 + 未把预演当权威依据」，并不检查子文档是否长期卡在 BLOCKED/NEEDS_CONTEXT。
- 影响：从 O 立场（O.md ②「凌晨被叫醒场景是否覆盖、RTO/RPO 是否明确」），一个子文档长期卡在 BLOCKED、或整文件夹 0 结论就被删除——这种「静默腐烂」没有任何监控/告警。凌晨被叫醒的触发条件（Human 误删未结论集合、长期悬而未决被遗忘）当前护栏完全失明。
- 建议：在 Phase 2 处置契约处加「删除前放行闸门」脚本：遍历 `discussions/<slug>/` 所有 sub-doc，任一 `状态协议` 非 DONE/DONE_WITH_CONCERNS（或缺失 `## conclusion`）即拒绝删除并列出清单；另把「长期 BLOCKED」作为人工巡检项（可在 digest 块标记 oldest-blocked 时间戳），而非靠人记。验收：造含 1 个 BLOCKED 子文档的 fixtures 跑删除闸门，确认被拦截。

**观点 4** — 删除 discussions/ 是破坏性操作，RPO/RTO 与备份职责未定义
- 发现：原文 L22-24 说 Phase 2「Human 确认后删除」。读 `sibling-boundary.md` L21-24 与 `SKILL.md` L39-42，删除前置条件是 zj-docs-ontology 完成「分类沉淀」，但全链路无「沉淀回执」校验，也未说明该文件夹是否在 git 跟踪内、删除前是否 commit。
- 影响：`discussions/` 是「过程权威基座 + 进行中完整解」（`SKILL.md` L35-38）。若 Human 在 ontology 未真正落盘 durable 内容前就删，损失全部 conclusion 与跨子文档约束——RPO 取决于最后一次 commit，若从未提交则 RPO=全丢、RTO=不可恢复。这是最高等级运维风险（不可逆数据丢失），却无任何 alerting/backup 兜底。
- 建议：① 删除前强制 `git add discussions/<slug> && git commit`，把 RPO 锁到删除前、RTO 降到 `git checkout`/reflog 级别；② 要求 zj-docs-ontology 产出「沉淀回执」（哪些 durable 内容已落 docs/、哪些纯过程噪音），删除闸门校验回执存在且非空后才放行；③ 在 `SKILL.md` Phase 4 增硬规则「未持回执 + 未提交 git 的文件夹不得删除」。验收：用 `--dry-run` 删除脚本在「含回执+已提交」fixtures 上验证放行、在「无回执」fixtures 上验证拦截。

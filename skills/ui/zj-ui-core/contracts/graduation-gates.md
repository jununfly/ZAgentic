# UI Agent Skills 毕业闸门与验收指标（冻结版）

- **归属节点**：1-3-1（skill portfolio 收口）的毕业判定约束；实现侧由 Experience Version 在 Wave 0–3 实测。
- **文档性质**：契约冻结。本文件定义十个 UI stage skill（及 S0 base `zj-ui-core`）从本地闭环到 Human 毕业的 **Wave 责任卡** 与 **预注册验收指标**，是 `skill-capability-manifest.md` 字段集之上的不可谈判闸门。
- **来源说明**：内容提炼自 `ui-agent-skills-complete-solution` 讨论过程记录的 Experience Version Wave 与 graduation 预注册指标，已去溯源化（不再引用讨论目录，结论以本文件为权威载体）。
- **本文件版本**：v0.1（冻结）。

---

## 1. Wave 责任卡

| Wave | 目标与责任 | 必须交付 | 失败回退/退出条件 |
| --- | --- | --- | --- |
| 0 | B/T/A：范围、契约、安全和 baseline | scope manifest、10 skill manifest、artifact/adapter/policy manifest、失败 fixture、资源账本、direct-prompt baseline | scope/fixture 不完整 → `NEEDS_CONTEXT`，不进入实现 |
| 1 | 各 skill owner：本地 skill 闭环 | 每个 skill 的输入/输出/禁止/依赖/停止条件、正常/冲突/失败 fixture；本地 artifact 可恢复 | 单个 skill 不合格 → quarantine；本地 fallback 继续 |
| 2 | A/T/O：本地验证 adapter 与兼容性 | Storybook active；json-render/A2UI/M3E opt-in fixture；schema lock/golden/removal test | adapter 失败 → degraded/disabled，本地 artifact 继续；Figma/Superdesign 不阻塞 |
| 3 | B/C/T/U/P：三次 paired run 与 Human graduation | 原始日志、receipt、指标、缺陷/quarantine、fallback 演练、签名 packet | 任何关键回归/越界/证据缺失 → `PILOT`/`QUARANTINED`，不可宣称毕业 |

## 2. 毕业预注册指标（不可挑选样本）

- 返工率相对 direct-prompt baseline 改善 **≥ 20%**；
- 用户决策时间改善 **≥ 15%**；
- escaped UI defects 每次不恶化、三次汇总改善 **≥ 20%**；
- 三次必须是**同一 case / environment / config** 的有效 paired run；缺证据、人工补丁或关键 gate 失败的 run **不计数而补跑**。

## 3. 与同源契约的接口

- 本文件是 `skill-capability-manifest.md` 字段集与失败 fixture→owner 矩阵的**验收侧补全集**；Wave 0 不完整则禁止进入实现（对应 manifest 的 `NEEDS_CONTEXT` 闸门）。
- Wave 3 的 `PILOT`/`QUARANTINED` 退出条件与 `guarantee-boundary.md` 的 `fail-closed` 状态机一致：任何关键 gate 失败不得伪称为毕业。
- 实测结果回写 roadmap 作为 1-3-1 的真实验收证据；若出现偏差，须显式隔离并追踪，不得静默标为「已接受」。

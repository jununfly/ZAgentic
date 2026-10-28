# UI Agent Skills 保证边界与风险控制矩阵（冻结版）

- **归属节点**：1-2-4（golden fixtures 收口）与 1-3-1（skill portfolio 收口）共同约束的「系统保证什么 / 不保证什么」边界。
- **文档性质**：契约冻结。本文件补全 `golden-fixtures-spec.md` / `ui-flow-v1-contract.md` / `skill-capability-manifest.md` 三份冻结契约未覆盖的**保证边界与局限**，是上述契约的同源约束，非独立可放行项。
- **来源说明**：本文件结论沉淀自 ui-agent-skills 早期讨论收敛过程（Remaining-risks 控制矩阵），去溯源化后不再引用任何外部讨论目录，以本文件为权威载体。
- **本文件版本**：v0.1（冻结）。

---

## 1. 风险控制矩阵（保证边界）

| 风险 | 能否彻底解决 | 机制控制 | 不能满足时的控制与状态 |
| --- | --- | --- | --- |
| schema/skill/adapter 漂移 | 可消除边界内漂移；长期漂移不能 | 版本锁、schema lock、golden fixture、semantic diff、breaking-change gate | 上游变更触发重评；旧投影保留，adapter `degraded/disabled` |
| Figma/Superdesign/远程服务不可用 | 不能消除 | 可选 connector、超时/熔断、远程 ID 不入 SSOT | 本地 artifact/静态 preview fallback；服务关闭仍可读写；`DEGRADED` |
| 未注册组件/危险 action | 可在执行边界内阻断 | catalog allowlist、intent、approval、sandbox、executor 单入口、deny fixtures | unknown/deny；Human 可批准的例外绑定 digest/expiry；不模拟成功 |
| 凭据、网络、截图泄露 | 不能靠 prompt 约束彻底消除 | broker、最小 scope、精确 egress、脱敏、secret redaction、审计 | 失败即 fail closed；敏感截图本地 quarantine；`BLOCKED` |
| 素材 license/provenance 缺失 | 不能自动做法律判断 | asset manifest、hash、SPDX/unknown、owner/replacement、构建门禁 | unknown quarantine；人工/合规复核；不进默认产物 |
| 多 skill 抢占/无限重试 | 可在 resolver 边界内收敛 | capability manifest、唯一 owner、precedence、plan hash、lease、幂等键 | 冲突冻结 artifact，Human 仲裁；`NEEDS_CONTEXT` |
| 浏览器/字体/网络视觉噪声 | 可消除可控噪声，不能消除未来环境变化 | pinned runner/font/network replay、双 lane、mutation fixture、receipt | fingerprint mismatch quarantine；旧基线 fallback；`revalidation_required` |
| 生成式审美、用户价值、语境体验 | 不能形式化彻底解决 | direction cards、可比较选择、任务级 Human review、三次 paired run | Human gate 未签则 `HUMAN_REVIEW_REQUIRED`，不自动 PASS |
| 法律/许可证/服务条款判断 | 不能由本系统代替专业判断 | 证据/版本/责任人/期限和变更触发器 | 合规人工 gate；重大变化立即停止新写入并 quarantine |
| 基准被选择性运行或指标被优化 | 不能靠平均数消除 | 预注册 case、paired run、invalid-run 规则、原始日志、第三方复核 | 样本无效则 `NEEDS_CONTEXT`，不挑选三次成功运行 |
| 长期维护/资源和容量 | 不能一次性解决 | owner/预算/WIP、adapter lifecycle、RTO/RPO、重评周期 | 超预算停止扩 scope；降级为 PILOT 或移除 adapter |

## 2. 明确无法解决的事项（长期治理边界，非待补代码）

以下事项不是「待补代码」，而是必须长期治理的边界，任何 receipt 或三次运行都不得把它们写成「已解决」：

- 生成式审美的最终好坏；
- 法律/许可证最终判断；
- 用户价值是否跨项目泛化；
- 外部 provider 的长期行为和条款变化；
- 真实世界未列入 fixture 的新环境组合。

控制方式是 Human gate、fallback、quarantine、到期复核、变更触发重评和状态降级。

## 3. 与同源契约的接口

- 本文件的「风险→机制控制→不满足时状态」三元组，是 `golden-fixtures-spec.md` 闸门（离线恢复 100%、静默丢失 0、未声明 warning 0）与 `skill-capability-manifest.md` 失败 fixture→owner 矩阵的**风险侧补全集**；三者一致，不得弱化任一侧。
- `fail-closed` 状态（`DEGRADED` / `BLOCKED` / `NEEDS_CONTEXT` / `HUMAN_REVIEW_REQUIRED` / `revalidation_required` / `QUARANTINED` / `PILOT`）由各 stage skill 在本地 artifact 仍可读写的前提下触发，不得伪造成功。

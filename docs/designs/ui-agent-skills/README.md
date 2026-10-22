# UI Agent Skills — 权威文档枢纽（INDEX）

> 本页是 `ui-agent-skills` 子系统**稳定契约 / 决策 / 风险 / 验收**权威入口（其路线图已收口，carrier 文件已清理）。讨论过程原样保留于 `discussions/ui-agent-skills-complete-solution/`（不在此页维护，待 Human 审核）。
>
> 路线进度：1-1 ~ 1-9 已完成；1-10（治理 / rollout）进行中；1-9-5（持久化重放闸门 G-19..G-25）单独立项。

## 0. 路线与状态

- 路线图：ui-agent-skills 路线图已收口（carrier 文件与 render 视图均已清理）。
- 毕业裁定：见 `DECISIONS-RISKS.md` 附录 A（内联，2026-10-22；CONDITIONAL_ADOPTION，zj 签署）
- 决策 / 风险收敛页：`./DECISIONS-RISKS.md`（同目录）

## 1. 十个技能（已实现，只读参考）

`zj-ui-brief` · `zj-ui-discover` · `zj-ui-direction` · `zj-ui-design-system` · `zj-ui-flow` · `zj-ui-prototype` · `zj-ui-visual-review` · `zj-ui-break` · `zj-ui-verify` · `zj-ui-handoff`

- 入口目录：`../../skills/ui/`（各 skill 含 `SKILL.md` + `scripts/ui_stages.py` 等）
- 能力 manifest 规范：`./ui-agent-skills-skill-capability-manifest.md`
- SKILL.md 模板：`./ui-agent-skills-skill-md-template.md`

## 2. 稳定契约索引（按路线阶段分组，链到本目录 `ui-agent-skills-*` 契约）

### 1-1 范围与基线

- `ui-agent-skills-scope-manifest.md` — Experience Version scope manifest、in/out-of-scope、成功标准
- `ui-agent-skills-wave0-ledger.md` — Wave 0 资源 / 许可证 / fixture / owner / 风险账本
- `ui-agent-skills-ev-metrics.md` — 返工 / 决策时间 / escaped defect / visual / a11y 指标与毕业门槛
- `ui-agent-skills-ev-sample-flow.md` — 表单 / 审批 sample flow
- `ui-agent-skills-ev-form-lock.md` — 表单锁语义

### 1-2 Canonical artifact 契约

- `ui-agent-skills-canonical-schema.md` — 六类 canonical artifact schema、字段 owner、requiredness
- `ui-agent-skills-brief-design-edit-semantics.md` — UI-BRIEF / UI-DESIGN 编辑 / patch / diff / unknown 语义
- `ui-agent-skills-ui-flow-v1-contract.md` — ui-flow/v1 screen/component/state/action/intent/acceptance 与迁移规则
- `ui-agent-skills-golden-fixtures-spec.md` — 字段保留 / round-trip / 离线恢复 / schema lock golden fixtures

### 1-3 Skill 编排与持久化

- `ui-agent-skills-skill-capability-manifest.md` — 十 skill 能力 manifest、禁止事项、依赖、停止条件
- `ui-agent-skills-resolver-contract.md` — 唯一 owner / precedence / resolver / plan hash / 冲突冻结
- `ui-agent-skills-lease-state-machine.md` — lease / 幂等键 / 失败阶梯 / NEEDS_CONTEXT / quarantine / degraded
- `ui-agent-skills-persistence-replay-contract.md` — plan / decision / revision / handoff 可恢复编排（G-19..G-25）

### 1-4 信任边界与 provenance

- `ui-agent-skills-catalog-allowlist-contract.md` — component / action catalog allowlist、effect intent、unknown 语义
- `ui-agent-skills-trust-chain-contract.md` — policy→approval→sandbox lease→executor deny-first 信任链
- `ui-agent-skills-provenance-asset-manifest-contract.md` — provenance / asset-manifest / secret redaction / 许可证 quarantine
- `ui-agent-skills-deny-fixtures-contract.md` — 未注册组件 / 危险 action / 凭据泄露 / 远程写回失败 deny fixtures

### 1-5 确定性验证

- `ui-agent-skills-fixture-manifest.md` / `.json` — fixture-manifest、verification-matrix、env fingerprint
- `ui-agent-skills-env-fingerprint.md` / `.json` — browser / environment fingerprint（Chromium 155 等）
- `ui-agent-skills-dual-lane-runner.md` — baseline / degraded 双 lane、固定字体 / 网络回放 / 时钟 / seed
- `ui-agent-skills-hard-gates.md` — DOM / ARIA / focus / contrast / overflow / responsive / motion / state 硬门禁
- `ui-agent-skills-verification-receipt.md` — verification receipt、聚合状态、stale / revalidation_required

### 1-6 技能本地闭环

- `ui-agent-skills-stage-engine.md` — 本地 resolver 与十 skill 编排的 stage engine（ui_stages.py）

### 1-7 Adapter 生命周期

- `adapter-boundary-v1/`（目录）— AdapterBoundary v1、manifest、schema lock、mapping、fallback、removal test
- `adapter-capability-fit/`（目录）— Storybook / json-render / A2UI / M3E Canvas 候选 capability-fit 证据

### 1-9 Paired-run 毕业

- `ui-agent-skills-paired-run-registration.md` / `.json` — paired run 注册、无效运行规则、原始日志留存
- `ui-agent-skills-paired-run-roles.md` — 角色定义
- `ui-agent-skills-paired-run-observer-protocol.md` — observer 协议
- 证据包：（随临时容器删除，未长期化；核心裁定见 `DECISIONS-RISKS.md` 附录 A；原 SYNTHESIS / CROSS-RUN-TABLE / RENDER-LAYER-COHORT / R1–R4 原始证据不再保留）

## 3. 治理 / rollout（进行中，1-10）

- 长期治理边界决策见路线图 1-10（已收口）+ 同目录 `DECISIONS-RISKS.md`
- 1-10-2 同步 bucket README / top-level README / 递归发现 / ZJ-CONTEXT.md（被 1-10-1 阻塞）
- 1-10-3 owner / 维护预算 / RTO-RPO / 版本重评 / WIP 治理（被 1-10-2 阻塞）
- 1-10-4 rollout / pilot / kill-switch / adapter 移除 / revalidation 决策（被 1-10-3 阻塞）

## 4. 回链与来源

- 讨论过程（保留不删）：`../../discussions/ui-agent-skills-complete-solution/`（MASTER + 6 sub + briefings + viewpoints）
- 毕业裁定底表：见 `DECISIONS-RISKS.md` 附录 A（2026-10-22 内联）
- 路线图：ui-agent-skills 路线图（已收口）

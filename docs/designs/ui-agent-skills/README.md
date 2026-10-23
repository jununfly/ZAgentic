# UI Agent Skills — 权威文档枢纽（INDEX）

> 本页是 `ui-agent-skills` 子系统**稳定契约 / 决策 / 风险 / 验收**的入口。
> 所有机器可读契约与配套规范现已随 skill 安装，统一位于 `skills/ui/zj-ui-core/contracts/`（closure 合规，见 AGENTS.md「Skill runtime closure」）。本 `docs/` 目录仅保留本枢纽 `README.md`。
>
> 路线进度：1-1 ~ 1-9 已完成；1-10（治理 / rollout）进行中；1-9-5（持久化重放闸门 G-19..G-25）单独立项。

## 0. 路线与状态

- 路线图：ui-agent-skills 路线图已收口（carrier 文件与 render 视图均已清理）。
- 毕业裁定：CONDITIONAL_ADOPTION，zj 签署（2026-10-22；原 `DECISIONS-RISKS.md` 已随规范层清理于 2026-10-23 删除）。
- 讨论过程（保留不删）：`../../discussions/ui-agent-skills-complete-solution/`。

## 1. 契约与规范的唯一权威位置

**所有契约与规范**均位于 `skills/ui/zj-ui-core/contracts/`：

- 机器可读：`fixture-manifest.json` · `env-fingerprint.json` · `adapter-manifest.schema.json`
- 规范（人类可读，随 skill 安装）：`skill-capability-manifest.md` · `skill-md-template.md` · `hard-gates.md` · `verification-receipt.md` · `adapter-boundary-v1.md` · `resolver-contract.md` · `scope-manifest.md` · `wave0-ledger.md` · `ev-sample-flow.md` · `canonical-schema.md` · `stage-engine.md` · `ui-flow-v1-contract.md` · `golden-fixtures-spec.md` · `dual-lane-runner.md`

CI 门禁（`scripts/run_ui_skills_gate.sh` → `ui-contract` required check）读取上述 `contracts/`，不依赖本 `docs/` 目录。

## 2. 十个技能（已实现，只读参考）

`zj-ui-brief` · `zj-ui-discover` · `zj-ui-direction` · `zj-ui-design-system` · `zj-ui-flow` · `zj-ui-prototype` · `zj-ui-visual-review` · `zj-ui-break` · `zj-ui-verify` · `zj-ui-handoff`

- 入口目录：`../../skills/ui/`
- 能力 manifest 规范：`skills/ui/zj-ui-core/contracts/skill-capability-manifest.md`
- SKILL.md 模板：`skills/ui/zj-ui-core/contracts/skill-md-template.md`

## 3. 治理 / rollout（进行中，1-10）

- 长期治理边界决策见路线图 1-10（已收口）。
- 1-10-2 同步 bucket README / top-level README / 递归发现 / ZJ-CONTEXT.md（被 1-10-1 阻塞）
- 1-10-3 owner / 维护预算 / RTO-RPO / 版本重评 / WIP 治理（被 1-10-2 阻塞）
- 1-10-4 rollout / pilot / kill-switch / adapter 移除 / revalidation 决策（被 1-10-3 阻塞）

## 4. 已清理（2026-10-23）

- **类 2 收口**：7 个运行时契约从本目录迁入 `contracts/`（去 `ui-agent-skills-` 前缀）。
- **类 3 清理**：12 个遗留孪生件 / 决策证据产物删除。
- **类「CI 负载（不可删集合）」收口**：9 篇规范层（`wave0-ledger` / `golden-fixtures-spec` / `ev-sample-flow` / `canonical-schema` / `scope-manifest` / `stage-engine` / `dual-lane-runner` / `ui-flow-v1-contract` / `adapter-boundary-v1`，外加 `resolver-contract`）迁入 `contracts/`；其余纯规范层复本（`catalog-allowlist` / `deny-fixtures` / `persistence-replay` / `provenance-asset-manifest` / `trust-chain` / `paired-run-*` / `ev-form-lock` / `ev-metrics` / `brief-design-edit-semantics` / `lease-state-machine` / `DECISIONS-RISKS` 等）删除——均不被任何代码或契约加载，仅 docs→docs 链接，删除零 CI 风险。

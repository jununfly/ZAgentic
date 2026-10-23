# UI Agent Skills — 决策收敛与治理状态页

> 本页只承载 `ui-agent-skills` 子系统的**仓库级决策收敛与治理状态**（毕业裁定、路线进度、治理 1-10、清理记录）。
> 契约与技能的导航（10 个技能全链、机器可读契约与规范清单）已随 skill 安装，统一见 [`skills/ui/README.md`](../../skills/ui/README.md) 与 `skills/ui/zj-ui-core/contracts/`（closure 合规，详见 AGENTS.md「Skill runtime closure」）。CI 门禁（`scripts/run_ui_skills_gate.sh` → `ui-contract` required check）只读 `contracts/`，不依赖本页。

## 状态与毕业裁定

- 路线图：ui-agent-skills 路线图已收口（carrier 文件与 render 视图均已清理）。
- 毕业裁定：CONDITIONAL_ADOPTION，zj 签署（2026-10-22；原 `DECISIONS-RISKS.md` 已随规范层清理于 2026-10-23 删除）。
- 讨论过程（保留不删）：`../../discussions/ui-agent-skills-complete-solution/`。
- 路线进度：1-1 ~ 1-9 已完成；1-10（治理 / rollout）进行中；1-9-5（持久化重放闸门 G-19..G-25）单独立项。

## 治理 / rollout（进行中，1-10）

- 长期治理边界决策见路线图 1-10（已收口）。
- 1-10-2 同步 bucket README / top-level README / 递归发现 / ZJ-CONTEXT.md（被 1-10-1 阻塞）
- 1-10-3 owner / 维护预算 / RTO-RPO / 版本重评 / WIP 治理（被 1-10-2 阻塞）
- 1-10-4 rollout / pilot / kill-switch / adapter 移除 / revalidation 决策（被 1-10-3 阻塞）

## 已清理（2026-10-23）

- **类 2 收口**：7 个运行时契约从本目录迁入 `contracts/`（去 `ui-agent-skills-` 前缀）。
- **类 3 清理**：12 个遗留孪生件 / 决策证据产物删除。
- **类「CI 负载（不可删集合）」收口**：9 篇规范层迁入 `contracts/`；其余纯规范层复本删除——均不被任何代码或契约加载，仅 docs→docs 链接，删除零 CI 风险。
- **类 1 瘦身（2026-10-23）**：本页从「权威文档枢纽（INDEX）」收窄为「决策收敛与治理状态页」。删除原 §1 契约清单与 §2 十个技能清单（二者均已由 `skills/ui/README.md` 覆盖），仅保留毕业裁定、治理 1-10 状态与清理记录；导航统一改指 `skills/ui/README.md`。

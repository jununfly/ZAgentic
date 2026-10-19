# Scope Manifest — UI Agent Skills（Wave 0 / Experience Version v0.1）

> 归属路线图节点：1-1-1（冻结 Experience Version scope manifest、in-scope/out-of-scope 与成功标准）
> 事实源：`docs/plans/ui-agent-skills-roadmap.json`
> 状态：Wave 0 冻结版，可由 Human 复核；后续 Wave 变更需经 1-10 治理流程。

## 1. Experience Version（被锁定的样例）

| 维度 | 锁定值 |
| --- | --- |
| 版本号 | **EV-v0.1（Wave 0，表单基准）** |
| 技术栈 | React 18 + Next.js（App Router），TypeScript |
| 样例 | **用户资料编辑表单（User Profile Edit Form）** |
| 角色 | 用户（编辑 + 提交）/ 系统（校验 + 持久化） |
| 状态机 | `idle → validating → submitting → success \| error`；字段级 `error` 覆盖 |
| 环境 | 本地 Next.js dev server + Storybook（active adapter） |
| 数据边界 | 内存 / 本地 mock，无真实后端写回；远程写回仅作 1-5 / 1-8 的演练项 |
| 不锁项 | 审批流（费用报销等）作为 **Wave 1 候选**，不在 Wave 0 scope 内 |

## 2. In-scope（Wave 0）

- 10 个公共 UI skill 的创建与契约化本地闭环：zj-ui-brief / zj-ui-discover / zj-ui-direction / zj-ui-design-system / zj-ui-flow / zj-ui-prototype / zj-ui-visual-review / zj-ui-break / zj-ui-verify / zj-ui-handoff（节点 1-6）
- Canonical artifact 契约 + `ui-flow/v1`（节点 1-2）
- Skill capability manifest + resolver 编排（节点 1-3）
- Trust boundary / provenance / deny-first policy（节点 1-4）
- 确定性验证、fixture、receipt（节点 1-5）
- Storybook **active** adapter；json-render / A2UI / M3E Canvas 仅作 opt-in golden fixtures（节点 1-7）
- 表单 Experience Version 的端到端人机协作演练（节点 1-8）
- 3 次 paired run + graduation gate（节点 1-9）
- Wave 0 资源、许可证、fixture、owner、风险账本（节点 1-1-4）

## 3. Out-of-scope（Wave 0）

- 其他前端框架（Vue / Angular / Svelte）的 adapter 实现
- 真实生产后端、真实凭据、真实网络写回
- 多 Experience Version 并行（仅锁表单一个）
- adapter 删除 / 断网 / 远程服务失败的完整治理（仅 1-7-5、1-8-5 局部演练，正式治理归 1-10）
- 长期文档、维护治理与 rollout 决策（节点 1-10，毕业后执行）

## 4. 成功 / 失败状态（毕业门槛）

- **成功**：3 次 paired run 中，skills path 在预注册指标上**不劣于** direct-prompt baseline，且 verification receipt 完整、可归因。
- **预注册指标**（基线于 1-1-3）：返工次数、决策时间、escaped defect。
- **无效 run 规则**：非同一 case / environment / config，或缺少原始日志留存 → 不计入口径。
- **退出 / 降级状态**：
  - 缺项且无法补齐 → 仅以 `NEEDS_CONTEXT` 退出，不编造。
  - 无法归因 → `quarantine`。
  - 产物过期 → `stale / revalidation_required`。
  - 远程服务失败 → 本地 `degraded / disabled / quarantine` 回退。

## 5. Experience Version 版本管理

- 当前冻结：**EV-v0.1**。
- 版本变更须经 1-10 重评流程；Wave 0 内不允许 silently 改基线样例。
- 任何 manifest 字段调整需回到本文件并同步 roadmap 决策（`decide` 落盘）。

## 6. 账本引用（不重复，指向节点）

- 资源 / 许可证 / fixture / owner / 风险 → 节点 **1-1-4**（Wave 0 账本）。
- 指标阈值与 graduation packet → 节点 **1-1-3**、**1-9-4**。
- 契约与 adapter 细节 → 节点 **1-2**、**1-7**。

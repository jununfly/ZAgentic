# UI-BRIEF / UI-DESIGN 文档编辑·patch/diff·unknown/source 语义（冻结版）

- **归属节点**：1-2-2（产品实现路线 · 计划层 · `exploit`）
- **文档性质**：契约冻结，交付物为语义规范，**不含产品代码落地**。
- **依赖**：1-2-1（六类 canonical artifact schema 已冻结，v0.1）。
- **引用源**：`discussions/ui-agent-skills-complete-solution/MASTER.md` L29-37 / L43-44 / L50-56 / L62-66 / L94-101。
- **本文件版本**：v0.1（冻结；后续变更经 1-2-3/ui-flow/v1 迁移规则与 1-2-4 golden fixtures 校验）。

---

## 0. 范围与停止条件（本节点退出判据）

> **退出判据原文**：文档编辑可产生可审阅 patch/diff，不直接执行 effect，拒绝非法字段。

本文件冻结以下四类语义，全部以**可机器校验**的方式表达，供 1-2-4 golden fixtures 评审：

1. 编辑入口与解析（如何把对话/文档变更变成 field-level diff）
2. patch/diff 可审阅（before/after + 影响字段 + receipt 预览，原子提交）
3. 拒绝非法字段（deny-first，不静默丢弃）
4. unknown / source 不变量（四元组保留、provenance 可归因、quarantine）

**停止条件（贯穿全文）**：
- brief 缺「目标 / 用户 / 成功标准」→ `NEEDS_CONTEXT`，**不写 effect**。
- design 方向不唯一或缺来源 → `Human gate`，**不自动替选**。
- 任何 effect 链路不完整（缺 intent / approval / sandbox lease / provenance）→ **不执行**。

---

## 1. 编辑入口与解析

**入口（两类，等价对待）**：
- A. 对话生成 brief 草案：最多追问**两个真正缺口**的问题（MASTER L33）。
- B. 直接编辑 `UI-BRIEF.md` / `UI-DESIGN.md`：解析文档 diff，校验字段与版本（MASTER L34）。

**解析为 field-level diff**：
- 每次编辑绑定 `(input_revision, schema_version)`（沿用 1-2-1 的版本校验键）。
- 解析输出必须包含：
  - `before` / `after` 字段级差异；
  - 字段来源（`source`，见第 4 节）；
  - 影响的 skill（zj-ui-brief / zj-ui-direction / zj-ui-design-system …）；
  - 待确认项（open questions，含 unknown 清单）。
- schema_version 不匹配 → **拒绝并提示迁移路径**（迁移规则在 1-2-3 定义，本节点只声明拒绝行为）。

**写入规则（解析阶段）**：只写 **draft / 本地 canonical**，不执行 effect（MASTER L33/L36）。Human 选择「接受 patch」后才提交新 revision（见第 2 节）。

---

## 2. patch / diff（可审阅）

**产出（可审阅闭环，MASTER L34/L36）**：
- `before/after` 文本 diff；
- **影响字段清单**（字段名 → owner → 影响的 skill）；
- **receipt 预览**（仅预览，不落最终 receipt；最终 receipt 由 verification 链路产出）。

**提交规则（原子）**：
- Human 显式「接受 patch」→ 校验通过 → **原子提交新 canonical revision**（绑定幂等键 `(fixture_id, input_revision, adapter_version, mapping_version)`，MASTER L55）。
- 不直接改生产代码 / 远程画布（MASTER L36）。effect 走第 5 节信任链，与本阶段解耦。

**审阅不变量**：
- 所有变更对人类可见（diff 可重现、可回放）。
- 未通过校验的 patch 一律拒绝，不因「已生成」而默认接受。

---

## 3. 拒绝非法字段（deny-first）

**原则**：未注册 / 未知字段**不静默丢弃**，一律显式拒绝并标注（MASTER L97 deny-first；L96 未注册 component/action = `unknown` 不可执行）。

**拒绝情形（hard fail，不降级处理）**：
- 字段不在 `UI-BRIEF.md` / `UI-DESIGN.md` 已注册 schema 内 → 拒绝，列出未知字段名。
- 未注册 component / action → 标 `unknown` 且**非可执行**（MASTER L96），不进入产物默认渲染。
- token 冲突 / contrast 不达标（design-system 层）→ 阻断（MASTER L67）。

**拒绝响应格式**（统一）：`{ rejected: true, field, reason, suggested_owner, recoverable: bool }`，供上游 skill 生成澄清或报错。

---

## 4. unknown / source 不变量

**unknown 四元组（MASTER L53，强制）**：`unknown` 必须保留
`{ path, raw, reason, source }`，**不能压成空值**。
- `path`：出现位置（文件/章节/字段路径）。
- `raw`：原始未解析内容。
- `reason`：为何判定为 unknown（未注册 / 歧义 / 缺来源 …）。
- `source`：原始出处（对话轮次 / 文档段落 / provider 引用 ID）。

**source 可归因（MASTER L43/L44/L56）**：
- `UI-BRIEF.md` 的 unknown/source 必须可追溯到 provider 输入引用。
- `UI-DESIGN.md` 的方向 / token / 字体 / 颜色 / provenance 必须可归因到外部参考链接或渲染参数。
- 外部缺 provenance → **quarantine 不进默认产物**（MASTER L100：`unknown` license/source/owner 缺失进入 quarantine）。

**保留率约束（MASTER L54）**：必填语义字段转换后 **100% 保留**；静默丢失数 = 0，未声明 warning 数 = 0。本节点冻结该约束，**数值实测**在 1-2-4 通过 golden fixtures 验证。

---

## 5. 不直接执行 effect（信任链解耦）

**信任链（MASTER L94，唯一路径）**：
`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`

**文档编辑阶段边界**：
- 文档编辑 / patch / diff **只写 draft 与本地 canonical**，不触发任何 effect（MASTER L33/L36）。
- effect = 代码执行 / 网络 / 凭据 / 截图 / 写回远程（MASTER L25）。无完整 intent、approval、sandbox lease、provenance，**effect 不得执行**（MASTER L25/L96）。
- 远程写回需 `request digest + 幂等键 + 单独 approval + 目标/变更摘要 + 审计`；失败回退本地，**不伪造成功**（MASTER L99）。

**停止条件再声明**：
- brief 缺目标 / 用户 / 成功标准 → `NEEDS_CONTEXT`（MASTER L64）。
- design 方向不唯一或缺来源 → `Human gate`（MASTER L66）。
- policy / catalog / manifest 不可用 → **fail closed**（MASTER L101）：offline simulator 与 deny-first fixtures 在无网络、无凭据、无 Figma 时仍必须可运行。

---

## 附：本节点对上下游的契约义务

- **向上（1-2-1）**：六类 schema 的 `owner/source/requiredness/unknown policy` 已冻结，本文件不重新定义 schema，仅在其上施加编辑/拒绝/unknown 语义。
- **向下（1-2-3）**：ui-flow/v1 的 screen/component/state/action/intent/acceptance 与迁移规则，须沿用本文件的「deny-first / unknown 四元组 / 不直接执行 effect」三条不变量，不得弱化。
- **向下（1-2-4）**：本文件所有「保留率 100% / 静默丢失=0 / 未声明 warning=0 / quarantine 不进默认产物」均为**待验证声明**，由 golden fixtures 在 1-2-4 实测，本文件不构成已通过证据。

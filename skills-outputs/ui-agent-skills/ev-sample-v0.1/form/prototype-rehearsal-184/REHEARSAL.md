# 1-8-4 演练报告：从 ui-flow/v1 生成本地 preview 并演练 effect approval 与安全边界

> **归属节点**：1-8-4（EV-v0.1 · 节点 1-8 · `exploit`）
> **事实源**：`docs/plans/ui-agent-skills-roadmap.json`
> **对齐文档**：`ui-agent-skills-ui-flow-v1-contract.md`、`zj-ui-prototype/SKILL.md`、`ui-agent-skills-trust-chain-contract.md`、`ui-agent-skills-verification-receipt.md`、`FF-PROTO-01/02/03`
> **性质**：**演练（rehearsal）**，不是 1-9 实证闸门运行。G-POL-1..9 实测闸门仍 `open`，本节点只演练、不回写实测值。

---

## 0. 退出判据对照（节点 1-8-4）

> 原文："prototype/preview 仅使用 catalog，effect approval、sandbox 和 receipt 链路完整"

| # | 判据要素 | 承载演练 | 结果 |
|---|---|---|---|
| 1 | preview 仅使用 catalog | 从 ui-flow/v1 生成 `UI_PREVIEW`，components = `[Form, Input, Button, Toast]`，全部 ∈ `COMPONENT_REGISTRY` | ✅ catalog_only = true |
| 2 | effect approval + sandbox 链路 | 三路径：P1 未签审批零写入 / P2 未注册组件 deny / P3 远程不可用 stop 不伪造成功 | ✅ 三条路径均符合预期（0 副作用） |
| 3 | receipt 链路完整 | preview → `zj-ui-verify` → verification receipt，receipt 串联 preview revision + flow revision | ✅ aggregate_status = OK，threads_preview/threads_flow = true |

`all_pass = true`（机器证据见 `rehearsal-evidence.json`，可重放 `/tmp/rehearse_184.py`）。

---

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `preview.html` | 从 form 样例 `ui-flow/v1` 生成的**真实本地 preview**，仅用 catalog 组件（Form/Input/Button/Toast），本地 mock 提交，无网络/无远程写回 |
| `rehearsal-evidence.json` | 确定性演练证据：flow revision、preview revision、三路径状态/写入数、receipt revision、退出判据断言 |
| `REHEARSAL.md` | 本报告 |

preview 生成链路：
`form/ui-flow.v1.md`（六义）→ `run_flow` 提交 `UI-FLOW`（rev `0047dc…`）→ 组件实例映射 catalog 类型（ProfileForm→Form 等）→ `run_prototype` 提交 `UI_PREVIEW`（rev `95b4bc…`，human_gate 已签）→ `preview.html` 渲染。

---

## 2. 安全边界三路径（复用 FF-PROTO 语义）

| 路径 | 输入 | 期望 | 实测 |
|---|---|---|---|
| P1 · effect approval gate | 无 `human_approval` | `HUMAN_REVIEW_REQUIRED`，0 写入 | ✅ 一致 |
| P2 · catalog 边界 | 混入未注册 `DateRangePicker` | `REJECTED`，0 写入，rejected=`components` | ✅ 一致（FF-PROTO-02） |
| P3 · sandbox / 远程关闭 | `remote_available=false` 且无本地 fallback | `HUMAN_REVIEW_REQUIRED`，0 写入，不伪造成功 | ✅ 一致（FF-PROTO-03） |

P1/P3 体现 **effect approval**：任何不可逆/外部写入前必须人签或显式 fallback，否则零副作用。
P2 体现 **catalog 是安全边界**：catalog 外组件一律 deny，不"临时补一个"绕过。
三路径共同体现 **fail-closed**：策略/catalog 不可用或拒签时，运行失败（不执行、不生成成功产物）。

---

## 3. receipt 链路闭环

`run_verify` 以三个 `check`（catalog-only / effect-approval / sandbox 边界）绑定 preview revision + env fingerprint 聚合 → `aggregate_status = OK` → 生成 verification receipt（rev `f9910b…`）。
receipt 的 `checks[0].artifact` == preview revision，fingerprint 绑定 flow revision，离线可审计（谁跑、跑什么、什么环境）。

> 注：`ui_stages.run_prototype` 本身是纯校验/提交，**不真正执行 effect**（无网络、无凭据、无远程写）。本节点演练的是"preview 产出前/产出时的安全边界判定"，与信任链 `policy→approval→sandbox lease→executor` 的**逐字段实证**（`G-POL-1..9`）正交——后者归 1-9 paired run。

---

## 4. 范围与边界声明（勿误读为已通过）

- 本节点 `completed` = **演练闭环落盘（exploit 层）**，不代表 G-POL 闸门实测通过。
- 信任链 `intent→policy→approval→sandbox lease→executor→provenance→receipt` 的逐字段断言（G-POL-1..9）仍为 `open`，待 1-6 真实落地 + 1-9 真实 fixture 回写实测。
- 远程写回（F-6 / 1-8-5）仅在本节点注释中声明 deny-first，真实演练归 **1-8-5**。

---

## 5. 重放方法

```bash
python /tmp/rehearse_184.py          # 重跑演练，输出 evidence 并打印 all_pass
```

脚本复用冻结实现 `skills/ui/zj-ui-core/scripts/{ui_stages,ui_skill_core}.py`，无任何真实副作用。

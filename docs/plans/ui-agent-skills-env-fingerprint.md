# Environment Fingerprint — UI Agent Skills（1-5-1 冻结版）

- **归属节点**：1-5-1（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：`docs/plans/ui-agent-skills-roadmap.json`
- **机器指纹**：`docs/plans/ui-agent-skills-env-fingerprint.json`
- **状态**：冻结版（指纹轴组成 + 政策）；concrete 值由 **1-5-2** runner 首次运行捕获并冻结。
- **退出判据对齐**：1-5-1 退出 = verification matrix key 与 fixture/env fingerprint 完整且可重算。

---

## 0. 目的

确定性验证要求"同一 case 在任何机器/时间跑出可比结果"。环境指纹把验证环境的**可变轴**固定为可哈希、可比对、可重算的记录；任一轴变化即判定指纹失配，验证结论降级为 `stale / revalidation_required`。本文件冻结**指纹由哪些轴构成**与**变更政策**，concrete 值（具体 Chromium build、seed 等）由 1-5-2 runner 在首次运行时捕获写入 `env-fingerprint.json` 并从此冻结。

---

## 1. 指纹轴（冻结组成）

| 轴 | 字段 | 取值 / 政策 | 来源 |
| --- | --- | --- | --- |
| 浏览器主版本 | `browser_major` | Chromium 固定 major；首跑捕获后冻结，变更须 revalidation | R-BRW-1 / R-RISK-1 |
| 运行时版本 | `node_version` | `≥18.17`（Next.js 14 要求） | R-ENV-1 |
| 渲染字体 | `font` | **L-FONT = NEEDS_CONTEXT**：未选字体。冻结期以"系统默认 + 显式标记 non-portable"占位；zj 选定自由许可字体后回填并重新冻结指纹 | L-FONT / R-RISK-3 |
| 网络模式 | `network_mode` | `replay`（无真实网络；本地 mock 层，form-lock §1） | R-MOCK-1 / R-RISK-5 |
| 时钟源 | `clock_source` | `fixed virtual time`（确定性虚拟时钟，无墙钟依赖） | 1-5-2 退出判据 |
| 随机种子 | `seed` | 固定 RNG seed，保证截图/布局随机性可复现 | 1-5-2 退出判据 |
| 配置哈希 | `config_hash` | 验证配置（viewport 集、断言阈值集、oracle 集）的 sha256 | 本节点定义 |

> `font` 为唯一开放口：L-FONT 依赖 zj 决策（选一款 SIL OFL 等自由许可字体并登记许可），在选定前渲染基线不可跨机比较，故本指纹显式标记 `non-portable`，不伪装可比。

---

## 2. 可重算定义

```
env_hash = sha256(
    "|".join([
        browser_major,
        node_version,
        font,                # 含 "NEEDS_CONTEXT" 占位或已选定值
        network_mode,
        clock_source,
        seed,
        config_hash
    ])
)
```

- 任一轴变化 → `env_hash` 变化 → 指纹失配 → `stale / revalidation_required`。
- 字体从 NEEDS_CONTEXT 改为具体值属"轴变化"，须重新冻结指纹并触发全量 revalidation（与 R-RISK-3 同源、已 `NEEDS_CONTEXT`）。
- `env_hash` 由 1-5-2 runner 在首跑时计算并写入 `env-fingerprint.json`；本冻结版先锁定**过程**与**轴组成**。

---

## 3. 关联风险（源自 wave0-ledger §5）

- **R-RISK-1**（Chromium 版本漂移）→ 本指纹固定 `browser_major` 缓解；漂移检测由 `env_hash` 比对实现。
- **R-RISK-3**（字体许可/可用性未定）→ L-FONT `NEEDS_CONTEXT`，本指纹显式开放该轴。
- **R-RISK-5**（adapter 网络依赖）→ `network_mode=replay` + 本地 mock 缓解，断网/远程失败走 degraded 回退（1-7-5/1-8-5）。

---

## 4. 上下游契约义务

- **向上**：消费 `wave0-ledger`（R-BRW-1/R-ENV-1/R-MOCK-1/R-RISK-*）、`scope-manifest`（EV-v0.1 环境）、`golden-fixtures-spec`（fail-closed 要求）。
- **向下（1-5-2）**：runner 首次运行须捕获 concrete 值、写 `env-fingerprint.json`、计算 `env_hash`、与 `fixture-manifest` 共同喂给 `verification-matrix` 派生 `matrix_key`。
- **向下（1-9）**：每次 paired run 须比对 `env_hash`，失配则 run 无效（invalid-run 规则，scope-manifest §4）。

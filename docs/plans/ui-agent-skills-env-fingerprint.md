# Environment Fingerprint — UI Agent Skills（1-5-1 冻结版）

- **归属节点**：1-5-1（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：`docs/plans/ui-agent-skills-roadmap.json`
- **机器指纹**：`docs/plans/ui-agent-skills-env-fingerprint.json`
- **状态**：冻结版（指纹轴组成 + 政策）；concrete 值由 **1-5-2** runner 首次运行捕获并冻结。font 轴已于 2026-10-20 回填定值并重冻结。
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
| 渲染字体 | `font` | **Noto Sans SC（主，中文+拉丁）+ Inter（拉丁 UI）+ JetBrains Mono（代码 fixture 条件启用）**；许可均 SIL OFL 1.1，经 `@fontsource` npm 自托管锁版本；2026-10-20 zj 选定回填，轴已定值；后续字体变更须重冻结 + 全量 revalidation | L-FONT(resolved) / R-RISK-3(mitigated) |
| 网络模式 | `network_mode` | `replay`（无真实网络；本地 mock 层，form-lock §1） | R-MOCK-1 / R-RISK-5 |
| 时钟源 | `clock_source` | `fixed virtual time`（确定性虚拟时钟，无墙钟依赖） | 1-5-2 退出判据 |
| 随机种子 | `seed` | 固定 RNG seed，保证截图/布局随机性可复现 | 1-5-2 退出判据 |
| 配置哈希 | `config_hash` | 验证配置（viewport 集、断言阈值集、oracle 集）的 sha256 | 本节点定义 |

> `font` 轴已解决（2026-10-20）：zj 选定 Noto Sans SC + Inter（+JetBrains Mono 条件项），许可全 SIL OFL 并登记 wave0-ledger L-FONT；经 `@fontsource` npm 包锁版本，CI/本地一致。原 `NEEDS_CONTEXT` / `non-portable` 占位自此撤销；本次轴变化发生于首跑前，无既有验证结论需作废。

---

## 2. 可重算定义

```
env_hash = sha256(
    "|".join([
        browser_major,
        node_version,
        font,                # 取 axes.font.value（2026-10-20 起为定值）
        network_mode,
        clock_source,
        seed,
        config_hash
    ])
)
```

- 任一轴变化 → `env_hash` 变化 → 指纹失配 → `stale / revalidation_required`。
- 字体从 NEEDS_CONTEXT 改为具体值属"轴变化"，须重新冻结指纹并触发全量 revalidation——该规则已于 2026-10-20 首次执行（font 轴回填，发生于首跑前，无既有结论需作废）。
- `env_hash` 由 1-5-2 runner 在首跑时计算并写入 `env-fingerprint.json`；本冻结版先锁定**过程**与**轴组成**。
- `config_hash` 于 1-5-3 重算（config v0.2）：viewport 集从占位 `1280x800/375x667` 对齐为
  `390x844/768x1024/1440x900`（1-3 capability manifest S8 FF-BRK 必测断点），阈值集改由
  `hard_gates.GATE_THRESHOLDS` 单一供给 → `config_hash` → `env_hash` → `matrix_key` 全部变化。
  轴变化发生于任何 cell 产生结论之前（1-5-2 两条 lane 全 `NOT_EXECUTED`/`DEGRADED_SKIP`），
  故无既有结论作废；旧值见 `ui-agent-skills-dual-lane-runner.md` §4.1 历史记录。

---

## 3. 关联风险（源自 wave0-ledger §5）

- **R-RISK-1**（Chromium 版本漂移）→ 本指纹固定 `browser_major` 缓解；漂移检测由 `env_hash` 比对实现。
- **R-RISK-3**（字体许可/可用性未定）→ **已缓解（2026-10-20）**：选定 Noto Sans SC + Inter + JetBrains Mono（SIL OFL 1.1），`@fontsource` 锁版本；L-FONT 许可登记见 wave0-ledger。
- **R-RISK-5**（adapter 网络依赖）→ `network_mode=replay` + 本地 mock 缓解，断网/远程失败走 degraded 回退（1-7-5/1-8-5）。

---

## 4. 上下游契约义务

- **向上**：消费 `wave0-ledger`（R-BRW-1/R-ENV-1/R-MOCK-1/R-RISK-*）、`scope-manifest`（EV-v0.1 环境）、`golden-fixtures-spec`（fail-closed 要求）。
- **向下（1-5-2）**：runner 首次运行须捕获 concrete 值、写 `env-fingerprint.json`、计算 `env_hash`、与 `fixture-manifest` 共同喂给 `verification-matrix` 派生 `matrix_key`。
- **向下（1-9）**：每次 paired run 须比对 `env_hash`，失配则 run 无效（invalid-run 规则，scope-manifest §4）。

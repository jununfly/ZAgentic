# Dual-Lane Deterministic Runner — UI Agent Skills（1-5-2 交付版）

- **归属节点**：1-5-2（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：ui-agent-skills 路线图（已收口，carrier 文件已清理）
- **机器实现**：`skills/ui/zj-ui-core/scripts/dual_lane_runner.py`（R-HAR-1，纯 stdlib）
- **输入**：`ui-agent-skills-fixture-manifest.json`、`ui-agent-skills-env-fingerprint.json`、`ui-agent-skills-verification-matrix.md`
- **状态**：双 lane + 确定性控制已落地并冻结首跑值；真实 cell 断言待 1-6/1-7。
- **退出判据对齐**：1-5-2 退出 = baseline/degraded 双 lane 固定 browser/font/network/clock/seed 并可复跑。

---

## 0. 范围与边界

本节点交付 **确定性双 lane 验证 runner（R-HAR-1）** 及其冻结的首跑指纹：把 1-5-1 冻结的
fixture-manifest / verification-matrix / env-fingerprint **过程**转为可执行的 runner，并捕获
concrete 环境值、计算 `manifest_hash` / `env_hash` / `matrix_key`。

- **在口径内**：runner 实现、双 lane 调度、确定性控制（browser/font/network/clock/seed +
  config_hash）、hash 计算与冻结、复跑幂等、fail-closed 占位 receipt。
- **在口径外（明确延迟，非静默接受）**：
  - 真实 fixture 数据文件（F-1…GF-11）由 **1-6/1-7** 落地；本节点仅就 manifest 元数据记录
    计算 `manifest_hash`，数据落地后须重算（见 §5）。
  - 真实 cell 断言（DOM/ARIA、a11y、像素、round-trip 等）需要 **浏览器 / adapter / flow
    engine**，由 1-5-3 / 1-6 / 1-7 提供；本节点 runner 在缺它们时如实标记
    `NOT_EXECUTED` / `DEGRADED_SKIP`，**绝不伪造通过**（golden-fixtures-spec §8 fail-closed）。
  - `browser_major` 不在本仓库 Wave 0 harness 内捕获（无内置浏览器引擎），延迟到 **1-7-3**
    （Storybook active adapter）。其占位变化即触发 revalidation（见 §4）。

---

## 1. 双 lane 设计

| 维度 | baseline lane | degraded lane |
| --- | --- | --- |
| 目的 | 全维度硬门禁（verification-matrix §2 全部 A/W cell） | adapter-off / 离线恢复路径，验证无网络/无 adapter 仍可闭环 |
| 依赖 | 浏览器 + active adapter（1-7-3）+ flow engine（1-6） | 仅需本地 canonical（flow engine，1-6） |
| 触发 | `run --lane baseline` | `run --lane degraded` |
| 当前状态 | 有 observation bundle 的 cell 执行 7 类硬门禁（1-5-3）；无证据 → `NOT_EXECUTED` / `HUMAN_REVIEW_REQUIRED` | 所有 cell `DEGRADED_SKIP`（等 1-6 engine） |
| 失败语义 | 任一 A cell 失败 → `FAIL`；缺证据 → `HUMAN_REVIEW_REQUIRED` | adapter 相关一律跳过；离线恢复失败 → `BLOCKED` |

两条 lane 共享同一套确定性控制与 hash 派生，保证同一 case 在任一 lane 内可复跑、可比对。

---

## 2. 确定性控制（1-5-2 退出判据：固定 browser/font/network/clock/seed）

| 控制 | 实现 | 首跑冻结值 |
| --- | --- | --- |
| 字体 `font` | 固定 Noto Sans SC + Inter（+JetBrains Mono 条件），`@fontsource` 自托管锁版本（SIL OFL 1.1） | `noto-sans-sc+inter+jetbrains-mono(conditional)`（2026-10-20 已定值） |
| 网络 `network_mode` | 本地 mock 回放层，无真实网络（R-MOCK-1/R-RISK-5） | `replay` |
| 时钟 `clock_source` | `VirtualClock` 固定虚拟 epoch，无墙钟依赖 | `fixed-virtual-time@2026-01-01T00:00:00+00:00` |
| 随机 `seed` | `random.Random(SEED)` 固定种子，保证截图/布局随机性可复现 | `20261020` |
| 浏览器 `browser_major` | 占位（无内置引擎），1-7-3 回填真实 major | `PENDING@1-7-3` |
| 运行时 `node_version` | 目标 EV 运行时约束（Next.js 14） | `>=18.17` |
| 视口 `viewports` | 必测断点（1-3 capability manifest S8 FF-BRK：390/768/1440） | v0.2：`390x844, 768x1024, 1440x900`（1-5-2 占位 `1280x800, 375x667` 已废弃） |
| 配置 `config_hash` | viewport 集 + 断言阈值 + oracle 集 的 sha256（阈值集自 1-5-3 起由 `hard_gates.GATE_THRESHOLDS` 单一供给） | v0.2：`70ecd3879750d8e70f365e8d78f5ae284c37189f2ae137f69f63f89c348b1830`（1-5-2 首跑为 `e5d3f6c0dda4fd74fa6fbb50f808b0a1b826900aca9ec7c2b13396346486de7e`） |

> 确定性不依赖 `PYTHONHASHSEED`：runner 所有序列化走 `canonical_json`（sort_keys +
> 固定分隔），dict/set 迭代显式 `sorted()`，跨进程/跨时间稳定（与本仓库跨 carrier 回放约束一致）。

---

## 3. Runner 生命周期与 CLI（R-HAR-1）

```
dual_lane_runner.py init [--plans DIR]      # 幂等建立 fixture 目录骨架 + 计算 manifest_hash（--write 落盘）
dual_lane_runner.py fingerprint [--plans DIR] # 捕获 env 轴 + config_hash + env_hash + matrix_key
dual_lane_runner.py plan [--lane baseline|degraded]  # 输出 cell 计划
dual_lane_runner.py run  --lane <baseline|degraded> [--observations DIR]  # 执行 lane
dual_lane_runner.py selfcheck [--plans DIR]  # 复跑幂等自检（rerun_idempotent）
dual_lane_runner.py demo                     # 确定性控制自检（虚拟时钟 + seed）
```

`--observations DIR`（1-5-3 起）：指向 `<fixture_id>/<viewport>.json` 的 observation bundle 根目录。
未给该参数时 baseline 全 `NOT_EXECUTED`（与 1-5-2 行为一致，fail-closed）；给了但覆盖不全时
缺证据的 fixture 记 `HG-EVID-02`，cell 最好只能到 `HUMAN_REVIEW_REQUIRED`。
门禁判定逻辑本身见 `ui-agent-skills-hard-gates.md`。

本会话采用 **print-only**（默认不写盘），由专用工具把计算结果写回 `docs/designs/ui-agent-skills/*.json`，
规避工作区写沙箱；runner 自身保留 `--write` 落盘逻辑，未来环境可直接冻结。

---

## 4. 可重算与 revalidation

```
manifest_hash = sha256( canonical_json( fixtures 按 id 排序的稳定字段
                 {id,class,source,trigger,expected,landed_at,status} ) )

env_hash      = sha256( "|".join([ browser_major, node_version, font,
                 network_mode, clock_source, seed, config_hash ]) )   # 固定顺序

matrix_key    = sha256( manifest_hash + env_hash
                 + sorted(DIMENSIONS) + canonical_json(CELL_GATE) )
```

- 上述三者已由 R-HAR-1 首跑计算并冻结（见下）。
- 任一轴 / fixture / 维度集合 / cell 门禁变化 → 对应 hash 变化 → `stale / revalidation_required`。
- **首跑冻结值（1-5-2）**：
  - `manifest_hash` = `5c72b455a1b7b91a347dea10db7fd0a0116b321188ea0475a26fa2abe5743825`
  - `env_hash`      = `6a1f1a72989c85d0795b87ae0cfc1bd01192eb6c86c1882db44368bedc206858`
  - `matrix_key`    = `010a2f83d794f1660f14b5dbb36dc6a3aaf46b4baaebc4d1a3d4f0a00505a69c`
  - `config_hash`   = `e5d3f6c0dda4fd74fa6fbb50f808b0a1b826900aca9ec7c2b13396346486de7e`
- `rerun_idempotent = true`：同输入两次运行得到相同三 hash（可复跑证据）。

### 4.1 config v0.2 重算（1-5-3）

1-5-3 把 viewport 集对齐 1-3 capability manifest（必测 390/768/1440），阈值集并入
`hard_gates.GATE_THRESHOLDS`，`config_hash` 因此变化并按 §4 公式重算三 hash：

- `config_hash` = `70ecd3879750d8e70f365e8d78f5ae284c37189f2ae137f69f63f89c348b1830`
- `env_hash`    = `57efae87180b2e27b1a43d02593c97f98b4c7ecc3b047fa72ab8c4f42149e02e`
- `matrix_key`  = `10ac66d18f56143e74a834907a6c2c318915164afd42e05cb9c32287ecfc0633`
- `manifest_hash` 不变（fixture-manifest 未改）

重算不覆盖任何既有结论：1-5-2 两条 lane 的 21 个 cell 全部 `NOT_EXECUTED` / `DEGRADED_SKIP`，
轴变化发生在首份结论产生之前（与 L-FONT 先例一致）。旧值保留在本节作为历史。

---

## 5. 已落地 / 待落地 清单

| 项 | 状态 | 责任节点 |
| --- | --- | --- |
| 双 lane 调度骨架 | ✅ 已实现 | 1-5-2 |
| 确定性控制（font/network/clock/seed/config_hash） | ✅ 已冻结 | 1-5-2 |
| `manifest_hash` / `env_hash` / `matrix_key` 计算 + 冻结 | ✅ 已计算写回 | 1-5-2 |
| fixture 目录骨架（19 个 landed_at 目录） | ✅ 已建立（空，待数据） | 1-5-2 |
| 真实 fixture 数据文件（F-1…GF-11） | ⏳ 待落地 | 1-6 / 1-7 |
| 真实 cell 断言（7 类硬门禁逻辑 + 自检 61 例） | ✅ 已实现（`hard_gates.py`） | 1-5-3 |
| 真实 observation 证据（浏览器捕获） | ⏳ 待 adapter | 1-7-3 |
| 契约维度断言（round_trip / migration / offline_recovery） | ⏳ 待 engine/投影 | 1-6 / 1-9 |
| `browser_major` 真实值 | ⏳ 占位 PENDING@1-7-3 | 1-7-3 |
| 完整 verification receipt 格式 | ✅ 已定稿（R-RCP-1） | 1-5-4 |

---

## 6. 上下游契约义务

- **向上**：消费 1-5-1 冻结的 fixture-manifest / verification-matrix / env-fingerprint（过程），
  把"冻结过程"转为可执行 runner 与 concrete 值。
- **向下（1-5-3）**：DOM/ARIA/focus/contrast/overflow/responsive/motion/state 硬门禁在 baseline
  lane 上实现（需 adapter）。→ 已于 1-5-3 落地：`hard_gates.py`（R-HAR-2）+ `--observations` 接线，
  契约见 `ui-agent-skills-hard-gates.md`。
- **向下（1-5-4）**：本节点 receipt 为结构占位；receipt 完整字段（claim/check/risk/fixture/env/
  oracle/threshold/command/commit/artifact/observed/status/reviewer/expiry）由 1-5-4 定稿，
  须携带 `matrix_key` 与每个 cell 的 `observed/status`，保证可归因、可重算。→ 已于 1-5-4 定稿：
  `ui-agent-skills-verification-receipt.md` §1（schema v1）+ `verification_receipt.py`
  （`build_receipt` 把本文件的 lane receipt 升格为完整收据，`observed.checked` 由本节点提供）。
- **向下（1-9）**：每次 paired run 须比对 `env_hash`，失配则 run 无效（invalid-run 规则，scope-manifest §4）。

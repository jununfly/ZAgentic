# Verification Matrix — UI Agent Skills（1-5-1 冻结版）

- **归属节点**：1-5-1（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：ui-agent-skills 路线图（已收口，carrier 文件已清理）
- **输入**：`ui-agent-skills-fixture-manifest.md`（fixture 全集）、`ui-agent-skills-env-fingerprint.md`（指纹轴）
- **状态**：冻结版（维度集合 + cell 门禁 + key 派生）；cell 实测在 1-5-2/1-5-3/1-9 执行。
- **退出判据对齐**：1-5-1 退出 = verification matrix key 与 fixture/env fingerprint 完整且可重算。

---

## 1. 验证维度（冻结集合）

维度来自 **1-5 退出判据**与 **golden-fixtures-spec**：

| 维度 | 类别 | 含义 | oracle 类型 |
| --- | --- | --- | --- |
| `dom_aria` | 视觉/结构 | DOM 结构与 ARIA 语义正确 | 静态断言 |
| `focus` | 交互 | 焦点顺序/可达性/trap | 交互模拟 |
| `contrast` | 视觉 | 文本对比度达标（WCAG AA） | 像素/计算 |
| `overflow` | 视觉 | 无意外溢出/裁切 | 布局断言 |
| `responsive` | 视觉 | viewport 集下布局正确 | 多视口截图比对 |
| `motion` | 视觉/动效 | 动效不遮挡/可降级 | 动效断言 |
| `state` | 状态 | 状态机（`idle→validating→submitting→success\|error`）+ 字段级 error 覆盖 | 状态机断言 |
| `round_trip` | 契约 | canonical→projection→canonical 语义集合等价 | 语义哈希 |
| `migration` | 契约 | v1 向后兼容加字段；破坏性变更升主版本+迁移器 | schema 断言 |
| `offline_recovery` | 契约 | 断网/删除 adapter 仅凭本地 canonical 恢复 | 恢复断言 |

> `dom_aria/focus/contrast/overflow/responsive/motion/state` 与 1-5 退出判据逐字对齐；`round_trip/migration/offline_recovery` 来自 golden-fixtures-spec，覆盖契约层确定性。

---

## 2. 矩阵（维度 × fixture 分类）

`A`=适用并硬门禁，`W`=适用仅 warning，`-`=不适用。

| 维度 \ 分类 | `form` | `adapter` | `contract` |
| --- | --- | --- | --- |
| dom_aria | A | A | A（canonical 结构） |
| focus | A | A | A |
| contrast | A | A | - |
| overflow | A | A | - |
| responsive | A | A | - |
| motion | A | A | - |
| state | A | A | A（状态机语义） |
| round_trip | - | A（投影回转） | A |
| migration | - | - | A |
| offline_recovery | - | - | A |

- `form`/`adapter` 跑全套视觉/交互维度；`contract` 跑结构与契约维度。
- 每个适用 cell 的**具体断言**由 `fixture-manifest` 中对应 fixture 的 `expected` 字段 + golden-fixtures-spec §1 失败分类确定。

---

## 3. 门禁语义（与 golden-fixtures-spec §8 对齐）

| 结果 | 触发 | 退出状态 |
| --- | --- | --- |
| hard fail | 核心语义静默丢失 / 必需字段缺失 / 越权修改 owned 字段 | `FAIL` |
| warning | 可选字段不支持 / 声明性 unknown（须一一对应 warning） | 逐字段 warning，不阻断 |
| recovery error | 断网/删除 adapter 后无法仅凭本地 canonical 恢复 | `BLOCKED` |
| evidence missing | 缺原始日志/屏幕/DOM 证据（invalid-run） | `HUMAN_REVIEW_REQUIRED` |
| un-attributable | 失败无法归因到具体 fixture/维度 | `QUARANTINED` |

> 闸门（0 容忍，golden-fixtures-spec §8）：核心 state/action/intent/acceptance 静默丢失 = 0；未声明 warning = 0；离线恢复成功率 = 100%；必填语义保留率 = 100%。

---

## 4. 可重算 key

```
matrix_key = sha256(
    manifest_hash
    + env_hash
    + sorted(dimensions)            # 本文件 §1 冻结集合
    + cell_gate_map                 # §2 的 A/W/- 映射（有序序列化）
)
```

- `matrix_key` 随 `fixture-manifest`（fixture 增删/内容变）、`env-fingerprint`（任一轴变）、维度集合或 cell 门禁变化而确定性变化。
- 变化即判定 `stale / revalidation_required`，须重跑受影响 cell 并重新出具 receipt（1-5-4）。
- 本冻结版锁定**集合与派生过程**；`matrix_key` 具体值由 1-5-2 runner 在 fixture/env 落地后计算。
- **当前冻结值**（1-5-3 config v0.2 重算，viewport 集对齐 390/768/1440）：
  `matrix_key = 10ac66d18f56143e74a834907a6c2c318915164afd42e05cb9c32287ecfc0633`
  （1-5-2 首跑值 `010a2f83…05a69c` 仅作历史——当时 21 个 cell 全未执行，不存在被覆盖的结论）。

---

## 5. 上下游契约义务

- **向上**：消费 1-5 退出判据（七维度）、golden-fixtures-spec（契约层 + 闸门）、scope-manifest（EV-v0.1 状态机）、wave0-ledger（fixture 来源）。
- **向下（1-5-2）**：runner 须用本矩阵 × `fixture-manifest` 生成 cell 计划，计算 `matrix_key`。
- **向下（1-5-3）**：DOM/ARIA/focus/contrast/overflow/responsive/motion/state 硬门禁在此矩阵上实现。
- **向下（1-5-4）**：receipt 须携带 `matrix_key` 与每个 cell 的 observed/status，保证结论可归因、可重算。
  → 已定稿：`ui-agent-skills-verification-receipt.md` §1/§2（schema v1 + 四层聚合 + 计数分母）。

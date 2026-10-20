# 硬门禁契约 — UI Agent Skills（1-5-3 交付版）

- **归属节点**：1-5-3（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：`docs/plans/ui-agent-skills-roadmap.json`
- **机器实现**：`research/ui-agent-skills/hard_gates.py`（R-HAR-2，纯 stdlib）
- **接线**：`research/ui-agent-skills/dual_lane_runner.py`（R-HAR-1，`run --lane baseline --observations DIR`）
- **上游**：`ui-agent-skills-verification-matrix.md`（维度 × cell 门禁）、`ui-agent-skills-fixture-manifest.json`（fixture 全集）、`ui-agent-skills-env-fingerprint.json`（env 指纹）、`ui-agent-skills-dual-lane-runner.md`（双 lane）
- **状态**：门禁逻辑已实现并自检；真实浏览器捕获待 1-7-3，真实 fixture 数据待 1-6/1-7。
- **退出判据对齐**：1-5-3 退出 = 硬门禁覆盖 DOM/ARIA、focus、contrast、overflow、responsive、motion 和关键状态。

---

## 0. 范围与边界

**在口径内**：7 类硬门禁的判定逻辑（R-HAR-2）、observation bundle 契约（R-OBS-1）、
结果语义与聚合规则、与双 lane runner 的接线、门禁自检（正例 + 反例 + 缺证据例）、
`config` v0.2 与指纹重算。

**在口径外（显式延迟，非静默接受）**：

| 项 | 归属 | 说明 |
| --- | --- | --- |
| 浏览器真实 DOM/布局/样式/焦点捕获 | 1-7-3（Storybook active adapter） | 本节点只消费 observation bundle，不实现采集 |
| 真实 fixture 数据（F-1…GF-11） | 1-6 / 1-7 | 缺数据时门禁不执行，标 `HUMAN_REVIEW_REQUIRED` |
| `round_trip` / `migration` / `offline_recovery` 三个契约维度 | 1-6 / 1-9 | 需 flow engine + canonical 投影，不在 1-5-3 七维度口径内 |
| receipt 完整字段与 quarantine 归因流程 | 1-5-4 | 本节点只产出 `observed` + `status` 供其消费 |

> **fail-closed 红线**：任何"没证据可判"都不得落到 `PASS`。见 §3。

---

## 1. Observation bundle 契约（R-OBS-1）

门禁与采集解耦：采集端（1-7-3 adapter）只负责产出证据，门禁只负责判定。
证据按 **fixture × viewport** 落盘：

```
<observations>/<fixture_id>/<viewport>.json      # viewport ∈ 390x844 | 768x1024 | 1440x900
```

```jsonc
{
  "schema": "ui-agent-skills/observations/v1",
  "fixture_id": "F-1",
  "class": "form",                  // form | adapter | contract
  "viewport": "390x844",
  "captured_by": "storybook@8.x",   // 采集者标识（可追溯）
  "captured_at": "2026-01-01T00:00:00+00:00",
  "dom":      { "nodes": [ ... ] },  // 结构与 ARIA
  "focus":    { "sequence": [...], "focus_visible": [...], "trap": {...}|null },
  "contrast": { "samples": [ ... ] },
  "layout":   { "viewport": {...}, "document": {...}, "boxes": [...], "targets": [...],
                "no_overlap_pairs": [...], "expected_layout": "stacked", "observed_layout": "stacked" },
  "motion":   { "animations": [ ... ], "reduced_motion_emulated": false },
  "states":   { "machine": "ev-v0.1", "transitions": [...], "submits": [...], "field_errors": [...] },
  "quarantine": []                   // adapter 自报无法归因的证据
}
```

### 1.1 节点（`dom.nodes[]`）字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 节点稳定 id（idref 解析与归因的锚点） |
| `tag` / `role` | 是 | 原生标签 + computed role |
| `name` | 交互节点必填 | **computed accessible name**（adapter 计算出，不由门禁推断） |
| `name_source` | 建议 | `label` / `labelledby` / `aria-label` / `placeholder` / `text`；缺省则跳过 HG-DOM-03 |
| `parent_id` | 建议 | 父子关系（供隐藏子树判定） |
| `tabindex` / `focusable` / `disabled` / `hidden` | 建议 | 焦点门禁输入 |
| `aria` | 建议 | `label/labelledby/describedby/controls/errormessage/owns/checked/expanded/modal/valuenow/hidden` |
| `attrs` | 建议 | `alt`/`type`/`placeholder` 等 |
| `text` / `heading_level` | 建议 | 文本与标题层级 |

### 1.2 必填段与空段语义

- 单 viewport 门禁只要求**自己那一段**：`dom_aria`→`dom`，`focus`→`dom`+`focus`，
  `contrast`→`contrast`，`overflow`→`layout`，`motion`→`motion`，`state`→`states`。
- **段缺失、空 list、空 dict 一律视为证据缺失**（`HG-EVID-01`），不是"0 个问题所以 PASS"。
- `responsive` 需要**整套 viewport**；缺任一必测 viewport → `HG-RSP-01`（证据缺失）。

---

## 2. 断言目录（7 门禁 / 45 条）

`severity`：`hard` → `FAIL`；`warning` → `WARNING`；`evidence` → `HUMAN_REVIEW_REQUIRED`；
`unattributable` → `QUARANTINED`（不参与 status 计算，仅入账）。

| code | 门禁 | severity | 断言 |
| --- | --- | --- | --- |
| HG-DOM-01 | dom_aria | hard | 交互节点必须有可及名称 |
| HG-DOM-02 | dom_aria | hard | `aria-labelledby/describedby/controls/errormessage/owns` 不得悬空 |
| HG-DOM-03 | dom_aria | hard | 表单控件不得仅靠 `placeholder` / 纯文本命名 |
| HG-DOM-04 | dom_aria | hard | `checkbox/switch/radio`→`aria-checked`、`combobox`→`aria-expanded`、`slider`→`aria-valuenow`、`dialog`→`aria-modal` |
| HG-DOM-05 | dom_aria | hard | `img` 必须有 `alt` 或显式装饰（`aria-hidden` / `role=presentation`） |
| HG-DOM-06 | dom_aria | hard | 节点 id 唯一 |
| HG-DOM-07 | dom_aria | warning | 标题层级不得跳级 |
| HG-DOM-08 | dom_aria | hard | `aria-hidden=true` 子树内不得有可聚焦节点 |
| HG-FOC-01 | focus | hard | 交互节点必须可达（tab 序列内） |
| HG-FOC-02 | focus | hard | 禁止正 `tabindex`（破坏 DOM 顺序） |
| HG-FOC-03 | focus | hard | 焦点顺序必须与 DOM 顺序一致 |
| HG-FOC-04 | focus | evidence | 焦点序列引用了不存在的节点（证据不可用） |
| HG-FOC-05 | focus | hard | 入序节点必须有可见焦点指示（outline / box-shadow） |
| HG-FOC-06 | focus | hard | dialog trap：进入 / 环绕 / Esc 释放 / 焦点归还 |
| HG-FOC-07 | focus | warning | `disabled` 节点不得出现在焦点序列 |
| HG-CON-01 | contrast | hard | 正文对比度 ≥ 4.5:1 |
| HG-CON-02 | contrast | hard | 大字号对比度 ≥ 3:1（≥18.66px，或 ≥14px 且 weight ≥ 700） |
| HG-CON-03 | contrast | hard | 非文本（UI 边界/图形）对比度 ≥ 3:1 |
| HG-CON-04 | contrast | evidence | 颜色无法解析 / 透明度未合成 → 无法判定 |
| HG-OVF-01 | overflow | hard | 文档无水平溢出（阈值 0px） |
| HG-OVF-02 | overflow | hard | 元素内容不得在非滚动容器里被裁切 |
| HG-OVF-03 | overflow | hard | 元素不得超出 viewport 宽度 |
| HG-OVF-04 | overflow | hard | 文本被裁切必须有 ellipsis / line-clamp |
| HG-RSP-01 | responsive | evidence | 必测 viewport 覆盖齐全（390/768/1440） |
| HG-RSP-02 | responsive | hard | bundle 声明宽度与 viewport 名一致 |
| HG-RSP-03 | responsive | hard | 每个 viewport 复用 overflow 判定（带 viewport 归因） |
| HG-RSP-04 | responsive | hard | 声明不重叠的交互目标不得重叠 |
| HG-RSP-05 | responsive | warning | 交互目标 ≥ 24×24（WCAG 2.2 AA） |
| HG-RSP-06 | responsive | hard | 布局与声明的 breakpoint 形态一致 |
| HG-MOT-01 | motion | hard | 有动画必须有 `prefers-reduced-motion` 降级变体 |
| HG-MOT-02 | motion | hard | 降级变体时长 ≤ 1ms（真降级，不是"缩短一点"） |
| HG-MOT-03 | motion | hard | 无限动画不得覆盖交互元素 |
| HG-MOT-04 | motion | warning | 自动播放 > 5s 必须有暂停控制 |
| HG-MOT-05 | motion | hard | reduced-motion 模拟下不得仍有动画 |
| HG-MOT-06 | motion | evidence | 动画时长不可解析 |
| HG-STA-01 | state | hard | 转移必须在 EV-v0.1 冻结状态机内 |
| HG-STA-02 | state | hard | fixture 必需状态必须全部出现 |
| HG-STA-03 | state | hard | `submitting` 态拒收第二次提交（F-4） |
| HG-STA-04 | state | hard | `error` 态必须有恢复路径（F-5） |
| HG-STA-05 | state | hard | 字段级 error 必须有 message |
| HG-STA-06 | state | hard | 字段级 error 必须被公告（aria-live / describedby） |
| HG-STA-07 | state | evidence | 状态机版本非 `ev-v0.1` → 无法按冻结口径判 |
| HG-EVID-01 | 全部 | evidence | 本门禁所需的段缺失 / 为空 |
| HG-EVID-02 | 全部 | evidence | class 内 fixture 覆盖不全（有 fixture 无 bundle） |
| HG-EVID-03 | 全部 | evidence | 段存在但 `checked == 0`（一条断言都没跑，属空转假绿） |
| HG-QUAR-01 | 全部 | unattributable | adapter 自报证据无法归因 |

### 2.1 EV-v0.1 状态机（唯一合法边集）

```
idle -> validating -> submitting -> success
          |    ^           |
          v    |           v
        error -+        (422 / timeout)
success -> idle（reset）
```

合法边集（`ALLOWED_TRANSITIONS`）：

```
idle->validating, validating->idle, validating->error, validating->submitting,
error->validating, error->idle, submitting->success, submitting->error, success->idle
```

其他任何转移 = `HG-STA-01` 硬失败。**`blocked`/未知状态不接受**——越界转移不是"新状态"，
是状态机语义漂移，按 0 容忍处理。

---

## 3. 结果语义与聚合

```
status 优先级：FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED > WARNING > PASS
```

| 情形 | status | 说明 |
| --- | --- | --- |
| 任一 `hard` finding | `FAIL` | 0 容忍，不可降级为 warning |
| 任一 `evidence` finding | `HUMAN_REVIEW_REQUIRED` | 缺证据 ≠ 通过 |
| 有 `quarantine` 且无 `FAIL` | `QUARANTINED` | 无法归因，不进分母，修复后新 run id 重跑 |
| 仅 `warning` | `WARNING` | 不阻断，但必须一一对应 |
| 断言全过且 `checked > 0` | `PASS` | 自检强制校验 `checked > 0`（防空转假绿） |

> **系统级兜底**：`checked == 0` 却想 `PASS` 的，`_finish` 一律改判 `HUMAN_REVIEW_REQUIRED`
> 并追加 `HG-EVID-03`。这不是"某个门禁忘了判空"，而是门禁框架层的约束——新增门禁即使
> 漏写判空分支，也不会静默变成通过。

**cell 级**：cell = (dimension × class)，对该 class 全部 fixture × viewport 的门禁结果聚合；
任一 fixture 缺 bundle → 追加 `HG-EVID-02`，因此**部分覆盖永远拿不到 PASS**
（capability manifest S8 FF-BRK-03：不得以"部分通过"冒充 PASS）。

**lane 级**（`dual_lane_runner._overall_status`）：

```
FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED >
  （无 cell 执行 → BLOCKED）> （有 cell 未执行 → PARTIAL）> WARNING > PASS
```

**degraded lane**：视觉/adapter 门禁一律 `DEGRADED_SKIP`，离线恢复归 1-6/1-9；
本节点不把 degraded 的 skip 计入通过率。

---

## 4. 与 runner 的接线

```bash
python research/ui-agent-skills/hard_gates.py selftest          # 门禁逻辑自检（35 例）
python research/ui-agent-skills/dual_lane_runner.py run --lane baseline --observations <DIR>
```

| 情形 | cell status | overall |
| --- | --- | --- |
| 未给 `--observations` | 全 `NOT_EXECUTED` | `BLOCKED`（与 1-5-2 一致，fail-closed） |
| 给了但 class 内全缺 | `NOT_EXECUTED` + reason | `BLOCKED` / `PARTIAL` |
| class 内部分 fixture 有证据 | 门禁判定 + `HG-EVID-02` → 最好 `HUMAN_REVIEW_REQUIRED` | 同上 |
| 全覆盖且断言全过 | `PASS` | `PASS` |
| 任一 hard 失败 | `FAIL` | `FAIL` |

receipt 每个 cell 增加 `observed` 明细（`fixtures_seen` / `bundles` / `missing_fixtures` /
`findings[]`），并带上 `config_version` / `config_hash` / `observations_dir`，供 1-5-4
的 `observed/status` 字段直接消费。

---

## 5. config v0.2 与指纹重算（显式偏差，非静默）

1-5-2 冻结的 `VERIFICATION_CONFIG.viewports` 是占位 `1280x800 / 375x667`，与 1-3 capability
manifest（S8 FF-BRK：必测 390/768/1440）冲突。1-5-3 按契约对齐为 **390x844 / 768x1024 /
1440x900**，并把阈值集并入 `hard_gates.GATE_THRESHOLDS`（单一事实源，runner 不再另抄）。

| 量 | 1-5-2 冻结值 | v0.2 重算值 |
| --- | --- | --- |
| `config_hash` | `e5d3f6c0…86de7e` | `70ecd3879750d8e70f365e8d78f5ae284c37189f2ae137f69f63f89c348b1830` |
| `env_hash` | `6a1f1a72…206858` | `57efae87180b2e27b1a43d02593c97f98b4c7ecc3b047fa72ab8c4f42149e02e` |
| `matrix_key` | `010a2f83…05a69c` | `10ac66d18f56143e74a834907a6c2c318915164afd42e05cb9c32287ecfc0633` |
| `manifest_hash` | `5c72b455…743825` | 不变（manifest 未改） |

**为什么不算"覆盖既有结论"**：1-5-2 两条 lane 的 21 个 cell 全部 `NOT_EXECUTED` /
`DEGRADED_SKIP`，没有任何 `PASS` 结论依赖旧 viewport 集；轴变化发生在首份结论产生前，
沿用 L-FONT 先例（轴变化 → 重冻结 → revalidation 规则对未来结论生效）。

---

## 6. 自检证据（门禁逻辑本身）

`hard_gates.py selftest` = **63 例**，覆盖目录里全部 **46 条断言码**（无一条"写了没响过"）：

| 类别 | 数量 | 判据 |
| --- | --- | --- |
| 正例（7 门禁 + 阈值分流） | 8 | `PASS` **且 `checked > 0`**（防空转假绿） |
| 反例（必须命中预期 code） | 42 | status 与 **预期 code** 同时匹配，不是"随便非 PASS" |
| 缺证据 / 空段 / 空转 | 11 | `HUMAN_REVIEW_REQUIRED` + `HG-EVID-01` 或 `HG-EVID-03` |
| quarantine | 1 | `QUARANTINED` + `HG-QUAR-01` |
| runner 级覆盖不全 | 1 | `HG-EVID-02`（单 bundle 门禁不触发，由 class 覆盖判定触发） |

```bash
python research/ui-agent-skills/hard_gates.py selftest
# {"total": 63, "failed": 0, "ok": true}   exit 0；任一用例不匹配 -> exit 1
python -m unittest tests.test_ui_agent_skills_hard_gates   # 14 项，含文档/代码码表一致性
```

其中三条专治假绿：

- `contrast/large-text-threshold-differs`：同一颜色 `#7c8288`（3.885:1）在 20px 判 `PASS`，
  证明大字号 3:1 与正文 4.5:1 两个分支真的分流，而不是恒取宽松值。
- `focus/empty-sequence` + `dom_aria/no-assertions-ran`：段存在但断言一条都跑不了时
  **必须是 `HUMAN_REVIEW_REQUIRED`**。这两个用例是在写单测时抓到的真实缺陷——
  首版 `gate_focus` 在 `dom.nodes` 与 `focus.sequence` 都为空时返回了 `PASS`（`checked=0`），
  现已由门禁自身的 `checked == 0 -> HG-EVID-03` 系统级兜底，不再依赖每个门禁自觉。
- `runner/missing-fixtures`：只给 1/6 fixture 的证据时必须是 `HUMAN_REVIEW_REQUIRED`，
  证明"部分覆盖不判 PASS"。

> 自检夹具是**内存合成**的，只证明门禁逻辑与 fail-closed 语义，**不构成验收证据**；
> 真实证据必须来自 1-7-3 的 observation bundle。

---

## 7. 上下游契约义务

- **向上**：实现 verification-matrix §1 七维度与 §2 的 A/W cell 门禁；消费 fixture-manifest
  的 fixture 全集（class 覆盖）；消费 env-fingerprint 的 config_hash 参与 `matrix_key`。
- **向下（1-5-4）**：每 cell 提供 `observed` + `status` + `findings[]`，evidence /
  unattributable 两级语义已分离，receipt 可直接引用。
- **向下（1-6/1-7）**：adapter 必须按 R-OBS-1 产出 bundle；`name` 为 computed accessible
  name，`name_source` 缺省即放弃 HG-DOM-03（不得由采集端自行补判）。
- **向下（1-9）**：paired run 比 `env_hash`；`QUARANTINED` 项不进分母。

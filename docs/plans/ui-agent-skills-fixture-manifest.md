# Fixture Manifest — UI Agent Skills（1-5-1 冻结版）

- **归属节点**：1-5-1（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：`docs/plans/ui-agent-skills-roadmap.json`
- **机器清单**：`docs/plans/ui-agent-skills-fixture-manifest.json`
- **状态**：冻结版（catalog + 指纹策略）；具体 fixture 数据文件于 **1-5-2** 落地。
- **退出判据对齐**：1-5-1 退出 = verification matrix key 与 fixture/env fingerprint 完整且可重算。

---

## 0. 范围与边界

本清单冻结 Wave 0（**EV-v0.1 表单基准**）确定性验证所需的 canonical fixture 全集：每条 fixture 的来源文档、触发路径、预期结果与落地点。它是 `verification-matrix.md` 与 `env-fingerprint.md` 的输入，也是 **1-5-2** 双 lane runner 的被测对象目录。

- **在口径内**：清单内的 fixture。
- **在口径外**：任何未列入本清单的 fixture 不得进入确定性验证口径；新增 fixture 须经本清单 + roadmap `decide` 落盘，并触发 `manifest_hash` 重算。
- **不落地代码**：本文件是契约冻结，不含可执行断言（可执行断言待 1-5-2 runner 与 1-6 技能实现后跑）。

---

## 1. Fixture 分类与来源（与上游账本/规范对齐）

| 分类 | 数量 | 来源 | 说明 |
| --- | --- | --- | --- |
| `form` 表单六类 | 6 | `ui-agent-skills-wave0-ledger.md` §3（F-1~F-6） | 对应 `ev-metrics.md` §1 invalid-run 边界用例 |
| `adapter` 适配器 | 2 | `ui-agent-skills-wave0-ledger.md` §3（F-A1/F-A2） | Storybook active / json-render·A2UI·M3E opt-in |
| `contract` 契约级 | 11 | `ui-agent-skills-golden-fixtures-spec.md` §2（GF-01~GF-11） | round-trip / 迁移·schema-lock / 离线恢复 / adapter 删除恢复 |

---

## 2. 冻结清单（权威目录）

### 2.1 `form`（表单六类，源自 wave0-ledger F-1~F-6）

| ID | 内容 | 触发路径 | 预期结果 | 落地点 | 状态 |
| --- | --- | --- | --- | --- | --- |
| F-1 | 成功路径（合法 profile） | idle→validating→submitting→success | mock 200 + 本地持久化 | `tests/ui-agent-skills/fixtures/form/F-1` | planned |
| F-2 | 空提交 | 必填校验 | 字段级 error，禁止提交 | `tests/ui-agent-skills/fixtures/form/F-2` | planned |
| F-3 | 非法格式（邮箱/长度） | 实时校验 | 字段级 error message | `tests/ui-agent-skills/fixtures/form/F-3` | planned |
| F-4 | 重复提交（提交中再触发） | submitting 锁输入 | 第二次提交被拒/忽略 | `tests/ui-agent-skills/fixtures/form/F-4` | planned |
| F-5 | 服务端 422 | 模拟 mock 422 | error 态 + 可恢复回 editable | `tests/ui-agent-skills/fixtures/form/F-5` | planned |
| F-6 | 超时 | 模拟服务端超时 | fallback 到稳定路径 / 显式标记 | `tests/ui-agent-skills/fixtures/form/F-6` | planned |

### 2.2 `adapter`（适配器，源自 wave0-ledger F-A1/F-A2）

| ID | 内容 | 归属 | 状态 |
| --- | --- | --- | --- |
| F-A1 | Storybook stories / a11y / viewport / interaction / docs | 1-7-3 active | planned |
| F-A2 | json-render / A2UI / M3E Canvas golden fixtures | 1-7-4 opt-in | planned |

### 2.3 `contract`（契约级，源自 golden-fixtures-spec GF-01~GF-11）

| ID | 内容 | 断言要点 | 失败分类 |
| --- | --- | --- | --- |
| GF-01 | 正常 flow round-trip | canonical→projection→canonical 后 `state/action/intent/acceptance` 语义集合等价 | 不一致 = fail |
| GF-02 | 缺 required 字段 | 必需字段缺失必须阻断 | hard fail |
| GF-03 | 未知字段 | 保留 `unknown` 四元组并生成声明性 warning | 静默丢弃 = fail |
| GF-04 | adapter 越权修改 owned 字段 | 改 `intent`/`acceptance` 必须失败并报字段路径 | hard fail |
| GF-05 | unknown 被压成空值 | 不得编码为空字符串/null | fail |
| GF-06 | 重复/冲突 action | 同一 `action+pre-state` 仅允许一个 canonical transition | 拒绝提交 |
| GF-07 | 并发转换 | 幂等键相同输入的并发提交不产生重复/半套结果 | 违反幂等 = fail |
| GF-08 | 迁移 | v1 向后兼容加字段通过；破坏性变更升主版本+迁移器 | 无迁移器破坏性变更 = fail |
| GF-09 | schema lock 重跑 | schema/adapter 修改后重跑全套；失败保留旧 artifact | 越权推进 = fail |
| GF-10 | 离线恢复 | 服务关闭时仅凭本地 canonical 重建 flow/恢复状态/重放动作 | 无法恢复 = recovery error |
| GF-11 | adapter 删除恢复 | 删除 adapter 后仍可从最后完整 canonical revision 恢复 | 恢复失败 = fail |

### 2.4 `skill`（阶段技能级，1-6-2 落地；源自 1-3-1 §4）

首批 12 条，四阶段 × 3（正常 / 冲突 / 失败）。与 1-5-1 冻结的 `form` / `adapter` / `contract` 不同，
这一类的期望不是"跑出一个页面"，而是**状态机与副作用次数**：`status` / `writes` /
`unknown` 四元组 / 被拒字段名 / quarantine 集合 / 产物里哪些字段必须存在、哪些**必须不存在**。

| ID | 内容 | 断言要点 | 期望终态 |
| --- | --- | --- | --- |
| FF-BRIEF-01 | 四类必填齐备 | reversion 提交、unknown 为空 | `OK`，`writes=1` |
| FF-BRIEF-02 | 缺 `success_criteria` | 转 unknown 四元组，零写入 | `NEEDS_CONTEXT` |
| FF-BRIEF-03 | 草稿含 `successCriteria` 笔误 | deny-first 拒绝并列出字段 | `REJECTED`，`writes=0` |
| FF-DISC-01 | 三处缺口由可归因证据补齐 | unknown 清零，只增一轮 revision | `OK`，`writes=1` |
| FF-DISC-02 | 证据来源为 `assumed` | 值不进入产物，仅保留四元组 | `OK`，`artifact_absent: content.goal_task` |
| FF-DISC-03 | `questions_asked=3 > budget=2` | 停止并交人，不写 artifact | `NEEDS_CONTEXT`，`writes=0` |
| FF-DIR-01 | 三张可比卡 + Human 选 `card-b` | 写入唯一 `direction_choice` | `OK`，`writes=1` |
| FF-DIR-02 | 两卡并列、Human 未签 | 展示候选，**不按顺序取第一** | `HUMAN_REVIEW_REQUIRED`，`writes=0` |
| FF-DIR-03 | 参考 `license: unknown` | 该卡 quarantine，不进默认产物 | `QUARANTINED`，`writes=0` |
| FF-DS-01 | tokens + 已注册 catalog | 两对 contrast 全达标 | `OK`，`writes=1` |
| FF-DS-02 | 未注册组件 `DateRangePicker` | adapter 不得扩表 | `BLOCKED`，`writes=0` |
| FF-DS-03 | `#777777 on #FFFFFF = 4.478` | 阻断且**不得替换相近色** | `BLOCKED`，`writes=0` |

跑批：`python skills/ui/zj-ui-core/scripts/run_fixture.py tests/ui-agent-skills/fixtures/skills --recursive`
（镜像断言由 `tests/test_ui_agent_skills_stage_skills.py` 守）。

---

## 3. 存储布局（`decide` 落盘）

- **根目录**：`tests/ui-agent-skills/fixtures/`（R-FIX-1 路径，原账本标"待定"，本节点冻结）
  - `form/` — F-1~F-6 数据
  - `adapters/` — F-A1/F-A2 数据
  - `contract/` — GF-01~GF-11 数据
  - `skills/` — FF-BRIEF / FF-DISC / FF-DIR / FF-DS 数据（1-6-2 起；每目录含 `input.json` + `expected.json`）
- **机器清单**：本文件配套 `ui-agent-skills-fixture-manifest.json`（含 `manifest_hash`）。
- 落地与 `manifest_hash` 回填在 **1-5-2**（R-HAR-1 runner 初始化时）；`skills/` 一类的 12 条于
  **1-6-2** 落地并重算（`manifest_hash` 由 `5c72b455…` 变为 `79b2ffa3…`）。

---

## 4. 可重算定义

```
manifest_hash = sha256( canonical_json(
    fixtures 按 id 排序，仅含稳定字段
    {id, class, source, trigger, expected, landed_at, status}
))
```

- fixture 内容或 `landed_at` 变更 → `manifest_hash` 变化 → verification `matrix_key` 变化 → 触发 `stale / revalidation_required`。
- `manifest_hash` 由 1-5-2 runner 在数据落地时计算并写回 json；本冻结版先锁定**过程**，值待回填。

---

## 5. 上下游契约义务

- **向上**：消费 `wave0-ledger` §3（F-1~F-6、F-A1/F-A2）与 `golden-fixtures-spec` §2（GF-01~GF-11），把"待验证声明"转为可枚举 fixture。
- **向下（1-5-2）**：runner 须按本清单建立 fixture 套件、计算 `manifest_hash`、喂给 `verification-matrix` 派生 `matrix_key`。
- **向下（1-9）**：paired run 的 fixture 须取自本清单，否则该 run 按 invalid 处理（`wave0-ledger` §3 末段）。

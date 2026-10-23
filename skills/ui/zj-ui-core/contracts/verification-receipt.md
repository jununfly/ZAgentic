# Verification Receipt 契约 — UI Agent Skills（1-5-4 定稿）

- **归属节点**：1-5-4（确定性验证、fixture 与 receipt · 计划层 · `exploit`）
- **事实源**：ui-agent-skills 路线图（已收口，carrier 文件已清理）
- **机器实现**：`skills/ui/zj-ui-core/scripts/verification_receipt.py`（R-RCP-1，纯 stdlib），稳定契约见本文件
- **上游**：`/docs/designs/ui-agent-skills/ui-agent-skills-dual-lane-runner.md`（lane receipt 结构占位）、`hard-gates.md`（cell `status` / `observed` / `findings` 语义）、`/docs/designs/ui-agent-skills/ui-agent-skills-verification-matrix.md`（`matrix_key`）、`env-fingerprint.json`（env 轴）、`fixture-manifest.json`（fixture 全集）
- **下游**：1-9 paired run（receipt 是唯一结论载体）、1-10 rollout（过期与重验决策）、`zj-ui-verify`（S9 产物）
- **退出判据对齐**：1-5-4 退出 = receipt 聚合、过期重评和无法归因 quarantine 状态可审计。
- **状态**：契约冻结 + 判定实现完成；真实证据仍待 1-7-3（observation bundle）与 1-6/1-9（契约维度）。

---

## 0. 范围与边界

**在口径内**：收据 schema v1、四层聚合语义、stale / revalidation_required 的判定与影响面收敛、
无法归因 quarantine 的记录/计数/解除条件、收据不可变与签发条件、以上全部判定逻辑与自检。

**在口径外（显式延迟，非静默接受）**：

| 项 | 归属 | 说明 |
| --- | --- | --- |
| 真实 observation bundle | 1-7-3 | 本节点只消费，不采集 |
| 真实 fixture 数据 | 1-6 / 1-7 | 缺数据时收据只能 BLOCKED / HUMAN_REVIEW_REQUIRED |
| `round_trip` / `migration` / `offline_recovery` 实测 | 1-6 / 1-9 | 收据为它们预留 cell，但当前口径内不判 |
| paired run 指标（返工/决策时间/escaped defect） | 1-9 | 收据只承载验证结论，不承载毕业指标 |
| 收据落盘 | 1-9 运行期 | 本节点维持 print-only，不新增写盘副作用 |

> **fail-closed 红线**：没有证据、没有签署、没有钉住 commit、算术不自洽的收据，
> 一律不得出现 `verdict = PASS`；"不知道"一律 `QUARANTINED`，不得写成 `FAIL`。

---

## 1. 收据 schema v1（R-RCP-1）

`schema = ui-agent-skills/verification-receipt/v1`，14 个固定段 + 5 个身份字段：

| 段 | 必填 | 内容 |
| --- | --- | --- |
| `schema` / `receipt_id` / `run_id` / `lane` / `issued_at` | 是 | 身份段；`receipt_id = rcp-<sha16(lane|run_id|body_hash)>` |
| `claim` | 是 | 声明了什么：`scope{dimensions,classes,viewports}` + `asserts` + `not_asserts`（**明确不声明什么**） |
| `checks` | 是 | 每个 cell 一条：dimension/class/gate/status/oracle/threshold/command/coverage/observed |
| `risks` | 是（可空） | 未关闭的风险与已知延迟（如 `browser_major=PENDING@1-7-3`） |
| `fixtures` | 是 | `manifest_hash` + `entries[{id,class,sha256}]` + `counts_by_class` |
| `env` | 是 | `env_hash` / `matrix_key` / `config_version` / `config_hash` / `axes` |
| `oracles` | 是 | 本收据使用的 oracle 全集（来自 config） |
| `thresholds` | 是 | 全量阈值快照（单条 cell 另存自己消费的阈值子集） |
| `command` | 是 | 可复跑命令（含 `--lane` / `--observations`） |
| `commit` | 是 | 40 位 sha；`UNPINNED*` 表示不可追溯 |
| `artifacts` | 是（可空） | `[{path, sha256}]`；证据目录无单文件产物时可空 |
| `observed` | 是 | `observations_dir` / `fixtures_seen` / `bundles` / `missing_fixtures` / `quarantine_records` / `worktree_dirty` |
| `status` | 是 | `verdict` / `raw_verdict` / `counts` / `coverage` / `reason_codes` / `quarantine` |
| `reviewer` | 是（可空） | `{name, signed_at}`；`PASS` 必填 |
| `expiry` | 是 | `{ttl_days, expires_at}`，默认 TTL 14 天 |

另有 `body_hash`（除 `receipt_id`/`issued_at`/`freshness` 外全字段的 sha256）与 `freshness`
（签发时的快照，读取时用 `check_freshness` 重算，不信任存量值）。

```jsonc
{
  "schema": "ui-agent-skills/verification-receipt/v1",
  "receipt_id": "rcp-1a2b3c4d5e6f7a8b",
  "run_id": "9f8e7d6c5b4a3210",
  "lane": "baseline",
  "issued_at": "2026-10-20T00:00:00+00:00",
  "claim": {
    "subject": "EV-v0.1 deterministic verification",
    "scope": {"dimensions": ["dom_aria", "..."], "classes": ["form", "..."], "viewports": ["390x844", "768x1024", "1440x900"]},
    "asserts": "cells 的 status 由 R-HAR-2 硬门禁对 observation bundle 判定",
    "not_asserts": ["不证明 fixture 数据本身正确", "不证明浏览器真实渲染", "不覆盖契约维度实测"]
  },
  "checks": [{
    "cell": "overflow/form", "dimension": "overflow", "class": "form", "gate": "A",
    "status": "FAIL",
    "oracle": ["pixel-calc"],
    "threshold": {"overflow_px": 0},
    "command": "python skills/ui/zj-ui-core/scripts/dual_lane_runner.py run --lane baseline --observations <DIR>",
    "coverage": {"planned_fixtures": 6, "fixtures_with_evidence": 6, "missing_fixtures": []},
    "observed": {"checked": 18, "bundles": 18, "fixtures_seen": 6, "missing_fixtures": [],
                 "findings": [{"code": "HG-OVF-01", "severity": "hard", "..." : "..."}]}
  }],
  "status": {"verdict": "FAIL", "raw_verdict": "FAIL",
             "counts": {"PASS": 15, "FAIL": 2, "...": 0},
             "coverage": {"planned_cells": 21, "passed_cells": 15, "attributable": 17,
                          "excluded": 4, "pass_rate": 0.8824, "unknown_statuses": []},
             "reason_codes": [], "quarantine": {"total": 0, "attributed": 0, "unattributable": 0}},
  "reviewer": {"name": "zj", "signed_at": "2026-10-20T00:00:00+00:00"},
  "expiry": {"ttl_days": 14, "expires_at": "2026-11-03T00:00:00+00:00"}
}
```

> `checks[].coverage.planned_fixtures` 在 lane receipt 未提供时为 `null`——**未提供不等于 0**，
> 收据不得据此声称"全覆盖"。

---

## 2. 聚合状态（四层）

```
finding（gate 内） → cell（dimension × class） → lane → receipt（多 lane 合并）
```

- **finding → cell**：由 R-HAR-2 完成（`FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED > WARNING > PASS`）。
- **cell → lane**：与 `dual_lane_runner._overall_status` **逐字同源**（`_verdict_from_statuses` 直接镜像，
  不另立一套口径）；唯一附加规则是**未知 status 一律降级 `HUMAN_REVIEW_REQUIRED`**——
  没见过的状态不能参与 PASS 的构成。
- **lane → receipt**：取最坏（`FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED > WARNING > BLOCKED/PARTIAL > PASS`）；
  每 lane 一张收据，不把 baseline 的 PASS 与 degraded 的 DEGRADED_SKIP 混算成一张"通过"。
- **更严偏移（合法）**：缺签 / 未钉 commit → `PASS` 降为 `HUMAN_REVIEW_REQUIRED`（记 `RCP-A-07/A-08`）；
  存在 quarantine → `QUARANTINED` 覆盖 PASS。两者都写进 `status.reason_codes`，不是静默改判。

### 2.1 计数与分母（必须可审计）

```jsonc
"counts": {"PASS": n, "WARNING": n, "QUARANTINED": n, "HUMAN_REVIEW_REQUIRED": n,
           "FAIL": n, "NOT_EXECUTED": n, "DEGRADED_SKIP": n}
```

| 概念 | 定义 |
| --- | --- |
| `planned_cells` | `len(checks)`（矩阵里适用的 cell 数） |
| `attributable` | `PASS + WARNING + FAIL + HUMAN_REVIEW_REQUIRED`（**进分母的只有真正跑过的**） |
| `excluded` | `QUARANTINED + NOT_EXECUTED + DEGRADED_SKIP`（不进分母，也不许变成 PASS） |
| `pass_rate` | `passed_cells / attributable`，**仅报告字段** |

**PASS 的判据不是通过率达标**，而是：`passed_cells == planned_cells` 且 `excluded == 0`
且每个 cell `checked > 0` 且 `bundles > 0`。通过率 0.9 的收据照样不通过——分母少了 10% 正是缺陷本身。

计数必须与 `checks` 逐项可对：`sum(counts) == planned_cells`、`attributable + excluded == planned_cells`。
任一不成立即 `RCP-A-04`（算术不可审计），收据失效。

---

## 3. stale 与 revalidation_required

`freshness` 是**读取时重算**的判定，不信任收据里存的值：

```jsonc
"freshness": {
  "status": "FRESH | STALE | REVALIDATION_REQUIRED",
  "changed": ["RCP-F-02"],
  "detail": {"RCP-F-02": ["fixture 漂移：['F-1']"]},
  "revalidate": {"required": true, "scope": "none|cells|all", "cells": ["overflow/form"],
                 "reason_codes": ["RCP-F-02"]}
}
```

| 状态 | 含义 | 触发 |
| --- | --- | --- |
| `FRESH` | hash 一致且未过期 | 无任何 F 码 |
| `STALE` | **可精确收敛到部分 cell** 的漂移 | fixture 内容/class 变化（`RCP-F-02`）→ 该 class 的 cell；阈值/oracle 变化（`RCP-F-03`）→ 消费该阈值的维度 cell |
| `REVALIDATION_REQUIRED` | 无法收敛或代价等同全量，或时间失效 | env 轴变化 `RCP-F-01`、维度集合/cell 门禁变化 `RCP-F-04`、过期 `RCP-F-05`、事实源不可读 `RCP-F-06`、schema 升版 `RCP-F-07` |

**影响面收敛规则**（`check_freshness`）：

| 变化 | 码 | 重跑范围 |
| --- | --- | --- |
| 任一 env 轴（font/network/clock/seed/node/config…） | `RCP-F-01` | 全部 cell |
| fixture 稳定字段（含 `landed_at`/`status`）逐 id sha 变化 | `RCP-F-02` | 该 fixture 所属 class 的 cell |
| 某维度消费的阈值 / oracle 变化 | `RCP-F-03` | 该维度的 cell |
| 维度集合、cell 门禁、`matrix_key` 无法归因的失配 | `RCP-F-04` | 全部 cell |
| `now > expiry.expires_at` | `RCP-F-05` | 全部 cell |
| 事实源缺失/不可解析 | `RCP-F-06` | 全部 cell |
| `schema` 升版 | `RCP-F-07` | 全部 cell |

- **过期不因 hash 未变而豁免**：TTL 默认 14 天，`expires_at` 可显式覆盖。
- `changed[]` 只记"变了什么"，`revalidate.cells` 记"要重跑什么"——两者都不是结论，
  重跑产生**新 run_id 的新收据**，旧收据保持原样（append-only）。
- 只读：`check_freshness` 不写盘、不重跑、不修改收据。
- CLI：`freshness <receipt.json>` 非 `FRESH` 退出码 1，可直接当 CI / 发版前的闸门。

---

## 4. 无法归因 quarantine

### 4.1 记录契约

```jsonc
{
  "code": "ADAPTER-FLAKY",           // 采集端/复核人给的分类
  "detail": "同一 bundle 两次渲染 diff 不一致",
  "fixture": "F-1",                   // 必须能映射到 manifest 里的 id
  "dimension": "overflow",            // 必须是矩阵维度
  "viewport": "390x844",              // 必须是必测 viewport
  "evidence": ["obs/F-1/390x844.json", "runs/run-123/trace.log"],
  "release_condition": "重跑 3 次结果稳定且人工确认",
  "raised_by": "adapter:storybook@8.x",
  "raised_at": "2026-10-20T00:00:00+00:00",
  "source": "adapter | gate-finding | reviewer",
  "resolution": null                  // 只允许 null / "REVALIDATED" / "ACCEPTED_RISK"
}
```

### 4.2 判定

- `quarantine` 段非空 → cell/lane verdict 为 `QUARANTINED`（`FAIL` 与 `HUMAN_REVIEW_REQUIRED` 优先）。
- **attributed**：fixture ∈ manifest、dimension ∈ 矩阵、viewport ∈ 必测集、`evidence` 与
  `release_condition` 均非空 → 可以定位到"哪一处、哪一维、哪一视口出了问题"。
- **unattributable**：上述任一缺失（`RCP-Q-01`）或没有证据/解除条件（`RCP-Q-02`）。
  **两类都判 `QUARANTINED`，分开计数**（`status.quarantine.attributed / unattributable`），
  不得把 unattributable 转成 `FAIL`（把"不知道"伪装成"已验证失败"）。
- `resolution` 只能是 `null / REVALIDATED / ACCEPTED_RISK`；写 `PASS` 或 `FAIL` 即 `RCP-Q-03`。
- 解除必须**新 run_id + 复核人签署**（`RCP-Q-04`）；原收据不改写，解除动作体现在新收据里。
- **Q-01/Q-02 是记录级审计码**：它们会让 `status.reason_codes` 出现，但不会让收据本身"结构非法"——
  一张如实记录"无法归因"的收据是合法收据。

---

## 5. 签发、不可变与落盘

| 规则 | 说明 |
| --- | --- |
| `PASS` 需复核人 | `reviewer.name` + `signed_at` 缺一 → `RCP-A-07`，build 直接降级 `HUMAN_REVIEW_REQUIRED` |
| `PASS` 需钉住 commit | 非 40 位 sha / `UNPINNED*` / `observed.worktree_dirty` → `RCP-A-08` |
| 不可变 | 同一 `receipt_id` 内容变化 → `RCP-V-07`；重出必须新 `run_id`（`receipt_id` 随之变化） |
| 落盘 | `<run_id>.json` 到 `docs/designs/ui-agent-skills/receipts/<lane>/`，append-only；本节点维持 print-only（不新增写盘副作用） |
| 派生字段 | `freshness` 永远读取时重算；存量值仅作历史快照 |

---

## 6. 审计码目录（28 条）

`severity`：`hard` → 收据失效；`evidence` → 收据有效但结论不可用于毕业；`quarantine` → 记录级审计。

| code | 类别 | severity | 断言 |
| --- | --- | --- | --- |
| RCP-V-01 | 结构 | hard | 缺必填段（身份段或 14 段之一） |
| RCP-V-02 | 结构 | hard | schema 不是可识别版本 |
| RCP-V-03 | 结构 | hard | `run_id` 缺失或 `receipt_id` 不合规 |
| RCP-V-04 | 结构 | hard | `checks` 为空（没有任何 cell 被判定） |
| RCP-V-05 | 结构 | hard | `claim.scope` / `command` / `commit` / `fixtures.entries` / `env_hash` 为空 |
| RCP-V-06 | 结构 | hard | artifact 缺 `path` 或 `sha256` |
| RCP-V-07 | 结构 | hard | 已签发收据被改写（同 `receipt_id` 内容变化） |
| RCP-V-08 | 结构 | hard | `lane` 非法（只允许 baseline / degraded） |
| RCP-A-01 | 聚合 | hard | `PASS` 但覆盖率不足（存在非 PASS / excluded cell） |
| RCP-A-02 | 聚合 | hard | `PASS` 但存在证据缺失或 quarantine |
| RCP-A-03 | 聚合 | hard | `verdict` 低于 cell 推出的结论（且无合法"更严偏移"理由） |
| RCP-A-04 | 聚合 | hard | `counts` / `status.quarantine` 与 `checks` 不一致（算术不可审计） |
| RCP-A-05 | 聚合 | hard | cell 判 `PASS` 但 `checked == 0`（空转假绿） |
| RCP-A-06 | 聚合 | hard | 通过率分母包含 `QUARANTINED / NOT_EXECUTED / DEGRADED_SKIP` |
| RCP-A-07 | 签发 | hard | `PASS` 缺复核人签署 |
| RCP-A-08 | 签发 | hard | `PASS` 但 commit 未钉住或工作树脏 |
| RCP-A-09 | 聚合 | hard | `PASS` 但 cell 没有任何 observation bundle（无证据通过） |
| RCP-F-01 | 过期 | evidence | env 轴变化（`env_hash` 失配）→ 全量重验 |
| RCP-F-02 | 过期 | evidence | fixture 稳定字段漂移 → 该 class 的 cell 重验 |
| RCP-F-03 | 过期 | evidence | 阈值 / oracle 漂移 → 该维度的 cell 重验 |
| RCP-F-04 | 过期 | evidence | 维度集合 / cell 门禁变化，或 `matrix_key` 失配无法归因 → 全量重验 |
| RCP-F-05 | 过期 | evidence | 收据过期（`now > expires_at`） |
| RCP-F-06 | 过期 | evidence | 事实源不可读 → 保守全量重验 |
| RCP-F-07 | 过期 | evidence | schema 升版 → 全量重出 |
| RCP-Q-01 | quarantine | quarantine | 记录无法映射到 fixture / dimension / viewport |
| RCP-Q-02 | quarantine | quarantine | 记录缺 evidence 或 release_condition |
| RCP-Q-03 | quarantine | quarantine | quarantine 被写成 `PASS` / `FAIL` |
| RCP-Q-04 | quarantine | quarantine | 解除未经新 run_id 或复核人签署 |

---

## 7. 自检证据

```bash
python skills/ui/zj-ui-core/scripts/verification_receipt.py selftest
# {"total": 34, "failed": 0, "ok": true}   exit 0；任一用例不匹配 -> exit 1
python -m unittest tests.test_ui_agent_skills_verification_receipt  # 该测试随原型脚本清理（2026-10-22），见治理报告
```

`selftest` 覆盖目录里全部 **28 条码**（无一条"写了没响过"），并额外锁三件事：

- `mirror/runner-verdict`：收据聚合与 R-HAR-1 的 `_overall_status` 在 8 组状态集上逐字一致——
  两个视图对同一事实不给两个答案。
- `build/degraded-receipt-valid` + `build/deterministic`：真实 runner receipt 能升格为合法收据，
  且同输入两次 build 逐字节相同。
- `positive/quarantine-attributed`：可归因记录不产生任何审计码（避免"quarantine 一律报错"的假阳性）。

写单测时抓到的真实缺陷（已修，非静默）：

1. `validate` 曾把 `PASS` 因缺签降级后的 `raw_verdict=PASS` 判成 `RCP-A-03`（自相矛盾）→
   显式允许两种"更严偏移"（A-07/A-08 降级、quarantine 提升）。
2. 首版把"记录级"的 `RCP-Q-01/Q-02` 塞进收据结构校验 → 一张如实记录"无法归因"的合法收据被判非法。
   现在它们只出现在 `status.reason_codes` 与 `validate_quarantine` 结果里。
3. 首版允许 `PASS` 且 `bundles == 0`（只校验 `checked > 0`）→ 新增 `RCP-A-09`。

> 自检用的 lane receipt 与 observation 是**合成夹具**，只证明判定语义，**不构成验收证据**。

---

## 8. 上下游契约义务

- **向上**：消费 1-5-1 的矩阵/指纹、1-5-2 的 lane receipt、1-5-3 的 cell status 与 findings；
  不重算门禁、不改写 cell 结论。
- **向下（1-6）**：`zj-ui-verify` / `zj-ui-handoff` 的 receipt 产物必须是本 schema；
  contract 维度 cell 在 engine 就绪后按同一 `checks` 结构填入。
- **向下（1-9）**：paired run 每次必须带 `env_hash` 一致的收据；`FAIL` / `QUARANTINED` /
  `HUMAN_REVIEW_REQUIRED` 不得进毕业分母；无收据 = 无效 run。
- **向下（1-10）**：rollout / pilot / kill-switch 决策引用收据的 `freshness.status` 与
  `revalidate.cells`，不得凭"曾经通过"放行过期结论。

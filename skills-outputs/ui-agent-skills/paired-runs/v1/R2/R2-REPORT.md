# R2 报告（契约层 · 第 2 次 paired run）

- **节点**：1-9-3（第 2/3 次 paired run；R2 已完成，R3 待跑）
- **配对轴**：`direct-prompt` vs `skills-path`（同一裸需求、同一 12 fixtures、同一 config_hash）
- **裸需求**：与 R1 **逐字节相同**（sha256 校验通过，同 case 不变量成立）
- **counterbalance**：R1 是 h3=skills / h4=direct，**R2 反序**（seed 2026102102）
- **config_hash**：`3235655e…f61791`（未变；model `Deepseek-V4.1-Flash`，skills_commit `ce75cb3`）

| hid | lane |
| --- | --- |
| h5 | **direct-prompt** |
| h6 | **skills-path** |

---

## 1. 结果

| 指标（host 实测优先） | h5 direct-prompt | h6 skills-path | 差 |
| --- | --- | --- | --- |
| fixtures 通过 | 12/12 | 12/12 | 平 |
| escaped defect（critical/high/medium/low） | **1** / 6 / 4 / 2 = 13 | **0** / 2 / 6 / 3 = 11 | 总数 +18%，加权 +100% |
| 加权缺陷（4/2/1） | 20 | 10 | −50% |
| 返工：日志中 `rework` 事件 | 1 | 14 | −93% |
| 返工：驱动失败次数（`driver-runs.jsonl`） | 1 | 2 | — |
| 墙钟 **host 实测**（日志首末 ts） | **1.67 min** | **27.15 min** | −94% |
| 墙钟 operator 自报 | 13 min | 18 min | −28% |
| 工具调用（自报 / host 审计步数） | 22 / 19 | 46 / 35 | −52% |
| 产物字节 | 41,039 | 61,393 | −33% |
| 观察员取证（executed / static） | 12 / 1 | 6 / 5 | **R-BAL 达标** |
| S1 审批动作可达性 | pass | pass | 平 |

**R-BAL 判定：`confounded = false`**（两 lane 都有 executed，且都不为 0）→ 本轮的 escaped defect 计数**可以**做跨 lane 比较，这是 R1 没做到的。

## 2. R1 遗留的三个缺口，本轮闭合了两个

| 缺口 | R1 状态 | R2 状态 |
| --- | --- | --- |
| **DEV-3 / R-BAL**（观察员取证不对称） | confounded，缺陷数不可用 | **闭合**：规程强制 12 项清单 + 必须执行；h5 12 executed / h6 6 executed |
| **BLK-4**（返工只能自记） | 事后不可反推 | **闭合**：新增 append-only `driver-runs.jsonl`，host 可独立数驱动失败次数 |
| BLK-2（token 预算不可测） | 空文 | 仍未闭合（需改 harness，出 Acceptance scope） |
| BLK-3（渲染层未实测） | 静态推导 | 仍未闭合（h5 观察员用自制 DOM 桩做了部分执行，属观察员自备手段，非 harness 能力） |

## 3. 主控抽查：2 条都成立

| 缺陷 | 抽查证据 | 结论 |
| --- | --- | --- |
| h5 D1 **critical**：idle 态直接提交 → 永久死锁 | `machine.mjs` 的 `TRANSITIONS: idle -> ['validating']`，idle→submitting 非法；但 `submit()` 丢弃 `go()` 返回值后照常 `locked=true` 并 `return ok:true`；`persist()` 首行 `if (state!=='submitting') return` 提前返回，而 `locked=false` 在其后 → **永不解锁** | **verified** |
| h6 S9 **high**：驳回理由不展示给申请人 | `app.mjs:174` 确有独立 `#decision-reason` 输入（S9 前半通过），但 `render()` 的 history 只输出 `v${version} · ${status}`（:130-133），banner 只写"原因已记录"却不显示内容 | **verified** |

审计记录：`observer/defect-audit.json`（2 audited / 2 verified）。

## 4. 必须挑明：R2 引入了**中途指令变更**（DEV-4）

我在 R2 的 operator 指令里加了两句 R1 没有的要求：

1. 「每个状态迁移都必须能从 UI 触发」（因为 R1 抓到了 h4 的 route 断链）
2. 「每次驱动执行都要往 `driver-runs.jsonl` 追加一行」（BLK-4 修复）

**后果**：

- **run 内比较仍然有效**——两条 lane 拿到的是同一份指令，所以 h5 vs h6 的对比没有被污染。
- **run 间合并失效**——R1 测的是"没人提醒时谁会想到"，R2 测的是"提醒之后谁能做到"。**S1 这个指标在 R1 与 R2 之间不可合并**。事实也印证了：R1 是 skills pass / direct fail，R2 是两 lane 都 pass（提醒之后 direct 也做到了）。
- 按 `ev-metrics §5`「范围变更 → 旧 run 作废」的严格读法，**R1 应视为探索性 run，毕业序列应从 R2 起算**（即需要 R3、R4 才够三次）。

我不打算悄悄把 R1+R2 合并成"两次 run"来凑数。所以：**R2 是毕业序列的第 1 次（若按严格读法），R1 降级为机制验证/探索。**

## 5. 新发现：operator 自报的墙钟与返工都不可信

`R2-C9` 对比 host 实测与自报，两条 lane **都偏，而且方向相反**：

| lane | host 实测（日志首末 ts） | operator 自报 | 差 |
| --- | --- | --- | --- |
| h5 | 1.67 min | 13 min | **−11.3 min**（自报虚高） |
| h6 | 27.15 min | 18 min | **+9.15 min**（自报虚低） |

返工同理：h6 自报 9 次，日志里实际 14 次 `rework` 事件；驱动失败 2 次。三个数互不相等，测的不是同一件事。

**结论**：`run_meta` 里的 `wallclock_minutes` / `tool_calls` 只能当参考，**graduation 指标必须用 host 实测**（日志跨度 + 审计步数 + driver-runs）。这条要写进 R3 规程。

## 6. R2 证明了什么 / 没证明什么

**证明了**：

1. 工具链第二次跑仍然可用：两 lane 都在 60 次调用、45 分钟内交付 12/12。
2. **观察员规程（DEV-3）与 driver-runs（BLK-4）两条修复都真的生效**——R-BAL 从 confounded 变 pass，返工有了独立口径。这是本轮最大的进展。
3. 反硬编码仍然有效：三个变异体（F-5 / F-6 / A-6）两 lane 全跟随。
4. 产物写入全部被 `file=` 记录（新的覆盖断言，两条 lane 都过）。

**没证明**：

- **技能链更好或更差**。R2 显示 skills-path 严重缺陷更少（加权 10 vs 20），但耗时 16 倍（27 vs 1.7 min）、返工 14 倍；R1 显示 skills-path 略快（3.67 vs 4.02）且缺陷更少。**两轮方向不一致，n=2 不能下结论。**
- 盲性仍未证实：R2 两 lane 都被猜成 `structured`（h5 实际是 direct，**猜错**）；累计 4 次探针 3 次命中，仍不足以支撑"双盲"表述。

## 7. 复现

```bash
cd skills-outputs/ui-agent-skills/paired-runs/v1/R2
PY=/Users/bilibili/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY _tools/r2_check.py        > _tools/r2-check-report.json
$PY _tools/metrics_r2.py                                  # RUN-METRICS.json
$PY _tools/build_receipt_r2.py                            # RUN-RECEIPT.json
```

## 8. 产物清单

```
R2/
├── RUN-RECEIPT.json               收据（paired-run-receipt/v1, canonical=false）
├── RUN-METRICS.json               指标（含独立返工口径 + 清单汇总）
├── R2-REPORT.md                   本文件
├── raw-requirement.md             与 R1 逐字节相同（sha256 已校验）
├── _sealed/lanemap.json           h5=direct-prompt / h6=skills-path
├── _tools/{r2_check,metrics_r2,build_receipt_r2}.py
├── _tools/r2-check-report.json
├── h5/{artifact,events.jsonl,driver-runs.jsonl,run_meta.json}   direct-prompt
├── h6/{artifact,briefs,events.jsonl,driver-runs.jsonl,run_meta.json}  skills-path
└── observer/{defects-h5.json,defects-h6.json,defect-audit.json}
```

## 9. 进 R3 的前提（保持指令冻结）

R3 必须**逐字复用 R2 的 operator 指令**（含可达性要求 + driver-runs），否则又是一次中途变更，三次 run 全部作废。除此之外：

1. **指标口径统一为 host 实测**（日志跨度 + 审计步数 + driver-runs），自报值只作备注。
2. R3 用新 seed 再随机一次 hid（保持 counterbalance）。
3. BLK-2 / BLK-3 仍未闭合，R3 不会闭合它们——它们需要改 `research/ui-agent-skills/` 的 harness（出 Acceptance scope，待立项）。

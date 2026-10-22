# R3 报告（契约层 · 第 3 次 paired run）

- **节点**：1-9-3（第 2/3 次；R3 为第 3 次）
- **指令**：**逐字复用 R2**（只换 hid / 路径 / operator_id）—— 满足 DEV-4 的冻结要求
- **裸需求**：与 R1、R2 **逐字节相同**（sha256 一致）
- **配对**：seed 2026102201 → **h7 = direct-prompt / h8 = skills-path**
- **config_hash**：`3235655e…f61791`（三轮未变）

| 指标（host 实测优先） | h7 direct-prompt | h8 skills-path |
| --- | --- | --- |
| fixtures 通过 | 12/12 | 12/12 |
| escaped defect（c/h/m/l） | 0 / 5 / 7 / 1 = 13 | 0 / 3 / 5 / 4 = 12 |
| 加权缺陷（4/2/1） | 17 | 11 |
| 返工：日志 `rework` | 1 | 2 |
| 返工：驱动失败次数 | 0 | 1 |
| 墙钟 host 实测 | 8.68 min | 24.62 min |
| 墙钟自报 | 8 min | 24 min（**本轮自报准确**） |
| 审计步数 / 事件数 | 44 / 60 | 46 / 66 |
| 观察员 executed / static | 10 / 3 | 8 / 4 |
| S1 审批动作可达性 | pass | pass |

**R-BAL：not confounded**（两条 lane 都有 executed）。

## 1. 抽查：两条 lane 都栽在同一类问题上

| 缺陷 | 证据 | 结论 |
| --- | --- | --- |
| h7 high「422 后静默回滚，丢弃未保存输入」 | `src/form/machine.mjs:126` 失败分支执行 `this.profile = {...this.stableDraft}`，把已编辑内容重置回上次保存值；紧接着的 `recover()` 注释却写着"保留用户输入" | **verified** |
| h8 high「第二次保存被静默丢弃却报成功」 | `src/core.mjs:64` 的 `commit()` 在内容变化时返回 `{written:false, reason:'revision_conflict'}`；但 `machine.mjs` 的 ok 分支**不检查 `result.written`** 就 `setState(SUCCESS)` 并 `emit('saved')` | **verified** |

值得单独说：**两条 lane 都出现了"静默数据丢失 / 伪成功"类 high**，而需求里明确写了"超时不能让用户以为保存成功"。这说明该类缺陷**不是技能链能消除的**，属于需要独立门禁（verification gate）卡住的类别——这是给技能链本身的反馈。

## 2. 本轮的方法修正：S1 gate 第 4 次改判据

判据演化（同一个坑反复踩，记录在此以免第 5 次）：

| 版本 | 判据 | 漏掉/误判 |
| --- | --- | --- |
| v1 | HTML 里出现 `route(` | R2 h6（`id="route-btn"`）假阴性 |
| v2 | 动作名从 fixture 派生 + id **前缀**匹配 | R3 h8（`a-route`）假阴性 |
| v3 | id/name **子串** + 按钮文案 | R1 h3（submit 成功后自动 `app.route()`）假阴性 |
| **v4** | 控件证据 **或** **视图层调用证据**（自动带出也算可达） | — |

v4 的判据回到定义本身：**可达性 = 用户操作能触发该迁移**，不是"有个以动作命名的按钮"。

用 v4 统一重测三轮（同一把尺子）：

| run | direct lane | skills lane |
| --- | --- | --- |
| R1 | h4 **fail**（route 全程 0 引用） | h3 pass（自动 `app.route()`） |
| R2 | h5 pass | h6 pass |
| R3 | h7 pass | h8 pass |

**唯一真断链仍是 R1 的 direct lane**——R2/R3 因为指令里明确要求了可达性，两条 lane 都补上了（DEV-4 的直接后果）。

另外修了一处误报：h7 原样回显整个 `expected.json`（含 `fixture_id` / `assertions`）被我的比对判成"篡改"。元键不该参与语义比较，已剔除，h7 洗清。

## 3. R3 自身的一条协议冲突（我造成的）

h8 自报 tool calls **66 > 60 预算**，并说明原因：我要求"每个 fixture 至少 start→validate→complete 三行"（12×3 = 36 行），加上构建期事件，60 次预算几乎必然被顶穿。

- host 实测的**审计步数**是 46（未超 60），所以按 host 口径不违规；
- 但这暴露了协议内部矛盾：**日志粒度要求与预算上限互相挤压**。R4 前要二选一：要么放宽预算到 80，要么把逐 fixture 的强制三行降为强制两行（start / complete）。我倾向后者——三行里的 `validate` 对指标没有贡献。

## 4. 复现

```bash
cd skills-outputs/ui-agent-skills/paired-runs/v1
PY=/Users/bilibili/.workbuddy/binaries/python/versions/3.13.12/bin/python3
(cd R3 && $PY _tools/r3_check.py > _tools/r3-check-report.json
        && $PY _tools/metrics_r3.py && $PY _tools/build_receipt_r3.py)
$PY /tmp/cross_run.py     # 三轮汇总 -> CROSS-RUN-TABLE.json
```

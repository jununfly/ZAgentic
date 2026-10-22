# R1 报告（契约层 · 第 1 次 paired run）

- **节点**：1-9-2（第 1 次 paired run：两条可比日志、receipt、review、指标）
- **运行时间**：2026-10-21 22:10–22:40（+08）
- **配对轴**：`direct-prompt` vs `skills-path`（同一裸需求、同一 12 fixtures、同一 config_hash）
- **样本**：form `F-1..F-6` + approval `A-1..A-6`（12/12，双样例齐全）
- **config_hash**：`3235655e…f61791`（两条 lane 相同；model `Deepseek-V4.1-Flash`，skills_commit `ce75cb3`）
- **解盲**：`_sealed/lanemap.json`（评审期间 Observer 不可见；本报告为解盲后交叉比对）

| hid | lane |
| --- | --- |
| h3 | **skills-path**（zj-ui 全链路） |
| h4 | **direct-prompt**（裸需求直写） |

---

## 1. 契约层结果：两条 lane 都 12/12

| 指标 | h3 skills-path | h4 direct-prompt | 差 |
| --- | --- | --- | --- |
| fixtures 通过 | 12/12 | 12/12 | 平 |
| 返工次数（自记） | 0 | 4（0.33/条） | −100% |
| 墙钟（run_meta 自报 / 日志跨度） | 3.5 min / 3.67 min | 4.0 min / 4.02 min | −12.5% |
| 工具调用（自报 / 宿主审计步数） | 59 / 57 | 60 / 56 | −1.7% |
| 产物字节 | 55,967 | 49,887 | +12% |
| escaped defect（critical/high/medium/low）※ | **0** / 5 / 8 / 5 = 18 | **4** / 6 / 5 / 2 = 17 | 总数 +6%，加权 −45% |

※ 该行 **confounded**（`R-BAL`：h3 0 executed vs h4 10 executed），只能用于"发现问题"，**不得用于毕业判定**。可用的机械差异见 §2.5 `R1-C7`。
| 盲性探针 | structured / low | direct / medium | 弱区分 |

**加权缺陷**（critical×4 + high×2 + medium×1）：h3 = 18，h4 = 33。

契约层结论只有一句：**两 lane 在"被 fixture 卡住的部分"打平**。差别全在 fixture 卡不住的地方（见 §2）。

## 2. escaped defect：h4 的 4 个 critical 我逐条抽查过

不只信 Observer 报告，主控抽查了 3 条（pilot 教训：Observer 会幻觉）：

| 缺陷 | 抽查方式 | 结论 |
| --- | --- | --- |
| h4 D3「报销提交后永久卡在 `submitted`，审批/驳回不可达」 | `grep -r under_review h4/artifact` + 机械 gate | **成立**。`approval.html` 全文无任何地方触发 `route` 动作；fixtures 把 `initial_state` 直接置 `under_review` 绕过了这条断链 |
| h4 D4「驳回理由偷用申请人的"事由"字段」 | 查 `approval.html` 全部 `id=` | **成立**。只有一个 `#reason`（申请人「事由」），没有独立的驳回理由输入；`reject` 却把 `els.reason.value` 当理由 |
| h3 D1「保存成功后表单永久锁死 + recover 恒隐藏」 | 查 `form.html:172` 极性 | **夸大**。`hidden = state !== 'error'` → 错误态**可见**，Observer 把极性读反；残留的"success 态无出路"成立但应降为 medium |

审计记录：`observer/defect-audit.json`（3 条抽查：2 verified / 1 overstated / 0 refuted）。**两条 critical 都成立** → Observer 不是幻觉；但 h3 自己也有 1 条 high 需下调，两边都不精确。

## 2.5 把"状态可达性"做成机械 gate（R1 的主要方法产出）

上面 h4 D3 是 Observer 的**意见**。为了不让它停在意见层面，我把它机械化成了 `R1-C7`：

> 状态机定义了动作 X，但视图层从未调用 X ⇒ 用户在 UI 上走不到该状态。

对需求明写的两条 transition 检查（不臆造）：

| gate | h3 skills-path | h4 direct-prompt |
| --- | --- | --- |
| S1 `approval.route`（"提交后进入审批中"） | **pass**（`approval.html:310 if (result.ok) app.route();`） | **fail**（0 处调用） |
| S6 form 恢复控件 | present（`hidden = state !== 'error'` → 错误态可见） | present（未捕获到 gating 表达式，待 R2 补） |

这条 gate 的价值：**它不依赖观察员取证深度**。所以 R1 的缺陷**总数**差值虽然 confounded（见 §3），但 S1 这一类的差异是**真的**——h3 在这条上确实通过，h4 确实断链。

这就是 paired run 想抓的东西：**单元测试/state-machine 测试全绿，但用户走不通**。h4 的 D3 更是典型——fixture 用 `initial_state` 直接注入状态，把"怎么走到这个状态"整段跳过，于是断链在契约层完全隐形。

## 3. 诚实声明：R1 目前**不能**当毕业证据

| 编号 | 问题 | 后果 |
| --- | --- | --- |
| **DEV-3 / R-BAL** | 两个 Observer 取证深度不对称（h3：0 executed / 18 static；h4：10 executed / 7 static）。按 `observer-protocol §3` 的配平规则 `R-BAL`（一 lane ≥3 executed 而另一 <1）→ **判定 confounded** | escaped defect 的**总数/加权差值不得用于 graduation**；只有机械 gate（`R1-C7`）的差异可用 |
| **BLK-2** | 冻结的 token 预算（≤80k）**无法审计**：host 无计量 | 预算护栏目前是空文 |
| **BLK-3** | 无浏览器引擎（Chrome 被沙箱拒） | 渲染/键盘可达性缺陷只能静态推导，视觉与真机交互未测 |
| **BLK-4** | `rework` 由 operator 自记，且**事后不可反推**：R1 实测两条 lane 的产物 mtime 都单向递增、无重写痕迹 | 返工率只能当自报值；R2 起需 append-only `driver-runs.jsonl` |
| — | h3 日志 4 行 `fixture`/`event` 字段对调（含结尾 `complete` 行） | 机械完整性仍 PASS（seq/ts/append-only 都对），但按 ev-metrics §4 **不重写日志**，原样留存 |
| — | h3 自身有 1 条 high 被抽查判为夸大（极性读反） | h3 的 high 计数 5→4；两条 lane 的缺陷计数都不精确 |

另外 **n=1**。ev-metrics §1 明写"不能用一次 baseline 支撑三个 Experience 版本，三次 run 必须各自内含 baseline 与 Experience"。R1 只是第一次。

所以本轮的定位：**机制可用性已被证明，方向性信号存在，结论待 R2/R3。**

## 3.5 仪器自己踩了 5 个坑（比 operator 的问题更该先说）

判别人的仪器，必须先自证。本轮（含 pilot）5 个坑全部会造成假绿或假红：

| # | 坑 | 症状 | 修法 |
| --- | --- | --- | --- |
| I-1 | 相对路径少算一层 | 两 lane 同时 ENOENT，像两个 operator 都没交付 | `_find_repo()` 逐级向上找 `.git` |
| I-2 | 泄漏扫描误报领域词 | CSS `align-items: baseline` 被判 lane 泄漏 | 只匹配与比较轴连用的 token；误报进 `suppressed_hits` |
| I-3 | 只匹配控件 id 就算"有恢复路径" | `#recover` 存在但 `hidden` 恒真 → 假 pass | 存在性给 `present`，把 `gating_expression` 摘出来交人判极性 |
| I-4 | **变异探针在产物目录内跑** | 驱动覆盖 `.run-fixtures-result.json`，汇总把 12/12 读成 **fail** | 变异一律在 **artifact 副本**里跑 |
| I-5 | `checked == 0` 判 PASS | artifact 为空时扫 0 个文件仍判 `clean` | 先断言 `checked > 0`，否则 `not_checked` |

I-4 是最危险的那个：它让"证据被自己的检查步骤改写"。已固化进 `observer-protocol §7` 仪器自检清单。

## 4. 已经站得住的几条（可以写进结论的部分）
1. **工具链可用**：两 lane 都在 4 分钟内、60 次工具调用内交付 12/12；宿主审计覆盖率 96%+（unaudited ≤ 7%）。
2. **反硬编码有效**：三个行为级变异体（F-5 422→200、F-6 超时→200、A-6 解除自审批）被**两条 lane 全部跟随**——说明 12/12 是真跑出来的，不是把 expected 抄进产物。这一条顺带洗清了 h3 的 `stable_path` 嫌疑：F-6 变异后它的 `fallback` 正常消失，属于错误分支的领域常量，不是无脑输出。
3. **日志纯度达标**：两条 lane 的 `events.jsonl` 都 append-only、seq 连续、ts 单调且由 `date -u` 真采。
4. **盲性只做到"机械隔离"**：产物零 lane 标注泄漏，但探针区分力弱（h3 被猜 structured/low 是猜对了，h4 猜 direct/medium 也猜对了，两个都 low–medium 置信）。**不能声称双盲已验证**。
5. **一条机械化的真差异（`R1-C7`）**：`approval.route` 可达性，h3 pass / h4 fail。这条不经过 Observer 判断，所以不受 R-BAL 影响。这是 R1 唯一可以拿去做"技能链 vs 裸写"方向性推断的证据点——但它只有 1 条 gate、1 个 run。
6. **"fixture 全绿 ≠ 用户能走通"已被实证**：h4 12/12 通过，同时三条主流程断链（审批卡死、驳回无理由输入、放弃修改覆盖已存值）。这是本次 paired run 给技能链本身的最有价值反馈——verification 层需要补"状态可达性"检查，否则契约层永远是绿灯。

## 5. 复现

```bash
cd skills-outputs/ui-agent-skills/paired-runs/v1/R1
PY=/Users/bilibili/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY _tools/r1_check.py        > _tools/r1-check-report.json   # 日志/契约/泄漏/反硬编码
$PY _tools/metrics_r1.py                                      # RUN-METRICS.json
$PY _tools/build_receipt_r1.py                                # RUN-RECEIPT.json
```

驱动单跑（以 h3 为例）：

```bash
N=/Users/bilibili/.workbuddy/binaries/node/versions/22.22.2-6/bin/node
cd h3/artifact && $N run-fixtures.mjs <repo>/tests/ui-agent-skills/fixtures
```

## 6. receipt 的边界（别误读）

`RUN-RECEIPT.json` 是 **paired-run-receipt/v1**，`canonical_receipt: false`。

它**不是** 1-5-4 的 R-RCP-1 verification receipt。后者必须由 `verification_receipt.py:build_receipt` 从 `dual_lane_runner` 的 lane receipt 升格，绑定 adapter 轴 + manifest/env hash。1-9 走 operator 轴且无浏览器，硬套会往收据里塞不可归因字段——那是假 provenance。要用 R-RCP-1，得先做 1-9 之外的 adapter 轴运行。

## 7. 进 R2 前必须先闭环（建议顺序）

| # | 事项 | 归谁 | 不动产品代码？ | R1 实测状态 |
| --- | --- | --- | --- | --- |
| 1 | **观察员取证规程统一**：两 Observer 执行同一套 12 项静态清单 + 证据配平规则 `R-BAL` | 主控 | ✅ 只改 runbook | **已落** `docs/plans/ui-agent-skills-paired-run-observer-protocol.md` |
| 2 | **token 计量**：宿主侧截获每次 LLM 调用的 usage 并写入 `budget.json` | 主控 | ⚠️ 改 harness（出 Acceptance scope → 需立项） | 未动 |
| 3 | **渲染层**：接 Chromium 155 或退一步用 DOM 断言把"渲染层未测"降级为"部分测到" | 需 zj 决策 | ⚠️ 同上 | 未动 |
| 4 | **rework 独立复核** | 主控 | ✅ | **R1 试过，判定不可行**：mtime 只保留最后一次写，h3/h4 的 9/11 个产物都是单向递增、无重写痕迹，无法从产物反推返工。要独立复核必须在 R2 加 **append-only `driver-runs.jsonl`**（每次驱动退出码 + 失败断言留痕） |

## 8. 产物清单

```
R/
├── RUN-RECEIPT.json               收据（非规范，口子写清）
├── RUN-METRICS.json               指标（含 unmeasurable 明细）
├── R1-REPORT.md                   本文件
├── raw-requirement.md             两 lane 逐字节相同的裸需求
├── _sealed/lanemap.json           hid→lane 映射（评审期封存）
├── _tools/r1_check.py             校验器（日志/契约/泄漏/变异/可达性/预算）
├── _tools/r1-check-report.json    校验器输出
├── _tools/metrics_r1.py           指标汇总
├── _tools/build_receipt_r1.py     收据生成
├── h3/{artifact,events.jsonl,run_meta.json}   skills-path
├── h4/{artifact,events.jsonl,run_meta.json}   direct-prompt
└── observer/
    ├── defects-h3.json            盲评（skills-path）
    ├── defects-h4.json            盲评（direct-prompt）
    └── defect-audit.json          主控抽查审计（2 verified / 1 overstated）
```

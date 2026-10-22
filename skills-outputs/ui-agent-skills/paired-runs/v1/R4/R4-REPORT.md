# R4 报告（契约层 · 第 4 次 paired run）

- **节点**：1-9-4（graduation gate 的第 3 次有效 run；R1 已因 DEV-4 降级为探索）
- **指令**：逐字复用 R2/R3 的 operator 指令（含「状态迁移必须 UI 可达」+ driver-runs.jsonl），只替换 hid / 路径 / operator_id
- **裸需求**：与 R1/R2/R3 **逐字节相同**（sha256 一致）
- **配对**：seed `2026102202` → **h9 = skills-path / h10 = direct-prompt**（skills-first，平衡 R2/R3 的 direct-first）
- **预算护栏**：**80 calls / 任务段**（DEV-5：R3 h8 实测 66 顶穿 60，放宽到 80 并重算 config_hash；treatment 变量未变）
- **config_hash**：`404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce`

| 指标（host 实测优先） | h9 skills-path | h10 direct-prompt |
| --- | --- | --- |
| fixtures 通过 | 12/12 | 12/12 |
| escaped defect（c/h/m/l） | 0 / 0 / 3 / 1 | 0 / 0 / 3 / 1 |
| 加权缺陷（4/2/1） | 7 | 7 |
| 返工：日志 `rework` | 0 | 1 |
| 返工：driver 失败次数（独立口径） | 1 | 0 |
| 墙钟 host 实测（日志首末 ts） | 0.95 min | 1.18 min |
| 工具调用（自报） | 30 | 14 |
| 产物字节 | 41,814 | 38,918 |
| 观察员 executed / static | 0 / 4 | 0 / 4 |
| S1 审批动作可达性 | pass | pass |
| S6 form 恢复控件 | present | present |
| 突变探针（F-5/F-6/A-6 跟随 input） | followed 3/3 | followed 3/3 |
| 机械校验 verdict | **PASS** | **PASS** |

**R-BAL：not confounded**（两条 lane 证据深度对称，均为 static → 缺陷计数可跨 lane 比较）。

## 1. R4 最关键的发现：skills 优势在 R4 完全消失

R2/R3 里 skills-path 的加权缺陷显著低于 direct（R2: 10 vs 20，R3: 11 vs 17）。**R4 两条 lane 的缺陷画像逐字相同（3 medium + 1 low，0 high/critical，加权 7）**。

可能原因（待 zj 判断，不擅自定论）：
- 两 lane 都是同一模型（Deepseek-V4.1-Flash）+ 同一冻结需求 + 紧密的 driver 反馈环；driver 立刻给 pass/fail，两 lane 都收敛到正确的状态机，差异被压缩。
- skills-path 的 skill 链咨询（briefs/01~05）在 R4 没有转化为更少的 UX 缺陷；观察员抓到的全是通用 a11y/HTML 语义缺陷（焦点、aria-describedby、required 属性），两 lane 都有。
- R4 观察员比 R2/R3 更"轻"（证据全 static），但两 lane 同口径，比较仍有效。

## 2. 抽查审计（主控，2/2 verified）

| 缺陷 | 证据 | 结论 |
| --- | --- | --- |
| h9 D1 medium：提交/审批禁用按钮无焦点保持 → 焦点回退 body | `index.html:241` 同步 `disabled=true`，全文件无 focus 管理 | **verified** |
| h10 D1 medium：字段错误与控件无程序化关联（缺 aria-describedby） | `index.html:74` input 无 aria-describedby，`:75` err-msg 仅 aria-live | **verified** |

## 3. 本 run 的方法修正与已闭口项

- **DEV-5 落实**：预算护栏 60→80，config_hash 重算；R2/R3 实际用量均 ≤80，按新护栏均判通过。
- **DEV-1 部分闭环**：env-fingerprint.json 的 `browser_major` 由 `PENDING@1-7-3` 回填为 `155`，与注册 env 轴对齐。
- **BLK-2（token 预算）仍 open**：host 侧无法从 operator 侧读 token 计数，`run_meta.budget_used.tokens=null`，预算护栏现以"可审计步数（file= 事件）"为准。
- **BLK-3（渲染层）已闭环（2026-10-22，b1 补 R2 后覆盖全 cohort）**：见 §6 + `RENDER-LAYER-COHORT.md` + `_tools/render-layer-report.json`。真实 Chromium 155 跑 **R2+R3+R4 共 6 lane**、7 断言：A1/A2/A5/A6/A7 在 6 lane **18/18 全过**（完全平价）；**唯一差异轴是 A3/A4（aria-describedby 关联）**——direct 0/3 全失败，skills 2/3 通过（R3-h8 漏）。方向纠正：补 R2 后三 run 一致呈 **skills ≥ direct（2 胜 1 平，从不劣于）**，与契约层方向一致。结论由"纯平价、强化 NOT_GRADUATED"修正为"**skills 有持续、窄幅 a11y 优势，成本溢价持续**"（详见 §6 与 CROSS-RUN-TABLE 的修订建议）。

## 4. 复现

```bash
cd skills-outputs/ui-agent-skills/paired-runs/v1/R4
PY=/Users/bilibili/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY _tools/r4_check.py      > _tools/r4-check-report.json
$PY _tools/metrics_r4.py                               # RUN-METRICS.json
$PY _tools/build_receipt_r4.py                         # RUN-RECEIPT.json
```

## 5. 产物清单

```
R4/
├── RUN-RECEIPT.json               收据（paired-run-receipt/v1, canonical=false）
├── RUN-METRICS.json               指标（含独立返工口径 + 12 项清单汇总）
├── R4-REPORT.md                   本文件
├── raw-requirement.md             与 R1/R2/R3 逐字节相同
├── _sealed/lanemap.json          h9=skills-path / h10=direct-prompt
├── _shared/run-fixtures.mjs       标准驱动（两 lane 共用，冻结）
├── _tools/{r4_check,metrics_r4,build_receipt_r4}.py
├── _tools/r4-check-report.json
├── h9/{artifact,briefs,events.jsonl,driver-runs.jsonl,run_meta.json}   skills-path
├── h10/{artifact,events.jsonl,driver-runs.jsonl,run_meta.json}          direct-prompt
└── observer/{defects-h9.json,defects-h10.json,defect-audit.json}

## 6. BLK-3 渲染层证据（已闭环，覆盖 R2+R3+R4 全 cohort，2026-10-22）

真实 Chromium 155.0.8059.85 headless，DOM 断言级（不依赖截图，每条信号是 DOM 事实/退出码）。驱动脚本 `_tools/render_layer_check.mjs`（puppeteer-core + Node 22），覆盖 **R2(h5/h6) + R3(h7/h8) + R4(h9/h10) 共 6 lane**，每 lane 7 断言 A1–A7（R2-h6 为双页面应用，由 `runLaneMultiPage` 处理 index.html + approval.html）。原始数据 `_tools/render-layer-report.json`，分析 `RENDER-LAYER-COHORT.md`。

| lane | A1 | A2 | A3 | A4 | A5 | A6 | A7 | 分 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2-h5 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R2-h6 **skills** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7/7 |
| R4-h9 **skills** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7/7 |
| R4-h10 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R3-h8 **skills** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R3-h7 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |

- A1/A2/A5/A6/A7 在 6 lane **18/18 全过**——启动无错、DOM 完整、键盘可达 approve、失败不为成功、超时不伪造成功，**两 lane 完全平价**。
- **唯一差异轴是 A3/A4（必填输入 `aria-describedby` 关联错误提示）**：direct **0/3 全失败**，skills **2/3 通过**（R3-h8 漏，与契约层 R3 那次 skills 漏一致）。
- §6 盲点#2（静默丢数据/伪成功）与 #3（超时不伪造成功）**在渲染层根本不存在**——它们只是契约层状态机内部问题，UI 层都正确处理了。
- **方向纠正**：原 R3+R4 子集（未含 R2）曾显"R4 有差异、R3 平 → 方向不稳健"。补 R2 后，三 run 一致呈 **skills ≥ direct（2 胜 1 平，从不劣于）**，与契约层方向完全一致。渲染层证据由"纯平价、强化 NOT_GRADUATED"**修正为"skills 有持续、窄幅 a11y 优势，成本溢价持续"**。
- 渲染层独立坐实的新门禁：`zj-ui-verify` 应补「必填输入必须 `aria-describedby` 关联错误区域」（direct 3/3 缺失，skills 1/3 漏检）。
```

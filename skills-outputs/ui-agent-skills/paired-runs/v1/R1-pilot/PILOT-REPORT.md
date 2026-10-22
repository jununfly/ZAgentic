# 1-9 R1 Pilot 报告（机制验证）

> 节点：1-9-2 前置 pilot（依 `docs/plans/ui-agent-skills-paired-run-roles.md` §6）
> 执行时间：2026-10-21 17:44–17:52（UTC+8）
> 输入：`R1-pilot/raw-requirement.md`（两 lane 逐字节同一份，sha256 见 `_tools/pilot-check-report.json`）
> 冻结引用：config_hash `3235655e…f61791`、model `Deepseek-V4.1-Flash`
> 机械校验产物：`_tools/pilot-check-report.json`（verdict=PASS, hard_failures=[]）

## 0. 一句话结论

**测量仪器能用，但还不准。** 三项机制（日志纯度 / operator 契约 / 无标注泄漏）可用；但 pilot 自己抓出 **8 处测量缺口**，其中 3 处会让全量 R1 的结论不可信（payload 非确定性、token 预算不可测、渲染层完全未验）。**因此 pilot 数据不得作为毕业证据，连趋势都不得引用。**

## 1. 三个问题的判决

| 问题 | 判决 | 证据强度 |
| --- | --- | --- |
| Q1 `events.jsonl` 日志纯度 | **PASS（机制可用）** | 强：seq 1..n 严格 +1、ts 单调、ts 由 `date -u` 真采、`>>` 追加、mtime ≥ 末条 ts |
| Q2 Observer 盲性 | **PARTIAL —— 只能说"artifact 无标注泄漏"** | 中：机械扫描 0 泄漏；但盲性探针**无区分力**（两条都猜 structured/medium），"双盲已证明"不成立 |
| Q3 Operator 契约可执行 | **PASS（可执行）** | 强：两 lane 独立 node 复跑 exit 0、字段匹配 expected、human gate 实签 |

## 2. 机械校验实据（`_tools/pilot_check.py`，独立复跑，非 operator 自报）

| 项 | h1 | h2 |
| --- | --- | --- |
| events 行数 | 14 | 7 |
| seq 严格递增 | true | true |
| ts 单调 | true | true |
| events mtime ≥ 末 ts | true | true |
| rework 计数 | 0 | 0 |
| wait 事件（单列） | 1 | 0 |
| completion latency（首个 start → complete） | **87.0 s** | **107.0 s** |
| node run-f1 exit | 0 | 0 |
| 匹配 expected.json | true | true |
| submit human gate 实签 @step3 | true | true |
| 盲性扫描 | clean（10 文件） | clean（8 文件，1 处 CSS `align-items: baseline` 已抑制留痕） |
| run_meta.tool_calls | 31 | 22（operator 自报 23，差 1） |
| Observer 缺陷数 | 11（1/2/5/3） | 14（1/4/6/3） |

**unseal（Observer 盲评已落盘后）**：`h1 = skills-path`，`h2 = direct-prompt`（随机化 seed 20261020）。

> 读表纪律：**n=1，禁止当作 skills 优劣**。若硬读，会得到"skills 更快更省、但缺陷更多"这种自相矛盾的方向；这正是 pilot 不该被当证据的原因——单样例 + 逻辑层验证 + 无渲染，任何方向都可能是噪声。

## 3. pilot 抓出的 8 个测量缺口（本次真实产出）

| id | 缺口 | 影响 | 处置 |
| --- | --- | --- | --- |
| **V-1** | 校验器 `REPO` 少算一层，把不存在的 fixture 路径传给两 lane → 两 lane 同时 ENOENT 假失败 | 若我直接采信，会误判两个 operator 都没交付 | **已修**（`../../../../..`）。教训：**不得用未自检的仪器判人**；仪器先跑 dry-run |
| **V-2** | 泄漏扫描把 CSS `align-items: baseline` 判成 lane 泄漏 | 假阳 → 误判 h2 破坏盲性 | **已修**：CSS 属性值抑制 + `suppressed_hits` 留痕，不静默丢 |
| **V-3** | 盲性探针无区分力：两 lane 都猜 `structured`/medium | "双盲"无法证明；探针本身失效 | 保留探针但改写报告措辞；全量 R1 需**换探针**（如让 Observer 排序"设计先验痕迹"而非二选一） |
| **V-4** | token 预算 operator 侧不可测（`tokens: null`） | 冻结的 ≤80k 预算**无法执行**，只能测 tool_calls/wallclock | 全量 R1 必须改 host 侧计量，否则预算条款是空文 |
| **V-5** | 无浏览器自动化（Chrome 启动被沙箱拒），Observer 的界面类结论全靠静态推导 | escaped defect 的"用户是否察觉"退化为猜测 | 全量 R1 前必须接 Chromium 155 harness（DEV-1 同源） |
| **V-6** | operator 自报 tool_calls 与 run_meta 差 1（23 vs 22） | 自计量不可靠 | 预算计量移到 host 侧（与 V-4 同一修复） |
| **V-7** | 产物把状态写进 `artifact/.data/` | 复跑非 hermetic，同目录二次运行携带上一轮状态 | 校验器应在临时副本里跑；或要求状态目录外置 |
| **V-8** | h1 的 `persisted_payload` 含 `savedAt` 墙钟 → 两次复跑字节不同 | **payload 不能逐字节比对**；与"确定性"要求冲突 | 比对须剔除墙钟字段，或要求虚拟时钟。全量 R1 必须先在协议里定死"哪些字段参与比对" |

## 4. Operator 交付质量速览（仅记录，不评判）

- **h1（skills-path）**：走完 core→brief→direction→design-system→flow→verify，产出 `briefs/`（UI-BRIEF / UI-DIRECTION / UI-DESIGN / ui-flow.v1.json / verification-receipt PASS 7/7）+ `artifact/`（5 个 src 模块 + index.html）。
- **h2（direct-prompt）**：直接按需求实现，`artifact/src/{validation,machine,persistence,app}.mjs` + index.html + styles.css，无中间设计件。
- 两条都一次通过 F-1（rework 0）。两条的 critical 我都做了**主控抽查**：
  - h1 D1（`<dialog>` `returnValue` 不复位 → 第二次 ESC 被当"确认保存"）：`index.html:345 showModal()` + `:348` 只判 `returnValue !== 'confirm'`，全文无复位。**结构性成立**，且机器层测试永远看不到。
  - h2 critical（mock 响应被双重入队 `app.mjs:125` + `machine.mjs:190` → 失败后首次重试仍失败）：代码路径**成立**（`setNextResponse` 被调用两次）。
- 结论：Observer 给出的两条 critical **不是幻觉**，抽查命中——这对 escaped defect 通道是正向证据。

## 5. pilot **不能**证明什么（防止后续误引）

1. 不能证明 skills-path 更好或更差（n=1，无渲染，无预算约束）。
2. 不能证明"双盲"（V-3）。
3. 不能证明预算被遵守（V-4/V-6：token 未测）。
4. 不能证明确定性可复现（V-8：payload 含墙钟）。
5. 不能证明真实 UI 质量（V-5：全程无浏览器；F-1 只验状态契约）。

## 6. 进全量 R1（12 fixtures）前必须闭环的 5 项

| # | 待办 | 归属 | 阻断级别 |
| --- | --- | --- | --- |
| 1 | 比对字段白名单（剔除 `savedAt` 等墙钟字段）写入注册 §payload | 1-9-1 补充 | **阻断**（否则每次 run 都无法判等同） |
| 2 | token/时间预算改 host 侧计量 | 1-9-2 | **阻断**（否则冻结预算空转） |
| 3 | 接 Chromium 155 真渲染（与 DEV-1 同源：harness `browser_major` 仍是 `PENDING@1-7-3`） | 代码改动，Acceptance scope 外 | **阻断 escaped defect 的真实性** |
| 4 | 盲性探针换设计（V-3） | 1-9-1 补充 | 非阻断但结论措辞受限 |
| 5 | 校验器在临时副本跑（V-7）+ 自身 dry-run 门禁（V-1 教训） | 1-9-2 | 非阻断 |

## 7. 复现命令

> 一律用**绝对路径**。本 pilot 的 V-1 与初次写本节时都把相对层级数错了——相对路径数层数是这类 harness 最廉价的 bug 来源。

```bash
REPO=/Users/bilibili/Documents/workspace/github/jununfly/ZAgentic
PILOT=$REPO/skills-outputs/ui-agent-skills/paired-runs/v1/R1-pilot
PY=/Users/bilibili/.workbuddy/binaries/python/versions/3.13.12/bin/python3
NODE=/Users/bilibili/.workbuddy/binaries/node/versions/22.22.2-6/bin/node
F1=$REPO/tests/ui-agent-skills/fixtures/form/F-1

cd "$PILOT"
"$PY" _tools/pilot_check.py > _tools/pilot-check-report.json    # verdict / 逐项硬检查
"$PY" _tools/pilot_check.py --unseal                            # 盲评落盘后才允许看映射
(cd h1/artifact && "$NODE" run-f1.mjs "$F1/input.json" "$F1/expected.json" | tail -1)
(cd h2/artifact && "$NODE" run-f1.mjs "$F1/input.json" "$F1/expected.json" | tail -1)
```

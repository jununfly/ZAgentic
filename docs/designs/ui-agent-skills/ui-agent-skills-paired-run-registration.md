# 1-9-1 Paired-Run 运行注册（Execution Registration）

> 归属路线图节点：1-9（三次 paired run 与 graduation gate）/ 1-9-1
> 事实源协议（冻结）：`ui-agent-skills-ev-metrics.md`（节点 1-1-3 预注册，运行前冻结）
> 冻结样例（case）：`ui-agent-skills-ev-form-lock.md`
> 确定性指纹轴来源：`skills/ui/zj-ui-core/scripts/dual_lane_runner.py` 常量 + ev-form-lock 环境段
> 机器可读侧车：`ui-agent-skills-paired-run-registration.json`
> 状态：**已冻结 v1（2026-10-21，zj 批准 ①~⑤）—— 待 zj 对 R1 开跑给 go/no-go**

## 0. 声明与范围（scope gate）

- **Scope = Acceptance/evaluation（技能验收 / graduation gate）**：目标项目代码、依赖、产品文档在本次 paired run 中保持只读；ui-agent-skills 是**被验收对象**，不是被修改对象。
- 本文件把 `ev-metrics.md` 的冻结协议**实例化**为可执行的运行注册。协议已在 1-1-3 冻结，本注册只钉死具体取值与留存位置，不改动口径。
- **配对轴澄清（关键，避免与 dual_lane_runner 混淆）**：1-9 的 paired run 配对 = **direct-prompt lane**（裸 prompt + 通用能力，不接 10 个 UI skill / adapter）**vs skills-path lane**（走 `zj-ui-brief → zj-ui-direction → zj-ui-design-system → zj-ui-flow → zj-ui-verify` 全链路）在**同一 case** 上的对照。这与 `dual_lane_runner.py` 的 `baseline/degraded`（adapter **可用性** 维度）是**不同配对轴**，二者不混用、不互相替代。

## 1. Case（已冻结，引用 ev-form-lock.md）

- **表单 sample**：F-1~F-6（成功 / 空提交 / 非法格式 / 重复提交 / 服务端 422 / 超时）
- **审批 sample**：A-1~A-6（成功审批 / 驳回 / 非法金额 / 重复提交 / 超时 / 越权审批）
- 每次 run 都包含 form + approval 两条 sample 的各一次配对；每 run = 2 pair × 2 lane = 4 执行段；R1/R2/R3 共 6 pair × 2 lane = 12 执行段。
- 框架：`Next.js 14 (App Router) + React 18 + TypeScript 5.x`；浏览器 `Chromium major 155`；数据边界 **本地 mock / 内存态，无真实后端写回**。

## 2. Environment 指纹（确定性轴）

| 轴 | 冻结值 / 口径 | 来源 |
| --- | --- | --- |
| 框架版本 | Next.js 14 + React 18 + TS 5.x | ev-form-lock §1 |
| 浏览器 | **Chromium major `155`**（实测本机 Google Chrome `155.0.8059.85`，Chromium-based）。注：harness 常量仍 `PENDING@1-7-3`，见 §10 偏差 | ev-form-lock §1 / 本机实测 |
| RNG seed | `20261020` | dual_lane_runner.SEED |
| 虚拟时钟 | `2026-01-01T00:00:00+00:00`（无墙钟依赖） | dual_lane_runner.VIRTUAL_EPOCH_ISO |
| 字体策略 | `noto-sans-sc+inter+jetbrains-mono(conditional)`（@fontsource 自托管锁版本，SIL OFL 1.1） | dual_lane_runner.FONT_AXIS_VALUE |
| 网络模式 | `replay`（无真实网络，mock 重放） | dual_lane_runner.NETWORK_MODE |
| 数据边界 | 本地 mock / 内存态，远程写回仅演练 | ev-form-lock §1 |
| Node 运行时 | `>=18.17`（目标 EV 运行时约束 R-ENV-1） | dual_lane_runner |

## 3. Config（同 case / environment / config 约束）

- **同 case**：三次 run 用同一 fixture 集合与同一成功定义。
- **同 environment**：env 指纹三 run 一致（任一阵列变更 → invalid，见 §5）。
- **同 config**：
  - **model（已冻结）**：direct-prompt lane 与 skills-path lane 同用 `Deepseek-V4.1-Flash`（本次注册对话所用 model，系统标注）；三次 run 不变。厂商 snapshot 若静默更新，按 `env_change` 判 invalid（记录 model label，可用时附快照号）。
  - **tool/token 预算（已冻结，2026-10-22 放宽到 80）**：两 lane 同额——每 lane 每任务段 ≤ 80 次工具调用 / ≤ 80k output tokens / ≤ 45 min 墙钟；超限即记 invalid（budget exhaustion 不静默延长）。**关键不变量是两 lane 相等**。原 60 上限因 R3 h8 实测 66 calls 顶穿（日志粒度 vs 预算相互挤压），2026-10-22 zj 决议放宽到 80（DEV-5）。
  - **skills 版本（已冻结）**：skills-path lane 所用 skill 切片 commit = **`ce75cb34b4b2d979b5265c8c50a5fd0084bed9bb`**（= `main` HEAD，PR #204 合并后，2026-10-21）；三次 run 间不变，记入 `config_hash`。
  - **顺序 counterbalance**：R1/R2/R3 在 control/experience 顺序上交错，隔离用户学习效应（见 §6）。
- **config_hash（已计算并冻结）**：
  - 口径：`sha256( canonical_json({ case_fixtures, env_axes, model, tool_budget, skills_commit, counterbalance_order }) )`（`sort_keys=True, ensure_ascii=False, separators=(",",":")`）。
  - 值：**`404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce`**（2026-10-22 因预算 60→80 重算；DEV-5）
  - canonical 载荷全文见侧车 json `config_payload`，可复算。三 run 必须同 hash；任一轴变更 → 该 run invalid。

## 4. Raw log 留存（write-once，不可重写）

- **根目录**：`skills-outputs/ui-agent-skills/paired-runs/v1/`（**已随 skills-outputs/ 清理，2026-10-22；原证据包不复存在**，毕业裁定见 DECISIONS-RISKS 附录 A）。
- **结构**：
  ```
  v1/
    R1/  R2/  R3/
      direct-prompt/   skills-path/
        form/   approval/
          events.jsonl        # 原始事件日志：起止、返工动作、决策起止、等待时间单列
          artifacts/         # screens/DOM 快照、receipt、review 记录
          run_meta.json       # run_id, version, fixture, env_fingerprint, config_hash,
                              #   model, skills_commit, operator, reviewer
  ```
- **不可重写规则**：不可事后重写 prompt、不可删异常样本；所有事件日志与截图/录屏原始留存，write-once。

## 5. Invalid-run 规则（实例化 adjudication，引用 ev-metrics §5）

| 类型 | 判定（实例化） |
| --- | --- |
| 配置漂移 | case / environment / config 与本文注册不一致（含 config_hash 不符） |
| 环境变化 | 浏览器/字体/model/tool 预算/skills 版本/仓库提交变更 |
| 日志缺失 | 缺原始事件、缺 screens/DOM 证据、缺决策起止记录 |
| 人工救援 | 主持人介入、用户被提示“下一步怎么做”、中途人工修补 |
| 范围变更 | scope manifest / paired protocol / 指标定义变化（旧 run 仅作历史，需 re-evaluate） |
| 选择偏差 | 只保留 skills 成功样本、direct-prompt 与 skills 用不同难度任务 |

- **判定与处置**：run 责任人（zjj）提出 invalid 疑议 → 复核者记录 → **Human（zj）批准是否按同协议重跑**；**run owner 不得自行裁定**（ev-metrics sub-06 P 观点 4）。
- 标记：invalid pair/run 不计入三次有效样本，以**新 run ID** 补跑（不补算、不平均）。

## 6. R1 / R2 / R3 计划（counterbalance）

| Run | 顺序 | 覆盖 sample |
| --- | --- | --- |
| R1 | direct-prompt → skills-path | form + approval |
| R2 | skills-path → direct-prompt | form + approval |
| R3 | direct-prompt → skills-path | form + approval |
| R4 | skills-path → direct-prompt | form + approval |

每次 run 含**独立观察员**复核 escaped UI defects（按 critical/high/medium/low 分级）。

## 7. 状态枚举（引用 ev-metrics §6）

`candidate` / `wave-passed` / `quarantined` / `needs-re-evaluation` / `graduated-experience` / `downgraded`
（仅人工 gate 可控：视觉层级、可理解性、关键错误提示、用户决策起止确认、自动化难判定的 UI 语义。）

## 8. 查询入口（可查）

- 本 md + 机器可读侧车 `ui-agent-skills-paired-run-registration.json`（programmatic 检查 case/env/config/invalid 规则，含 `config_hash` 与 `config_payload`）。
- 三次 run 的原始证据目录见 §4；graduation packet 聚合见 1-9-4。

## 9. 运行前冻结项（①~⑤，2026-10-21 全部确认）

| 项 | 状态 | 冻结值 |
| --- | --- | --- |
| ① model | ✅ 冻结 | `Deepseek-V4.1-Flash` |
| ① tool/token 预算 | ✅ 冻结（2026-10-22 放宽） | 两 lane 同额 80 calls / 80k tokens / 45 min / 任务段（超限记 invalid） |
| ② skills_commit | ✅ 冻结 | `ce75cb34b4b2d979b5265c8c50a5fd0084bed9bb`（main HEAD） |
| ③ 双样例范围 | ✅ 确认 | 每次 run 同时覆盖 form F-1~F-6 + approval A-1~A-6 |
| ④ 留存路径 | ✅ 确认（历史） | `skills-outputs/ui-agent-skills/paired-runs/v1/`（**已随 skills-outputs/ 清理，2026-10-22**） |
| ⑤ Chromium major | ✅ 回填（带偏差） | `155`（实测 Chrome 155.0.8059.85）；harness 常量仍 PENDING，见 §10 |
| config_hash | ✅ 冻结（2026-10-22 重算） | `404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce` |

## 10. 已知偏差（不静默接受）

| ID | 偏差 | 影响 | 处置 |
| --- | --- | --- | --- |
| DEV-1 | 原型 `dual_lane_runner.py`（已于 2026-10-22 恢复移植至 `skills/ui/zj-ui-core/scripts/`，此前随 research/ 清理）与 `ui-agent-skills-env-fingerprint.json` 的 `browser_major` 仍是 `PENDING@1-7-3`；`fingerprint` 只回显常量、不探测真实浏览器。1-7-3（storybook adapter）本应回填但未回填。 | 1-9 注册 env 轴（155）与 harness 指纹不一致；不能声称"harness 与注册 env 完全一致"。 | 本注册以实测 155 冻结 1-9 环境；**修 harness 常量属代码改动，Acceptance scope 下不改**，作为独立 product-execution 后续项跟踪（建议新节点或 issue）。此偏差不阻断 1-9 注册与 R1 开跑，但阻断"harness/注册 env 逐字节一致"的强断言。**2026-10-22 补充**：env-fingerprint.json 的 `browser_major` 已回填为 `155`（DEV-1 部分闭环），与注册 env 轴对齐；dual_lane_runner.py 内无字面 `browser_major` 常量（指纹由 env-fingerprint.json 驱动），故无需改代码。 |
| DEV-5 | 预算护栏 60→80 放宽（2026-10-22 zj 决议）。R3 h8 实测 66 calls 顶穿 60 上限，暴露「日志粒度要求 vs 预算上限互相挤压」。 | 仅护栏口径变更：**非**处理变量变更。R2+R3+R4 毕业 cohort 内部效度不受影响（model/skills_commit/case/env 全不变）。 | config_hash 重算为 `404b5c8b…e38ce`；R4 起用新 hash。R2/R3 在 60 上限下从未被 host 硬拦（BLK-2），实际用量均 ≤80，按新护栏均判通过。**禁止**把「80 预算下 skills-path 调用更多」解读为质量差异（lane 固有属性，与预算无关）。 |

## 11. 角色分工（subagent）与口径变更

- 操作者（Builder+Operator）与独立观察员改由 **subagent** 承担，详见 `ui-agent-skills-paired-run-roles.md`。动机：Human 注意力无法持续锁定工具操作 → 计时/操作日志易被污染。
- **口径变更（DEV-2）**：AI 操作者下「决策时间」= **operator completion latency（秒）**，**不等于 human decision time**。graduation 结论 scope 收窄为「AI-operator 下的 artifact 质量与操作效率」，**不得声称"改善人类决策时间 / 人类 UX"**。human-UX 断言需另设人工决策时间轨道。因 1-9 尚未跑，无旧 run 作废；记 1-10 重评待办。

## 12. R1 pilot 回填（2026-10-21，机制验证非证据）

- pilot 记录：`skills-outputs/ui-agent-skills/paired-runs/v1/R1-pilot/PILOT-REPORT.md`（**已随 skills-outputs/ 清理，2026-10-22**；机械校验 `_tools/pilot-check-report.json`，verdict=PASS）。
- 机制判决：Q1 日志纯度 **PASS**；Q2 盲性 **PARTIAL**（无标注泄漏成立，但探针无区分力，**禁止写"双盲已证明"**）；Q3 operator 契约 **PASS**。
- **config_hash 未变**（pilot 不改 case/env/config）；pilot 产物**不计入 R1/R2/R3 任何一次 run**。
- 全量 R1 前新增 3 项**阻断级**待办（详见 pilot 报告 V-1..V-8）：

| ID | 阻断项 | 不修的后果 |
| --- | --- | --- |
| BLK-1 | payload 比对字段白名单（剔除 `savedAt` 等墙钟字段） | payload 两次复跑字节不同，无法判等同 |
| BLK-2 | tool/token 预算改 host 侧计量（§3 的 ≤60 calls / ≤80k tokens 现无可执行计量） | 冻结的预算条款是空文，超限不可发现 |
| BLK-3 | 接 Chromium 155 真渲染（与 DEV-1 同源） | escaped defect 只能静态推导，"用户是否察觉"退化为猜测 |

# 1-9 Paired-Run 角色分工（Operator / Observer 由 Subagent 承担）

> 归属路线图节点：1-9（graduation gate）/ 1-9-2（R1 执行）
> 上游：`ui-agent-skills-ev-metrics.md` §1/§2/§4、`ui-agent-skills-paired-run-registration.md`
> 决策：2026-10-21 zj —— 操作者与独立观察员改由 **subagent** 承担；理由：Human 注意力无法持续锁定工具操作，起止/返工/等待时间戳易被分心污染，**计时与操作日志不可信**。

## 0. 动机（为什么 operator 不用 Human）

- 原协议 operator 是人类：起止事件、返工动作、等待时间靠人手动记录。
- 现实缺陷：Human 注意力漂移 → 时间戳晚记/漏记、返工靠事后回忆补记、等待与决策时间混淆 → 直接污染三项毕业指标。
- 改法：operator 与 observer 均为 subagent，确定性执行 + append-only 日志，Human 只做最终 gate，不参与逐动作计时。

## 1. 角色模型

| 角色 | 承担者 | 职责 | 产物 |
| --- | --- | --- | --- |
| Builder + Operator | **Operator subagent**（每 lane 每次） | 按 lane 条件（skills on/off）构建 artifact，并在 12 fixtures 上操作（填/校验/提交/返工），全程记录 | `artifact/` + `events.jsonl` + `run_meta.json` |
| Observer | **Observer subagent**（每 lane 每次，独立进程） | 只看 artifact + fixtures，**盲评** escaped UI defects（critical/high/medium/low） | `defects.json` |

- **lane = 处理变量**（skills-path vs direct-prompt），由 Operator 的指令决定，**不是**独立角色。故 Builder 与 Operator 合并为同一 subagent（省一次上下文传递、减少漂移）。

## 2. 盲性与隔离（internal validity）

- Operator **不知"被比较"**：只按自己的 lane 指令工作（有 skills / 无 skills），不知道存在对照 lane。
- Observer **不知 artifact 来自哪条 lane**：artifact 目录先去标识（`lane_hidden_id`），Observer 只看到 artifact + fixtures。
- Operator 与 Observer **不共享上下文**；日志分开存放。
- 交叉比对只在校验阶段由主控（zjj）做，且不在 Observer 盲评完成前进行。

## 3. 日志纯度协议（append-only）

- `events.jsonl` 字段：`seq`（monotonic） / `ts`（ISO8601，wall-clock） / `fixture` / `event` / `detail`。
- `event` 枚举：`start` / `action` / `validate` / `submit` / `rework` / `wait` / `complete` / `abandon`。
- **禁止**事后改时间戳、禁止删异常样本（ev-metrics §4 原始证据留存）。
- `run_meta.json`：`role`、`lane_hidden_id`、`budget_used{tool_calls,tokens,wallclock}`、`model`、`config_hash`、`operator_id`。
- **等待时间单列**（`event=wait`），不并入决策时间（ev-metrics §2.2）。

## 4. 指标映射与口径变更（诚实标注，重要）

| 指标 | AI-operator 下的口径 | 是否等价原定义 |
| --- | --- | --- |
| 返工率 | `rework` 事件数 / 任务数 | **基本等价**（由 artifact 质量驱动） |
| Escaped defects | Observer 盲评（不变） | **等价** |
| 决策时间 | **operator completion latency（秒）** | **不等价**：测的是 AI 完成时延，不是 human decision time |

- **结论**：thresholds（返工≥20% / 决策时延≥15% / escaped≥20%）仍可作「**AI-operator 下的 artifact 质量与操作效率**」判据，但**graduation 不得声称"改善人类决策时间 / 人类 UX"**。
- 若要 human-UX 断言：另设**人工决策时间轨道**（小样本，人做决策，subagent 只做机械操作与打点），与本 AI-operator 轨道分开报告，不混算。
- 这是 **scope/validity 变更**（ev-metrics §5）：因 1-9 尚未跑，**无旧 run 作废**；记入 1-10 重评待办。

## 5. Subagent 契约（prompt 骨架，落盘供 R1 用）

### Operator subagent

```
You are the paired-run OPERATOR. You do NOT know there is a comparison lane.
Inputs: frozen_brief_dir, fixtures_dir, config_hash, lane_condition (skills: on|off).
Task: build the artifact under lane_condition; then for each fixture in
      {form F-1..F-6, approval A-1..A-6}, operate the artifact to satisfy expected.json.
Log every step to events.jsonl: {"seq","ts","fixture","event","detail"} (append-only).
Count rework events per ev-metrics §2.1 (validate-fail / submit-reject / field-misread -> revise).
Record wait separately (event=wait). Respect budget: <=60 tool calls, <=80k tokens, <=45min;
  exceed -> event=abandon, stop.
Do NOT read other lanes' artifacts or observer logs.
Output: artifact/, events.jsonl, run_meta.json.
```

### Observer subagent

```
You are the INDEPENDENT OBSERVER. You are blind to the lane.
Inputs: artifact_dir (de-identified), fixtures_dir ONLY.
Task: review escaped UI defects per ev-metrics §2.3; classify severity
      critical/high/medium/low; note whether user_noticed and affects_decision.
Do NOT read operator logs, run_meta, or lane labels.
Output: defects.json [{"id","severity","desc","user_noticed","affects_decision"}].
```

## 6. 开跑前提

- 先产 artifact（Builder = Operator 同一 subagent）。
- Operator 预算与 lane 同额：60 calls / 80k tokens / 45 min（超限 `abandon`）。
- 每 pair 起 1 个 Operator + 1 个 Observer。
- 日志落 `skills-outputs/ui-agent-skills/paired-runs/v1/R1/<lane>/<sample>/`（**已随 skills-outputs/ 清理，2026-10-22；原日志不复存在**）。
- **R1 pilot 先跑 1 个 fixture**，验证日志纯度与盲性，再全量 12 fixtures。

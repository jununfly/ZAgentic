# 1-9 R1 PILOT —— 只验机制，不产出毕业证据

> 归属：1-9-2（R1 执行）的前置 pilot，依 `docs/plans/ui-agent-skills-paired-run-roles.md` §6「R1 pilot 先跑 1 个 fixture，验证日志纯度与盲性，再全量 12 fixtures」。
> config_hash 引用：`3235655e0978279fa004a8e3727677ec3bc6c56d18a963bf921797af13f61791`（见 `ui-agent-skills-paired-run-registration.json`）
> 时间：2026-10-21 17:4x（UTC+8）

## 1. pilot 要回答的三个问题（唯一目的）

| # | 问题 | 判据 |
| --- | --- | --- |
| Q1 | `events.jsonl` 日志纯度机制是否可用？ | seq 严格递增、ts 单调、event 枚举合法、ts 由 `date` 真采（非手填）、append-only（`>>`） |
| Q2 | Observer 盲性是否成立？ | artifact 内无 lane 泄漏 token；Observer 猜 lane 的 self-probe 结果记录在案 |
| Q3 | Operator 契约是否可执行？ | 产出 artifact + run-f1.mjs（node 退出 0）+ run_meta 完整；预算可计量部分被计量 |

## 2. pilot **不是**毕业证据（诚实边界，勿在毕业报告引用）

| 降级项 | pilot 实际 | 冻结协议要求 | 后果 |
| --- | --- | --- | --- |
| 样例数 | **1 个**（F-1 form 成功路径） | form F-1~F-6 + approval A-1~A-6（每次 run 双样例） | 指标无统计意义，n=1 |
| 技术栈 | **零依赖 ESM + 静态 HTML**（离线，禁 npm install） | Next.js 14 / React 18 / TS 5.x | 不是冻结栈的产物，不可作交付质量判据 |
| 渲染验证 | 状态机 / 契约层（node 直跑） | Chromium major 155 真渲染 + 确定性指纹 | 未验像素/可达性（无 playwright/jsdom 可用） |
| 指标口径 | 只计算并记录，**不做门槛判定** | 返工≥20% / 决策时延≥15% / escaped≥20% | pilot 不判 pass/fail，只看机制 |
| token 预算 | **operator 侧不可测**（副代理无法读自己的 token 用量） | ≤80k output tokens | 该维度在 pilot 记 `null`，属已知不可执行项 |

- 这些降级是**故意**的：pilot 的目的是「先证明测量仪器能用」，不是「先测出结论」。
- 全量 R1（12 fixtures）前必须先解决上表第 1、3、5 行（fixture 集齐 + 浏览器 harness + host 侧 token 计量）。

## 3. 目录约定

```
R1-pilot/
  README.md                 本文件
  raw-requirement.md        两 lane **逐字节相同**的裸需求输入
  pilot_meta.json           config_hash / fixture / 预算 / 时间
  _sealed/lanemap.json      hid → lane 映射（Observer 禁止读；盲评完成前主控不交叉比对）
  _sealed/<hid>.profile.json  operator 自写：作业模式(有/无 skill) + operator_id（不进 artifact 目录）
  _tools/pilot_check.py     Q1/Q2/Q3 机械校验器
  h1/  h2/                  hid 目录（去标识）：artifact/ events.jsonl run_meta.json
  observer/defects-<hid>.json  Observer 盲评产出
```

## 4. 盲性与隔离的真实强度（不吹）

- **可机械验证的**：artifact 内容里是否出现 `direct-prompt` / `skills-path` / `zj-ui-*` / `lane` 等 token（`pilot_check.py` 扫）；Observer 是否给出了 lane 猜测及其依据。
- **只能靠指令+信任的**：subagent 是否偷看 `run_meta.json` / `_sealed/` / 对方目录。本 sandbox 不对 subagent 的文件读做审计，**无法证明**。
- 故 pilot 对盲性的结论措辞上限是：**「artifact 内容层面无标注泄漏 + Observer 猜测记录在案」**，不得写成「已证明双盲」。

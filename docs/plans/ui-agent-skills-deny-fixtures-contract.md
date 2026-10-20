# UI Agent Skills — Deny Fixtures 契约（1-4-4）

> 路线图节点：1-4-4（Trust boundary 路线末片叶）
> 层：plan（仅冻结 fixture 契约，不写可执行断言代码）
> 权威源：sub-04-trust-boundary.md（DONE_WITH_CONCERNS）、MASTER.md L94-101、跨视角 B/A/T/S/L 整合立场、以及上游 1-4-1 / 1-4-2 / 1-4-3 沉淀
> 配套：1-4（trust chain 总节点）、1-4-1（catalog allowlist）、1-4-2（policy/approval/sandbox/executor）、1-4-3（provenance/asset-manifest/redaction/quarantine）

## 0. 定位与 Trust Chain 位置

唯一信任链（MASTER L94）：

`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`

本节点是 1-4 子树**末片叶**，冻结**证明层**：用一组 deny fixtures 证明前文 1-4-1/1-4-2/1-4-3 定义的 deny-first 与 fail-closed 语义**真的发生**，而非仅停留在契约文字。它不新定义不变量，只把 1-4-1 §5（G-CAT）、1-4-2 §7（G-POL）、1-4-3 §7（G-PRV）的 deny/fail-closed 闸门转成可判定断言。

Scope 边界：plan 层。本节点**只定义 fixture 契约**（ID / setup / assert / proves / 失败分类），**不写**可执行断言代码；真实 fixture 实现与运行归 1-6（真实技能落地）+ 1-9（paired run 实测），沿用 1-2-4 边界。

## 1. 核心不变量（对 fixture 套件本身）

- **DF1 — deny-first 可证明**：每条 deny fixture 必须断言"请求被 deny / 形成 unknown / 零副作用"，而非"请求被默认 allow"。deny-first 不可证 → fixture 失效。
- **DF2 — fail-closed 可证明**：远程/凭据/策略/catalog 不可用时，fixture 断言"运行失败、不施加副作用、不伪造成功"。伪造成功 → fixture 失效。
- **DF3 — 离线可运行**：所有 deny fixture 在**无网络、无凭据、无外部设计工具**下必须可运行（沿用 golden-fixtures-spec §8 fail-closed 要求）。这是本节点退出判据的承载。
- **DF4 — 零泄漏可证明**：凭据/网络/截图泄露类 fixture 必须断言 secret 明文出现计数 = 0、redaction 失败 → fail closed。
- **DF5 — 覆盖完整**：1-4-1/2/3 的全部 deny 与 fail-closed 闸门须被至少一条 DF-* 覆盖（no gate left unproven）。

## 2. Fixture 设计规范

每条 fixture 形式化字段：

| 字段 | 含义 |
|---|---|
| `id` | `DF-<类别>-<序号>`（见 §3 命名空间） |
| `category` | `CAT`（未注册组件/危险 action）/ `SEC`（凭据网络截图泄露）/ `REM`（远程写回失败）/ `OFF`（离线 fail-closed 覆盖） |
| `setup` | 触发条件（含模拟的不可用/失败注入点） |
| `assert` | 必须成立的判定（deny / 零副作用 / 零明文 / fail closed） |
| `proves` | 指向其证明的 1-4-x 闸门 ID（G-CAT-* / G-POL-* / G-PRV-*） |
| `fail_class` | 违反 deny-first / fail-closed / 零泄漏 → **契约失败**（非 warning） |

- 命名空间：`DF-*`（区别于 golden `GF-*` 与 skill 级 `FF-*`），与闸门 ID（G-CAT/G-POL/G-PRV）解耦避免混淆。
- 失败分类口径：与 golden-fixtures-spec §1 一致——关键语义被静默丢弃 / 伪造成功 = **失败**（非 warning）。
- 复用 property：1-4-1 §3 `intent_id` 确定性派生、1-4-2 §5 严格四检、1-4-3 §3 `asset_id`/`content_hash` 确定性——fixture 断言须可重放（同输入同结果）。

## 3. Deny Fixtures 清单（DF-*）

### 3.1 Category CAT — 未注册组件 / 危险 action（proves 1-4-1 + 1-4-2）

| ID | setup | assert | proves |
|---|---|---|---|
| DF-CAT-01 | 调用未注册 component/action | 形成 `unknown`/`deny` intent，executor 零副作用，写最小审计事件 | G-CAT-1, G-POL-5 |
| DF-CAT-02 | 请求危险 action（未授权 Figma 写回 / 越权网络 egress） | intent 标记 deny，不进入 policy 放行；无旁路 | canonical schema §3 action "危险 action→deny", G-POL-5 |
| DF-CAT-03 | catalog 不可用（registry 缺失/签名失败） | fail closed：形成 `unknown`，不返回默认 allow | G-CAT-2, G-POL-6 |
| DF-CAT-04 | intent 缺 `catalog_id/version` 或引用未注册条目 | 拒绝生成 intent，不进入 policy | G-CAT-3 |
| DF-CAT-05 | intent 与 catalog 版本/参数哈希不一致 | 拒绝；不自动降级 | G-CAT-4 |
| DF-CAT-06 | unknown 项 | 不压空值、不按名称猜测、不模拟成功，审计含决策点 | G-CAT-5 |
| DF-CAT-07 | intent 重放 100 次 | 结果一致（确定性），均 deny | G-CAT-7 |

### 3.2 Category SEC — 凭据 / 网络 / 截图泄露（proves 1-4-2 P7/G-POL-7 + 1-4-3 G-PRV-3/8）

| ID | setup | assert | proves |
|---|---|---|---|
| DF-SEC-01 | 触发含 secret 的副作用（prompt/产物/日志/截图/audit） | secret 明文出现计数 = 0；credential 仅 ref | G-POL-7, G-PRV-3 |
| DF-SEC-02 | 含 secret 的 screenshot 落盘 | 落盘前被 redact；redactor 失败 → fail closed 不落盘 | G-PRV-8 |
| DF-SEC-03 | credential broker 不可用 | 运行失败，不回退明文、不伪造成功 | G-POL-6/7 |
| DF-SEC-04 | 网络 egress 越权（DNS/redirect 重新校验失败） | deny；egress 精确限定 host/path/method/data_class | G-POL-1/2（approval 维度） |

### 3.3 Category REM — 远程写回失败（proves 1-4-2 P6 + scope-manifest §4）

| ID | setup | assert | proves |
|---|---|---|---|
| DF-REM-01 | 远程写回失败（endpoint 5xx/timeout） | 失败不伪造成功；本地回退 `degraded/disabled/quarantine` | G-POL-6, scope-manifest §4 |
| DF-REM-02 | 远程服务不可用时的 verification | 聚合状态 `BLOCKED`/`QUARANTINED`，不计入 PASS 覆盖率（G-18 精神） | G-POL-6, lease-state-machine G-18 |
| DF-REM-03 | 远程写回幂等键缺失/重复 | 同一 `(intent_hash, lease)` 仅一份副作用（P8） | G-POL-8 |

### 3.4 Category OFF — 离线 fail-closed 覆盖矩阵（直接承载退出判据）

退出判据原文："deny fixtures 在无网络、无凭据、未注册组件和远程失败时均 fail closed"。

| ID | 条件 | assert | 承载退出判据 |
|---|---|---|---|
| DF-OFF-01 | 无网络 | 全部 DF-* deny 语义不变，fixture 可运行 | 无网络 |
| DF-OFF-02 | 无凭据 | 全部 DF-* 可运行，secret 零明文（DF-SEC-01 仍 0） | 无凭据 |
| DF-OFF-03 | 未注册组件（catalog 空/缺） | deny-first 仍生效（DF-CAT-01/03 仍 deny） | 未注册组件 |
| DF-OFF-04 | 远程失败（模拟 endpoint 失败） | fail closed 不伪造成功（DF-REM-01/02 仍失败） | 远程失败 |

## 4. 套件级硬闸门（本节点对 fixture 套件自身的要求）

| 闸门 | 含义 | 实测归属 |
|---|---|---|
| G-DF-1 | 1-4-1/2/3 全部 deny/fail-closed 闸门被至少一条 DF-* 覆盖（no gate unproven） | 1-9 套件运行 |
| G-DF-2 | 任一 deny fixture 出现"默认 allow / 零副作用未断言 / 伪造成功" → 套件失败（非 warning） | 1-9 套件运行 |
| G-DF-3 | DF-OFF-01..04 四条件全部满足（无网络/无凭据/未注册组件/远程失败均 fail closed） | 1-9 套件运行 |
| G-DF-4 | DF-SEC 类 fixture 的 secret 明文计数恒为 0 | 1-9 套件运行 |
| G-DF-5 | 全部 DF-* 可重放（同输入同结果），断言确定性 | 1-9 套件运行 |

fail closed 优先：策略/catalog/manifest/broker 不可用时 fail closed；deny fixtures 在无网络/无凭据/无外部设计工具时仍必须可运行（MASTER L101，golden-fixtures-spec §8）。

## 5. 与 1-4-x 闸门映射（证明矩阵）

- **1-4-1（G-CAT-1..7）** → DF-CAT-01..07（全覆盖）。
- **1-4-2（G-POL-1..9）** → DF-CAT-01/02/04/05/07（policy/approval/lease/digest/三入口同决策）、DF-SEC-01/03/04（secret/网络）、DF-REM-01/02/03（fail closed/幂等）。G-POL-9（三入口同 decision_record）由 1-9 多入口同决策用例承载，本节点提供单入口 deny 语义基线。
- **1-4-3（G-PRV-1..8）** → DF-SEC-01/02（secret 零明文 / redaction fail closed）、DF-OFF-02（无凭据零明文）。license quarantine（G-PRV-4/7）由 1-9 资产采用用例承载，本节点提供"unknown license 资产不进默认产物"的 deny 基线。
- 覆盖完整性由 G-DF-1 强制；任一 gate 未被 `proves` 引用 → G-DF-1 失败。

## 6. 上下游契约义务

- **上游**：1-4-1/2/3 定义的不变量与本节点 `proves` 字段一一对应；本节点不新增不变量，只把前文闸门转为可判定断言。
- **下游**：本节点 fixture 套件在 1-9 paired run 中与 direct-prompt baseline 并行执行，其 deny-first / fail-closed 实测结果回写 roadmap（解除 1-4-1/2/3 的 open 标注），并作为 1-4 整节点可声明完成的**最后一块拼图**（1-4-1 §10 / 1-4-2 §10 / 1-4-3 §10 共同指向本节点）。
- **跨节点**：与 golden-fixtures-spec §8 同口径——deny-first fixtures 在无网络/无凭据/无外部设计工具时仍必须可运行；本节点是 1-4 对"deny-first 真发生"的收口证据。

## 7. 退出判据对照（1-4-4 exit criteria）

> 原文："deny fixtures 在无网络、无凭据、未注册组件和远程失败时均 fail closed"

| 判据要素 | 承载 fixture | 状态 |
|---|---|---|
| 无网络 → fail closed | DF-OFF-01 | 契约已定义，实测 open（归 1-9） |
| 无凭据 → fail closed | DF-OFF-02 | 契约已定义，实测 open（归 1-9） |
| 未注册组件 → fail closed | DF-OFF-03 | 契约已定义，实测 open（归 1-9） |
| 远程失败 → fail closed | DF-OFF-04 | 契约已定义，实测 open（归 1-9） |

## 8. 遗留 open 项（禁止当作已通过）

- 全部 G-DF-1..5 属**实测闸门**，需 1-6（真实技能 + fixture 断言落地）+ 1-9（paired run 真实运行）回写实测证据。
- 本节点 `completed` = **fixture 契约冻结落盘（plan 层）**，不等于闸门实测通过。任何 receipt / 运行不得把 G-DF 写成"已通过"。
- 待 1-9 真实跑通且 G-DF-1..5 全绿后，由 1-9 承载节点回写实测值，并解除 1-4-1/2/3 的 open 标注；至此 1-4 整节点方可声明完成。

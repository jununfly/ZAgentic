# paired run · 观察员取证规程（v1，R2 起强制）

- **归属**：1-9（三次 paired run 与 graduation gate）· 支撑节点 1-9-2/1-9-3
- **解决的问题**：**DEV-3** —— R1 里两个 Observer 取证深度不对称（h3 全部 `static`，h4 有 6 条 `executed`），
  导致两条 lane 的 escaped defect 计数**不完全可比**：差异里混进了"谁查得更深"。
- **本规程的作用**：把"查什么、怎么查、证据怎么记"钉成同一套动作，让两 lane 的缺陷计数只在产物质量上分叉。

---

## 1. 强制动作（两个 Observer 必须逐条执行，顺序一致）

| # | 动作 | 记录要求 |
| --- | --- | --- |
| A1 | 跑驱动：`cd <artifact> && <node> run-fixtures.mjs <fixtures>` | 记录 exit code 与 `all_match` |
| A2 | 静态清单逐项判定（见 §2），每项标 `pass / fail / na` | 每项 `fail` 必须转成一条 defect |
| A3 | 逐条 defect 必须给 `file:line` | 无行号 = 无效 defect，不得入账 |
| A4 | 标 `evidence`：`executed`（真的跑过该路径/DOM-less harness）或 `static`（只读代码推断） | 不许把 static 写成 executed |
| A5 | 盲性探针（lane_guess + confidence + basis） | 只许基于产物，不许读目录外任何东西 |

## 2. 静态清单（12 项，缺项即 `na` 而非 `pass`）

这 12 项是 R1 实际抓到缺陷的收敛结果，也是 fixture **结构上卡不住**的地方——fixture 只校验状态机的输入输出，不校验"用户怎么走到那个状态"。

| ID | 检查项 | 为什么 fixture 卡不住 |
| --- | --- | --- |
| S1 | **状态可达性**：目标状态的入口是否真的存在于 UI（是否存在触发该 transition 的控件/动作） | fixture 用 `initial_state` 直接注入，跳过 transition（R1 h4 D3 正是此类） |
| S2 | 错误文案可执行性：失败提示是否说清"哪个字段/违反什么约束/怎么改" | fixture 只断言 `final_state`，不看文案 |
| S3 | 字段错误与控件的程序化关联：`aria-describedby` / `role=alert` / `aria-live` | 无 a11y 断言 |
| S4 | 提交/审批瞬间的焦点归属：被禁用或关闭的元素是否持焦点 | 无焦点断言 |
| S5 | disabled 矩阵：每个状态下哪些控件该可用/该禁用，是否与产品语义一致 | fixture 不断言控件可用性 |
| S6 | 恢复路径存在性：每个错误态是否都有一条 UI 出口（重试/编辑/放弃） | fixture 只给下一条 action，不管用户点得到点不到 |
| S7 | 双提交防护：提交中连点是否只生效一次 | fixture 单线程驱动 |
| S8 | 必填/长度的**语义**暴露（`required`/`aria-required`/`maxlength`），不只是 JS 校验 | 无 a11y 断言 |
| S9 | 驳回理由：是否存在独立的理由输入且被展示给申请人 | R1 h4 D4/D5 正是此类 |
| S10 | 版本可见性：「形成新的一版」在界面上是否可见 | fixture 只断言 `version` 字段 |
| S11 | 回滚语义：放弃修改回滚到"最近一次保存"还是"硬编码初始值" | R1 h4 D2 正是此类（静默数据丢失） |
| S12 | 内部枚举外泄：`client_validation` / `role_denied` 这类状态码是否直接进用户文案 | 无文案断言 |

## 3. 证据配平规则（**本次新增，硬规则**）

R1 的教训是"谁跑得多，谁缺陷多"。因此：

> **配平规则 R-BAL**：若一条 lane 的 `executed` 证据条数 ≥3，而另一条 <1，
> 则该 run 的 **escaped defect 差值标记为 `confounded`**，只能用于"发现问题"，
> **不得用于 graduation 判定**。

落地方式：`RUN-RECEIPT.json` 的 `blindness` / `checks` 里写 `evidence_balance`：
`{"h_a": {"executed": n, "static": m}, "h_b": {...}, "balanced": true|false, "confounded": true|false}`。

## 4. 严重度锚点（避免两人标尺不一）

| 级别 | 锚点（满足其一） |
| --- | --- |
| critical | 主流程走不通（状态不可达 / 无法提交 / 无法恢复）；可能提交或审批**错误数据**；关键控件键盘/读屏不可达；关键错误信息不可理解 |
| high | 焦点丢失；错误恢复路径断裂；静默数据丢失；明显的语义/布局错误；双提交 |
| medium | 文案不准确、内部枚举外泄、状态变化无反馈 |
| low | 纯视觉/措辞细节 |

## 5. R2 执行顺序（固定，防串味）

1. 主控起 2 个 Operator（互不可见），得 `hA` / `hB`。
2. 主控跑机械校验（`r1_check.py`）——**先仪器自检**，仪器 bug 不得判人（pilot V-1 教训）。
3. 主控起 2 个 Observer，**同一条 prompt 模板**、只换 hid 与目录；两者都不知对方存在。
4. Observer 落盘 `defects-<hid>.json` 后，主控才做交叉比对（解封 `lanemap`）。
5. 主控填 `evidence_balance`，判断是否 `confounded`。
6. 出 run 报告 + 收据。

## 7. 仪器自检清单（每次跑 run 之前必须过一遍）

R1（含 pilot）一共踩到 5 个**仪器自身**的坑，全部会造成假绿或假红。仪器没自检就判人 = 无效运行。

| # | 坑 | 症状 | 硬要求 |
| --- | --- | --- | --- |
| I-1 | 相对路径少算一层 | 两 lane 同时 ENOENT，看起来像两个 operator 都没交付 | 用 `_find_repo()` 逐级向上找 `.git`，不写死 `../..` |
| I-2 | 泄漏扫描误报领域词 | CSS `align-items: baseline`、`recovery lane` 被判成 lane 泄漏 | 只匹配与比较轴连用的具体 token；误报要进 `suppressed_hits` 留痕，不静默丢 |
| I-3 | 只匹配控件 id 就算"有恢复路径" | `#recover` 存在但 `hidden = state !== 'error'` 恒隐藏 → 假 pass | 存在性与**门控极性**分开判：机械只给 `present` + 摘出 `gating_expression`，人判极性 |
| I-4 | 变异探针在产物目录内跑 | 驱动覆盖 `.run-fixtures-result.json`，后续汇总把 12/12 读成 fail | **变异一律在 artifact 副本里跑**，原件只读 |
| I-5 | `checked == 0` 判 PASS | artifact 为空时扫描 0 个文件却判 `clean` | 任何 gate 先断言 `checked > 0`，否则 `not_checked` |

> 通用规则：**先跑一次干跑（dry-run），确认仪器在"已知会失败"的输入上真的报 FAIL**，
> 再拿它去判 operator。

## 8. 仍未闭环（不属本规程能解决）

| 编号 | 缺口 | 出路 |
| --- | --- | --- |
| BLK-2 | token 预算不可计量 | 需改 harness（`skills/ui/zj-ui-core/scripts/`，已恢复移植）截获 usage（出 Acceptance scope，待 zj 立项） |
| BLK-3 | 渲染层未实测（无浏览器） | 接 Chromium 155，或退一步做 DOM 断言级验证（同样需代码改动） |
| BLK-4 | rework 仅 operator 自记，且**事后不可反推** | R1 实测：产物 mtime 只保留最后一次写，两条 lane 的产物 mtime 序列均单向递增、无重写痕迹 → 无法反推返工次数。**R2 起必须加 append-only `driver-runs.jsonl`**（每次驱动退出码 + 失败断言明细），否则返工率永远只是自报值 |
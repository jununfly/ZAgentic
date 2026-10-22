# 渲染层验证 · R2+R3+R4 全 cohort（BLK-3 闭环）

> 取代 `RENDER-LAYER-R3R4.md`：原文档仅覆盖 R3+R4（4 lane）。本文件覆盖毕业 cohort
> **全部 3 次 run × 2 lane = 6 lane**，闭环 b1（补 R2 渲染层）。

## 方法
真实 Chromium 155.0.8059.85 headless + puppeteer-core + Node 22，**DOM 断言级**
（不依赖截图/读图，每条信号是 DOM 事实或退出码）。覆盖：

- R2：`h5` = direct-prompt，`h6` = skills-path
- R3：`h7` = direct-prompt，`h8` = skills-path
- R4：`h9` = skills-path，`h10` = direct-prompt

每 lane 7 断言 A1–A7，驱动脚本 `_tools/render_layer_check.mjs`（可复现，`RL_OUT` 指定输出；
R2-h6 为双页面应用，由 `runLaneMultiPage` 处理 index.html + approval.html）。

| 断言 | 含义 |
| --- | --- |
| A1 | 启动无 pageerror / console error |
| A2 | 关键控件 + 必填输入在 DOM 中存在 |
| A3 | 资料必填输入经 `aria-describedby` 关联错误区 |
| A4 | 审批必填输入经 `aria-describedby` 关联错误区 |
| A5 | under_review 态下 approve 控件键盘可达（不禁用、可见、focus 落点） |
| A6 | 强制服务端失败渲染为 error，绝不渲染为 success |
| A7 | 超时/升级保持 under_review，绝不伪造成功 |

## 结果矩阵

| lane | A1 | A2 | A3 | A4 | A5 | A6 | A7 | 分 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2-h5 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R2-h6 **skills** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7/7 |
| R4-h9 **skills** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7/7 |
| R4-h10 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R3-h8 **skills** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |
| R3-h7 **direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | 5/7 |

原始数据：`_tools/render-layer-report.json`（紧凑 cohort 矩阵；verbose 报告可由 harness 再生）。

## 解读

1. **唯一差异轴是 A3/A4（aria-describedby 关联）**。A1/A2/A5/A6/A7 在全部 6 lane
   **18/18 全过**——启动、DOM 完整性、键盘可达、失败不渲染成功、超时不伪造成功，两 lane 完全平价。
2. **direct-prompt 在 A3/A4 上 0/3 全失败**：3 次 run 的 direct lane 全部未给必填输入关联错误区
   （这是 §6 盲点#4 的真实 a11y 缺陷，独立坐实）。
3. **skills-path 在 A3/A4 上 2/3 通过**：R2-h6、R4-h9 通过，R3-h8 漏（与契约层 R3 那次 skills 也漏一致）。
   skills 自身在该维度也**非 100% 可靠**。
4. **方向纠正（相对 R3+R4 子集）**：原未含 R2 时曾显"R4 有差异、R3 平 → 方向不稳健"。补 R2 后，
   三 run 一致呈现 **skills ≥ direct（2 胜 1 平，从不劣于）**——render 层与契约层方向完全一致
   （契约层：R2 10 vs 20、R3 11 vs 17、R4 7 vs 7）。

## 对 graduation gate 的影响

- 渲染层证据从"平价、强化 `NOT_GRADUATED`"**修正为"skills 有持续、窄幅 a11y 优势
  （从不更差，2 胜 1 平），其余完全平价"**。
- 该优势**仅落在单一 a11y 维度（aria-describedby 关联）**，且 skills 自身仅 2/3 可靠；
  成本侧（契约层）skills 仍 3 次全更贵（返工 +303% / 调用 +48% / 墙钟 +357%）。
- **最高杠杆仍是把 4 条机械门禁落到 `zj-ui-verify`**（含 A3/A4 的 aria-describedby 关联）：
  一旦该门禁存在，direct 的 0/3 缺陷与 skills 的 1/3 漏检都会被硬拦截，质量差异在验证层被抹平，
  采纳决策回归成本权衡。

## 结论（控制器不自裁，待 zj 签）

渲染层**不再支持"纯平价"**。证据指向：**skills-path 在 a11y 维度有真实但窄且非完全可靠的优势，
成本溢价持续**。建议裁定方向从 `NOT_GRADUATED_as_quality_win` 调整为
**"有条件采纳 / pilot + 门禁"**——但 gate 最终由 zj 批准（ev-metrics sub-06 P4：run owner 不自裁）。

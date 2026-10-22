# 渲染层证据（BLK-3 闭环）· R3 + R4 cohort

真实 Chromium 155.0.8059.85 headless，DOM 断言级验证（**不依赖截图/读图**——每条信号都是 DOM 事实或退出码）。
覆盖毕业 cohort 中**决策最关键的两轮**：R4（平局那次）+ R3（skills 优势最大那次）。每 lane 7 条断言 A1–A7。
R2 延后（见末尾）。原始数据：`_tools/render-layer-report.json`；驱动脚本：`_tools/render_layer_check.mjs`（puppeteer-core + Node 22）。

## 1. 断言定义

| id | 断言 | 为什么重要 |
| --- | --- | --- |
| A1 | 启动无 pageerror / console error | 渲染失败 = 页面崩了 |
| A2 | 关键控件 + 必填输入都在 DOM | 结构完整性 |
| A3 | 必填资料输入用 `aria-describedby` 关联错误提示 | 视障/读屏可达性（a11y） |
| A4 | 必填审批输入用 `aria-describedby` 关联错误提示 | a11y |
| A5 | `under_review` 态下 approve 控件键盘可聚焦（不 disabled、可见、`focus()` 命中） | §6 盲点#1「迁移 UI 不可达」的视图层判据 |
| A6 | 强制服务端失败 → 渲染为 error，绝不为 success | §6 盲点#2「静默丢数据/伪成功」 |
| A7 | 超时/升级 → 状态停在 `under_review`，绝不伪造 success | §6 盲点#3 的 UI 侧表现 |

## 2. 结果（4 lane × 7 断言）

| lane | A1 | A2 | A3 | A4 | A5 | A6 | A7 | **分** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **R4-h9 skills** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **7/7** |
| **R4-h10 direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | **5/7** |
| **R3-h8 skills** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | **5/7** |
| **R3-h7 direct** | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | **5/7** |

A3/A4 失败细节：除 R4-h9 外，其余 3 个 lane 的必填输入**完全没有 `aria-describedby`**（错误提示只有 `aria-live`/`role=alert`，但输入本身没程序化关联到它）。

## 3. 逐断言解读

- **A1 / A2（启动 + DOM）**：4 lane 全 PASS。两 lane 都能正常渲染、控件齐全。**渲染层无崩溃，无结构缺失。**
- **A3 / A4（aria-describedby 关联）**：**只有 R4-h9（skills）通过**；R4-h10、R3-h8、R3-h7 全 FAIL。
  → skills-path 在「错误提示程序化关联」上**仅仅在 R4 那次做到了**，R3 那次（也是 skills）同样没做到。direct 三次全没做到。
  → 这是渲染层**唯一**出现 skills/direct 差异的维度，且**方向不稳健**（1 胜 / 1 平）。
- **A5（键盘可达 approve）**：4 lane 全 PASS。两 lane 在正确状态下 approve 控件都键盘可达。**平价。**
- **A6（失败不为成功）**：4 lane 全 PASS。§6 盲点#2（静默丢数据/伪成功）**在渲染层根本不存在**——它只是契约层状态机的内部问题，UI 层都正确处理了。
- **A7（超时不伪造成功）**：4 lane 全 PASS。平价。

## 4. 跨 run 方向（skills vs direct，渲染层）

| 断言 | R3 | R4 | 方向 |
| --- | --- | --- | --- |
| A1/A2/A5/A6/A7 | 平价 | 平价 | **5/5 平价** |
| A3/A4（aria 关联） | 平（两 lane 都 FAIL） | skills 胜 | **1 胜 / 1 平，非稳健** |

## 5. 结论（控制器分析，zj 终审）

**BLK-3 证据并未揭示 skills-path 有任何稳健的渲染层优势：**
- 7 条断言里 6 条两 lane **完全平价**（含键盘可达性、失败/超时正确性这些最关键的可达性与「不伪成功」属性）。
- 唯一差异维度（aria-describedby 关联）skills 只在 R4 做到、R3 同样缺失 → 与契约层结论同构：**skills 优势方向不稳健**。

**对毕业判定的影响**：强化而非推翻 `NOT_GRADUATED_as_quality_win`。在「最有价值的 a11y/视觉层」实测后，skills-path 仍 ≈ **平价但更贵**（契约层：返工 +303% / 调用 +48% / 墙钟 +357%；渲染层：无稳健质量胜出）。

## 6. 比毕业结论更值钱：渲染层坐实的缺陷（转 `zj-ui-verify` 门禁）

**`aria-describedby` 关联缺失**（4 lane 中 3 个 FAIL，含 R3 的 skills lane）→ 这是契约层观察员已标记（h10 D1）但渲染层**独立确认其广泛存在**的真实 a11y 缺陷。
→ 给 `zj-ui-verify` 补第 4 条强制门禁：**必填输入必须 `aria-describedby` 关联其错误区域**（与已有的「迁移可达性 / 失败不得渲染为成功 / 状态机返回值必须被检查」并列）。

## 7. 范围与未闭环

- 覆盖 R3+R4（决策关键 cohort）。**R2（h5 direct / h6 skills）未跑**——其 artifact DOM 尚未接入驱动脚本；如需把渲染层证据扩到完整 R2+R3+R4 cohort，再补两个 lane 的 selectors/驱动即可（同 harness，增量）。
- BLK-2（token 不可计量）仍 open。
- 盲性仍不可称双盲（探针 4~5/6 命中）。
- 像素级视觉（布局/对比度）未测——属「视觉」而非「可达性」；当前结论限定在 a11y/可达性/不伪成功，已足以回答「skills 是否在最有价值层有独特价值」。

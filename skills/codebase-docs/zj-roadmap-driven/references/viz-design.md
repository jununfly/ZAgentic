# 只读可视化设计要点（viz/ 包）

本页是 `zj-roadmap-driven` 的按需参考：只有需要理解或修改可视化投影时才读。
**入口命令与路径基准在 [SKILL.md](../SKILL.md) 的「只读可视化」小节**；本页不重复发布命令。

viz 把 roadmap carrier **只读**投影成同一份 view-ir 派生的多张视图：自包含 HTML
（局部 DAG + 信息卡片 + 交互 + 边回溯）、Mermaid 文本等价物、S3 dependency 投影、
S4 context 侧载包。**绝不回写 carrier** —— 只消费 `nodes` / `edges`(blocks) /
`debts` / `context` / `metadata.updated`，不修改任何传入数据。只读不变式由 S0/S2
与 S3/S4 两组单测共同钉住（`viz/tests/test_viz.py` 的 `TestS0ReadonlyContract`）。

## 信息选择

- **确定性 DOI 选择**（非 LLM）：六权重加权 `T1 图邻近 0.30 / T2 阻塞关键 0.25 /
  T3 共享上下文 0.15 / T4 债务严重度 0.15 / T5 新鲜度 0.10 / T6 稳定性惩罚 0.05`
  （sum=1.0）。焦点自身 DOI=1.0；低于 θ 直接折叠。
- **θ 单一旋钮**（A 方案）：θ = 最低可见 DOI 下限；运行时按焦点下非强制项 DOI
  分布取百分位（0.85 / 0.50 / 0.15）校准三档预设（overview / neighborhood / expand），
  避免写死阈值在部分焦点退化成等价。
- **三档 LOD + 阅读预算**：L2(4行) / L1(2行) / L0(1行)，预算硬上限 40 行；预算溢出
  **不静默** —— `budget_folded` 显式报数，且 LOD 对 DOI **严格单调**（同 DOI 整桶一起
  升级，升不动即停手，禁止更低 DOI 越级）。
- **必备项强制可见**：焦点 + 阻塞前驱 + 后继 + 高严重度债务必进可见集 V，
  非焦点必备项恒为 L1。
- **债务一等建模**：显式 `debts` 优先；文本启发仅认 gap / todo / risk / sweep 一类
  关键词，**不把「有 notes」误判为债务**。

## 投影与渲染

- **局部 DAG 渲染**：vendored `@dagrejs/dagre@3.1.3` UMD 提供分层坐标，自研 SVG 渲染；
  交互含多行标签、点击展开折叠项、重置视图、θ 滑块。几何经几何校验脚本复核：
  全焦点零重叠、零裁切、复合节点界内。依赖溯源见 [VENDOR.md](../viz/VENDOR.md)。
- **anchor 信封**：`zj-roadmap-visual-review/v1` 携带 view-kind + carrier-stem +
  node-uid + carrier-revision，视图可追溯到源 carrier 而不污染 carrier。S4 起另有
  `zj-roadmap-anchor/v1` 单行 token（CLI 输出、可复制、可解析），显示 id 从不作锚点。
- **S3 dependency 投影**：阻塞链取自 `doi.rev_bfs`（与 S1 view-ir 的
  `selection.pdepth` 同一函数），`impact` / `critical-path` 与 CLI 同名查询逐行等价，
  测试直接 import 核心库交叉断言。每条 blocks 边带 `edge_id`（carrier uid，缺失时
  确定性派生）与 `source`（edges 下标 + evidence-ref，缺失显式 `unknown`）；HTML 点击
  边回溯，Mermaid 等价物用边标签写 id。
- **S4 context side-pack**：单节点的决策 / trace / 边 / 证据引用 / 影响闭包打成独立
  JSON，每条带 `source` 与 `evidence-ref`。主视图只内嵌展示字段白名单并留一个恒定
  入口，**上下文条目增长时 HTML 逐字节不变**。`revision` 不符时显式 stale 并写出
  刷新命令，`auto_refresh=false` —— 绝不执行、不静默重绘、不回写 carrier。

演示语料：`demos/roadmap_viz_sample.json`（21 节点 + 15 条 blocks 边 + 3 条一等债务）。

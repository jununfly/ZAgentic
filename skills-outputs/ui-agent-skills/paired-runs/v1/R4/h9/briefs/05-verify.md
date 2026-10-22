# 05 · S9 Verify — 验证门禁与 receipt

> 来源 skill：zj-ui-verify（S9 VERIFY）。DOM/ARIA、focus、contrast、reduced-motion、
> 网络边界硬门禁；receipt 缺链路/用 baseline 冒充/stale 当证据 → 不生成成功 receipt。

## verification matrix（本任务可执行的硬门禁）
1. **DOM/ARIA**：输入框配 `aria-describedby` 错误节点；Banner 用 `role=alert` + `aria-live=assertive`；
   状态读屏区 `aria-live=polite`。两页面用 `role=tablist/tab/tabpanel`。
2. **focus**：主按钮在禁用态不可聚焦触发；加载/角色切换后焦点不丢失（tab 锚点存在）。
3. **contrast**：见 03-design-system，全部 ≥4.5（AA）。
4. **reduced-motion**：动效 ≤150ms 且为必要过渡；已避免持续动画，满足 prefers-reduced-motion 兜底。
5. **network boundary（关键业务语义）**：
   - 422 → 明确错误 + 可恢复，无成功文案；
   - 超时(0) → `fallback=stable_path` + `explicit_marker=true`，**绝不**显示“保存成功”；
   - 重复提交 → `duplicate_suppressed`，仅一次 `writes`；
   - 越权审批 → deny-first，状态不前进，无 human_gate。

## 自动化结论（headless）
- 驱动重放 12 fixture，逐条比对 snapshot，`mismatch_keys` 全空。
- `all_match: true`，exit code 0。
- receipt 链路：fixture 集 F-1..F-6 / A-1..A-6 + 本产物 commit 哈希 + config_hash
  `404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce`。

## 观察者 UX 复核要点（人工/observer）
- 每个状态迁移在 UI 有可达控件（见 04-flow 控件表）→ S1 可达性满足。
- 提交/审批均需 `window.confirm` 显式确认（human gate 实签）。
- 错误态提供恢复控件，避免死路。

## status
- PASS（12/12）。如环境 fingerprint 变化需重跑；baseline 不冒充新通过。

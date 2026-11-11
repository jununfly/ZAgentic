# dagre 供应商说明（viz 包）

`dagre.vendor.js` 是从 **`@dagrejs/dagre@3.1.3`**（npm 官方包，MIT，活跃维护）取出的浏览器 UMD 构建，用于**布局坐标计算**（Sugiyama 确定性分层：rank + 重心降交叉 + 坐标分配）。

- 它不是我们手写的布局算法，而是真实 npm 依赖；`package.json` 钉了版本号作为来源证据。
- 取包内 `dist/` 目录下的 UMD 构建 dagre.min.js（顶层 `var dagre=(...)` 全局绑定，无 `export`）：可直接 `<script>` 内联；暴露 `dagre.graphlib.Graph` 与 `dagre.layout`，API 与 0.8.5 时代一致。
- 渲染 / DOI / 卡片 / 交互全部由本仓库 `render_html.py` 自定义——dagre 只负责"坐标"这一易维护痛点。

## 刷新方式

`$SKILL_ROOT` 是本 SKILL.md 所在目录的绝对路径（定义见 [SKILL.md](../SKILL.md) 的 Quick start）。

```bash
cd "$SKILL_ROOT/viz"
npm pack @dagrejs/dagre@3.1.3        # 得到 dagrejs-dagre-3.1.3.tgz
tar xzf dagrejs-dagre-3.1.3.tgz
cp package/dist/dagre.min.js dagre.vendor.js
```

刷新后重跑 `PYTHONPATH="$SKILL_ROOT" python3 -m viz.cli` 生成样例，并跑
`node "$SKILL_ROOT/viz/verify_geometry.mjs"` 复核零重叠 / 零裁切。

## 为什么不 `import @dagrejs/dagre`（ESM）？

生成的 HTML 需要 `file://` 双击即可打开、且不依赖本地 dev server / bundler。
UMD 全局构建内联进 HTML 后满足"自包含、可离线、可双击"的发布约束
（spec 边界：安装态只携带 skill 目录，投影器与模板随 skill 发布）。
运行时仍是正版 dagre，只是以 vendored UMD 形式随包发布。

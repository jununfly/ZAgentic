"""zj-dp-driven §6 R7 — 交互式 HTML 卡片视图（Phase-4b，Mermaid 后端 + 原生 JS）。

Design baseline: docs/designs/zj-dp-driven-skill-design.md §6 R7 / §8。

Architecture (选型 A，见 references/dp_driven-viz.md):
* **Mermaid 仍是图与语义的唯一呈现**：图体直接复用 `dp_driven_viz.render()`（R1–R6 已定稿），
  浏览器端由 mermaid.js 渲染成可点击 SVG。本模块**不做布局**、**不 vendor 布局引擎**——
  本模块不做布局引擎 vendor，保持实现独立（不镜像任何外部 viz 形状）。
* **node IR 快照**：`dp_driven_viz.build_node_ir()` 的产物以 JSON 内嵌进单文件，
  key 与 Mermaid 节点 id 一一对应；点击 SVG 节点 → 查 IR → 渲染右区卡片。
* **零回写**（invariant 10 延伸）：IR/HTML 是**生成时快照**，从不写回 carrier、从不回连 CLI。
  时效语义 = 重跑 `viz` 即重生成。

Mermaid JS 加载两模式（离线分发诉求见 §5.4 / 决策 2）：
* `assets="cdn"`（默认）：浏览器打开时按需取官方 ESM（仓库零体积）。
* `assets="inline"`：把调用方提供的 mermaid ESM **文本**经 JSON 字符串内嵌，运行时用
  Blob + 动态 import 装载 —— 完全自包含、可离线双击打开。

Invariants honored:
* **read-only + deterministic**（同 render()，§3.1）：只读派生 API；同 (model.data, now,
  assets, js_text) ⇒ 字节相等输出（JSON `sort_keys=True`，Python 侧无 wall-clock）。
* **blocked/expired 显示皆来自派生视图**（§3.2 / §4.4）：`node_view` / `claim_owner(epoch=)`。
* **XSS-safe 卡片**：卡片内容一律经 DOM `textContent` 写入，绝不把模型数据拼进 innerHTML。
"""

from __future__ import annotations

import html as _html
import json

from dp_driven_model import DpDriven, DpDrivenError
from dp_driven_viz import build_node_ir, default_html_path, render

# Mermaid official CDN ESM path (v11). Only emitted in assets="cdn" mode.
MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"

_STYLE = """
:root { color-scheme: light; }
body { margin: 0; font: 14px/1.5 -apple-system, "Segoe UI", sans-serif; color: #0f172a;
       display: flex; height: 100vh; }
#graph { flex: 1 1 auto; position: relative; overflow: hidden; padding: 0; }
#card { flex: 0 0 340px; overflow: auto; border-left: 1px solid #d0d7de; padding: 14px;
        background: #f6f8fa; }
#card h3 { margin: 0 0 8px; font-size: 15px; }
#card dl { margin: 0; }
#card dt { font-weight: 600; color: #57606a; margin-top: 8px; font-size: 12px; }
#card dd { margin: 0; word-break: break-all; }
#card .hint { color: #57606a; }
#card .badge { display: inline-block; padding: 1px 6px; border-radius: 8px;
               background: #dafbe1; color: #1a7f37; font-size: 12px; margin-left: 6px; }
svg .node { cursor: pointer; }
svg .cluster rect { cursor: pointer; }
#canvas { transform-origin: 0 0; will-change: transform; padding: 12px; }
#toolbar { position: absolute; top: 10px; left: 10px; display: flex; gap: 8px;
           align-items: center; background: #fff; border: 1px solid #d0d7de;
           border-radius: 8px; padding: 4px 6px; }
#toolbar .zoom-ctl { display: flex; gap: 4px; align-items: center; }
#toolbar button { border: 1px solid #d0d7de; background: #f6f8fa; border-radius: 6px;
                  min-width: 28px; height: 28px; cursor: pointer; font-size: 14px; }
#toolbar button.active { background: #0f172a; color: #fff; border-color: #0f172a; }
#toolbar .zoom-label { min-width: 48px; text-align: center; }
#toolbar .zoom-cap { color: #57606a; font-size: 12px; margin: 0 2px; }
#graph.hand { cursor: grab; }
#graph.hand.dragging { cursor: grabbing; }
#graph.hand svg .node, #graph.hand svg .cluster rect { cursor: grab; }
#graph.hand.dragging svg .node, #graph.hand.dragging svg .cluster rect { cursor: grabbing; }
""".lstrip()

# Vanilla JS: click delegation on the rendered SVG → lookup in the embedded IR →
# right-region card built with textContent only (never innerHTML with model data).
_JS = """
(function () {
  var IR = JSON.parse(document.getElementById("dp-ir").textContent);
  var card = document.getElementById("card");

  function nodeKey(g) {
    var id = g.getAttribute("data-id") || g.getAttribute("data-Id");
    if (id && IR[id]) return id;
    var m = (g.id || "").match(/^(?:flowchart|chart)-(.+)-\\d+$/);
    return m && IR[m[1]] ? m[1] : null;
  }

  // Mermaid v11 不再给 <g> 写 data-id，且把 id 嵌进 `mermaid-<ts>-…` 前缀，
  // nodeKey() 两条路径都失效（issue #320）。这里渲染后把 mid 回填成 data-id，
  // nodeKey() 路径1即命中，点击逻辑不改。mid 取值锚定**封闭 IR 键集**而非
  // Mermaid 的 id 字符串格式，故不追随版本漂移：
  //   ① 优先读 Mermaid 绑定的图数据 __data__.id/.name（即我方文本里的节点名）；
  //   ② 兜底把 g.id 按 '-' 切 token 与 IR 求交（我方 mid 从不含 '-'，切分即天然词边界，
  //      避免 `T1` ⊂ `tk0_T1` 之类子串误命中；老格式 id 同样命中）。
  function resolveMid(g) {
    var d = g.__data__;
    if (d) {
      if (d.id && IR[d.id]) return d.id;
      if (d.name && IR[d.name]) return d.name;
    }
    var toks = (g.id || "").split("-");
    for (var i = 0; i < toks.length; i++) {
      if (IR[toks[i]]) return toks[i];
    }
    return null;
  }

  function backfill() {
    var svg = document.querySelector("#graph svg");
    if (!svg) return;
    svg.querySelectorAll("g.node, g.cluster").forEach(function (g) {
      if (g.getAttribute("data-id")) return;
      var k = resolveMid(g);
      if (k) g.setAttribute("data-id", k);
    });
  }

  function row(dl, label, value) {
    if (value === null || value === undefined || value === "") return;
    var dt = document.createElement("dt"); dt.textContent = label;
    var dd = document.createElement("dd"); dd.textContent = String(value);
    dl.appendChild(dt); dl.appendChild(dd);
  }

  function showCard(n) {
    card.textContent = "";
    var h = document.createElement("h3"); h.textContent = n.label || n.mid;
    card.appendChild(h);
    if (n.claim_agent) {
      var b = document.createElement("span"); b.className = "badge";
      b.textContent = "claim: " + n.claim_agent + (n.claim_expired ? " (expired)" : "");
      h.appendChild(b);
    }
    var dl = document.createElement("dl");
    row(dl, "kind", n.kind);
    row(dl, "id", n.ref_id);
    row(dl, "plan", n.plan);
    row(dl, "display_status", n.display_status || n.status);
    if (n.shown_blocked) {
      row(dl, "blocked", "yes (derived)");
      if (n.blocked_reason) row(dl, "blocked_reason", n.blocked_reason.join(", "));
    }
    row(dl, "external_hold", n.external_hold);
    if (n.kind === "plan") row(dl, "summary", n.summary);
    row(dl, "claim_agent", n.claim_agent);
    row(dl, "md_path", n.md_path);
    row(dl, "context_md", n.context_md);
    row(dl, "memory_md", n.memory_md);
    row(dl, "memberships", n.memberships);
    if (n.overlap) row(dl, "overlap", "shared finding (\\u27f2 drawn per plan, \\u00a76 R6)");
    row(dl, "derived_from_finding", n.derived_from_finding);
    row(dl, "parent_id", n.parent_id);
    row(dl, "ref", n.ref);
    row(dl, "created_at", n.created_at);
    row(dl, "completed_at", n.completed_at);
    card.appendChild(dl);
  }

  // ── 左区 pan/zoom chrome（§6 R7 的 "pan/zoom chrome" 由未决转实现）──────────
  var graph = document.getElementById("graph");
  var canvas = document.getElementById("canvas");
  var zoomLabel = document.getElementById("zoom-reset");
  var handBtn = document.getElementById("hand-toggle");
  var view = { scale: 1, tx: 0, ty: 0, hand: false };
  var MIN = 0.2, MAX = 4, STEP = 1.2;

  function applyTransform() {
    canvas.style.transform = "translate(" + view.tx + "px," + view.ty + "px) "
                             + "scale(" + view.scale + ")";
    zoomLabel.textContent = Math.round(view.scale * 100) + "%";
  }
  function zoom(factor) {
    var s = view.scale * factor;
    view.scale = s < MIN ? MIN : (s > MAX ? MAX : s);
    applyTransform();
  }
  document.getElementById("zoom-in").addEventListener("click", function () { zoom(STEP); });
  document.getElementById("zoom-out").addEventListener("click", function () { zoom(1 / STEP); });
  zoomLabel.addEventListener("click", function () {
    view.scale = 1; view.tx = 0; view.ty = 0; applyTransform();
  });

  function setHand(on) {
    view.hand = on;
    graph.classList.toggle("hand", on);
    handBtn.classList.toggle("active", on);
  }
  handBtn.addEventListener("click", function () { setHand(!view.hand); });

  var panning = false, sx = 0, sy = 0, stx = 0, sty = 0;
  graph.addEventListener("mousedown", function (ev) {
    if (!view.hand || ev.button !== 0) return;
    panning = true; sx = ev.clientX; sy = ev.clientY; stx = view.tx; sty = view.ty;
    graph.classList.add("dragging");
    ev.preventDefault();
  });
  window.addEventListener("mousemove", function (ev) {
    if (!panning) return;
    view.tx = stx + (ev.clientX - sx);
    view.ty = sty + (ev.clientY - sy);
    applyTransform();
  });
  window.addEventListener("mouseup", function () {
    if (!panning) return;
    panning = false; graph.classList.remove("dragging");
  });

  document.getElementById("graph").addEventListener("click", function (ev) {
    if (view.hand) return;                 // 手型模式下不触发 inspect，避免拖拽误改卡片
    var g = ev.target.closest("g.node, g.cluster");
    if (!g) return;
    var id = nodeKey(g);
    if (id) showCard(IR[id]);
  });

  var hint = document.createElement("p");
  hint.className = "hint";
  hint.textContent = "Click a node or a plan frame to inspect it. "
                     + "Use the toolbar to zoom, or the hand tool to pan.";
  card.appendChild(hint);

  window.__dpBackfill = backfill;   // boot() 在 mermaid.run() resolve 后调用一次
})();
""".lstrip()


def _embed_json(obj) -> str:
    r"""Deterministic JSON for inline <script> embedding. `</` is neutralized to `<\/`
    (a legal JSON escape that parses back to `</`) so no embedded value can terminate
    the script element early."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def render_html(model: DpDriven, *, now: int | None = None,
                assets: str = "cdn", mermaid_js: str | None = None,
                cdn_url: str = MERMAID_CDN_URL) -> str:
    """Return a self-contained single-file HTML viewer for the DP state graph (§6 R7).

    * `now` — epoch seconds injected into `build_node_ir` so expired claims (§4.4)
      render as paused. No wall clock is read here (deterministic-output discipline).
    * `assets="cdn"` — module `import` of `cdn_url`; needs network when the file opens.
      (CLI restricts the value via argparse choices, so anything not "inline" is cdn.)
    * `assets="inline"` — embed `mermaid_js` text, load via Blob URL; fully offline.
      Missing text → DpDrivenError E_VIZ_ASSETS (CLI exit 2).
    """
    if assets == "inline" and mermaid_js is None:
        raise DpDrivenError("E_VIZ_ASSETS", "assets=inline 需要 mermaid_js 文本")

    mermaid_text = render(model, epoch=now)      # R1–R6 truth for the graph body — SAME clock as the IR below
    ir = build_node_ir(model, epoch=now)          # click payload snapshot (id-aligned)
    title = model.data["meta"].get("destination") or "zj-dp-driven graph"

    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{_html.escape(title)} · DP-driven</title>",
        "<style>", _STYLE, "</style>",
        "</head>",
        "<body>",
        # One part so the escaped render() text is byte-exact inside <pre> — the JS
        # hands this same text to mermaid.run(); no extra newlines around the graph.
        '<div id="graph"><div id="canvas"><pre class="mermaid">'
        + _html.escape(mermaid_text, quote=False)
        + '</pre></div>'
        '<div id="toolbar">'
        '<span class="zoom-ctl"><span aria-hidden="true">&#128269;</span>'
        '<span class="zoom-cap">缩放</span>'
        '<button id="zoom-out" type="button" title="缩小">&#8722;</button>'
        '<button id="zoom-reset" type="button" class="zoom-label" '
        'title="重置为 100%">100%</button>'
        '<button id="zoom-in" type="button" title="放大">+</button></span>'
        '<button id="hand-toggle" type="button" title="按住左键拖拽平移">'
        '&#9995; 手型</button>'
        '</div></div>',
        '<aside id="card"></aside>',
        '<script type="application/json" id="dp-ir">',
        _embed_json(ir),
        "</script>",
    ]
    if assets == "inline":
        parts += ['<script type="application/json" id="mermaid-js">',
                  _embed_json(mermaid_js), "</script>"]

    if assets == "cdn":
        loader = (f"import mermaid from {_embed_json(cdn_url)};\n"
                  "boot(mermaid);")
    else:
        loader = (
            'var src = JSON.parse(document.getElementById("mermaid-js").textContent);\n'
            "var blob = new Blob([src], { type: \"text/javascript\" });\n"
            "import(URL.createObjectURL(blob)).then(function (mod) { boot(mod.default); });"
        )
    boot = (
        "<script type=\"module\">\n"
        "async function boot(mermaid) {\n"
        "  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', "
        "htmlLabels: false });\n"
        "  await mermaid.run({ querySelector: 'pre.mermaid' });\n"
        "  if (window.__dpBackfill) window.__dpBackfill();\n"
        "}\n"
        f"{loader}\n"
        "</script>"
    )
    parts += [boot, "<script>", _JS, "</script>", "</body>", "</html>", ""]
    return "\n".join(parts)


def read_mermaid_js(path: str) -> str:
    """Read the user-supplied mermaid ESM file. Absence propagates as
    FileNotFoundError (CLI exit 3 — same I/O path as the carrier)."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def render_html_to_file(model: DpDriven, out_path: str, *, now: int | None = None,
                        assets: str = "cdn", mermaid_js: str | None = None,
                        cdn_url: str = MERMAID_CDN_URL) -> str:
    """Write the viewer to out_path only (§5.4 placement discipline). Returns path."""
    text = render_html(model, now=now, assets=assets, mermaid_js=mermaid_js,
                       cdn_url=cdn_url)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


__all__ = ["MERMAID_CDN_URL", "default_html_path", "render_html", "render_html_to_file",
           "read_mermaid_js"]

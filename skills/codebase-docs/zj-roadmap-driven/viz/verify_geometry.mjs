#!/usr/bin/env node
// 几何校验：加载 viz 生成的真实 HTML，用 DOM 桩跑其内嵌 JS 运行时（含 vendored dagre），
// 对每个焦点跑 render()，解析生成的 SVG，校验：
//   1) 节点矩形零重叠  2) 零裁切（均在 svg 边界内）  3) 复合节点（其余 N 项）在边界内
//   4) 展开态（点击「其余 N 项」）同样零重叠零裁切
// 这是对「dagre 确定性分层 + 自研渲染」落地质量的硬校验，与 Python 逻辑测试互补。
import { readFileSync } from "node:fs";

const htmlPath = process.argv[2];
if (!htmlPath) { console.log("usage: node verify_geometry.mjs <generated.html>"); process.exit(2); }
const html = readFileSync(htmlPath, "utf8");

// 抽取两段 <script>：dagre 构建 + 运行时
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const dagreSrc = scripts.find((s) => s.includes("var dagre="));
const runtimeSrc = scripts.find((s) => s.includes("const GRAPH ="));
if (!dagreSrc || !runtimeSrc) { console.log("FAIL: 找不到 dagre 或运行时脚本"); process.exit(1); }

// DOM 桩
const elements = new Map();
function makeEl(id) {
  return {
    id, value: "50", textContent: "", innerHTML: "", style: {},
    dataset: {}, classList: { add() {}, remove() {}, toggle() { return false; }, contains() { return false; } },
    addEventListener() {}, appendChild() {}, querySelectorAll() { return []; }, querySelector() { return null; },
  };
}
function getEl(id) { if (!elements.has(id)) elements.set(id, makeEl(id)); return elements.get(id); }
const document = {
  getElementById: (id) => getEl(id),
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: () => makeEl("dyn"),
};
const window = { addEventListener() {} };

const vm = await import("node:vm");
const sandbox = { document, window, console, Math, JSON, Array, Object, Set, String, Number, isNaN, structuredClone };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(dagreSrc, sandbox, { filename: "dagre.js" });

// 解析真实 GRAPH（占位 __GRAPH__ 已被实际 JSON 替换），预置 focus 为合法节点 id，避免初始 render 用错焦点。
const graphMatch = runtimeSrc.match(/const GRAPH = (\{[\s\S]*?\});\s*\nconst ENVELOPE/);
const GRAPH = graphMatch ? JSON.parse(graphMatch[1]) : null;
if (!GRAPH) { console.log("FAIL: 无法解析 GRAPH"); process.exit(1); }
const fociAll = Object.keys(GRAPH.nodes).sort();
elements.set("focus", makeEl("focus"));
elements.get("focus").value = fociAll[0];

const hook = "\n;globalThis.__render=render; globalThis.__setExpanded=function(v){expanded=v; render();};";
const fullRuntime = runtimeSrc + hook;
try {
  vm.runInContext(fullRuntime, sandbox, { filename: "runtime.js" });
} catch (e) {
  console.log("FAIL: 运行时执行错误: " + e.message);
  console.log(e.stack ? e.stack.split("\n").slice(0, 4).join("\n") : "");
  process.exit(1);
}

const focusEl = getEl("focus");
const dagEl = getEl("dag");

function checkGeom(label) {
  const svg = dagEl.innerHTML;
  const svgDims = svg.match(/<svg width="(\d+)" height="(\d+)"/);
  if (!svgDims) { console.log(`${label}: 无 SVG 尺寸`); return false; }
  const W = +svgDims[1], H = +svgDims[2];
  const rects = [...svg.matchAll(/<rect class="nbox[^"]*" x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"/g)]
    .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
  let clip = 0, overlap = 0;
  for (const r of rects) if (r.x < 0 || r.y < 0 || r.x + r.w > W || r.y + r.h > H) clip++;
  for (let i = 0; i < rects.length; i++)
    for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) overlap++;
    }
  const comp = svg.match(/class="composite" x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"/);
  let compIn = true;
  if (comp) { const x = +comp[1], y = +comp[2], w = +comp[3], h = +comp[4]; compIn = (x >= 0 && y >= 0 && x + w <= W && y + h <= H); }
  const ok = clip === 0 && overlap === 0 && compIn;
  console.log(`${label}: 节点=${rects.length} 裁切=${clip} 重叠=${overlap} 复合节点界内=${compIn} W=${W} H=${H} ${ok ? "OK" : "FAIL"}`);
  return ok;
}

let allOk = true;
const foci = fociAll;
for (const f of foci) {
  focusEl.value = f;
  sandbox.__render();
  if (!checkGeom(`焦点 ${f}`)) allOk = false;
}
// 展开态：取一个有复合节点（rest 非空）的焦点，展开后校验
const someFocus = foci.find((f) => {
  focusEl.value = f; sandbox.__render();
  return dagEl.innerHTML.includes("其余") || dagEl.innerHTML.includes("收起");
});
if (someFocus) {
  focusEl.value = someFocus; sandbox.__render();
  sandbox.__setExpanded(true);
  if (!checkGeom(`焦点 ${someFocus} 展开态`)) allOk = false;
  sandbox.__setExpanded(false);
}

console.log(allOk ? "\nALL_OK: 全焦点零重叠零裁切，复合节点界内" : "\nFAIL: 存在几何问题");
process.exit(allOk ? 0 : 1);

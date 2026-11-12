#!/usr/bin/env node
// C::10 guard: the local DAG and the info cards must share ONE DOI ordering.
// Loads the real generated HTML with the same DOM stub as verify_selection.mjs,
// then checks that the DAG's node insertion order is a stable subsequence of
// the card order under the shared rankByDoi() comparator.
import { readFileSync } from "node:fs";

const [htmlPath, casesPath] = process.argv.slice(2);
if (!htmlPath || !casesPath) {
  console.log("usage: node verify_ordering.mjs <generated.html> <cases.json>");
  process.exit(2);
}
const html = readFileSync(htmlPath, "utf8");
const cases = JSON.parse(readFileSync(casesPath, "utf8")).cases;
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const dagreSrc = scripts.find((s) => s.includes("var dagre="));
const runtimeSrc = scripts.find((s) => s.includes("const GRAPH ="));
if (!dagreSrc || !runtimeSrc) {
  console.log("FAIL: cannot find dagre or runtime script");
  process.exit(1);
}

const elements = new Map();
function makeEl(id) {
  return {
    id, value: "50", textContent: "", innerHTML: "", style: {}, dataset: {},
    classList: { add() {}, remove() {}, toggle() { return false; }, contains() { return false; } },
    addEventListener() {}, appendChild() {}, querySelectorAll() { return []; },
    querySelector() { return null; },
  };
}
function getEl(id) {
  if (!elements.has(id)) elements.set(id, makeEl(id));
  return elements.get(id);
}
const document = {
  getElementById: getEl, querySelector: () => null, querySelectorAll: () => [],
  createElement: () => makeEl("dyn"),
};
const window = { addEventListener() {} };
const vm = await import("node:vm");
const sandbox = { document, window, console, Math, JSON, Array, Object, Set, String, Number, isNaN, structuredClone };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(dagreSrc, sandbox, { filename: "dagre.js" });

const graphMatch = runtimeSrc.match(/const GRAPH = (\{[\s\S]*?\});\s*\nconst ENVELOPE/);
if (!graphMatch) { console.log("FAIL: cannot parse GRAPH"); process.exit(1); }
const GRAPH = JSON.parse(graphMatch[1]);
elements.set("focus", makeEl("focus"));
elements.get("focus").value = Object.keys(GRAPH.nodes).sort()[0];

const hook = "\n;globalThis.__select=select;globalThis.__rank=rankByDoi;globalThis.__layout=layoutDAG;";
try {
  vm.runInContext(runtimeSrc + hook, sandbox, { filename: "runtime.js" });
} catch (e) {
  console.log("FAIL: runtime threw: " + e.message);
  process.exit(1);
}
const { __select: select, __rank: rank, __layout: layout } = sandbox;
if (typeof select !== "function" || typeof rank !== "function" || typeof layout !== "function") {
  console.log("FAIL: shared ordering comparator is not exposed by the runtime");
  process.exit(1);
}

let checked = 0;
for (const c of cases) {
  const res = select(c.focus, c.theta);
  const cardOrder = rank(res.shown, res);
  const dag = layout(c.focus, res, new Set());
  const dagOrder = dag.orderedKeep;
  if (!Array.isArray(dagOrder) || dagOrder.length === 0) {
    console.log(`FAIL: focus=${c.focus} theta=${c.theta} DAG exposes no orderedKeep`);
    process.exit(1);
  }
  const dagSet = new Set(dagOrder);
  const projected = cardOrder.filter((id) => dagSet.has(id));
  if (JSON.stringify(projected) !== JSON.stringify(dagOrder)) {
    console.log(`FAIL: focus=${c.focus} theta=${c.theta} card=${JSON.stringify(projected)} dag=${JSON.stringify(dagOrder)}`);
    process.exit(1);
  }
  checked += 1;
}
console.log(`OK: ${checked} (focus, theta) cases share one DOI ordering`);

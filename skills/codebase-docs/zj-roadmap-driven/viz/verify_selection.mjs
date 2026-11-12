#!/usr/bin/env node
// Cross-check the HTML runtime's select() against Python's doi.select().
// Loads the real generated HTML with the same DOM stub as verify_geometry.mjs,
// then compares the LOD map for several (focus, theta) pairs. INV::03 guard.
import { readFileSync } from "node:fs";

const [htmlPath, expectedPath] = process.argv.slice(2);
if (!htmlPath || !expectedPath) {
  console.log("usage: node verify_selection.mjs <generated.html> <expected.json>");
  process.exit(2);
}
const html = readFileSync(htmlPath, "utf8");
const expected = JSON.parse(readFileSync(expectedPath, "utf8"));
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
const GRAPH = graphMatch ? JSON.parse(graphMatch[1]) : null;
if (!GRAPH) { console.log("FAIL: cannot parse GRAPH"); process.exit(1); }
elements.set("focus", makeEl("focus"));
elements.get("focus").value = Object.keys(GRAPH.nodes).sort()[0];

const hook = "\n;globalThis.__select=select;";
try {
  vm.runInContext(runtimeSrc + hook, sandbox, { filename: "runtime.js" });
} catch (e) {
  console.log("FAIL: runtime threw: " + e.message);
  process.exit(1);
}
const select = sandbox.__select;
if (typeof select !== "function") {
  console.log("FAIL: select() is not exposed by the runtime");
  process.exit(1);
}

let checked = 0;
for (const c of expected.cases) {
  const got = select(c.focus, c.theta).lod || {};
  const want = c.lod;
  const keys = new Set([...Object.keys(got), ...Object.keys(want)]);
  const diff = [...keys].filter((k) => got[k] !== want[k]).sort();
  if (diff.length) {
    const detail = diff.slice(0, 8).map((k) => [k, want[k], got[k]]);
    console.log(`FAIL: focus=${c.focus} theta=${c.theta} lod diff=${JSON.stringify(detail)}`);
    process.exit(1);
  }
  checked += 1;
}
console.log(`OK: ${checked} (focus, theta) selections match Python doi.select()`);

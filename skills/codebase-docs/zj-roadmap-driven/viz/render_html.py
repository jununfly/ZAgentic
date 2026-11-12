#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 投影：把 view-ir + 归一化图渲染成自包含 HTML。

产物是**单一 HTML 文件**：内联 vendored @dagrejs/dagre（UMD）做确定性分层布局，
JS 运行时做 DOI 选择、卡片 LOD、拖拽平移、点击聚焦、展开/折叠、θ 滑块、复位视图。
布局原语来自真实 npm 依赖；渲染 / DOI / 卡片 / 交互全部本仓库自定义。

读取端：本模块只 *消费* 输入的路线图数据，绝不回写 carrier（只读投影）。
"""
from __future__ import annotations

from .authority import AUTHORITY_ENVELOPE
import json
from pathlib import Path

from .context import unchecked_status
from .dependency import build_edge_meta

HERE = Path(__file__).resolve().parent
DAGRE_JS = (HERE / "dagre.vendor.js").read_text(encoding="utf-8")

# 主视图内嵌的展示字段白名单：carrier 的 context / traces 等侧载字段绝不进 GRAPH，
# 否则「上下文条目增长时主视图字节不变」这条 S4 硬判据会失效。
DISPLAY_FIELDS = (
    "id", "label", "status", "mode", "parent", "rounds",
    "notes", "decisions", "exit_criteria", "budget",
)

# ---------------------------------------------------------------------------
# HTML 模板（CSS + 结构 + JS 运行时）。__DAGRE__ / __GRAPH__ / __ENVELOPE__ 占位。
# 运行时 JS 移植自已验证原型（dagre 坐标 + 自研 DOI/卡片/交互），仅把硬编码 DATA 泛化为内嵌 GRAPH。
# ---------------------------------------------------------------------------
HTML_TEMPLATE = r"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
  :root{ --bg:#f7f8fa; --panel:#ffffff; --ink:#1f2329; --muted:#6b7280; --line:#e5e7eb;
         --focus:#d9480f; --block:#b91c1c; --sib:#2563eb; --debt:#7c3aed; --ok:#15803d;
         --chip:#eef2ff; --warn:#fef3c7; }
  *{box-sizing:border-box}
  body{margin:0;font:13px/1.5 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg)}
  .wrap{max-width:1180px;margin:0 auto;padding:14px}
  .anchor{display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin-bottom:12px}
  .anchor h1{font-size:14px;margin:0 12px 0 0;font-weight:700}
  .anchor select{font:13px inherit;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:#fff;max-width:420px}
  .anchor .grp{display:flex;gap:6px;align-items:center}
  .anchor button{font:12px inherit;padding:4px 10px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer}
  .anchor button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
  .anchor input[type=range]{width:130px}
  .stat{font-size:11px;color:var(--muted);padding:3px 8px;background:var(--chip);border-radius:6px}
  .stat.warn{background:var(--warn);color:#92400e}
  .stale{background:#fdecec;color:#991b1b;border:1px solid #f3c4c4;border-radius:10px;padding:8px 12px;margin-bottom:12px;font-size:12px}
  .edge-info{margin-top:8px;font-size:11px;color:var(--muted);background:#fafafa;border:1px dashed var(--line);border-radius:8px;padding:6px 8px}
  .edge-hit{cursor:pointer}
  .edge-hit:hover{stroke-width:3}
  .layout{display:flex;gap:12px;align-items:flex-start;position:relative}
  .dag{flex:1 1 auto;min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px}
  .dag-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:10px}
  .dag-head h2,.sidebar h2{font-size:12px;margin:0;color:var(--muted);font-weight:700;letter-spacing:.04em;text-transform:uppercase}
  .dag-head button{font:12px inherit;padding:3px 10px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer}
  .dag-viewport{position:relative;height:660px;overflow:hidden;border:1px solid var(--line);border-radius:10px;background:#fbfcfe;cursor:grab;touch-action:none;user-select:none}
  .dag-viewport.grabbing{cursor:grabbing}
  .dag-canvas{position:absolute;top:0;left:0;transform:translate(0,0);transform-origin:0 0;will-change:transform}
  .dag-canvas svg{display:block}
  .sidebar{flex:0 0 364px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px;max-height:744px;overflow:auto;transition:flex-basis .18s ease,padding .18s ease,opacity .18s ease,margin .18s ease}
  .sidebar.collapsed{flex-basis:0;padding:0;border:none;opacity:0;overflow:hidden;margin:0}
  .sidebar-handle{flex:0 0 26px;align-self:stretch;min-height:60px;writing-mode:vertical-rl;text-orientation:upright;letter-spacing:3px;background:var(--panel);border:1px solid var(--line);border-radius:10px;cursor:pointer;color:var(--muted);font-size:12px;display:flex;align-items:center;justify-content:center}
  .sidebar-handle:hover{color:var(--ink);border-color:#c9ced6}
  .card{border:1px solid var(--line);border-radius:10px;padding:9px 11px;margin-bottom:8px;background:#fff}
  .card.focus{border-color:var(--focus);box-shadow:0 0 0 2px #ffd8c2}
  .card .hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .card .id{font-weight:700;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
  .card .lab{font-weight:600}
  .badge{font-size:10px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
  .b-prog{background:#fff4ed;color:var(--focus);border-color:#f3c9b3}
  .b-done{background:#ecfdf3;color:var(--ok);border-color:#b6e8c8}
  .b-pend{background:#f1f5f9;color:var(--muted);border-color:var(--line)}
  .b-debt{background:#f5f0ff;color:var(--debt);border-color:#d9c8f5}
  .b-sib{background:#eef4ff;color:var(--sib);border-color:#c7dbff}
  .b-block{background:#fdecec;color:var(--block);border-color:#f3c4c4}
  .muted{color:var(--muted);font-size:11px}
  .kv{margin-top:5px;font-size:11px}
  .kv b{color:var(--muted);font-weight:600}
  .notes{margin-top:6px;white-space:pre-wrap;font-size:12px;background:#fafafa;border:1px solid var(--line);border-radius:8px;padding:6px 8px;max-height:120px;overflow:auto}
  .dec{margin-top:5px;font-size:11px;border-left:3px solid var(--sib);padding:3px 8px;background:#f7faff}
  .chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:3px 10px;margin:2px 3px 2px 0;background:#fff;font-size:11px}
  .dot{width:8px;height:8px;border-radius:50%}
  .s-prog{background:var(--focus)}.s-done{background:var(--ok)}.s-pend{background:#9ca3af}
  .composite{fill:#f1f5f9;stroke:#cbd5e1;stroke-dasharray:4 3}
  .nbox{fill:#fff;stroke:var(--line)}
  .nbox.focus{stroke:var(--focus);stroke-width:2.5}
  .nbox.block{stroke:var(--block)}
  .nbox.sib{stroke:var(--sib)}
  .nbox.debt{stroke:var(--debt)}
  .node,.composite-g{cursor:pointer}
  .node:hover .nbox{stroke-width:2.5}
  .elabel{font-size:9px;fill:var(--muted)}
  .delta{margin-top:12px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
  .delta .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .pill{font-size:11px;padding:3px 9px;border-radius:8px}
  .pill.add{background:#e7f6ec;color:#15803d}.pill.chg{background:#fff4ed;color:#d9480f}.pill.stab{background:#eef2ff;color:#4338ca}
  .legend{font-size:10px;color:var(--muted);margin-top:6px}
  .nodetxt{font-size:10.5px;fill:var(--ink);font-weight:600}
  .nid{font-size:11px;fill:var(--ink);font-weight:800;font-family:ui-monospace,Menlo,Consolas,monospace}
</style>
</head><body><div class="wrap">
  <div id="stale-banner" class="stale" hidden></div>
  <div class="anchor">
    <h1 id="ptitle"></h1>
    <div class="grp">焦点 <select id="focus"></select></div>
    <div class="grp">θ <input id="theta" type="range" min="0" max="100" value="50"><span id="thv" class="muted">0.50</span></div>
    <div class="grp">
      <button data-t="75">概览</button>
      <button data-t="45" class="on">邻域</button>
      <button data-t="20">展开</button>
    </div>
    <span class="stat" id="s-budget">预算 0/40 行</span>
    <span class="stat warn" id="s-compress">压缩 0 项</span>
    <span class="stat" id="s-env"></span>
  </div>
  <div class="layout">
    <div class="dag">
      <div class="dag-head"><h2>局部 DAG（DOI 裁剪 · 确定性分层 · 可拖拽平移）</h2><button id="reset-pan">复位视图</button></div>
      <div class="dag-viewport" id="dag-viewport"><div class="dag-canvas" id="dag-canvas"><div id="dag"></div></div></div>
      <div class="legend">实线箭头 = blocks（顺序依赖，X 完成才能做 Y）。节点描边：<b style="color:var(--focus)">焦点</b>/<b style="color:var(--block)">阻塞前驱</b>/<b style="color:var(--sib)">同父高耦合</b>/<b style="color:var(--debt)">含债务</b>。远端子树折成复合节点。<b>左键按住拖拽平移；点击节点=设为焦点；点击「其余 N 项」=展开折叠项，点击「收起」=折叠。</b></div>
    </div>
    <div class="sidebar" id="sidebar"><h2>信息卡片（三级 LOD · 40 行阅读预算）</h2><div id="cards"></div></div>
    <div class="sidebar-handle" id="sidebar-handle" title="展开/收起卡片侧栏">收起</div>
  </div>
  <div class="delta"><h2 style="font-size:12px;margin:0 0 8px;color:var(--muted)">边回溯 / 上下文侧载</h2>
    <div id="edge-info" class="edge-info">点击 blocks 边可回溯 edge id 与来源；上下文条目由 --context 侧载为独立 JSON。</div>
    <details><summary>上下文包入口（恒定，不随条目数变化）</summary>
      <div class="legend">单节点的决策、trace、边、证据引用与影响闭包打包为侧载数据；主视图不内嵌条目、不显示条目数，展开时显示上下文来源、BFS 半径与条目数。</div>
    </details>
  </div>
  <div class="delta"><h2 style="font-size:12px;margin:0 0 8px;color:var(--muted)">增量重入（Δ 提示）</h2>
    <div class="row" id="delta"></div>
    <div class="legend" id="delta-note"></div>
  </div>
</div>
<script>__DAGRE__</script>
<script>
const GRAPH = __GRAPH__;
const ENVELOPE = __ENVELOPE__;
const EDGE_META = __EDGE_META__;
const DELTA = __DELTA__;
const EDGE_BY_PAIR = {};
EDGE_META.forEach(m=>{ EDGE_BY_PAIR[m.from+"|"+m.to]=m; });
const W = {T1:0.30,T2:0.25,T3:0.15,T4:0.15,T5:0.10,T6:0.05};
const BUDGET = 40, COST = {L2:4,L1:2,L0:1};
const NODE_H = 46, V_GAP = 18, H_GAP = 44;
const DEBT_HIGH=["风险","risk","缺口","gap","缺失","不一致","返工","错误"];
const DEBT_MED=["todo","待","sweep","清理","核对","跟进","补","未覆盖","隐患"];

// ---- 图结构（blocks 邻接；edges 已过滤为 blocks）----
const nodes = GRAPH.nodes, edges = GRAPH.edges, debt = GRAPH.debt;
const adj = {}, pred = {}, succ = {};
Object.keys(nodes).forEach(id=>{adj[id]=[];pred[id]=new Set();succ[id]=new Set();});
edges.forEach(e=>{ const f=e.from, t=e.to; if(f in nodes && t in nodes){ adj[f].push(t); adj[t].push(f); pred[t].add(f); succ[f].add(t);} });

function bfsHop(src){ const dist={},q=[[src,0]]; dist[src]=0;
  while(q.length){const [u,d]=q.shift(); (adj[u]||[]).forEach(v=>{ if(dist[v]===undefined){dist[v]=d+1;q.push([v,d+1]);}});} return dist; }
function revBFS(src){ const depth={},q=[[src,0]]; while(q.length){const [u,d]=q.shift(); pred[u].forEach(p=>{ if(depth[p]===undefined){depth[p]=d+1;q.push([p,d+1]);}});} return depth; }

function recency(n){ let b = n.status==="in_progress"?0.85 : n.status==="blocked"?0.6 : n.status==="completed"?0.30 : 0.15;
  return Math.min(1, b + Math.min(0.10, 0.02*(n.rounds||1))); }

function doi(n, focus, hop, pdepth){
  const id=n.id; if(id===focus) return 1.0;
  const T1 = 1/(1+(hop[id]??99));
  const T2 = (pdepth[id]!==undefined)? Math.max(0.2, 1-0.2*(pdepth[id]-1)) : 0;
  const T3 = (n.parent===nodes[focus].parent && n.parent!==null)?1.0 : (n.layer===nodes[focus].layer?0.4:0);
  const T4 = debt[id].score;
  const T5 = recency(n);
  const T6 = (n.status==="completed" && pdepth[id]===undefined)? -1 : 0;
  return Math.max(0, Math.min(1, W.T1*T1+W.T2*T2+W.T3*T3+W.T4*T4+W.T5*T5+W.T6*T6));
}

function select(focus, theta){
  const hop=bfsHop(focus), pdepth=revBFS(focus), fp=nodes[focus].parent, fl=nodes[focus].layer;
  const scores=Object.values(nodes).map(n=>({id:n.id,d:doi(n,focus,hop,pdepth)}));
  const byId=Object.fromEntries(scores.map(s=>[s.id,s]));
  const mandatory=new Set([focus]);
  pdepth && Object.keys(pdepth).forEach(p=>mandatory.add(p));
  (succ[focus]||[]).forEach(s=>mandatory.add(s));
  Object.keys(debt).forEach(id=>{ if(debt[id].level==="high") mandatory.add(id); });
  let tp=nodes[focus].parent; const tseen=new Set();
  while(tp && nodes[tp] && !tseen.has(tp)){ mandatory.add(tp); tseen.add(tp); tp=nodes[tp].parent; }
  const lod={};
  scores.forEach(({id,d})=>{ let L;
    if(mandatory.has(id)){ L = (id===focus)?"L2":"L1"; }
    else { L = d>=theta ? "L2" : "COMPRESSED"; }
    lod[id]=L; });
  let used=0; const shown=[];
  [...mandatory].forEach(id=>{ used+=COST[lod[id]]; shown.push(id); });
  // 与 Python doi.select 同源：整桶塞入，首个塞不下的桶及其后全部 COMPRESSED。
  const candList=scores.filter(s=>!mandatory.has(s.id)&&lod[s.id]==="L2").sort((a,b)=>b.d-a.d);
  const byD=new Map();
  candList.forEach(s=>{ const k=s.d.toFixed(12); if(!byD.has(k)) byD.set(k,[]); byD.get(k).push(s.id); });
  let exhausted=false;
  [...byD.keys()].sort((a,b)=>Number(b)-Number(a)).forEach(k=>{
    const ids=byD.get(k);
    if(!exhausted && used+COST.L0*ids.length<=BUDGET){ ids.forEach(id=>{lod[id]="L0"; used+=COST.L0; shown.push(id);}); }
    else { exhausted=true; ids.forEach(id=>{lod[id]="COMPRESSED";}); }
  });
  // 两轮整桶升级；首个升不动的桶即停手，禁止更低 d 节点越级。
  [["L0","L1",COST.L1-COST.L0],["L1","L2",COST.L2-COST.L1]].forEach(([from,to,step])=>{
    const byD2=new Map();
    Object.keys(lod).forEach(id=>{
      if(lod[id]===from && !(to==="L2"&&mandatory.has(id))){
        const k=byId[id].d.toFixed(12); if(!byD2.has(k)) byD2.set(k,[]); byD2.get(k).push(id);
      }
    });
    const keys=[...byD2.keys()].sort((a,b)=>Number(b)-Number(a));
    for(const k of keys){ const ids=byD2.get(k);
      if(used+step*ids.length<=BUDGET){ ids.forEach(id=>{lod[id]=to; used+=step;}); }
      else break; }
  });
  const compressed=Object.keys(lod).filter(id=>lod[id]==="COMPRESSED");
  const thetaFolded=compressed.filter(id=>byId[id].d<theta).length;
  const budgetFolded=compressed.length-thetaFolded;
  const budgetOverflow=Math.max(0,used-BUDGET);
  return {shown,lod,scores,byId,used,mandatory,pdepth,compressed,thetaFolded,budgetFolded,budgetOverflow,hop,fp,fl};
}

// ---- 局部 DAG 布局：委托 dagre（Sugiyama 确定性分层）----
function wrapLabel(s, maxChars){ s=(s||""); if(!s) return [""]; if(s.length<=maxChars) return [s];
  const out=[]; for(let i=0;i<s.length;i+=maxChars) out.push(s.slice(i,i+maxChars)); return out; }
function nodeWidth(id, res){ return Math.max(104, 84 + Math.round((res && res.byId[id] ? res.byId[id].d : 0) * 46)); }
function nodeLines(id, w){ const n=nodes[id]; const maxC=Math.max(6, Math.floor((w-12)/11)); return wrapLabel(n.label, maxC); }
function nodeHeight(lines){ return NODE_H + (lines.length-1)*14; }
// C::10 / INV::03: ONE ordering comparator for both the DAG and the cards.
// mandatory first, then DOI descending. Never fork this into a second sort.
function rankByDoi(ids, res){ return [...ids].sort((a,b)=>{
  const ma=res.mandatory.has(a)?0:1, mb=res.mandatory.has(b)?0:1; if(ma!==mb) return ma-mb;
  return res.byId[b].d-res.byId[a].d; }); }
// C::01: one partition helper, shared shape with the Mermaid COMPOSITE line.
function partitionRest(ids){ const m=new Map();
  ids.forEach(id=>{ const p=(nodes[id]&&nodes[id].parent)||"根"; m.set(p,(m.get(p)||0)+1); });
  return [...m.entries()].sort((a,b)=>String(a[0]).localeCompare(String(b[0]))); }
function layoutDAG(focus, res, expSet){
  const nbhd=new Set([focus]);
  (res.pdepth?Object.keys(res.pdepth):[]).forEach(p=>nbhd.add(p));
  (succ[focus]||[]).forEach(s=>nbhd.add(s));
  (adj[focus]||[]).forEach(n=>nbhd.add(n));
  const exp=expSet||new Set();
  const keepBase=rankByDoi([...nbhd].filter(id=>res.shown.includes(id)), res);
  const keepAll=keepBase.concat(rankByDoi([...exp].filter(id=>res.shown.includes(id)), res));
  const kset=new Set(keepAll);
  const rest=res.shown.filter(id=>!kset.has(id)).concat([...nbhd].filter(id=>!res.shown.includes(id)));
  const subPred={}, subSucc={}; keepAll.forEach(id=>{subPred[id]=new Set();subSucc[id]=new Set();});
  edges.forEach(e=>{ if(e.type==="blocks"&&kset.has(e.from)&&kset.has(e.to)){ subSucc[e.from].add(e.to); subPred[e.to].add(e.from);} });
  const g=new dagre.graphlib.Graph({directed:true}).setGraph({rankdir:"TB", nodesep:V_GAP, ranksep:H_GAP, marginx:20, marginy:20});
  g.setDefaultEdgeLabel(()=>({}));
  const lines={}, h={}, w={};
  keepAll.forEach(id=>{ w[id]=nodeWidth(id,res); lines[id]=nodeLines(id,w[id]); h[id]=nodeHeight(lines[id]); g.setNode(id,{width:w[id], height:h[id]}); });
  edges.forEach(e=>{ if(e.type==="blocks"&&kset.has(e.from)&&kset.has(e.to)) g.setEdge(e.from,e.to); });
  dagre.layout(g);
  const pos={};
  keepAll.forEach(id=>{ const n=g.node(id); pos[id]={x:n.x-n.width/2, y:n.y-n.height/2}; });
  const gl=g.graph();
  let W_=gl.width, H_=gl.height;
  const compW=172, compH=46;
  const compX = rest.length ? W_+14 : null;
  const collapseX = (exp.size && !rest.length) ? W_+14 : null;
  if(compX!==null) W_=W_+14+compW;
  if(collapseX!==null) W_=W_+14+compW;
  if((compX!==null||collapseX!==null) && H_<100) H_=100;
  return {keep:kset, orderedKeep:keepAll, subPred, subSucc, pos, w, h, lines, rest, W_, H_, compW, compH, compX, collapseX};
}
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function txt(v){ return Array.isArray(v)? v.join("；") : String(v==null?"":v); }
function shortLabel(s,n){s=(s||"");return s.length>n?s.slice(0,n)+"…":s;}

function render(){
  const focus=document.getElementById("focus").value;
  const hop=bfsHop(focus), pdepth=revBFS(focus);
  const allD=Object.values(nodes).map(n=>({id:n.id, d:doi(n,focus,hop,pdepth)}));
  const mand=new Set([focus]); pdepth&&Object.keys(pdepth).forEach(p=>mand.add(p)); (succ[focus]||[]).forEach(s=>mand.add(s)); Object.keys(debt).forEach(id=>{ if(debt[id].level==="high") mand.add(id); });
  let tpm=nodes[focus].parent; const tseem=new Set();
  while(tpm && nodes[tpm] && !tseem.has(tpm)){ mand.add(tpm); tseem.add(tpm); tpm=nodes[tpm].parent; }
  const cand=allD.filter(s=>!mand.has(s.id)).map(s=>s.d).sort((a,b)=>a-b);
  const pct=p=> cand.length? cand[Math.min(cand.length-1, Math.floor(p*cand.length))] : null;
  const tOv=pct(0.85), tNb=pct(0.50), tEx=pct(0.15);
  const presets = (tOv!=null)? {overview:tOv, neighborhood:tNb, expand:tEx} : {overview:0.75, neighborhood:0.45, expand:0.20};
  document.querySelectorAll(".anchor button[data-t]").forEach(b=>{ const k=b.textContent.trim();
    if(k==="概览") b.dataset.t=Math.round(presets.overview*100);
    else if(k==="邻域") b.dataset.t=Math.round(presets.neighborhood*100);
    else if(k==="展开") b.dataset.t=Math.round(presets.expand*100); });
  const onBtn=document.querySelector(".anchor button[data-t].on");
  let theta = onBtn ? parseInt(onBtn.dataset.t,10)/100 : parseInt(document.getElementById("theta").value,10)/100;
  document.getElementById("theta").value=Math.round(theta*100);
  document.getElementById("thv").textContent=theta.toFixed(2);
  const res=select(focus,theta);
  const order=rankByDoi(res.shown, res);
  let html="";
  order.forEach(id=>{
    const n=nodes[id],L=res.lod[id],d=res.byId[id].d, db=debt[id];
    const cls=["card"]; if(id===focus)cls.push("focus");
    let badges=`<span class="badge b-${n.status==='in_progress'?'prog':n.status==='completed'?'done':'pend'}">${n.status}</span>`;
    if(res.pdepth[id]!==undefined) badges+=`<span class="badge b-block">阻塞前驱</span>`;
    if(n.parent===res.fp && id!==focus) badges+=`<span class="badge b-sib">同父</span>`;
    if(db.score>0) badges+=`<span class="badge b-debt">债:${db.level}</span>`;
    badges+=`<span class="badge">DOI ${d.toFixed(2)}</span><span class="badge">${n.layer}</span>`;
    if(L==="L2"){
      let body=`<div class="kv"><b>mode</b> ${n.mode||""} · <b>rounds</b> ${n.rounds??"—"} · <b>parent</b> ${n.parent??"—"}</div>`;
      if(n.notes&&n.notes.trim()) body+=`<div class="notes">${esc(n.notes)}</div>`;
      (n.decisions||[]).forEach(dc=>{ body+=`<div class="dec"><b>Q:</b> ${esc(dc.q||"")}${dc.a?` <b>A:</b> ${esc(dc.a)}`:""}${dc.note?` <i class="muted">— ${esc(dc.note)}</i>`:""}</div>`; });
      if(n.exit_criteria) body+=`<div class="kv"><b>exit:</b> ${esc(txt(n.exit_criteria))}</div>`;
      if(n.budget) body+=`<div class="kv"><b>预算:</b> ${esc(JSON.stringify(n.budget))}</div>`;
      if(db.hits.length) body+=`<div class="kv"><b>债务命中:</b> ${db.hits.join("、")}</div>`;
      html+=`<div class="${cls.join(' ')}"><div class="hd"><span class="id">${id}</span><span class="lab">${esc(n.label)}</span>${badges}</div>${body}</div>`;
    } else if(L==="L1"){
      html+=`<div class="${cls.join(' ')}"><div class="hd"><span class="id">${id}</span><span class="lab">${esc(n.label)}</span>${badges}</div>`+
        (n.notes?`<div class="muted">${esc(shortLabel(n.notes.replace(/\s+/g,' '),70))}</div>`:"")+`</div>`;
    } else {
      html+=`<div class="${cls.join(' ')}"><div class="hd"><span class="id">${id}</span><span class="lab">${esc(shortLabel(n.label,40))}</span>${badges}</div></div>`;
    }
  });
  document.getElementById("cards").innerHTML=html;
  document.getElementById("s-budget").textContent=`预算 ${res.used}/${BUDGET} 行 · 可见 ${res.shown.length}`;
  const cs=document.getElementById("s-compress");
  if(res.compressed.length){ cs.textContent=`压缩 ${res.compressed.length} 项（θ截 ${res.thetaFolded} · 预算截 ${res.budgetFolded}）`; cs.style.display=""; }
  else cs.style.display="none";
  const nbhd=new Set([focus]);
  (res.pdepth?Object.keys(res.pdepth):[]).forEach(p=>nbhd.add(p));
  (succ[focus]||[]).forEach(s=>nbhd.add(s));
  (adj[focus]||[]).forEach(n=>nbhd.add(n));
  const folded = res.shown.filter(id=>!nbhd.has(id)).concat([...nbhd].filter(id=>!res.shown.includes(id)));
  let expSet=new Set();
  if(expanded){
    folded.forEach(id=>{ if(!res.shown.includes(id)){ res.shown.push(id); res.used+=COST.L0; } res.lod[id]="L0"; });
    const fset=new Set(folded);
    res.compressed=res.compressed.filter(id=>!fset.has(id));
    res.thetaFolded=res.compressed.filter(id=>res.byId[id].d<theta).length;
    res.budgetFolded=res.compressed.length-res.thetaFolded;
    expSet=new Set(folded);
  }
  const dl=layoutDAG(focus,res,expSet);
  const SW=Math.round(dl.W_), SH=Math.round(dl.H_);
  let svg=`<svg width="${SW}" height="${SH}" viewBox="0 0 ${SW} ${SH}">`;
  svg+=`<defs><marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="#b91c1c"/></marker></defs>`;
  edges.forEach(e=>{ if(e.type==="blocks"&&dl.keep.has(e.from)&&dl.keep.has(e.to)){
    const a=dl.pos[e.from],b=dl.pos[e.to], aw=dl.w[e.from], ah=dl.h[e.from], bw=dl.w[e.to], bh=dl.h[e.to];
    const ax=a.x+aw, ay=a.y+ah/2, bx=b.x, by=b.y+bh/2;
    const em=EDGE_BY_PAIR[e.from+"|"+e.to];
    const eid=em?em.edge_id:"unknown";
    svg+=`<path class="edge-hit" data-edge="${eid}" d="M${ax},${ay} C${(ax+bx)/2},${ay} ${(ax+bx)/2},${by} ${bx},${by}" fill="none" stroke="#b91c1c" stroke-width="1.8" marker-end="url(#ar)"><title>${eid} · ${e.from} → ${e.to}</title></path>`; } });
  dl.keep.forEach(id=>{ const p=dl.pos[id],n=nodes[id], w=dl.w[id], h=dl.h[id], lines=dl.lines[id];
    const st = id===focus?"focus": res.pdepth[id]!==undefined?"block": n.parent===res.fp?"sib": debt[id].score>0?"debt":"";
    let t=`<text class="nid" x="${p.x+6}" y="${p.y+17}">${id}</text>`;
    lines.forEach((ln,i)=>{ t+=`<text class="nodetxt" x="${p.x+6}" y="${p.y+17+15+(i*14)}">${esc(ln)}</text>`; });
    svg+=`<g class="node" data-id="${id}"><rect class="nbox ${st}" x="${p.x}" y="${p.y}" width="${w}" height="${h}" rx="8"/>${t}</g>`; });
  if(dl.rest.length){ const cx2=dl.compX;
    svg+=`<g class="composite-g" data-comp="expand"><rect class="composite" x="${cx2}" y="20" width="${dl.compW}" height="${dl.compH}" rx="8"/>`+
      `<text class="nodetxt" x="${cx2+8}" y="${20+dl.compH/2+4}">其余 ${dl.rest.length} 项（${partitionRest(dl.rest).map(x=>"分区 "+x[0]+" "+x[1]+" 项").join(" · ")} · 点击展开）</text></g>`; }
  if(dl.collapseX!==null){ const cx2=dl.collapseX;
    svg+=`<g class="composite-g" data-comp="collapse"><rect class="composite" x="${cx2}" y="20" width="${dl.compW}" height="${dl.compH}" rx="8"/>`+
      `<text class="nodetxt" x="${cx2+8}" y="${20+dl.compH/2+4}">收起（点击）</text></g>`; }
  svg+=`</svg>`;
  document.getElementById("dag").innerHTML=svg;
  lastDL=dl; centerFocus();
  const D = (typeof DELTA!=="undefined" && DELTA) ? DELTA :
    {mode:"full-fallback",added:[],changed:[],removed:[],"stable-folded":0,warning:null};
  const stableN = D["stable-folded"]||0;
  document.getElementById("delta").innerHTML=
    `<span class="pill chg">变更 ${D.changed.length}</span>`+
    `<span class="pill add">新增 ${D.added.length}</span>`+
    `<span class="pill comp">移除 ${D.removed.length}</span>`+
    `<span class="pill stab">稳定折叠 ${stableN}</span>`;
  document.getElementById("delta-note").textContent=
    D.mode==="full-fallback"
      ? `全量视图（fail-closed）：${D.warning||"无 baseline"}；receipt 不进 carrier、不参与 view-ir 计算。`
      : `增量重入：added=${D.added.length} changed=${D.changed.length} removed=${D.removed.length} stable-folded=${stableN}；锚点=${(ENVELOPE.node_uid||focus)}、θ=${theta.toFixed(2)}。`;
}

const vp=document.getElementById("dag-viewport"), cv=document.getElementById("dag-canvas");
let panX=0, panY=0, dragging=false, startX=0, startY=0, lastDL=null, expanded=false;
function applyPan(){ cv.style.transform=`translate(${panX}px,${panY}px)`; }
function clampPan(){
  const vw=vp.clientWidth||0, vh=vp.clientHeight||0, cw=cv.offsetWidth||0, ch=cv.offsetHeight||0;
  if(cw<=vw) panX=(vw-cw)/2; else panX=Math.min(0, Math.max(vw-cw, panX));
  if(ch<=vh) panY=(vh-ch)/2; else panY=Math.min(0, Math.max(vh-ch, panY));
  applyPan();
}
function centerFocus(){
  if(!lastDL) return;
  const fv=document.getElementById("focus").value;
  const p=lastDL.pos[fv]; if(!p) return;
  const w=lastDL.w[fv]||90;
  const vpW=vp.clientWidth||0, vpH=vp.clientHeight||0;
  panX=vpW/2-(p.x+w/2);
  panY=vpH/2-(p.y+NODE_H/2);
  clampPan();
}
vp.addEventListener("mousedown",e=>{ dragging=true; startX=e.clientX-panX; startY=e.clientY-panY; vp.classList.add("grabbing"); e.preventDefault(); });
window.addEventListener("mousemove",e=>{ if(!dragging) return; panX=e.clientX-startX; panY=e.clientY-startY; clampPan(); });
window.addEventListener("mouseup",()=>{ if(dragging){ dragging=false; vp.classList.remove("grabbing"); } });
document.getElementById("reset-pan").addEventListener("click",centerFocus);
function showEdge(eid){
  const box=document.getElementById("edge-info");
  const m=EDGE_META.filter(x=>x.edge_id===eid)[0];
  if(!m){ box.textContent=`edge ${eid} · 无来源元数据（unknown）`; return; }
  box.textContent=`edge ${m.edge_id} · ${m.from} → ${m.to} (${m.type}) · 来源 ${m.source.carrier_stem}:edges[${m.source.index}] · evidence-ref ${m.source.evidence_ref} · rev ${m.source.carrier_revision}`;
}
document.getElementById("dag").addEventListener("click", e=>{
  const t=e.target;
  const p=(t&&t.closest)?t.closest("path[data-edge]"):null;
  if(p){ showEdge(p.getAttribute("data-edge")); return; }
  const g=(t&&t.closest)?t.closest("g"):null; if(!g) return;
  const cid=g.getAttribute("data-id");
  if(cid){ document.getElementById("focus").value=cid; render(); return; }
  const comp=g.getAttribute("data-comp");
  if(comp==="expand"){ expanded=true; render(); return; }
  if(comp==="collapse"){ expanded=false; render(); return; }
});
window.addEventListener("resize",clampPan);
const sb=document.getElementById("sidebar"), handle=document.getElementById("sidebar-handle");
handle.addEventListener("click",()=>{ const c=sb.classList.toggle("collapsed"); handle.textContent=c?"卡片":"收起"; });

const staleBox=document.getElementById("stale-banner");
if(ENVELOPE.revision_status && ENVELOPE.revision_status.stale){
  staleBox.hidden=false;
  staleBox.textContent=`STALE · 视图 revision ${ENVELOPE.revision_status.expected_revision} ≠ carrier ${ENVELOPE.revision_status.carrier_revision}；刷新命令（只写出，不执行）：${ENVELOPE.revision_status.refresh_command}`;
}
document.getElementById("ptitle").textContent=GRAPH.title||"路线图可视化";
document.getElementById("s-env").textContent=`carrier:${ENVELOPE.carrier_stem} · rev:${ENVELOPE.carrier_revision} · uid:${(ENVELOPE.node_uid)||"?"}`;
const sel=document.getElementById("focus");
Object.keys(nodes).sort().forEach(id=>{ const o=document.createElement("option"); o.value=id; o.textContent=`${id} · ${nodes[id].label}`; if(id===ENVELOPE.focus)o.selected=true; sel.appendChild(o); });
document.getElementById("theta").addEventListener("input",e=>{ document.querySelectorAll(".anchor button[data-t]").forEach(x=>x.classList.remove("on")); document.getElementById("thv").textContent=(e.target.value/100).toFixed(2); render(); });
sel.addEventListener("change",render);
document.querySelectorAll(".anchor button[data-t]").forEach(b=>b.addEventListener("click",()=>{
  document.querySelectorAll(".anchor button[data-t]").forEach(x=>x.classList.remove("on"));
  b.classList.add("on"); document.getElementById("theta").value=b.dataset.t; document.getElementById("thv").textContent=(b.dataset.t/100).toFixed(2); render(); }));
// CLI 传入固定 θ 时，打开即用该 θ（取消默认档高亮，render 改读滑块值）
if(ENVELOPE.theta!=null){ document.querySelectorAll(".anchor button[data-t]").forEach(x=>x.classList.remove("on")); document.getElementById("theta").value=Math.round(ENVELOPE.theta*100); }
render();
</script>
</body></html>"""


def render_html(graph, focus, theta=None, edge_meta=None, revision_status=None, delta=None):
    """生成自包含 HTML（S2 主视图 + S3 边回溯 + S4 stale 横幅）。

    context 侧载条目永不进入 embed / envelope / edge_meta；主视图只有一个恒定入口，
    因此上下文条目增长时本函数输出逐字节不变（S4 硬判据）。

    Args:
        graph: viz.graph.RoadmapGraph 归一化图。
        focus: 默认焦点节点 id。
        theta: 可选，固定 θ；None 时由前端按焦点百分位校准（概览/邻域/展开三档）。
        edge_meta: S3 边回溯元数据；None 时由 dependency.build_edge_meta 确定性生成。
        revision_status: S4 stale 判定；None 时为 checked=false 的未核对态。
    Returns:
        HTML 字符串（含 vendored dagre + 内嵌 GRAPH/ENVELOPE/EDGE_META）。
    """
    embed_nodes = {
        nid: {
            **{k: node.get(k) for k in DISPLAY_FIELDS},
            "layer": graph.layer.get(nid, nid.count("-")),
            "uid": graph.uid.get(nid),
        }
        for nid, node in graph.nodes.items()
    }
    embed = {
        "title": getattr(graph, "title", "") or "",
        "description": getattr(graph, "description", "") or "",
        "nodes": embed_nodes,
        "edges": graph.edges,
        "debt": graph.debt,
    }
    envelope = {
        "view_kind": "zj-roadmap-visual-review/v1",
        "carrier_stem": graph.carrier_stem,
        "node_uid": graph.uid.get(focus),
        "carrier_revision": graph.revision,
        "focus": focus,
        "theta": theta,
        "generated_by": "zj-roadmap-driven/viz",
        "authority": AUTHORITY_ENVELOPE,
        "revision_status": revision_status if revision_status is not None else unchecked_status(graph),
    }
    meta = edge_meta if edge_meta is not None else build_edge_meta(graph)
    if delta is None:
        # Deterministic full-view fallback: baseline=None stays byte-identical
        # across carriers (INV::11).
        delta = {"mode": "full-fallback", "added": [], "changed": [],
                 "removed": [], "stable-folded": 0, "warning": None}
    return (
        HTML_TEMPLATE
        .replace("__DAGRE__", DAGRE_JS)
        .replace("__EDGE_META__", json.dumps(meta, ensure_ascii=False))
        .replace("__GRAPH__", json.dumps(embed, ensure_ascii=False))
        .replace("__ENVELOPE__", json.dumps(envelope, ensure_ascii=False))
        .replace("__DELTA__", json.dumps(delta, ensure_ascii=False, sort_keys=True))
    )

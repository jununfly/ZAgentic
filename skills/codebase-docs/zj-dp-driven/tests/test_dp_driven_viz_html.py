#!/usr/bin/env python3
"""§6 R7 interactive HTML viewer — invariant locks (Phase-4b).

Two product surfaces are locked here:
1. build_node_ir() — the click payload, byte-aligned with render()'s node ids (§6 R7 core
   guarantee: the SVG node you click is exactly the card you get).
2. render_html()/render_html_to_file() — self-contained single file, cdn vs inline,
   deterministic, PURE READ, XSS-safe embedding, §4.4 expired-claim surfacing.

Run: python tests/test_dp_driven_viz_html.py
"""

import copy
import hashlib
import html as htmllib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
CLI = SKILL_DIR / "scripts" / "dp_driven_cli.py"

from dp_driven_model import DpDriven, DpDrivenError
import dp_driven_viz as viz
import dp_driven_viz_html as vh


def seeded():
    """Model with: 2 plans, shared finding (overlap), a blocked ticket, a live-lease
    plan claim. Saved + reopened so the carrier round-trip is in play."""
    d = tempfile.TemporaryDirectory()
    db = os.path.join(d.name, "dp_driven.sqlite")
    m = DpDriven.init(db, "登录改造")
    t0 = m.add_task("后端登录")
    tk0 = m.add_ticket(task_id=t0, md_path=os.path.join(d.name, "tk0.md"))
    tk1 = m.add_ticket(task_id=t0)
    m.add_blocks("ticket", tk0, "ticket", tk1)
    f0 = m.add_finding(md_path=os.path.join(d.name, "f0.md"))
    m.add_finding_membership(f0, t0)
    t1 = m.add_task("前端登录")
    m.add_finding_membership(f0, t1)          # shared ⇒ R6 overlap
    m.claim("plan", t0, "alice", now="2020-01-01 00:00:00", lease_seconds=300, epoch=1000)
    m.save()
    m2 = DpDriven.open(db)
    m2._tmp = d
    return m2


class NodeIr(unittest.TestCase):
    def test_ir_ids_match_mermaid_ids(self):
        # The load-bearing parity gate: every IR key is declared by render() and every
        # node/subgraph id render() declares has an IR entry (ORPHANS container excepted).
        m = seeded()
        ir = viz.build_node_ir(m, epoch=None)
        txt = viz.render(m)
        declared = set(re.findall(r'^\s+(?:subgraph\s+)?(\w+)(?:\[|\s*$)', txt, re.M))
        declared = {d for d in declared if d != "ORPHANS" and d != "end"
                    and not d.startswith(("classDef", "flowchart"))}
        self.assertEqual(set(ir), declared, "IR ids must equal render() node ids")

    def test_card_payload_has_derived_fields(self):
        # §3.2 discipline mirrored: blocked arrives only via derived view; an unblocked
        # node has NO `blocked` key (absent, not False). shown_blocked always present.
        m = seeded()
        ir = viz.build_node_ir(m, epoch=1100)
        self.assertNotIn("blocked", ir["tk0_T0"])          # prereq itself is free
        self.assertTrue(ir["tk1_T0"].get("blocked"))       # blocked by tk0 (derived)
        self.assertTrue(ir["tk1_T0"]["shown_blocked"])
        self.assertEqual(ir["tk1_T0"]["display_status"], "被阻塞")

    def test_R6_overlap_badge_in_ir(self):
        # §6 R6 取巧渲染: shared finding = one IR record per plan instance, overlap flag,
        # no synthetic "overlap edge" object anywhere in the IR.
        m = seeded()
        ir = viz.build_node_ir(m, epoch=None)
        f0s = [k for k in ir if k.startswith("f0_")]
        self.assertEqual(sorted(f0s), ["f0_T0", "f0_T1"])
        self.assertTrue(all(ir[k]["overlap"] for k in f0s))
        self.assertTrue(all(sorted(ir[k]["memberships"]) == [0, 1] for k in f0s))

    def test_claim_expired_surfaced_not_hidden(self):
        # §4.4: an expired lease renders the plan frame as paused, but the card keeps the
        # stale agent + claim_expired=True so the Human sees WHO dropped it.
        m = seeded()
        live = viz.build_node_ir(m, epoch=1100)["T0"]
        dead = viz.build_node_ir(m, epoch=99999)["T0"]
        self.assertEqual(live["claim_class"], "plan_inflight")
        self.assertNotIn("claim_expired", live)
        self.assertEqual(dead["claim_class"], "plan_paused")
        self.assertEqual(dead["claim_agent"], "alice")
        self.assertTrue(dead["claim_expired"])

    def test_epoch_none_never_expires(self):
        # model/CLI-clock discipline (§4.4): without an injected epoch nothing expires.
        m = seeded()
        ir = viz.build_node_ir(m, epoch=None)
        self.assertEqual(ir["T0"]["claim_class"], "plan_inflight")

    def test_build_node_ir_is_pure_readonly(self):
        m = seeded()
        before = copy.deepcopy(m.data)
        viz.build_node_ir(m, epoch=1100)
        self.assertEqual(m.data, before)


class HtmlViewer(unittest.TestCase):
    def test_render_html_deterministic(self):
        m = seeded()
        a = vh.render_html(m, now=1100, assets="cdn")
        b = vh.render_html(m, now=1100, assets="cdn")
        self.assertEqual(a, b)

    def test_render_html_is_pure_readonly(self):
        # invariant 10 extended: HTML snapshot never writes back — model.data unchanged
        # AND the carrier file bytes unchanged (no sqlite write happened).
        m = seeded()
        db_bytes = hashlib.sha256(Path(m.db_path).read_bytes()).hexdigest()
        before = copy.deepcopy(m.data)
        vh.render_html(m, now=1100, assets="cdn")
        self.assertEqual(m.data, before)
        self.assertEqual(hashlib.sha256(Path(m.db_path).read_bytes()).hexdigest(), db_bytes)

    def test_html_embeds_ir_json_valid(self):
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        seg = _ir_segment(html)
        ir = json.loads(seg)
        self.assertEqual(ir, viz.build_node_ir(m, epoch=1100))

    def test_html_cdn_mode_uses_official_esm_url(self):
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        self.assertIn(vh.MERMAID_CDN_URL, html)
        self.assertIn("import mermaid from", html)

    def test_html_inline_mode_self_contained(self):
        # inline: no network URL at all, mermaid text embedded + loaded via Blob.
        m = seeded()
        html = vh.render_html(m, now=1100, assets="inline", mermaid_js="export default {};")
        self.assertNotIn("http", html)
        self.assertIn('id="mermaid-js"', html)
        self.assertIn("URL.createObjectURL", html)

    def test_html_mermaid_body_matches_render(self):
        # The graph body is render()'s output (html-escaped) — no second layout truth.
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        body = html.split('<pre class="mermaid">')[1].split("</pre>")[0]
        self.assertEqual(htmllib.unescape(body), viz.render(m))

    def test_html_escape_node_name(self):
        # A hostile name must not break the document: the IR segment stays a single JSON
        # value (no premature </script>) and still parses back to the original string.
        d = tempfile.TemporaryDirectory()
        m = DpDriven.init(os.path.join(d.name, "x.sqlite"), "evil<script>x")
        t = m.add_task('A" </script><b onmouseover=1>')
        m.add_ticket(task_id=t, md_path='</script><img src=x onerror="alert(1)">')
        m.save()
        html = vh.render_html(m, now=None, assets="cdn")
        seg = _ir_segment(html)
        self.assertNotIn("</script>", seg)                    # neutralized as <\/ in raw
        ir = json.loads(seg)
        hostile = [c for c in ir.values() if c.get("kind") == "plan"][0]
        self.assertIn("</script>", hostile["name"])           # data survives intact

    def test_inline_missing_text_raises(self):
        m = seeded()
        with self.assertRaises(DpDrivenError) as cm:
            vh.render_html(m, now=None, assets="inline")
        self.assertEqual(cm.exception.code, "E_VIZ_ASSETS")

    def test_render_html_to_file_only_target_path(self):
        # §5.4 placement: exactly one file appears at out_path, nothing beside it.
        m = seeded()
        d = tempfile.TemporaryDirectory()
        out = os.path.join(d.name, "view.html")
        r = vh.render_html_to_file(m, out, now=1100, assets="inline", mermaid_js="x")
        self.assertEqual(r, out)
        self.assertEqual(os.listdir(d.name), ["view.html"])

    def test_default_html_path(self):
        self.assertEqual(viz.default_html_path("/tmp/x.sqlite"), "/tmp/x.html")
        self.assertEqual(viz.default_html_path("/tmp/x.db"), "/tmp/x.html")

    def test_title_from_destination(self):
        m = seeded()
        self.assertIn("登录改造", vh.render_html(m, now=None, assets="cdn").split("</title>")[0])

    # issue #320: Mermaid v11 DOM 变更打断点击→卡片链路。锁「渲染后回填 data-id」
    # 这一修复结构，防止退回只放宽 nodeKey 正则、或有人删掉回填步骤。
    def test_html_backfills_data_id_on_render(self):
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        self.assertIn("g.node, g.cluster", html)          # 覆盖 node 与 cluster 两类
        self.assertIn('setAttribute("data-id"', html)     # 命中 nodeKey() 路径1
        self.assertIn("window.__dpBackfill", html)        # 钩子已暴露给 boot()

    def test_html_awaits_run_before_backfill(self):
        # 回填必须发生在渲染之后：run() 被 await，boot() 再调 __dpBackfill()。
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        self.assertIn("await mermaid.run(", html)
        self.assertIn("window.__dpBackfill()", html)

    # §6 R7 pan/zoom chrome（缩放按钮 + 手型拖拽平移）结构锁，纯 Python 可失败。
    def test_html_includes_pan_zoom_chrome(self):
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        for tok in ['id="toolbar"', 'id="zoom-in"', 'id="zoom-out"',
                    'id="zoom-reset"', 'id="hand-toggle"', 'id="canvas"']:
            self.assertIn(tok, html)
        self.assertIn("applyTransform", html)
        self.assertIn('classList.toggle("hand"', html)

    def test_html_click_inspect_gated_on_hand_mode(self):
        # 手型模式下左键拖拽不得触发 inspect（避免拖拽误改卡片）。
        m = seeded()
        html = vh.render_html(m, now=1100, assets="cdn")
        self.assertIn("if (view.hand) return;", html)


class HtmlCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")
        subprocess.run([sys.executable, str(CLI), "init", self.db,
                        "--destination", "登录改造"], capture_output=True, check=True)

    def run_cli(self, *args, expect_code=0):
        proc = subprocess.run([sys.executable, str(CLI), *args],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, expect_code,
                         f"cmd={args}\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def test_viz_html_stdout(self):
        p = self.run_cli("viz", self.db, "--format", "html", "--now", "1700000000")
        self.assertIn("<!DOCTYPE html>", p.stdout)
        self.assertIn('id="dp-ir"', p.stdout)

    def test_viz_html_write_file(self):
        out = str(Path(self.tmp.name) / "view.html")
        self.run_cli("viz", self.db, "--format", "html", "--out", out,
                     "--assets", "inline", "--js-path", self._fake_js(), "--now", "1")
        self.assertIn('id="mermaid-js"', Path(out).read_text(encoding="utf-8"))

    def test_viz_html_cli_readonly(self):
        before = Path(self.db).read_bytes()
        self.run_cli("viz", self.db, "--format", "html")
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_assets_inline_requires_js_path(self):
        p = self.run_cli("viz", self.db, "--format", "html", "--assets", "inline",
                         expect_code=2)
        self.assertIn("E_VIZ_ASSETS", p.stderr)

    def test_assets_inline_missing_file_exit3(self):
        self.run_cli("viz", self.db, "--format", "html", "--assets", "inline",
                     "--js-path", str(Path(self.tmp.name) / "nope.mjs"), expect_code=3)

    def _fake_js(self):
        p = Path(self.tmp.name) / "mermaid.esm.min.mjs"
        p.write_text("export default { initialize(){}, run(){} };", encoding="utf-8")
        return str(p)


def _ir_segment(html: str) -> str:
    start = html.index('<script type="application/json" id="dp-ir">')
    body = html[start:]
    body = body.split(">", 1)[1]
    return body.split("</script>", 1)[0].strip()


if __name__ == "__main__":
    unittest.main(verbosity=2)

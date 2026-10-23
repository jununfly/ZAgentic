#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R-HAR-2 — UI Agent Skills 硬门禁（1-5-3 交付物）

职责（契约见 docs/designs/ui-agent-skills/ui-agent-skills-hard-gates.md，节点 1-5-3 硬门禁）：
  硬门禁覆盖 DOM/ARIA、focus、contrast、overflow、responsive、motion 和关键状态。

设计原则：
- 纯 stdlib，无网络 / 无浏览器 / 无外部依赖。门禁只吃「观察证据」（observation bundle），
  浏览器真实捕获由 1-7-3 Storybook active adapter 供给；本模块不做采集、不做 DOM 解析。
- fail-closed：证据缺失或为空 -> HUMAN_REVIEW_REQUIRED，绝不因为「没断言可跑」而 PASS。
  这是 golden-fixtures-spec §8 与 capability manifest S8/S9 的硬要求（禁止把 overflow/focus
  失败记为 warning，禁止用「部分通过」冒充 PASS）。
- 确定性：所有判定为纯函数，迭代顺序显式 sorted，输出可逐字节复现（不受 PYTHONHASHSEED 影响）。
- 可归因：每条 finding 带 code / severity / node_id / observed / expected，供 1-5-4 receipt
  直接落 observed 字段；无法归因的证据走 QUARANTINED。

契约（R-OBS-1，详见 docs/designs/ui-agent-skills/ui-agent-skills-hard-gates.md）：
  <observations>/<fixture_id>/<viewport>.json  ->  observation bundle
  bundle = {schema, fixture_id, class, viewport, captured_by, captured_at,
            dom, focus, contrast, layout, motion, states, quarantine}

CLI：
  hard_gates.py selftest           # 门禁逻辑自检（每门禁正例 + 反例 + 证据缺失例）
  hard_gates.py check --bundle F   # 对单个 bundle 跑适配它的全部门禁
  hard_gates.py schema             # 打印 observation bundle 契约摘要
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_skill_core as core  # single WCAG contrast source of truth (F3)

# --------------------------------------------------------------------------- #
# 契约常量（单一事实源：runner 从这里 import，不另行抄一份）
# --------------------------------------------------------------------------- #

SCHEMA = "ui-agent-skills/observations/v1"

# responsive 必测 viewport（capability manifest S8 / FF-BRK：390/768/1440）
REQUIRED_VIEWPORTS = ["390x844", "768x1024", "1440x900"]

# 门禁阈值（进入 config_hash，改动即触发 revalidation）
GATE_THRESHOLDS = {
    "contrast_ratio": 4.5,          # WCAG AA 正文
    "contrast_ratio_large": 3.0,    # WCAG AA 大字号
    "non_text_contrast_ratio": 3.0,  # UI 边界 / 图形
    "overflow_px": 0,               # 允许的溢出像素（0 容忍）
    "target_size_px": 24,           # WCAG 2.2 AA 最小点击目标（warning 级）
    "motion_reduced_max_ms": 1,     # prefers-reduced-motion 下的时长上限
    "motion_autoplay_warn_ms": 5000,  # 自动播放可感知时长告警阈值
}

# 状态优先级：FAIL 最高。证据缺失不得被 WARNING 淹没。
STATUS_PRECEDENCE = ["FAIL", "HUMAN_REVIEW_REQUIRED", "QUARANTINED", "WARNING", "PASS"]
NON_PASS_FROM_GATE = {"FAIL", "HUMAN_REVIEW_REQUIRED", "QUARANTINED", "WARNING"}

# 交互角色 / 可聚焦标签
INTERACTIVE_ROLES = {
    "button", "link", "textbox", "searchbox", "checkbox", "radio", "combobox",
    "switch", "slider", "tab", "menuitem", "menuitemcheckbox", "menuitemradio",
    "option", "spinbutton", "treeitem",
}
INTERACTIVE_TAGS = {"button", "a", "input", "select", "textarea", "summary"}
# 需要「label 关联」的表单控件
CONTROL_ROLES = {"textbox", "searchbox", "combobox", "checkbox", "radio", "switch", "spinbutton"}
CONTROL_TAGS = {"input", "select", "textarea"}
# 名称来源不可接受的取值（placeholder / 文本内容当 label 是一种 a11y blocker）
BAD_NAME_SOURCES = {"placeholder", "text"}

# EV-v0.1 冻结状态机（scope-manifest §1）
ALLOWED_TRANSITIONS = {
    ("idle", "validating"),
    ("validating", "idle"),
    ("validating", "error"),
    ("validating", "submitting"),
    ("error", "validating"),
    ("error", "idle"),
    ("submitting", "success"),
    ("submitting", "error"),
    ("success", "idle"),
}
RECOVERY_TARGETS = {"validating", "idle"}  # error 态必须能回到 editable

# fixture -> 必须出现过的状态序列（F-1..F-6，wave0-ledger trigger）
REQUIRED_STATES_BY_FIXTURE = {
    "F-1": ["idle", "validating", "submitting", "success"],
    "F-2": ["idle", "validating", "error"],
    "F-3": ["idle", "validating", "error"],
    "F-4": ["idle", "validating", "submitting"],
    "F-5": ["idle", "validating", "submitting", "error", "validating"],
    "F-6": ["idle", "validating", "submitting", "error"],
}

# 单 viewport 门禁 / 跨 viewport 门禁
SINGLE_BUNDLE_GATES = ["dom_aria", "focus", "contrast", "overflow", "motion", "state"]
CROSS_VIEWPORT_GATES = ["responsive"]


# --------------------------------------------------------------------------- #
# 基元
# --------------------------------------------------------------------------- #

def finding(code, severity, message, node_id=None, observed=None, expected=None):
    return {
        "code": code,
        "severity": severity,          # hard | warning | evidence
        "message": message,
        "node_id": node_id,
        "observed": observed,
        "expected": expected,
    }


def _status_from_findings(findings):
    sev = [f["severity"] for f in findings]
    if "hard" in sev:
        return "FAIL"
    if "evidence" in sev:
        return "HUMAN_REVIEW_REQUIRED"
    if "warning" in sev:
        return "WARNING"
    return "PASS"


def _quarantine_findings(bundle):
    out = []
    for item in sorted(bundle.get("quarantine") or [], key=lambda q: str(q.get("code", ""))):
        out.append(finding(
            "HG-QUAR-01", "unattributable",
            "adapter 标记该证据无法归因到具体 fixture/维度（quarantine）",
            node_id=item.get("node_id"),
            observed={"code": item.get("code"), "detail": item.get("detail")},
            expected="可归因证据",
        ))
    return out


def _finish(gate, bundle, findings, checked):
    """统一收口：quarantine 优先于 PASS/WARNING/evidence，但不掩盖 hard。

    severity="unattributable" 的 finding 不参与 status 计算（它表达的是"无法归因"，
    而非某条断言失败），但必须出现在 findings 里供 1-5-4 receipt 记录。
    """
    quarantined = bool(bundle.get("quarantine"))
    findings = list(findings)
    status = _status_from_findings(findings)
    # 系统级 fail-closed：一条断言都没跑却想 PASS == 空转假绿，一律降为证据缺失
    if status == "PASS" and checked == 0:
        findings.append(finding("HG-EVID-03", "evidence",
                                "该门禁在当前证据下没有任何可执行断言（checked=0），不得判 PASS",
                                observed={"checked": 0}, expected="至少一条断言被执行"))
        status = "HUMAN_REVIEW_REQUIRED"
    if quarantined:
        findings.extend(_quarantine_findings(bundle))
    if quarantined and status != "FAIL":
        status = "QUARANTINED"
    return {
        "gate": gate,
        "fixture_id": bundle.get("fixture_id"),
        "viewport": bundle.get("viewport"),
        "status": status,
        "checked": checked,
        "findings": findings,
    }


def evidence_finding(gate, detail, fixture_id=None, viewport=None):
    return {
        "gate": gate,
        "fixture_id": fixture_id,
        "viewport": viewport,
        "status": "HUMAN_REVIEW_REQUIRED",
        "checked": 0,
        "findings": [finding("HG-EVID-01", "evidence",
                             "缺少必须的观察证据：" + detail,
                             observed=None, expected=detail)],
    }


def _section(bundle, name):
    """返回 (section, ok)。缺段 / 空 list / 空 dict 都算证据缺失。"""
    data = bundle.get(name)
    if data is None:
        return None, False
    if isinstance(data, (list, dict, str)) and len(data) == 0:
        return None, False
    return data, True


def _nodes(dom):
    nodes = (dom or {}).get("nodes") or []
    return [n for n in nodes if isinstance(n, dict)]


def _by_id(nodes):
    return {n.get("id"): n for n in nodes if n.get("id")}


def _aria(node, key, default=None):
    return (node.get("aria") or {}).get(key, default)


def _is_interactive(node):
    if node.get("disabled") or node.get("hidden"):
        return False
    tag = (node.get("tag") or "").lower()
    role = (node.get("role") or "").lower()
    if node.get("focusable") is True:
        return True
    if tag in INTERACTIVE_TAGS:
        return True
    return role in INTERACTIVE_ROLES


def _focusable(node):
    if node.get("disabled") or node.get("hidden"):
        return False
    ti = node.get("tabindex")
    if isinstance(ti, int):
        return ti >= 0
    return _is_interactive(node)


def _accessible_name(node, by_id):
    if node.get("name"):
        return str(node["name"]).strip()
    label = _aria(node, "label")
    if label:
        return str(label).strip()
    for ref in (_aria(node, "labelledby") or []):
        target = by_id.get(ref)
        if target and (target.get("text") or target.get("name")):
            return str(target.get("text") or target.get("name")).strip()
    if (node.get("attrs") or {}).get("alt"):
        return str(node["attrs"]["alt"]).strip()
    if node.get("text"):
        return str(node["text"]).strip()
    return ""


def _alpha_composited(color, bg):
    """把 rgba 叠到已知背景上；无法合成时返回 None（-> 证据缺失）。"""
    parsed = _parse_color(color)
    if parsed is None:
        return None
    rgb, alpha = parsed
    if alpha >= 1.0:
        return rgb
    base = _parse_color(bg)
    if base is None:
        return None
    base_rgb, base_alpha = base
    if base_alpha < 1.0:
        return None
    out = []
    for fg_c, bg_c in zip(rgb, base_rgb):
        out.append(int(round(fg_c * alpha + bg_c * (1.0 - alpha))))
    return tuple(out)


def _parse_color(value):
    """支持 #rgb / #rrggbb / rgb() / rgba()；未知写法返回 None。"""
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            try:
                return tuple(int(c * 2, 16) for c in h), 1.0
            except ValueError:
                return None
        if len(h) == 6:
            try:
                return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), 1.0
            except ValueError:
                return None
        return None
    for prefix in ("rgba(", "rgb("):
        if s.startswith(prefix) and s.endswith(")"):
            body = s[len(prefix):-1]
            parts = [p.strip() for p in body.split(",")]
            if prefix == "rgba(" and len(parts) == 4:
                try:
                    rgb = tuple(int(float(p)) for p in parts[:3])
                    alpha = float(parts[3])
                except ValueError:
                    return None
                return rgb, max(0.0, min(1.0, alpha))
            if prefix == "rgb(" and len(parts) == 3:
                try:
                    return tuple(int(float(p)) for p in parts), 1.0
                except ValueError:
                    return None
            return None
    return None


def contrast_ratio(fg, bg):
    """Delegates to ui_skill_core.contrast_ratio_rgb — the single WCAG source.

    Previously this file kept its own copy of the WCAG math with a different
    linearization threshold (0.03928) and no rounding, which could flip the
    PASS/FAIL verdict versus the stage check (S4) on borderline ratios. Both
    now share one implementation.
    """
    return core.contrast_ratio_rgb(fg, bg)


def _is_large_text(size_px, weight):
    try:
        size = float(size_px)
        w = int(weight)
    except (TypeError, ValueError):
        return False
    return size >= 18.66 or (size >= 14.0 and w >= 700)


def aggregate(results):
    """cell / lane 聚合：FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED > WARNING > PASS。"""
    statuses = [r["status"] for r in results]
    for s in STATUS_PRECEDENCE:
        if s in statuses:
            return s
    return "PASS"


# --------------------------------------------------------------------------- #
# 门禁 1 — DOM / ARIA
# --------------------------------------------------------------------------- #

REQUIRED_ARIA_FOR_ROLE = {
    "checkbox": "checked",
    "switch": "checked",
    "radio": "checked",
    "combobox": "expanded",
    "slider": "valuenow",
    "dialog": "modal",
}


def gate_dom_aria(bundle, thresholds=None, fixture=None):
    dom, ok = _section(bundle, "dom")
    if not ok:
        return evidence_finding("dom_aria", "dom 段缺失或为空", bundle.get("fixture_id"), bundle.get("viewport"))
    nodes = _nodes(dom)
    if not nodes:
        return evidence_finding("dom_aria", "dom.nodes 为空", bundle.get("fixture_id"), bundle.get("viewport"))
    by_id = _by_id(nodes)
    out = []
    checked = 0

    # 重复 id / 悬空 idref
    seen = {}
    for n in nodes:
        nid = n.get("id")
        if not nid:
            continue
        seen[nid] = seen.get(nid, 0) + 1
    for nid in sorted(k for k, v in seen.items() if v > 1):
        checked += 1
        out.append(finding("HG-DOM-06", "hard", "节点 id 重复，破坏 idref 唯一性",
                           node_id=nid, observed={"duplicates": seen[nid]}, expected=1))

    for n in nodes:
        nid = n.get("id")
        for key in ("labelledby", "describedby", "controls", "errormessage", "owns"):
            for ref in (_aria(n, key) or []):
                checked += 1
                if ref not in by_id:
                    out.append(finding("HG-DOM-02", "hard",
                                       "aria-%s 引用了不存在的 id（悬空 idref）" % key,
                                       node_id=nid, observed={"ref": ref}, expected="已存在的节点 id"))

        # 交互节点必须有可及名称
        if _is_interactive(n):
            checked += 1
            name = _accessible_name(n, by_id)
            if not name:
                out.append(finding("HG-DOM-01", "hard",
                                   "交互节点缺少可及名称（accessible name）",
                                   node_id=nid, observed={"name": ""}, expected="非空 accessible name"))

        # 表单控件必须有 label 关联，不能靠 placeholder / 纯文本
        tag = (n.get("tag") or "").lower()
        role = (n.get("role") or "").lower()
        if tag in CONTROL_TAGS or role in CONTROL_ROLES:
            src = n.get("name_source")
            if src is not None:
                checked += 1
                if src in BAD_NAME_SOURCES:
                    out.append(finding("HG-DOM-03", "hard",
                                       "表单控件仅靠 %s 提供名称，缺少 label 关联" % src,
                                       node_id=nid, observed={"name_source": src},
                                       expected="label / labelledby / aria-label"))

        # role 必需的 aria 属性
        need = REQUIRED_ARIA_FOR_ROLE.get(role)
        if need:
            checked += 1
            if _aria(n, need) is None:
                out.append(finding("HG-DOM-04", "hard",
                                   "role=%s 缺少必需的 aria-%s" % (role, need),
                                   node_id=nid, observed=None, expected="aria-" + need))

        # 图片必须有 alt 或显式装饰
        if tag == "img":
            checked += 1
            alt = (n.get("attrs") or {}).get("alt")
            decorative = _aria(n, "hidden") is True or role in ("presentation", "none")
            if alt is None and not decorative:
                out.append(finding("HG-DOM-05", "hard",
                                   "img 缺少 alt 且未显式标记为装饰性",
                                   node_id=nid, observed=None, expected="alt 或 aria-hidden=true"))

        # aria-hidden 子树内不得有可聚焦节点
        if _aria(n, "hidden") is True and _focusable(n):
            checked += 1
            out.append(finding("HG-DOM-08", "hard",
                               "aria-hidden=true 的子树内含可聚焦节点（隐藏焦点陷阱）",
                               node_id=nid, observed={"aria-hidden": True},
                               expected="aria-hidden 子树不可聚焦"))

    # 标题层级不得跳级（warning：语义建议，不阻断）
    levels = [n.get("heading_level") for n in nodes if isinstance(n.get("heading_level"), int)]
    levels = [lv for lv in levels if lv > 0]
    prev = 0
    for lv in levels:
        checked += 1
        if prev and lv > prev + 1:
            out.append(finding("HG-DOM-07", "warning", "标题层级跳级",
                               observed={"from": prev, "to": lv}, expected="逐级递增"))
        prev = lv

    return _finish("dom_aria", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 门禁 2 — focus
# --------------------------------------------------------------------------- #

def gate_focus(bundle, thresholds=None, fixture=None):
    dom, dom_ok = _section(bundle, "dom")
    foc, foc_ok = _section(bundle, "focus")
    if not (dom_ok and foc_ok):
        return evidence_finding("focus", "dom 或 focus 段缺失/为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    nodes = _nodes(dom)
    if not nodes:
        return evidence_finding("focus", "dom.nodes 为空，无法判定焦点可达性",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    if not (foc.get("sequence") or []):
        return evidence_finding("focus", "focus.sequence 为空，未捕获 tab 序列",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    by_id = _by_id(nodes)
    order_index = {n.get("id"): i for i, n in enumerate(nodes) if n.get("id")}
    out = []
    checked = 0

    # 交互节点可达性 + 正 tabindex
    for n in nodes:
        nid = n.get("id")
        tag = (n.get("tag") or "").lower()
        role = (n.get("role") or "").lower()
        interactive = tag in INTERACTIVE_TAGS or role in INTERACTIVE_ROLES
        if not interactive:
            continue
        ti = n.get("tabindex")
        if isinstance(ti, int) and ti > 0:
            checked += 1
            out.append(finding("HG-FOC-02", "hard",
                               "正 tabindex 破坏 DOM 焦点顺序",
                               node_id=nid, observed={"tabindex": ti}, expected="tabindex <= 0"))
        if not _focusable(n) and not n.get("disabled") and not n.get("hidden"):
            checked += 1
            out.append(finding("HG-FOC-01", "hard", "交互节点不可达（不在 tab 序列中）",
                               node_id=nid, observed={"tabindex": ti}, expected="可达"))

    # 焦点序列：连续性、DOM 顺序、可见焦点、disabled 不入序
    seq = (foc.get("sequence") or [])
    vis = {v.get("node_id"): v for v in (foc.get("focus_visible") or []) if isinstance(v, dict)}
    last_idx = -1
    for entry in sorted(seq, key=lambda e: e.get("order", 0)):
        nid = entry.get("node_id")
        checked += 1
        node = by_id.get(nid)
        if node is None:
            out.append(finding("HG-FOC-04", "evidence", "焦点序列引用了不存在的节点 id",
                               node_id=nid, observed={"node_id": nid}, expected="已存在的节点 id"))
            continue
        if node.get("disabled"):
            out.append(finding("HG-FOC-07", "warning", "disabled 节点出现在焦点序列",
                               node_id=nid, observed={"disabled": True}, expected="不参与 tab"))
        idx = order_index.get(nid, -1)
        if idx >= 0 and idx < last_idx:
            out.append(finding("HG-FOC-03", "hard", "焦点顺序与 DOM 顺序不一致",
                               node_id=nid, observed={"dom_index": idx, "prev_dom_index": last_idx},
                               expected="单调递增"))
        if idx >= 0:
            last_idx = max(last_idx, idx)
        v = vis.get(nid)
        if v is None:
            out.append(finding("HG-FOC-05", "hard", "入序节点缺少焦点可见样式证据",
                               node_id=nid, observed=None, expected="outline / box-shadow 记录"))
        else:
            style = str(v.get("outline_style") or "").lower()
            px = v.get("outline_px") or 0
            shadow = v.get("box_shadow")
            visible = (style not in ("", "none")) or (float(px) > 0) or bool(shadow)
            if not visible:
                out.append(finding("HG-FOC-05", "hard", "焦点不可见（outline:none 且无替代指示）",
                                   node_id=nid,
                                   observed={"outline_style": style, "outline_px": px,
                                             "box_shadow": shadow},
                                   expected="可见焦点指示"))

    # 焦点陷阱（dialog）：进入 / 环绕 / Esc 释放 / 焦点归还
    trap = foc.get("trap")
    if isinstance(trap, dict):
        checks = [("entered", "焦点未进入 trap 作用域"),
                  ("wrapped", "焦点未在 trap 内环绕"),
                  ("esc_releases", "Esc 未释放 trap"),
                  ("restored_to", "关闭后焦点未归还触发元素")]
        for key, msg in checks:
            checked += 1
            val = trap.get(key)
            if key == "restored_to":
                if not val or val not in by_id:
                    out.append(finding("HG-FOC-06", "hard", msg, node_id=val,
                                       observed={"restored_to": val}, expected="触发元素 id"))
            elif val is not True:
                out.append(finding("HG-FOC-06", "hard", msg,
                                   observed={key: val}, expected=True))

    return _finish("focus", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 门禁 3 — contrast
# --------------------------------------------------------------------------- #

def gate_contrast(bundle, thresholds=None, fixture=None):
    thr = dict(GATE_THRESHOLDS, **(thresholds or {}))
    sec, ok = _section(bundle, "contrast")
    if not ok:
        return evidence_finding("contrast", "contrast 段缺失或为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    samples = sec.get("samples") or []
    if not samples:
        return evidence_finding("contrast", "contrast.samples 为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    out = []
    checked = 0
    for s in samples:
        checked += 1
        nid = s.get("node_id")
        kind = s.get("kind") or "text"
        fg = _alpha_composited(s.get("fg"), s.get("bg"))
        bg = _parse_color(s.get("bg"))
        if fg is None or bg is None or bg[1] < 1.0:
            out.append(finding("HG-CON-04", "evidence", "前景/背景色无法解析或透明度未合成，无法判定",
                               node_id=nid, observed={"fg": s.get("fg"), "bg": s.get("bg")},
                               expected="可解析的最终色值"))
            continue
        ratio = contrast_ratio(fg, bg[0])
        large = _is_large_text(s.get("font_size_px"), s.get("font_weight"))
        if kind == "non_text":
            need = thr["non_text_contrast_ratio"]
        elif large:
            need = thr["contrast_ratio_large"]
        else:
            need = thr["contrast_ratio"]
        if ratio + 1e-9 < need:
            if kind == "non_text":
                code, label = "HG-CON-03", "非文本对比度不足"
            elif large:
                code, label = "HG-CON-02", "大字号文本对比度不足"
            else:
                code, label = "HG-CON-01", "正文对比度不足"
            out.append(finding(code, "hard", label,
                               node_id=nid,
                               observed={"ratio": round(ratio, 3), "fg": s.get("fg"),
                                         "bg": s.get("bg"), "kind": kind,
                                         "font_size_px": s.get("font_size_px"),
                                         "font_weight": s.get("font_weight")},
                               expected={"min_ratio": need}))
    return _finish("contrast", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 门禁 4 — overflow
# --------------------------------------------------------------------------- #

def _overflow_findings(layout, thr, prefix="HG-OVF", viewport_tag=None):
    out, checked = [], 0
    tol = thr["overflow_px"]
    doc = layout.get("document") or {}
    vw = (layout.get("viewport") or {}).get("w")
    if doc.get("scroll_width") is not None and doc.get("client_width") is not None:
        checked += 1
        delta = int(doc["scroll_width"]) - int(doc["client_width"])
        if delta > tol:
            out.append(finding(prefix + "-01", "hard", "文档出现水平溢出",
                               observed={"delta_px": delta, "viewport": viewport_tag},
                               expected={"max_delta_px": tol}))
    for box in (layout.get("boxes") or []):
        checked += 1
        nid = box.get("node_id")
        sx, cx = box.get("scroll_width"), box.get("client_width")
        ox = str(box.get("overflow_x") or "visible").lower()
        if sx is not None and cx is not None and int(sx) - int(cx) > tol:
            if ox in ("visible", "hidden", "clip"):
                out.append(finding(prefix + "-02", "hard",
                                   "元素内容水平溢出且未被允许滚动（被裁切）",
                                   node_id=nid,
                                   observed={"scroll_width": sx, "client_width": cx, "overflow_x": ox},
                                   expected={"max_delta_px": tol, "overflow_x": "auto|scroll"}))
        sy, cy = box.get("scroll_height"), box.get("client_height")
        oy = str(box.get("overflow_y") or "visible").lower()
        truncates = box.get("line_clamp") or box.get("text_overflow") == "ellipsis"
        if sy is not None and cy is not None and int(sy) - int(cy) > tol and oy in ("hidden", "clip") and not truncates:
            out.append(finding(prefix + "-04", "hard",
                               "文本被裁切且未声明 ellipsis / line-clamp",
                               node_id=nid,
                               observed={"scroll_height": sy, "client_height": cy, "overflow_y": oy},
                               expected="可见截断提示或允许滚动"))
        if vw is not None:
            rect = box.get("rect") or {}
            right = rect.get("x"), rect.get("w")
            if isinstance(right[0], (int, float)) and isinstance(right[1], (int, float)):
                if str(box.get("position") or "static") in ("static", "relative", "absolute"):
                    checked += 1
                    over = (right[0] + right[1]) - float(vw)
                    if over > tol:
                        out.append(finding(prefix + "-03", "hard", "元素超出 viewport 宽度",
                                           node_id=nid,
                                           observed={"right_px": right[0] + right[1], "viewport_w": vw,
                                                     "over_px": over},
                                           expected={"max_over_px": tol}))
    return out, checked


def gate_overflow(bundle, thresholds=None, fixture=None):
    thr = dict(GATE_THRESHOLDS, **(thresholds or {}))
    layout, ok = _section(bundle, "layout")
    if not ok:
        return evidence_finding("overflow", "layout 段缺失或为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    out, checked = _overflow_findings(layout, thr, "HG-OVF", bundle.get("viewport"))
    return _finish("overflow", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 门禁 5 — responsive（跨 viewport）
# --------------------------------------------------------------------------- #

def gate_responsive(bundles_by_viewport, thresholds=None, fixture=None):
    thr = dict(GATE_THRESHOLDS, **(thresholds or {}))
    if not isinstance(bundles_by_viewport, dict) or not bundles_by_viewport:
        return evidence_finding("responsive", "没有任何 viewport 的 observation bundle",
                                None, None)
    fixture_id = (fixture or {}).get("id") or next(iter(bundles_by_viewport.values())).get("fixture_id")
    out = []
    checked = 0

    # 必测 viewport 覆盖（缺一档即证据不足，不能"部分通过"冒充 PASS）
    for vp in REQUIRED_VIEWPORTS:
        checked += 1
        if vp not in bundles_by_viewport:
            out.append(finding("HG-RSP-01", "evidence", "必测 viewport 缺少 observation bundle",
                               observed={"missing": vp}, expected={"required": REQUIRED_VIEWPORTS}))

    for vp in sorted(bundles_by_viewport):
        b = bundles_by_viewport[vp] or {}
        layout = b.get("layout") or {}
        checked += 1
        declared = layout.get("viewport") or {}
        try:
            width = int(str(vp).split("x")[0])
        except (ValueError, IndexError):
            width = None
        if width is not None and declared.get("w") is not None and int(declared["w"]) != width:
            out.append(finding("HG-RSP-02", "hard", "bundle 声明宽度与 viewport 名不符",
                               observed={"viewport": vp, "declared_w": declared.get("w")},
                               expected={"w": width}))
        # 每个 viewport 复用 overflow 断言
        ovf, n = _overflow_findings(layout, thr, "HG-RSP", vp)
        checked += n
        for f in ovf:
            f["code"] = "HG-RSP-03"
            f["message"] = "[%s] %s" % (vp, f["message"])
            f["observed"] = dict(f.get("observed") or {}, viewport=vp)
        out.extend(ovf)

        # 声明的布局断言
        expected_layout = layout.get("expected_layout")
        observed_layout = layout.get("observed_layout")
        if expected_layout and observed_layout:
            checked += 1
            if expected_layout != observed_layout:
                out.append(finding("HG-RSP-06", "hard", "布局与声明的 breakpoint 形态不符",
                                   observed={"viewport": vp, "observed_layout": observed_layout},
                                   expected={"expected_layout": expected_layout}))

        # 交互目标尺寸（warning 级）
        for target in (layout.get("targets") or []):
            checked += 1
            w, h = target.get("w"), target.get("h")
            if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                if w < thr["target_size_px"] or h < thr["target_size_px"]:
                    out.append(finding("HG-RSP-05", "warning", "交互目标小于最小点击尺寸",
                                       node_id=target.get("node_id"),
                                       observed={"viewport": vp, "w": w, "h": h},
                                       expected={"min_px": thr["target_size_px"]}))

        # 声明的不重叠对
        rects = {t.get("node_id"): t for t in (layout.get("targets") or []) if t.get("node_id")}
        for pair in (layout.get("no_overlap_pairs") or []):
            checked += 1
            a, b_ = (pair + [None, None])[:2] if isinstance(pair, list) else (None, None)
            ra, rb = rects.get(a), rects.get(b_)
            if ra and rb and _rects_overlap(ra, rb):
                out.append(finding("HG-RSP-04", "hard", "声明不重叠的交互目标发生重叠",
                                   node_id=a, observed={"viewport": vp, "pair": [a, b_]},
                                   expected="不相交"))

    return _finish("responsive", {"fixture_id": fixture_id, "viewport": "all",
                                  "quarantine": []}, out, checked)


def _rects_overlap(a, b):
    def box(t):
        return (t.get("x", 0), t.get("y", 0), t.get("x", 0) + t.get("w", 0), t.get("y", 0) + t.get("h", 0))
    ax1, ay1, ax2, ay2 = box(a)
    bx1, by1, bx2, by2 = box(b)
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


# --------------------------------------------------------------------------- #
# 门禁 6 — motion
# --------------------------------------------------------------------------- #

def gate_motion(bundle, thresholds=None, fixture=None):
    thr = dict(GATE_THRESHOLDS, **(thresholds or {}))
    sec, ok = _section(bundle, "motion")
    if not ok:
        return evidence_finding("motion", "motion 段缺失或为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    anims = sec.get("animations") or []
    if not anims and not sec.get("reduced_motion_emulated"):
        return evidence_finding("motion", "motion.animations 为空且未做 reduced-motion 模拟",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    out = []
    checked = 0
    max_reduced = thr["motion_reduced_max_ms"]

    for a in anims:
        checked += 1
        nid = a.get("node_id")
        name = a.get("name")
        dur = a.get("duration_ms")
        try:
            dur_val = float(dur)
        except (TypeError, ValueError):
            out.append(finding("HG-MOT-06", "evidence", "动画时长不可解析",
                               node_id=nid, observed={"duration_ms": dur}, expected="数值毫秒"))
            continue
        if dur_val > 0:
            variant = a.get("reduced_variant")
            if not isinstance(variant, dict):
                out.append(finding("HG-MOT-01", "hard",
                                   "动画未提供 prefers-reduced-motion 降级变体",
                                   node_id=nid, observed={"name": name, "duration_ms": dur_val},
                                   expected="reduced_variant"))
            else:
                try:
                    rdur = float(variant.get("duration_ms", 0))
                except (TypeError, ValueError):
                    rdur = None
                if rdur is None or rdur > max_reduced:
                    out.append(finding("HG-MOT-02", "hard",
                                       "reduced-motion 变体仍有时长，未真正降级",
                                       node_id=nid,
                                       observed={"name": name, "reduced_duration_ms": variant.get("duration_ms")},
                                       expected={"max_ms": max_reduced}))
        if str(a.get("iterations")).lower() == "infinite" and a.get("covers_interactive"):
            out.append(finding("HG-MOT-03", "hard", "无限动画覆盖交互元素",
                               node_id=nid, observed={"name": name, "iterations": "infinite"},
                               expected="不遮挡交互区域"))
        if dur_val > thr["motion_autoplay_warn_ms"] and not a.get("has_pause_control"):
            out.append(finding("HG-MOT-04", "warning", "自动播放动效超过可感知时长且无暂停控制",
                               node_id=nid, observed={"duration_ms": dur_val},
                               expected={"max_ms": thr["motion_autoplay_warn_ms"]}))

    # reduced-motion 模拟下仍在动 = 硬失败
    if sec.get("reduced_motion_emulated"):
        for a in anims:
            checked += 1
            try:
                dur_val = float(a.get("duration_ms"))
            except (TypeError, ValueError):
                continue
            if dur_val > max_reduced:
                out.append(finding("HG-MOT-05", "hard",
                                   "reduced-motion 模拟下仍存在动画（动效未降级）",
                                   node_id=a.get("node_id"),
                                   observed={"name": a.get("name"), "duration_ms": a.get("duration_ms")},
                                   expected={"max_ms": max_reduced}))

    return _finish("motion", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 门禁 7 — state（EV-v0.1 状态机）
# --------------------------------------------------------------------------- #

def gate_state(bundle, thresholds=None, fixture=None):
    sec, ok = _section(bundle, "states")
    if not ok:
        return evidence_finding("state", "states 段缺失或为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))
    machine = sec.get("machine")
    fixture_id = (fixture or {}).get("id") or bundle.get("fixture_id")
    out = []
    checked = 0

    if machine and machine != "ev-v0.1":
        out.append(finding("HG-STA-07", "evidence", "状态机版本不是 EV-v0.1，无法按冻结口径判定",
                           observed={"machine": machine}, expected="ev-v0.1"))

    transitions = [t for t in (sec.get("transitions") or []) if isinstance(t, dict)]
    if not transitions:
        return evidence_finding("state", "states.transitions 为空",
                                bundle.get("fixture_id"), bundle.get("viewport"))

    visited = []
    for t in transitions:
        checked += 1
        frm, to = t.get("from"), t.get("to")
        visited.append(frm)
        visited.append(to)
        if (frm, to) not in ALLOWED_TRANSITIONS:
            out.append(finding("HG-STA-01", "hard", "出现状态机不存在的转移",
                               observed={"from": frm, "to": to, "event": t.get("event")},
                               expected={"allowed": sorted("%s->%s" % e for e in ALLOWED_TRANSITIONS)}))
    visited = [s for s in visited if s]

    # fixture 必需状态覆盖
    required = REQUIRED_STATES_BY_FIXTURE.get(fixture_id)
    if required:
        for st in required:
            checked += 1
            if st not in visited:
                out.append(finding("HG-STA-02", "hard",
                                   "fixture 必需状态未出现（状态覆盖缺失）",
                                   observed={"missing": st, "visited": sorted(set(visited))},
                                   expected={"required": required}))

    # submitting 期间不得接受第二次提交
    for sub in (sec.get("submits") or []):
        checked += 1
        if sub.get("at_state") == "submitting" and sub.get("accepted") is True:
            out.append(finding("HG-STA-03", "hard",
                               "submitting 态下第二次提交被接受（输入未锁定）",
                               observed={"at_state": "submitting", "accepted": True},
                               expected={"accepted": False}))

    # error 态必须可恢复回 editable
    if "error" in visited:
        checked += 1
        recover = [t for t in transitions if t.get("from") == "error" and t.get("to") in RECOVERY_TARGETS]
        if not recover:
            out.append(finding("HG-STA-04", "hard", "error 态无恢复路径（无法回到 editable）",
                               observed={"transitions": sorted({"%s->%s" % (t.get("from"), t.get("to")) for t in transitions})},
                               expected={"recovery_targets": sorted(RECOVERY_TARGETS)}))

    # 字段级 error 覆盖
    for fe in (sec.get("field_errors") or []):
        checked += 1
        field = fe.get("field")
        if not fe.get("has_message"):
            out.append(finding("HG-STA-05", "hard", "字段级 error 缺少可读 message",
                               observed={"field": field, "has_message": False},
                               expected="字段级 error message"))
        if not fe.get("announced"):
            out.append(finding("HG-STA-06", "hard",
                               "字段级 error 未对辅助技术公告（缺 aria-live / aria-describedby 关联）",
                               observed={"field": field, "announced": False},
                               expected="error 被公告"))

    return _finish("state", bundle, out, checked)


# --------------------------------------------------------------------------- #
# 注册表与调度
# --------------------------------------------------------------------------- #

GATES = {
    "dom_aria": gate_dom_aria,
    "focus": gate_focus,
    "contrast": gate_contrast,
    "overflow": gate_overflow,
    "motion": gate_motion,
    "state": gate_state,
    "responsive": gate_responsive,
}


def run_gate(dimension, payload, thresholds=None, fixture=None):
    fn = GATES.get(dimension)
    if fn is None:
        return evidence_finding(dimension, "门禁未实现", (fixture or {}).get("id"))
    return fn(payload, thresholds=thresholds, fixture=fixture)


# --------------------------------------------------------------------------- #
# 自检夹具（纯内存合成，明确标注：证明门禁逻辑本身，不是验收证据）
# --------------------------------------------------------------------------- #

def synthetic_good_bundle(viewport="390x844", fixture_id="F-1"):
    w = int(viewport.split("x")[0])
    return {
        "schema": SCHEMA,
        "fixture_id": fixture_id,
        "class": "form",
        "viewport": viewport,
        "captured_by": "selftest/synthetic",
        "captured_at": "2026-01-01T00:00:00+00:00",
        "dom": {
            "nodes": [
                {"id": "title", "tag": "h1", "heading_level": 1, "text": "用户资料编辑"},
                {"id": "form", "tag": "form", "role": "form", "name": "用户资料编辑"},
                {"id": "email", "tag": "input", "role": "textbox", "name": "邮箱",
                 "name_source": "label", "tabindex": 0, "focusable": True,
                 "attrs": {"type": "email"}},
                {"id": "submit", "tag": "button", "role": "button", "name": "保存",
                 "name_source": "text", "tabindex": 0, "focusable": True,
                 "attrs": {"type": "submit"}},
            ]
        },
        "focus": {
            "sequence": [{"order": 1, "node_id": "email"}, {"order": 2, "node_id": "submit"}],
            "focus_visible": [
                {"node_id": "email", "outline_style": "solid", "outline_px": 2, "box_shadow": None},
                {"node_id": "submit", "outline_style": "solid", "outline_px": 2, "box_shadow": None},
            ],
            "trap": None,
        },
        "contrast": {
            "samples": [
                {"node_id": "email", "kind": "text", "fg": "#111827", "bg": "#ffffff",
                 "font_size_px": 16, "font_weight": 400},
                {"node_id": "title", "kind": "text", "fg": "#111827", "bg": "#ffffff",
                 "font_size_px": 28, "font_weight": 700},
            ]
        },
        "layout": {
            "viewport": {"w": w, "h": 844},
            "document": {"scroll_width": w, "client_width": w},
            "expected_layout": "stacked" if w < 768 else "two-column",
            "observed_layout": "stacked" if w < 768 else "two-column",
            "boxes": [
                {"node_id": "email", "rect": {"x": 16, "y": 80, "w": w - 32, "h": 44},
                 "scroll_width": w - 32, "client_width": w - 32,
                 "overflow_x": "visible", "overflow_y": "visible", "position": "static"},
            ],
            "targets": [{"node_id": "submit", "x": 16, "y": 140, "w": 96, "h": 44}],
            "no_overlap_pairs": [],
        },
        "motion": {
            "animations": [
                {"name": "fade-in", "node_id": "email", "duration_ms": 200, "iterations": 1,
                 "property": "opacity", "covers_interactive": False,
                 "reduced_variant": {"duration_ms": 0}},
            ],
            "reduced_motion_emulated": False,
        },
        "states": {
            "machine": "ev-v0.1",
            "transitions": [
                {"from": "idle", "to": "validating", "event": "input"},
                {"from": "validating", "to": "submitting", "event": "submit"},
                {"from": "submitting", "to": "success", "event": "mock-200"},
            ],
            "submits": [{"at_state": "submitting", "accepted": False}],
            "field_errors": [],
        },
        "quarantine": [],
    }


def synthetic_bundle_set(fixture_id="F-1"):
    return {vp: synthetic_good_bundle(vp, fixture_id) for vp in REQUIRED_VIEWPORTS}


def _selftest_cases():
    """(case_name, dimension, payload_builder, expected_status, expected_code)。"""
    def mut(fn):
        def build():
            b = synthetic_good_bundle("390x844")
            fn(b)
            return b
        return build

    cases = [
        # --- 正例：每门禁都必须 PASS（且 checked > 0，证明断言真的跑了） ---
        ("dom_aria/good", "dom_aria", synthetic_good_bundle, "PASS", None),
        ("focus/good", "focus", synthetic_good_bundle, "PASS", None),
        ("contrast/good", "contrast", synthetic_good_bundle, "PASS", None),
        ("overflow/good", "overflow", synthetic_good_bundle, "PASS", None),
        ("motion/good", "motion", synthetic_good_bundle, "PASS", None),
        ("state/good", "state", synthetic_good_bundle, "PASS", None),
        ("responsive/good", "responsive", synthetic_bundle_set, "PASS", None),

        # --- 反例：必须命中预期 code（不是"随便非 PASS"） ---
        ("dom_aria/no-accessible-name", "dom_aria",
         mut(lambda b: b["dom"]["nodes"][3].update({"name": "", "text": ""})), "FAIL", "HG-DOM-01"),
        ("dom_aria/placeholder-only", "dom_aria",
         mut(lambda b: b["dom"]["nodes"][2].update({"name_source": "placeholder"})), "FAIL", "HG-DOM-03"),
        ("dom_aria/dangling-idref", "dom_aria",
         mut(lambda b: b["dom"]["nodes"][2].update({"aria": {"labelledby": ["ghost"]}})), "FAIL", "HG-DOM-02"),
        ("focus/positive-tabindex", "focus",
         mut(lambda b: b["dom"]["nodes"][3].update({"tabindex": 3})), "FAIL", "HG-FOC-02"),
        ("focus/invisible-focus", "focus",
         mut(lambda b: b["focus"]["focus_visible"][0].update({"outline_style": "none", "outline_px": 0})),
         "FAIL", "HG-FOC-05"),
        ("focus/trap-escaped", "focus",
         mut(lambda b: b["focus"].update({"trap": {"entered": True, "wrapped": True,
                                                  "esc_releases": False, "restored_to": "submit"}})),
         "FAIL", "HG-FOC-06"),
        ("contrast/low-ratio", "contrast",
         mut(lambda b: b["contrast"]["samples"][0].update({"fg": "#d1d5db"})), "FAIL", "HG-CON-01"),
        ("contrast/rgba-uncomposited", "contrast",
         mut(lambda b: b["contrast"]["samples"][0].update({"fg": "rgba(17,24,39,0.4)", "bg": "transparent"})),
         "HUMAN_REVIEW_REQUIRED", "HG-CON-04"),
        ("overflow/document-scroll", "overflow",
         mut(lambda b: b["layout"]["document"].update({"scroll_width": 520})), "FAIL", "HG-OVF-01"),
        ("overflow/clipped-box", "overflow",
         mut(lambda b: b["layout"]["boxes"][0].update({"scroll_width": 480, "client_width": 358})),
         "FAIL", "HG-OVF-02"),
        ("motion/no-reduced-variant", "motion",
         mut(lambda b: b["motion"]["animations"][0].pop("reduced_variant")), "FAIL", "HG-MOT-01"),
        ("motion/reduced-still-animated", "motion",
         mut(lambda b: (b["motion"].update({"reduced_motion_emulated": True}),
                        b["motion"]["animations"][0].update({"duration_ms": 300, "reduced_variant": {"duration_ms": 300}}))),
         "FAIL", "HG-MOT-05"),
        ("state/illegal-transition", "state",
         mut(lambda b: b["states"]["transitions"].append({"from": "validating", "to": "success", "event": "shortcut"})),
         "FAIL", "HG-STA-01"),
        ("state/double-submit", "state",
         mut(lambda b: b["states"]["submits"].append({"at_state": "submitting", "accepted": True})),
         "FAIL", "HG-STA-03"),
        ("state/missing-required", "state",
         mut(lambda b: b["states"].update({"transitions": [{"from": "idle", "to": "validating", "event": "input"}],
                                          "submits": []})),
         "FAIL", "HG-STA-02"),
        ("state/field-error-unannounced", "state",
         mut(lambda b: b["states"].update({"field_errors": [{"field": "email", "has_message": True,
                                                            "announced": False}]})),
         "FAIL", "HG-STA-06"),
        ("responsive/missing-viewport", "responsive",
         lambda: {vp: synthetic_good_bundle(vp) for vp in REQUIRED_VIEWPORTS[:2]},
         "HUMAN_REVIEW_REQUIRED", "HG-RSP-01"),
        ("responsive/overflow-at-1440", "responsive",
         (lambda: _mutate_vp("1440x900", lambda b: b["layout"]["document"].update({"scroll_width": 1600}))()),
         "FAIL", "HG-RSP-03"),

        # --- 目录内每条 hard/warning 断言都必须有一个"证明它会响"的用例 ---
        ("dom_aria/role-missing-aria", "dom_aria",
         mut(lambda b: b["dom"]["nodes"][2].update({"role": "combobox"})), "FAIL", "HG-DOM-04"),
        ("dom_aria/img-no-alt", "dom_aria",
         mut(lambda b: b["dom"]["nodes"].append({"id": "avatar", "tag": "img", "attrs": {}})),
         "FAIL", "HG-DOM-05"),
        ("dom_aria/duplicate-id", "dom_aria",
         mut(lambda b: b["dom"]["nodes"].append(dict(b["dom"]["nodes"][2]))), "FAIL", "HG-DOM-06"),
        ("dom_aria/heading-skip", "dom_aria",
         mut(lambda b: b["dom"]["nodes"].append({"id": "sub", "tag": "h3", "heading_level": 3})),
         "WARNING", "HG-DOM-07"),
        ("dom_aria/hidden-focusable", "dom_aria",
         mut(lambda b: b["dom"]["nodes"].append({"id": "ghost-btn", "tag": "button", "role": "button",
                                                "name": "隐藏", "tabindex": 0, "focusable": True,
                                                "aria": {"hidden": True}})),
         "FAIL", "HG-DOM-08"),
        ("focus/unreachable", "focus",
         mut(lambda b: b["dom"]["nodes"][3].update({"focusable": False, "tabindex": -1})),
         "FAIL", "HG-FOC-01"),
        ("focus/order-mismatch", "focus",
         mut(lambda b: b["focus"].update({"sequence": [{"order": 1, "node_id": "submit"},
                                                      {"order": 2, "node_id": "email"}]})),
         "FAIL", "HG-FOC-03"),
        ("focus/unknown-node", "focus",
         mut(lambda b: b["focus"]["sequence"].append({"order": 3, "node_id": "ghost"})),
         "HUMAN_REVIEW_REQUIRED", "HG-FOC-04"),
        ("focus/disabled-in-sequence", "focus",
         mut(lambda b: (b["dom"]["nodes"].append({"id": "submit2", "tag": "button", "name": "禁用",
                                                  "disabled": True, "tabindex": 0}),
                        b["focus"]["sequence"].append({"order": 3, "node_id": "submit2"}),
                        b["focus"]["focus_visible"].append({"node_id": "submit2", "outline_style": "solid",
                                                            "outline_px": 2}))),
         "WARNING", "HG-FOC-07"),
        ("contrast/large-text-ratio", "contrast",
         mut(lambda b: b["contrast"]["samples"].append({"node_id": "title", "kind": "text",
                                                        "fg": "#a1a6ae", "bg": "#ffffff",
                                                        "font_size_px": 20, "font_weight": 400})),
         "FAIL", "HG-CON-02"),
        # 同一颜色在大字号下合规（3.885:1 >= 3.0）、正文下不合规（< 4.5）——证明阈值分支真的分流
        ("contrast/large-text-threshold-differs", "contrast",
         mut(lambda b: b["contrast"].update({"samples": [{"node_id": "title", "kind": "text",
                                                          "fg": "#7c8288", "bg": "#ffffff",
                                                          "font_size_px": 20, "font_weight": 400}]})),
         "PASS", None),
        ("contrast/non-text-ratio", "contrast",
         mut(lambda b: b["contrast"]["samples"].append({"node_id": "submit", "kind": "non_text",
                                                        "fg": "#9ca3af", "bg": "#ffffff"})),
         "FAIL", "HG-CON-03"),
        ("overflow/box-beyond-viewport", "overflow",
         mut(lambda b: b["layout"]["boxes"].append({"node_id": "email", "rect": {"x": 300, "y": 80, "w": 200, "h": 44},
                                                    "scroll_width": 200, "client_width": 200})),
         "FAIL", "HG-OVF-03"),
        ("overflow/clipped-text", "overflow",
         mut(lambda b: b["layout"]["boxes"].append({"node_id": "bio", "rect": {"x": 16, "y": 200, "w": 200, "h": 40},
                                                    "scroll_height": 200, "client_height": 40,
                                                    "overflow_y": "hidden"})),
         "FAIL", "HG-OVF-04"),
        ("responsive/width-mismatch", "responsive",
         _mutate_vp("390x844", lambda b: b["layout"]["viewport"].update({"w": 400})),
         "FAIL", "HG-RSP-02"),
        ("responsive/overlapping-targets", "responsive",
         _mutate_vp("390x844", lambda b: (b["layout"]["targets"].extend([
             {"node_id": "t1", "x": 16, "y": 200, "w": 100, "h": 44},
             {"node_id": "t2", "x": 60, "y": 210, "w": 100, "h": 44}]),
             b["layout"].update({"no_overlap_pairs": [["t1", "t2"]]}))),
         "FAIL", "HG-RSP-04"),
        ("responsive/small-target", "responsive",
         _mutate_vp("768x1024", lambda b: b["layout"]["targets"].append(
             {"node_id": "tiny", "x": 16, "y": 300, "w": 12, "h": 12})),
         "WARNING", "HG-RSP-05"),
        ("responsive/layout-mismatch", "responsive",
         _mutate_vp("390x844", lambda b: b["layout"].update({"expected_layout": "two-column"})),
         "FAIL", "HG-RSP-06"),
        ("motion/reduced-not-enough", "motion",
         mut(lambda b: b["motion"]["animations"][0].update({"reduced_variant": {"duration_ms": 150}})),
         "FAIL", "HG-MOT-02"),
        ("motion/infinite-over-interactive", "motion",
         mut(lambda b: b["motion"]["animations"].append({"name": "pulse", "node_id": "submit",
                                                         "duration_ms": 1000, "iterations": "infinite",
                                                         "covers_interactive": True,
                                                         "reduced_variant": {"duration_ms": 0}})),
         "FAIL", "HG-MOT-03"),
        ("motion/autoplay-no-pause", "motion",
         mut(lambda b: b["motion"]["animations"][0].update({"duration_ms": 8000})),
         "WARNING", "HG-MOT-04"),
        ("motion/unparsable-duration", "motion",
         mut(lambda b: b["motion"]["animations"][0].update({"duration_ms": "fast"})),
         "HUMAN_REVIEW_REQUIRED", "HG-MOT-06"),
        ("state/no-recovery", "state",
         mut(lambda b: b["states"].update({"transitions": [
             {"from": "idle", "to": "validating", "event": "input"},
             {"from": "validating", "to": "submitting", "event": "submit"},
             {"from": "submitting", "to": "error", "event": "mock-500"}], "submits": []})),
         "FAIL", "HG-STA-04"),
        ("state/field-error-no-message", "state",
         mut(lambda b: b["states"].update({"field_errors": [{"field": "email", "has_message": False,
                                                            "announced": True}]})),
         "FAIL", "HG-STA-05"),
        ("state/unknown-machine", "state",
         mut(lambda b: b["states"].update({"machine": "ev-v0.2"})),
         "HUMAN_REVIEW_REQUIRED", "HG-STA-07"),

        # --- 证据缺失：每门禁都必须 HUMAN_REVIEW_REQUIRED，不得 PASS ---
        ("dom_aria/no-evidence", "dom_aria", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("focus/no-evidence", "focus", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("contrast/no-evidence", "contrast", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("overflow/no-evidence", "overflow", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("motion/no-evidence", "motion", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("state/no-evidence", "state", lambda: {"fixture_id": "F-1"}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("responsive/no-evidence", "responsive", lambda: {}, "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),

        # --- 空段（有 key 无内容）同样不得 PASS ---
        ("dom_aria/empty-section", "dom_aria", lambda: {"fixture_id": "F-1", "dom": {"nodes": []}},
         "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),
        ("contrast/empty-samples", "contrast", lambda: {"fixture_id": "F-1", "contrast": {"samples": []}},
         "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),

        # --- 空转假绿：段存在但一条断言都跑不了，不得 PASS ---
        ("dom_aria/no-assertions-ran", "dom_aria",
         lambda: {"fixture_id": "F-1", "dom": {"nodes": [{"id": "wrap", "tag": "div"}]}},
         "HUMAN_REVIEW_REQUIRED", "HG-EVID-03"),
        ("focus/empty-sequence", "focus",
         mut(lambda b: b["focus"].update({"sequence": []})),
         "HUMAN_REVIEW_REQUIRED", "HG-EVID-01"),

        # --- quarantine：无法归因的失败不得当成 PASS ---
        ("dom_aria/quarantined", "dom_aria",
         mut(lambda b: b.update({"quarantine": [{"code": "ADAPTER-FLAKY", "detail": "render 不稳定"}]})),
         "QUARANTINED", "HG-QUAR-01"),
    ]
    return cases


def _mutate_vp(viewport, fn):
    def build():
        s = synthetic_bundle_set()
        fn(s[viewport])
        return s
    return build


def selftest():
    results = []
    for name, dim, builder, exp_status, exp_code in _selftest_cases():
        payload = builder()
        res = run_gate(dim, payload, thresholds=GATE_THRESHOLDS,
                       fixture={"id": (payload.get("fixture_id") if isinstance(payload, dict) else "F-1") or "F-1"})
        codes = sorted({f["code"] for f in res["findings"]})
        ok = res["status"] == exp_status and (exp_code is None or exp_code in codes)
        if exp_code is None:
            ok = ok and res["checked"] > 0   # 证明断言确实跑了，不是空转假绿
        results.append({
            "case": name,
            "gate": dim,
            "expected_status": exp_status,
            "actual_status": res["status"],
            "expected_code": exp_code,
            "actual_codes": codes,
            "checked": res["checked"],
            "ok": bool(ok),
        })
    # runner 级断言：class 内 fixture 覆盖不全 -> HG-EVID-02（不由单 bundle 门禁触发）
    missing = missing_fixtures_result("dom_aria", ["F-2", "F-3"], "form")
    missing_codes = sorted({f["code"] for f in missing["findings"]})
    results.append({
        "case": "runner/missing-fixtures",
        "gate": "dom_aria",
        "expected_status": "HUMAN_REVIEW_REQUIRED",
        "actual_status": missing["status"],
        "expected_code": "HG-EVID-02",
        "actual_codes": missing_codes,
        "checked": missing["checked"],
        "ok": missing["status"] == "HUMAN_REVIEW_REQUIRED" and "HG-EVID-02" in missing_codes,
    })

    failed = [r for r in results if not r["ok"]]
    return {"cases": results, "total": len(results), "failed": len(failed), "ok": not failed}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def load_bundles(path):
    """从目录加载 <fixture_id>/<viewport>.json；返回 {fixture_id: {viewport: bundle}}。"""
    out = {}
    if not path or not os.path.isdir(path):
        return out
    for fixture_id in sorted(os.listdir(path)):
        fdir = os.path.join(path, fixture_id)
        if not os.path.isdir(fdir):
            continue
        for fname in sorted(os.listdir(fdir)):
            if not fname.endswith(".json"):
                continue
            vp = fname[:-5]
            with open(os.path.join(fdir, fname), "r", encoding="utf-8") as fh:
                out.setdefault(fixture_id, {})[vp] = json.load(fh)
    return out


def missing_fixtures_result(dimension, fixture_ids, fixture_class=None):
    """class 内 fixture 覆盖不全时的统一结果：证据缺失，不得判 PASS。"""
    ids = sorted(str(f) for f in fixture_ids)
    return {
        "gate": dimension,
        "fixture_id": ",".join(ids),
        "viewport": None,
        "status": "HUMAN_REVIEW_REQUIRED",
        "checked": 0,
        "findings": [finding(
            "HG-EVID-02", "evidence",
            "fixture 缺少 observation bundle（%s 类覆盖不全）" % (fixture_class or "?"),
            observed={"missing_fixtures": ids},
            expected="每个 fixture 至少一份 observation bundle",
        )],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="R-HAR-2 hard gates (1-5-3)")
    ap.add_argument("cmd", choices=["selftest", "check", "schema"])
    ap.add_argument("--bundle", help="check: 单 bundle 文件路径")
    ap.add_argument("--fixture", default="F-1")
    args = ap.parse_args(argv)

    if args.cmd == "schema":
        print(json.dumps({
            "schema": SCHEMA,
            "required_viewports": REQUIRED_VIEWPORTS,
            "thresholds": GATE_THRESHOLDS,
            "gates": sorted(GATES),
            "single_bundle_gates": SINGLE_BUNDLE_GATES,
            "cross_viewport_gates": CROSS_VIEWPORT_GATES,
            "bundle_sections": ["dom", "focus", "contrast", "layout", "motion", "states", "quarantine"],
            "status_precedence": STATUS_PRECEDENCE,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.cmd == "selftest":
        res = selftest()
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if res["ok"] else 1

    if args.cmd == "check":
        if not args.bundle:
            print("check 需要 --bundle <path>")
            return 2
        with open(args.bundle, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
        out = [run_gate(g, bundle, thresholds=GATE_THRESHOLDS, fixture={"id": args.fixture})
               for g in SINGLE_BUNDLE_GATES]
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if aggregate(out) == "PASS" else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())

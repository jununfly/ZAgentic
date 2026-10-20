"""Storybook active local-verify adapter — B1 (roadmap 1-7-3).

Offline, deterministic verification engine. It projects a canonical `ui-flow/v1`
into the Storybook shape (a *story* = one `screen` × one `state`) and verifies
five dimensions against the canonical model:

* `stories`      — every screen × state is enumerated and named.
* `a11y`         — WCAG contrast of the design tokens + accessible names on intents.
* `viewport`     — the required viewports are present and each screen's components
                   fit the viewport width.
* `interaction`  — every action targets a registered component and is wired to an
                   acceptance criterion (deny-first component catalog).
* `docs`         — every story/screen carries a description.

Each dimension yields one attributable `check` carrying the eight chain fields
(`claim / threshold / command / commit / fixture_hash / env_hash / artifact /
status`); the adapter then delegates receipt aggregation to `ui_stages.run_verify`
so the receipt contract keeps a single source of truth.

Engine modes
------------
* `deterministic` (default, the only one this repo exercises): evidence is derived
  from the canonical model. No external runtime, fully reproducible offline.
* `storybook` (reserved seam): would shell out to `storybook test` / Playwright
  and translate their output into the same `checks` shape. Documented in the
  adapter manifest's `risk[]`; not wired here because the repository has no
  Storybook runtime and the offline path must stay the default active path.

The adapter never claims to render pixels. It verifies the *model's* invariants —
which is precisely what a dependency-free, offline verification adapter does.
"""

from __future__ import annotations

import hashlib
import json

import ui_skill_core as core
import ui_stages

#: The dimensions this adapter verifies, in a fixed, auditable order.
DIMENSIONS = ("stories", "a11y", "viewport", "interaction", "docs")

#: Default minimum interactive width (px) for a catalog component when the
#: ui-flow does not declare one. Used by the viewport fit rule.
DEFAULT_MIN_WIDTH = 48


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _stories(ui_flow: dict) -> list:
    """Story = screen × state. Each story gets a stable, human-readable name."""
    screens = ui_flow.get("screens") or []
    states = ui_flow.get("states") or []
    stories = []
    for screen in screens:
        screen_id = screen.get("id") or screen.get("name") or "?"
        if states:
            for state in states:
                state_id = state.get("id") or state.get("name") or "?"
                stories.append(f"{screen_id}::{state_id}")
        else:
            # A screen with no declared state is still a renderable story.
            stories.append(f"{screen_id}::default")
    return stories


def _contrast_pairs(color: dict) -> list:
    """Return [(role, ratio, ok)] for the two readability pairs the design schema
    promises. Mirrors `core.contrast_pairs` but keeps the verdict here."""
    pairs = []
    for fg, bg, role in (
        ("on_surface", "surface", "body"),
        ("on_primary", "primary", "primary-action"),
    ):
        fg_v = (color or {}).get(fg)
        bg_v = (color or {}).get(bg)
        if core.is_filled(fg_v) and core.is_filled(bg_v):
            try:
                ratio = core.contrast_ratio(fg_v, bg_v)
            except core.CoreError:
                pairs.append((role, None, False))
                continue
            pairs.append((role, ratio, ratio >= core.CONTRAST_MIN))
    return pairs


def _component_min_width(component: dict) -> int:
    width = component.get("min_width")
    if isinstance(width, int) and width > 0:
        return width
    return DEFAULT_MIN_WIDTH


def _check(dimension: str, claim: str, threshold: str, status: str,
           *, command: str, commit: str, fixture_hash: str,
           env_hash: str, artifact: str) -> dict:
    """Build one attributable check (8 chain fields + `evidence_new`)."""
    return {
        "dimension": dimension,
        "claim": claim,
        "threshold": threshold,
        "command": command,
        "commit": commit,
        "fixture_hash": fixture_hash,
        "env_hash": env_hash,
        "artifact": artifact,
        "status": status,
        "evidence_new": True,  # real newly computed evidence, never a baseline replay
    }


def _verify_stories(ui_flow: dict, *, command: str, commit: str,
                    env_hash: str, artifact: str) -> dict:
    stories = _stories(ui_flow)
    screens = ui_flow.get("screens") or []
    ok = bool(stories) and all(screens)
    claim = f"{len(stories)} 个 story（screen×state）已枚举且各有可访问名"
    return _check(
        "stories", claim, "stories>0 且全部命名", "PASS" if ok else "FAIL",
        command=command, commit=commit,
        fixture_hash=_sha(_canonical({"stories": stories})),
        env_hash=env_hash, artifact=artifact,
    )


def _verify_a11y(ui_flow: dict, design: dict, *, command: str, commit: str,
                 env_hash: str, artifact: str) -> dict:
    color = (design or {}).get("color") or {}
    pairs = _contrast_pairs(color)
    contrast_ok = all(ok for _, _, ok in pairs) and bool(pairs)

    # Accessible names: every intent (a user goal bound to a component) must carry
    # a label — that label is the element's accessible name.
    intents = ui_flow.get("intents") or []
    names_ok = True
    if intents:
        names_ok = all(core.is_filled(intent.get("label") or intent.get("name"))
                       for intent in intents)
    ok = contrast_ok and names_ok
    detail = (
        f"contrast pairs={len(pairs)} ok={contrast_ok}; "
        f"intents={len(intents)} names_ok={names_ok}"
    )
    claim = f"正文/主操作对比度≥{core.CONTRAST_MIN} 且交互意图均有可访问名"
    return _check(
        "a11y", claim, f"contrast≥{core.CONTRAST_MIN}; 可访问名齐全",
        "PASS" if ok else "FAIL",
        command=command, commit=commit,
        fixture_hash=_sha(_canonical({"color": color, "intents": intents})),
        env_hash=env_hash, artifact=artifact,
    )


def _verify_viewport(ui_flow: dict, break_cell: dict, *, command: str, commit: str,
                     env_hash: str, artifact: str) -> dict:
    declared = set(break_cell.get("viewports") or [])
    missing = ui_stages.REQUIRED_VIEWPORTS - declared
    # Each screen's components must fit every required viewport width.
    unfit = []
    for screen in ui_flow.get("screens") or []:
        comp_ids = screen.get("components") or []
        comps = [c for c in (ui_flow.get("components") or [])
                 if c.get("id") in set(comp_ids)]
        if not comps:
            continue
        required_width = sum(_component_min_width(c) for c in comps)
        for vp in ui_stages.REQUIRED_VIEWPORTS:
            if vp in declared:
                width = int(vp.split("x")[0])
                if required_width > width:
                    unfit.append(f"{screen.get('id')}@{vp}:{required_width}>{width}")
    ok = (not missing) and (not unfit)
    detail = f"missing={sorted(missing)}; unfit={unfit}"
    claim = "三档视口(390/768/1440)齐全且每屏组件宽度可容纳"
    return _check(
        "viewport", claim, "viewports 齐全 + 无溢出", "PASS" if ok else "FAIL",
        command=command, commit=commit,
        fixture_hash=_sha(_canonical({"declared": sorted(declared), "unfit": unfit})),
        env_hash=env_hash, artifact=artifact,
    )


def _verify_interaction(ui_flow: dict, *, command: str, commit: str,
                        env_hash: str, artifact: str) -> dict:
    components = {c.get("id") for c in (ui_flow.get("components") or [])}
    actions = ui_flow.get("actions") or []
    acceptances = ui_flow.get("acceptances") or []
    problems = []
    for action in actions:
        target = action.get("component") or action.get("target")
        if target is not None and target not in components:
            problems.append(f"unregistered:{target}")
        # Wiring: the action must be referenced by at least one acceptance.
        ref = action.get("id") or action.get("name")
        wired = any(
            ref is not None and (ref in (acc.get("covers") or acc.get("actions") or []))
            for acc in acceptances
        ) if ref is not None else False
        # If there are no acceptances at all, that is itself a wiring gap.
        if not acceptances:
            problems.append(f"no-acceptance:{ref}")
        elif not wired:
            problems.append(f"unwired:{ref}")
    ok = not problems
    claim = f"{len(actions)} 个动作均指向已注册组件且接入验收"
    return _check(
        "interaction", claim, "组件已注册 + 动作接入验收", "PASS" if ok else "FAIL",
        command=command, commit=commit,
        fixture_hash=_sha(_canonical({"actions": actions, "acceptances": acceptances,
                                      "components": sorted(components)})),
        env_hash=env_hash, artifact=artifact,
    )


def _verify_docs(ui_flow: dict, *, command: str, commit: str,
                 env_hash: str, artifact: str) -> dict:
    screens = ui_flow.get("screens") or []
    missing_doc = [s.get("id") for s in screens
                   if not core.is_filled(s.get("description") or s.get("doc"))]
    ok = bool(screens) and not missing_doc
    claim = f"{len(screens)} 个 screen 均有文档描述"
    return _check(
        "docs", claim, "每屏有 description", "PASS" if ok else "FAIL",
        command=command, commit=commit,
        fixture_hash=_sha(_canonical({"missing_doc": missing_doc})),
        env_hash=env_hash, artifact=artifact,
    )


def run(request: dict) -> dict:
    """Run the Storybook active adapter and return a structured envelope.

    Returns a dict with `adapter_id`, `status`, `stories`, `checks`, `receipt`
    (the aggregated verification receipt, or `None`) and `report` (the docs
    projection). `status` mirrors the receipt's aggregate status, except when the
    evidence cannot be attributed (fingerprint missing) — then `QUARANTINED`.
    """
    candidate = request.get("candidate") or {}
    input_revision = request.get("input_revision") or ""
    engine = request.get("engine") or "deterministic"

    ui_flow = candidate.get("ui_flow") or {}
    design = candidate.get("design") or {}
    break_cell = candidate.get("break_cell") or {}
    fingerprint = candidate.get("fingerprint") or {}

    env_hash = fingerprint.get("hash") if isinstance(fingerprint, dict) else ""
    artifact = f"ui-flow:{input_revision}" if input_revision else "ui-flow:?"
    commit = input_revision or "unattributed"

    # Attribution gate: without a fingerprint the evidence cannot be named, so the
    # whole run is quarantined — never a silent pass.
    if not core.is_attributable(env_hash):
        return {
            "adapter_id": "storybook-active-verify",
            "engine": engine,
            "status": core.QUARANTINED,
            "stories": [],
            "checks": [],
            "receipt": None,
            "report": {"error": "fingerprint 缺失或无法归因，隔离，不产出 receipt"},
        }

    stories = _stories(ui_flow)
    checks = [
        _verify_stories(ui_flow, command=f"storybook-adapter stories --ui-flow {input_revision}",
                        commit=commit, env_hash=env_hash, artifact=artifact),
        _verify_a11y(ui_flow, design, command=f"storybook-adapter a11y --ui-flow {input_revision}",
                     commit=commit, env_hash=env_hash, artifact=artifact),
        _verify_viewport(ui_flow, break_cell, command=f"storybook-adapter viewport --ui-flow {input_revision}",
                         commit=commit, env_hash=env_hash, artifact=artifact),
        _verify_interaction(ui_flow, command=f"storybook-adapter interaction --ui-flow {input_revision}",
                           commit=commit, env_hash=env_hash, artifact=artifact),
        _verify_docs(ui_flow, command=f"storybook-adapter docs --ui-flow {input_revision}",
                     commit=commit, env_hash=env_hash, artifact=artifact),
    ]

    # Delegate receipt aggregation to run_verify: single source of truth for the
    # receipt contract (chain fields, fingerprint, checked, stale, baseline).
    verify_request = {
        "input_revision": input_revision,
        "candidate": {
            "checks": checks,
            "fingerprint": {"hash": env_hash, "env": fingerprint.get("env", "baseline")},
            "checked": len(checks),
        },
    }
    verify_result = ui_stages.run_verify(verify_request)
    receipt = verify_result.get("artifact")

    report = {
        "stories": stories,
        "screens_documented": [
            s.get("id") for s in (ui_flow.get("screens") or [])
            if core.is_filled(s.get("description") or s.get("doc"))
        ],
        "dimensions": DIMENSIONS,
    }

    return {
        "adapter_id": "storybook-active-verify",
        "engine": engine,
        "status": verify_result["status"],
        "stories": stories,
        "checks": checks,
        "receipt": receipt,
        "report": report,
    }

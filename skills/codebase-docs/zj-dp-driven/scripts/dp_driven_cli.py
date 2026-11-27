#!/usr/bin/env python3
"""zj-dp-driven CLI — orchestration command surface (§4).

Design baseline: docs/designs/zj-dp-driven-skill-design.md §4 (orchestration loop),
§4.4 (two-layer claim), §4.5 (settlement round), §5.2 (two-stage closeout).

Every mutating subcommand runs inside `dp_driven_lock.acquire(db)` (§4.4 single-writer).
Errors surface as `E_*` codes on stderr; the exit code table lives in
references/dp_driven-cli.md. Read commands (pool/status/validate/…) print JSON to stdout.

Path discipline (SKILL.md): `$SKILL_ROOT/scripts/dp_driven_cli.py` — never assume cwd.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import dp_driven_lock
import dp_driven_optimize
from dp_driven_model import (
    CLAIM_PLAN, CLAIM_TICKET, DEFAULT_CLAIM_LEASE_SECONDS, DpDriven, DpDrivenError,
    KIND_FINDING, KIND_TICKET, SETTLEMENT_AGENT,
)


# ── helpers ──────────────────────────────────────────────

def _parse_ref(ref: str) -> tuple[str, int]:
    if ":" not in ref:
        raise SystemExit(f"E_USAGE: 期望 kind:id，收到 {ref!r}")
    kind, raw = ref.split(":", 1)
    if kind not in (KIND_TICKET, KIND_FINDING):
        raise SystemExit(f"E_USAGE: kind ∈ {KIND_TICKET}|{KIND_FINDING}，收到 {kind!r}")
    return kind, int(raw)


def _open_model(db: str) -> DpDriven:
    return DpDriven.open(db)


def _emit(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


# ── subcommand handlers ─────────────────────────────────

def cmd_init(args):
    with dp_driven_lock.acquire(args.db):
        model = DpDriven.init(args.db, destination=args.destination)
    _emit({"ok": True, "db": model.db_path, "destination": args.destination})


def cmd_task_add(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        tid = m.add_task(name=args.name, context_md=args.context_md, memory_md=args.memory_md,
                         derived_from_finding=args.derived_from_finding)
        m.save()
    _emit({"task_id": tid})


def cmd_task_status(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.set_plan_status(args.task_id, args.set, summary=args.summary, agent=args.agent)
        m.save()
    _emit({"ok": True, "task_id": args.task_id, "status": args.set})


def cmd_task_summary(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.plan_summary(args.task_id, args.text)
        m.save()
    _emit({"ok": True, "task_id": args.task_id})


def cmd_task_view(args):
    m = _open_model(args.db)
    _emit(m.task_view(args.task_id))


def cmd_finding_add(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        fid = m.add_finding(md_path=args.md_path, external_hold=args.external_hold,
                            derived_from_finding=args.derived_from_finding)
        m.save()
    _emit({"finding_id": fid})


def cmd_finding_dispose(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.dispose_finding(args.finding_id, to=args.to)   # §4.4 lock-free
        m.save()
    _emit({"ok": True, "finding_id": args.finding_id, "status": args.to})


def cmd_finding_membership_add(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.add_finding_membership(args.finding_id, args.task_id)   # §4.4 lock-free
        m.save()
    _emit({"ok": True})


def cmd_finding_membership_remove(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.remove_finding_membership(args.finding_id, args.task_id)
        m.save()
    _emit({"ok": True})


def cmd_ticket_add(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        kv = json.loads(args.kv) if args.kv else None
        tkid = m.add_ticket(
            ref=args.ref, kv=kv, md_path=args.md_path,
            derived_from_finding=args.derived_from_finding,
            parent_id=args.parent, task_id=args.task,
            external_hold=args.external_hold,
        )
        m.save()
    _emit({"ticket_id": tkid})


def cmd_ticket_assign(args):
    tid = None if args.task in (None, "NULL", "null") else int(args.task)
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.assign_ticket(args.ticket_id, tid)   # §4.3 hotplug / §4.4 lock-free
        m.save()
    _emit({"ok": True, "ticket_id": args.ticket_id, "task_id": tid})


def cmd_ticket_status(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.set_ticket_status(args.ticket_id, args.set, agent=args.agent)
        m.save()
    _emit({"ok": True, "ticket_id": args.ticket_id, "status": args.set})


def cmd_blocks_add(args):
    fk, fi = _parse_ref(args.from_ref)
    tk, ti = _parse_ref(args.to_ref)
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        eid = m.add_blocks(fk, fi, tk, ti)
        m.save()
    _emit({"edge_id": eid})


def cmd_edge_remove(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.remove_edge(args.edge_id)
        m.save()
    _emit({"ok": True})


def cmd_external_hold(args):
    kind, nid = _parse_ref(args.ref)
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        m.set_external_hold(kind, nid, reason=args.reason or None)
        m.save()
    _emit({"ok": True, "kind": kind, "id": nid, "hold": args.reason or None})


def cmd_status(args):
    kind, nid = _parse_ref(args.ref)
    m = _open_model(args.db)
    _emit(m.node_view(kind, nid))


def cmd_pool(args):
    m = _open_model(args.db)
    _emit(m.pool())


def cmd_validate(args):
    m = _open_model(args.db)
    errs = m.validate()
    _emit({"ok": not errs, "errors": errs})


def cmd_complete_check(args):
    m = _open_model(args.db)
    _emit({"is_complete": m.is_complete(),
           "plans": {p["task_id"]: p["status"] for p in m.data["plans"].values()}})


# ── claims (§4.4) ────────────────────────────────────────

def _epoch(args):
    """§4.4 lease clock: use --now EPOCH when given (tests/replay), else wall clock.
    The *model* never reads wall clock — only the CLI does (§4.4 / determinism)."""
    return args.now if getattr(args, "now", None) is not None else int(time.time())


def cmd_claim(args):
    lease = None if args.no_lease else args.lease_seconds
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        acquired = m.claim(args.kind, args.ref_id, agent=args.agent,
                           lease_seconds=lease, epoch=_epoch(args))
        m.save()
    _emit({"ok": True, "kind": args.kind, "ref_id": args.ref_id,
           "agent": args.agent, "newly_acquired": acquired, "lease_seconds": lease})


def cmd_release(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        released = m.release(args.kind, args.ref_id, agent=args.agent, force=args.force)
        m.save()
    _emit({"ok": True, "released": released})


def cmd_renew(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        renewed = m.renew(args.kind, args.ref_id, agent=args.agent, epoch=_epoch(args))
        m.save()
    _emit({"ok": renewed, "renewed": renewed, "epoch": _epoch(args)})


def cmd_claims_list(args):
    m = _open_model(args.db)
    _emit(m.list_claims(epoch=_epoch(args)))


# ── settlement (§4.5) ────────────────────────────────────

def cmd_settlement_run(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        tid, items = m.settlement_run(name=args.name)
        m.save()
    _emit({"ok": True, "task_id": tid, "items": items})


# ── closeout (§5.2) ──────────────────────────────────────

def cmd_closeout_summary(args):
    m = _open_model(args.db)
    out = m.closeout_export_summary(args.out)
    _emit({"ok": True, "written": out})


def cmd_closeout_check(args):
    m = _open_model(args.db)
    payload = m.closeout_verify_governed(marker_path=args.marker)
    _emit({"ok": True, "marker": payload})


def cmd_closeout_delete(args):
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        deleted = m.closeout_delete_carrier(force=args.force, marker_path=args.marker)
    _emit({"ok": True, "deleted": deleted})


# ── orchestration (§4.2 optimizer) ────────────────────────

def _step_to_dict(st) -> dict:
    return {
        "action": st.action, "task_id": st.task_id,
        "items": [[k, i] for (k, i) in st.items],
        "score": (st.score.total if st.score else None),
        "factors": (st.score.factors if st.score else None),
        "rationale": st.rationale,
    }


def cmd_suggest(args):
    m = _open_model(args.db)
    steps = dp_driven_optimize.suggest(m, threshold=args.threshold, max_size=args.max_size)
    _emit({"steps": [_step_to_dict(s) for s in steps]})


def cmd_orchestrate(args):
    if not args.execute:
        # dry-run preview: read-only, no lock, no write.
        m = _open_model(args.db)
        steps = dp_driven_optimize.suggest(m, threshold=args.threshold, max_size=args.max_size)
        _emit({"executed": False, "steps": [_step_to_dict(s) for s in steps]})
        return
    with dp_driven_lock.acquire(args.db):
        m = _open_model(args.db)
        steps = dp_driven_optimize.suggest(m, threshold=args.threshold, max_size=args.max_size)
        applied = dp_driven_optimize.execute(m, steps, agent=args.agent, name=args.name)
        m.save()
    _emit({"executed": True, "applied": applied})


# ── visualization (§6) ───────────────────────────────────

def cmd_viz(args):
    m = _open_model(args.db)                      # read-only, no lock (§6 render)
    now = args.now if getattr(args, "now", None) is not None else int(time.time())
    fmt = getattr(args, "format", "mermaid") or "mermaid"
    if fmt == "html":                             # §6 R7 interactive viewer (Phase-4b)
        import dp_driven_viz_html
        assets = getattr(args, "assets", "cdn") or "cdn"
        js_text = None
        if assets == "inline":
            path = args.js_path or os.environ.get("DP_DRIVEN_MERMAID_JS")
            if not path:
                raise DpDrivenError(
                    "E_VIZ_ASSETS", "assets=inline 需 --js-path 或 env DP_DRIVEN_MERMAID_JS")
            js_text = dp_driven_viz_html.read_mermaid_js(path)  # absent → exit 3
        text = dp_driven_viz_html.render_html(m, now=now, assets=assets, mermaid_js=js_text)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
            _emit({"ok": True, "written": args.out, "format": "html", "assets": assets})
        else:
            sys.stdout.write(text)
        return
    import dp_driven_viz
    if args.out:
        path = dp_driven_viz.render_to_file(m, args.out)
        _emit({"ok": True, "written": path, "format": "mermaid"})
    else:
        sys.stdout.write(dp_driven_viz.render(m))  # stdout = the Human's live view


# ── parser wiring ────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dp_driven_cli", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_db(sp): sp.add_argument("db", help="carrier sqlite path")

    sp = sub.add_parser("init", help="§4.0 open carrier with destination")
    add_db(sp); sp.add_argument("--destination", required=True); sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("task")
    tsub = sp.add_subparsers(dest="sub", required=True)
    a = tsub.add_parser("add"); add_db(a); a.add_argument("--name", required=True)
    a.add_argument("--context-md"); a.add_argument("--memory-md")
    a.add_argument("--derived-from-finding", type=int); a.set_defaults(fn=cmd_task_add)
    s = tsub.add_parser("status"); add_db(s); s.add_argument("task_id", type=int)
    s.add_argument("--set", required=True); s.add_argument("--summary"); s.add_argument("--agent")
    s.set_defaults(fn=cmd_task_status)
    sm = tsub.add_parser("summary"); add_db(sm); sm.add_argument("task_id", type=int)
    sm.add_argument("--text", required=True); sm.set_defaults(fn=cmd_task_summary)
    v = tsub.add_parser("view"); add_db(v); v.add_argument("task_id", type=int)
    v.set_defaults(fn=cmd_task_view)

    sp = sub.add_parser("finding")
    fsub = sp.add_subparsers(dest="sub", required=True)
    a = fsub.add_parser("add"); add_db(a); a.add_argument("--md-path"); a.add_argument("--external-hold")
    a.add_argument("--derived-from-finding", type=int); a.set_defaults(fn=cmd_finding_add)
    d = fsub.add_parser("dispose"); add_db(d); d.add_argument("finding_id", type=int)
    d.add_argument("--to", required=True); d.set_defaults(fn=cmd_finding_dispose)
    ms = fsub.add_parser("membership")
    msub = ms.add_subparsers(dest="msub", required=True)
    ma = msub.add_parser("add"); add_db(ma); ma.add_argument("finding_id", type=int)
    ma.add_argument("--task", type=int, required=True); ma.set_defaults(fn=cmd_finding_membership_add)
    mr = msub.add_parser("remove"); add_db(mr); mr.add_argument("finding_id", type=int)
    mr.add_argument("--task", type=int, required=True); mr.set_defaults(fn=cmd_finding_membership_remove)

    sp = sub.add_parser("ticket")
    ksub = sp.add_subparsers(dest="sub", required=True)
    a = ksub.add_parser("add"); add_db(a); a.add_argument("--task", type=int)
    a.add_argument("--ref"); a.add_argument("--kv"); a.add_argument("--md-path")
    a.add_argument("--derived-from-finding", type=int); a.add_argument("--parent", type=int)
    a.add_argument("--external-hold"); a.set_defaults(fn=cmd_ticket_add)
    asg = ksub.add_parser("assign"); add_db(asg); asg.add_argument("ticket_id", type=int)
    asg.add_argument("--task", help="task id or NULL to release (§4.1)")
    asg.set_defaults(fn=cmd_ticket_assign)
    st = ksub.add_parser("status"); add_db(st); st.add_argument("ticket_id", type=int)
    st.add_argument("--set", required=True); st.add_argument("--agent")
    st.set_defaults(fn=cmd_ticket_status)

    sp = sub.add_parser("blocks"); bsub = sp.add_subparsers(dest="sub", required=True)
    ba = bsub.add_parser("add"); add_db(ba); ba.add_argument("--from", dest="from_ref", required=True)
    ba.add_argument("--to", dest="to_ref", required=True); ba.set_defaults(fn=cmd_blocks_add)

    sp = sub.add_parser("edge"); esub = sp.add_subparsers(dest="sub", required=True)
    er = esub.add_parser("remove"); add_db(er); er.add_argument("edge_id", type=int)
    er.set_defaults(fn=cmd_edge_remove)

    sp = sub.add_parser("hold"); add_db(sp); sp.add_argument("ref"); sp.add_argument("--reason")
    sp.set_defaults(fn=cmd_external_hold)

    sp = sub.add_parser("status"); add_db(sp); sp.add_argument("ref"); sp.set_defaults(fn=cmd_status)
    sp = sub.add_parser("pool"); add_db(sp); sp.set_defaults(fn=cmd_pool)
    sp = sub.add_parser("validate"); add_db(sp); sp.set_defaults(fn=cmd_validate)
    sp = sub.add_parser("complete-check"); add_db(sp); sp.set_defaults(fn=cmd_complete_check)

    sp = sub.add_parser("claim"); add_db(sp); sp.add_argument("kind", choices=(CLAIM_PLAN, CLAIM_TICKET))
    sp.add_argument("ref_id", type=int); sp.add_argument("--agent", required=True)
    sp.add_argument("--lease-seconds", type=int, default=DEFAULT_CLAIM_LEASE_SECONDS)
    sp.add_argument("--no-lease", action="store_true")
    sp.add_argument("--now", type=int, help="epoch seconds (default: wall clock)")
    sp.set_defaults(fn=cmd_claim)
    sp = sub.add_parser("renew"); add_db(sp); sp.add_argument("kind", choices=(CLAIM_PLAN, CLAIM_TICKET))
    sp.add_argument("ref_id", type=int); sp.add_argument("--agent", required=True)
    sp.add_argument("--now", type=int, help="epoch seconds (default: wall clock)")
    sp.set_defaults(fn=cmd_renew)
    sp = sub.add_parser("release"); add_db(sp); sp.add_argument("kind", choices=(CLAIM_PLAN, CLAIM_TICKET))
    sp.add_argument("ref_id", type=int); sp.add_argument("--agent"); sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_release)
    sp = sub.add_parser("claims"); csub = sp.add_subparsers(dest="sub", required=True)
    cl = csub.add_parser("list"); add_db(cl); cl.add_argument("--now", type=int)
    cl.set_defaults(fn=cmd_claims_list)

    sp = sub.add_parser("settlement"); ssub = sp.add_subparsers(dest="sub", required=True)
    sr = ssub.add_parser("run"); add_db(sr); sr.add_argument("--name"); sr.set_defaults(fn=cmd_settlement_run)

    sp = sub.add_parser("suggest"); add_db(sp)
    sp.add_argument("--threshold", type=float, default=dp_driven_optimize.COHESION_THRESHOLD_DEFAULT)
    sp.add_argument("--max-size", type=int, default=dp_driven_optimize.MAX_PLAN_SIZE_DEFAULT)
    sp.set_defaults(fn=cmd_suggest)
    sp = sub.add_parser("orchestrate"); add_db(sp)
    sp.add_argument("--agent"); sp.add_argument("--name"); sp.add_argument("--execute", action="store_true")
    sp.add_argument("--threshold", type=float, default=dp_driven_optimize.COHESION_THRESHOLD_DEFAULT)
    sp.add_argument("--max-size", type=int, default=dp_driven_optimize.MAX_PLAN_SIZE_DEFAULT)
    sp.set_defaults(fn=cmd_orchestrate)

    sp = sub.add_parser("viz"); add_db(sp)        # §6 read-only render
    sp.add_argument("--out"); sp.add_argument("--format", default="mermaid",
                    choices=("mermaid", "html"))  # html = §6 R7 interactive viewer
    sp.add_argument("--assets", default="cdn", choices=("cdn", "inline"))  # html 模式
    sp.add_argument("--js-path", help="inline 模式的 mermaid ESM 文件路径")
    sp.add_argument("--now", type=int, help="epoch 秒（判 claim 过期，默认当前时间）")
    sp.set_defaults(fn=cmd_viz)

    sp = sub.add_parser("closeout"); cosub = sp.add_subparsers(dest="sub", required=True)
    cs = cosub.add_parser("summary"); add_db(cs); cs.add_argument("--out", required=True)
    cs.set_defaults(fn=cmd_closeout_summary)
    cc = cosub.add_parser("check"); add_db(cc); cc.add_argument("--marker")
    cc.set_defaults(fn=cmd_closeout_check)
    cd = cosub.add_parser("delete"); add_db(cd); cd.add_argument("--marker"); cd.add_argument("--force", action="store_true")
    cd.set_defaults(fn=cmd_closeout_delete)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.fn(args)
        return 0
    except FileNotFoundError as e:
        sys.stderr.write(f"E_DB_MISSING: {e}\n")
        return 3
    except dp_driven_lock.LockTimeout as e:
        sys.stderr.write(f"E_LOCK_TIMEOUT: {e}\n")
        return 4
    except DpDrivenError as e:
        sys.stderr.write(f"{e.code}: {e.message}\n")
        return 2
    except SystemExit as e:
        # argparse already printed; propagate usage errors as code 1.
        if isinstance(e.code, int):
            return e.code
        sys.stderr.write(f"E_USAGE: {e.code}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Produce a read-only documentation governance proposal for one repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


POINTER_RE = re.compile(r"(?im)^\s*docs-map:\s*([^\s`]+)\s*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
AUTHORITY_RE = re.compile(r"authority-id:\s*`?([A-Za-z0-9._-]+)`?", re.I)
RETIRED_RE = re.compile(r"retired-to:\s*`?([^`\s]+)`?", re.I)
EVIDENCE_NAMES = {"artifacts", "evidence", "evaluations", "fixtures", "skills-outputs", "test-results"}
# Output-zone default, relative to the GOVERNED REPO ROOT (issue #275 Fix 6):
# resolve through resolve_out_base, never against CWD.
DEFAULT_OUT = Path("tmp/skills-outputs/zj-docs-ontology")


def resolve_out_base(root: Path, out: Path | None) -> Path:
    """Output-zone base directory. The launch directory is not an input.

    The default and any relative ``--out`` anchor to the governed repo root,
    so the SKILL.md-declared checklist path cannot drift with where the CLI
    was started. An absolute ``--out`` is honored as given.
    """
    base = out if out is not None else DEFAULT_OUT
    if base.is_absolute():
        return base
    return root / base
# Ruling 1 (v4): the category set ships inside the skill as a sibling of this
# script's parent — never CWD, never the target repo root. Runtime closure.
DEFAULT_PRESET = Path(__file__).resolve().parents[1] / "references" / "canonical-preset.json"
TOPIC_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOPIC_BANNED = re.compile(r"(?:\d{4}-\d{2}-\d{2}|\d{8}|[0-9a-f]{7,40}|-v\d+|-done$|-draft$|-active$)", re.I)


def load_preset(path: Path | None = None) -> dict | None:
    """Load the canonical preset; a missing/invalid file is a signal, not a
    fallback to hardcoded constants (Ruling 1, DECISIONS v4 line 80).

    Returns the parsed preset, or None on failure. The caller emits
    PRESET_UNAVAILABLE and makes no category claims when this is None.
    """
    target = path or DEFAULT_PRESET
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def preset_unavailable_diagnostic(path: Path) -> dict[str, str]:
    """The signal emitted when the preset is absent or unreadable."""
    return {
        "code": "PRESET_UNAVAILABLE",
        "path": str(path),
        "message": "canonical preset unavailable; no category claims are made, no hardcoded fallback used",
    }


def preset_categories(preset: dict | None) -> tuple[list[str], list[str]]:
    """Derive the long-lived / process category names from the preset.

    With no preset the caller gets two empty lists — never a hardcoded
    vocabulary — so inventory makes no category claims.
    """
    if preset is None:
        return [], []
    categories = preset.get("categories", {})
    long_lived = list(categories.get("long_lived", []))
    process = list(categories.get("process", []))
    return long_lived, process


# --- Ruling 1: canonical preset (normative) + HEAD roster (observed) ---------
GEN_BLOCK_RE = re.compile(r"<!-- BASE_RULES_START -->.*?```json\s*\n(.*?)\n```", re.S)
FIELD_RE = re.compile(r"^\s*([a-z][a-z0-9_-]*):\s*(.*?)\s*$")


def shared_vocabulary() -> tuple[set[str], set[str]]:
    """Read doc-kind / authority closed vocabularies from the inline shared
    core in this skill's SKILL.md (generated from skill-conventions.json).

    Runtime closure: the source is a sibling of this script inside the install
    unit — never CWD, never the target repo. doc-kind and authority are shared
    cross-skill rules, not ontology-private data; the preset holds the private
    per-kind placement vocabulary. An unreadable core yields empty sets and the
    caller makes no vocabulary claims (never a hardcoded fallback).
    """
    skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
    try:
        match = GEN_BLOCK_RE.search(skill_md.read_text(encoding="utf-8"))
        core = json.loads(match.group(1))["core"] if match else {}
    except (OSError, ValueError, KeyError):
        return set(), set()
    doc_kinds = set(core.get("doc-kind", {}).get("values", []))
    authorities = set(core.get("authority", {}).get("values", []))
    return doc_kinds, authorities


def front_matter(page: Path) -> dict[str, list[str]]:
    """Parse the leading `---` block only. Repeated keys are kept as a list so
    `authority-id` count is checkable without depending on YAML libraries."""
    text = page.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}
    fields: dict[str, list[str]] = {}
    for line in parts[1].splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields.setdefault(match.group(1).lower(), []).append(match.group(2).strip())
    return fields


def scan_page_vocabulary(
    root: Path,
    preset: dict | None,
    process_names: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    """Case 2b (Ruling 1): closed-vocabulary breaches → ERROR; permitted
    divergence → signal. Reads living pages' front matter only; evidence and
    process surfaces stay unread. Returns (diagnostics, read_paths).

    Vocabulary sources: doc-kind + authority sets from the inline shared core;
    per-kind template rows from the canonical preset's `kinds`. No set is
    hardcoded here — an absent source makes no claim rather than falling back.
    """
    doc_kinds, authorities = shared_vocabulary()
    kinds_rows = set(preset.get("kinds", {})) if preset else set()
    diagnostics: list[dict[str, str]] = []
    reads: list[str] = []
    if not doc_kinds and not authorities and not kinds_rows:
        return diagnostics, reads
    map_path: Path | None = None
    for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
        candidate = root / name
        if candidate.is_file():
            for value in POINTER_RE.findall(candidate.read_text(encoding="utf-8")):
                target = resolve(root, value, root)
                if target and target.is_file() and target.suffix == ".md":
                    map_path = target
            if candidate.is_file():
                reads.append(relative(root, candidate))
    for md in sorted(root.rglob("*.md")):
        rel = relative(root, md)
        if md == map_path or md.suffix != ".md":
            continue
        if any(part in EVIDENCE_NAMES or part in process_names for part in rel.split("/")):
            continue
        fields = front_matter(md)
        if not fields:
            continue
        reads.append(rel)
        kind_values = fields.get("doc-kind", [])
        for value in kind_values:
            if doc_kinds and value not in doc_kinds:
                diagnostics.append({
                    "code": "PRESET_VOCABULARY_VIOLATION", "path": rel,
                    "message": (
                        f"doc-kind '{value}' outside the closed vocabulary "
                        f"(canonical-preset.json#/kinds / core.doc-kind.values) at {rel}"
                    ),
                })
            elif kinds_rows and value not in kinds_rows:
                diagnostics.append({
                    "code": "PRESET_VOCABULARY_VIOLATION", "path": rel,
                    "message": f"doc-kind '{value}' has no template row (canonical-preset.json#/kinds) at {rel}",
                })
        for value in fields.get("authority", []):
            if authorities and value not in authorities:
                diagnostics.append({
                    "code": "PRESET_VOCABULARY_VIOLATION", "path": rel,
                    "message": f"authority '{value}' outside shared core vocabulary (core.authority.values) at {rel}",
                })
        if "primary" in fields.get("authority", []):
            id_count = len([v for v in fields.get("authority-id", []) if v])
            if id_count != 1:
                diagnostics.append({
                    "code": "PRESET_VOCABULARY_VIOLATION", "path": rel,
                    "message": f"primary page declares {id_count} authority-id values (core.authority.binding requires exactly 1) at {rel}",
                })
    return diagnostics, reads


def scan_preset_divergence(
    root: Path,
    preset: dict | None,
    long_lived_names: list[str],
) -> list[dict[str, str]]:
    """Case 2b2: a target repo may legitimately omit preset long-lived
    categories (e.g. ontology is ZAgentic-local). Signal, never auto-repair;
    name the exact preset key so the report is actionable."""
    if preset is None:
        return []
    docs = root / "docs"
    missing = sorted(name for name in long_lived_names if not (docs / name).is_dir())
    if not missing:
        return []
    return [{
        "code": "PRESET_DIVERGENCE", "path": "docs",
        "message": (
            "target repo omits preset long-lived categories "
            f"canonical-preset.json#/categories/long_lived: {', '.join(missing)}; "
            "permitted divergence, not auto-repaired"
        ),
    }]


def head_roster(root: Path) -> set[str] | None:
    """Observed reference: `git ls-tree -r --name-only HEAD`.

    Returns None when there is no HEAD at all (first setup — the roster is not
    applicable) or git is unavailable, so no disappearance claim is made. An
    empty set means a real commit exists but tracks nothing.
    """
    env = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
    try:
        proc = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"],
            cwd=root, env=env, capture_output=True, text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def bootstrap_from_preset(preset: dict | None) -> dict[str, object] | None:
    """Case 1: on first setup the preset is the baseline, not an empty HEAD."""
    if preset is None:
        return None
    categories = preset.get("categories", {})
    kinds = preset.get("kinds", {})
    return {
        "source": str(DEFAULT_PRESET),
        "categories": {
            "long_lived": list(categories.get("long_lived", [])),
            "process": list(categories.get("process", [])),
        },
        "kinds": sorted(kinds),
    }


def detect_pending_moves(root: Path) -> list[dict[str, str]]:
    """Git-native rename evidence (issue #275 defect B, revising Ruling v7).

    Two sources, both git's own declarations — never content-hash pairing:
      - `git status --porcelain=v1 -z`: staged renames (`git mv`);
      - `git diff --name-status -M HEAD`: unstaged worktree renames.
    Orientation is normalized by worktree existence: the "from" side is the
    HEAD-tracked path that vanished, so field-order differences across git
    versions cannot flip the meaning.
    """
    env = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
    pairs: list[tuple[str, str]] = []
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z"],
            cwd=root, env=env, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            fields = proc.stdout.split("\0")
            index = 0
            while index < len(fields):
                entry = fields[index]
                if len(entry) >= 3 and entry[0] in ("R", "C"):
                    to_path = entry[3:]
                    from_path = fields[index + 1] if index + 1 < len(fields) else ""
                    if from_path and to_path:
                        pairs.append((from_path, to_path))
                    index += 2
                else:
                    index += 1
        proc = subprocess.run(
            ["git", "diff", "--name-status", "-M", "HEAD", "--"],
            cwd=root, env=env, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                parts = line.split("\t")
                if parts and parts[0].startswith("R") and len(parts) == 3:
                    pairs.append((parts[1], parts[2]))
    except OSError:
        return []
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for first, second in pairs:
        first_exists = (root / first).exists()
        second_exists = (root / second).exists()
        if first_exists == second_exists:
            continue  # not a worktree disappearance; nothing to adjudicate
        from_path, to_path = (second, first) if first_exists else (first, second)
        if from_path in seen:
            continue
        seen.add(from_path)
        normalized.append({"from": from_path, "to": to_path})
    return normalized


def scan_head_disappearance(
    root: Path,
    process_names: list[str],
    moves: list[dict[str, str]] | None = None,
    declared_paths: set[str] | None = None,
    pending_moves: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Observed reference: a tracked file that vanished from the working tree
    is adjudicated at three levels (issue #275 defect B):

      1. confirmed `moves` entry in the proposal → exempt (Human's decision);
      2. git-native rename evidence, not yet confirmed →
         RENAME_AWAITING_CONFIRMATION (signal) — no tombstone stub is needed;
      3. no rename evidence → UNDECLARED_RETIREMENT (ERROR, fail-closed).

    A `retired-to:` declaration in the map is the other legitimate exemption.
    Process/evidence surfaces are exempt. When no HEAD exists, no claim is made.
    """
    roster = head_roster(root)
    if roster is None:
        return []
    moves = moves or []
    exempt = {item.get("from") for item in moves if isinstance(item, dict)}
    exempt |= declared_paths or set()
    pending = {
        item.get("from") for item in (pending_moves or []) if isinstance(item, dict)
    }
    vanished = sorted(
        path for path in roster
        if not (root / path).exists()
        and path not in exempt
        and not any(part in EVIDENCE_NAMES or part in process_names for part in path.split("/"))
    )
    undeclared = [path for path in vanished if path not in pending]
    awaiting = [path for path in vanished if path in pending]
    diagnostics: list[dict[str, str]] = []
    if undeclared:
        diagnostics.append({
            "code": "UNDECLARED_RETIREMENT",
            "path": "HEAD",
            "message": (
                "tracked path(s) vanished without a retirement declaration: "
                + ", ".join(undeclared)
                + "; if this was a rename, add a `moves` entry to the confirmed proposal and re-run"
            ),
            "paths": undeclared,
        })
    if awaiting:
        diagnostics.append({
            "code": "RENAME_AWAITING_CONFIRMATION",
            "path": "HEAD",
            "message": (
                "git-detected rename(s) awaiting Human confirmation: "
                + ", ".join(awaiting)
                + "; confirm them in the confirmed proposal's `moves` to exempt — "
                "unconfirmed rename evidence is a signal, never an exemption"
            ),
            "paths": awaiting,
        })
    return diagnostics


def valid_topic(topic: str) -> bool:
    """Q3 naming-syntax core: lowercase-hyphen, no date/sha/version/status.

    A pass key is stable; a repeated pass on the same topic reuses its output
    directory. The caller supplies the topic explicitly — the tool never
    guesses one from the repository or the clock.
    """
    return bool(TOPIC_RE.fullmatch(topic)) and TOPIC_BANNED.search(topic) is None


def confirmation_id(payload: dict[str, object]) -> str:
    """Deterministic id of the confirmed proposal (Ruling 2).

    Hash of the canonical proposal JSON, computed by the tool — never supplied
    by the executor. A `--confirm` flag would be self-certification and is
    rejected. The Human confirmation itself remains an external human fact;
    this id records *which* proposal was confirmed, not that the Human was
    truthful.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_dir(path: Path) -> None:
    """mkdir that tolerates an existing dir under the local sitecustomize shim."""
    if path.is_dir():
        return
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        if not path.is_dir():
            raise


def emit_checklist(payload: dict[str, object], base: Path, topic: str) -> dict[str, object]:
    """Write the confirmed-proposal ledger + tool-derived checklist to the
    gitignored ADR 0010 output zone. No target-repo mutation (`mutations: []`)."""
    case_dir = base / topic
    ensure_dir(case_dir)
    (case_dir / "proposal.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    cid = confirmation_id(payload)
    steps: list[dict[str, object]] = [
        {"step": number, "status": "pending", "artifact": None, "confirmation_id": cid}
        for number in (1, 2, 3, 4)
    ]
    steps.append({
        "step": 5,
        "status": "pending",
        # Single basis (issue #275 defect A): the declared artifact is a bare
        # filename resolved against the case dir — emit and inspect can never
        # disagree about the path.
        "artifact": "architecture-validator.txt",
        "fingerprint": None,
        "confirmation_id": cid,
    })
    for index, action in enumerate(payload.get("proposed_actions", []), start=1):  # type: ignore[arg-type]
        steps.append({
            "step": f"action-{index}",
            "status": "pending",
            "artifact": None,
            "confirmation_id": cid,
            "action": action,
        })
    checklist = {"topic": topic, "confirmation_id": cid, "steps": steps}
    (case_dir / "checklist.json").write_text(
        json.dumps(checklist, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return checklist


def inspect_checklist(
    base: Path,
    topic: str,
    arch_witness: str | None = None,
) -> dict[str, object]:
    """Cross-check the checklist against the confirmed proposal (Rulings 2+4).

    When a checklist is supplied it is the *only* source for the Step 5
    witness — `arch_witness` is accepted for compatibility but never overrides
    it. Two live declaration sources for one fact is the drift this removes.
    """
    case_dir = base / topic
    proposal_path = case_dir / "proposal.json"
    checklist_path = case_dir / "checklist.json"
    unwitnessed: dict[str, object] = {
        "status": "not-declared", "artifact": None, "exists": False,
        "fingerprint": None, "expected_fingerprint": None,
    }
    diagnostics: list[dict[str, str]] = []
    if not proposal_path.is_file() or not checklist_path.is_file():
        diagnostics.append({
            "code": "CONFIRMATION_BASELINE_LOST",
            "path": str(case_dir),
            "message": "confirmed proposal or checklist missing; checklist claims are not made",
        })
        return {"witness": unwitnessed, "diagnostics": diagnostics, "status": "lost"}
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
    expected = confirmation_id(proposal)
    if checklist.get("confirmation_id") != expected:
        diagnostics.append({
            "code": "UNCONFIRMED_MUTATION",
            "path": str(checklist_path),
            "message": "checklist confirmation_id does not match the confirmed proposal",
        })
    witness = unwitnessed
    for step in checklist.get("steps", []):
        artifact = step.get("artifact")
        target = Path(str(artifact)) if artifact else None
        if target is not None and not target.is_absolute():
            target = case_dir / target
        exists = target is not None and target.is_file()
        if step.get("step") == 5:
            # Tool-declared path: existence is checked regardless of the
            # executor's status, so an honest `skipped` is still exposed.
            if not exists:
                diagnostics.append({
                    "code": "EXEC_STEP5_ARTIFACT_MISSING",
                    "path": str(artifact),
                    "message": "declared Step 5 architecture-witness artifact does not exist",
                })
            else:
                actual = hashlib.sha256(target.read_bytes()).hexdigest()  # type: ignore[union-attr]
                expected_fp = step.get("fingerprint")
                if expected_fp is not None and expected_fp != actual:
                    diagnostics.append({
                        "code": "EXEC_STEP5_FINGERPRINT_MISMATCH",
                        "path": str(artifact),
                        "message": f"Step 5 witness fingerprint mismatch: expected {expected_fp}, got {actual}",
                    })
                witness = {
                    "status": "checklist",
                    "artifact": str(artifact),
                    "exists": True,
                    "fingerprint": actual,
                    "expected_fingerprint": expected_fp,
                }
        elif step.get("status") == "done" and not exists:
            diagnostics.append({
                "code": "EXEC_CHECKLIST_STEP_UNBACKED",
                "path": str(step.get("step")),
                "message": f"step {step.get('step')} marked done with no existing artifact",
            })
    return {"witness": witness, "diagnostics": diagnostics, "status": "checked"}


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, value: str, base: Path) -> Path | None:
    if value.startswith(("http://", "https://", "mailto:", "#")):
        return None
    candidate = (base / value.split("#", 1)[0]).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def read_pointers(root: Path) -> tuple[list[Path], list[dict[str, str]], list[str]]:
    pointers: list[Path] = []
    diagnostics: list[dict[str, str]] = []
    reads: list[str] = []
    for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
        path = root / name
        if not path.is_file():
            continue
        reads.append(relative(root, path))
        for value in POINTER_RE.findall(path.read_text(encoding="utf-8")):
            target = resolve(root, value, root)
            if target and target.is_file():
                pointers.append(target)
            else:
                diagnostics.append({"code": "MAP_POINTER_BROKEN", "path": name, "message": f"docs-map target does not exist: {value}"})
    return pointers, diagnostics, reads


def discover(root: Path) -> tuple[Path | None, str, list[dict[str, str]], list[str]]:
    pointers, diagnostics, reads = read_pointers(root)
    unique = sorted(set(pointers))
    if len(unique) == 1:
        return unique[0], "explicit-pointer", diagnostics, reads
    if len(unique) > 1:
        diagnostics.append({"code": "MAP_AMBIGUOUS", "path": ".", "message": "multiple distinct explicit docs-map pointers"})
        return None, "ambiguous", diagnostics, reads
    default = root / "docs" / "README.md"
    if default.is_file():
        return default, "default", diagnostics, reads
    candidates = sorted((root / "docs").glob("**/*-map.md")) if (root / "docs").is_dir() else []
    if len(candidates) == 1:
        return candidates[0], "candidate", diagnostics, reads
    if len(candidates) > 1:
        diagnostics.append({"code": "MAP_AMBIGUOUS", "path": "docs", "message": "multiple compatible map candidates"})
        return None, "ambiguous", diagnostics, reads
    return None, "greenfield", diagnostics, reads


def map_links(root: Path, path: Path, reads: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Read the selected map and report link drift plus authority conflicts.

    The conflict is detected where the contract puts the binding — on the map,
    which binds one authority-id to one page — so this never has to open the
    linked pages. Page-internal `authority` declarations stay with
    `zj-docs-architecture`.
    """
    reads.append(relative(root, path))
    text = path.read_text(encoding="utf-8")
    links: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    bindings: dict[str, list[str]] = {}
    for block in re.split(r"(?m)^(?=-\s+)", text):
        authority = AUTHORITY_RE.search(block)
        for value in LINK_RE.findall(block):
            target = resolve(root, value, path.parent)
            if target is None:
                continue
            target_value = relative(root, target) if target.exists() else value
            links.append({"target": target_value, "exists": str(target.exists()).lower()})
            if not target.exists():
                diagnostics.append({"code": "MAP_LINK_BROKEN", "path": relative(root, path), "message": f"map link does not exist: {value}"})
                continue
            if authority is None:
                continue
            pages = bindings.setdefault(authority.group(1), [])
            if target_value not in pages:
                pages.append(target_value)
    for authority_id in sorted(bindings):
        pages = bindings[authority_id]
        if len(pages) > 1:
            diagnostics.append({
                "code": "MAP_AUTHORITY_CONFLICT",
                "path": relative(root, path),
                "message": f"authority-id {authority_id} is bound to more than one page: {', '.join(pages)}",
            })
    return links, diagnostics


def files_under(root: Path, directory: Path) -> list[str]:
    return sorted(relative(root, path) for path in directory.rglob("*") if path.is_file())


def inventory(root: Path, long_lived_names: list[str], process_names: list[str]) -> dict[str, object]:
    """Inventory the docs tree against preset-derived category names.

    Both name lists come from `preset_categories`; with no preset they are
    empty, so the tool makes no category claims rather than falling back to
    a hardcoded vocabulary.
    """
    docs = root / "docs"
    long_lived = {name: files_under(root, docs / name) for name in long_lived_names if (docs / name).is_dir()}
    process = {name: files_under(root, docs / name) for name in process_names if (docs / name).is_dir()}
    target_defined = []
    if docs.is_dir():
        known = set(long_lived_names) | set(process_names)
        target_defined = sorted(child.name for child in docs.iterdir() if child.is_dir() and child.name not in known)
    evidence = sorted(child.name for child in root.iterdir() if child.is_dir() and child.name in EVIDENCE_NAMES)
    root_entries = [name for name in ("ZJ-CONTEXT.md", "ZJ-CONTEXT-MAP.md") if (root / name).is_file()]
    return {"long_lived": long_lived, "process_material": process, "target_defined_categories": target_defined, "evidence_surfaces": evidence, "root_entries": root_entries}


def scan_retirement(root: Path, map_path: Path, process_names: list[str]) -> tuple[dict[str, object] | None, list[dict[str, str]]]:
    """Mechanical surface of the retirement contract (governance-contract.md,
    "Retirement").

    A map entry declares retirement with `retired-to:`. Three things are then
    checkable without reading page front matter: the named destination must
    exist, the declaration must name a page, and inbound references from
    living pages must drain before the page is a deletion candidate. Evidence
    and process-material surfaces are skipped — frozen records and transient
    plans are not living references, and reading them would cross the read
    boundary.
    """
    text = map_path.read_text(encoding="utf-8")
    diagnostics: list[dict[str, str]] = []
    entries: list[dict[str, object]] = []
    for block in re.split(r"(?m)^(?=-\s+)", text):
        retired = RETIRED_RE.search(block)
        if retired is None:
            continue
        page: Path | None = None
        for value in LINK_RE.findall(block):
            target = resolve(root, value, map_path.parent)
            if target is not None and target.is_file() and target.suffix == ".md":
                page = target
                break
        if page is None:
            diagnostics.append({
                "code": "RETIRE_DECLARATION_INCOMPLETE",
                "path": relative(root, map_path),
                "message": "retired-to without a resolvable page link in the same map entry",
            })
            continue
        target_value = retired.group(1)
        target = resolve(root, target_value, map_path.parent)
        target_exists = target is not None and target.is_file()
        if not target_exists and not target_value.startswith(("http://", "https://", "#")):
            diagnostics.append({
                "code": "RETIRE_TARGET_MISSING",
                "path": relative(root, map_path),
                "message": f"retired-to target does not exist: {target_value}",
            })
        entries.append({"page_path": page, "page": relative(root, page), "target": target_value, "target_exists": target_exists})
    if not entries:
        return None, diagnostics
    scanned = 0
    for md in sorted(root.rglob("*.md")):
        if md == map_path or md.suffix != ".md":
            continue
        rel_parts = relative(root, md).split("/")
        if any(part in EVIDENCE_NAMES or part in process_names for part in rel_parts):
            continue
        scanned += 1
        body = md.read_text(encoding="utf-8")
        for value in LINK_RE.findall(body):
            resolved = resolve(root, value, md.parent)
            if resolved is None:
                continue
            for entry in entries:
                if resolved == entry["page_path"] and md != entry["page_path"]:
                    entry["inbound_sources"] = sorted(set(entry.get("inbound_sources", [])) | {relative(root, md)})  # type: ignore[union-attr]
    for entry in entries:
        sources = entry.pop("page_path")  # type: ignore[arg-type,misc]
        del sources
        inbound = len(entry.get("inbound_sources", []))  # type: ignore[arg-type]
        entry["inbound_count"] = inbound
        entry["status"] = "deletion-candidate" if (entry["target_exists"] and inbound == 0) else "drain-in-progress"
        if inbound:
            diagnostics.append({
                "code": "RETIRE_DRAIN_INCOMPLETE",
                "path": entry["page"],  # type: ignore[typeddict-item]
                "message": f"{entry['page']} still receives {inbound} inbound reference(s) from: {', '.join(entry['inbound_sources'])}",  # type: ignore[index]
            })
    return {"entries": entries, "scanned_files": scanned}, diagnostics


def architecture_witness(
    base: Path,
    artifact: str | None,
    fingerprint: str | None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    """Witness for the Step 5 `/zj-docs-architecture` composition (P0 ruling 3).

    Existence is an external mechanical fact → ERROR. Fingerprint equality is
    in-pass self-certification → signal. The artifact is caller-supplied: this
    tool never imports or invokes the architecture skill, and it records only
    a file's digest — it does not open, parse, or inventory the artifact.
    A call with no declaration is not an error: the tool cannot know whether
    this pass was a full governance pass.
    `base` is the checklist output zone: relative witness paths resolve
    against it (single basis, issue #275 defect A) — never against the repo
    root.
    """
    if artifact is None:
        return ({"status": "not-declared", "artifact": None, "exists": False, "fingerprint": None, "expected_fingerprint": None}, [])
    declared = artifact
    target = Path(artifact)
    if not target.is_absolute():
        # Single basis (issue #275 defect A): relative witness paths resolve
        # against the checklist output zone — the same basis the checklist's
        # Step 5 artifact uses — never against the repo root.
        target = base / target
    exists = target.is_file()
    actual = hashlib.sha256(target.read_bytes()).hexdigest() if exists else None
    witness: dict[str, object] = {
        "status": "declared",
        "artifact": declared,
        "exists": exists,
        "fingerprint": actual,
        "expected_fingerprint": fingerprint,
    }
    diagnostics: list[dict[str, str]] = []
    if not exists:
        diagnostics.append({
            "code": "EXEC_STEP5_ARTIFACT_MISSING",
            "path": declared,
            "message": f"declared architecture-witness artifact does not exist: {declared}",
        })
    elif fingerprint is not None and fingerprint != actual:
        diagnostics.append({
            "code": "EXEC_STEP5_FINGERPRINT_MISMATCH",
            "path": declared,
            "message": f"architecture-witness fingerprint mismatch: expected {fingerprint}, got {actual}",
        })
    return witness, diagnostics


def report(
    root: Path,
    validate_links: bool,
    arch_witness: str | None = None,
    arch_fingerprint: str | None = None,
    topic: str | None = None,
    out: Path | None = None,
    preset_path: Path | None = None,
    proposal: dict[str, object] | None = None,
) -> dict[str, object]:
    selected, origin, diagnostics, reads = discover(root)
    preset = load_preset(preset_path)
    if preset is None:
        diagnostics.append(preset_unavailable_diagnostic(preset_path or DEFAULT_PRESET))
    long_lived_names, process_names = preset_categories(preset)
    # Ruling 1: observed reference is the HEAD roster; None means not applicable.
    roster = head_roster(root)
    first_setup = roster is None or roster == set()
    # Ruling v7: rename exemptions come from the confirmed proposal's `moves`.
    moves = list(proposal.get("moves", [])) if proposal else []  # type: ignore[arg-type]
    checklist_result: dict[str, object] | None = None
    if validate_links and topic is not None:
        # Checklist is the sole witness source when a pass topic is supplied.
        # CLI witness values are ignored, never merged — two sources for one
        # fact is the drift this design removes.
        checklist_result = inspect_checklist(resolve_out_base(root, out), topic)
        witness = checklist_result["witness"]
        diagnostics.extend(checklist_result["diagnostics"])  # type: ignore[index]
    elif validate_links:
        # Platform-layer C disclosure (issue #264): with no pass topic the tool
        # cannot check a checklist. It cannot tell a shape-only check from a
        # full pass that skipped its checklist, so this stays a signal (exit 0)
        # for a CI / step-gate consumer to escalate — never an ERROR here.
        diagnostics.append({
            "code": "EXEC_CHECKLIST_NOT_DECLARED",
            "path": str(root.resolve()),
            "message": "validate ran with no pass topic: no execution checklist was checked; a green run here is not evidence that a full governance pass ran or that content is correct",
        })
        witness, witness_diagnostics = architecture_witness(
            resolve_out_base(root, out), arch_witness, arch_fingerprint
        )
        diagnostics.extend(witness_diagnostics)
    else:
        witness = {"status": "not-declared", "artifact": None, "exists": False, "fingerprint": None, "expected_fingerprint": None}
    proposal: dict[str, object] = {
        "repository": str(root.resolve()),
        "mode": "read-only-proposal",
        "map": relative(root, selected) if selected else None,
        "map_origin": origin,
        "inventory": inventory(root, long_lived_names, process_names),
        "canonical_preset": {
            "available": preset is not None,
            "path": str(preset_path or DEFAULT_PRESET),
            "schema_version": preset.get("schema_version") if preset else None,
            "long_lived_categories": long_lived_names,
            "process_categories": process_names,
        },
        "baseline": "not-applicable" if first_setup else "head-roster",
        "bootstrap": bootstrap_from_preset(preset) if first_setup else None,
        "diagnostics": diagnostics,
        "proposed_actions": [],
        "mutations": [],
        "read_paths": reads,
        "architecture_witness": witness,
        "checklist": {
            "topic": topic,
            "status": checklist_result["status"] if checklist_result else ("not-declared" if validate_links else None),
        },
    }
    if selected is None:
        if origin == "greenfield":
            proposal["proposed_actions"] = [{"action": "create-map", "target": "docs/README.md", "confirmation": "Human confirms the proposed map and lazy category creation"}]
        else:
            proposal["proposed_actions"] = [{"action": "resolve-map", "confirmation": "Human selects one map before any writes"}]
        return proposal
    if validate_links:
        links, link_diagnostics = map_links(root, selected, reads)
        proposal["map_links"] = links
        proposal["diagnostics"].extend(link_diagnostics)  # type: ignore[index]
        retirement, retire_diagnostics = scan_retirement(root, selected, process_names)
        if retirement is not None:
            proposal["retirement"] = retirement
        proposal["diagnostics"].extend(retire_diagnostics)  # type: ignore[index]
        # Ruling 1 — case 2b: closed-vocabulary breaches are ERROR, permitted
        # divergence is a signal. Both read living pages' front matter only.
        vocab_diagnostics, vocab_reads = scan_page_vocabulary(root, preset, process_names)
        proposal["diagnostics"].extend(vocab_diagnostics)  # type: ignore[index]
        for read in vocab_reads:
            if read not in reads:
                reads.append(read)
        if preset is not None:
            proposal["diagnostics"].extend(  # type: ignore[index]
                scan_preset_divergence(root, preset, long_lived_names)
            )
        # Ruling 1 — observed reference: first setup emits a signal and makes
        # no disappearance claim; an established HEAD checks vanished paths.
        if first_setup:
            proposal["diagnostics"].append({  # type: ignore[index]
                "code": "BASELINE_NOT_APPLICABLE",
                "path": "HEAD",
                "message": "no HEAD roster yet (first setup): preset is the baseline; no disappearance claim is made",
            })
        else:
            declared_paths = {
                entry["page"] for entry in (retirement or {}).get("entries", [])  # type: ignore[union-attr]
            }
            # Git-native rename evidence (issue #275 defect B): renames the
            # tool detected itself, minus the ones the Human already confirmed
            # in the proposal's `moves`. Surfaced in the report so a consumer
            # sees what awaits confirmation.
            confirmed_from = {
                item.get("from") for item in moves if isinstance(item, dict)
            }
            pending_moves = [
                item for item in detect_pending_moves(root)
                if item.get("from") not in confirmed_from
            ]
            proposal["pending_moves"] = pending_moves
            proposal["diagnostics"].extend(  # type: ignore[index]
                scan_head_disappearance(
                    root, process_names, moves, declared_paths, pending_moves
                )
            )
    process_paths = [path for paths in proposal["inventory"]["process_material"].values() for path in paths]  # type: ignore[index,union-attr]
    if process_paths:
        proposal["proposed_actions"] = [{"action": "review-process-material", "targets": process_paths, "confirmation": "Human confirms any durable extraction and each deletion candidate"}]
    return proposal


# P0 ruling "Exit-code whitelist": ERROR codes are explicit, not a prefix
# guess that silently exits 0 for a newly added gate. Signal codes stay exit 0.
ERROR_CODES = frozenset({
    "UNDECLARED_RETIREMENT",
    "UNCONFIRMED_MUTATION",
    "EXEC_STEP5_ARTIFACT_MISSING",
    "EXEC_CHECKLIST_STEP_UNBACKED",
    "PRESET_VOCABULARY_VIOLATION",
})
SIGNAL_CODES = frozenset({
    "BASELINE_NOT_APPLICABLE",
    "CONFIRMATION_BASELINE_LOST",
    "PRESET_DIVERGENCE",
    "PRESET_UNAVAILABLE",
    "EXEC_STEP5_FINGERPRINT_MISMATCH",
    "EXEC_CHECKLIST_NOT_DECLARED",
    "RENAME_AWAITING_CONFIRMATION",
})
# Mechanical codes emitted by the current tool (prefix families), plus the
# explicit allowlist above. Kept as families so a new MAP_/RETIRE_ gate cannot
# be forgotten while the four P0 rulings are being landed slice by slice.
ERROR_PREFIXES = ("MAP_", "RETIRE_")


def has_error(payload: dict[str, object]) -> bool:
    if payload["map_origin"] == "greenfield":
        return False
    return any(
        item["code"] in ERROR_CODES or item["code"].startswith(ERROR_PREFIXES)
        for item in payload["diagnostics"]  # type: ignore[union-attr]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--proposal", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--arch-witness",
        metavar="PATH",
        help="declared path to the saved architecture-validator output (Step 5 witness)",
    )
    parser.add_argument(
        "--arch-fingerprint",
        metavar="SHA256",
        help="compatibility fallback: expected witness fingerprint when no checklist is supplied",
    )
    parser.add_argument(
        "--topic",
        metavar="NAME",
        help="pass key for the checklist (lowercase-hyphen; no date/sha/version/status)",
    )
    parser.add_argument(
        "--emit-checklist",
        action="store_true",
        help="with --proposal --topic: write proposal.json + checklist.json to the output zone",
    )
    parser.add_argument(
        "--out",
        type=Path,
        metavar="DIR",
        help=f"checklist base directory (default: {DEFAULT_OUT} under the repo root; a relative value also anchors to the repo root)",
    )
    parser.add_argument(
        "--preset",
        type=Path,
        metavar="PATH",
        help=f"canonical preset path (default: the skill-root sibling {DEFAULT_PRESET})",
    )
    args = parser.parse_args()
    if args.topic is not None and not valid_topic(args.topic):
        print(
            json.dumps({
                "error": "INVALID_TOPIC",
                "message": f"topic must be lowercase-hyphen with no date/sha/version/status token: {args.topic}",
            }, indent=2),
            file=sys.stderr,
        )
        return 2
    base = resolve_out_base(args.repo.resolve(), args.out)
    payload = report(
        args.repo.resolve(),
        validate_links=args.validate,
        arch_witness=args.arch_witness,
        arch_fingerprint=args.arch_fingerprint,
        topic=args.topic,
        out=base,
        preset_path=args.preset,
    )
    if args.proposal and args.topic and args.emit_checklist:
        emit_checklist(payload, base, args.topic)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if has_error(payload) else 0


if __name__ == "__main__":
    sys.exit(main())

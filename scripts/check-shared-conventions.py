#!/usr/bin/env python3
"""Three mechanical checks for the shared skill-conventions authority.

Repo-root, dev-time tool. Intended to be called by the consistency gate
(skill-closure-lint) and by tests; not shipped inside any skill.

Checks:
  1. Closed schema — fixed core key set, consumes ⊆ core, and no consumer's
     private ``extensions`` term leaks into the shared source or any generated
     block. The extension list in each consumer's declaration is the sole
     ban-list source of truth (no duplicated hardcoded vocabulary).
  2. Byte-equal re-render — every consuming skill's BASE_RULES block must be
     byte-for-byte what the generator produces from the rule source. Reuses the
     generator module's own functions rather than re-implementing rendering.
  3. Validator binding (canary) — prove causality: a fake architecture
     doc-kind injected into the value domain must flip the validator from
     rejecting a page that declares it to accepting it. Runs entirely in a
     temporary copy so the working tree is never touched and checks are
     parallel-safe.

Exit 0 iff all checks pass; non-zero otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DEFAULT = SCRIPT_DIR.parent

RULE_SOURCE_REL = "docs/skill-conventions/skill-conventions.json"
ARCH_SKILL_REL = "skills/codebase-docs/zj-docs-architecture"
VALID_MINIMAL_REL = f"{ARCH_SKILL_REL}/tests/fixtures/valid-minimal"
CANARY_KIND = "architecture-canary"
EXPECTED_CORE_KEYS = ["naming-syntax-core", "doc-kind", "authority"]
RULES_RE = __import__("re").compile(
    r"<!-- BASE_RULES_START -->.*?```json\n(.*?)\n```.*?<!-- BASE_RULES_END -->",
    __import__("re").DOTALL,
)


def _load_module(path: Path, name: str):
    """Load a repo script as a module (dataclass-safe: register before exec)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_generator(root: Path):
    return _load_module(root / "scripts" / "generate-shared-conventions.py", "_scc_generator")


# ---------------------------------------------------------------------------
# Check 1 — closed schema
# ---------------------------------------------------------------------------

def extension_tokens(ext: str) -> list[str]:
    """Extract concrete ban literals from one extension declaration.

    ``page-prefix:ta-/ba-/pa-`` → ``ta-``, ``ba-``, ``pa-`` (take the part
    after the colon, split on ``/``). A bare tag such as ``topic-batch-token``
    is a literal on its own. Both forms come straight from the authoritative
    declaration; no vocabulary is duplicated in this checker.
    """
    value = ext.strip()
    if ":" in value:
        tail = value.split(":", 1)[1]
        return [part.strip() for part in tail.split("/") if part.strip()]
    return [value] if value else []


def check_closed_schema(root: Path, gen) -> list[str]:
    """Fixed core keys + consumes ⊆ core + no extension leak in shared core."""
    errors: list[str] = []
    try:
        source = gen.parse_rule_source(root)
    except (OSError, ValueError) as exc:
        return [f"closed-schema: cannot read rule source: {exc}"]

    if source.get("core_keys") != EXPECTED_CORE_KEYS:
        errors.append(
            f"closed-schema: core_keys must be exactly {EXPECTED_CORE_KEYS}, "
            f"got {source.get('core_keys')}"
        )
    core = source.get("core", {})
    if set(core) != set(EXPECTED_CORE_KEYS):
        errors.append(f"closed-schema: core keys drifted: {sorted(core)}")
    for key in EXPECTED_CORE_KEYS:
        block = core.get(key)
        if isinstance(block, dict) and block.get("closed") is True:
            if not isinstance(block.get("values"), list):
                errors.append(f"closed-schema: {key}.closed but values missing")

    ban_tokens: set[str] = set()
    consumers = gen.discover_consumers(root, gen.RULE_SOURCE_REL)
    if not consumers:
        errors.append("closed-schema: no consuming skill declares rule_source")
    for skill_md, decl in consumers:
        rel = skill_md.relative_to(root).as_posix()
        consumes = decl.get("consumes", [])
        unknown = [k for k in consumes if k not in EXPECTED_CORE_KEYS]
        if unknown:
            errors.append(f"closed-schema: {rel} consumes outside core: {unknown}")
        for ext in decl.get("extensions", []):
            ban_tokens.update(extension_tokens(ext))

    # Scan only the shared core surfaces: the source core + every inlined core.
    shared_texts: list[tuple[str, str]] = [
        (RULE_SOURCE_REL, json.dumps(core, ensure_ascii=False, sort_keys=True))
    ]
    for skill_md, _ in consumers:
        text = skill_md.read_text(encoding="utf-8")
        match = RULES_RE.search(text)
        if match is None:
            errors.append(f"closed-schema: {rel} has no BASE_RULES block")
            continue
        inlined = json.loads(match.group(1)).get("core", {})
        shared_texts.append(
            (skill_md.relative_to(root).as_posix(),
             json.dumps(inlined, ensure_ascii=False, sort_keys=True))
        )
    for label, text in shared_texts:
        for token in sorted(ban_tokens):
            if token in text:
                errors.append(
                    f"closed-schema: extension literal {token!r} leaked into shared core at {label}"
                )
    return errors


# ---------------------------------------------------------------------------
# Check 2 — byte-equal re-render
# ---------------------------------------------------------------------------

def check_byte_equal(root: Path, gen) -> list[str]:
    """Every inlined block must equal a fresh render from the rule source."""
    errors: list[str] = []
    try:
        source = gen.parse_rule_source(root)
    except (OSError, ValueError) as exc:
        return [f"byte-equal: cannot read rule source: {exc}"]
    consumers = gen.discover_consumers(root, gen.RULE_SOURCE_REL)
    if not consumers:
        return ["byte-equal: no consuming skill declares rule_source"]
    for skill_md, decl in consumers:
        rel = skill_md.relative_to(root).as_posix()
        expected = gen.render_block(source, decl["consumes"])
        actual = skill_md.read_text(encoding="utf-8")
        start = actual.find(gen.START_MARKER)
        if start < 0:
            errors.append(f"byte-equal: {rel} missing BASE_RULES block")
            continue
        end_marker = actual.find(gen.END_MARKER, start)
        if end_marker < 0:
            errors.append(f"byte-equal: {rel} has START without END")
            continue
        end = end_marker + len(gen.END_MARKER)
        current = actual[start:end]
        if current != expected:
            errors.append(f"byte-equal: {rel} BASE_RULES block is stale (re-run generator)")
    return errors


# ---------------------------------------------------------------------------
# Check 3 — validator binding canary (temporary copy, no working-tree writes)
# ---------------------------------------------------------------------------

def _validator_codes(state_dir: Path, fixture: Path) -> tuple[set[str], str]:
    """Import a copied validator in a subprocess and return its diagnostics."""
    code = (
        "import sys; from pathlib import Path; "
        f"sys.path.insert(0, r'{state_dir / 'scripts'}'); "
        "import validate_architecture_docs as v; "
        f"d, _, _ = v.validate(Path(r'{fixture}')); "
        "print('|'.join(x.code for x in d))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return (
        {part for part in result.stdout.strip().split("|") if part},
        result.stdout.strip(),
    )


def _make_state(tmp: Path, tag: str, arch: Path, fixture_src: Path,
                payload: dict, inject: bool) -> tuple[Path, Path]:
    state = tmp / tag
    scripts = state / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(arch / "scripts" / "validate_architecture_docs.py",
                scripts / "validate_architecture_docs.py")
    block_payload = json.loads(json.dumps(payload))
    if inject:
        block_payload["core"]["doc-kind"]["values"].append(CANARY_KIND)
    block = (
        "<!-- BASE_RULES_START -->\n```json\n"
        + json.dumps(block_payload, ensure_ascii=False, indent=2)
        + "\n```\n<!-- BASE_RULES_END -->"
    )
    (state / "SKILL.md").write_text("# skill\n\n" + block + "\n", encoding="utf-8")
    fixture = state / "fixture"
    shutil.copytree(fixture_src, fixture)
    page = fixture / "docs" / "architecture" / "ta-overview.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(
        text.replace("doc-kind: architecture-overview", f"doc-kind: {CANARY_KIND}"),
        encoding="utf-8",
    )
    return state, fixture


def check_canary(root: Path, gen) -> list[str]:
    """Prove the validator reads the inlined doc-kind domain, not a hardcoded enum."""
    errors: list[str] = []
    arch = root / ARCH_SKILL_REL
    validator_py = arch / "scripts" / "validate_architecture_docs.py"
    skill_md = arch / "SKILL.md"
    fixture_src = root / VALID_MINIMAL_REL
    for label, path in (("validator", validator_py), ("SKILL.md", skill_md),
                        ("fixture", fixture_src)):
        if not path.exists():
            return [f"canary: missing {label} at {path}"]
    match = RULES_RE.search(skill_md.read_text(encoding="utf-8"))
    if match is None:
        return ["canary: architecture SKILL.md has no BASE_RULES block"]
    payload = json.loads(match.group(1))

    with tempfile.TemporaryDirectory(prefix="scc-canary-") as td:
        tmp = Path(td)
        try:
            base_state, base_fixture = _make_state(
                tmp, "baseline", arch, fixture_src, payload, inject=False
            )
            base_codes, base_raw = _validator_codes(base_state, base_fixture)
            if "PAGE_KIND_INVALID" not in base_codes:
                errors.append(
                    "canary: baseline did not reject the fake kind "
                    f"(expected PAGE_KIND_INVALID, got {base_raw!r})"
                )

            inj_state, inj_fixture = _make_state(
                tmp, "injected", arch, fixture_src, payload, inject=True
            )
            inj_codes, inj_raw = _validator_codes(inj_state, inj_fixture)
            if inj_codes:
                errors.append(
                    "canary: validator still rejected the injected kind "
                    f"(hardcoded enum may be in force): {inj_codes}"
                )
        except RuntimeError as exc:
            errors.append(f"canary: validator subprocess failed: {exc}")
    return errors


# ---------------------------------------------------------------------------
# Runner / CLI
# ---------------------------------------------------------------------------

def run_all(root: Path) -> dict[str, list[str]]:
    root = Path(root).resolve()
    gen = load_generator(root)
    return {
        "closed-schema": check_closed_schema(root, gen),
        "byte-equal": check_byte_equal(root, gen),
        "canary": check_canary(root, gen),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT_DEFAULT), help="repository root")
    ap.add_argument("--only", choices=["closed-schema", "byte-equal", "canary"],
                    help="run only one check (default: all)")
    args = ap.parse_args()

    results = run_all(Path(args.root))
    if args.only:
        results = {args.only: results[args.only]}

    failed = False
    for name, errors in results.items():
        if errors:
            failed = True
            print(f"FAIL {name}:")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"PASS {name}")
    if failed:
        print("shared-conventions checks FAILED", file=sys.stderr)
        return 1
    print(f"shared-conventions checks OK ({len(results)} check(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Clone the CLI into a scratch dir with *every* first-party dependency it imports.

Why this module exists
----------------------
The baseline control tests run today's CLI against a CLI pinned at a historical
commit, in two independent directories. They used to list the files to clone as
a literal 4-tuple repeated at **six** call sites. When #116 added
``roadmap_sqlite.py``, none of those six lists was updated, so the cloned
"current" CLI raised ``ModuleNotFoundError`` at import time and the control
tests went red for a reason that had nothing to do with the behavior they are
supposed to guard — a red you learn to ignore, which is worse than no red.

``current_files()`` derives the list from ``roadmap_cli.py``'s own imports, so
a future carrier module cannot be forgotten again. The *baseline* lists stay
literal and historical: a pinned commit needs exactly the modules that existed
back then, deriving them from today's import graph would be wrong.
"""

from __future__ import annotations

import ast
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def local_imports(cli_path: str | Path | None = None) -> list[str]:
    """First-party module names imported by the CLI and living in the skill dir.

    Third-party and stdlib imports are filtered out by the "has a sibling
    ``.py`` in the skill directory" test, which is exactly the closure the
    cloned directory has to satisfy.
    """
    cli = Path(cli_path) if cli_path is not None else SKILL_DIR / "roadmap_cli.py"
    tree = ast.parse(cli.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.append(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen and (SKILL_DIR / f"{name}.py").is_file():
            seen.add(name)
            ordered.append(name)
    return ordered


def current_files(skill_dir: str | Path = SKILL_DIR) -> tuple[str, ...]:
    """Every file a cloned "current" CLI needs in order to import cleanly."""
    skill = Path(skill_dir)
    required = {f"{name}.py" for name in local_imports(skill / "roadmap_cli.py")}
    required.add("roadmap_cli.py")
    return tuple(sorted(required))


def clone_current_cli(target: str | Path, skill_dir: str | Path = SKILL_DIR) -> Path:
    """Write today's CLI plus its runtime dependencies into ``target``."""
    target_dir = Path(target)
    skill = Path(skill_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in current_files(skill):
        (target_dir / name).write_text((skill / name).read_text(encoding="utf-8"), encoding="utf-8")
    return target_dir

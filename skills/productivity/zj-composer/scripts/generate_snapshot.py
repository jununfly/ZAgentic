#!/usr/bin/env python3
"""Persist an immutable, content-addressed Composer catalog snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from discover_catalog import discover_catalog  # noqa: E402


SNAPSHOT_SCHEMA = "zj-composer/catalog-snapshot/v1"
DEFAULT_OUTPUT_DIR = Path("skills-outputs/zj-composer/catalog-snapshots")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_paths(root: Path, catalog: dict[str, Any]) -> list[str]:
    surfaces = catalog["index_surfaces"]
    paths = set(surfaces["bucket_readmes"])
    paths.update(
        {
            surfaces["root_readme"],
            surfaces["guide"],
            surfaces["install_list"],
        }
    )
    paths.update(skill["path"] for skill in catalog["skills"])
    return sorted(paths)


def source_manifest(root: Path, paths: Iterable[str]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for relative in paths:
        path = root / relative
        if path.is_file():
            content = path.read_bytes()
            manifest.append(
                {
                    "path": relative,
                    "exists": True,
                    "size": len(content),
                    "sha256": sha256_bytes(content),
                }
            )
        else:
            manifest.append(
                {
                    "path": relative,
                    "exists": False,
                    "size": 0,
                    "sha256": None,
                }
            )
    return manifest


def content_digest(manifest: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(canonical)


def metadata_warnings(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for message in catalog.get("warnings", []):
        warnings.append({"code": "discovery_warning", "message": message})

    for skill in catalog["skills"]:
        path = skill["path"]
        for message in skill.get("warnings", []):
            warnings.append(
                {
                    "code": "skill_metadata_warning",
                    "path": path,
                    "message": message,
                }
            )
        for surface, present in sorted(skill["declarations"].items()):
            if not present:
                warnings.append(
                    {
                        "code": "missing_catalog_declaration",
                        "path": path,
                        "surface": surface,
                        "message": f"{skill['directory']} is not registered by {surface}",
                    }
                )

    return sorted(
        warnings,
        key=lambda item: (
            item.get("path", ""),
            item.get("code", ""),
            item.get("surface", ""),
            item["message"],
        ),
    )


def build_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    catalog = discover_catalog(root)
    files = source_manifest(root, source_paths(root, catalog))
    digest = content_digest(files)
    snapshot_id = f"catalog-v1-{digest}"
    return {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_id": snapshot_id,
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": {
            "root": ".",
            "content_digest": digest,
            "files": files,
            "discovery_schema": catalog["schema"],
        },
        "catalog": catalog,
        "metadata_warnings": metadata_warnings(catalog),
    }


def default_output(root: Path, snapshot_id: str) -> Path:
    return root / DEFAULT_OUTPUT_DIR / f"{snapshot_id}.json"


def write_snapshot(payload: dict[str, Any], output: Path) -> bool:
    """Write once; return False when the same immutable snapshot already exists."""

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"existing snapshot is unreadable: {output}: {exc}") from exc
        if (
            existing.get("schema") != payload["schema"]
            or existing.get("snapshot_id") != payload["snapshot_id"]
            or existing.get("source", {}).get("content_digest")
            != payload["source"]["content_digest"]
        ):
            raise RuntimeError(f"existing snapshot conflicts with {output}")
        return False

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(rendered)
    try:
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return True


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an immutable content-addressed Composer catalog snapshot."
    )
    default_root = Path(__file__).resolve().parents[4]
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument(
        "--output",
        type=Path,
        help="Explicit output path; defaults to skills-outputs/zj-composer/catalog-snapshots.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    payload = build_snapshot(root)
    output = (args.output or default_output(root, payload["snapshot_id"])).resolve()
    created = write_snapshot(payload, output)
    action = "written" if created else "already present"
    print(
        f"Snapshot {action}: {output} "
        f"({payload['snapshot_id']}; warnings={len(payload['metadata_warnings'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

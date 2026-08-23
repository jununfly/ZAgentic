#!/usr/bin/env python3
"""Build and read immutable Repository Map snapshot bundles."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA = "zj-repository-map-manifest/v1"
SUMMARY_SCHEMA = "zj-repository-map-summary/v1"
TREE_SCHEMA = "zj-repository-map-tree/v1"
TARGETS_SCHEMA = "zj-repository-map-targets/v1"
DEFAULT_VIEW_LIMIT = 100
DEFAULT_EXCLUDES = (".git",)
PACKAGE_MANIFESTS = {
    "package.json": "node",
    "pyproject.toml": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "composer.json": "php",
    "Package.swift": "swift",
}
WORKFLOW_FILES = {
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "pipeline.yml",
    "Makefile",
    "Taskfile.yml",
}
INTEGRATION_DIRECTORY_NAMES = {
    "adapter",
    "adapters",
    "api",
    "apis",
    "connector",
    "connectors",
    "deploy",
    "deployment",
    "docker",
    "infrastructure",
    "infra",
    "integration",
    "integrations",
    "k8s",
    "kubernetes",
    "plugins",
    "terraform",
}
LANGUAGES = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".css": "css",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".md": "markdown",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "shell",
    ".sql": "sql",
    ".swift": "swift",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".yml": "yaml",
    ".yaml": "yaml",
}


class MapError(RuntimeError):
    """A user-actionable Repository Map failure."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_id(identity: str, kind: str, path: str) -> str:
    return f"{kind}-{sha256_bytes(f'{identity}\0{kind}\0{path}'.encode('utf-8'))[:20]}"


def path_is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() or "."


def run_git(root: Path, *args: str, required: bool = True) -> str | None:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        if required:
            detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
            raise MapError(detail)
        return None
    return completed.stdout.strip()


def git_source(root: Path, ref: str) -> dict[str, Any] | None:
    if run_git(root, "rev-parse", "--show-toplevel", required=False) is None:
        return None
    commit = run_git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    head = run_git(root, "rev-parse", "HEAD")
    if commit != head:
        raise MapError(f"working tree HEAD {head} does not match requested ref {ref} ({commit})")
    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD", required=False)
    remote = run_git(root, "config", "--get", "remote.origin.url", required=False)
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all") or ""
    return {
        "repository": remote or root.name,
        "ref": branch or ref,
        "commit": commit,
        "state": "dirty" if status else "clean",
        "statusEntries": len(status.splitlines()) if status else 0,
    }


def file_hash(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as content:
        for chunk in iter(lambda: content.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def normalized_exclusions(root: Path, bundle: Path, values: Iterable[str]) -> list[tuple[str, Path]]:
    exclusions: list[tuple[str, Path]] = [(name, root / name) for name in DEFAULT_EXCLUDES]
    for value in values:
        candidate = Path(value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (root / candidate).resolve()
        if not path_is_within(resolved, root):
            raise MapError(f"exclude path is outside repository root: {value}")
        exclusions.append((relative_path(resolved, root), resolved))
    if path_is_within(bundle, root):
        exclusions.append((relative_path(bundle, root), bundle))
    unique: dict[str, Path] = {}
    for name, path in exclusions:
        unique[name] = path
    return sorted(unique.items())


def scan_tree(root: Path, exclusions: list[tuple[str, Path]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    excluded_paths = [path for _, path in exclusions]
    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []

    def on_walk_error(error: OSError) -> None:
        path = Path(error.filename) if error.filename else root
        try:
            displayed_path = relative_path(path.resolve(), root)
        except ValueError:
            displayed_path = str(path)
        unknowns.append({"kind": "unreadable-path", "path": displayed_path, "reason": str(error)})

    for current, directories, files in os.walk(root, topdown=True, onerror=on_walk_error, followlinks=False):
        current_path = Path(current)
        directories.sort()
        files.sort()
        kept_directories: list[str] = []
        for name in directories:
            path = current_path / name
            if any(path_is_within(path, excluded) for excluded in excluded_paths):
                continue
            rel = relative_path(path, root)
            try:
                mode = stat.S_IMODE(path.lstat().st_mode)
            except OSError as error:
                unknowns.append({"kind": "unreadable-path", "path": rel, "reason": str(error)})
                continue
            if path.is_symlink():
                records.append({"kind": "symlink", "path": rel, "target": os.readlink(path), "mode": mode})
                continue
            records.append({"kind": "directory", "path": rel, "mode": mode})
            kept_directories.append(name)
        directories[:] = kept_directories
        for name in files:
            path = current_path / name
            rel = relative_path(path, root)
            try:
                mode = stat.S_IMODE(path.lstat().st_mode)
                if path.is_symlink():
                    records.append({"kind": "symlink", "path": rel, "target": os.readlink(path), "mode": mode})
                    continue
                size, digest = file_hash(path)
                suffix = path.suffix.lower()
                records.append({
                    "kind": "file",
                    "path": rel,
                    "size": size,
                    "sha256": digest,
                    "extension": suffix,
                    "language": LANGUAGES.get(suffix),
                    "mode": mode,
                })
            except OSError as error:
                unknowns.append({"kind": "unreadable-path", "path": rel, "reason": str(error)})
    records.sort(key=lambda item: (item["path"], item["kind"]))
    unknowns.sort(key=lambda item: (item["path"], item["kind"]))
    return records, unknowns


def source_fingerprint(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_json({key: record.get(key) for key in ("kind", "path", "size", "sha256", "target")}))
    return digest.hexdigest()


def read_manifest_name(root: Path, path: Path, unknowns: list[dict[str, Any]]) -> tuple[str | None, str]:
    try:
        if path.name == "package.json" or path.name == "composer.json":
            value = json.loads(path.read_text(encoding="utf-8"))
            name = value.get("name") if isinstance(value, dict) else None
        elif path.name in {"pyproject.toml", "Cargo.toml"}:
            import tomllib

            value = tomllib.loads(path.read_text(encoding="utf-8"))
            if path.name == "pyproject.toml":
                name = (value.get("project") or {}).get("name")
            else:
                name = (value.get("package") or {}).get("name")
        elif path.name == "go.mod":
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()
            name = next((line.split(maxsplit=1)[1] for line in first if line.startswith("module ")), None)
        else:
            name = None
        return (name if isinstance(name, str) else None), "parsed"
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        unknowns.append({"kind": "unparsed-manifest", "path": relative_path(path, root), "reason": str(error)})
        return None, "unparsed"


def package_records(root: Path, tree: list[dict[str, Any]], unknowns: list[dict[str, Any]], identity: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in tree:
        if item["kind"] != "file":
            continue
        name = Path(item["path"]).name
        ecosystem = PACKAGE_MANIFESTS.get(name)
        if ecosystem is None:
            continue
        path = root / item["path"]
        package_name, parse_status = read_manifest_name(root, path, unknowns)
        records.append({
            "id": stable_id(identity, "package", item["path"]),
            "path": item["path"],
            "manifest": name,
            "ecosystem": ecosystem,
            "name": package_name,
            "parseStatus": parse_status,
        })
    return sorted(records, key=lambda item: item["path"])


def integration_records(tree: list[dict[str, Any]], identity: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in tree:
        path = Path(item["path"])
        parts = path.parts
        if item["kind"] == "directory" and path.name.lower() in INTEGRATION_DIRECTORY_NAMES:
            records.append({"id": stable_id(identity, "integration", item["path"]), "path": item["path"], "kind": "directory", "reason": "integration-named-directory"})
        elif item["kind"] == "file" and (path.name.startswith("Dockerfile") or path.name.lower().startswith("openapi.") or path.name.lower().startswith("docker-compose")):
            records.append({"id": stable_id(identity, "integration", item["path"]), "path": item["path"], "kind": "file", "reason": "integration-surface-file"})
        elif item["kind"] == "file" and parts and parts[0].lower() in INTEGRATION_DIRECTORY_NAMES:
            records.append({"id": stable_id(identity, "integration", item["path"]), "path": item["path"], "kind": "file", "reason": "inside-integration-directory"})
    return sorted(records, key=lambda item: (item["path"], item["kind"]))


def workflow_records(tree: list[dict[str, Any]], identity: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in tree:
        if item["kind"] != "file":
            continue
        path = Path(item["path"])
        parts = path.parts
        is_github_workflow = len(parts) >= 3 and parts[0] == ".github" and parts[1] == "workflows"
        if is_github_workflow or path.name in WORKFLOW_FILES or (parts and parts[0] == ".circleci") or (parts and parts[0] == ".buildkite"):
            records.append({"id": stable_id(identity, "workflow", item["path"]), "path": item["path"], "kind": "automation", "reason": "recognized-workflow-surface"})
    return sorted(records, key=lambda item: item["path"])


def build_targets(tree: list[dict[str, Any]], packages: list[dict[str, Any]], integrations: list[dict[str, Any]], workflows: list[dict[str, Any]], identity: str) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = [{"id": stable_id(identity, "target", "."), "kind": "root", "path": ".", "label": "Repository root", "reason": "map orientation"}]
    for item in tree:
        path = Path(item["path"])
        if item["kind"] == "directory" and len(path.parts) == 1:
            targets.append({"id": stable_id(identity, "target", f"directory:{item['path']}"), "kind": "top-level", "path": item["path"], "label": item["path"], "reason": "top-level structure"})
    for item in packages:
        targets.append({"id": stable_id(identity, "target", f"package:{item['path']}"), "kind": "package", "path": item["path"], "label": item["name"] or item["path"], "reason": f"{item['ecosystem']} package manifest"})
    for item in integrations:
        targets.append({"id": stable_id(identity, "target", f"integration:{item['path']}"), "kind": "integration", "path": item["path"], "label": item["path"], "reason": item["reason"]})
    for item in workflows:
        targets.append({"id": stable_id(identity, "target", f"workflow:{item['path']}"), "kind": "workflow", "path": item["path"], "label": item["path"], "reason": item["reason"]})
    return sorted(targets, key=lambda item: (item["kind"], item["path"], item["id"]))


def inventory(tree: list[dict[str, Any]]) -> dict[str, Any]:
    extensions = Counter(item.get("extension") for item in tree if item["kind"] == "file" and item.get("extension"))
    languages = Counter(item.get("language") for item in tree if item["kind"] == "file" and item.get("language"))
    return {
        "files": sum(item["kind"] == "file" for item in tree),
        "directories": sum(item["kind"] == "directory" for item in tree),
        "symlinks": sum(item["kind"] == "symlink" for item in tree),
        "bytes": sum(item.get("size", 0) for item in tree if item["kind"] == "file"),
        "extensions": dict(sorted(extensions.items())),
        "languages": dict(sorted(languages.items())),
    }


def render_markdown(summary: dict[str, Any], targets: list[dict[str, Any]], limit: int) -> str:
    source = summary["source"]
    inv = summary["inventory"]
    lines = [
        f"# Repository Map: {source['repository']}",
        "",
        f"- Snapshot: `{summary['snapshotId']}`",
        f"- Commit: `{source.get('commit') or 'unknown'}`",
        f"- Working tree: `{source['state']}`",
        f"- Files / directories / bytes: `{inv['files']} / {inv['directories']} / {inv['bytes']}`",
        "",
        "## Navigation targets",
        "",
    ]
    for target in targets[:limit]:
        lines.append(f"- `{target['kind']}` **{target['label']}** — `{target['path']}` — {target['reason']}")
    if len(targets) > limit:
        lines.extend(["", f"> View truncated to {limit} targets. Use `view --limit` for another bounded view."])
    lines.extend(["", "## Unknowns", ""])
    if summary["unknowns"]:
        lines.extend(f"- `{item['kind']}` `{item['path']}` — {item['reason']}" for item in summary["unknowns"][:limit])
    else:
        lines.append("- None recorded.")
    return "\n".join(lines) + "\n"


def render_html(summary: dict[str, Any], targets: list[dict[str, Any]], limit: int) -> str:
    markdown = render_markdown(summary, targets, limit)
    output = ["<!doctype html>", '<html lang="en"><meta charset="utf-8"><title>Repository Map</title><body>']
    for line in markdown.splitlines():
        escaped = html.escape(line)
        if line.startswith("# "):
            output.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            output.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            output.append(f"<li>{escaped[2:]}</li>")
        elif line.startswith("> "):
            output.append(f"<p><em>{html.escape(line[2:])}</em></p>")
        elif line:
            output.append(f"<p>{escaped}</p>")
    output.append("</body></html>\n")
    return "\n".join(output)


def jsonl(records: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def write_bundle(root: Path, bundle: Path, files: dict[str, str]) -> None:
    if bundle.exists():
        raise MapError(f"snapshot bundle already exists and is immutable: {bundle}")
    bundle.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{bundle.name}.", dir=bundle.parent))
    try:
        for name, content in files.items():
            destination = temporary / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        if bundle.exists():
            raise MapError(f"snapshot bundle appeared during publication: {bundle}")
        os.rename(temporary, bundle)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_bundle(repository: Path, bundle: Path, ref: str, extra_excludes: list[str], view_limit: int) -> dict[str, Any]:
    repository = repository.resolve()
    bundle = bundle.resolve()
    if not repository.is_dir():
        raise MapError(f"repository directory does not exist: {repository}")
    if bundle.exists():
        raise MapError(f"snapshot bundle already exists and is immutable: {bundle}")
    exclusions = normalized_exclusions(repository, bundle, extra_excludes)
    tree, unknowns = scan_tree(repository, exclusions)
    fingerprint = source_fingerprint(tree)
    source = git_source(repository, ref) or {
        "repository": repository.name,
        "ref": None,
        "commit": None,
        "state": "unversioned",
        "statusEntries": None,
    }
    source["workingTreeFingerprint"] = fingerprint
    source["identity"] = "commit-plus-working-tree" if source["commit"] else "working-tree-fingerprint"
    identity = source["commit"] or fingerprint
    packages = package_records(repository, tree, unknowns, identity)
    integrations = integration_records(tree, identity)
    workflows = workflow_records(tree, identity)
    targets = build_targets(tree, packages, integrations, workflows, identity)
    summary_without_id = {
        "schema": SUMMARY_SCHEMA,
        "source": source,
        "scope": {"root": ".", "exclusions": [name for name, _ in exclusions]},
        "inventory": inventory(tree),
        "unknowns": sorted(unknowns, key=lambda item: (item["kind"], item["path"])),
    }
    snapshot_digest = hashlib.sha256()
    for value in (source, summary_without_id["scope"], tree, packages, integrations, workflows, targets):
        snapshot_digest.update(canonical_json(value))
    snapshot_id = f"map-{snapshot_digest.hexdigest()[:24]}"
    summary = {"schema": SUMMARY_SCHEMA, "snapshotId": snapshot_id, **{key: value for key, value in summary_without_id.items() if key != "schema"}}
    targets_document = {"schema": TARGETS_SCHEMA, "snapshotId": snapshot_id, "targets": targets}
    files = {
        "facts/summary.json": json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "facts/tree.jsonl": jsonl(tree),
        "facts/packages.jsonl": jsonl(packages),
        "facts/integrations.jsonl": jsonl(integrations),
        "facts/workflows.jsonl": jsonl(workflows),
        "navigation/targets.json": json.dumps(targets_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    markdown = render_markdown(summary, targets, view_limit)
    html_view = render_html(summary, targets, view_limit)
    files["views/map.md"] = markdown
    files["views/map.html"] = html_view
    shard_metadata = []
    view_metadata = []
    for name in sorted(files):
        metadata = {"path": name, "sha256": sha256_bytes(files[name].encode("utf-8")), "bytes": len(files[name].encode("utf-8"))}
        if name.startswith("views/"):
            view_metadata.append(metadata)
        else:
            shard_metadata.append(metadata)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "kind": "repository-map",
        "snapshotId": snapshot_id,
        "source": source,
        "scope": summary["scope"],
        "shards": shard_metadata,
        "views": {"defaultTargetLimit": view_limit, "artifacts": view_metadata},
        "immutable": True,
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    write_bundle(repository, bundle, files)
    return manifest


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MapError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise MapError(f"JSON object expected: {path}")
    return value


def safe_bundle_path(bundle: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise MapError(f"bundle contains unsafe relative path: {value}")
    resolved = bundle / path
    if not path_is_within(resolved, bundle):
        raise MapError(f"bundle contains unsafe path: {value}")
    return resolved


def validate_bundle(bundle: Path) -> dict[str, Any]:
    bundle = bundle.resolve()
    manifest = read_json(bundle / "manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("kind") != "repository-map" or manifest.get("immutable") is not True:
        raise MapError(f"unsupported Repository Map manifest: {bundle / 'manifest.json'}")
    snapshot_id = manifest.get("snapshotId")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("map-"):
        raise MapError("manifest has an invalid snapshotId")
    checked = 0
    for item in manifest.get("shards", []) + manifest.get("views", {}).get("artifacts", []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise MapError("manifest contains an invalid artifact entry")
        path = safe_bundle_path(bundle, item["path"])
        if not path.is_file():
            raise MapError(f"manifest artifact is missing: {path}")
        actual = sha256_bytes(path.read_bytes())
        if actual != item["sha256"]:
            raise MapError(f"artifact SHA-256 mismatch: {path}")
        checked += 1
    targets_path = safe_bundle_path(bundle, "navigation/targets.json")
    targets = read_json(targets_path)
    if targets.get("schema") != TARGETS_SCHEMA or targets.get("snapshotId") != snapshot_id or not isinstance(targets.get("targets"), list):
        raise MapError("navigation targets do not match the manifest")
    summary = read_json(safe_bundle_path(bundle, "facts/summary.json"))
    if summary.get("schema") != SUMMARY_SCHEMA or summary.get("snapshotId") != snapshot_id:
        raise MapError("summary does not match the manifest")
    return {"valid": True, "schema": MANIFEST_SCHEMA, "snapshotId": snapshot_id, "artifactsChecked": checked, "targetCount": len(targets["targets"])}


def shard_path(manifest: dict[str, Any], name: str) -> str:
    for item in manifest.get("shards", []):
        if isinstance(item, dict) and item.get("path") == name:
            return name
    raise MapError(f"bundle has no shard: {name}")


def read_jsonl(bundle: Path, name: str, limit: int) -> list[dict[str, Any]]:
    path = safe_bundle_path(bundle, name)
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as content:
        for line in content:
            if len(records) >= limit:
                break
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def render_section(bundle: Path, manifest: dict[str, Any], section: str, limit: int, output_format: str) -> str:
    summary = read_json(safe_bundle_path(bundle, shard_path(manifest, "facts/summary.json")))
    if section == "summary":
        targets: list[dict[str, Any]] = []
    elif section == "targets":
        targets_document = read_json(safe_bundle_path(bundle, shard_path(manifest, "navigation/targets.json")))
        targets = targets_document.get("targets", [])[:limit]
    else:
        targets = read_jsonl(bundle, shard_path(manifest, f"facts/{section}.jsonl"), limit)
        targets = [{"kind": section, "label": item.get("path", ""), "path": item.get("path", ""), "reason": json.dumps(item, ensure_ascii=False, sort_keys=True)} for item in targets]
    if output_format == "html":
        return render_html(summary, targets, limit)
    return render_markdown(summary, targets, limit)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Build and inspect immutable Repository Map bundles")
    commands = root.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="scan a repository into a new snapshot bundle")
    scan.add_argument("repository", type=Path)
    scan.add_argument("bundle", type=Path)
    scan.add_argument("--ref", default="HEAD")
    scan.add_argument("--exclude", action="append", default=[])
    scan.add_argument("--view-limit", type=int, default=DEFAULT_VIEW_LIMIT)
    validate = commands.add_parser("validate", help="validate a snapshot bundle")
    validate.add_argument("bundle", type=Path)
    view = commands.add_parser("view", help="render one bounded view from a bundle")
    view.add_argument("bundle", type=Path)
    view.add_argument("--section", choices=("summary", "targets", "packages", "integrations", "workflows", "tree"), default="targets")
    view.add_argument("--limit", type=int, default=DEFAULT_VIEW_LIMIT)
    view.add_argument("--format", choices=("markdown", "html"), default="markdown")
    view.add_argument("--output", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if getattr(args, "view_limit", 1) <= 0 or getattr(args, "limit", 1) <= 0:
        raise MapError("view limits must be positive")
    if args.command == "scan":
        manifest = build_bundle(args.repository, args.bundle, args.ref, args.exclude, args.view_limit)
        print(json.dumps({"created": True, "bundle": str(args.bundle.resolve()), "snapshotId": manifest["snapshotId"]}, ensure_ascii=False))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_bundle(args.bundle), ensure_ascii=False))
        return 0
    rendered = render_section(args.bundle.resolve(), read_json(args.bundle.resolve() / "manifest.json"), args.section, args.limit, args.format)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MapError, OSError, json.JSONDecodeError) as error:
        print(f"repository map: {error}", file=sys.stderr)
        raise SystemExit(1)

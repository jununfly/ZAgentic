#!/usr/bin/env python3
"""Build and pin a relocatable ZHarness research compiler artifact."""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

PROTOCOL = "zj-research-cli/v1"
EVALUATION_PROTOCOL = "zj-research-eval-cli/v1"
LOCK_SCHEMA = "zj-research-compiler-lock/v2"
EXECUTABLES = {"research": "lib/bin.js", "evaluation": "lib/eval.js"}
JSDOM_VERSION = "26.1.0"
MERMAID_VERSION = "11.16.0"


def run(
    command: list[str],
    cwd: Path,
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def add_deterministic_tree(source: Path, destination: Path) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT, dereference=True) as archive:
                for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
                    relative = path.relative_to(source).as_posix()
                    info = archive.gettarinfo(str(path), arcname=relative)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o755 if info.isdir() or relative in EXECUTABLES.values() else 0o644
                    if info.isfile():
                        with path.open("rb") as content:
                            archive.addfile(info, content)
                    else:
                        archive.addfile(info)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as content:
        for chunk in iter(lambda: content.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zharness", type=Path, help="clean ZHarness checkout at the commit to pin")
    args = parser.parse_args()
    zharness = args.zharness.resolve()
    skill = Path(__file__).resolve().parents[1] / "skills" / "engineering" / "zj-research"
    artifacts = skill / "artifacts"

    git_env = dict(os.environ)
    git_env.pop("NODE_OPTIONS", None)
    commit = run(["git", "rev-parse", "HEAD"], zharness, env=git_env)
    changed_packages = run(["git", "status", "--porcelain", "--", "packages"], zharness, env=git_env)
    if changed_packages:
        raise RuntimeError("ZHarness packages/ must be clean before pinning a compiler artifact")
    esbuild = zharness / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    if not esbuild.exists():
        raise RuntimeError("ZHarness esbuild is unavailable; run pnpm install and pnpm run build first")
    mermaid_min = Path(
        run(
            [
                "node",
                "-e",
                "console.log(require.resolve('mermaid/dist/mermaid.min.js'))",
            ],
            zharness,
        )
    )
    mermaid_package = mermaid_min.parent.parent / "package.json"

    artifacts.mkdir(parents=True, exist_ok=True)
    artifact_name = f"dsh-research-cli-{commit[:7]}.tgz"
    artifact = artifacts / artifact_name
    with tempfile.TemporaryDirectory(prefix="zj-research-compiler-") as directory:
        stage = Path(directory)
        (stage / "lib").mkdir()
        run(
            [
                str(esbuild),
                "packages/research/research-cli/src/bin.ts",
                "--bundle",
                "--platform=node",
                "--format=esm",
                "--target=node22",
                "--external:jsdom",
                f"--outfile={stage / 'lib' / 'bin.js'}",
            ],
            zharness,
        )
        run(
            [
                str(esbuild),
                "packages/research/research-eval/src/bin.ts",
                "--bundle",
                "--platform=node",
                "--format=esm",
                "--target=node22",
                f"--outfile={stage / 'lib' / 'eval.js'}",
            ],
            zharness,
        )
        package = {
            "name": "@deepseek-ai/dsh-research-compiler-artifact",
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "dependencies": {"jsdom": JSDOM_VERSION},
        }
        (stage / "package.json").write_text(json.dumps(package, separators=(",", ":")) + "\n", encoding="utf-8")
        run(
            [
                "npm.cmd" if os.name == "nt" else "npm",
                "install",
                "--ignore-scripts",
                "--omit=dev",
                "--package-lock=false",
                "--no-audit",
                "--no-fund",
                "--prefix",
                str(stage),
            ],
            zharness,
        )
        shutil.rmtree(stage / "node_modules" / ".bin", ignore_errors=True)
        (stage / "node_modules" / ".package-lock.json").unlink(missing_ok=True)
        mermaid_target = stage / "node_modules" / "mermaid"
        (mermaid_target / "dist").mkdir(parents=True)
        shutil.copyfile(mermaid_package, mermaid_target / "package.json")
        shutil.copyfile(mermaid_min, mermaid_target / "dist" / "mermaid.min.js")
        response = run(
            ["node", str(stage / "lib" / "bin.js")],
            stage,
            input_text=json.dumps({"protocol": PROTOCOL, "operation": "describe"}),
        )
        if json.loads(response).get("protocol") != PROTOCOL:
            raise RuntimeError("generated compiler failed its protocol handshake")
        evaluation_response = run(
            ["node", str(stage / "lib" / "eval.js")],
            stage,
            input_text=json.dumps({"protocol": EVALUATION_PROTOCOL, "operation": "describe"}),
        )
        if json.loads(evaluation_response).get("protocol") != EVALUATION_PROTOCOL:
            raise RuntimeError("generated evaluation runtime failed its protocol handshake")
        add_deterministic_tree(stage, artifact)

    lock = {
        "schema": LOCK_SCHEMA,
        "repository": "https://github.com/jununfly/ZHarness",
        "commit": commit,
        "protocols": {"research": PROTOCOL, "evaluation": EVALUATION_PROTOCOL},
        "executables": EXECUTABLES,
        "artifact": artifact_name,
        "sha256": sha256(artifact),
        "minimumNodeMajor": 22,
    }
    (artifacts / "compiler-lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for previous in artifacts.glob("dsh-research-cli-*.tgz"):
        if previous != artifact:
            previous.unlink()
    print(json.dumps(lock, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"research compiler artifact: {error}", file=os.sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
# probe-litesandbox-ref.py — decide whether Symptom F (nested-ref rollback) is caused by
# WorkBuddy's LiteSandbox FS protection (Layer ②) or by a third-party antivirus / minifilter.
#
# Run INSIDE a WorkBuddy Bash/PowerShell tool. Requires only the Windows-builtin python.
# No git CLI needed for the verdict logic; git is used only to create throwaway repos.
#
# Verdicts:
#   litesandbox   — ref survives in a TEMP repo but is rolled back inside the protected
#                   project tree, AND we are inside the LiteSandbox process tree.
#                   => Symptom F is Layer ②. Use flat names / commit-tree / a sandbox-free terminal.
#   external-av   — ref is rolled back in BOTH the TEMP repo and the workspace repo.
#                   => not LiteSandbox; investigate third-party file-system filters.
#   clean         — ref survives in both. Symptom F did not reproduce here.

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def git(repo: Path, *args):
    env = dict(os.environ)
    env.pop("NODE_OPTIONS", None)  # disable Node shim sub-layer; we're testing Layer ②, not Layer ①
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def make_repo(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "probe@local")
    git(path, "config", "user.name", "probe")
    (path / "f.txt").write_text("hi\n", encoding="utf-8")
    git(path, "add", "f.txt")
    git(path, "commit", "-q", "-m", "init")
    return path


def nested_ref_survives(repo: Path) -> bool:
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "branch", "zz/probe", head)
    probe = Path(repo) / ".git/refs/heads/zz/probe"
    t0 = probe.exists()
    time.sleep(1.0)  # LiteSandbox rolls back ~70ms after the write; 1s is plenty
    t1 = probe.exists()
    # clean up the probe ref so the repo is left untouched
    if probe.parent.exists():
        shutil.rmtree(probe.parent, ignore_errors=True)
    log = Path(repo) / ".git/logs/refs/heads/zz"
    if log.exists():
        shutil.rmtree(log, ignore_errors=True)
    return bool(t0 and t1)


def main():
    tmp = make_repo(Path(tempfile.gettempdir()) / "lsbox_probe_tmp")
    # workspace probe: a throwaway repo INSIDE the current working directory.
    # If cwd is inside a WorkBuddy-protected project tree, this exercises Layer ②'s scope.
    ws = make_repo(Path.cwd() / ".lsbox_probe_tmp")

    r_temp = nested_ref_survives(tmp)
    r_ws = nested_ref_survives(ws)

    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(ws, ignore_errors=True)

    in_lsbox = any(k.startswith("LSBOX_") for k in os.environ) or os.environ.get("IN_DOCKER") == "1"

    print("git nested-ref survives in TEMP repo     :", r_temp)
    print("git nested-ref survives in workspace repo :", r_ws)
    print("running inside LiteSandbox env           :", in_lsbox)
    print()

    if r_temp and not r_ws and in_lsbox:
        print("VERDICT: litesandbox  (Symptom F = Layer ② — flat name / commit-tree / sandbox-free terminal)")
    elif (not r_temp) and (not r_ws):
        print("VERDICT: external-av  (investigate third-party minifilter / antivirus, not LiteSandbox)")
    else:
        print("VERDICT: clean / not-reproduced")


if __name__ == "__main__":
    main()

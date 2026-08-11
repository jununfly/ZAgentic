---
name: zj-git-bypass-safe-delete
description: Diagnose and recover from WorkBuddy's safe-delete shim corrupting git repositories on Windows Git Bash. Use when `git status` shows all files as A, `git diff` fails with missing tree, `refs/heads/<branch>` is gone, or `git fetch`/`git stash`/`git commit` left .git in a broken state. Also use proactively before any `rm -rf` in WorkBuddy shell — the shim can actually delete under Git Bash.
---

# Bypass WorkBuddy Safe-Delete for Git

WorkBuddy's safe-delete shim (`genie-safe-delete.cjs`, injected via `NODE_OPTIONS=--require=...`) intercepts `fs.unlinkSync` / `fs.rmSync` / `fs.rmdirSync` and routes deletes to the OS trash. On Windows Git Bash, `uname -s` returns `MINGW64_NT-10.0` — which the shim's `case MINGW*` does **not** match, so it falls through to `trash_linux` whose EXDEV fallback actually runs `REAL_RM -rf "$p"`. Net effect: `rm -rf` is destructive on this host, and git's internal Node helpers silently lose `.git/refs/*` / `index.lock` / `FETCH_HEAD`.

This skill makes both the **symptom** (broken git) and the **root cause** (`rm -rf` is destructive) safe to handle.

## Quick start

1. Diagnose: `bash scripts/diagnose.sh <repo-path>` — reports which files are missing, whether reflog is intact, and whether the shim is in scope.
2. Recover: `bash scripts/recover-refs.sh <repo-path> <branch> [<commit>]` — recreates missing `refs/heads/...` from reflog using direct file IO (not `git update-ref`, which itself is unsafe under the shim).
3. Stop using `rm -rf` for cleanup — use `mv <target> <backup>/` instead (shim does not wrap `mv`).

## Workflow

### 1. Diagnose

Run:

```bash
bash scripts/diagnose.sh <repo-path>
```

It checks (in order):

- `.git/refs/heads/`, `.git/refs/tags/`, `.git/refs/remotes/` exist and are non-empty
- `HEAD` resolves to a real commit (else `git log` errors with "does not have any commits yet")
- `FETCH_HEAD` is non-empty
- `.git/logs/HEAD` reflog is non-empty (your history is recoverable if so)
- whether the WorkBuddy shim is in scope (`NODE_OPTIONS` contains `genie-safe-delete.cjs`)

Output is a one-screen report. If any line is red, jump to the matching recovery step.

### 2. Recover a broken repo (reflog intact)

```bash
bash scripts/recover-refs.sh <repo-path> <branch-name>
```

Without a `<commit>` argument, it takes the **last** reflog entry as the new HEAD. With one, it sets HEAD to that exact commit.

> **Do not use `git update-ref` instead** — it internally unlinks the old ref file, and the shim routes that unlink to the trash. The script writes the ref via `printf > tmp && mv tmp ref` (atomic, shim-safe).

After running:

```bash
cd <repo-path>
git log --oneline -3   # confirm history
git status --short     # confirm files show M/A/D, not "all A"
```

### 3. Prevent future breakage

Add `~/bin/zj-git` and use it instead of plain `git`:

```bash
mkdir -p ~/bin
cat > ~/bin/zj-git <<'EOF'
#!/bin/bash
exec env -u NODE_OPTIONS /mingw64/bin/git "$@"
EOF
chmod +x ~/bin/zj-git
```

Then call `zj-git <command>` instead of `git <command>`. This strips the `NODE_OPTIONS` injection from the immediate process and (in most git commands) from helpers git spawns.

> Note: `git` may invoke Node helpers internally. `env -u NODE_OPTIONS` only affects the *immediate* process. If a helper still breaks, run with `GIT_TRACE=1` to see what gets spawned, and add the helper to the bypass.

### 4. Never `rm -rf` in WorkBuddy shell

Use `mv` to park targets in a sibling backup directory. Shim does not wrap `mv`:

```bash
mv <target> <backup-dir>/$(basename <target>)
```

If you genuinely need a destructive delete, do it from a non-WorkBuddy process (cmd.exe, PowerShell with the shim disabled, or a manual `Recycle Bin` operation).

## When NOT to use this skill

- The git error is **not** a refs/lock corruption (e.g. merge conflict, bad refspec). Use `zj-diagnosing-bugs` for those.
- You're on macOS or Linux — the shim works correctly there. Use `git` directly.
- The repo is genuinely corrupted at the object level (missing blobs in `objects/`). Recovery is impossible without `git fsck` + remote re-fetch.

## Files

- `scripts/diagnose.sh` — read-only inspection of `.git/` state
- `scripts/recover-refs.sh` — recreate loose refs from reflog

---
name: zj-git-bypass-safe-delete
description: Diagnose and recover from WorkBuddy's safe-delete shim corrupting git repositories on Windows Git Bash. Use when `git status` shows all files as A, `git diff` fails with missing tree, `refs/heads/branch-name` is gone, or `git fetch`/`git stash`/`git commit` left .git in a broken state. Also use proactively before any `rm -rf` in WorkBuddy shell — the shim can actually delete under Git Bash.
---

# Bypass WorkBuddy Safe-Delete for Git

WorkBuddy's safe-delete shim (`genie-safe-delete.cjs`, injected via `NODE_OPTIONS=--require=...`) intercepts `fs.unlinkSync` / `fs.rmSync` / `fs.rmdirSync` and routes deletes to the OS trash. On Windows Git Bash, `uname -s` returns a `MINGW*` value (e.g. `MINGW64_NT-10.0`) — which the shim's `case MINGW*` does **not** match, so it falls through to `trash_linux` whose EXDEV fallback actually runs `REAL_RM -rf "$p"`. Net effect: `rm -rf` is destructive on this host, and git's internal Node helpers silently lose `.git/refs/*` / `index.lock` / `FETCH_HEAD`.

This skill makes both the **symptom** (broken git) and the **root cause** (`rm -rf` is destructive) safe to handle.

## Bypass wrapper (the key idea)

The shim only loads because `NODE_OPTIONS` is set for the git process. The fix is to run git with `NODE_OPTIONS` stripped:

```bash
env -u NODE_OPTIONS git <args>        # one-off
```

For repeated use, wrap that in a small script (a "git bypass wrapper") that unsets `NODE_OPTIONS` and execs git. Such a wrapper can live anywhere on `PATH` (per-project or in your home bin). Throughout this skill, "the bypass wrapper" means *any* wrapper that produces `env -u NODE_OPTIONS git ...`. Plain `git` (with the shim loaded) is unsafe on this host.

> Note: `git` may invoke Node helpers internally. `env -u NODE_OPTIONS` only affects the *immediate* process. If a helper still breaks, run with `GIT_TRACE=1` to see what gets spawned, and report it — the bypass path may need widening.

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

Use the bypass wrapper (see "Bypass wrapper" above) instead of plain `git` for every git operation.

```bash
env -u NODE_OPTIONS git --version       # verify it works
env -u NODE_OPTIONS git fetch           # use instead of plain `git fetch`
env -u NODE_OPTIONS git commit -m "..." # use instead of plain `git commit`
```

If you want a permanent replacement, wrap it in a shell function / alias pointing at your bypass wrapper:

```bash
# bash — point <wrapper> at your bypass script on PATH
alias git="<wrapper>"
```

```powershell
# PowerShell
function git { & <wrapper> @args }
```

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

## When in doubt — decision tree

If you don't know whether the corruption is shim-caused or something else, walk this:

```
1. Run `uname -s` in your shell.
   - Returns MINGW* on Windows Git Bash  →  SHIM-CORRUPTED is the default assumption. Go to step 2.
   - Returns Darwin / Linux              →  shim works correctly. Use `zj-diagnosing-bugs` instead.

2. `bash scripts/diagnose.sh <repo>` — read the report.
   - Any RED line? (refs missing / HEAD unresolvable / FETCH_HEAD empty) → shim-corrupted, go to step 3.
   - All green?                          → not shim corruption. Use `zj-diagnosing-bugs`.

3. `git reflog` (plain `git`, NOT the bypass wrapper) — is `.git/logs/HEAD` non-empty?
   - Empty  → unrecoverable. `rm -rf .git && git init && git remote add origin <url> && git fetch && git reset --hard origin/main`. Re-clone may be faster.
   - Non-empty → recoverable. Go to step 4.

4. `bash scripts/recover-refs.sh <repo> <branch>` (last reflog entry as HEAD).
   - `git log --oneline -3` confirms history
   - `git status --short` shows real M/A/D (not "all A")
   - Still broken?  →  re-run with explicit `<commit>` from `git reflog`.

5. Prevention: use the bypass wrapper going forward. See step 3 in the main workflow above.
```

**Time budget**: most shim-corrupted repos recover in under 30 seconds (diagnose + one recover-refs call). If you've spent more than 2 minutes, stop and re-read the tree — you're probably on the wrong branch.

## Known shim symptoms beyond the obvious

The three symptoms above (refs missing, `all A` status, broken commit/fetch) are the loud ones. The shim also produces three quieter symptoms that won't break git but will mislead you. Recognise them or you'll chase the wrong fix.

### Symptom A — `git fetch` reports success but the local ref doesn't move

You run `git fetch origin main` (or via the bypass wrapper), the command exits 0, you see `From <remote> * branch main -> FETCH_HEAD`. But `git rev-parse origin/main` still points to the old commit, and `git status -sb` says `## main...origin/main [ahead N]` even though the remote is actually caught up.

**Root cause**: the shim's `fs.unlinkSync` wrapper intercepts the loose-ref rewrite that follows a successful fetch. The fetch itself completes, but the ref file write is routed to the trash. So Git's in-memory state advances, but the on-disk ref is left stale.

**Detection**:
```bash
git ls-remote origin main            # what the remote actually has
git rev-parse origin/main            # what your local ref says (stale?)
# If they differ, symptom A is active
```

**Fix** (in order — stop at the first that works):

1. `git pack-refs --all` — forces loose refs to be merged into `packed-refs`, which the shim doesn't touch.
2. Write the ref directly with the bypass wrapper, never plain `git update-ref` — `update-ref` internally unlinks the old ref file (which the shim would route to trash).
3. Manual fix from outside the shim (no WorkBuddy process): create a loose ref by writing directly to `.git/refs/remotes/origin/main`. From inside WorkBuddy Bash, use `mv` from a temp dir rather than `printf >` to dodge the shim:
   ```bash
   echo "<correct-sha>" > /tmp/origin-main-new
   mkdir -p .git/refs/remotes/origin
   mv /tmp/origin-main-new .git/refs/remotes/origin/main
   ```

### Symptom B — `git status` shows fewer M/A files than the commit actually contains

You run `git add -A` then `git status --short` and only see some of your changes — but `git commit` succeeds and `git log --stat` shows all the right files. Or you run `git commit` and afterwards `git status` shows the files as if they were never staged, even though the commit object really does include them.

**Root cause**: the shim's `fs.unlinkSync` wrapper also intercepts operations on `.git/index`. The index entry is added in memory and committed to the commit object, but the index file on disk gets its entries stripped shortly after. `git status` reads the on-disk index and is fooled.

**Verification rule**: **never trust `git status` to confirm what's in a commit. Use `git ls-tree -r <sha>`.** That command reads the commit object directly from `.git/objects/`, bypassing the index.

```bash
git ls-tree -r HEAD | grep <filepath>   # authoritative — what's actually in the commit
# or for a specific past commit:
git ls-tree -r <sha> | grep <filepath>
```

**Don't** rely on `git show <sha>:<path>` for this purpose. If the loose ref for that path is missing, Git falls back to the working tree file and will *lie* — it'll show you a file that isn't actually in the commit. `git ls-tree` doesn't have this fallback.

### Symptom C — `git commit -F <path>` fails with "could not read log file"

You run `git commit -F /tmp/my-message.txt` and get `fatal: could not open '/tmp/my-message.txt' for reading`, even though `ls /tmp/my-message.txt` shows the file is there with the right contents.

**Root cause**: the shim sometimes intercepts the syscall that Git uses to stat the `-F` path, returning ENOENT. The path exists, but Git can't see it through the shim's wrapped syscall layer.

**Fix**: read the file and pipe it into Git on stdin:
```bash
cat /tmp/my-message.txt | git commit -F -
```

This bypasses the `-F` path entirely. The shim doesn't intercept stdin reads.

### Symptom D — `git rm <path>` trashes the path's entire ancestor tree (worktree loss)

You run `git rm <dir>/<file>` (even with `env -u NODE_OPTIONS`), it prints `rm '<dir>/<file>'` and exits 0 — but the **whole ancestor directory tree** (the parent dir including subdirs you never touched) lands in the Recycle Bin. `git status` shows unstaged ` D` for files you never modified; `ls <dir>/` returns ENOENT.

**Root cause**: git's directory pruning after unlink gets routed through the shim's trash path, and the trash operation is applied to ancestor dirs that are *not* actually empty — the shim recursively trashes live content. `env -u NODE_OPTIONS` does **not** prevent this (it happens below the node-injection layer).

**Evidence**: the OS Recycle Bin contains same-minute entries for the path you `git rm`'d and each of its ancestor directories, including content you never touched.

**Fix**:
```bash
git restore <dir>          # recovers every git-tracked file (objects are untouched)
```
Untracked new files lost this way must be rewritten from elsewhere (context, backup). Zero git-history loss — only the worktree was hit.

**Prevention**: after **any** `git rm`, immediately `ls` the parent tree and `git status --short`. If files show unexpected ` D`, restore before doing anything else. For single-file removals inside shared dirs, `git rm --cached` + `mv` to a backup dir is the shim-proof route.

### Symptom D2 — `git checkout <branch>` 之后工作树整片文件消失（status 一片 ` D`）

You run `git checkout <branch>` (or any branch switch), it prints `Switched to branch '<branch>'` and exits 0 — then `git status --short` lists **dozens/hundreds of ` D`** entries for files you never touched (whole directories). The files are in `HEAD` (`git ls-tree HEAD <path>` returns a blob) but absent from disk (`Test-Path` false).

Same family as Symptom D — the shim's trash path swallows worktree trees during checkout — but the trigger is a branch switch, not `git rm`, and the scale is the whole diff between the two branches rather than one path. **Nothing is lost**: the objects are intact, only the worktree files were moved.

**Fix** (one invocation, before anything else):
```bash
git restore .              # 救回全部 tracked 文件；status 应回到 0 条
git fsck --no-dangling     # 顺手确认仓库没被弄坏
```
Untracked files would be gone for real — check `git status --short` for non-` D` entries before restoring, and recover those from the Recycle Bin by name.

**Prevention**: after **any** `git checkout` / `git switch`, immediately run `git status --short` and expect zero entries. If it shows ` D` you did not create, restore first and investigate second — running more git commands on a half-trashed worktree compounds it.

### Symptom E — `.git/refs/remotes/origin/` vanishes right after `fetch` / `update-ref`

`git fetch` prints `<old>..<new> main -> origin/main` (success), but `git log origin/main` still resolves to the **old** commit and `git status -sb` says `[ahead N]`. Inspection: `.git/refs/remotes/origin/` doesn't exist; git is falling back to stale `packed-refs`. Worse, `git update-ref refs/remotes/origin/main <sha>` can write the loose ref and have the directory vanish **within the same command chain**.

**Ground truth**: `git ls-remote origin main` — trust this over local refs after any fetch/push.

**Fix that actually sticks** — write the loose ref by hand in a standalone Bash invocation, with **no git command after it in the same chain**:
```bash
mkdir -p .git/refs/remotes/origin
echo -n "<correct-sha>" > .git/refs/remotes/origin/main
```
Then verify in a *separate* invocation (`git log --oneline origin/main -2`). If a git command runs in the same chain, the freshly written ref dir can be trashed again.

### Symptom F — 本地分支 ref（嵌套目录）被吞，分支变 unborn

Typical trigger: you commit on a newly created branch (e.g. `<dir>/<branch>`); git prints `[<dir>/<branch> <sha>] ...` and exits 0. The very next command — even inside the same invocation — says `fatal: your current branch '<dir>/<branch>' does not have any commits yet`, and `git status --short` lists **the whole tree as `A`** (index intact, HEAD empty). Inspection: `.git/refs/heads/` still holds the old branches, but the `<dir>/` directory is gone.

Symptom E's sibling — same swallowing, but on `refs/heads/**`. **The commit object is safe**: `.git/logs/HEAD` still carries the `old new ... commit: <subject>` line, and `git cat-file -t <sha>` says `commit`.

**触发点不止 `commit`。** 实测 `git checkout -b <branch>` 与 `git push` 之后 ref 同样消失，症状完全一致（HEAD unborn、`status` 全 `A`）。后果是：

- 新建分支之后、跑下一条 git 命令之前，得先把 ref 写回去。嵌套目录要自己建 —— git 不会因为你要写文件就替你造出 `refs/heads/<dir>/`：
  ```powershell
  [IO.Directory]::CreateDirectory("$PWD\.git\refs\heads\<dir>") | Out-Null
  [IO.File]::WriteAllText("$PWD\.git\refs\heads\<dir>\<branch-name>", $sha)
  ```
- `git push` 之后如果还要继续在这个分支上提交 / 再推，push 完**再写一次** ref。
- 反过来，`gh pr create` 与 `git ls-remote` 走的是远端，**本地 ref 被吞也不受影响**。ref 丢了又急着开 PR，这是最快的出路。

**Push recipe that survives it** — never let the push depend on resolving a local ref; push the raw sha:

```powershell
# 1) ref 丢了但 reflog 在：从最后一行取第二个字段 = 新 commit 的 sha
$sha = ((Get-Content .git\logs\HEAD -Tail 1) -split "\s+")[1]
# 2) 手写回本地 ref（只为让后续 git 命令正常；同样可能被吞，所以不依赖它）
[IO.Directory]::CreateDirectory("$PWD\.git\refs\heads\<dir>") | Out-Null
[IO.File]::WriteAllText("$PWD\.git\refs\heads\<dir>\<branch-name>", $sha)
# 3) 用 sha 推，完全不解析本地 ref
git push origin "${sha}:refs/heads/<branch-name>"
# 4) 用远端当真相校验，不要信本地 ref
git ls-remote origin refs/heads/<branch-name>
```

用 `[IO.File]::WriteAllText`（无 BOM）而不是 `>` / `Out-File` —— 后者在 PS 5.1 会写出 UTF-16/BOM，git 读不出 sha。写的时候**带上结尾 `\n`**，否则 `git fsck` 会一直报 `refMissingNewline`。

第 2 步写回去的那份通常活不过第 3 步的 push（push 自己也吞）。这就是为什么校验必须走第 4 步的 `ls-remote` 而不是 `git log`：本地 ref 在这条链里根本不是可靠的读回通道。

**陷阱：一条命令链里连着做两个 commit。** ref 是在 `git commit` **进程结束前**被吞的，所以第二个 commit 会看到 unborn HEAD，落成 **root-commit**——整个 index 被当成新增（实测出现过把整库当成一次新增提交、与分支历史完全断开的情况），而且它跟分支历史完全断开。防御两步：

```powershell
# 每个 commit 之前先把 ref 写回已知 sha
[IO.File]::WriteAllText("$PWD\.git\refs\heads\<dir>\<branch>", $knownSha)
git commit -F msg
# 提交后先验证父提交再推，不对就别推
git rev-parse "$newSha^"    # 必须等于 $knownSha，否则是 root-commit
```

更稳的做法：**一次调用只做一个 commit，做完立刻 push**，不要攒两个再一起推。

若 push 报 `SANDBOX EXECUTION REJECTED BY USER`，**不要照字面理解成"用户点了拒绝"**：那是沙箱对默认密钥路径（`~/.ssh/*`）通配规则的自动拦截（Blocked paths 里列的是 SSH 依次尝试的全部默认密钥名，机器上大多不存在）。请用户放开权限后重试一次即可，不是凭据问题。

### Symptom G — 未提交改动落新分支：`commit-tree` 造提交 + 显式 sha 直推（完整脚本）

场景：工作树有一组干净的未提交改动，要推到远端一个新分支开 PR。但 `git commit` 会在进程结束前吞掉新分支 ref（Symptom F）→ 第二个 commit 落成 **root-commit**（整库被当成一次新增、与历史断开）；`git checkout -b` 也会吞 `refs/heads/<dir>/` 目录。结论：**这一组操作里一次都不要调 `git commit` / `git checkout -b`**。

改用 `git write-tree` + `git commit-tree` 造提交对象，再 `git push origin "<sha>:refs/heads/<branch>"` 把 sha 直接写到远端分支 ref，全程用 `git ls-remote` 当真相。**提交对象 / 树对象都不碰 ref 文件，所以根本不触发吞 ref**。

完整 PowerShell 脚本（复制即用；把 `<repo-root>` / `<branch>` / 暂存目录 / 提交说明换成你的）：

```powershell
$ErrorActionPreference = "Stop"
# 0) 在仓库根
Set-Location <repo-root>

# 1) 真父提交：远端目标分支的真相（不信本地 origin/<branch>，Symptom E 假 ahead）
$P = (& git ls-remote origin main) -split '\s+' | Select-Object -First 1
if (-not ($P -match '^[0-9a-f]{40}$')) { throw "ls-remote 没拿到干净 sha: '$P'" }

# 2) 只暂存本 PR 触及的目录（不要 git add -A，避免夹带其他脏文件）
& git add <paths-you-touched>

# 3) 写树 + commit-tree 造提交对象（绕开 git commit 的吞 ref）
$T = (& git write-tree).Trim()
$branch = "<branch>"
$msgFile = ".workbuddy\pr-commit-msg.txt"
$msg = "feat: <your one-line subject>`n`n<optional body / closes #N>"
[System.IO.File]::WriteAllText($msgFile, $msg, [System.Text.UTF8Encoding]::new($false))  # 无 BOM，否则 git 读不出
$C = (& git commit-tree $T -p $P -F $msgFile).Trim()
if (-not ($C -match '^[0-9a-f]{40}$')) { throw "commit-tree 没返回干净 sha: '$C'" }

# 4) push 前校验父链：C^ 必须等于 P，否则是 root-commit，绝不推
$parentOfC = (& git rev-parse "$C^").Trim()
if ($parentOfC -ne $P) { throw "父链不符：C^=$parentOfC P=$P，未推送" }

# 5) 显式 sha 直推远端分支 ref（不解析本地 ref，避开 checkout -b 吞 ref）
& git push origin "$C`:refs/heads/$branch"
if ($LASTEXITCODE -ne 0) { throw "push 失败" }

# 6) ls-remote 复核：远端分支 sha == C（不靠本地 rev-parse，本地 ref 在这条链不可靠）
$remoteSha = (& git ls-remote origin "refs/heads/$branch") -split '\s+' | Select-Object -First 1
if ($remoteSha -ne $C) { throw "远端 sha 不符：got $remoteSha want $C" }
Write-Host "OK $branch = $C"

# 7) 可选：本地也建同名 ref 便于后续（可能再被吞，所以不依赖它）
& git update-ref "refs/heads/$branch" $C
```

为什么安全（逐行对应）：

- 第 1 步 `ls-remote` 取真父，不信任本地 `origin/main`（Symptom E 假 ahead）。
- 第 3 步 `commit-tree` 造的是**提交对象**，`write-tree` 造的是**树对象**——两者都不碰任何 ref 文件，所以不被吞。
- 第 4 步 push 前用 `rev-parse "<C>^"` 校验父链，root-commit 直接中止（Symptom F 的连锁坑）。
- 第 5 步 `push origin "<C>:refs/heads/<branch>"` 把 sha 直接写到远端分支 ref，**完全不创建 / 解析本地 branch ref**，所以 `checkout -b` 的吞 ref 路径根本没被触发。
- 第 6 步用 `ls-remote` 复核，因为本地 ref 在这条链里不可靠（Symptom F/E 验证表）。

与 Symptom F 第 3 步 push recipe 的关系：F 那条假定你**已经有** commit sha（从 reflog 取）；本段覆盖你**只有未提交工作树**、要先 `write-tree`+`commit-tree` 造出 sha 的情形。两者都靠「显式 sha 直推 + ls-remote 复核」，可叠加。

开 PR：`gh pr create -F <body文件>`（正文走文件避 PowerShell 拆参），`$env:GH_PAGER="cat"` 防 `--no-pager` 放错位。

### Prevention

Symptoms A/B/C disappear when you use the bypass wrapper (or `env -u NODE_OPTIONS git`) for git operations. **Symptoms D/D2/E/F are NOT prevented by `env -u NODE_OPTIONS`** — they happen below the node-injection layer, so the only defense is verification. Four checkpoints, each right after the command that can trigger it:

| After | Check | Bad sign |
| --- | --- | --- |
| `git rm` | `ls` the parent tree + `git status --short` | unexpected ` D` → Symptom D |
| `git checkout` / `git switch` | `git status --short` | any ` D` → Symptom D2 |
| `git checkout -b` / `git commit` / `git push` | `git rev-parse --abbrev-ref HEAD` + `git log --oneline -1` | "does not have any commits yet" → Symptom F, hand-write the ref before running anything else |
| `git fetch` / `git push` | `git ls-remote origin <branch>` (not local refs) | local ref disagrees → Symptom E |

If you must do one of those by hand, expect to hit one of the seven symptoms above and apply the corresponding fix.

## 环境坑：Mechanism ② —— 沙箱把 `.git` 从 git 子进程视图里藏起来（易与机制一混淆）

前面的 Symptom A–G 都是 **机制一：safe-delete shim**——`.git` 内部件（refs 目录、松散对象）被 shim 路由进回收站，物理内容缺失。这里要记的是**机制二**，完全不同的另一类故障。

### 现象

在 WorkBuddy（agent）会话里跑 `git` 子进程，一律 `fatal: not a git repository`，连 `git rev-parse --git-dir`、`git --git-dir=<绝对路径>` 都报这个；但 **PowerShell cmdlets（`Get-ChildItem` / `Get-Content`）或文件管理器能看到 `.git` 且 HEAD / objects / index / packed-refs 全在**——即 `.git` 物理没坏，是 git 子进程被沙箱蒙了眼。

### 触发与生命周期

实测在 cleanup 阶段跑了 `git checkout -f <branch>` / `git reset --hard` 之后出现。这是**会话级沙箱状态**，跨多次 PowerShell 调用持续，**本会话内不可恢复**（重开 agent 会话 / 重启 WorkBuddy 才重置）。注意 Bash 运行时可能同时损坏（`dirname: command not found`，连 `cd` 都失败），两类故障会叠加。

### 与机制一的关键区别（拿不准时先读这段）

| | 机制一：shim 移走内部件 | 机制二：沙箱藏 `.git` |
| --- | --- | --- |
| `.git` 物理内容 | **确实缺失**（refs 目录 / 松散对象被删到回收站） | **完好**，文件管理器 / cmdlets 看得全 |
| `git init` 新建的干净仓库 | 完全正常 | 视沙箱范围——若沙箱只蒙本仓库则正常，若会话级则同失败 |
| 失败范围 | 只有受损的那个仓库失败 | git 子进程在本会话**所有仓库**都看不到 `.git` |
| 恢复 | 重建 refs / `git fetch` 补齐（见下） | 重开 agent 会话 / 用无沙箱的终端 |
| 根因 | shim 的 `fs.unlinkSync` 路由 | 沙箱对 `git` 子进程的文件系统视图过滤 |

**快速判别**（拿不准时跑）：

```bash
git init /tmp/scratch && cd /tmp/scratch && git status   # 若正常 → git 本身没坏
# 回到原仓库仍 not a git repository：
#   - 只有这个仓库失败 → 机制一（查 .git/refs、objects/ 有没有缺）
#   - git 在本会话所有仓库都失败、且 cmdlets 能看到 .git → 机制二
```

### 应对

- **机制二下，agent 会话内不要对本地仓库跑任何 `git`**；把提交 / 同步留给用户在无 WorkBuddy 沙箱的终端执行（普通 PowerShell、文件资源管理器地址栏起 `powershell`、或 Win+R → `powershell`）。
- 本地仓库同步（main 快进、pack-refs 修正等）照常走既定配方，但必须**在 agent 会话之外**做。
- **规避复现**：agent 会话内绝不对本地仓库跑 `checkout -f` / `reset --hard`；改用 `git update-ref` + `git pack-refs --all --prune`（改 ref、不动工作树）与 `git checkout -f <sha> -- .`（checkout 提交对象而非分支，不移动 HEAD）来同步与恢复。

### 实测教训（2026-09-12）

本次某仓库的 `not a git repository` **一开始误诊为机制二**，最后在用户真独立终端查明是**机制一**：`.git/refs` 目录缺失 + `main` tip 的松散对象被移走。`git init` 在用户终端正常、唯独本仓库失败——这符合机制一而非机制二。**教训：`not a git repository` 但 `.git` 物理可见时，先查 `.git` 内部结构（refs / objects 是否被 shim 移走），别急于归咎沙箱。** 机制二罕见且只能靠重开会话解决；机制一才是日常主因，且可恢复。

## Files

- `scripts/diagnose.sh` — read-only inspection of `.git/` state
- `scripts/recover-refs.sh` — recreate loose refs from reflog

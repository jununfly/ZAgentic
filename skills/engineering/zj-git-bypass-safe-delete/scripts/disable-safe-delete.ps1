# disable-safe-delete.ps1
# Permanent fix for WorkBuddy's safe-delete shim corrupting git (and breaking the
# Bash tool) on Windows. Neutralizes the 3-layer move-to-Recycle-Bin interception so
# Windows behaves like macOS (native delete). Re-run this after every WorkBuddy update.
#
# This script ships inside the zj-git-bypass-safe-delete skill. It is intentionally
# Windows + WorkBuddy only (see the guard below); on macOS/Linux the shim defaults to
# off, so there is nothing to patch and the script exits cleanly.
#
# What it patches (all under the WorkBuddy install shim dir, resolved from the
# environment so the script is portable across machines):
#   1. node-language-shim.cjs        -> safeDeleteEnabled = false  (Node layer)
#   2. sitecustomize.py             -> _SAFE_DELETE_ENABLED = False (Python layer)
#   3. safe-bin/safe-delete-bash-env.sh -> `if false` (bash rm/unlink/rmdir rewrite)
#   4. shell-runtime-bash-env.sh    -> fix broken BASH_SOURCE resolution (kills the
#                                     "dirname: command not found" error in the Bash tool)
#
# Trade-off: WorkBuddy's "delete protection" (files go to Recycle Bin instead of
# being really deleted) is disabled. For a developer that is acceptable.

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Environment gate: Windows + WorkBuddy only
# ---------------------------------------------------------------------------
if ($env:OS -notmatch 'Windows') {
    Write-Output "SKIP: not Windows (`$env:OS = '$($env:OS)'). This fix is for WorkBuddy on Windows only."
    exit 0
}

# Resolve the WorkBuddy install root. Honour an explicit override, then probe the
# standard per-user and machine-wide install locations.
$candidates = @()
if ($env:WORKBUDDY_HOME) { $candidates += $env:WORKBUDDY_HOME }
$candidates += "$env:LOCALAPPDATA\Programs\WorkBuddy"
$candidates += "$env:ProgramFiles\WorkBuddy"

$wbRoot = $null
foreach ($c in $candidates) {
    if ($c -and (Test-Path (Join-Path $c 'resources\app.asar.unpacked\cli\vendor\shim'))) {
        $wbRoot = $c
        break
    }
}

if (-not $wbRoot) {
    Write-Output "SKIP: WorkBuddy install not found in any of:"
    $candidates | Where-Object { $_ } | ForEach-Object { Write-Output "  - $_" }
    Write-Output "Set `$env:WORKBUDDY_HOME to your install root if it lives elsewhere."
    exit 0
}

Write-Output "WorkBuddy install: $wbRoot"
$shimDir = Join-Path $wbRoot 'resources\app.asar.unpacked\cli\vendor\shim'
$backupDir = Join-Path $shimDir 'disabled-backup'
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

function Patch-File {
    param(
        [string]$RelPath,
        [string]$OldText,
        [string]$NewText
    )
    $full = Join-Path $shimDir $RelPath
    if (-not (Test-Path $full)) {
        Write-Output "SKIP (missing): $RelPath"
        return
    }
    $content = [System.IO.File]::ReadAllText($full)
    if ($content.Contains($OldText)) {
        $bak = Join-Path $backupDir (([System.IO.Path]::GetFileName($full)) + ".bak")
        if (-not (Test-Path $bak)) { [System.IO.File]::Copy($full, $bak) }
        $new = $content.Replace($OldText, $NewText)
        [System.IO.File]::WriteAllText($full, $new)
        Write-Output "PATCHED: $RelPath"
    } else {
        Write-Output "NO-CHANGE (already patched or text drifted): $RelPath"
    }
}

# 1. Node layer
Patch-File "node-language-shim.cjs" `
  "const safeDeleteEnabled = process.env.CODEBUDDY_SAFE_DELETE_ENABLED !== '0';" `
  "const safeDeleteEnabled = false; /* PATCHED: safe-delete disabled (Windows == Mac) by disable-safe-delete.ps1 */"

# 2. Python layer
Patch-File "sitecustomize.py" `
  '_SAFE_DELETE_ENABLED = os.environ.get("CODEBUDDY_SAFE_DELETE_ENABLED") != "0"' `
  '_SAFE_DELETE_ENABLED = False  # PATCHED: safe-delete disabled by disable-safe-delete.ps1'

# 3. Bash layer (rm/unlink/rmdir rewrite)
Patch-File "safe-bin/safe-delete-bash-env.sh" `
  'if [ -n "${CODEBUDDY_SAFE_DELETE_BIN_DIR:-}" ]; then' `
  'if false; then  # PATCHED: safe-delete disabled by disable-safe-delete.ps1'

# 4. Fix broken BASH_SOURCE resolution in the bash runtime bootstrap
#    Use pure parameter expansion (no `dirname`, which is missing from PATH in
#    WorkBuddy's non-interactive bash) so the "dirname: command not found" error
#    in the Bash tool disappears.
Patch-File "shell-runtime-bash-env.sh" `
  '__codebuddy_shell_runtime_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' `
  '__codebuddy_shell_runtime_dir="${BASH_SOURCE[0]:-$0}"; __codebuddy_shell_runtime_dir="${__codebuddy_shell_runtime_dir%/*}"; __codebuddy_shell_runtime_dir="$(cd "$__codebuddy_shell_runtime_dir" 2>/dev/null && pwd)"'

# -------- Verification --------
Write-Output ""
Write-Output "=== Verification ==="

# Deterministic source check: every patched file must contain its patched marker.
$checks = @(
    @{File="node-language-shim.cjs"; Marker="const safeDeleteEnabled = false;"},
    @{File="sitecustomize.py"; Marker="_SAFE_DELETE_ENABLED = False"},
    @{File="safe-bin/safe-delete-bash-env.sh"; Marker="if false; then  # PATCHED"},
    @{File="shell-runtime-bash-env.sh"; Marker="%/*"}
)
$allOk = $true
foreach ($c in $checks) {
    $p = Join-Path $shimDir $c.File
    if (Test-Path $p) {
        $txt = [System.IO.File]::ReadAllText($p)
        if ($txt.Contains($c.Marker)) { Write-Output "OK   $($c.File) contains patched marker" }
        else { Write-Output "FAIL $($c.File) missing patched marker"; $allOk = $false }
    } else { Write-Output "SKIP (missing) $($c.File)"; $allOk = $false }
}

# Best-effort runtime check (needs node on PATH).
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$nodeExe = if ($nodeCmd) { $nodeCmd.Source } else { $null }
if ($nodeExe) {
    $shimPath = Join-Path $shimDir "node-language-shim.cjs"
    $env:CODEBUDDY_SESSION_ID = "verify"
    $env:NODE_OPTIONS = "--require $shimPath"
    try {
        $res = & $nodeExe -e "const fs=require('fs'); const s=fs.unlinkSync.toString(); console.log((s.includes('safeDelete')||s.includes('_try_trash')||s.includes('genie')) ? 'WRAPPED(STILL-HOOKED)' : 'NATIVE(unhooked-OK)')" 2>&1
        Write-Output "Node fs.unlinkSync : $res"
    } finally {
        Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
        Remove-Item Env:CODEBUDDY_SESSION_ID -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "Node runtime check skipped (node not on PATH)."
}

Write-Output ""
if ($allOk) {
    Write-Output "Done. Safe-delete shim disabled. Originals backed up under: $backupDir"
} else {
    Write-Output "WARN: some patches did not apply. Review output above."
    exit 1
}

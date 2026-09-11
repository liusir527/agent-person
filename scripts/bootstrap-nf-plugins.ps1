# scripts/bootstrap-nf-plugins.ps1
#
# Purpose: First-time setup / reset script for DSH web profile. Compiles the
# three TypeScript packages under packages/* to lib/ and links all six NF
# packages into the DSH web profile as Loader entries (bundles).
#
# When to run:
#   - First clone of this workspace (lib/ + node_modules/ do not exist yet)
#   - After moving to a new machine
#   - After DSH web profile is reset (rm -rf ~/.dsh/profiles/web, or after
#     `dsh plugin remove` of any @nsfocus/* dep)
#
# When NOT to run (daily development, no re-run needed):
#   - Editing packages/*/src/*.ts           -> cd packages/<p> && pnpm exec tsc
#   - Editing packages/*/client.js          -> browser refresh / restart dsh web
#   - Editing packages/*/cordis.patch.yml   -> restart dsh web
#   - Editing packages/*/package.json       -> restart dsh web
#   - Editing Python sources               -> none (script installs deps, not code)
#
# Python side (idempotent):
#   This script also resolves a Python interpreter (DSH_PYTHON / pin file /
#   well-known path / PATH) and pip-installs pyyaml + paramiko + requests for
#   .dsh/skills/* scripts. It writes a stub mcp_memory.py to
#   %USERPROFILE%/.dsh-memory/scripts/ when the real one is missing, and
#   injects the mcp-memory patch into ~/.dsh/profiles/web/cordis.patch.yml.
#   Force-install optional deps (evengsdk) with BOOTSTRAP_OPTIONAL_PYDEPS=1.
#
# Usage (from repo root):
#   pwsh -File scripts/bootstrap-nf-plugins.ps1
#   powershell -File scripts/bootstrap-nf-plugins.ps1     # also works on PS 5.1
#
# Optional env vars:
#   FORCE_REBUILD=1    force rebuild of TS packages even if lib/ exists
#   FORCE_RELINK=1     force re-link of all 7 NF packages to web profile
#
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# --- 0. Anchor workspace root (no machine-specific absolute paths) -------
$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) {
  throw "Not inside a git repository. Run this from the repo root."
}
Set-Location $repoRoot
Write-Host "[bootstrap] workspace = $repoRoot"

# --- 0a. First-run safety net: seed dirs.json so nf-hooks stops blocking ----
# Only on the very first bootstrap does this matter. Once the user restarts
# dsh web, the new dirs.json loads and the workspace toolchain stops blocking
# C:\Users\<user>\.dsh{,-memory}. Re-running is a no-op.
$dirsJson = Join-Path $repoRoot '.dsh/rules/dirs.json'
$dshHome     = Join-Path $env:USERPROFILE '.dsh'
$memoryHome  = Join-Path $env:USERPROFILE '.dsh-memory'

if (Test-Path $dirsJson) {
  Write-Host "[bootstrap] .dsh/rules/dirs.json exists, skip (delete to re-seed)"
} else {
  Write-Host "[bootstrap] seeding .dsh/rules/dirs.json (machine-specific)"
  $dshHomeEsc = $dshHome -replace '\\', '\\'
  $memoryHomeEsc = $memoryHome -replace '\\', '\\'
  $template = @"
{
  "mode": "restricted",
  "dirs": [
    {
      "path": "$dshHomeEsc",
      "reason": "DSH home; bootstrap writes here (web profile, plugin reconciliation).",
      "addedBy": "scripts/bootstrap-nf-plugins.ps1"
    },
    {
      "path": "$memoryHomeEsc",
      "reason": "Memory root; bootstrap installs scripts/mcp_memory.py here.",
      "addedBy": "scripts/bootstrap-nf-plugins.ps1"
    }
  ]
}
"@
  $rulesDir = Split-Path $dirsJson
  New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
  # Use BOM-less UTF-8 so the JSON parses cleanly.
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($dirsJson, $template, $utf8NoBom)
  Write-Host "  NOTE: restart 'dsh web' once so nf-hooks loads the new dirs.json."
}

# --- 0b. Activate pre-commit knowledge gate hooks (idempotent) ------------
# 蜂巢大脑去毒门禁：提交知识时自动跑 link_check，FAIL 拦截提交。
# 主仓 + submodule 各配 core.hooksPath 指向仓库内 hooks/ 目录（可 git 管理）。
Write-Host ""
Write-Host "[hooks] pre-commit knowledge gate:"
if (Test-Path (Join-Path $repoRoot 'hooks/pre-commit')) {
  & git config core.hooksPath hooks
  Write-Host "  * main repo: core.hooksPath -> hooks"
} else {
  Write-Host "  * main repo hooks/pre-commit missing, skip"
}
$memSub = Join-Path $repoRoot '.dsh-memory'
if ((Test-Path (Join-Path $memSub 'hooks/pre-commit')) -and (Test-Path (Join-Path $memSub '.git'))) {
  Push-Location $memSub
  try {
    & git config core.hooksPath hooks
    Write-Host "  * submodule (.dsh-memory): core.hooksPath -> hooks"
  } finally {
    Pop-Location
  }
} else {
  Write-Host "  * submodule hooks/pre-commit or .git missing, skip (clone --recursive 后再跑本脚本)"
}

# --- 1. Verify required tools -------------------------------------------
function Test-Cmd {
  param($Name, $Hint)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command '$Name': $Hint"
  }
}
Test-Cmd pnpm "install pnpm (npm i -g pnpm)"
Test-Cmd dsh  "install DSH (npm i -g @deepseek-ai/dsh)"
Test-Cmd git  "install git"

$nodeVer = (& node -v).TrimStart('v').Split('.')[0]
if ([int]$nodeVer -lt 22) {
  throw "Node $(& node -v) too old; need >= 22.19"
}

# --- 2. Define the 7 NF packages (single source of truth) --------------
$tsPackages   = @('nf-hooks', 'nf-gdb-guard', 'nf-system-prompt', 'nf-env-watcher')
$allPackages  = @('nf-brand', 'nf-bug-progress', 'nf-terminal-monitor') + $tsPackages

foreach ($p in $allPackages) {
  if (-not (Test-Path "packages/$p/package.json")) {
    throw "Missing packages/$p/package.json; package list out of sync with directory layout."
  }
}

# --- 3. Compile TS packages (idempotent) -------------------------------
foreach ($p in $tsPackages) {
  $libIndex = "packages/$p/lib/index.js"
  $shouldBuild = ($env:FORCE_REBUILD -eq '1') -or (-not (Test-Path $libIndex))

  if (-not $shouldBuild) {
    Write-Host "[build] $p - lib/ exists, skip (set FORCE_REBUILD=1 to rebuild)"
    continue
  }

  Write-Host "[build] $p - compiling TS -> lib/"
  Push-Location "packages/$p"
  try {
    if (-not (Test-Path node_modules)) {
      Write-Host "  * pnpm install (first run / node_modules missing)"
      & pnpm install --silent
      if ($LASTEXITCODE -ne 0) { throw "pnpm install failed in packages/$p" }
    }
    & pnpm exec tsc -p tsconfig.json
    if ($LASTEXITCODE -ne 0) { throw "tsc failed in packages/$p (exit=$LASTEXITCODE)" }
    if (-not (Test-Path lib/index.js)) {
      throw "post-build: packages/$p/lib/index.js missing; check tsconfig and source"
    }
  } finally {
    Pop-Location
  }
}

# --- 4. Link 7 NF packages to DSH web profile (idempotent) --------------
$profileDir = Join-Path $env:USERPROFILE '.dsh\profiles\web'
$profileManifest = Join-Path $profileDir 'package.json'
if (-not (Test-Path $profileManifest)) {
  throw "Missing $profileManifest. Run 'dsh web' once first to initialize the profile."
}
$manifest = Get-Content $profileManifest -Raw -Encoding UTF8 | ConvertFrom-Json
$declared = @{}
if ($manifest.dependencies) {
  foreach ($prop in $manifest.dependencies.PSObject.Properties) { $declared[$prop.Name] = $prop.Value }
}

foreach ($p in $allPackages) {
  $pkgJson = Get-Content "packages/$p/package.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $pkgName = $pkgJson.name
  $spec = "link:$repoRoot/packages/$p"

  $alreadyLinked = $declared.ContainsKey($pkgName) -and ($declared[$pkgName] -like 'link:*')
  if ($alreadyLinked -and $env:FORCE_RELINK -ne '1') {
    Write-Host "[link] $p - already declared ($($declared[$pkgName])), skip"
    continue
  }

  Write-Host "[link] $p -> $spec"
  & dsh plugin --profile web add $spec 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "dsh plugin add failed for $pkgName (exit=$LASTEXITCODE)"
  }
}

# --- 5. Verify ----------------------------------------------------------
Write-Host ""
Write-Host "[verify] bundles check:"
$updatedManifest = Get-Content $profileManifest -Raw -Encoding UTF8 | ConvertFrom-Json
$bundles = @($updatedManifest.dsh.profile.bundles)
$missing = $allPackages | Where-Object { -not ($bundles -match "^@nsfocus/$_$") }
if ($missing) {
  throw "These packages are missing from bundles: $($missing -join ', '). Check each package.json dsh.bundle.patch field."
}
Write-Host "  OK - all 7 NF packages registered in web profile.bundles"

# --- 6. Python: detect interpreter + install required packages ----------
Write-Host ""
Write-Host "[python] interpreter detection:"

# Resolution order: $env:DSH_PYTHON > %USERPROFILE%\.dsh\python.txt (pin) >
# well-known locations > 'python' on PATH.
$python = $null
$dshPinFile = Join-Path $env:USERPROFILE '.dsh\python.txt'
if ($env:DSH_PYTHON -and (Test-Path $env:DSH_PYTHON)) {
  $python = (Resolve-Path $env:DSH_PYTHON).Path
  Write-Host "  * from \$env:DSH_PYTHON: $python"
} elseif (Test-Path $dshPinFile) {
  $pin = (Get-Content $dshPinFile -Raw -Encoding UTF8).Trim()
  if ($pin -and (Test-Path $pin)) {
    $python = (Resolve-Path $pin).Path
    Write-Host "  * from ${dshPinFile}: $python"
  }
}
if (-not $python) {
  foreach ($candidate in @('C:\Python314\python.exe', 'C:\Python313\python.exe', 'C:\Python312\python.exe')) {
    if (Test-Path $candidate) { $python = (Resolve-Path $candidate).Path; break }
  }
  if ($python) {
    Write-Host "  * well-known location: $python"
  }
}
if (-not $python) {
  foreach ($name in @('python3', 'python', 'py')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) {
      $python = $cmd.Source
      Write-Host "  * from PATH ($name): $python"
      break
    }
  }
}
if (-not $python) {
  throw "Python not found. Set `$env:DSH_PYTHON, or install Python 3.12+ to a well-known path (C:\Python314\python.exe etc.), or add 'python' to PATH."
}
$pyVer = (& $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
$pyMajor = [int]$pyVer.Split('.')[0]
if ($pyMajor -lt 3) { throw "Python $pyVer too old; need >= 3.12" }
Write-Host "  * version: $pyVer"

# Persist the resolved interpreter so future runs (and other tooling) can reuse it.
New-Item -ItemType Directory -Force -Path (Split-Path $dshPinFile) | Out-Null
Set-Content -Path $dshPinFile -Value $python -Encoding UTF8 -NoNewline
Write-Host "  * pinned to ${dshPinFile}"

# --- 7. pip install required third-party packages (idempotent) ----------
Write-Host ""
Write-Host "[python] pip install (idempotent):"
$requiredPkgs = @('pyyaml', 'paramiko', 'requests')
# Optional (off by default): 'evengsdk' (gns-topo), 'mcp-atlassian' (ask-atlassian skill).
# Enable with: BOOTSTRAP_OPTIONAL_PYDEPS=1
if ($env:BOOTSTRAP_OPTIONAL_PYDEPS -eq '1') {
  $requiredPkgs += @('evengsdk')
  Write-Host "  * BOOTSTRAP_OPTIONAL_PYDEPS=1 -> also installing evengsdk"
}

# pip install is slow when re-run; check first and skip already-installed ones.
$needInstall = @()
foreach ($pkg in $requiredPkgs) {
  $installed = (& $python -m pip show $pkg 2>$null)
  if ($installed -and $LASTEXITCODE -eq 0) {
    Write-Host "  * $pkg - already installed, skip"
  } else {
    $needInstall += $pkg
  }
}
if ($needInstall.Count -gt 0) {
  Write-Host "  * installing: $($needInstall -join ', ')"
  & $python -m pip install $needInstall
  if ($LASTEXITCODE -ne 0) {
    throw "pip install failed for: $($needInstall -join ', ')"
  }
}

# --- 8. Verify core .dsh-memory scripts are syntactically valid --------
Write-Host ""
Write-Host "[python] .dsh-memory scripts syntax check:"
$memoryDir = Join-Path $env:USERPROFILE '.dsh-memory'
foreach ($py in @('search.py', 'tier_manager.py', 'backfill_frontmatter.py', 'fix_yaml_summary.py')) {
  $src = Join-Path $memoryDir "scripts/$py"
  if (-not (Test-Path $src)) {
    # Fallback: scripts may live inside the workspace's .dsh-memory submodule
    $src = "config\.dsh-memory-workspace-not-used\scripts\$py"
    $src = Join-Path $repoRoot ".dsh-memory/scripts/$py"
  }
  if (Test-Path $src) {
    & $python -m py_compile $src 2>$null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "  * $py - OK"
    } else {
      Write-Host "  * $py - SYNTAX ERROR (see above)"
    }
  } else {
    Write-Host "  * $py - not found (skip; memory MCP may be limited)"
  }
}

# --- 9. Render mcp-memory patch into web profile (idempotent) ---------
Write-Host ""
Write-Host "[mcp-memory] patch injection:"
$templatePath = Join-Path $repoRoot 'config/mcp-memory.patch.yml.template'
$patchTarget  = Join-Path $profileDir 'cordis.patch.yml'
if (-not (Test-Path $templatePath)) {
  Write-Host "  * template missing ($templatePath), skip"
} else {
  $template = Get-Content $templatePath -Raw -Encoding UTF8
  $rendered = $template.Replace('{{PYTHON_EXE}}', $python).Replace('{{MEMORY_DIR}}', $memoryDir).Replace('{{SERVER_NAME}}', 'memory')

  $existingPatch = if (Test-Path $patchTarget) { Get-Content $patchTarget -Raw -Encoding UTF8 } else { '' }
  if ($existingPatch -match 'id:\s*mcp-memory') {
    Write-Host "  * mcp-memory already injected in cordis.patch.yml, skip"
  } else {
    Write-Host "  * injecting mcp-memory into $patchTarget"
    Add-Content -Path $patchTarget -Value "`n# --- dsh-memory MCP (added by bootstrap) ---`n$rendered`n" -Encoding UTF8
  }
}

# --- 10. Stub mcp_memory.py if missing (idempotent, never overwrites) -
Write-Host ""
Write-Host "[mcp-memory] stub server:"
$stubSrc = Join-Path $repoRoot 'config/mcp_memory.py.stub'
$stubDst = Join-Path $memoryDir 'scripts/mcp_memory.py'
if (Test-Path $stubDst) {
  Write-Host "  * $stubDst already exists, skip"
} elseif (-not (Test-Path $stubSrc)) {
  Write-Host "  * stub source missing ($stubSrc), skip"
} else {
  $memScriptsDir = Split-Path $stubDst
  New-Item -ItemType Directory -Force -Path $memScriptsDir | Out-Null
  Copy-Item -Path $stubSrc -Destination $stubDst -Force
  Write-Host "  * installed stub -> $stubDst"
  Write-Host "    (real implementation pending per doc/spec P4 (memory MCP server);"
  Write-Host "     replace this file when ready; bootstrap will not overwrite it)"
}

# --- 11. Done -----------------------------------------------------------
Write-Host ""
Write-Host "[bootstrap] DONE. Next:"
Write-Host "  dsh web                 # launch Web GUI (default port 3080)"
Write-Host ""
Write-Host "Daily development does NOT need this script:"
Write-Host "  * TS changes: cd packages/<p> && pnpm exec tsc"
Write-Host "  * client.js / cordis.patch.yml changes: refresh browser or restart dsh web"
Write-Host "  * python deps: re-run with BOOTSTRAP_OPTIONAL_PYDEPS=1 to also install evengsdk"

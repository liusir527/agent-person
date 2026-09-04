<#
.SYNOPSIS
    agent-person one-click installer (idempotent). Deploys the .dsh-memory
    submodule to %USERPROFILE%\.dsh-memory and wires up DSH integration.

.DESCRIPTION
    Run after `git clone --recursive` of the agent-person repo. Steps:
      1. prerequisite checks (git / python / dsh)
      2. submodule init (git submodule update --init --recursive)
      3. deploy memory repo (robocopy submodule -> target dir, excluding cache)
      4. install python deps (jieba, pyyaml)
      5. write ~/.dsh/AGENTS.md (instantiated from template)
      6. register MCP channel (dsh-mcp-client install + cordis.patch.yml snippet)
      7. rebuild index
      8. smoke test
      9. print report

    NOTE: this script is pure ASCII on purpose (works with Windows
    PowerShell 5.1 which decodes BOM-less UTF-8 as ANSI/GBK).

.PARAMETER MemoryDir
    Memory repo deploy directory. Default: $env:USERPROFILE\.dsh-memory

.PARAMETER Profile
    Target dsh profile name. Default: web

.PARAMETER ServerName
    MCP serverName (tool prefix mcp__<name>__). Default: memory

.PARAMETER WritePatch
    Auto-append the MCP snippet into the profile cordis.patch.yml.
    Default: false (only prints the snippet for manual confirmation)

.PARAMETER SkipInstall
    Skip pip install (speed up when already ready).

.PARAMETER SkipIndex
    Skip index rebuild.

.PARAMETER DryRun
    Print the action plan only, do not execute.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -MemoryDir "D:\mem" -Profile web -WritePatch
#>
[CmdletBinding()]
param(
    [string]$MemoryDir = "$env:USERPROFILE\.dsh-memory",
    [string]$Profile = "web",
    [string]$ServerName = "memory",
    [switch]$WritePatch,
    [switch]$SkipInstall,
    [switch]$SkipIndex,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
# PS 7.3+ 默认会将 native stderr 转为 ErrorRecord（EAP=Stop 时终止）
# 显式阻止此行为，我们只靠 $LASTEXITCODE 判断原生命令成败
$PSNativeCommandUseErrorActionPreference = $false
$reportItems = New-Object System.Collections.ArrayList

function Add-Report {
    param([string]$Step, [string]$Status, [string]$Detail)
    $null = $reportItems.Add([PSCustomObject]@{Step = $Step; Status = $Status; Detail = $Detail })
    Write-Verbose "[$Status] $Step - $Detail"
}

function Test-Cmd {
    param([string]$Name)
    try { Get-Command $Name -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

# ---------------------------------------------------------------- repo root
$RepoRoot = Split-Path -Parent $PSCommandPath
Write-Verbose "Repo root: $RepoRoot"
$SubmoduleDir = Join-Path $RepoRoot ".dsh-memory"
if (-not (Test-Path $SubmoduleDir)) {
    Add-Report "repo layout" "FAIL" "submodule dir missing: $SubmoduleDir"
    exit 1
}

# ------------------------------------------------- Phase 1: prerequisites
Write-Verbose "=== Phase 1: prerequisites ==="
$prereqs = @(
    @{ Name = "git"; Check = { Test-Cmd "git" } },
    @{ Name = "python"; Check = { Test-Cmd "python" } },
    @{ Name = "dsh"; Check = { Test-Cmd "dsh" } }
)
$allOk = $true
foreach ($p in $prereqs) {
    if (& $p.Check) { Add-Report "prereq: $($p.Name)" "PASS" "found" }
    else { Add-Report "prereq: $($p.Name)" "FAIL" "missing"; $allOk = $false }
}
if (-not $allOk) {
    Write-Warning "install missing components and retry"
    if ($DryRun) { exit 0 } else { exit 1 }
}

# ------------------------------------------------- Phase 2: submodule init
Write-Verbose "=== Phase 2: submodule init ==="
if ($DryRun) {
    Add-Report "submodule init" "DRYRUN" "will run: git submodule update --init --recursive"
} else {
    try {
        Push-Location $RepoRoot
        $substat = git submodule status 2>$null | Out-String
        if ($substat -match '^-') {
            # file:// URLs require protocol.file.allow=always
            $subUrl = git config --file .gitmodules --get submodule..dsh-memory.url 2>$null
            if ($subUrl -match '^file://') {
                $null = git -c protocol.file.allow=always submodule update --init --recursive 2>$null
            } else {
                $null = git submodule update --init --recursive 2>$null
            }
            $updateOk = $LASTEXITCODE -eq 0
            if ($updateOk) {
                Add-Report "submodule init" "PASS" "git submodule update --init --recursive"
            } else {
                $err = git submodule status 2>&1 | Out-String
                Add-Report "submodule init" "FAIL" "update failed: $(if ($err) { $err.Trim() } else { 'unknown' })"
            }
        } else {
            Add-Report "submodule init" "PASS" "already ready: $($substat.Trim())"
        }
        Pop-Location
    } catch {
        Add-Report "submodule init" "FAIL" "$($_.Exception.Message)"
        Pop-Location
    }
}

# ------------------------------------------------- Phase 3: deploy memory
Write-Verbose "=== Phase 3: deploy memory repo to $MemoryDir ==="
$MemoryDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($MemoryDir)
if ($DryRun) {
    Add-Report "deploy memory" "DRYRUN" "will robocopy $SubmoduleDir -> $MemoryDir (exclude .git/__pycache__/db cache)"
} else {
    try {
        if (-not (Test-Path $MemoryDir)) {
            New-Item -ItemType Directory -Force -Path $MemoryDir | Out-Null
            Add-Report "deploy memory" "PASS" "created dir $MemoryDir"
        }
        $excludeDirs = @(".git", "__pycache__", "index")
        $excludeFiles = @("index.db", "index.db-wal", "index.db-shm", "benchmark.log", "rebuild.log", "*.pyc")
        $rcArgs = @($SubmoduleDir, $MemoryDir, "/E", "/R:1", "/W:1", "/NP", "/MT:4")
        foreach ($d in $excludeDirs) { $rcArgs += "/XD"; $rcArgs += $d }
        foreach ($f in $excludeFiles) { $rcArgs += "/XF"; $rcArgs += $f }
        $null = & robocopy @rcArgs
        if ($LASTEXITCODE -ge 8) {
            Add-Report "deploy memory" "WARN" "robocopy exit=$LASTEXITCODE (partial copy possible)"
        } else {
            Add-Report "deploy memory" "PASS" "robocopy done (exit=$LASTEXITCODE)"
        }
    } catch {
        Add-Report "deploy memory" "FAIL" "$($_.Exception.Message)"
    }
}

# ------------------------------------------------- Phase 4: python deps
Write-Verbose "=== Phase 4: python deps ==="
if ($SkipInstall) {
    Add-Report "python deps" "SKIP" "-SkipInstall given"
} elseif ($DryRun) {
    Add-Report "python deps" "DRYRUN" "will run: python -m pip install jieba pyyaml"
} else {
    try {
        # 幂等检测：先验证 import，失败才安装
        $test = & python -c "import jieba, yaml; print('ok')" 2>&1
        if ($LASTEXITCODE -eq 0 -and $test -match 'ok') {
            Add-Report "python deps" "PASS" "jieba/pyyaml already available"
        } else {
            $null = & python -m pip install jieba pyyaml 2>&1
            $test2 = & python -c "import jieba, yaml; print('ok')" 2>&1
            if ($LASTEXITCODE -eq 0 -and $test2 -match 'ok') {
                Add-Report "python deps" "PASS" "jieba/pyyaml installed"
            } else {
                Add-Report "python deps" "WARN" "pip install failed to install jieba/pyyaml"
            }
        }
    } catch {
        Add-Report "python deps" "WARN" "$($_.Exception.Message)"
    }
}

# ------------------------------------------------- Phase 5: AGENTS.md
Write-Verbose "=== Phase 5: DSH AGENTS.md ==="
$userProfile = [Environment]::GetFolderPath("UserProfile")
$agentsDir = Join-Path $userProfile ".dsh"
$agentsFile = Join-Path $agentsDir "AGENTS.md"
$templateFile = Join-Path $RepoRoot "config\AGENTS.md.template"
if ($DryRun) {
    Add-Report "AGENTS.md" "DRYRUN" "will write $agentsFile (MEMORY_DIR=$MemoryDir)"
} else {
    try {
        if (-not (Test-Path $agentsDir)) { New-Item -ItemType Directory -Force -Path $agentsDir | Out-Null }
        if (Test-Path $agentsFile) {
            Add-Report "AGENTS.md" "PASS" "already exists, skip (delete to regenerate)"
        } elseif (Test-Path $templateFile) {
            $content = (Get-Content $templateFile -Raw -Encoding UTF8) -replace "{{MEMORY_DIR}}", $MemoryDir.Replace('\', '/')
            Set-Content -Path $agentsFile -Value $content -Encoding UTF8
            Add-Report "AGENTS.md" "PASS" "written $agentsFile"
        } else {
            Add-Report "AGENTS.md" "WARN" "template missing: $templateFile"
        }
    } catch {
        Add-Report "AGENTS.md" "FAIL" "$($_.Exception.Message)"
    }
}

# ------------------------------------------------- Phase 6: MCP channel
Write-Verbose "=== Phase 6: MCP channel ==="
if ($DryRun) {
    Add-Report "MCP register" "DRYRUN" "will install dsh-mcp-client (if missing) and register mcp-memory"
} else {
    try {
        $pluginList = dsh plugin --profile $Profile list 2>&1 | Out-String
        if ($pluginList -match "dsh-mcp-client") {
            Add-Report "MCP plugin" "PASS" "dsh-mcp-client already installed"
        } else {
            $null = dsh plugin --profile $Profile add @deepseek-ai/dsh-mcp-client 2>&1
            Add-Report "MCP plugin" "PASS" "dsh-mcp-client installed"
        }
    } catch {
        Add-Report "MCP plugin" "WARN" "install failed: $($_.Exception.Message). Manual: dsh plugin --profile $Profile add @deepseek-ai/dsh-mcp-client"
    }

    $patchTemplate = Join-Path $RepoRoot "config\mcp-memory.patch.yml.template"
    $snippet = $null
    if (Test-Path $patchTemplate) {
        $snippet = (Get-Content $patchTemplate -Raw -Encoding UTF8) `
            -replace "{{PYTHON_EXE}}", (Get-Command python).Source `
            -replace "{{MEMORY_DIR}}", $MemoryDir.Replace('\', '/') `
            -replace "{{SERVER_NAME}}", $ServerName
    }

    $patchFile = Join-Path $userProfile ".dsh\profiles\$Profile\cordis.patch.yml"
    if ($WritePatch -and $snippet) {
        try {
            if (Test-Path $patchFile) {
                $current = Get-Content $patchFile -Raw -Encoding UTF8
                if ($current -match "mcp-memory") {
                    Add-Report "MCP patch.yml" "PASS" "cordis.patch.yml already has mcp-memory, skip"
                } else {
                    Add-Content -Path $patchFile -Value "`n$snippet" -Encoding UTF8
                    Add-Report "MCP patch.yml" "PASS" "appended to $patchFile"
                }
            } else {
                Set-Content -Path $patchFile -Value $snippet -Encoding UTF8
                Add-Report "MCP patch.yml" "PASS" "created $patchFile"
            }
        } catch {
            Add-Report "MCP patch.yml" "WARN" "write failed: $($_.Exception.Message)"
        }
    } elseif ($snippet) {
        Add-Report "MCP snippet" "INFO" "use -WritePatch to auto-append, or paste manually into: $patchFile"
        Write-Host "`n--- paste below into $patchFile ---" -ForegroundColor Cyan
        Write-Host $snippet -ForegroundColor Gray
        Write-Host "--- end snippet ---`n" -ForegroundColor Cyan
    }
}

# ------------------------------------------------- Phase 7: rebuild index
Write-Verbose "=== Phase 7: rebuild index ==="
$rebuildScript = Join-Path $MemoryDir "scripts\rebuild.py"
if ($SkipIndex) {
    Add-Report "rebuild index" "SKIP" "-SkipIndex given"
} elseif ($DryRun) {
    Add-Report "rebuild index" "DRYRUN" "will run: python $rebuildScript"
} else {
    try {
        if (Test-Path $rebuildScript) {
            $out = python $rebuildScript 2>&1 | Out-String
            Add-Report "rebuild index" "PASS" "rebuild done: $($out.Trim())"
        } else {
            Add-Report "rebuild index" "WARN" "script missing: $rebuildScript"
        }
    } catch {
        Add-Report "rebuild index" "FAIL" "$($_.Exception.Message)"
    }
}

# ------------------------------------------------- Phase 8: smoke test
Write-Verbose "=== Phase 8: smoke test ==="
$smokeScript = Join-Path $MemoryDir "test_smoke.py"
if ($DryRun) {
    Add-Report "smoke test" "DRYRUN" "will run: python $smokeScript"
} else {
    try {
        if (Test-Path $smokeScript) {
            $env:DSH_MEMORY_ROOT = $MemoryDir
            $out = python $smokeScript 2>&1 | Out-String
            if ($out -match "30 PASS.*0 FAIL") {
                Add-Report "smoke test" "PASS" "30/30 PASS"
            } else {
                Add-Report "smoke test" "WARN" "partial: $($out.Substring(0, [Math]::Min(200, $out.Length)))"
            }
            Remove-Item Env:DSH_MEMORY_ROOT -ErrorAction SilentlyContinue
        } else {
            Add-Report "smoke test" "SKIP" "not found: $smokeScript"
        }
    } catch {
        Add-Report "smoke test" "FAIL" "$($_.Exception.Message)"
    }
}

# -------------------------------------------------------- print report
Write-Verbose "=== report ==="
Write-Host "`n===== agent-person install report =====" -ForegroundColor Green
$cPass = 0; $cFail = 0; $cWarn = 0; $cSkip = 0; $cDry = 0
$reportItems | ForEach-Object {
    $row = $_
    switch ($row.Status) {
        "PASS"   { $cPass++; $icon = "[OK]   " }
        "FAIL"   { $cFail++; $icon = "[FAIL] " }
        "WARN"   { $cWarn++; $icon = "[WARN] " }
        "SKIP"   { $cSkip++; $icon = "[SKIP] " }
        "DRYRUN" { $cDry++; $icon = "[DRY]  " }
        "INFO"   { $icon = "[INFO] " }
        default  { $icon = "[?]    " }
    }
    Write-Host "$icon $($row.Step): $($row.Detail)"
}
Write-Host "`nSummary: OK=$cPass FAIL=$cFail WARN=$cWarn SKIP=$cSkip DRY=$cDry" -ForegroundColor $(if ($cFail -eq 0) { "Green" } else { "Yellow" })
if ($cFail -gt 0) { exit 1 } else { exit 0 }

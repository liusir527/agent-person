# scripts/test-mcp-memory.ps1
#
# Smoke test for ~/.dsh-memory/scripts/mcp_memory.py (the MCP stdio server
# that dsh-web spawns when the mcp-memory plugin is enabled).
#
# The test pipes 5 JSON-RPC requests into the server's stdin (initialize,
# tools/list, tools/call, ping, unknown method) and parses each stdout line
# as a JSON-RPC response. Result is written to runtime/test-mcp-memory/.
#
# Run from the repo root:
#   pwsh -File scripts/test-mcp-memory.ps1
#
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# --- Resolve python + stub paths ---------------------------------------
$python = $null
$dshPin = Join-Path $env:USERPROFILE '.dsh\python.txt'
if (Test-Path $dshPin) {
  $pin = (Get-Content $dshPin -Raw -Encoding UTF8).Trim()
  if ($pin -and (Test-Path $pin)) { $python = (Resolve-Path $pin).Path }
}
if (-not $python) {
  foreach ($c in @('C:\Python314\python.exe','C:\Python313\python.exe','C:\Python312\python.exe')) {
    if (Test-Path $c) { $python = (Resolve-Path $c).Path; break }
  }
}
if (-not $python) {
  foreach ($n in @('python3','python','py')) {
    $cmd = Get-Command $n -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source; break }
  }
}
if (-not $python) { throw "Python not found. Set \$env:DSH_PYTHON or rerun scripts/bootstrap-nf-plugins.ps1" }

$stub = Join-Path $env:USERPROFILE '.dsh-memory\scripts\mcp_memory.py'
if (-not (Test-Path $stub)) {
  throw "Stub not found at $stub. Rerun scripts/bootstrap-nf-plugins.ps1"
}

# --- Output directory --------------------------------------------------
$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) { throw "Run from repo root" }
$outDir = Join-Path $repoRoot 'runtime/test-mcp-memory'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# --- Build the request stream ------------------------------------------
$requests = @(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"memory_search","arguments":{"query":"postgres dead-lock"}}}'
  '{"jsonrpc":"2.0","id":4,"method":"ping"}'
  '{"jsonrpc":"2.0","id":5,"method":"nonsense/method"}'
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"memory_read","arguments":{"id":"exp-001"}}}'
  '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"memory_save","arguments":{"text":"hit a postgres deadlock","tags":["postgres","deadlock"]}}}'
)

# --- Spawn python with our stdin --------------------------------------
$requestStream = ($requests -join "`n") + "`n"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = "`"$stub`""
$psi.RedirectStandardInput  = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)
$proc.StandardInput.Write($requestStream)
$proc.StandardInput.Close()

# Read all stdout (with timeout) — python exits when stdin closes.
$stdoutTask = $proc.StandardOutput.ReadToEndAsync()
$stderrTask = $proc.StandardError.ReadToEndAsync()

# Wait up to 10s.
$exited = $proc.WaitForExit(10000)
if (-not $exited) {
  try { $proc.Kill() } catch {}
  throw "Python stub did not exit within 10s; killing."
}

$stdout = $stdoutTask.Result
$stderr = $stderrTask.Result
$exitCode = $proc.ExitCode

# --- Sanity-check Python parses the stub --------------------------------
$pyParse = & $python -c "import ast; ast.parse(open(r'''$stub''', encoding='utf-8').read()); print('ok')" 2>$null
$pyParse = ($pyParse | Select-Object -Last 1)

# --- Save raw + structured results -------------------------------------
$rawOut = Join-Path $outDir 'raw.jsonl'
$stdout -split "`r?`n" | Where-Object { $_ -ne '' } | Set-Content -Path $rawOut -Encoding UTF8

$results = @()
$idx = 0
foreach ($line in ($stdout -split "`r?`n")) {
  if (-not $line) { continue }
  try {
    $resp = $line | ConvertFrom-Json
    $reqMethod = if ($idx -lt $requests.Count) { ($requests[$idx] | ConvertFrom-Json).method } else { '?' }
    $results += [PSCustomObject]@{
      id   = $resp.id
      method = $reqMethod
      ok   = ($null -ne $resp.result)
      err  = $resp.error
      keys = if ($resp.result) { ($resp.result.PSObject.Properties.Name) -join ',' } else { '' }
    }
  } catch {
    $results += [PSCustomObject]@{ id = -1; method = '?'; ok = $false; err = "parse: $_"; keys = '' }
  }
  $idx++
}

$report = [PSCustomObject]@{
  python     = $python
  stub       = $stub
  pySyntax   = $pyParse
  exitCode   = $exitCode
  sentCount  = $requests.Count
  recvCount  = ($stdout -split "`r?`n" | Where-Object { $_ -ne '' }).Count
  stderr     = $stderr
  results    = $results
  timestamp  = (Get-Date -Format 'o')
}
$report | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $outDir 'report.json') -Encoding UTF8

# --- Console summary ---------------------------------------------------
Write-Host ""
Write-Host "[test] python:    $python"
Write-Host "[test] stub:      $stub"
Write-Host "[test] syntax:    $pyParse"
Write-Host "[test] exit:      $exitCode  sent=$($requests.Count)  recv=$($report.recvCount)"
Write-Host ""
Write-Host "id   method                          ok  keys"
Write-Host "---- ------------------------------- --  ----"
foreach ($r in $results) {
  $mark = if ($r.ok) { 'OK' } else { 'ERR' }
  Write-Host ("{0,-4} {1,-31} {2,-3} {3}" -f $r.id, $r.method, $mark, $r.keys)
}
if ($stderr) {
  Write-Host ""
  Write-Host "[stderr]"
  Write-Host $stderr
}

if ($report.recvCount -ne $requests.Count) {
  Write-Host ""
  Write-Host "WARN: response count ($($report.recvCount)) != request count ($($requests.Count))"
  exit 1
}
Write-Host ""
Write-Host "OK - all responses received. Full report: $outDir/report.json"

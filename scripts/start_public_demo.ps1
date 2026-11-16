# =============================================================================
# CYBERSLEUTH AI - Public demo supervisor
# =============================================================================
# Keeps the public demo reachable:
#
#   * starts the API, the preview server and the SSH tunnel
#   * restarts the tunnel when the tunnel service drops the connection
#   * publishes the new tunnel address to the GitHub Pages build, so the
#     published demo follows the tunnel without a rebuild
#
# The tunnel service hands out a new address on every reconnect, so the
# address is written to scripts/.public-demo.txt and pushed to the
# `gh-pages` branch with scripts/set_pages_api_url.mjs.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/start_public_demo.ps1
#
# Stop it with:
#   powershell -ExecutionPolicy Bypass -File scripts/stop_public_demo.ps1
# =============================================================================

param(
    # Local port the public tunnel points at (the Vite preview server).
    [int]$Port = 4173,
    # Local port the API listens on.
    [int]$ApiPort = 8000,
    # Where the tunnel address is written.
    [string]$OutputFile = "$PSScriptRoot\.public-demo.txt",
    # Push the new address to the published demo (requires the GitHub CLI).
    [switch]$Publish
)

$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv310\Scripts\python.exe'
$logDir = Join-Path $env:TEMP 'opencode'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Step($message) {
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Test-Port($port) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $connection)
}

# --- 1. the API ------------------------------------------------------------
if (Test-Port $ApiPort) {
    Write-Step "The API already runs on 127.0.0.1:$ApiPort"
} else {
    Write-Step "Starting the API on 127.0.0.1:$ApiPort"
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort", '--log-level', 'info' `
        -WorkingDirectory (Join-Path $repoRoot 'backend') `
        -RedirectStandardOutput (Join-Path $logDir 'backend.log') `
        -RedirectStandardError (Join-Path $logDir 'backend.err.log') `
        -WindowStyle Hidden | Out-Null
}

# --- 2. the preview server -------------------------------------------------
if (Test-Port $Port) {
    Write-Step "The preview server already runs on 127.0.0.1:$Port"
} else {
    Write-Step "Starting the preview server on 127.0.0.1:$Port"
    Start-Process -FilePath 'npm.cmd' `
        -ArgumentList 'run', 'preview', '--', '--host', '127.0.0.1', '--port', "$Port" `
        -WorkingDirectory (Join-Path $repoRoot 'frontend') `
        -RedirectStandardOutput (Join-Path $logDir 'preview.log') `
        -RedirectStandardError (Join-Path $logDir 'preview.err.log') `
        -WindowStyle Hidden | Out-Null
}

Start-Sleep -Seconds 8

# --- 3. the tunnel, with a reconnect loop ----------------------------------
Write-Step 'Starting the public tunnel (it reconnects automatically)'

$lastUrl = ''
while ($true) {
    $tunnelLog = Join-Path $logDir 'tunnel.log'
    Remove-Item $tunnelLog -ErrorAction SilentlyContinue

    $tunnel = Start-Process -FilePath 'ssh.exe' `
        -ArgumentList '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=6', '-o', 'ExitOnForwardFailure=yes', '-R', "80:127.0.0.1:$Port", 'nokey@localhost.run' `
        -RedirectStandardOutput $tunnelLog `
        -RedirectStandardError (Join-Path $logDir 'tunnel.err.log') `
        -WindowStyle Hidden `
        -PassThru

    # Wait for the tunnel service to report its address.
    $url = $null
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $tunnelLog) {
            $content = Get-Content $tunnelLog -Raw -ErrorAction SilentlyContinue
            if ($content) {
                $match = [regex]::Match($content, 'https://[a-z0-9]+\.app\.lhr\.life')
                if ($match.Success) { $url = $match.Value; break }
            }
        }
        if ($tunnel.HasExited) { break }
    }

    if ($url) {
        Set-Content -Path $OutputFile -Value $url -Encoding utf8
        Write-Host "  Public demo : $url" -ForegroundColor Green
        Write-Host "  API         : $url/api"

        if ($Publish -and $url -ne $lastUrl) {
            Write-Host '  Publishing the address to GitHub Pages ...' -ForegroundColor DarkGray
            & node (Join-Path $PSScriptRoot 'set_pages_api_url.mjs') --url $url
        }
        $lastUrl = $url
    } else {
        Write-Host '  The tunnel did not report an address - retrying in 10s' -ForegroundColor Yellow
    }

    # Wait until the tunnel dies, then reconnect.
    while (-not $tunnel.HasExited) {
        Start-Sleep -Seconds 5
    }
    Write-Host '  The tunnel was closed - reconnecting in 10s' -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

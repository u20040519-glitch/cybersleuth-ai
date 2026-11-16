# =============================================================================
# CYBERSLEUTH AI - Public demo supervisor
# =============================================================================
# Keeps the public demo reachable:
#
#   * starts the API and the preview server on this machine
#   * publishes them through tunnels, so the demo can be opened from anywhere
#     without a Netlify login
#   * restarts a tunnel when it dies and republishes the new address to the
#     GitHub Pages build, so the published demo follows along
#
# Two tunnels are used:
#
#   the app tunnel   -> the preview server (the SPA plus an /api proxy), which
#                       gives one address for the whole application
#   the API tunnel   -> the API itself, which the GitHub Pages build calls
#                       directly (it cannot proxy)
#
# Cloudflare quick tunnels are used when `cloudflared` is available: they
# forward CORS preflight requests to the origin, so the Pages build may call
# the API from another origin. The SSH fallback (localhost.run) is used
# otherwise; it serves the app tunnel perfectly well, but its edge answers
# preflight requests itself, so the Pages build must then be pointed at the
# app tunnel instead of the API.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/start_public_demo.ps1 -Publish
#
# Stop it with:
#   powershell -ExecutionPolicy Bypass -File scripts/stop_public_demo.ps1
# =============================================================================

param(
    # Local port the preview server listens on.
    [int]$Port = 4173,
    # Local port the API listens on.
    [int]$ApiPort = 8000,
    # Where the addresses are written.
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

function Find-Cloudflared {
    $command = Get-Command 'cloudflared' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $local = Join-Path $env:USERPROFILE 'bin\cloudflared.exe'
    if (Test-Path $local) { return $local }
    return $null
}

# ---------------------------------------------------------------------------
# 1. the API and the preview server
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 2. the tunnels
# ---------------------------------------------------------------------------
$cloudflared = Find-Cloudflared
if ($cloudflared) {
    Write-Step "Using the Cloudflare quick tunnel ($cloudflared)"
} else {
    Write-Step 'cloudflared was not found - falling back to the SSH tunnel' -ForegroundColor Yellow
}

function Start-Tunnel {
    <#
        Starts a tunnel to a local port and returns the process plus the
        address the service handed out.
    #>
    param(
        [int]$LocalPort,
        [string]$Name
    )

    if ($cloudflared) {
        $log = Join-Path $logDir "tunnel-$Name.log"
        Remove-Item $log -ErrorAction SilentlyContinue
        $process = Start-Process -FilePath $cloudflared `
            -ArgumentList 'tunnel', '--url', "http://127.0.0.1:$LocalPort", '--no-autoupdate' `
            -RedirectStandardOutput "$log.out" `
            -RedirectStandardError "$log.err" `
            -WindowStyle Hidden `
            -PassThru

        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep -Seconds 1
            if (Test-Path "$log.err") {
                $content = Get-Content "$log.err" -Raw -ErrorAction SilentlyContinue
                if ($content) {
                    $match = [regex]::Match($content, 'https://[a-z0-9\-]+\.trycloudflare\.com')
                    if ($match.Success) { return @{ Process = $process; Url = $match.Value } }
                }
            }
            if ($process.HasExited) { break }
        }
        return @{ Process = $process; Url = $null }
    }

    $log = Join-Path $logDir "tunnel-$Name.log"
    Remove-Item $log -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath 'ssh.exe' `
        -ArgumentList '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=6', '-o', 'ExitOnForwardFailure=yes', '-R', "80:127.0.0.1:$LocalPort", 'nokey@localhost.run' `
        -RedirectStandardOutput $log `
        -RedirectStandardError (Join-Path $logDir "tunnel-$Name.err.log") `
        -WindowStyle Hidden `
        -PassThru

    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $log) {
            $content = Get-Content $log -Raw -ErrorAction SilentlyContinue
            if ($content) {
                $match = [regex]::Match($content, 'https://[a-z0-9]+\.app\.lhr\.life')
                if ($match.Success) { return @{ Process = $process; Url = $match.Value } }
            }
        }
        if ($process.HasExited) { break }
    }
    return @{ Process = $process; Url = $null }
}

function Publish-ApiUrl($url) {
    if (-not $Publish -or -not $url) { return }
    Write-Host '  Publishing the address to GitHub Pages ...' -ForegroundColor DarkGray
    & node (Join-Path $PSScriptRoot 'set_pages_api_url.mjs') --url $url | Out-Null
}

Write-Step 'Starting the public tunnels'

$appTunnel = Start-Tunnel -LocalPort $Port -Name 'app'
$apiTunnel = Start-Tunnel -LocalPort $ApiPort -Name 'api'

if (-not $appTunnel.Url) {
    Write-Host 'The application tunnel did not report an address.' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host '  Public demo : ' -NoNewline
Write-Host $appTunnel.Url -ForegroundColor Green

if ($apiTunnel.Url) {
    Write-Host '  API         : ' -NoNewline
    Write-Host "$($apiTunnel.Url)/api" -ForegroundColor Green
    Publish-ApiUrl $apiTunnel.Url
} else {
    # Without a separate API tunnel the Pages build has to use the app
    # tunnel, whose /api path is proxied to the backend.
    Write-Host '  API         : ' -NoNewline
    Write-Host "$($appTunnel.Url)/api (through the app tunnel)" -ForegroundColor Green
    Publish-ApiUrl $appTunnel.Url
}

Set-Content -Path $OutputFile -Value $appTunnel.Url -Encoding utf8
Write-Host ''
Write-Host '  The tunnels run until this machine is switched off.'
Write-Host '  Stop everything with scripts/stop_public_demo.ps1'

# ---------------------------------------------------------------------------
# 3. keep the tunnels alive
# ---------------------------------------------------------------------------
while ($true) {
    Start-Sleep -Seconds 10

    if ($appTunnel.Process.HasExited) {
        Write-Host 'The application tunnel died - restarting it in 10s' -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        $appTunnel = Start-Tunnel -LocalPort $Port -Name 'app'
        if ($appTunnel.Url) {
            Set-Content -Path $OutputFile -Value $appTunnel.Url -Encoding utf8
            Write-Host "  Public demo : $($appTunnel.Url)" -ForegroundColor Green
        }
    }

    if ($apiTunnel.Process.HasExited) {
        Write-Host 'The API tunnel died - restarting it in 10s' -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        $apiTunnel = Start-Tunnel -LocalPort $ApiPort -Name 'api'
        if ($apiTunnel.Url) {
            Write-Host "  API         : $($apiTunnel.Url)/api" -ForegroundColor Green
            Publish-ApiUrl $apiTunnel.Url
        }
    }
}

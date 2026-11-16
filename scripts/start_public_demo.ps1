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

# Only one supervisor may run: the Startup entry and a manual start would
# otherwise open two sets of tunnels and fight over the address file. A named
# mutex is the precise way to detect it - a search through the process list
# would also match the shell that merely mentions this script.
$mutex = New-Object System.Threading.Mutex($false, 'Local\CyberSleuthAiPublicDemo')
$ownsMutex = $mutex.WaitOne(0)
if (-not $ownsMutex) {
    Write-Host 'The public demo is already running. Nothing to do.'
    exit 0
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
function Start-Api {
    Write-Step "Starting the API on 127.0.0.1:$ApiPort"
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort", '--log-level', 'info' `
        -WorkingDirectory (Join-Path $repoRoot 'backend') `
        -RedirectStandardOutput (Join-Path $logDir 'backend.log') `
        -RedirectStandardError (Join-Path $logDir 'backend.err.log') `
        -WindowStyle Hidden | Out-Null
}

function Start-Preview {
    Write-Step "Starting the preview server on 127.0.0.1:$Port"
    Start-Process -FilePath 'npm.cmd' `
        -ArgumentList 'run', 'preview', '--', '--host', '127.0.0.1', '--port', "$Port" `
        -WorkingDirectory (Join-Path $repoRoot 'frontend') `
        -RedirectStandardOutput (Join-Path $logDir 'preview.log') `
        -RedirectStandardError (Join-Path $logDir 'preview.err.log') `
        -WindowStyle Hidden | Out-Null
}

if (Test-Port $ApiPort) {
    Write-Step "The API already runs on 127.0.0.1:$ApiPort"
} else {
    Start-Api
}

if (Test-Port $Port) {
    Write-Step "The preview server already runs on 127.0.0.1:$Port"
} else {
    Start-Preview
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

function Publish-ApiUrl($urls) {
    if (-not $Publish) { return }
    $list = @($urls | Where-Object { $_ })
    if ($list.Count -eq 0) { return }

    Write-Host '  Publishing the address to GitHub Pages ...' -ForegroundColor DarkGray
    $arguments = @((Join-Path $PSScriptRoot 'set_pages_api_url.mjs'))
    foreach ($url in $list) { $arguments += @('--url', $url) }
    & node @arguments | Out-Null
}

function Test-Tunnel($url) {
    <#
        Checks that a tunnel really serves traffic.

        A quick tunnel can be dropped by the edge while cloudflared keeps
        running and keeps retrying the registration of a tunnel that no
        longer exists ("Unauthorized: Tunnel not found"). The process is
        alive, but nothing is served - so the address has to be probed, not
        the process watched.
    #>
    if (-not $url) { return $false }
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 15 -UseBasicParsing
        return ($response.StatusCode -lt 500)
    } catch {
        return $false
    }
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
    # Both tunnels serve the API, so both are published: if one of them is
    # replaced, the published demo still finds a working address.
    Publish-ApiUrl @($apiTunnel.Url, $appTunnel.Url)
} else {
    # Without a separate API tunnel the Pages build has to use the app
    # tunnel, whose /api path is proxied to the backend.
    Write-Host '  API         : ' -NoNewline
    Write-Host "$($appTunnel.Url)/api (through the app tunnel)" -ForegroundColor Green
    Publish-ApiUrl @($appTunnel.Url)
}

Set-Content -Path $OutputFile -Encoding utf8 -Value @(
    "app: $($appTunnel.Url)"
    "api: $(if ($apiTunnel.Url) { "$($apiTunnel.Url)/api" } else { "$($appTunnel.Url)/api" })"
)

Write-Host ''
Write-Host '  The tunnels run until this machine is switched off.'
Write-Host '  Stop everything with scripts/stop_public_demo.ps1'

# ---------------------------------------------------------------------------
# 3. keep everything alive
# ---------------------------------------------------------------------------
$appFailures = 0
$apiFailures = 0

while ($true) {
    Start-Sleep -Seconds 15

    # The API and the preview server are watched as well: a crash there
    # would break the demo just as badly as a dead tunnel.
    if (-not (Test-Port $ApiPort)) {
        Write-Step 'The API is not listening - restarting it'
        Start-Api
    }

    if (-not (Test-Port $Port)) {
        Write-Step 'The preview server is not listening - restarting it'
        Start-Preview
    }

    # --- the application tunnel ---------------------------------------------
    if ($appTunnel.Process.HasExited) {
        $appFailures = 2
    } elseif (Test-Tunnel $appTunnel.Url) {
        $appFailures = 0
    } else {
        $appFailures++
    }

    if ($appFailures -ge 2) {
        Write-Step 'The application tunnel does not serve anything - replacing it'
        try { $appTunnel.Process.Kill() } catch { }
        $appTunnel = Start-Tunnel -LocalPort $Port -Name 'app'
        $appFailures = 0
        if ($appTunnel.Url) {
            Set-Content -Path $OutputFile -Encoding utf8 -Value @(
                "app: $($appTunnel.Url)"
                "api: $(if ($apiTunnel.Url) { "$($apiTunnel.Url)/api" } else { "$($appTunnel.Url)/api" })"
            )
            Write-Host "  Public demo : $($appTunnel.Url)" -ForegroundColor Green
            Publish-ApiUrl @($(if ($apiTunnel.Url) { $apiTunnel.Url }), $appTunnel.Url)
        }
    }

    # --- the API tunnel -----------------------------------------------------
    if ($apiTunnel.Process.HasExited) {
        $apiFailures = 2
    } elseif (Test-Tunnel "$($apiTunnel.Url)/api/health") {
        $apiFailures = 0
    } else {
        $apiFailures++
    }

    if ($apiFailures -ge 2) {
        Write-Step 'The API tunnel does not serve anything - replacing it'
        try { $apiTunnel.Process.Kill() } catch { }
        $apiTunnel = Start-Tunnel -LocalPort $ApiPort -Name 'api'
        $apiFailures = 0
        if ($apiTunnel.Url) {
            Write-Host "  API         : $($apiTunnel.Url)/api" -ForegroundColor Green
            Publish-ApiUrl @($apiTunnel.Url, $appTunnel.Url)
        }
    }
}

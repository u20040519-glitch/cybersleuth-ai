# =============================================================================
# CYBERSLEUTH AI - Stop the public demo
# =============================================================================
# Stops the processes started by scripts/start_public_demo.ps1: the tunnel,
# the preview server and the API. The embedded PostgreSQL keeps running (it
# holds the demo data and starts again automatically).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/stop_public_demo.ps1
# =============================================================================

$ErrorActionPreference = 'SilentlyContinue'

function Stop-ByCommandLine($pattern, $label) {
    $processes = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like $pattern }
    foreach ($process in $processes) {
        Write-Host "Stopping $label (pid $($process.ProcessId))"
        Stop-Process -Id $process.ProcessId -Force
    }
}

Stop-ByCommandLine '*localhost.run*' 'the tunnel'
Stop-ByCommandLine '*vite*preview*' 'the preview server'
Stop-ByCommandLine '*uvicorn*app.main*' 'the API'

Remove-Item "$PSScriptRoot\.public-demo.txt" -ErrorAction SilentlyContinue
Write-Host 'Public demo stopped.'

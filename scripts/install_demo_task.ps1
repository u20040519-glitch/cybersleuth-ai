# =============================================================================
# CYBERSLEUTH AI - Install the public demo as a Windows scheduled task
# =============================================================================
# The published demo (https://u20040519-glitch.github.io/cybersleuth-ai/) is
# served by GitHub Pages, but its API runs on this machine behind a tunnel.
# Registering the supervisor as a scheduled task makes the demo come back by
# itself after a reboot or a sign-out, without anybody having to start it.
#
# The task starts:
#
#   * at every logon (so the demo is back after a restart), and
#   * when the machine starts (for the case that nobody logs in).
#
# It runs as the current user and needs no administrator rights for the logon
# trigger.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/install_demo_task.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/install_demo_task.ps1 -Remove
# =============================================================================

param(
    # Remove the task instead of creating it.
    [switch]$Remove,
    # Name of the scheduled task.
    [string]$TaskName = 'CyberSleuth AI - public demo',
    # Skip the scheduled task and use the Startup folder instead (no
    # administrator rights needed, but the demo then only starts after a
    # sign-in).
    [switch]$StartupFolder
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'start_public_demo.ps1'
$arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Publish"

# The Startup folder works without administrator rights.
$startup = [Environment]::GetFolderPath('Startup')
$shortcut = Join-Path $startup 'CyberSleuth AI - public demo.cmd'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item $shortcut -ErrorAction SilentlyContinue
    Write-Host "Removed the scheduled task '$TaskName' and the Startup entry."
    exit 0
}

if (-not (Test-Path $script)) { throw "Cannot find $script" }

# --- the Startup folder entry ----------------------------------------------
@(
    '@echo off'
    "rem Starts the CyberSleuth AI public demo (API + preview server + tunnels)."
    "start ""CyberSleuth AI public demo"" /min powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Publish"
) | Set-Content -Path $shortcut -Encoding ascii

Write-Host "Added the Startup entry: $shortcut"
Write-Host 'The public demo now starts by itself after every sign-in.'

# --- the scheduled task (needs administrator rights) ------------------------
if (-not $StartupFolder) {
    try {
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
        $logon = New-ScheduledTaskTrigger -AtLogOn
        $boot = New-ScheduledTaskTrigger -AtStartup
        $boot.Delay = 'PT3M'

        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -RestartCount 10 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -MultipleInstances IgnoreNew

        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $action `
            -Trigger @($logon, $boot) `
            -Settings $settings `
            -Principal $principal `
            -Force | Out-Null

        Write-Host "Registered the scheduled task '$TaskName'."
        Write-Host 'The public demo now starts on its own after every logon and every boot.'
    } catch {
        Write-Host "The scheduled task could not be registered ($($_.Exception.Message))."
        Write-Host 'The Startup folder entry is enough for a normal sign-in; run this script'
        Write-Host 'as administrator to add the boot trigger as well.'
    }
}

Write-Host 'Start it right now with:'
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$script`" -Publish"

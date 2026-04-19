# install.ps1 — Registriert den Autostart-Task bei Windows Task Scheduler.
#
# Voraussetzung: venv ist bereits angelegt (`python -m venv .venv` im Projekt-Root)
# und `pip install -e .` wurde ausgefuehrt. Skript prueft das.
#
# Ausfuehren:
#   cd <projekt-root>
#   ./install/install.ps1
#
# Das Skript legt einen Task "Kraken Claude Monitor" an, der bei jedem Login
# automatisch startet. pythonw.exe wird statt python.exe verwendet, damit
# kein Konsolenfenster erscheint. Logs laufen nach
# %USERPROFILE%\kraken-claude-monitor.log.

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$pythonwExe  = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$configFile  = Join-Path $projectRoot "config.default.toml"

Write-Host "Projekt-Root: $projectRoot"

# Pre-Flight-Checks — lieber hier scheitern als im Task-Scheduler.
if (-not (Test-Path $pythonwExe)) {
    Write-Error "pythonw.exe nicht gefunden: $pythonwExe`nBitte erst venv einrichten: python -m venv .venv"
    exit 1
}
if (-not (Test-Path $configFile)) {
    Write-Error "config.default.toml fehlt unter: $configFile"
    exit 1
}

$taskName = "Kraken Claude Monitor"
$userId   = "$env:USERDOMAIN\$env:USERNAME"

$action = New-ScheduledTaskAction `
    -Execute $pythonwExe `
    -Argument "-m kraken_monitor" `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $userId `
    -LogonType Interactive `
    -RunLevel Limited

# Vorhandenen Task loeschen, damit Re-Install idempotent ist.
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Live-Claude-Code-Quota auf NZXT Kraken LCD" | Out-Null

Write-Host ""
Write-Host "[OK] Task '$taskName' registriert."
Write-Host "    Trigger: AtLogOn ($userId)"
Write-Host "    Exec:    $pythonwExe -m kraken_monitor"
Write-Host "    CWD:     $projectRoot"
Write-Host "    Log:     $env:USERPROFILE\kraken-claude-monitor.log"
Write-Host ""
Write-Host "Sofort starten mit:"
Write-Host "    Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
Write-Host "Status pruefen mit:"
Write-Host "    Get-ScheduledTaskInfo -TaskName '$taskName'"

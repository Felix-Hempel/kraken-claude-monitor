# uninstall.ps1 - Entfernt den Kraken-Claude-Monitor Task.

$ErrorActionPreference = "Stop"

$taskName = "Kraken Claude Monitor"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "[info] Task '$taskName' nicht registriert - nichts zu tun."
    exit 0
}

# Laufenden Task stoppen (falls aktiv), dann loeschen.
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false

Write-Host "[OK] Task '$taskName' entfernt."
Write-Host "Hinweis: venv, Code und Logdatei bleiben bestehen."


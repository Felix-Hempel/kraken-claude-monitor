# Troubleshooting

Reihenfolge: Vom Häufigsten zum Seltensten.

## 1. `liquidctl list` zeigt Kraken nicht

**Symptom:** Nach Erst-Install oder Windows-Update ist der Kraken aus der Device-Liste verschwunden.

**Ursache (häufig):** MI_01 hat `libusb0` statt `HidUsb` (alter Zadig-Lauf hat falsches Interface erwischt).

**Fix:** Admin-PowerShell:

```powershell
pnputil /enum-drivers | Select-String "nzxt_kraken|libwdi"
# Notiere den Published Name (z.B. oem99.inf) der falsch gebundenen INF.
pnputil /delete-driver oemNN.inf /uninstall /force
pnputil /restart-device "USB\VID_1E71&PID_300E&MI_01\<instanz-id>"
```

Danach `Get-PnpDevice -PresentOnly -InstanceId 'USB\VID_1E71&PID_300E*'` prüfen — MI_01 sollte jetzt Service `HidUsb` haben.

Volle Recovery-Anleitung: `docs/sprint-1/ZADIG-SETUP.md`.

## 2. `AccessDeniedError` beim `liquidctl status` oder test-push

**Symptom:** `liquidctl --match kraken status` wirft `AccessDeniedError` oder Push hängt.

**Ursache:** NZXT CAM läuft und hat das HID-Handle blockiert.

**Fix:**

- In CAM den Kraken-LCD auf "Off" stellen (siehe `docs/sprint-1/CAM-COEXISTENCE.md`)
- Oder CAM während der Monitor-Session komplett beenden:
  ```powershell
  Get-Process "NZXT CAM" -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

Der Monitor selbst hat `cam_check.py` eingebaut, das eine Warning loggt wenn CAM läuft.

## 3. `AttributeError: 'NoneType' object has no attribute 'write'` bei erstem Push

**Symptom:** `python -m kraken_monitor test-push <pfad>` crasht mit dem genannten Error auf Kraken 2023 (PID 0x300E).

**Ursache:** liquidctl's `winusbcdc`-Library findet das Bulk-Interface MI_00 nicht. Zwei Bugs treffen zusammen — hardcoded WinUSB-GUID und fehlender VID/PID-Filter.

**Fix:** Ist bereits im Code (`src/kraken_monitor/kraken.py:_patch_winusbcdc`). Falls der Patch nicht greift: sicherstellen, dass das Modul `kraken_monitor.kraken` importiert wird, bevor `liquidctl.find_liquidctl_devices()` aufgerufen wird. Details: `docs/sprint-1/WINUSBCDC-PATCH.md`.

## 4. Zweiter Push im Loop hängt / `AssertionError: missing messages`

**Symptom:** Loop macht den ersten Push erfolgreich, beim zweiten crasht `liquidctl.kraken3._read_until` mit "missing messages (attempts=12)".

**Ursache:** Nach dem FW2-static-Push bleiben HID-Reports in der Queue, und der nächste `set_screen([0x30, 0x01])`-Call bekommt keine Antwort.

**Fix:** `KrakenDevice.push_frame` ruft vor `set_screen` `clear_enqueued_reports()` auf. Ist im Code (`src/kraken_monitor/kraken.py:185`). Falls trotzdem Symptom auftritt: liquidctl-Version prüfen (`pip show liquidctl`) — 1.14+ muss es sein.

## 5. Display zeigt verzerrtes / "lila" Muster statt Bild

**Symptom:** Push läuft ohne Error, aber statt des Test-Bildes ist nur buntes Rauschen auf dem LCD.

**Ursache:** Falsche `lcd_resolution`. Panel ist physisch 640×640, aber Firmware erwartet **240×240**-Framebuffer und skaliert intern. Bei falscher Auflösung bleiben bei gleichfarbigen Bildern unsichtbar, bei Mustern wird's chaotisch.

**Fix:** `KrakenDevice.connect()` setzt `lcd_resolution = (240, 240)` explizit (Code: `src/kraken_monitor/kraken.py:_LCD_RESOLUTION`). Falls doch kaputt: Smoke-Test mit monochromem PNG (z.B. vollweiß) ausprobieren — wenn das geht, ist nur die Auflösung falsch.

## 6. `ccusage` / `npx` nicht gefunden

**Symptom:** `CCUsageError: npx nicht gefunden`.

**Fix:**

- Node.js installieren (https://nodejs.org/, LTS-Version reicht)
- Verifizieren: `npx ccusage@latest blocks --json` läuft ohne Fehler
- Beim ersten Call lädt npm das Package — dauert 30-60s. Der Monitor-Timeout ist 30s, beim Erst-Start können daher die ersten 1-2 Polls failen und in den Stale-Mode rutschen. Ab dem 2. Start geht's aus dem Cache schnell (< 2s).

## 7. Task-Scheduler: Task läuft nicht nach Login

**Symptom:** `install.ps1` hat Task registriert, aber nach Reboot/Login passiert nichts am LCD.

**Fix:**

```powershell
# Status prüfen:
Get-ScheduledTaskInfo -TaskName "Kraken Claude Monitor"
# LastRunTime, LastTaskResult (0 = OK, !=0 = Fehler-Code)

# Task-Log-Datei anschauen:
Get-Content "$env:USERPROFILE\kraken-claude-monitor.log" -Tail 30

# Manuell starten zum Debuggen:
Start-ScheduledTask -TaskName "Kraken Claude Monitor"

# Falls UserId falsch: Task neu registrieren mit korrektem $env:USERDOMAIN\$env:USERNAME:
./install/uninstall.ps1
./install/install.ps1
```

Wenn der Task als `LastTaskResult: 267011` (0x41303) zeigt, lief er nie — meist falsche UserId. Wenn `1` kam, hat der Python-Prozess einen Nicht-0-Exit produziert; Logdatei prüfen.

## 8. LCD zeigt dauerhaft 100%

**Symptom:** Prozent-Ring ist voll rot bei 100%, obwohl du nichts gemacht hast.

**Ursache:** `plan.session_token_limit = 19000` ist zu klein für den tatsächlichen Plan (mit Opus 1M Context gehen einzelne Tool-Calls leicht über 1 M Tokens inkl. Cache-Reads).

**Fix:** In `config.local.toml` auf `plan.type = "auto"` stellen — dann nutzt der Monitor `ccusage --token-limit max` und das historisch maximale 5h-Block-Limit als Plan-Proxy. Meist ein paar hundert Millionen Tokens, passend zum realen Verbrauch.

## 9. Nach Windows-Update ist alles kaputt

Typisch: Windows-Update hat einen Treiber ersetzt. Durchgehen:

1. `Get-PnpDevice -PresentOnly -InstanceId 'USB\VID_1E71&PID_300E*'` — beide Interfaces mit `HidUsb` / `WinUSB`-Service?
2. Falls MI_01 jetzt WinUSB hat statt HidUsb → Recovery Fall 1 in `docs/sprint-1/ZADIG-SETUP.md`
3. `python scripts/post_install.py` nochmal ausführen (libusb-DLL könnte weg sein)
4. `liquidctl list` checken

## Logs sammeln für einen Bug-Report

```powershell
# Letzte 100 Zeilen Monitor-Log:
Get-Content "$env:USERPROFILE\kraken-claude-monitor.log" -Tail 100

# Device-Snapshot:
Get-PnpDevice -PresentOnly -InstanceId 'USB\VID_1E71&PID_300E*','HID\VID_1E71&PID_300E*' | Format-List FriendlyName, Class, Service, Status

# liquidctl-Diagnose:
liquidctl --verbose list
liquidctl --match kraken status

# Python + Dependencies:
python --version
pip show liquidctl winusbcdc pyusb pillow | Select-String "^(Name|Version)"
```

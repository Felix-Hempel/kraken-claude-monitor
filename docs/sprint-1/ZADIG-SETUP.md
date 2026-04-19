# Kraken 2023 Treiber-Setup (PID 1E71:300E)

> **Kurzform:** Für Kraken 2023 / FW 2.X.Y gilt: MI_00 = WinUSB (Bulk/Display), MI_01 = HidUsb (HID-Steuerung). In dieser Konstellation werden **keine Zadig-Custom-Treiber** benötigt — Windows bindet beide Interfaces automatisch korrekt. Zadig ist nur im Recovery-Fall nötig.

## Interface-Layout (PID 0x300E, verifiziert via USB-Descriptor)

| Interface | Rolle | Benötigter Windows-Treiber | Service |
|-----------|-------|----------------------------|---------|
| MI_00 | Bulk-Endpoints (LCD-Bildtransfer, ~820 KB pro Frame) | WinUSB | `WINUSB` |
| MI_01 | HID-Class Interrupt-EPs (Steuerung, Pumpe, Sensoren, LCD-Mode) | HidUsb | `HidUsb` |

**Achtung — Falle:** Bei älteren Kraken X3/Z3 (PID 0x2007, 0x3008) sind die Rollen umgekehrt (MI_00 = HID, MI_01 = Bulk). Die ältere liquidctl-Dokumentation und viele Zadig-Tutorials beziehen sich auf dieses Layout. **Für Kraken 2023 (0x300E) nicht übernehmen.**

## Verifikation (sollte nach normalem Windows-Enumerate passen)

```powershell
Get-PnpDevice -PresentOnly -InstanceId 'USB\VID_1E71&PID_300E*','HID\VID_1E71&PID_300E*' |
    Format-List FriendlyName, Class, Service, Status
```

Erwartet:
- `USB Composite Device` (Service `usbccgp`)
- `NZXT Kraken Base` auf MI_00 (Service **`WINUSB`**)
- `USB Input Device` / `HID-compliant vendor-defined device` auf MI_01 (Service **`HidUsb`**)

liquidctl-Test:
```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\liquidctl.exe list
# Erwartet: "Device #N: NZXT Kraken 2023"
```

## Wenn das Layout anders aussieht — Recovery

### Fall 1: MI_01 hat `libusb0` statt `HidUsb`
Typisch nach einem früheren Zadig-Lauf, der fälschlich auf Interface 1 libusb-win32 installiert hat.

1. Zadig-generierten INF aus dem Driver-Store entfernen (**Admin-PowerShell**):
   ```powershell
   pnputil /enum-drivers
   # OEM-INF finden, dessen "Original Name" `nzxt_kraken_base_(interface_1).inf` o. ä. enthält
   pnputil /delete-driver oemNN.inf /uninstall /force
   ```
2. USB-Kabel der Kraken kurz abziehen und wieder einstecken (oder **Admin-PS**: `pnputil /restart-device "USB\VID_1E71&PID_300E&MI_01\<instanz>"`)
3. Windows bindet `HidUsb` automatisch neu (MI_01 meldet HID-Class laut USB-Descriptor).

### Fall 2: MI_00 hat `HidUsb` statt `WinUSB`
Wird Windows normalerweise nicht so machen, weil MI_00 keine HID-Class-Descriptoren hat. Falls doch: im **Geräte-Manager** unter *Human Interface Devices* → `NZXT Kraken Base` (MI_00) → *Deinstallieren* (Haken *Treibersoftware entfernen*) → *Aktion → Nach geänderter Hardware suchen*. Windows sollte MS_COMP_WINUSB matchen und `winusb.inf` binden.

### Fall 3: winusbcdc findet das Bulk-Interface nicht (`bulk_device: None`)
Ist ein Bibliotheks-Inkompatibilitäts-Problem, kein Treiber-Problem. Siehe `WINUSBCDC-PATCH.md`.

## Warum früher `libusb-win32 auf MI_01` empfohlen wurde

Die ursprüngliche Version dieser Doku (und viele Community-Guides) kam vom Kraken X3/Z3-Layout. Das Reverse-Engineering für PID 0x300E in der Session 2026-04-19 hat per USB-Descriptor-Dump bestätigt:

```
INTERFACE 1: Human Interface Device
  bInterfaceClass: 0x3 (HID)
  EP 0x81 IN  Interrupt, 64 byte mps
  EP 0x01 OUT Interrupt, 64 byte mps
```

Das ist eindeutig das HID-Steuerinterface. MI_00 (nicht im obigen Dump sichtbar, weil libusb auf Windows nur das an es gebundene Interface liefert) ist per Ausschlussverfahren + CAM-Verhalten das Bulk-Interface.

## Häufige Fehler

| Symptom | Ursache | Fix |
|---------|---------|-----|
| `liquidctl list` zeigt Kraken nicht | MI_01 hat WinUSB oder libusb0 statt HidUsb | Recovery Fall 1 |
| `AccessDeniedError` beim Status | CAM läuft und blockiert HID | CAM beenden (Task-Manager) |
| `bulk_device: None` / `AttributeError: NoneType has no write` | winusbcdc findet MI_00 nicht | `WINUSBCDC-PATCH.md` |
| Bild wird nicht angezeigt / verzerrt | `lcd_resolution` auf falschem Wert | muss `(240, 240)` sein, siehe CLAUDE.md Regel 5 |
| Nach Windows-Update alles weg | Update hat Treiber ersetzt | Recovery-Fälle durchgehen |

## Reset (alles auf Anfang)

1. Geräte-Manager → alle `NZXT Kraken`-Einträge deinstallieren (mit *Treibersoftware entfernen*)
2. Admin-PS: `pnputil /enum-drivers` → alle OEM-INFs mit `libwdi` oder `nzxt_kraken` entfernen via `pnputil /delete-driver oemNN.inf /uninstall /force`
3. Kraken USB-Kabel abziehen + neu einstecken
4. Windows installiert Standard-Treiber neu — in der Regel direkt korrektes Layout (MI_00 WinUSB via MS_COMP_WINUSB, MI_01 HidUsb via HID-Descriptor)

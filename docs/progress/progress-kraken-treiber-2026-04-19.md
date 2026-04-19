# Kraken 2023 Treiber + LCD-Push — Debug-Session 2026-04-19

## Ausgangslage

Sprint 1 noch TODO. User wollte einen manuellen Test-Push auf das Kraken-LCD, um den Hardware-Pfad zu validieren bevor Sprint 1 richtig anfängt. `liquidctl list` zeigte die Kraken nicht an.

## Was rauskam

### 1. Geräte-Identifikation

- USB-ID: `1E71:300E` (nicht 0x3008/0x3012 wie in älteren Docs angenommen)
- liquidctl 1.16 kennt PID 0x300E als "NZXT Kraken 2023"
- Firmware-Version: **2.0.0** — fällt unter den "static-Bug"-Code-Pfad (`_send_2023_data_fw2`), nicht den regulären FW1-Pfad mit Bucket-Setup
- Panel-Auflösung: physisch 640×640, **Framebuffer 240×240** (Firmware skaliert intern). Bei 640er-Frames wird bei uniformen Farben korrekt angezeigt, aber Muster/Text verzerrt — diagnostisch bestätigt durch Push von solid-white (OK), solid-red (OK), test.png @ 640 (verzerrt), test.png @ 240 (OK).
- CLAUDE.md hatte "Kraken Elite LCD (640×640)" stehen — ist korrigiert auf "Kraken 2023 (physisch 640×640, Framebuffer 240×240)".

### 2. Korrektes Treiber-Layout

Per USB-Descriptor-Dump (pyusb) verifiziert:

```
INTERFACE 1: Human Interface Device
  bInterfaceClass: 0x3 (HID)
  EP 0x81 IN  Interrupt, 64 byte mps
  EP 0x01 OUT Interrupt, 64 byte mps
```

→ **MI_01 ist das HID-Steuerinterface**, MI_00 per Ausschluss das Bulk/Display-Interface.

Bei älterer Kraken X3/Z3 (liquidctl-Doku + `docs/sprint-1/ZADIG-SETUP.md` alt) ist es umgekehrt. Die bestehende ZADIG-SETUP.md war für 2023er-Kraken irreführend — ist neu geschrieben.

Korrekte Treiber-Bindung:
- MI_00 → `WINUSB` (via Microsoft `winusb.inf`, CompatibilityID-Match `MS_COMP_WINUSB`)
- MI_01 → `HidUsb` (via HID-Class-Descriptor, automatisch)

**Keine Zadig-Installation nötig.** Wenn MI_01 durch früheren falschen Zadig-Lauf libusb-win32 hat, muss der OEM-INF aus dem Store entfernt werden:

```powershell
# Admin-PS
pnputil /enum-drivers           # suche nzxt_kraken_base_(interface_1).inf
pnputil /delete-driver oemNN.inf /uninstall /force
pnputil /restart-device "USB\VID_1E71&PID_300E&MI_01\<instanz>"
```

### 3. winusbcdc-Inkompatibilitäten (Runtime-Patch nötig)

Auch mit korrektem Treiber-Layout fehlte `bulk_device` — zwei Bugs in `winusbcdc`:

**Bug A:** Hardcoded Standard-WinUSB-GUID (`dee824ef-729b-4a0e-9c14-b7117d33a817`). Die Kraken 2023 meldet per MS-OS-Descriptor aber einen Custom-GUID: `{300e300d-7EE7-1125-0724-101503010819}`. SetupDiGetClassDevs mit dem Standard-GUID findet MI_00 nicht.

**Bug B:** `list_usb_devices()` ohne `vid`/`pid`/`name`-Filter liefert leere Liste — else-Zweig ignoriert alles. liquidctl's `_find_winusb_device` ruft aber genau ohne Filter auf.

Fix: Zwei-Zeilen-Monkeypatch. Details in `docs/sprint-1/WINUSBCDC-PATCH.md`. Gehört in `src/kraken_monitor/kraken.py` beim Modul-Import.

### 4. FW2-Push-Eigenheiten

- `_send_2023_data_fw2` schickt das Bild zweimal hintereinander (Framebuffer-Swap-Trick, im Code kommentiert "sending it twice is only required once after initialization").
- Kein expliziter `_switch_bucket` im FW2-Pfad — das macht das Doppel-Senden. Wenn man nur einmal pusht, springt Firmware nach kurzer Zeit zurück auf Default-Liquid-Temp-Anzeige.
- FW1-Pfad (`_send_data` mit `_prepare_bucket`, `_setup_bucket`, `_switch_bucket`) funktioniert auf FW 2.0.0 **nicht** — Bucket-Commands werden nicht beantwortet, `_read_until_first_match` wirft AssertionError "missing messages".

### 5. End-to-End funktioniert

Manuelles Setup das funktioniert hat:

```python
# 1. Patch winusbcdc
from ctypes import c_byte
from winusbcdc.winusbclasses import GUID
from winusbcdc.winusbpy import WinUsbPy
ba = c_byte * 8
WinUsbPy.usb_winusb_guid = GUID(0x300e300d, 0x7EE7, 0x1125,
                                ba(0x07,0x24,0x10,0x15,0x03,0x01,0x08,0x19))
_orig = WinUsbPy.list_usb_devices
def _patched(cls, **kw):
    if kw.get('vid') is None:
        kw['vid'], kw['pid'] = 0x1e71, 0x300e
    return _orig(**kw)
WinUsbPy.list_usb_devices = classmethod(_patched)

# 2. liquidctl nutzen
from liquidctl.driver import find_liquidctl_devices
t = next(d for d in find_liquidctl_devices() if 'kraken' in d.description.lower())
t.lcd_resolution = (240, 240)  # wichtig!
t.connect()
for _ in t.initialize(): pass
t.set_screen('lcd', 'static', 'frames/test.png')
t.disconnect()
```

`frames/test.png` wurde korrekt am LCD angezeigt.

## Offene Punkte für Sprint 1

- [ ] `_patch_winusbcdc()` in `src/kraken_monitor/kraken.py` implementieren (wird beim Modul-Import aufgerufen)
- [ ] `lcd_resolution = (240, 240)` im KrakenDevice-Wrapper hart setzen (override, nicht von liquidctl übernehmen — liquidctl hat's bei 0x300E zwar schon auf (240,240), aber explizit setzen macht's robust gegen spätere Upstream-Änderungen)
- [ ] `docs/sprint-1/ZADIG-SETUP.md` + `WINUSBCDC-PATCH.md` im Setup-Story verlinken
- [ ] Sprint-1-Story um Dokumentations-Quellen ergänzen: Treiber-Recovery-Prozedur (Fall 1-3 in ZADIG-SETUP.md)

## Entscheidungen

- **Keine Zadig-Abhängigkeit mehr.** Die frühere Annahme "libusb-win32 auf Interface 1" war falsch für 2023er-Kraken. Installation soll komplett ohne Zadig auskommen.
- **Monkeypatch statt Fork.** winusbcdc hat zwei Bugs, aber ein Fork/PR-Weg ist disproportional zum Aufwand. Patch ist 8 Zeilen und gut dokumentiert.
- **`static`-Mode bleibt Single-Source-of-Truth.** FW1-Bucket-Pfad auf FW 2.0.0 nicht nutzbar, GIF nicht unterstützt (Issue #631) — `static` mit Doppel-Push ist der einzige verlässliche Weg.

## Offene Fragen / Nice-to-have

- Was triggert CAM anders, sodass CAMs "Liquid 42"-Anzeige stabil bleibt ohne Doppel-Push? Reverse-Engineering via USB-Capture wäre interessant aber nicht sprint-blockierend.
- Ob dynamische Frames (Poll-Loop alle 10s) den "zurück-zu-Liquid-nach-N-Sek"-Zustand überhaupt erreichen, oder ob der reguläre Push jede 10s das Problem überschreibt — muss in Sprint 2 beobachtet werden.

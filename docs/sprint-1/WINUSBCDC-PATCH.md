# winusbcdc Runtime-Patch für Kraken 2023

liquidctl 1.16 nutzt für den LCD-Bulk-Transfer die Library `winusbcdc`. Zwei Probleme in der Kombination verhindern, dass `bulk_device` erfolgreich initialisiert wird — **ohne Patch bekommt man `AttributeError: 'NoneType' object has no attribute 'write'`** beim ersten `set_screen`-Aufruf.

## Problem 1: Falscher WinUSB-Interface-GUID

`winusbcdc.WinUsbPy` hat den Standard-WinUSB-Interface-GUID hardcoded:

```python
usb_winusb_guid = GUID(0xdee824ef, 0x729b, 0x4a0e, byte_array(0x9c, ..., 0x17))
```

Die Kraken 2023 meldet per MS-OS-Descriptor einen **Custom-GUID**:

```
{300e300d-7EE7-1125-0724-101503010819}
```

Der Custom-GUID wird bei der Installation des Microsoft-Standard-`winusb.inf` (via `MS_COMP_WINUSB`) in die Registry geschrieben:
`HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_1E71&PID_300E&MI_00\<instanz>\Device Parameters\DeviceInterfaceGUIDS`

`SetupDiGetClassDevs` mit dem Standard-GUID findet MI_00 damit nicht. Muss auf den Custom-GUID gepatched werden.

## Problem 2: `list_usb_devices()` ohne Filter liefert leere Liste

In `winusbcdc/winusbpy.py` filtert die Enumerations-Schleife so:

```python
if vid is not None and pid is not None:
    if is_device(name, vid, pid, path):
        device_paths.append(...)
else:
    if name is not None and uname == name:
        device_paths.append(...)
```

Wird `list_usb_devices(deviceinterface=True, present=True, findparent=True)` **ohne** `vid`/`pid`/`name` aufgerufen — so wie `liquidctl.driver.kraken3._find_winusb_device` es tut —, wird **nie** etwas zur Ergebnisliste hinzugefügt. Der else-Zweig ignoriert alles ausser gesetztem `name`.

## Fix (Monkeypatch zur Laufzeit)

Vor dem `find_liquidctl_devices()`- oder `KrakenZ3(...)`-Aufruf:

```python
from ctypes import c_byte
from winusbcdc.winusbclasses import GUID
from winusbcdc.winusbpy import WinUsbPy

_byte_array = c_byte * 8

# 1. Custom-GUID für Kraken 2023 (aus MS-OS-Descriptor)
WinUsbPy.usb_winusb_guid = GUID(
    0x300e300d, 0x7EE7, 0x1125,
    _byte_array(0x07, 0x24, 0x10, 0x15, 0x03, 0x01, 0x08, 0x19),
)

# 2. Wrapper: setze vid/pid default, damit list_usb_devices() ohne Filter Ergebnisse liefert
_orig_list = WinUsbPy.list_usb_devices
def _list_with_default_filter(cls, **kwargs):
    if kwargs.get('vid') is None:
        kwargs['vid'] = 0x1E71
        kwargs['pid'] = 0x300E
    return _orig_list(**kwargs)
WinUsbPy.list_usb_devices = classmethod(_list_with_default_filter)
```

Gehört in `src/kraken_monitor/kraken.py` als `_patch_winusbcdc()` und wird einmalig beim Modul-Import ausgeführt.

## Verifikation

```python
import kraken_monitor.kraken  # triggert Patch
from liquidctl.driver import find_liquidctl_devices

for d in find_liquidctl_devices():
    if 'kraken' in d.description.lower():
        d.lcd_resolution = (240, 240)  # Framebuffer-Auflösung, siehe CLAUDE.md
        d.connect()
        list(d.initialize())
        d.set_screen('lcd', 'static', 'frames/test.png')
        d.disconnect()
        break
```

Muss ohne `AttributeError` durchlaufen und das Bild anzeigen.

## Session-Notiz

Beide Bugs wurden in der Debug-Session 2026-04-19 identifiziert (siehe `docs/progress/progress-kraken-treiber-2026-04-19.md`). Upstream-Fix wurde nicht eingereicht — der Monkeypatch ist stabil und das Paket versioned im venv.

Falls eine zukünftige `winusbcdc`-Version den List-Bug fixt: Check ob `WinUsbPy.list_usb_devices()` ohne Filter nicht-leere Liste liefert; wenn ja, Wrapper entfernen. Der GUID-Patch bleibt nötig, solange die Library keinen per-Instance-GUID-Override bekommt.

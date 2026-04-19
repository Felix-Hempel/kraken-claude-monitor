"""Kraken-Device-Wrapper um liquidctl.

Kapselt Device-Discovery + Connect + set_screen-Calls. Context-Manager-fähig.
"""

from __future__ import annotations

import logging
from ctypes import c_byte
from pathlib import Path
from types import TracebackType
from typing import Self

from liquidctl import find_liquidctl_devices

log = logging.getLogger(__name__)

# Kraken 2023 (PID 1E71:300E) meldet per MS-OS-Descriptor einen Custom-WinUSB-
# Interface-GUID. winusbcdc sucht aber hardcoded den Standard-GUID dee824ef-… —
# deshalb findet es MI_00 sonst nicht. Zusätzlich: list_usb_devices() ohne
# vid/pid-Filter liefert leere Liste, aber liquidctl.kraken3._find_winusb_device
# ruft genau so auf. Siehe docs/sprint-1/WINUSBCDC-PATCH.md.
_KRAKEN_VID = 0x1E71
_KRAKEN_PID = 0x300E
_KRAKEN_WINUSB_GUID = (
    0x300E300D,
    0x7EE7,
    0x1125,
    (0x07, 0x24, 0x10, 0x15, 0x03, 0x01, 0x08, 0x19),
)

# Framebuffer-Auflösung: Panel ist physisch 640×640, Firmware erwartet aber
# 240×240 und skaliert intern. Bei 640er-Frames werden Muster verzerrt (bei
# uniformen Farben fällt's nicht auf). liquidctl hat das für 0x300E korrekt,
# wir setzen es explizit gegen künftige Upstream-Drift.
_LCD_RESOLUTION = (240, 240)


def _patch_winusbcdc() -> None:
    """Monkeypatch für winusbcdc: korrekter GUID + vid/pid-Default."""
    from winusbcdc.winusbclasses import GUID
    from winusbcdc.winusbpy import WinUsbPy

    data1, data2, data3, data4 = _KRAKEN_WINUSB_GUID
    WinUsbPy.usb_winusb_guid = GUID(data1, data2, data3, (c_byte * 8)(*data4))

    _orig = WinUsbPy.list_usb_devices

    def _list_with_default_filter(cls, **kwargs):
        if kwargs.get("vid") is None:
            kwargs["vid"] = _KRAKEN_VID
            kwargs["pid"] = _KRAKEN_PID
        return _orig(**kwargs)

    WinUsbPy.list_usb_devices = classmethod(_list_with_default_filter)


_patch_winusbcdc()


class KrakenError(RuntimeError):
    """Basis-Fehler für Kraken-Operationen."""


class KrakenNotFoundError(KrakenError):
    """Kein Kraken-Device gefunden — meist Treiber-Layout oder USB-Problem."""


class KrakenDevice:
    """Wrapper um liquidctl-Device mit LCD-Fokus.

    Beispiel:
        with KrakenDevice() as kraken:
            kraken.push_frame(Path("frames/live.gif"))
            kraken.set_brightness(80)
    """

    def __init__(self, match: str = "kraken") -> None:
        self._match = match
        self._device = None  # type: ignore[assignment]
        self._connected = False

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def connect(self) -> None:
        """Findet, verbindet und initialisiert das Kraken-Device.

        Raises:
            KrakenNotFoundError: wenn kein passendes Device gefunden wurde.
        """
        if self._connected:
            return

        candidates = list(find_liquidctl_devices(match=self._match))
        if not candidates:
            raise KrakenNotFoundError(
                "Kein NZXT Kraken gefunden. Pruefe:\n"
                "  1. MI_01 hat HidUsb-Treiber (nicht libusb0)?\n"
                "  2. MI_00 hat WinUSB-Treiber?\n"
                "  3. NZXT CAM beendet (blockiert HID-Handle)?\n"
                "  4. USB-Kabel korrekt?\n"
                "Siehe docs/sprint-1/ZADIG-SETUP.md (Recovery-Faelle)"
            )
        if len(candidates) > 1:
            log.warning(
                "Mehrere Kraken-Devices gefunden (%d). Verwende erstes: %s",
                len(candidates),
                candidates[0].description,
            )

        device = candidates[0]
        if hasattr(device, "lcd_resolution"):
            device.lcd_resolution = _LCD_RESOLUTION

        device.connect()
        try:
            device.initialize()
        except Exception:
            device.disconnect()
            raise

        self._device = device
        self._connected = True
        log.info("Kraken verbunden: %s @ %dx%d", device.description, *_LCD_RESOLUTION)

    def close(self) -> None:
        if self._connected and self._device is not None:
            try:
                self._device.disconnect()
            except Exception as e:
                log.warning("disconnect fehlgeschlagen: %s", e)
            finally:
                self._connected = False
                self._device = None

    def _ensure_connected(self) -> None:
        if not self._connected or self._device is None:
            raise KrakenError("Device nicht verbunden — connect() oder Context-Manager nutzen.")

    def push_frame(self, frame_path: Path) -> None:
        """Pusht ein Bild aufs LCD.

        Format-Detection:
          - .png / .jpg / .jpeg / .bmp → `static`-Mode (1 Frame)
          - .gif                        → `gif`-Mode (animiert)

        HINWEIS: Auf Kraken 2023 FW 2.X.Y ist `gif`-Mode nicht unterstuetzt
        (liquidctl Issue #631). Dort nur `static` verwenden. Fuer unsere
        Poll-basierte Live-Anzeige reicht `static` sowieso — pro Poll ein PNG.
        """
        self._ensure_connected()
        path = Path(frame_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Frame nicht gefunden: {path}")

        suffix = path.suffix.lower()
        static_exts = {".png", ".jpg", ".jpeg", ".bmp"}
        if suffix in static_exts:
            mode = "static"
        elif suffix == ".gif":
            mode = "gif"
        else:
            raise ValueError(f"Unsupported frame format: {suffix}")

        assert self._device is not None
        # Clear HID-Response-Queue: nach einem static-Push bleiben Reports
        # übrig und der nächste `set_screen(...)` ruft intern `_read_until`
        # für [0x31, 0x01] und hängt sich fest. `clear_enqueued_reports()`
        # ist liquidctls eigener Helper in der Device-Layer.
        underlying = getattr(self._device, "device", None)
        if underlying is not None and hasattr(underlying, "clear_enqueued_reports"):
            underlying.clear_enqueued_reports()
        self._device.set_screen("lcd", mode, str(path))
        log.debug("Frame gepusht (%s): %s", mode, path.name)

    def set_brightness(self, pct: int) -> None:
        self._ensure_connected()
        if not 0 <= pct <= 100:
            raise ValueError(f"brightness muss 0-100 sein, ist {pct}")
        assert self._device is not None
        self._device.set_screen("lcd", "brightness", str(pct))
        log.debug("Brightness: %d%%", pct)

    def get_status(self) -> list[tuple[str, object, str]]:
        """Liefert Status-Tuples (key, value, unit) fuer Logs/Debug."""
        self._ensure_connected()
        assert self._device is not None
        return self._device.get_status()

    @property
    def description(self) -> str:
        if self._device is None:
            return "<disconnected>"
        return str(self._device.description)

"""Post-Install-Helper: fix libusb-DLL in libusb_package auf Windows.

Grund: libusb-package 1.0.26.1 (cp314-wheel) bundled die libusb-1.0.dll nicht mit.
Das alternative `libusb`-Package (karpierz/libusb) bringt die DLL mit — wir kopieren
sie ins libusb_package-Verzeichnis, damit PyUSB sie findet.

Usage:
    python scripts/post_install.py

Nach `pip install -e .[dev]` einmal ausfuehren.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def find_site_packages() -> Path:
    import site

    # Nimm das venv-site-packages
    for p in site.getsitepackages():
        path = Path(p)
        if path.name == "site-packages" and (path / "libusb_package").exists():
            return path
    # Fallback: aus sys.path
    for p in sys.path:
        if p.endswith("site-packages") and (Path(p) / "libusb_package").exists():
            return Path(p)
    raise RuntimeError("site-packages mit libusb_package nicht gefunden")


def ensure_libusb_installed() -> None:
    """Stellt sicher dass `libusb` package installiert ist (fuer DLL-Quelle)."""
    try:
        import libusb  # noqa: F401
    except ImportError:
        print("Installiere 'libusb' package (fuer DLL-Source) ...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "libusb"],
            check=True,
        )


def main() -> int:
    if platform.system() != "Windows":
        print("[skip] Nicht Windows — kein DLL-Fix noetig.")
        return 0

    ensure_libusb_installed()

    site_packages = find_site_packages()
    libusb_package_dir = site_packages / "libusb_package"
    libusb_dll = libusb_package_dir / "libusb-1.0.dll"

    if libusb_dll.exists():
        print(f"[OK] libusb-1.0.dll bereits vorhanden: {libusb_dll}")
        return 0

    # DLL aus libusb-package kopieren
    arch = "x86_64" if platform.machine().endswith("64") else "x86"
    src_dll = site_packages / "libusb" / "_platform" / "windows" / arch / "libusb-1.0.dll"
    if not src_dll.exists():
        print(f"[FAIL] Source-DLL nicht gefunden: {src_dll}")
        return 1

    shutil.copy2(src_dll, libusb_dll)
    size_kb = libusb_dll.stat().st_size / 1024
    print(f"[OK] libusb-1.0.dll kopiert: {libusb_dll} ({size_kb:.1f} KB)")

    # Smoke-Test
    try:
        import libusb_package

        backend = libusb_package.get_libusb1_backend()
        if backend is None:
            print("[WARN] Backend lädt trotz DLL nicht — weitere Diagnose noetig.")
            return 2
        print(f"[OK] libusb-Backend laedt: {backend}")
    except Exception as e:
        print(f"[WARN] Smoke-Test fehlgeschlagen: {e}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

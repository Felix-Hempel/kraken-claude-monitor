# CAM-Coexistenz — LCD-Screen in NZXT CAM deaktivieren

> **Warum?** Wenn CAM einen LCD-Screen-Modus aktiv hat, überschreibt es unsere Frames — typischerweise alle paar Sekunden. Das Tool würde dann flackern oder nur kurz sichtbar sein.
>
> **Was bleibt aktiv?** Pumpen-Steuerung, RGB, Lüfter-Kurven, Sensoren. Nur das LCD-Display wird von CAM freigegeben.

## Schritte (einmalig)

1. NZXT CAM öffnen
2. In der Sidebar auf den Kraken klicken (Kachel mit Pumpe)
3. Reiter **"LCD"** öffnen
4. Mode auf **"Off"** / **"Blank"** stellen (NICHT "CPU Temp", NICHT "GIF", NICHT "Logo")
5. "Apply" / "Save" klicken
6. CAM minimieren (nicht schließen — Pumpensteuerung läuft weiter)

## Verifizieren

Nach dem Umschalten sollte das Kraken-LCD schwarz sein (kein CAM-Inhalt). Erst dann kann `kraken-claude-monitor` das Display ohne Störung bespielen.

Falls das LCD weiterhin CAM-Inhalt zeigt:
- CAM komplett neu starten (Task-Manager → "CAM.exe" beenden, CAM erneut starten)
- Erneut auf LCD-Reiter schauen, Off-Status prüfen

## Nach Reboot

CAM startet automatisch mit Windows, die LCD-Einstellung bleibt erhalten. Falls nicht: Schritte 1-5 wiederholen.

## Fallback: CAM komplett beenden

Wenn CAM partout das LCD bespielt, kann man CAM während des Monitor-Runs komplett beenden:
```powershell
taskkill /IM "CAM.exe" /F
```
Dann übernimmt allerdings Windows die Pumpen-Standardwerte — nicht optimal. Besser den "Off"-Mode verwenden.

## Warum kann das Tool das nicht automatisieren?

CAM hat keine CLI, keine REST-API, keine dokumentierten IPC-Endpoints. Der LCD-Screen-Mode liegt in der CAM-Datenbank (SQLite), aber das Schreiben während CAM läuft ist nicht unterstützt und würde beim nächsten CAM-Refresh überschrieben. Einmal-Klick in der GUI ist der saubere Weg.

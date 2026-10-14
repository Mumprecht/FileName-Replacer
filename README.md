# FileName-Replacer

Grafische Windows-Anwendung zum Ersetzen einzelner Zeichen in Datei- und Ordnernamen.

## Funktionen

- Standard: Leerzeichen durch Unterstrich ersetzen
- Dateien, Ordner oder beides auswählen
- Unterordner optional einbeziehen
- Vorschau und Konfliktprüfung vor Umbenennung
- Letzte Umbenennungsaktion rückgängig machen (innerhalb derselben Sitzung)
- Testdaten erstellen und sicher löschen
- Hilfe → Über FileName-Replacer: Version, Copyright, MIT-Lizenz

## Starten in PyCharm

`main.py` mit Python 3.14 starten. Für die GUI sind keine zusätzlichen Python-Pakete nötig.

## EXE erstellen

In PowerShell im Projektordner ausführen:

```powershell
.\tools\build_exe.ps1
```

Das Skript installiert PyInstaller in `.venv` und erzeugt `dist\FileName-Replacer.exe`.

## Lizenz

MIT License. Copyright (c) 2026 Urs Mumprecht. Siehe [LICENSE](LICENSE).

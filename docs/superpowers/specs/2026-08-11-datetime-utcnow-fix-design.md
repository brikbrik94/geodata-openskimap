# Design: `datetime.utcnow()` DeprecationWarning fixen

## Problem

`scripts/generate_manifest.py:90` erzeugt `generated_at` im Manifest mit
`datetime.utcnow()` — unter Python 3.12+ als deprecated markiert (siehe
`docs/TODO.md`, Eintrag "`datetime.utcnow()` DeprecationWarning in
generate_manifest.py").

## Lösung

`timezone.utc` zusätzlich aus `datetime` importieren, Zeile 90 auf
`datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` umstellen.
`timezone.utc` existiert seit Python 3.2 — kompatibler als das neuere
`datetime.UTC`-Alias (erst ab 3.11). Der Format-String bleibt unverändert;
das `Z` darin ist ein literales Zeichen, kein Format-Direktiv, daher ändert
sich die Ausgabe nicht.

## Scope

Nur `scripts/generate_manifest.py` (Import-Zeile + Zeile 90). Kein
Verhaltensunterschied, keine weiteren Dateien betroffen.

## Verifikation

Manueller Lauf von `python3 scripts/generate_manifest.py` gegen ein
vorhandenes `work/`-Verzeichnis: keine DeprecationWarning mehr, `generated_at`
im erzeugten `dist/manifest.json` weiterhin im selben Format.

# Design: Versionierung & CHANGELOG.md einführen

## Problem

`docs/TODO.md` → letzter offener Punkt: "Versionierung & CHANGELOG.md
einführen (oe5ith-coding-rules §4)". `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md`
§4 verlangt eine zentrale Versionskonstante als Single Source of Truth
sowie ein nach Keep-a-Changelog strukturiertes `CHANGELOG.md` mit
datierten `[Unreleased]`-Journal-Blöcken. Beides existiert in diesem Repo
aktuell nicht.

Bewusst zurückgestellt (Entscheidung 2026-08-11) bis alle anderen
TODO-Punkte abgearbeitet sind — jetzt der Fall (Sub-Projekte D, A, C, B
alle fertig und committet).

## Untersuchung

Das Repo hat keine package.json/pyproject.toml/`__init__.py` o. ä. — es
ist eine reine Bash+Python-Build-Pipeline, kein zu versionierendes Package
im klassischen Sinn. `dist/manifest.json`s `"version": "1.0"`-Feld
(`scripts/generate_manifest.py:88`) ist ein **anderes** Versions-Konzept:
die Schema-Version des Manifest-Formats selbst, vorgegeben durch
`geodata-plugin-standard` §4, nicht die Release-Version dieses Repos —
beide dürfen nicht verwechselt/vereinheitlicht werden.

Nebenfund: `scripts/generate_manifest.py:21,36` hat eine hartkodierte,
mittlerweile falsche Versionsangabe für den Plugin-*Standard*
("Migriert auf v1.2 Standard" / "Generating Manifest according to
Plugin-Standard (v1.2)..."), aus der Zeit vor der Submodul-Extraktion.
Die tatsächliche Standard-Version läuft seit der Restrukturierung über den
`geodata-plugin-standard`-Submodul-Git-Tag (aktuell `v1.0.0`) — die
hartkodierte Zeile ist verwaist. Wird in diesem Zug mit korrigiert (siehe
Entscheidung 3).

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-11)

1. **Versionskonstante: `VERSION`-Datei am Repo-Root**, enthält nur die
   Versionsnummer (`1.0.0`, kein Präfix, keine mehrdeutige
   Zeilenumbruch-Formatierung) — sprachunabhängig aus Bash (`cat VERSION`)
   und Python (`open("VERSION").read().strip()`) gleichermaßen trivial
   lesbar, kein Framework-Bezug nötig.
2. **Startversion `1.0.0`**, nicht `0.1.0`. Begründung: passt zur
   Konvention der beiden bereits eingebundenen Submodule
   (`oe5ith-coding-rules`, `geodata-plugin-standard`), die beide bei ihrer
   initialen Extraktion mit `v1.0.0` starteten. Die
   `manifest.json`/`layer-list.json`-Schnittstelle wird bereits produktiv
   vom externen Deployment-System konsumiert — kein frühes
   0.x-Entwicklungsstadium mehr, auch wenn dies der erste *versionierte*
   Release-Schnitt ist.
3. **Stale `v1.2`-Referenz in `generate_manifest.py` wird im selben Zug
   entfernt** (Zeilen 21 und 36) — generischer Text ohne Versionsnummer,
   da die tatsächliche Standard-Version über den Submodul-Tag läuft, nicht
   hier dupliziert werden soll.
4. **`CHANGELOG.md` bekommt keinen rückwirkenden Eintrag pro historischem
   Commit** (bereits am 11.08. entschieden) — der erste Eintrag markiert
   nur den Startpunkt (`### Added` / "Initiale versionierte
   Veröffentlichung"), keine Rekonstruktion der bisherigen Git-Historie
   als Changelog-Einträge.
5. **Ab diesem Release**: jede künftige Änderung bekommt einen datierten
   `## [Unreleased] - YYYY-MM-DD HH:mm`-Journal-Block (Keep-a-Changelog-
   Kategorien: Added/Changed/Fixed/Removed/…), der beim nächsten Release
   zu `## [X.Y.Z] - <Datum>` konsolidiert wird — Standard-Mechanik aus
   `oe5ith-coding-rules` §4, hier nur die Erstanlage der Datei.
6. **Release-Commit bündelt alles**: `VERSION` (neu) + `CHANGELOG.md`
   (neu) + der `generate_manifest.py`-Fix landen in einem Commit, danach
   ein annotierter Git-Tag `v1.0.0` auf genau diesem Commit — passt zur
   Konvention der beiden Submodule und zur Release-Checkliste in
   `oe5ith-coding-rules` §4 ("Versions-Bump im Release-Commit selbst").

**Nicht Teil dieses Designs:** Push zu `origin` (eigene, im Session-Verlauf
mehrfach bewusst zurückgestellte Entscheidung), Deploy (externe
Infrastruktur, nicht Teil dieses Repos).

## Betroffene Dateien

- `VERSION` — neu, Inhalt: `1.0.0`
- `CHANGELOG.md` — neu, Keep-a-Changelog-Format, ein Eintrag `[1.0.0] - 2026-08-11`
- `scripts/generate_manifest.py:21,36` — hartkodierte `v1.2`-Referenz entfernt

## Verifikation

- `cat VERSION` liefert exakt `1.0.0` (keine trailing Whitespace-Überraschungen
  prüfen: `xxd VERSION | tail -3` oder `wc -c VERSION`).
- `python3 -c "import json; json.load(open('...'))"`-artige Syntaxprüfung
  entfällt (kein JSON) — stattdessen: `CHANGELOG.md` ist gültiges Markdown
  (visuelle Prüfung reicht, keine Tooling-Pflicht im Repo für Markdown-Lint).
- `python3 scripts/generate_manifest.py` läuft weiterhin fehlerfrei, Log-Zeile
  enthält keine `v1.2`-Referenz mehr.
- `git tag -l 'v1.0.0'` zeigt den neu gesetzten, annotierten Tag auf dem
  Release-Commit.

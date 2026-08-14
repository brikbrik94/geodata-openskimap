# TODO

Offene Punkte für kommende Iterationen des Styles/der Konvertierung. Nicht
umgesetzt, nur dokumentiert.

## Referenz: echtes OpenSkiMap-Stylesheet

Alle Punkte unten sind gegen das tatsächliche, produktive Stylesheet von
openskimap.org verifiziert (nicht geraten):

- Homepage lädt `https://openskimap.org/assets/index-*.js`, darin referenziert:
  `https://tiles.openskimap.org/styles/terrain_v2.json` und `.../satellite_v2.json`.
- Lokal gesichert unter `/tmp/openskimap_terrain_style.json` (Session-Snapshot,
  nicht Teil des Repos — bei Bedarf per curl neu laden, URL s.o.).
- `line-color: ["get", "color"]` bei den meisten Lauf-/Lift-Layern bedeutet:
  OpenSkiMap berechnet die Farbe serverseitig (in ihrer `openskidata`-Pipeline)
  und liefert sie als fertiges Feature-Property aus — nicht per Client-seitiger
  match/case-Expression wie bei uns. Die eigentlichen Farbwerte pro
  Schwierigkeit/Status dürften trotzdem mit unserer Task-5-Tabelle
  übereinstimmen (dort ebenfalls aus `openskidata-format` übernommen); die
  Lücken unten sind strukturell (welche Layer/Kategorien es gibt), nicht bei
  den Farbwerten selbst.

## Versionierung & CHANGELOG.md einführen (oe5ith-coding-rules §4)

`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4 verlangt eine zentrale
Versionskonstante als Single Source of Truth sowie ein nach Keep-a-Changelog
strukturiertes `CHANGELOG.md` mit datierten `[Unreleased]`-Journal-Blöcken.
Beides existiert in diesem Repo aktuell nicht.

Bewusst zurückgestellt (Entscheidung 2026-08-11): `docs/TODO.md` ist jetzt
leer (alle Punkte erledigt, siehe `docs/TODO_ARCHIVE.md`) — die erste
Version wird als Nächstes geschnitten (Versionskonstante festlegen,
`CHANGELOG.md` mit diesem Stand als erstem Eintrag anlegen).

## `extract_layer_metadata()` in `layer_metadata_extractor.py` ist toter Code

`generate_layer_list.py` reimplementiert die Gruppen-Metadaten-Logik lokal
(`_group_metadata`), weil openskimap-Gruppen mehrere `source-layer`s
umspannen können — `extract_layer_metadata()` (Single-`source-layer`-Variante,
für den `geodata-overlays`-Fall gedacht) wird nirgends in diesem Repo
aufgerufen. Seit dem v1.1-Feld-Update (`width`/`dasharray`/`outline_*`/`icon`,
siehe `docs/superpowers/specs/2026-08-12-layer-list-legend-scale-v1.1-design.md`)
ist sie zusätzlich veraltet: sie kennt diese Felder nicht. Entscheiden und
umsetzen: entweder entfernen, oder auf den aktuellen Stand bringen, falls
sie doch als Referenz/Portierungs-Vorlage für andere `geodata-*`-Repos
gebraucht wird (`scripts/layer_metadata_extractor.py:450-504`).

## `scripts/ci/__pycache__/*.pyc` ist versehentlich getrackt

`scripts/ci/__pycache__/utils.cpython-313.pyc` ist im Repo eingecheckt
(sollte gitignored sein — kompilierte Python-Bytecode-Caches gehören nie ins
Git). Erzeugt bei jedem Testlauf lokale, unstaged Änderungen (`git status`
zeigt die Datei als modifiziert, sobald `python3 -m unittest` gelaufen ist),
ohne dass echte Arbeit dahintersteckt. Entscheiden und umsetzen: Datei aus
dem Git-Tracking entfernen (`git rm --cached`) und `__pycache__/` zum
`.gitignore` hinzufügen.

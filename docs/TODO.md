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

## Alle `BOOLEAN`-Spalten in `openskidata.gpkg` sind immer `0`/`false`

Verifiziert über `runs_linestring`, `runs_multipolygon`, `lifts_linestring`, `spots_point`:
`gladed`, `snowmaking`, `snowfarming`, `patrolled`, `lit`, `oneway`, `detachable`, `bubble`,
`heating`, `entry`, `exit` haben tabellenübergreifend ausschließlich den Wert `0` — kein
einziger `true`-Wert irgendwo, weltweit, auch nicht in älteren lokalen Snapshots
(`data/src/openskidata.1.gpkg`). Unabhängig bestätigt: `way/30066149` ("Silleralmabfahrt") hat
auf OSM `oneway=yes`, unser Export zeigt `0` — kein Zufall/Rand-Fall, sondern ein
Export-/Konvertierungsfehler bei OpenSkiMap selbst (nicht durch unseren AT-Filter verursacht,
siehe `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`).

Konkrete Konsequenz: `ski-runs-downhill-gladed` (Waldabfahrten-Variante) und
`ski-runs-downhill-snowmaking`/`ski-runs-nordic-snowmaking` (v2.1.0-Migration, `e5f227f`)
konnten mit den heruntergeladenen Daten **nie** matchen — nicht weil es keine
Waldabfahrten/Beschneiung gibt, sondern weil die zugrundeliegenden Datenfelder kaputt
exportiert werden. Alle drei Style-Layer wurden deshalb beim Pisten-Restyling (2026-08-16)
ganz aus dem Style entfernt statt als permanent leere Layer stehen zu bleiben. Nicht selbst
fixbar (Upstream-Problem bei OpenSkiMap) — bei Gelegenheit dort melden oder regelmäßig neu
prüfen, ob ein zukünftiger Datenexport das
Feld korrekt befüllt.

## Übungswiesen (`ski-runs-playground`): Schraffur-Fläche + Icon

Aktuell (2026-08-16 Follow-up, Pisten-Restyling) rendert `ski-runs-playground-fill` als
flache Füllung in Novice-Grün (`hsl(125, 100%, 33%)`, an die Pisten-Schwierigkeitsfarbe
angepasst — bestätigt nach visueller Prüfung). Zwei Verbesserungen bewusst zurückgestellt,
da beide ein neues Sprite-Asset brauchen (aktuell existieren nur Lift-Icons in
`assets/sprites/openskimap/sprite.json`, kein Pattern/Fläche-Icon):

- **Schraffur statt Flächenfüllung**: `fill-pattern` statt `fill-color` auf
  `ski-runs-playground-fill` — bräuchte ein neues Schraffur-Pattern-Bild im Sprite-Sheet.
- **Icon**: zusätzliches Symbol (z. B. Anfänger-/Übungswiesen-Icon) auf den
  `ski-runs-playground`-Flächen/Punkten — bräuchte ein passendes neues Icon im Sprite-Sheet.

## `scripts/ci/__pycache__/*.pyc` ist versehentlich getrackt

`scripts/ci/__pycache__/utils.cpython-313.pyc` ist im Repo eingecheckt
(sollte gitignored sein — kompilierte Python-Bytecode-Caches gehören nie ins
Git). Erzeugt bei jedem Testlauf lokale, unstaged Änderungen (`git status`
zeigt die Datei als modifiziert, sobald `python3 -m unittest` gelaufen ist),
ohne dass echte Arbeit dahintersteckt. Entscheiden und umsetzen: Datei aus
dem Git-Tracking entfernen (`git rm --cached`) und `__pycache__/` zum
`.gitignore` hinzufügen.

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

## `ski-runs-downhill`'s `variants[]` ist nicht §5.3-konform (Part-Duplikation über Einträge)

`GEODATA_PLUGIN_STANDARD.md` v2.1.0 §5.3 verlangt, dass ein Style-Layer
entweder in `render[]` oder in genau einem `variants[]`-Eintrag landet, nie
in beiden und nie in mehreren. `ski-runs-downhill-gladed` und
`ski-runs-downhill-ungroomed` (`scripts/generate_layer_list.py`,
`GROUP_VARIANTS["ski-runs-downhill"]`) verletzen das: beide erscheinen
jeweils in ihrem eigenen Einzel-Eintrag der `grooming-terrain`-Achse UND im
kombinierten Eintrag "Waldabfahrt, nicht präpariert" — also je zweimal statt
einmal. Bewusst in Kauf genommen bei der v2.1.0-Migration (siehe
`docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`,
Entscheidung 3 und Abschnitt "Verworfene Alternative"), um keine zweite
Breaking-Change-Formänderung für `website-v3` so kurz nach der `ski-lifts`-
Retaxonomie zu erzwingen.

Lösung (dort bereits als technisch machbar geprüft): orthogonale Zerlegung
in eine `"terrain"`-Achse (`"Waldabfahrt"`, aus `-gladed`) und eine separate
`"grooming"`-Achse (`"Präpariert"`/`"Nicht präpariert"`, aus
`-line`/`-ungroomed`) statt der aktuellen 4-Kombi-Form — macht den
kombinierten Eintrag überflüssig und jeden Style-Layer eindeutig einem
Eintrag zuordenbar. Siehe Design-Doc oben für die volle Analyse.

## Alle `BOOLEAN`-Spalten in `openskidata.gpkg` sind immer `0`/`false`

Verifiziert über `runs_linestring`, `runs_multipolygon`, `lifts_linestring`, `spots_point`:
`gladed`, `snowmaking`, `snowfarming`, `patrolled`, `lit`, `oneway`, `detachable`, `bubble`,
`heating`, `entry`, `exit` haben tabellenübergreifend ausschließlich den Wert `0` — kein
einziger `true`-Wert irgendwo, weltweit, auch nicht in älteren lokalen Snapshots
(`data/src/openskidata.1.gpkg`). Unabhängig bestätigt: `way/30066149` ("Silleralmabfahrt") hat
auf OSM `oneway=yes`, unser Export zeigt `0` — kein Zufall/Rand-Fall, sondern ein
Export-/Konvertierungsfehler bei OpenSkiMap selbst (nicht durch unseren AT-Filter verursacht,
siehe `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`).

Konkrete Konsequenz: die `ski-runs-downhill-gladed`-Variante und die `snowmaking`-Achse
(v2.1.0-Migration, `e5f227f`) können mit den aktuell heruntergeladenen Daten **nie** matchen —
nicht weil es keine Waldabfahrten/Beschneiung gibt, sondern weil das Datenfeld kaputt exportiert
wird. Nicht selbst fixbar (Upstream-Problem bei OpenSkiMap) — bei Gelegenheit dort melden oder
regelmäßig neu prüfen, ob ein zukünftiger Datenexport das Feld korrekt befüllt.

## `scripts/ci/__pycache__/*.pyc` ist versehentlich getrackt

`scripts/ci/__pycache__/utils.cpython-313.pyc` ist im Repo eingecheckt
(sollte gitignored sein — kompilierte Python-Bytecode-Caches gehören nie ins
Git). Erzeugt bei jedem Testlauf lokale, unstaged Änderungen (`git status`
zeigt die Datei als modifiziert, sobald `python3 -m unittest` gelaufen ist),
ohne dass echte Arbeit dahintersteckt. Entscheiden und umsetzen: Datei aus
dem Git-Tracking entfernen (`git rm --cached`) und `__pycache__/` zum
`.gitignore` hinzufügen.

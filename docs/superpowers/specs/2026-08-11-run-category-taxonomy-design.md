# Design: Pisten-Kategorien (downhill/nordic/skitour/other) + Nordic-Einfärbung

## Problem

`docs/TODO.md` → zwei gekoppelte Punkte:

1. "Pisten-Kategorien: downhill / nordic / skitour / other statt nur
   alpine/nordic" — das echte OpenSkiMap-Stylesheet nutzt vier Kategorien
   pro Lauf-Feature statt unseres Alpine/Nordic-Splits. Zwei konkrete
   Lücken dokumentiert: Rodelbahn (`uses=sled`) nicht gestrichelt
   (`feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`), Winterwanderweg
   (`uses=hike`) nicht erkennbar
   (`feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`).
2. "Loipen (nordic) nicht nach Schwierigkeit einfärben" — wir haben die
   komplette Alpine-Schwierigkeitsfarblogik 1:1 auf Nordic gespiegelt, das
   echte Stylesheet färbt Loipen nicht nach Schwierigkeit.

## Untersuchung

Das echte Stylesheet (`/tmp/openskimap_terrain_style.json`, Session-Snapshot)
hat für `source-layer: "runs"` u.a. folgende Layer (per `["has", "<kategorie>"]`-Filter,
serverseitig vorberechnete numerische Felder `downhill`/`nordic`/`skitour`/`other`,
zusätzlich für `line-offset` bei Mehrfachnutzung genutzt):

- **downhill**: `downhill-runs-casing`, `downhill-runs` (Basis),
  `downhill-runs-gladed` (`line-dasharray: [0.1, 4]`), `downhill-runs-ungroomed`
  (`line-dasharray: [2, 4]`), `downhill-area-runs-tappable` (Fläche,
  schwierigkeitsgefärbt via serverseitigem `color`-Feld) + gladed-/ungroomed-Varianten.
- **nordic**: `nordic-runs-casing`, `nordic-runs` (Basis, `line-color`:
  `case lit==true → hsl(63,100%,76%) sonst hsl(0,0%,100%)`, **keine**
  Schwierigkeitsfarbe), `nordic-runs-ungroomed` (`[2,4]`, gleiche
  Case-Farblogik), `nordic-area-runs-tappable` (Fläche) — **kein** Gladed-Layer.
- **skitour**: nur `skitour-runs` (`line-dasharray: [3,6]`) +
  `skitour-area-runs-tappable` — keine Casing-/Gladed-/Ungroomed-Variante.
- **other**: nur `other-runs` (`line-dasharray: [3,3]`) +
  `other-area-runs-tappable` — keine Casing-Variante.
- `snowmaking-run-area`/`-border`: eine gemeinsame, kategorie-unabhängige
  Overlay-Fläche über `snowmaking`/`snowfarming`, nicht pro Kategorie
  dupliziert (bei uns aktuell pro Kategorie eigene Layer,
  `ski-runs-alpine-snowmaking`/`-nordic-snowmaking`).

Alle vier `*-area-runs-tappable`-Layer sind **sichtbare** Flächenfüllungen
(`fill-opacity` 0.2–0.4, Farbe aus dem serverseitigen `color`-Feld) — trotz
des Namens keine unsichtbaren Klickziele. *(Korrektur einer ursprünglich
falschen Annahme während des Brainstormings — initial als "unsichtbare
Klickziele" beschrieben, beim genaueren Prüfen als sichtbare Füllung
erkannt und mit dem Nutzer neu abgestimmt, siehe Entscheidung 5.)*

Unser GeoPackage (`data/src/openskidata.gpkg`, Tabelle `runs_linestring`)
hat **kein** vorberechnetes `downhill`/`nordic`/`skitour`/`other`-Feld,
sondern ein einzelnes kommagetrenntes `uses`-Feld (z. B.
`"downhill,skitour"`, `"nordic,hike"`). Volle Taxonomie im Datensatz
(`ogrinfo -sql "SELECT uses, COUNT(*) ... GROUP BY uses"`): `downhill`,
`nordic`, `hike`, `skitour`, `sled`, `connection`, `snow_park`, `fatbike`,
`sleigh`, `ice_skate`, `playground`, in beliebigen Kombinationen. Auch
`difficulty`, `grooming`, `gladed`, `lit`, `snowmaking`, `snowfarming` sind
vorhanden — die aktuelle Style-Logik für Gladed/Ungroomed/Snowmaking/Lit
bleibt also weiterhin nutzbar, unabhängig von der Kategorie.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-11)

1. **Kein `line-offset` bei Mehrfachnutzung.** Jedes Feature bekommt genau
   eine Kategorie nach fester Priorität (Entscheidung 3), keine parallel
   versetzten Linien wie im Original. Grund: kein vorberechnetes
   Offset-Index-Feld verfügbar, selbst berechnen wäre deutlich komplexer.
   **Als Roadmap-Punkt zurückgestellt** (neue `docs/ROADMAP.md`, siehe
   Abschnitt "Roadmap" unten) — echtes neues Feature, keine Erweiterung
   von etwas Bestehendem, daher laut `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md`
   §3 kein `TODO.md`-, sondern ein `ROADMAP.md`-Eintrag.
2. **Layer-Umfang pro Kategorie asymmetrisch wie das Original**: downhill
   und nordic behalten den vollen Umfang (downhill: Fill+Casing+Basis+Gladed+Ungroomed+Snowmaking+Labels;
   nordic: Fill+Casing+Basis+Ungroomed+Snowmaking+Labels, **ohne** Gladed —
   das echte Stylesheet kennt keinen `nordic-runs-gladed`-Layer). skitour
   und other bekommen nur Fill+Basis-Linie+Labels — keine Casing-,
   Gladed-, Ungroomed- oder Snowmaking-Variante.
3. **Priorität bei der Ein-Kategorie-pro-Feature-Zuordnung**:
   `downhill > nordic > skitour > other`. Ein Feature mit z. B.
   `uses=downhill,nordic` landet in `downhill`.
4. **`other`-Bucket bekommt alle acht Nicht-{downhill,nordic,skitour}-Werte**:
   `hike`, `sled`, `connection`, `fatbike`, `ice_skate`, `playground`,
   `sleigh`, `snow_park` sowie NULL/leeres `uses`. Kein Informationsverlust
   gegenüber heute (aktuell rendert alles unmarkiert im Alpine-Katalog).
5. **Alle vier Kategorien bekommen eine Flächenfüllung** (nach Korrektur
   der ursprünglich falschen Annahme, siehe Untersuchung oben): downhill
   bleibt schwierigkeitsgefärbt (unverändert). nordic/skitour/other haben
   kein server-berechnetes `color`-Feld und keine sinnvolle
   Schwierigkeits-Datengrundlage, bekommen daher je eine **einzelne
   neutrale Flächenfarbe** (keine Match-Expression):
   - nordic: `hsl(200, 30%, 85%)` (helles Blaugrau)
   - skitour: `hsl(280, 70%, 55%)` (Violett, Backcountry-Konvention)
   - other: `hsl(0, 0%, 45%)` (neutrales Grau)

   Alle bei `fill-opacity: 0.25` (wie downhill). Linienfarbe für
   skitour/other-Basislinien: derselbe Vollton wie die jeweilige
   Füllfarbe (kein separater Wert).
6. **Nordic-Linienfarbe** (Basis + Ungroomed + Casing): 1:1 vom echten
   Stylesheet übernommen — `case lit==true → hsl(63,100%,76%) (gelb),
   sonst hsl(0,0%,100%) (weiß)`. Ersetzt die bisherige
   Schwierigkeits-Match-Expression. Casing war bereits identisch (schon
   vorher `case lit`-basiert, keine Änderung nötig, nur Umbenennung falls
   der Layer verschoben wird — bleibt inhaltlich gleich).
7. **Dasharray/Breiten für skitour/other**: `[3, 6]` (skitour) und
   `[3, 3]` (other), 1:1 vom echten Stylesheet übernommen (kategorie-
   unabhängiges Verhältnis, unabhängig von unterschiedlichen
   Zoom-Skalen). Breiten-Interpolation: dieselbe Kurve wie die
   bestehenden Basis-Linien (`downhill`/`nordic`: Zoom 6→0.8, 9→1.4,
   12→2.2, 14→3.0) — kein neuer Parameter, Konsistenz mit dem Bestand.
8. **Snowmaking bleibt auf downhill/nordic beschränkt** (kein
   kategorie-übergreifender gemeinsamer Layer wie im Original — technisch
   nicht möglich, da wir separate `source-layer`s pro Kategorie haben,
   keinen gemeinsamen `runs`-Source-Layer). skitour/other bekommen keine
   Snowmaking-Variante (Kunstschnee auf Skitouren-/Sonstige-Routen ist in
   der Praxis selten relevant) — konsistent mit Entscheidung 2
   (asymmetrischer Umfang).
9. **`oneway-run-icons`, `run-names`-Patrolled-Icon, `line-offset`-Feld**
   aus dem echten Stylesheet sind **nicht** Teil dieses Designs — neue
   Features ohne Bezug zur Kategorien-/Farb-Frage dieses TODO-Punkts,
   YAGNI.

## Kategorisierung (`scripts/convert.sh`)

Ersetzt die bisherigen `ALPINE_RUN_WHERE`/`NORDIC_RUN_WHERE`-Variablen
durch vier, mit fester Priorität:

```sql
DOWNHILL_RUN_WHERE = uses LIKE '%downhill%'
NORDIC_RUN_WHERE   = uses LIKE '%nordic%' AND uses NOT LIKE '%downhill%'
SKITOUR_RUN_WHERE  = uses LIKE '%skitour%' AND uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%'
OTHER_RUN_WHERE    = uses IS NULL OR (uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%')
```

`OTHER_RUN_WHERE` braucht das explizite `uses IS NULL OR (...)`: OGR-SQL
(SQLite-Dialekt) wertet `NULL LIKE '%x%'` als `NULL`, was in einer
`WHERE`-Klausel wie `false` behandelt wird — ohne den `IS NULL`-Zweig
würden Features mit leerem `uses`-Feld aus **allen vier** Kategorien
herausfallen und komplett verschwinden, statt in `other` zu landen
(Entscheidung 4: "kein Informationsverlust"). Aktueller Datensatz hat
0 Zeilen mit `uses IS NULL` in `runs_linestring`
(`ogrinfo -sql "SELECT COUNT(*) FROM runs_linestring WHERE uses IS NULL"`,
geprüft 2026-08-11) — der Fall tritt also aktuell nicht ein, die
Absicherung ist aber für künftige Datenstände nötig, da OpenSkiMap das
Feld nicht als Pflichtfeld garantiert.

Jede der vier Kategorien wird wie bisher getrennt nach Geometrietyp
extrahiert (`ogr2ogr` gegen `runs_linestring` und `runs_multipolygon`,
Entscheidung 5 macht die Polygon-Extraktion jetzt für alle vier relevant,
nicht nur downhill) → 8 `ogr2ogr`-Aufrufe statt 4, 8 Tippecanoe-`-L`-Layer
statt 4 für Runs:

`ski_runs_downhill_line`, `ski_runs_downhill_poly`,
`ski_runs_nordic_line`, `ski_runs_nordic_poly`,
`ski_runs_skitour_line`, `ski_runs_skitour_poly`,
`ski_runs_other_line`, `ski_runs_other_poly`.

## Style-Layer (`styles/openskimap-style.json`)

| Kategorie | Layer (Anzahl) | Herkunft |
|---|---|---|
| downhill | fill, casing, line, gladed, ungroomed, snowmaking, labels (7) | 1:1 heutige `ski-runs-alpine-*`-Werte, nur `alpine`→`downhill` umbenannt (Layer-IDs, `source-layer`) |
| nordic | fill, casing, line, ungroomed, snowmaking, labels (6) | Casing/Ungroomed/Snowmaking inhaltlich unverändert (nur `source-layer`-Name gleich, keine Umbenennung nötig); Fill/Line/Ungroomed-Farbe geändert (Entscheidung 5/6); **Gladed-Layer entfällt** (Entscheidung 2) |
| skitour | fill, line, labels (3) | Neu (Entscheidung 5/7) |
| other | fill, line, labels (3) | Neu (Entscheidung 5/7) |

19 Style-Layer insgesamt (heute: 14; −1 `ski-runs-nordic-gladed` entfällt,
+6 neu für skitour/other).

## `scripts/generate_layer_list.py`

`GROUP_MAP` wächst von 2 auf 4 Pisten-Gruppen (`ski-runs-downhill`,
`ski-runs-nordic`, `ski-runs-skitour`, `ski-runs-other`), alle
betroffenen Style-Layer-IDs entsprechend neu/umbenannt eingetragen —
sonst bricht `generate_manifest.py` mit `KeyError` ab (bestehender
Fail-Fast-Mechanismus, siehe Sub-Projekt A).

## Roadmap

Neuer Eintrag in einer neu anzulegenden `docs/ROADMAP.md`
(`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §3: neue Features gehören
dorthin, nicht in `TODO.md`): "Parallel versetzte Linien bei
Pisten-Mehrfachnutzung (`line-offset`)" — Kurzbeschreibung des im echten
Stylesheet beobachteten Verhaltens (serverseitig vorberechnete
Offset-Indizes pro Kategorie, `line-offset`-Expression pro Layer) und
warum es hier zurückgestellt wurde (kein vorberechnetes Feld, würde eigene
SQL-/Konvertierungslogik brauchen).

## Betroffene Dateien

- `scripts/convert.sh` — vier statt zwei `*_RUN_WHERE`-Variablen, 8 statt
  4 `ogr2ogr`-Aufrufe für Runs, 8 statt 4 Tippecanoe-`-L`-Flags.
- `styles/openskimap-style.json` — 19 statt 14 Run-Layer (siehe Tabelle
  oben).
- `scripts/generate_layer_list.py` — `GROUP_MAP` erweitert.
- `docs/ROADMAP.md` — neu angelegt, ein Eintrag (line-offset).
- `docs/TODO.md` — beide Punkte nach Umsetzung nach `docs/TODO_ARCHIVE.md`
  verschoben (wie bei den vorherigen Sub-Projekten).

**Nicht betroffen:** `scripts/download.sh`, `scripts/generate_manifest.py`,
`scripts/check_dependencies.sh`, `sources/openskimap.env`,
`assets/sprites/openskimap/*` (keine neuen Icons nötig, nur Linien/Flächen).

## Verifikation

- `python3 -c "import json; json.load(open('styles/openskimap-style.json'))"`
  — JSON weiterhin valide.
- `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
  bleibt grün.
- `python3 scripts/test_validate_style.py` bleibt grün (ggf. um einen
  Test für die vier neuen `source-layer`-Namen in
  `scripts/validate_style.py`s `KNOWN_SOURCE_LAYERS` ergänzt — Teil der
  Plan-Erstellung, nicht mehr Bestandteil dieses Designs).
- Stichprobe an den beiden TODO-Beispiel-Features: `feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`
  (`uses=sled`) muss laut Priorität in `other` landen (gestrichelt
  `[3,3]`), `feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`
  (`uses=hike`) ebenso.
- `ogrinfo -sql "SELECT uses, COUNT(*) FROM runs_linestring GROUP BY uses"`
  gegen jede der vier neuen WHERE-Klauseln geprüft, um sicherzustellen,
  dass jede Kombination aus der Taxonomie genau einer Kategorie zugeordnet
  wird (keine Überlappung durch die `LIKE`-Ketten, NULL-Fall über
  `uses IS NULL` in `OTHER_RUN_WHERE` abgedeckt, siehe Kategorisierungs-Abschnitt).
- Kompletter `run.sh`-Build gegen die echten Daten (etablierter
  End-to-End-Testpfad).

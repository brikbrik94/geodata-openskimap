# Run-Category Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Alpine/Nordic run-category split with four categories (downhill/nordic/skitour/other) matching the real OpenSkiMap taxonomy, and remove Nordic's difficulty-based coloring in favor of the real stylesheet's lit-based white/yellow scheme.

**Architecture:** `scripts/convert.sh` gets four `*_RUN_WHERE` SQL filters (priority downhill > nordic > skitour > other) instead of two, extracting 8 source-layers instead of 4 (line+poly × 4 categories). `styles/openskimap-style.json`'s run layers grow from 14 to 19 (downhill keeps the full 7-layer set renamed from alpine; nordic drops its gladed layer and switches from difficulty-match to lit-based coloring on fill/line/ungroomed; skitour/other are new, 3 layers each — fill+line+labels only, no casing/gladed/ungroomed/snowmaking). `scripts/generate_layer_list.py`'s `GROUP_MAP` and `scripts/validate_style.py`'s `KNOWN_SOURCE_LAYERS` are updated to match.

**Tech Stack:** Bash (`ogr2ogr`/`tippecanoe`), MapLibre-Style-JSON, Python 3.

## Global Constraints

Aus `docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`:

- Priorität: `downhill > nordic > skitour > other`, ein Feature bekommt genau eine Kategorie (kein `line-offset`, kein Mehrfach-Rendering).
- `OTHER_RUN_WHERE` muss `uses IS NULL` explizit abdecken (OGR-SQL: `NULL LIKE ...` ist `NULL`/falsy).
- Layer-Umfang: downhill = fill+casing+line+gladed+ungroomed+snowmaking+labels (7, aus `alpine` umbenannt). nordic = fill+casing+line+ungroomed+snowmaking+labels (6, **kein** gladed). skitour/other = fill+line+labels (3 je Kategorie, keine Casing/Gladed/Ungroomed/Snowmaking).
- Nordic-Farben: `line-color` bei `line`/`ungroomed`/`casing` = `case lit==true → hsl(63,100%,76%) sonst hsl(0,0%,100%)` (Casing hatte das schon, bleibt unverändert). `fill-color` = flacher Ton `hsl(200, 30%, 85%)`, keine Schwierigkeits-Match-Expression mehr.
- Skitour-Farbe (fill + line, einheitlich): `hsl(280, 70%, 55%)`. Dasharray Basis-Linie: `[3, 6]`.
- Other-Farbe (fill + line, einheitlich): `hsl(0, 0%, 45%)`. Dasharray Basis-Linie: `[3, 3]`.
- Skitour/Other-Basislinien-Breite: identische Zoom-Kurve wie downhill/nordic (`6→0.8, 9→1.4, 12→2.2, 14→3.0`).
- `fill-opacity: 0.25` für alle vier Kategorien (unverändert für downhill, neu für die anderen drei).
- Labels (`ski-runs-nordic-labels`) bleiben **komplett unverändert** — die Schwierigkeits-Match-Textfarbe ist nicht Teil der TODO-Beanstandung (die betraf nur Fläche/Linie) und degradiert in der Praxis ohnehin meist zum grauen Fallback, da `difficulty` bei Loipen meist `null` ist. Neue skitour/other-Labels bekommen die jeweilige Kategorie-Volltonfarbe als `text-color`.
- `scripts/download.sh`, `scripts/generate_manifest.py`, `scripts/check_dependencies.sh`, `sources/openskimap.env`, `assets/sprites/openskimap/*` bleiben unangetastet.

---

### Task 1: `scripts/convert.sh` — vier Kategorien statt zwei

**Files:**
- Modify: `scripts/convert.sh:47-58` (Kommentar + `*_RUN_WHERE`-Variablen + `ogr2ogr`-Aufrufe)
- Modify: `scripts/convert.sh:82-85` (Tippecanoe `-L`-Flags für Runs)

**Interfaces:**
- Produces: acht `.jsonseq`-Zwischendateien (`ski_runs_downhill_line/poly`, `ski_runs_nordic_line/poly`, `ski_runs_skitour_line/poly`, `ski_runs_other_line/poly`) und entsprechende Tippecanoe-`source-layer`-Namen im fertigen PMTiles — Task 2-5 konsumieren genau diese acht Namen als `"source-layer"`-Werte in `styles/openskimap-style.json`.

- [ ] **Step 1: `*_RUN_WHERE`-Block und `ogr2ogr`-Aufrufe ersetzen**

Mit dem Edit-Tool `old_string`:
```bash
# Pisten/Loipen: nach 'uses' in Alpine/Nordic aufgeteilt.
# Gemischte Nutzung (uses="downhill,nordic") landet in beiden Layern; alles was
# nicht explizit nordic ist (downhill, skitour, connection, sled, hike, ...)
# faellt in den Alpine-Layer. Linien- und Polygon-Geometrie bleiben getrennt,
# siehe Kommentar oben.
ALPINE_RUN_WHERE="uses LIKE '%downhill%' OR uses NOT LIKE '%nordic%'"
NORDIC_RUN_WHERE="uses LIKE '%nordic%'"

ogr2ogr -f GeoJSONSeq ski_runs_alpine_line.jsonseq "$INPUT_FILE" runs_linestring -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_alpine_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
```
ersetzen durch `new_string`:
```bash
# Pisten/Loipen: nach 'uses' in vier Kategorien aufgeteilt, mit fester
# Prioritaet downhill > nordic > skitour > other (siehe
# docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md).
# Jedes Feature bekommt genau eine Kategorie - keine Mehrfachzuordnung wie
# bei den Ski-Gebieten oben. Das echte OpenSkiMap-Stylesheet zeichnet bei
# Mehrfachnutzung mehrere parallel versetzte Linien (line-offset); das ist
# als Roadmap-Punkt zurueckgestellt, siehe docs/ROADMAP.md. Linien- und
# Polygon-Geometrie bleiben getrennt, siehe Kommentar oben.
# OTHER_RUN_WHERE deckt auch NULL/leeres 'uses' ab: OGR-SQL wertet
# "NULL LIKE '%x%'" als NULL/falsy - ohne den IS-NULL-Zweig wuerden
# Features ganz ohne uses-Wert aus allen vier Kategorien herausfallen.
DOWNHILL_RUN_WHERE="uses LIKE '%downhill%'"
NORDIC_RUN_WHERE="uses LIKE '%nordic%' AND uses NOT LIKE '%downhill%'"
SKITOUR_RUN_WHERE="uses LIKE '%skitour%' AND uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%'"
OTHER_RUN_WHERE="uses IS NULL OR (uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%')"

ogr2ogr -f GeoJSONSeq ski_runs_downhill_line.jsonseq "$INPUT_FILE" runs_linestring -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_downhill_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_line.jsonseq "$INPUT_FILE" runs_linestring -where "$OTHER_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$OTHER_RUN_WHERE"
```

- [ ] **Step 2: Tippecanoe `-L`-Flags für Runs ersetzen**

Mit dem Edit-Tool `old_string`:
```
  -L "ski_runs_alpine_line:ski_runs_alpine_line.jsonseq" \
  -L "ski_runs_alpine_poly:ski_runs_alpine_poly.jsonseq" \
  -L "ski_runs_nordic_line:ski_runs_nordic_line.jsonseq" \
  -L "ski_runs_nordic_poly:ski_runs_nordic_poly.jsonseq" \
```
ersetzen durch `new_string`:
```
  -L "ski_runs_downhill_line:ski_runs_downhill_line.jsonseq" \
  -L "ski_runs_downhill_poly:ski_runs_downhill_poly.jsonseq" \
  -L "ski_runs_nordic_line:ski_runs_nordic_line.jsonseq" \
  -L "ski_runs_nordic_poly:ski_runs_nordic_poly.jsonseq" \
  -L "ski_runs_skitour_line:ski_runs_skitour_line.jsonseq" \
  -L "ski_runs_skitour_poly:ski_runs_skitour_poly.jsonseq" \
  -L "ski_runs_other_line:ski_runs_other_line.jsonseq" \
  -L "ski_runs_other_poly:ski_runs_other_poly.jsonseq" \
```

- [ ] **Step 3: Bash-Syntax prüfen**

Run: `bash -n scripts/convert.sh`
Expected: keine Ausgabe (Exit-Code 0)

- [ ] **Step 4: Kategorisierungs-Logik gegen die echten Daten verifizieren**

Run (vier Kategorien, `runs_linestring`):
```bash
cd /mnt/geodata/geodata-openskimap
for label in "downhill:uses LIKE '%downhill%'" \
             "nordic:uses LIKE '%nordic%' AND uses NOT LIKE '%downhill%'" \
             "skitour:uses LIKE '%skitour%' AND uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%'" \
             "other:uses IS NULL OR (uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%')"; do
    name="${label%%:*}"
    where="${label#*:}"
    echo -n "$name: "
    ogrinfo -sql "SELECT COUNT(*) as cnt FROM runs_linestring WHERE $where" data/src/openskidata.gpkg 2>/dev/null | grep "cnt (Integer)"
done
```
Expected (Datenstand 2026-08-11, `data/src/openskidata.gpkg`):
```
downhill:   cnt (Integer) = 96482
nordic:     cnt (Integer) = 96555
skitour:    cnt (Integer) = 5554
other:      cnt (Integer) = 16239
```
Summe = 214830 = `SELECT COUNT(*) FROM runs_linestring` (Gesamtzahl Features) — bestätigt, dass die vier Kategorien lückenlos und überlappungsfrei sind. Bei Abweichung: WHERE-Klauseln erneut gegen die Kategorisierungs-Logik im Design-Dokument prüfen, nicht einfach die Erwartungswerte anpassen — eine Abweichung von der Summe bedeutet, dass entweder Features doppelt gezählt werden (Priorität falsch) oder welche durchfallen (NULL-Fall falsch).

- [ ] **Step 5: Die zwei TODO-Beispiel-Features landen in `other`**

Run:
```bash
ogrinfo -sql "SELECT feature_id, uses FROM runs_linestring WHERE feature_id='3d4a993682eda4d6b4b318d83fc3178819d74d0e'" data/src/openskidata.gpkg 2>/dev/null | grep -E "feature_id \(|uses \("
ogrinfo -sql "SELECT feature_id, uses FROM runs_linestring WHERE feature_id='62ad174f8ac9d72c286582fd5d680ba007ea795f'" data/src/openskidata.gpkg 2>/dev/null | grep -E "feature_id \(|uses \("
```
Expected: erstes Feature `uses = sled`, zweites `uses = hike` — beide matchen keine der `downhill`/`nordic`/`skitour`-Bedingungen, fallen also in `other` (bestätigt die beiden in der TODO-Notiz dokumentierten Lücken sind jetzt behoben: sled landet gestrichelt `[3,3]` in `other` statt unmarkiert in `downhill`).

- [ ] **Step 6: `convert.sh` end-to-end laufen lassen**

Run: `bash scripts/convert.sh 2>&1 | tail -40`
Expected: läuft durch bis `✔ OpenSkimap PMTiles erfolgreich erstellt.`, keine Fehlermeldung von `ogr2ogr` oder `tippecanoe`. Dauert mehrere Minuten (Tippecanoe über den vollen Datensatz) — kein `timeout` mit kurzer Frist verwenden, im Hintergrund laufen lassen und auf Fertigstellung warten statt die Ausgabe abzuschneiden.

**Kein Commit in diesem Task.** `styles/openskimap-style.json` referenziert bis Task 5 noch die alten `ski_runs_alpine_*`-Source-Layer-Namen, die `convert.sh` ab jetzt nicht mehr erzeugt — ein Build zu diesem Zeitpunkt liefe zwar durch (MapLibre wirft bei unbekanntem `source-layer` keinen Fehler, rendert aber schlicht nichts für die betroffenen Layer), das ist ein stiller, nicht laut fehlschlagender Zwischenzustand. Tasks 1-5 landen deshalb gemeinsam in einem Commit (Task 5), analog zum Vorgehen in Sub-Projekt A.

---

### Task 2: `styles/openskimap-style.json` — downhill (Umbenennung von alpine)

**Files:**
- Modify: `styles/openskimap-style.json` (7 Layer: `ski-runs-alpine-fill` bei Zeile 84, `-casing` bei 272, `-line` bei 356, `-gladed` bei 494, `-ungroomed` bei 623, `-snowmaking` bei 757, `-labels` bei 1667 — Zeilennummern Stand vor diesem Task, verschieben sich nicht durch diesen Task, da nur Kopf-Zeilen ersetzt werden, keine Zeilen hinzugefügt/entfernt)

**Interfaces:**
- Consumes: `ski_runs_downhill_line`/`ski_runs_downhill_poly` aus Task 1.
- Produces: Layer-IDs `ski-runs-downhill-fill`, `-casing`, `-line`, `-gladed`, `-ungroomed`, `-snowmaking`, `-labels` — Task 5 (`GROUP_MAP`) konsumiert genau diese sieben IDs.

Alle sieben Änderungen sind reine Kopfzeilen-Umbenennungen (`id` und `source-layer`, `alpine`→`downhill`) — der komplette Rest jedes Layers (Filter, Layout, Paint) bleibt **byte-identisch**, nur mit dem Edit-Tool auf den eindeutigen 4-Zeilen-Kopf beschränkt, damit kein Transkriptionsrisiko am großen, unveränderten Rest entsteht.

- [ ] **Step 1: `ski-runs-alpine-fill` → `ski-runs-downhill-fill`**

`old_string`:
```json
      "id": "ski-runs-alpine-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_poly",
```
`new_string`:
```json
      "id": "ski-runs-downhill-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_poly",
```

- [ ] **Step 2: `ski-runs-alpine-casing` → `ski-runs-downhill-casing`**

`old_string`:
```json
      "id": "ski-runs-alpine-casing",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-casing",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 3: `ski-runs-alpine-line` → `ski-runs-downhill-line`**

`old_string`:
```json
      "id": "ski-runs-alpine-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 4: `ski-runs-alpine-gladed` → `ski-runs-downhill-gladed`**

`old_string`:
```json
      "id": "ski-runs-alpine-gladed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-gladed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 5: `ski-runs-alpine-ungroomed` → `ski-runs-downhill-ungroomed`**

`old_string`:
```json
      "id": "ski-runs-alpine-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 6: `ski-runs-alpine-snowmaking` → `ski-runs-downhill-snowmaking`**

`old_string`:
```json
      "id": "ski-runs-alpine-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 7: `ski-runs-alpine-labels` → `ski-runs-downhill-labels`**

`old_string`:
```json
      "id": "ski-runs-alpine-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
```
`new_string`:
```json
      "id": "ski-runs-downhill-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_downhill_line",
```

- [ ] **Step 8: JSON-Syntax prüfen**

Run: `python3 -c "import json; json.load(open('styles/openskimap-style.json')); print('valid JSON')"`
Expected: `valid JSON`

- [ ] **Step 9: Sieben Umbenennungen bestätigen, keine `alpine`-Reste mehr bei Runs**

Run:
```bash
python3 -c "
import json
d = json.load(open('styles/openskimap-style.json'))
ids = [l['id'] for l in d['layers'] if l['id'].startswith('ski-runs-downhill') or l['id'].startswith('ski-runs-alpine')]
print(sorted(ids))
"
```
Expected: `['ski-runs-downhill-casing', 'ski-runs-downhill-fill', 'ski-runs-downhill-gladed', 'ski-runs-downhill-labels', 'ski-runs-downhill-line', 'ski-runs-downhill-snowmaking', 'ski-runs-downhill-ungroomed']` — keine `ski-runs-alpine-*`-IDs mehr.

**Kein Commit in diesem Task** (siehe Begründung in Task 1).

---

### Task 3: `styles/openskimap-style.json` — nordic (Gladed entfernen, Farben umstellen)

**Files:**
- Modify: `styles/openskimap-style.json` (vier vollständige Layer-Ersetzungen: `ski-runs-nordic-fill`, `-line`, `-ungroomed`; ein Layer wird gelöscht: `ski-runs-nordic-gladed`)

**Interfaces:**
- Consumes: `ski_runs_nordic_line`/`ski_runs_nordic_poly` (Namen unverändert seit Task 1 — nordic behält seinen Source-Layer-Namen).
- Produces: Layer-IDs `ski-runs-nordic-fill`, `-casing` (unverändert), `-line`, `-ungroomed`, `-snowmaking` (unverändert), `-labels` (unverändert) — sechs statt sieben, `-gladed` entfällt. Task 5 (`GROUP_MAP`) konsumiert diese sechs IDs.

**Explizit unverändert, kein Edit nötig:** `ski-runs-nordic-casing` (referenziert bereits `ski_runs_nordic_line`, Farblogik war schon `case lit`-basiert), `ski-runs-nordic-snowmaking` (Source-Layer-Name unverändert, Farblogik war schon fix), `ski-runs-nordic-labels` (Textfarbe bewusst unverändert, siehe Global Constraints).

- [ ] **Step 1: `ski-runs-nordic-fill` — Schwierigkeits-Match durch flachen Ton ersetzen**

`old_string`:
```json
      "id": "ski-runs-nordic-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_poly",
      "paint": {
        "fill-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "fill-opacity": 0.25
      }
    },
    {
      "id": "ski-runs-alpine-casing",
```

**Hinweis:** Der `old_string` oben endet bewusst mit der ersten Zeile des nachfolgenden Layers (`"id": "ski-runs-alpine-casing",`), NICHT `ski-runs-downhill-casing` — Task 2 läuft vor diesem Task und hat diese Zeile bereits umbenannt. Verwende stattdessen als letzte Zeile des `old_string` die durch Task 2 bereits umbenannte Zeile:
```json
      "id": "ski-runs-downhill-casing",
```
(nur zur eindeutigen Verankerung des Blockendes — diese Zeile selbst bleibt unverändert, nur der `ski-runs-nordic-fill`-Block davor wird ersetzt.)

`new_string` (ersetzt nur den `ski-runs-nordic-fill`-Block, die verankernde `ski-runs-downhill-casing`-Zeile am Ende bleibt identisch erhalten):
```json
      "id": "ski-runs-nordic-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_poly",
      "paint": {
        "fill-color": "hsl(200, 30%, 85%)",
        "fill-opacity": 0.25
      }
    },
    {
      "id": "ski-runs-downhill-casing",
```

- [ ] **Step 2: `ski-runs-nordic-line` — Filter vereinfachen (kein Gladed-Ausschluss mehr) + Farbe auf `case lit` umstellen**

`old_string`:
```json
      "id": "ski-runs-nordic-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "filter": [
        "all",
        [
          "!=",
          [
            "get",
            "gladed"
          ],
          true
        ],
        [
          "match",
          [
            "get",
            "grooming"
          ],
          [
            "backcountry",
            "mogul"
          ],
          false,
          true
        ]
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ]
      }
    },
```
`new_string`:
```json
      "id": "ski-runs-nordic-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "filter": [
        "match",
        [
          "get",
          "grooming"
        ],
        [
          "backcountry",
          "mogul"
        ],
        false,
        true
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "case",
          [
            "==",
            [
              "get",
              "lit"
            ],
            true
          ],
          "hsl(63, 100%, 76%)",
          "hsl(0, 0%, 100%)"
        ],
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ]
      }
    },
```

**Wichtig:** Der Gladed-Ausschluss (`["!=", ["get","gladed"], true]`) entfällt bewusst — da nordic ab diesem Task keinen eigenen Gladed-Layer mehr hat (Step 3), würden gladed-markierte Loipen sonst in keinem Layer mehr auftauchen (unsichtbar statt nur undifferenziert dargestellt). Das echte Stylesheet macht es genauso: `nordic-runs` filtert nicht nach `gladed`.

- [ ] **Step 3: `ski-runs-nordic-gladed` komplett löschen**

`old_string`:
```json
    {
      "id": "ski-runs-nordic-gladed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "filter": [
        "==",
        [
          "get",
          "gladed"
        ],
        true
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            0.1,
            4
          ]
        ]
      }
    },
```
`new_string`: *(leer — der gesamte Block wird ersatzlos gelöscht)*

- [ ] **Step 4: `ski-runs-nordic-ungroomed` — Farbe auf `case lit` umstellen**

`old_string`:
```json
      "id": "ski-runs-nordic-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "filter": [
        "match",
        [
          "get",
          "grooming"
        ],
        [
          "backcountry",
          "mogul"
        ],
        true,
        false
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            2,
            4
          ]
        ]
      }
    },
```
`new_string`:
```json
      "id": "ski-runs-nordic-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "filter": [
        "match",
        [
          "get",
          "grooming"
        ],
        [
          "backcountry",
          "mogul"
        ],
        true,
        false
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "case",
          [
            "==",
            [
              "get",
              "lit"
            ],
            true
          ],
          "hsl(63, 100%, 76%)",
          "hsl(0, 0%, 100%)"
        ],
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            2,
            4
          ]
        ]
      }
    },
```

- [ ] **Step 5: JSON-Syntax prüfen**

Run: `python3 -c "import json; json.load(open('styles/openskimap-style.json')); print('valid JSON')"`
Expected: `valid JSON`

- [ ] **Step 6: Nordic-Layer-Satz bestätigen (sechs statt sieben, kein Gladed mehr)**

Run:
```bash
python3 -c "
import json
d = json.load(open('styles/openskimap-style.json'))
ids = sorted(l['id'] for l in d['layers'] if l['id'].startswith('ski-runs-nordic'))
print(ids)
"
```
Expected: `['ski-runs-nordic-casing', 'ski-runs-nordic-fill', 'ski-runs-nordic-labels', 'ski-runs-nordic-line', 'ski-runs-nordic-snowmaking', 'ski-runs-nordic-ungroomed']` (sechs, kein `-gladed`).

**Kein Commit in diesem Task** (siehe Begründung in Task 1).

---

### Task 4: `styles/openskimap-style.json` — skitour und other (neu)

**Files:**
- Modify: `styles/openskimap-style.json` (sechs neue Layer eingefügt: `ski-runs-skitour-fill`, `-line`, `-labels`, `ski-runs-other-fill`, `-line`, `-labels`)

**Interfaces:**
- Consumes: `ski_runs_skitour_line`/`_poly`, `ski_runs_other_line`/`_poly` aus Task 1.
- Produces: Layer-IDs `ski-runs-skitour-fill`, `-line`, `-labels`, `ski-runs-other-fill`, `-line`, `-labels` — Task 5 (`GROUP_MAP`) konsumiert genau diese sechs IDs.

- [ ] **Step 1: `ski-runs-skitour-fill` und `ski-runs-skitour-line` nach `ski-runs-nordic-snowmaking` einfügen**

`old_string` (Ende von `ski-runs-nordic-snowmaking`, Anker unverändert seit vor Task 3, da dieser Layer nicht editiert wurde):
```json
      "id": "ski-runs-nordic-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "minzoom": 11,
      "filter": [
        "any",
        [
          "==",
          [
            "get",
            "snowmaking"
          ],
          true
        ],
        [
          "==",
          [
            "get",
            "snowfarming"
          ],
          true
        ]
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "rgba(196, 251, 255, 0.9)",
        "line-width": 1.5
      }
    },
```
`new_string` (identischer Block + zwei neue Layer angehängt):
```json
      "id": "ski-runs-nordic-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "minzoom": 11,
      "filter": [
        "any",
        [
          "==",
          [
            "get",
            "snowmaking"
          ],
          true
        ],
        [
          "==",
          [
            "get",
            "snowfarming"
          ],
          true
        ]
      ],
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "rgba(196, 251, 255, 0.9)",
        "line-width": 1.5
      }
    },
    {
      "id": "ski-runs-skitour-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_skitour_poly",
      "paint": {
        "fill-color": "hsl(280, 70%, 55%)",
        "fill-opacity": 0.25
      }
    },
    {
      "id": "ski-runs-skitour-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_skitour_line",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "hsl(280, 70%, 55%)",
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            3,
            6
          ]
        ]
      }
    },
```

- [ ] **Step 2: `ski-runs-other-fill` und `ski-runs-other-line` direkt nach `ski-runs-skitour-line` einfügen**

`old_string` (Ende des in Step 1 eingefügten `ski-runs-skitour-line`-Blocks):
```json
    {
      "id": "ski-runs-skitour-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_skitour_line",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "hsl(280, 70%, 55%)",
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            3,
            6
          ]
        ]
      }
    },
```
`new_string` (identischer Block + zwei neue Layer angehängt):
```json
    {
      "id": "ski-runs-skitour-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_skitour_line",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "hsl(280, 70%, 55%)",
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            3,
            6
          ]
        ]
      }
    },
    {
      "id": "ski-runs-other-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_other_poly",
      "paint": {
        "fill-color": "hsl(0, 0%, 45%)",
        "fill-opacity": 0.25
      }
    },
    {
      "id": "ski-runs-other-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_other_line",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "hsl(0, 0%, 45%)",
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          0.8,
          9,
          1.4,
          12,
          2.2,
          14,
          3.0
        ],
        "line-dasharray": [
          "literal",
          [
            3,
            3
          ]
        ]
      }
    },
```

- [ ] **Step 3: `ski-runs-skitour-labels` und `ski-runs-other-labels` nach `ski-runs-nordic-labels` einfügen**

`old_string` (Ende von `ski-runs-nordic-labels`, unverändert seit vor Task 3 — dieser Layer wurde nicht editiert):
```json
      "id": "ski-runs-nordic-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "minzoom": 13,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "get",
          "name"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          13,
          10,
          14,
          12
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-rotation-alignment": "map",
        "text-keep-upright": true,
        "text-max-angle": 30,
        "text-letter-spacing": 0.05,
        "text-padding": 2
      },
      "paint": {
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.2,
        "text-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "text-opacity": 0.9
      }
    },
```
`new_string` (identischer Block + zwei neue Label-Layer angehängt):
```json
      "id": "ski-runs-nordic-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic_line",
      "minzoom": 13,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "get",
          "name"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          13,
          10,
          14,
          12
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-rotation-alignment": "map",
        "text-keep-upright": true,
        "text-max-angle": 30,
        "text-letter-spacing": 0.05,
        "text-padding": 2
      },
      "paint": {
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.2,
        "text-color": [
          "case",
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "europe"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(208, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "==",
            [
              "get",
              "difficulty_convention"
            ],
            "japan"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(359, 94%, 53%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ],
          [
            "match",
            [
              "get",
              "difficulty"
            ],
            "novice",
            "hsl(125, 100%, 33%)",
            "easy",
            "hsl(125, 100%, 33%)",
            "intermediate",
            "hsl(208, 100%, 33%)",
            "advanced",
            "hsl(0, 0%, 0%)",
            "expert",
            "hsl(0, 0%, 0%)",
            "freeride",
            "hsl(34, 100%, 50%)",
            "extreme",
            "hsl(34, 100%, 50%)",
            "hsl(0, 0%, 35%)"
          ]
        ],
        "text-opacity": 0.9
      }
    },
    {
      "id": "ski-runs-skitour-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_skitour_line",
      "minzoom": 13,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "get",
          "name"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          13,
          10,
          14,
          12
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-rotation-alignment": "map",
        "text-keep-upright": true,
        "text-max-angle": 30,
        "text-letter-spacing": 0.05,
        "text-padding": 2
      },
      "paint": {
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.2,
        "text-color": "hsl(280, 70%, 55%)",
        "text-opacity": 0.9
      }
    },
    {
      "id": "ski-runs-other-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_other_line",
      "minzoom": 13,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "get",
          "name"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          13,
          10,
          14,
          12
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-rotation-alignment": "map",
        "text-keep-upright": true,
        "text-max-angle": 30,
        "text-letter-spacing": 0.05,
        "text-padding": 2
      },
      "paint": {
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.2,
        "text-color": "hsl(0, 0%, 45%)",
        "text-opacity": 0.9
      }
    },
```

- [ ] **Step 4: JSON-Syntax prüfen**

Run: `python3 -c "import json; json.load(open('styles/openskimap-style.json')); print('valid JSON')"`
Expected: `valid JSON`

- [ ] **Step 5: Vollständigen Run-Layer-Satz bestätigen (19 Layer)**

Run:
```bash
python3 -c "
import json
d = json.load(open('styles/openskimap-style.json'))
ids = sorted(l['id'] for l in d['layers'] if l['id'].startswith('ski-runs-'))
print(len(ids), ids)
"
```
Expected: `19` Layer, genau diese Liste:
```
['ski-runs-downhill-casing', 'ski-runs-downhill-fill', 'ski-runs-downhill-gladed',
 'ski-runs-downhill-labels', 'ski-runs-downhill-line', 'ski-runs-downhill-snowmaking',
 'ski-runs-downhill-ungroomed', 'ski-runs-nordic-casing', 'ski-runs-nordic-fill',
 'ski-runs-nordic-labels', 'ski-runs-nordic-line', 'ski-runs-nordic-snowmaking',
 'ski-runs-nordic-ungroomed', 'ski-runs-other-fill', 'ski-runs-other-labels',
 'ski-runs-other-line', 'ski-runs-skitour-fill', 'ski-runs-skitour-labels',
 'ski-runs-skitour-line']
```

**Kein Commit in diesem Task** (siehe Begründung in Task 1).

---

### Task 5: `generate_layer_list.py` + `validate_style.py` — GROUP_MAP/KNOWN_SOURCE_LAYERS aktualisieren, alles committen

**Files:**
- Modify: `scripts/generate_layer_list.py:51-64` (`GROUP_MAP`-Ausschnitt für Runs)
- Modify: `scripts/validate_style.py:12-23` (`KNOWN_SOURCE_LAYERS`)

**Interfaces:**
- Consumes: alle 19 Run-Layer-IDs aus Task 2-4, alle acht neuen `source-layer`-Namen aus Task 1.

- [ ] **Step 1: `GROUP_MAP` aktualisieren**

`old_string`:
```python
    "ski-runs-alpine-fill": "ski-runs-alpine",
    "ski-runs-alpine-casing": "ski-runs-alpine",
    "ski-runs-alpine-line": "ski-runs-alpine",
    "ski-runs-alpine-gladed": "ski-runs-alpine",
    "ski-runs-alpine-ungroomed": "ski-runs-alpine",
    "ski-runs-alpine-snowmaking": "ski-runs-alpine",
    "ski-runs-alpine-labels": "ski-runs-alpine",
    "ski-runs-nordic-fill": "ski-runs-nordic",
    "ski-runs-nordic-casing": "ski-runs-nordic",
    "ski-runs-nordic-line": "ski-runs-nordic",
    "ski-runs-nordic-gladed": "ski-runs-nordic",
    "ski-runs-nordic-ungroomed": "ski-runs-nordic",
    "ski-runs-nordic-snowmaking": "ski-runs-nordic",
    "ski-runs-nordic-labels": "ski-runs-nordic",
```
`new_string`:
```python
    "ski-runs-downhill-fill": "ski-runs-downhill",
    "ski-runs-downhill-casing": "ski-runs-downhill",
    "ski-runs-downhill-line": "ski-runs-downhill",
    "ski-runs-downhill-gladed": "ski-runs-downhill",
    "ski-runs-downhill-ungroomed": "ski-runs-downhill",
    "ski-runs-downhill-snowmaking": "ski-runs-downhill",
    "ski-runs-downhill-labels": "ski-runs-downhill",
    "ski-runs-nordic-fill": "ski-runs-nordic",
    "ski-runs-nordic-casing": "ski-runs-nordic",
    "ski-runs-nordic-line": "ski-runs-nordic",
    "ski-runs-nordic-ungroomed": "ski-runs-nordic",
    "ski-runs-nordic-snowmaking": "ski-runs-nordic",
    "ski-runs-nordic-labels": "ski-runs-nordic",
    "ski-runs-skitour-fill": "ski-runs-skitour",
    "ski-runs-skitour-line": "ski-runs-skitour",
    "ski-runs-skitour-labels": "ski-runs-skitour",
    "ski-runs-other-fill": "ski-runs-other",
    "ski-runs-other-line": "ski-runs-other",
    "ski-runs-other-labels": "ski-runs-other",
```

- [ ] **Step 2: `KNOWN_SOURCE_LAYERS` aktualisieren**

`old_string`:
```python
KNOWN_SOURCE_LAYERS = {
    "ski_areas_alpine_point",
    "ski_areas_alpine_poly",
    "ski_areas_nordic_point",
    "ski_areas_nordic_poly",
    "ski_runs_alpine_line",
    "ski_runs_alpine_poly",
    "ski_runs_nordic_line",
    "ski_runs_nordic_poly",
    "ski_lifts",
    "ski_spots",
}
```
`new_string`:
```python
KNOWN_SOURCE_LAYERS = {
    "ski_areas_alpine_point",
    "ski_areas_alpine_poly",
    "ski_areas_nordic_point",
    "ski_areas_nordic_poly",
    "ski_runs_downhill_line",
    "ski_runs_downhill_poly",
    "ski_runs_nordic_line",
    "ski_runs_nordic_poly",
    "ski_runs_skitour_line",
    "ski_runs_skitour_poly",
    "ski_runs_other_line",
    "ski_runs_other_poly",
    "ski_lifts",
    "ski_spots",
}
```

- [ ] **Step 3: Bestehende Style-Tests laufen lassen**

Run: `python3 scripts/test_validate_style.py`
Expected: `OK` (alle 7 Tests grün, unverändert — diese Tests prüfen generisches `validate()`-Verhalten, nicht layerspezifisch).

- [ ] **Step 4: `validate_style.py` gegen den echten Style laufen lassen**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 5: `generate_manifest.py` laufen lassen — bestätigt, dass `GROUP_MAP` vollständig ist**

Run: `python3 scripts/generate_manifest.py 2>&1 | tail -10`

Voraussetzung: `work/openskimap.pmtiles` muss existieren (aus Task 1 Step 6). Falls nicht mehr vorhanden (z. B. neue Session), zuerst `bash scripts/convert.sh` erneut laufen lassen.

Expected: Kein `KeyError` (bestätigt, dass alle 19 Run-Layer-IDs jetzt im `GROUP_MAP` stehen), Ausgabe endet mit `✔ Layer-list saved to: .../dist/layer-list.json (N Gruppen)`.

- [ ] **Step 6: `ski-runs-*`-Gruppen in `dist/layer-list.json` inspizieren**

Run:
```bash
python3 -c "
import json
d = json.load(open('dist/layer-list.json'))
for s in d['styles']:
    for g in s['groups']:
        if g['template'].startswith('ski-runs'):
            print(g['template'], sorted(g['style_layers']))
"
```
Expected: vier Gruppen (`ski-runs-downhill`, `ski-runs-nordic`, `ski-runs-skitour`, `ski-runs-other`), mit 7/6/3/3 `style_layers` je Gruppe (siehe Task 2-4 für die genauen Listen).

- [ ] **Step 7: Commit (Tasks 1-5 zusammen)**

```bash
git add scripts/convert.sh styles/openskimap-style.json scripts/generate_layer_list.py scripts/validate_style.py
git commit -m "$(cat <<'EOF'
feat(style): replace alpine/nordic run split with downhill/nordic/skitour/other

The real OpenSkiMap stylesheet categorizes runs into four buckets
(downhill/nordic/skitour/other) instead of our alpine/nordic split, each
with its own dash pattern, and doesn't color nordic (cross-country) runs
by difficulty. convert.sh now extracts four run categories by priority
(downhill > nordic > skitour > other, single category per feature — no
line-offset support for multi-use ways, see docs/ROADMAP.md) instead of
two. styles/openskimap-style.json's run layers grow from 14 to 19:
downhill keeps the full casing/gladed/ungroomed/snowmaking set (renamed
from alpine), nordic drops its gladed layer and switches from
difficulty-match to lit-based white/yellow coloring on fill/line/
ungroomed (labels keep their difficulty-based text color unchanged — not
part of this fix, and it degrades to a sensible gray fallback in practice
since nordic features rarely have a difficulty rating), skitour/other are
new with a single dashed line + flat-color fill each (no casing/gladed/
ungroomed/snowmaking, matching the real stylesheet's simpler treatment of
those categories). generate_layer_list.py's GROUP_MAP and
validate_style.py's KNOWN_SOURCE_LAYERS updated to match.

Fixes both examples from docs/TODO.md: a sled-use run
(feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e) and a hike-use run
(feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f) now render dashed
in the "other" category instead of unmarked in the old alpine catchall.

See docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md for
the full design and the decisions behind the category priority, colors,
and asymmetric layer scope.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `docs/ROADMAP.md` anlegen + `docs/TODO.md` archivieren

**Files:**
- Create: `docs/ROADMAP.md`
- Modify: `docs/TODO.md` (beide erledigten Punkte entfernen)
- Modify: `docs/TODO_ARCHIVE.md` (beide Punkte anhängen)

**Interfaces:** Keine — reine Dokumentation, unabhängig vom Code-Commit in Task 5.

- [ ] **Step 1: `docs/ROADMAP.md` neu anlegen**

Mit dem Write-Tool folgenden Inhalt nach `docs/ROADMAP.md` schreiben:
```markdown
# ROADMAP

Neue Features/Funktionen, die es im Code noch nicht gibt (keine Erweiterung
von etwas Bestehendem) — siehe `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md`
§3 zur Abgrenzung gegenüber `docs/TODO.md`. Erledigte Punkte wandern nach
`docs/ROADMAP_ARCHIVE.md` (nicht löschen — Historie bleibt erhalten).

## Parallel versetzte Linien bei Pisten-Mehrfachnutzung (`line-offset`)

Das echte OpenSkiMap-Stylesheet zeichnet bei Mehrfachnutzung einer Piste
(z. B. `uses=downhill,skitour`) **mehrere parallel versetzte Linien** —
eine pro zutreffender Kategorie —, über ein serverseitig vorberechnetes
numerisches Feld pro Kategorie (`downhill`/`nordic`/`skitour`/`other`),
das zusätzlich als `line-offset`-Multiplikator dient (siehe
`downhill-runs-casing` im Session-Snapshot `/tmp/openskimap_terrain_style.json`:
`"line-offset": ["interpolate", ..., ["*", 0.5, ["get", "downhill"]], ...]`).

Wir haben stattdessen (Entscheidung in
`docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`) ein
einfacheres Modell: jedes Feature bekommt genau eine Kategorie nach fester
Priorität (`downhill > nordic > skitour > other`), keine parallelen
Linien. Grund: unser GeoPackage hat kein vorberechnetes Offset-Index-Feld,
das selbst zu berechnen wäre deutlich komplexer als die aktuelle
Prioritäts-Zuordnung (u. a. müsste für jede Kombination aus mehreren
zutreffenden Kategorien ein stabiler Index ermittelt werden, der bei
paralleler Nutzung mehrerer benachbarter Pisten nicht überlappt).

Für eine spätere Umsetzung: `scripts/convert.sh` müsste die Feature-Zahl
pro Kategorie in ein eigenes numerisches Property schreiben (z. B. per
SQL-`CASE`/Fensterfunktion oder einem nachgelagerten Python-Skript vor der
`ogr2ogr`-Extraktion), `styles/openskimap-style.json`s Run-Line-Layer
bräuchten dann `line-offset`-Expressions analog zum echten Stylesheet.
```

- [ ] **Step 2: Beide Punkte aus `docs/TODO.md` entfernen**

Aktueller Inhalt von `docs/TODO.md` zwischen der "Referenz"-Sektion und
der "Versionierung"-Sektion (die beiden zu diesem Sub-Projekt gehörenden
Punkte):

```
## Pisten-Kategorien: downhill / nordic / skitour / other statt nur alpine/nordic

Echtes Stylesheet nutzt **vier** Kategorien pro Lauf-Feature (nicht zwei wie
unser Alpine/Nordic-Split), jede mit eigenem Layer + Dash-Pattern, per
`["has", "<kategorie>"]`-Flag (serverseitig vorberechnet, vermutlich
Mehrfachzuordnung möglich):

- `downhill-runs`: `has downhill`, durchgezogen, schwierigkeitsgefärbt.
- `nordic-runs`: `has nordic` — **keine Schwierigkeitsfarbe**, nur
  casing-artiges Weiß/Gelb(falls `lit`). Loipen haben im Datensatz meist gar
  keine `difficulty` (Beispiel unten: `difficulty=null`).
- `skitour-runs`: `has skitour`, gestrichelt `[3, 6]`.
- `other-runs`: `has other` — Sammeltopf für alles, was in keine der drei
  obigen Kategorien fällt (Rodelbahnen, Winterwanderwege, vermutlich auch
  `fatbike`/`ice_skate`/`playground`/`sleigh`/`snow_park`). Gestrichelt `[3, 3]`.

Bei Mehrfachnutzung (z.B. `uses=downhill,skitour`) zeichnet OpenSkiMap **mehrere
parallel versetzte Linien** (`line-offset`, eine pro zutreffender Kategorie),
statt wie bei uns eine Linie mit einer einzigen gewählten Farbe/Filterpriorität.

Zwei Lücken bei uns dadurch bestätigt:

1. **Rodelbahn nicht gestrichelt.** `feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`
   ("Gaisberg", `uses=sled`, sonst nichts) — bei uns aktuell im
   Alpine-Katalog (`uses NOT LIKE '%nordic%'`-Catchall), durchgezogen,
   Schwierigkeitsfarbe (meist grauer Fallback, da `difficulty` oft leer).
   Auf OpenSkiMap: `other`-Kategorie, gestrichelt `[3,3]`.
2. **Winterwanderweg nicht erkennbar.** `feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`
   ("Hannenkamm", `uses=hike`) — landet bei uns ebenfalls unmarkiert im
   Alpine-Katalog statt in `other`.

`uses` ist ein Mehrfachwert-Feld, volle Taxonomie im aktuellen Datensatz:
`downhill`, `nordic`, `skitour`, `hike`, `sled`, `connection`, `fatbike`,
`ice_skate`, `playground`, `sleigh`, `snow_park`. Bei Umsetzung klären, welche
davon OpenSkiMaps `other`-Bucket zugeordnet werden (vermutlich alle außer
downhill/nordic/skitour/connection).

Betrifft `scripts/convert.sh` (WHERE-Klauseln/Source-Layer neu denken - evtl.
weg vom reinen Alpine/Nordic-Split hin zu den vier echten Kategorien),
`styles/openskimap-style.json` (neue Layer-Gruppe(n)), `scripts/generate_layer_list.py`
(`GROUP_MAP` erweitern).

## Loipen (nordic) nicht nach Schwierigkeit einfärben

Siehe oben — OpenSkiMap färbt `nordic-runs` nicht nach Schwierigkeit
(nur casing-artiges Weiß/gelb bei `lit`). Wir haben in Task 6 die komplette
Alpine-Schwierigkeitsfarblogik 1:1 auf Nordic gespiegelt (`ski-runs-nordic-*`
in `styles/openskimap-style.json`) — das war laut echtem Stylesheet so nicht
vorgesehen. Beispiel: `feature_id=6a6a6f940d135a95cf034a6e7ca99563a5364bd0`
(`uses=nordic`, `difficulty=null`).

Hängt mit dem Punkt oben zusammen — beim Überarbeiten der Pisten-Kategorien
gleich mitentscheiden, ob/wie stark `ski-runs-nordic-line` etc. vereinfacht
werden.

## Versionierung & CHANGELOG.md einführen (oe5ith-coding-rules §4)
```

Mit dem Edit-Tool diesen kompletten Ausschnitt (beide Abschnitte inkl.
Überschriften, endend mit der `## Versionierung`-Überschrift als Anker)
ersetzen durch nur noch:
```
## Versionierung & CHANGELOG.md einführen (oe5ith-coding-rules §4)
```

- [ ] **Step 3: Beide Punkte an `docs/TODO_ARCHIVE.md` anhängen**

Mit dem Edit-Tool ans Ende von `docs/TODO_ARCHIVE.md` anhängen (nach dem
letzten bestehenden Eintrag "Ausrichtung der Sprites prüfen"):
```markdown

## Pisten-Kategorien: downhill / nordic / skitour / other statt nur alpine/nordic

*Erledigt: 2026-08-11 (Sub-Projekt B, Spec
`docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`,
Plan `docs/superpowers/plans/2026-08-11-run-category-taxonomy-plan.md`,
Commit `feat(style): replace alpine/nordic run split with downhill/nordic/skitour/other`)*

Echtes Stylesheet nutzte vier Kategorien pro Lauf-Feature (nicht zwei wie
unser bisheriger Alpine/Nordic-Split). Beide dokumentierten Lücken behoben:
Rodelbahn (`feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`, `uses=sled`)
und Winterwanderweg (`feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`,
`uses=hike`) landen jetzt beide sichtbar gestrichelt in der neuen
`other`-Kategorie statt unmarkiert im alten Alpine-Katalog. Mehrfachnutzung
mit parallel versetzten Linien (`line-offset`) bewusst nicht nachgebaut —
siehe `docs/ROADMAP.md`.

## Loipen (nordic) nicht nach Schwierigkeit einfärben

*Erledigt: 2026-08-11 (Sub-Projekt B, selber Commit wie oben)*

OpenSkiMap färbt `nordic-runs` nicht nach Schwierigkeit (nur casing-artiges
Weiß/gelb bei `lit`). Die 1:1 von Alpine gespiegelte Schwierigkeitsfarblogik
auf `ski-runs-nordic-*` wurde durch die `case lit`-Expression vom echten
Stylesheet ersetzt (Fill/Line/Ungroomed). Beispiel:
`feature_id=6a6a6f940d135a95cf034a6e7ca99563a5364bd0` (`uses=nordic`,
`difficulty=null`).
```

- [ ] **Step 4: Versionierungs-Hinweis in `docs/TODO.md` aktualisieren**

`old_string`:
```
Bewusst zurückgestellt (Entscheidung 2026-08-11): erst die übrigen offenen
Punkte in dieser Datei abarbeiten (Pisten-Kategorien, Nordic-Einfärbung —
`datetime.utcnow()`, Lift-Status, Sprite-Ausrichtung bereits erledigt,
siehe `docs/TODO_ARCHIVE.md`), danach daraus die erste Version schneiden
(Versionskonstante festlegen, `CHANGELOG.md` mit diesem Stand als erstem
Eintrag anlegen) statt jetzt schon rückwirkend eine Changelog-Historie zu
konstruieren. Reihenfolge: TODO-Punkte zuerst,
Versionierung/Changelog danach.
```
`new_string`:
```
Bewusst zurückgestellt (Entscheidung 2026-08-11): `docs/TODO.md` ist jetzt
leer (alle Punkte erledigt, siehe `docs/TODO_ARCHIVE.md`) — die erste
Version wird als Nächstes geschnitten (Versionskonstante festlegen,
`CHANGELOG.md` mit diesem Stand als erstem Eintrag anlegen).
```

- [ ] **Step 5: Commit**

```bash
git add docs/ROADMAP.md docs/TODO.md docs/TODO_ARCHIVE.md
git commit -m "$(cat <<'EOF'
docs: archive resolved run-category/nordic-coloring TODOs, add ROADMAP.md

docs/TODO.md is now empty (per oe5ith-coding-rules §3, resolved items move
to TODO_ARCHIVE.md instead of being deleted). Also introduces ROADMAP.md
(new features, as opposed to TODO.md's extensions of existing code) with
the line-offset multi-use rendering deferred in sub-project B's design.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: End-to-End-Verifikation gegen echte Daten

**Files:** keine (reine Verifikation, keine Code-Änderung)

**Interfaces:**
- Consumes: den committeten Stand aus Task 5/6.

- [ ] **Step 1: Vollen Build laufen lassen**

Run: `GEODATA_LOG_DIR=/tmp/run-taxonomy-verify ./run.sh 2>&1 | tail -30`
Expected: Läuft alle vier Phasen durch, endet mit `▶▶▶ BUILD ERFOLGREICH ABGESCHLOSSEN`. Dauert mehrere Minuten (Tippecanoe über den vollen Datensatz, inkl. Neu-Download-Check) — kein `timeout` mit kurzer Frist verwenden, im Hintergrund laufen lassen und auf tatsächliche Fertigstellung warten statt die Ausgabe abzuschneiden (bei einem vorherigen Sub-Projekt dieser Reihe hat ein Subagent genau diesen Fehler gemacht: Build im Hintergrund gestartet und die eigene Runde beendet, bevor er fertig war).

- [ ] **Step 2: `dist/layer-list.json` — vier Run-Gruppen mit korrekten Layer-Zahlen**

Run:
```bash
python3 -c "
import json
d = json.load(open('dist/layer-list.json'))
for s in d['styles']:
    for g in s['groups']:
        if g['template'].startswith('ski-runs'):
            print(g['template'], len(g['style_layers']))
"
```
Expected: `ski-runs-downhill 7`, `ski-runs-nordic 6`, `ski-runs-skitour 3`, `ski-runs-other 3`.

- [ ] **Step 3: Arbeitsverzeichnis sauber**

Run: `git status --short`
Expected: keine Ausgabe (working tree clean — Task 7 ändert keine Dateien).

Bei Erfolg ist Sub-Projekt B (letztes der Reihe D→A→C→B) abgeschlossen.

---

## Self-Review

**Spec coverage:** Alle neun Design-Entscheidungen aus der Spec sind umgesetzt: Priorität (Task 1), Layer-Umfang asymmetrisch (Task 2-4), `other`-Bucket via NOT-LIKE-Kette (Task 1), Fill für alle vier (Task 2-4), Nordic-Farbe `case lit` (Task 3), Dasharray/Breiten skitour/other (Task 4), Snowmaking nur downhill/nordic (kein Snowmaking-Layer für skitour/other in Task 4 — bewusst weggelassen), Roadmap-Eintrag (Task 6), TODO-Archivierung (Task 6). Verifikations-Abschnitt der Spec (JSON-Validität, validate_style.py, test_validate_style.py, Beispiel-Features, run.sh-Build) auf Task 1-7 verteilt.

**Placeholder-Scan:** Kein TBD/TODO. Jeder Edit-Step enthält vollständigen `old_string`/`new_string` — auch die sieben "reinen Umbenennungen" in Task 2 sind einzeln und vollständig ausgeschrieben, kein "analog zu oben"-Verweis ohne Code. Die einzige Stelle mit einem Verweis auf einen anderen Task (Task 3 Step 1's Hinweis auf die durch Task 2 bereits umbenannte Ankerzeile) benennt die exakte Zeile, kein vages "wie vorher".

**Typkonsistenz:** Layer-IDs zwischen Task 2/3/4 (Produzenten) und Task 5s `GROUP_MAP`/`KNOWN_SOURCE_LAYERS`-Edits (Konsumenten) stimmen exakt überein — gegengeprüft: 19 IDs in Task 2-4, 19 IDs in Task 5 Step 1, 8 `source-layer`-Namen in Task 1, 8 in Task 5 Step 2. Kategorisierungs-Prioritäts-Logik zwischen Spec, Task 1 (SQL) und Task 1 Step 4 (Verifikation) identisch.

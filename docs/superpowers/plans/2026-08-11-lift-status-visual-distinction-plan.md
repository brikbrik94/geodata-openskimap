# Lift-Status visuell unterscheiden (operating vs. other) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ski-lifts-*` Line-Layer in `styles/openskimap-style.json` visuell nach `status` (operating vs. alles andere) unterscheiden, wie im echten OpenSkiMap-Stylesheet, ohne den bestehenden `access=private`-Split zu verlieren.

**Architecture:** Die drei bestehenden Layer `ski-lifts-casing`/`ski-lifts-line`/`ski-lifts-line-private` werden durch fünf Layer ersetzt (Casing nur für `operating`, vier Line-Varianten für die Kreuzung `{public,private} × {operating,other}`). `scripts/generate_layer_list.py`s `GROUP_MAP` bekommt die zwei neuen Layer-IDs ergänzt, damit `generate_manifest.py` nicht mit `KeyError` abbricht.

**Tech Stack:** MapLibre-Style-JSON, Python 3 (`generate_layer_list.py`), Bash-Pipeline (`run.sh`).

## Global Constraints

Aus `docs/superpowers/specs/2026-08-11-lift-status-visual-distinction-design.md`:

- Casing (`ski-lifts-casing`) nur für `status == operating`, sonst unverändert.
- `ski-lifts-line` (public, operating): unverändert bis auf neuen Status-Filterteil + `line-opacity: 0.8`.
- `ski-lifts-line-other` (public, other): neu, `line-dasharray: [1, 3]`, `line-width`-Stops = bestehende Stops × 0.66 (6→0.53, 9→0.92, 12→1.45, 14→1.98), `line-opacity: 0.8`.
- `ski-lifts-line-private` (private, operating): unverändert bis auf neuen Status-Filterteil + `line-opacity: 0.8`; bestehendes `line-dasharray: [1, 2]` bleibt.
- `ski-lifts-line-private-other` (private, other): neu, `line-dasharray: [1, 3]` (Status-Dash gewinnt gegenüber Private-Dash), `line-width` × 0.66 wie oben, `line-opacity: 0.8`.
- `line-color` (`match` auf `status`) und `line-cap`/`line-join` bleiben in allen vier Line-Layern identisch zur bisherigen `ski-lifts-line`-Definition.
- `ski-lifts-labels`/`ski-lifts-icons` bleiben unverändert.
- `scripts/convert.sh` bleibt unverändert (keine neue Geometrie-Extraktion nötig).

---

### Task 1: `styles/openskimap-style.json` — fünf Layer statt drei

**Files:**
- Modify: `styles/openskimap-style.json:1255-1405` (der Block von `ski-lifts-casing` bis zum Ende von `ski-lifts-line-private`)

**Interfaces:**
- Produces: Layer-IDs `ski-lifts-casing`, `ski-lifts-line`, `ski-lifts-line-other`, `ski-lifts-line-private`, `ski-lifts-line-private-other` (alle `source-layer: "ski_lifts"`) — Task 2 konsumiert genau diese fünf IDs.

- [ ] **Step 1: Aktuellen Block lesen und Zeilengrenzen bestätigen**

Der zu ersetzende Block beginnt bei `styles/openskimap-style.json:1255` mit der Zeile `    {` (Start von `ski-lifts-casing`) und endet bei Zeile `1405` mit `    },` (Ende von `ski-lifts-line-private`, vor dem nächsten Layer `ski-areas-alpine-labels`). Mit dem Read-Tool `styles/openskimap-style.json` ab Zeile 1250 lesen und bestätigen, dass Zeile 1255 `"id": "ski-lifts-casing"` und Zeile 1406 `"id": "ski-areas-alpine-labels"` enthält, bevor der Ersetzung erfolgt (Datei kann sich seit Planerstellung nicht mehr verändert haben, aber sicherheitshalber prüfen).

- [ ] **Step 2: Block ersetzen**

Mit dem Edit-Tool den kompletten Block von Zeile 1255 (`    {`) bis Zeile 1405 (`    },`) — exakter `old_string` ist der aktuelle Inhalt dieser Zeilen (drei Layer-Objekte `ski-lifts-casing`, `ski-lifts-line`, `ski-lifts-line-private`) — durch folgenden `new_string` ersetzen:

```json
    {
      "id": "ski-lifts-casing",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": "hsl(0, 0%, 100%)",
        "line-width": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          6,
          1.8,
          9,
          2.8,
          12,
          4.0,
          14,
          5.0
        ]
      },
      "filter": [
        "==",
        [
          "get",
          "status"
        ],
        "operating"
      ]
    },
    {
      "id": "ski-lifts-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "match",
          [
            "get",
            "status"
          ],
          "operating",
          "hsl(0, 82%, 42%)",
          "proposed",
          "hsl(0, 82%, 42%)",
          "planned",
          "hsl(0, 82%, 42%)",
          "construction",
          "hsl(0, 82%, 42%)",
          "disused",
          "hsl(0, 53%, 42%)",
          "abandoned",
          "hsl(0, 53%, 42%)",
          "hsl(0, 53%, 42%)"
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
        "line-opacity": 0.8
      },
      "filter": [
        "all",
        [
          "!=",
          [
            "get",
            "access"
          ],
          "private"
        ],
        [
          "==",
          [
            "get",
            "status"
          ],
          "operating"
        ]
      ]
    },
    {
      "id": "ski-lifts-line-other",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "match",
          [
            "get",
            "status"
          ],
          "operating",
          "hsl(0, 82%, 42%)",
          "proposed",
          "hsl(0, 82%, 42%)",
          "planned",
          "hsl(0, 82%, 42%)",
          "construction",
          "hsl(0, 82%, 42%)",
          "disused",
          "hsl(0, 53%, 42%)",
          "abandoned",
          "hsl(0, 53%, 42%)",
          "hsl(0, 53%, 42%)"
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
          0.53,
          9,
          0.92,
          12,
          1.45,
          14,
          1.98
        ],
        "line-opacity": 0.8,
        "line-dasharray": [
          "literal",
          [
            1,
            3
          ]
        ]
      },
      "filter": [
        "all",
        [
          "!=",
          [
            "get",
            "access"
          ],
          "private"
        ],
        [
          "!=",
          [
            "get",
            "status"
          ],
          "operating"
        ]
      ]
    },
    {
      "id": "ski-lifts-line-private",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "match",
          [
            "get",
            "status"
          ],
          "operating",
          "hsl(0, 82%, 42%)",
          "proposed",
          "hsl(0, 82%, 42%)",
          "planned",
          "hsl(0, 82%, 42%)",
          "construction",
          "hsl(0, 82%, 42%)",
          "disused",
          "hsl(0, 53%, 42%)",
          "abandoned",
          "hsl(0, 53%, 42%)",
          "hsl(0, 53%, 42%)"
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
        "line-opacity": 0.8,
        "line-dasharray": [
          "literal",
          [
            1,
            2
          ]
        ]
      },
      "filter": [
        "all",
        [
          "==",
          [
            "get",
            "access"
          ],
          "private"
        ],
        [
          "==",
          [
            "get",
            "status"
          ],
          "operating"
        ]
      ]
    },
    {
      "id": "ski-lifts-line-private-other",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "layout": {
        "line-cap": "round",
        "line-join": "round"
      },
      "paint": {
        "line-color": [
          "match",
          [
            "get",
            "status"
          ],
          "operating",
          "hsl(0, 82%, 42%)",
          "proposed",
          "hsl(0, 82%, 42%)",
          "planned",
          "hsl(0, 82%, 42%)",
          "construction",
          "hsl(0, 82%, 42%)",
          "disused",
          "hsl(0, 53%, 42%)",
          "abandoned",
          "hsl(0, 53%, 42%)",
          "hsl(0, 53%, 42%)"
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
          0.53,
          9,
          0.92,
          12,
          1.45,
          14,
          1.98
        ],
        "line-opacity": 0.8,
        "line-dasharray": [
          "literal",
          [
            1,
            3
          ]
        ]
      },
      "filter": [
        "all",
        [
          "==",
          [
            "get",
            "access"
          ],
          "private"
        ],
        [
          "!=",
          [
            "get",
            "status"
          ],
          "operating"
        ]
      ]
    },
```

- [ ] **Step 3: JSON-Syntax prüfen**

Run: `python3 -c "import json; json.load(open('styles/openskimap-style.json')); print('valid JSON')"`
Expected: `valid JSON` (kein Traceback)

- [ ] **Step 4: Fail-Fast-Guard bestätigen (erwarteter Fehler, GROUP_MAP noch nicht aktualisiert)**

Run: `python3 scripts/generate_manifest.py 2>&1 | tail -5`
Expected: Abbruch mit `KeyError` und der Meldung `style layer 'ski-lifts-line-other' has no entry in GROUP_MAP` (oder `ski-lifts-line-private-other`, je nach Layer-Reihenfolge im Style — beide sind zu diesem Zeitpunkt nicht in `GROUP_MAP`). Dieser Fehler ist zu diesem Zeitpunkt **erwartet** — er bestätigt, dass der bestehende Fail-Fast-Mechanismus in `generate_layer_list.py` die neuen Layer-IDs korrekt erkennt. Kein Commit in diesem Task — der Build ist absichtlich noch rot, Task 2 macht ihn grün.

---

### Task 2: `scripts/generate_layer_list.py` — `GROUP_MAP` ergänzen

**Files:**
- Modify: `scripts/generate_layer_list.py:66-70`

**Interfaces:**
- Consumes: Layer-IDs aus Task 1 (`ski-lifts-line-other`, `ski-lifts-line-private-other`).
- Produces: `GROUP_MAP["ski-lifts-line-other"] == "ski-lifts"`, `GROUP_MAP["ski-lifts-line-private-other"] == "ski-lifts"` — beide fallen in dieselbe Gruppe wie die bestehenden Lift-Layer, damit `dist/layer-list.json` weiterhin genau eine `ski-lifts`-Gruppe hat.

- [ ] **Step 1: Aktuellen `GROUP_MAP`-Ausschnitt bestätigen**

`scripts/generate_layer_list.py:66-70` enthält aktuell:

```python
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
```

- [ ] **Step 2: Zwei neue Einträge ergänzen**

Mit dem Edit-Tool `old_string`:

```python
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
```

durch `new_string`:

```python
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-other": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-line-private-other": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
```

ersetzen.

- [ ] **Step 3: Fail-Fast-Guard jetzt grün — Manifest-Generierung läuft durch**

Run: `python3 scripts/generate_manifest.py 2>&1 | tail -10`
Expected: Kein `KeyError` mehr, Ausgabe endet mit `✔ Layer-list saved to: .../dist/layer-list.json (6 Gruppen)` (weiterhin 6 Gruppen — `ski-lifts` bleibt eine Gruppe, nur mit mehr `style_layers`/`source_layers`-Einträgen).

- [ ] **Step 4: `ski-lifts`-Gruppe in `dist/layer-list.json` inspizieren**

Run:
```bash
python3 -c "
import json
d = json.load(open('dist/layer-list.json'))
for s in d['styles']:
    for g in s['groups']:
        if g['template'] == 'ski-lifts':
            print(sorted(g['style_layers']))
"
```
Expected: `['ski-lifts-casing', 'ski-lifts-icons', 'ski-lifts-labels', 'ski-lifts-line', 'ski-lifts-line-other', 'ski-lifts-line-private', 'ski-lifts-line-private-other']` (alle sieben Style-Layer der Gruppe, inklusive der beiden neuen).

- [ ] **Step 5: Bestehende Style-Tests laufen lassen**

Run: `python3 scripts/test_validate_style.py`
Expected: `OK` (alle 7 Tests grün, unverändert — diese Tests prüfen generisches `validate()`-Verhalten, nicht layerspezifisch).

- [ ] **Step 6: `validate_style.py` gegen den echten Style laufen lassen**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 7: Commit**

```bash
git add styles/openskimap-style.json scripts/generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(style): distinguish lift status (operating vs. other) visually

Splits ski-lifts-casing/ski-lifts-line/ski-lifts-line-private into five
layers so non-operating lifts (proposed/planned/construction/disused/
abandoned) render thin and dashed instead of identical to operating lifts,
matching the real OpenSkiMap stylesheet. The pre-existing access=private
split is kept and combined with the new status split (4 line-layer
combinations); casing is now operating-only. See
docs/superpowers/specs/2026-08-11-lift-status-visual-distinction-design.md
for the full design and the decisions behind the dash/width/opacity values.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: End-to-End-Verifikation gegen echte Daten

**Files:** keine (reine Verifikation, keine Code-Änderung)

**Interfaces:**
- Consumes: Den committeten Stand aus Task 2.

- [ ] **Step 1: Vollen Build laufen lassen**

Run: `GEODATA_LOG_DIR=/tmp/lift-status-verify ./run.sh 2>&1 | tail -30`
Expected: Läuft alle vier Phasen durch, endet mit `▶▶▶ BUILD ERFOLGREICH ABGESCHLOSSEN`. (Hinweis: `run.sh` lädt bei Bedarf erneut das ~400 MB GeoPackage und braucht für `tippecanoe` mehrere Minuten — kein `timeout` mit kurzer Frist verwenden, siehe Erfahrung aus der `update.sh`/`run.sh`-Restrukturierung.)

- [ ] **Step 2: Beispiel-Feature aus der TODO-Notiz gegen die neue Filterlogik prüfen**

Die TODO-Notiz nennt `feature_id=84b8d675587243994b24ee9b7e0aa4629a6e54f6` ("Steyrsbergerreithbahn", `status=proposed`). Property-Werte aus der Quelle abfragen:

Run: `ogrinfo -al -where "feature_id='84b8d675587243994b24ee9b7e0aa4629a6e54f6'" data/src/openskidata.gpkg lifts_linestring 2>/dev/null | grep -E "feature_id|status|access|lift_type"`
Expected: `status (String) = proposed`, `access (String) = (null)`.

Mit `access = (null)` matcht die Filterbedingung `["!=", ["get","access"], "private"]` (fehlende Property → `get` liefert `null`, `null != "private"` ist wahr) — das Feature fällt also in den **public**-Zweig. Mit `status = proposed` (≠ `operating`) fällt es in den **other**-Zweig. Erwartung: Das Feature matcht die Filterbedingung von `ski-lifts-line-other`, nicht von `ski-lifts-line`, `ski-lifts-line-private` oder `ski-lifts-line-private-other`. Das lässt sich ohne Vector-Tile-Decoding rein durch Nachvollziehen der Filterlogik in Schritt 2 bestätigen — kein weiterer Bash-Befehl nötig.

- [ ] **Step 3: Kein Cleanup-Commit nötig**

Task 3 ändert keine Dateien — nichts zu committen. Bei Erfolg ist Teilprojekt A (Lift-Status) abgeschlossen.

---

## Self-Review

**Spec coverage:** Alle 5 Design-Entscheidungen aus der Spec (Private-Split behalten, Casing nur operating, Breitenfaktor auf bestehende Kurve, Opacity 0.8 für beide, Status-Dash gewinnt bei other+private) sind in Task 1 als konkrete JSON-Werte umgesetzt. `GROUP_MAP`-Ergänzung (Spec-Abschnitt "Betroffene Dateien") ist Task 2. Verifikations-Abschnitt der Spec (validate_style.py, test_validate_style.py, run.sh-Build, Beispiel-Feature) ist auf Task 2/3 verteilt. Keine Lücke gefunden.

**Placeholder-Scan:** Kein TBD/TODO, jeder Step enthält konkreten Befehl oder vollständigen JSON-/Python-Code, keine "ähnlich wie oben"-Verweise (die vier Line-Layer-Blöcke sind jeweils vollständig ausgeschrieben, nicht referenziert).

**Typkonsistenz:** Layer-IDs zwischen Task 1 (`ski-lifts-line-other`, `ski-lifts-line-private-other`) und Task 2 (`GROUP_MAP`-Keys) stimmen exakt überein. Zeilennummern (1255-1405, 66-70) wurden gegen den aktuellen Dateistand verifiziert.

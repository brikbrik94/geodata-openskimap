# Symbol Rotation-Alignment Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the rotation/orientation behavior of line-placed symbols in `styles/openskimap-style.json` — lift icons should stay upright regardless of line bearing, and run/lift text labels should never render upside-down.

**Architecture:** Four isolated property edits across four existing `symbol`-type layers in one JSON file. No new layers, no new source-layer references, no changes to `convert.sh` or `generate_layer_list.py`.

**Tech Stack:** MapLibre-Style-JSON.

## Global Constraints

Aus `docs/superpowers/specs/2026-08-11-symbol-rotation-alignment-design.md`:

- `ski-lifts-icons`: `icon-rotation-alignment: "viewport"` neu ergänzen. `symbol-placement: "line"` und `symbol-spacing: 150` bleiben unverändert.
- `ski-runs-alpine-labels`, `ski-runs-nordic-labels`, `ski-lifts-labels`: `text-keep-upright` von `false` auf `true`. `text-rotation-alignment: "map"` bleibt unverändert.
- `assets/sprites/openskimap/*`, `scripts/convert.sh`, `scripts/generate_layer_list.py` bleiben unangetastet.

---

### Task 1: Vier Rotation-/Ausrichtungs-Properties in `styles/openskimap-style.json` fixen

**Files:**
- Modify: `styles/openskimap-style.json:1667-1699` (`ski-runs-alpine-labels`)
- Modify: `styles/openskimap-style.json:1796-1828` (`ski-runs-nordic-labels`)
- Modify: `styles/openskimap-style.json:1925-1971` (`ski-lifts-labels`)
- Modify: `styles/openskimap-style.json:1989-1992` (`ski-lifts-icons`)

**Interfaces:** Keine — reine Property-Wertänderungen an bestehenden Layern, keine neuen/umbenannten IDs, nichts, was eine andere Datei konsumiert oder produziert.

Die drei Label-Layer-Blöcke sind rund um `text-keep-upright` textuell identisch — jede Ersetzung unten beginnt deshalb bei der jeweils eindeutigen `"id"`-Zeile des Layers, damit der `old_string` im Edit-Tool eindeutig im Dokument ist.

- [ ] **Step 1: `ski-runs-alpine-labels` — `text-keep-upright` auf `true`**

Mit dem Edit-Tool `old_string`:
```json
      "id": "ski-runs-alpine-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
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
        "text-keep-upright": false,
```
ersetzen durch `new_string` (identisch, nur letzte Zeile geändert):
```json
      "id": "ski-runs-alpine-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine_line",
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
```

- [ ] **Step 2: `ski-runs-nordic-labels` — `text-keep-upright` auf `true`**

Mit dem Edit-Tool `old_string`:
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
        "text-keep-upright": false,
```
ersetzen durch `new_string` (identisch, nur letzte Zeile geändert):
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
```

- [ ] **Step 3: `ski-lifts-labels` — `text-keep-upright` auf `true`**

Mit dem Edit-Tool `old_string`:
```json
      "id": "ski-lifts-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "minzoom": 13,
      "filter": [
        "any",
        [
          "has",
          "name"
        ],
        [
          "has",
          "ref"
        ]
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "coalesce",
          [
            "get",
            "name"
          ],
          [
            "get",
            "ref"
          ]
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
        "text-keep-upright": false,
```
ersetzen durch `new_string` (identisch, nur letzte Zeile geändert):
```json
      "id": "ski-lifts-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "minzoom": 13,
      "filter": [
        "any",
        [
          "has",
          "name"
        ],
        [
          "has",
          "ref"
        ]
      ],
      "layout": {
        "symbol-placement": "line",
        "text-field": [
          "coalesce",
          [
            "get",
            "name"
          ],
          [
            "get",
            "ref"
          ]
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
```

- [ ] **Step 4: `ski-lifts-icons` — `icon-rotation-alignment: "viewport"` ergänzen**

Mit dem Edit-Tool `old_string`:
```json
      "layout": {
        "symbol-placement": "line",
        "symbol-spacing": 150,
        "icon-image": [
```
ersetzen durch `new_string`:
```json
      "layout": {
        "symbol-placement": "line",
        "symbol-spacing": 150,
        "icon-rotation-alignment": "viewport",
        "icon-image": [
```

- [ ] **Step 5: JSON-Syntax prüfen**

Run: `python3 -c "import json; json.load(open('styles/openskimap-style.json')); print('valid JSON')"`
Expected: `valid JSON`

- [ ] **Step 6: Gezielte Property-Prüfung (alle vier Layer in einem Durchlauf)**

Run:
```bash
python3 -c "
import json
d = json.load(open('styles/openskimap-style.json'))
by_id = {l['id']: l for l in d['layers']}
checks = [
    ('ski-lifts-icons', 'icon-rotation-alignment', 'viewport'),
    ('ski-runs-alpine-labels', 'text-keep-upright', True),
    ('ski-runs-nordic-labels', 'text-keep-upright', True),
    ('ski-lifts-labels', 'text-keep-upright', True),
]
ok = True
for layer_id, prop, expected in checks:
    actual = by_id[layer_id]['layout'].get(prop)
    status = 'OK' if actual == expected else 'MISMATCH'
    if actual != expected:
        ok = False
    print(f'{status}: {layer_id}.{prop} = {actual!r} (expected {expected!r})')
print('ALL OK' if ok else 'FAILURES PRESENT')
"
```
Expected: alle vier Zeilen `OK: ...`, letzte Zeile `ALL OK`.

- [ ] **Step 7: Bestehende Style-Tests laufen lassen**

Run: `python3 scripts/test_validate_style.py`
Expected: `OK` (alle 7 Tests grün, unverändert).

- [ ] **Step 8: `validate_style.py` gegen den echten Style laufen lassen**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 9: Commit**

```bash
git add styles/openskimap-style.json
git commit -m "$(cat <<'EOF'
fix(style): keep lift icons upright and run/lift labels right-side-up

ski-lifts-icons had no icon-rotation-alignment, so the spec default
("auto") resolved to "map" for symbol-placement: "line" — icons rotated
to match each lift segment's bearing even though the sprites are static,
non-directional front-view pictograms. Sets icon-rotation-alignment:
"viewport" so icons stay upright regardless of line direction.

ski-runs-alpine-labels/ski-runs-nordic-labels/ski-lifts-labels had
text-keep-upright: false with no documented rationale (git log -S found
no explaining commit message), diverging from both the MapLibre default
(true) and the real OpenSkiMap stylesheet's analogous line-placed text
layer (which doesn't override it). Flips it to true so labels can no
longer render upside-down. text-rotation-alignment: "map" is unchanged —
labels still follow the line contour.

See docs/superpowers/specs/2026-08-11-symbol-rotation-alignment-design.md
for the full investigation and design.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: End-to-End-Verifikation gegen echte Daten

**Files:** keine (reine Verifikation, keine Code-Änderung)

**Interfaces:**
- Consumes: Den committeten Stand aus Task 1.

- [ ] **Step 1: Vollen Build laufen lassen**

Run: `GEODATA_LOG_DIR=/tmp/symbol-rotation-verify ./run.sh 2>&1 | tail -30`
Expected: Läuft alle vier Phasen durch, endet mit `▶▶▶ BUILD ERFOLGREICH ABGESCHLOSSEN`. (`run.sh` braucht für `tippecanoe` mehrere Minuten — kein `timeout` mit kurzer Frist verwenden; im Hintergrund laufen lassen und auf Fertigstellung warten statt die Ausgabe abzuschneiden.)

- [ ] **Step 2: Kein Cleanup-Commit nötig**

Task 2 ändert keine Dateien — nichts zu committen. Bei Erfolg ist Teilprojekt C (Sprite-/Label-Ausrichtung) abgeschlossen.

---

## Self-Review

**Spec coverage:** Beide Design-Entscheidungen (icon-rotation-alignment auf ski-lifts-icons, text-keep-upright auf den drei Label-Layern) sind in Task 1 als konkrete, vollständig ausgeschriebene old_string/new_string-Blöcke umgesetzt. Verifikations-Abschnitt der Spec (JSON-Validität, validate_style.py, test_validate_style.py, gezielte Property-Prüfung, run.sh-Build) ist auf Task 1/2 verteilt. Keine Lücke gefunden.

**Placeholder-Scan:** Erste Fassung von Steps 1-3 beschrieb nur eine Disambiguierungs-Strategie in Prosa statt exaktem `old_string`/`new_string` — beim Self-Review als Verstoß gegen "Steps that describe what to do without showing how" erkannt und durch die drei vollständig ausgeschriebenen, je bei der eindeutigen `id`-Zeile beginnenden Blöcke ersetzt. Jetzt kein TBD/TODO, kein "ähnlich wie oben"-Verweis mehr.

**Typkonsistenz:** Property-Namen (`icon-rotation-alignment`, `text-keep-upright`) und Layer-IDs zwischen Spec, Task-1-Steps und der Verifikations-Prüfung in Step 6 stimmen exakt überein. Zeilennummern und Blockinhalte gegen den aktuellen Dateistand verifiziert (1667-1699, 1796-1828, 1925-1971, 1989-1992).

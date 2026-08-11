# OpenSkiMap Style Adoption & Layer Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `geodata-openskimap`'s flat, geometry-fragmented tippecanoe layers and hand-rolled style with a 6-layer, activity-split (alpine/nordic) vector tile structure and a MapLibre style that reproduces OpenSkiMap's own difficulty/status color language, using only our own sprite set.

**Architecture:** `scripts/convert.sh` extracts and activity-filters the 6 GeoPackage source tables into 6 merged GeoJSONSeq streams, then tippecanoe packages them as 6 independently-toggleable vector-tile source-layers. `styles/openskimap-style.json` is rewritten against those 6 source-layers, porting OpenSkiMap's published difficulty/status color tables (from `openskidata-format`) as static MapLibre expressions. A new `scripts/validate_style.py` statically checks that every `source-layer` and `icon-image` reference in the style actually resolves, catching typos before a full tippecanoe/tile round-trip is needed.

**Tech Stack:** bash (`set -euo pipefail`), GDAL `ogr2ogr`, `tippecanoe`, Python 3 stdlib only (`json`, `unittest` — no new pip dependencies), MapLibre GL style spec v8.

## Global Constraints

- Only attributes already verified present in `data/src/openskidata.gpkg` may be referenced in filters/expressions (verified via `ogrinfo`/`ogr2ogr -sql` during design — see spec). No invented properties.
- Only icon names already present in `assets/sprites/openskimap/sprite.json` may be used in `icon-image`. No new sprite assets in this plan.
- No new runtime dependencies — stdlib Python only, no `pip install`, consistent with `DEPENDENCIES.md` ("Python 3 ... im Haupt-Workflow noch nicht aktiv genutzt" is superseded by this plan making light, dependency-free use of it).
- Exactly six `source-layer` values are valid anywhere in the style: `ski_areas_alpine`, `ski_areas_nordic`, `ski_runs_alpine`, `ski_runs_nordic`, `ski_lifts`, `ski_spots`.
- Spec: `docs/superpowers/specs/2026-08-10-openskimap-style-layer-consolidation-design.md` — every task below implements a section of it.

---

### Task 1: Data layer consolidation in `scripts/convert.sh`

**Files:**
- Modify: `scripts/convert.sh` (full replacement of the extraction/tippecanoe body)

**Interfaces:**
- Consumes: `data/src/openskidata.gpkg` (6 tables: `ski_areas_point`, `ski_areas_multipolygon`, `lifts_linestring`, `runs_linestring`, `runs_multipolygon`, `spots_point`), `scripts/ci/utils.sh` (`log_header`/`log_info`/`log_error`/`log_success`, `get_rel_path`) — unchanged interface, already sourced by the existing script.
- Produces: `work/openskimap.pmtiles` containing exactly 6 vector-tile source-layers: `ski_areas_alpine`, `ski_areas_nordic`, `ski_runs_alpine`, `ski_runs_nordic`, `ski_lifts`, `ski_spots`. Task 3–6 (the style) depend on these exact names.

- [ ] **Step 1: Replace the body of `scripts/convert.sh`**

Replace the entire file with:

```bash
#!/bin/bash
set -euo pipefail

# 1. CI Utils laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    echo "❌ Fehler: scripts/ci/utils.sh nicht gefunden!"
    exit 1
fi

log_header "CONVERT: OPENSKIMAP -> PMTILES"

BASE_DIR="$REPO_DIR"
SRC_DIR="$BASE_DIR/data/src"
TMP_DIR="$BASE_DIR/work"

INPUT_FILE="$SRC_DIR/openskidata.gpkg"
OUTPUT_PMTILES="$TMP_DIR/openskimap.pmtiles"

if [ ! -f "$INPUT_FILE" ]; then
    log_error "Eingabedatei nicht gefunden: $INPUT_FILE"
    exit 1
fi

mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

log_info "Extrahiere Layer aus GeoPackage..."

# Ski-Gebiete: nach 'activities' in Alpine/Nordic aufgeteilt.
# Gemischte Gebiete (activities="downhill,nordic") landen in beiden Layern.
ALPINE_AREA_WHERE="activities LIKE '%downhill%' OR activities NOT LIKE '%nordic%'"
NORDIC_AREA_WHERE="activities LIKE '%nordic%'"

ogr2ogr -f GeoJSONSeq areas_point_alpine.jsonseq "$INPUT_FILE" ski_areas_point -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq areas_poly_alpine.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq areas_point_nordic.jsonseq "$INPUT_FILE" ski_areas_point -where "$NORDIC_AREA_WHERE"
ogr2ogr -f GeoJSONSeq areas_poly_nordic.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$NORDIC_AREA_WHERE"
cat areas_point_alpine.jsonseq areas_poly_alpine.jsonseq > ski_areas_alpine.jsonseq
cat areas_point_nordic.jsonseq areas_poly_nordic.jsonseq > ski_areas_nordic.jsonseq

# Pisten/Loipen: nach 'uses' in Alpine/Nordic aufgeteilt.
# Gemischte Nutzung (uses="downhill,nordic") landet in beiden Layern; alles was
# nicht explizit nordic ist (downhill, skitour, connection, sled, hike, ...)
# faellt in den Alpine-Layer.
ALPINE_RUN_WHERE="uses LIKE '%downhill%' OR uses NOT LIKE '%nordic%'"
NORDIC_RUN_WHERE="uses LIKE '%nordic%'"

ogr2ogr -f GeoJSONSeq runs_line_alpine.jsonseq "$INPUT_FILE" runs_linestring -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq runs_poly_alpine.jsonseq "$INPUT_FILE" runs_multipolygon -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq runs_line_nordic.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq runs_poly_nordic.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
cat runs_line_alpine.jsonseq runs_poly_alpine.jsonseq > ski_runs_alpine.jsonseq
cat runs_line_nordic.jsonseq runs_poly_nordic.jsonseq > ski_runs_nordic.jsonseq

# Lifte: unveraendert, ein Layer
ogr2ogr -f GeoJSONSeq ski_lifts.jsonseq "$INPUT_FILE" lifts_linestring

# Spots: neu (Liftstationen, Halfpipes, Lawinen-Checkpunkte, Kreuzungen)
ogr2ogr -f GeoJSONSeq ski_spots.jsonseq "$INPUT_FILE" spots_point

log_info "Erstelle PMTiles: $(get_rel_path "$OUTPUT_PMTILES" "$REPO_DIR")"

tippecanoe -o "$OUTPUT_PMTILES" --force \
  --minimum-zoom=0 --maximum-zoom=14 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  -L "ski_areas_alpine:ski_areas_alpine.jsonseq" \
  -L "ski_areas_nordic:ski_areas_nordic.jsonseq" \
  -L "ski_runs_alpine:ski_runs_alpine.jsonseq" \
  -L "ski_runs_nordic:ski_runs_nordic.jsonseq" \
  -L "ski_lifts:ski_lifts.jsonseq" \
  -L "ski_spots:ski_spots.jsonseq"

log_info "Bereinige temporäre JSON-Dateien..."
rm -f *.jsonseq

log_success "OpenSkimap PMTiles erfolgreich erstellt."
```

- [ ] **Step 2: Run the conversion end-to-end**

Run: `bash scripts/convert.sh`

This requires `data/src/openskidata.gpkg` to already exist (it does — confirmed present, ~404MB) and `aria2c`/`ogr2ogr`/`tippecanoe` to be installed (confirmed present). Expect it to take a few minutes (six `ogr2ogr` extractions plus one `tippecanoe` build over ~227k run features and ~34k spot features). Expected: exits 0, ends with `OpenSkimap PMTiles erfolgreich erstellt.`, and `work/openskimap.pmtiles` exists with no leftover `*.jsonseq` files in `work/`.

- [ ] **Step 3: Verify the 6 source-layers exist**

Run: `pmtiles show --metadata work/openskimap.pmtiles | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(l['id'] for l in d['vector_layers']))"`

Expected output:
```
['ski_areas_alpine', 'ski_areas_nordic', 'ski_lifts', 'ski_runs_alpine', 'ski_runs_nordic', 'ski_spots']
```

- [ ] **Step 4: Sanity-check the alpine/nordic split has plausible, non-zero counts on both sides**

Run: `ogrinfo -so work/openskimap.pmtiles ski_runs_alpine | grep "Feature Count"` and the same for `ski_runs_nordic`, `ski_areas_alpine`, `ski_areas_nordic`.

Expected: all four report a non-zero feature count (this is a GDAL PMTiles-driver estimate, not an exact source count — just confirms neither split is empty and alpine dominates globally, which is expected given the dataset's global mix of resorts).

- [ ] **Step 5: Commit**

```bash
git add scripts/convert.sh
git commit -m "$(cat <<'EOF'
feat: consolidate tippecanoe layers into alpine/nordic-split concepts

Replaces the 5 geometry-fragmented source-layers with 6 concept-based
ones (ski_areas_alpine/nordic, ski_runs_alpine/nordic, ski_lifts,
ski_spots), matching upstream OpenSkiMap's own layer grouping and
making alpine vs. nordic independently toggleable downstream.
EOF
)"
```

---

### Task 2: `scripts/validate_style.py` — static style/sprite checker

**Files:**
- Create: `scripts/validate_style.py`
- Create: `scripts/test_validate_style.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure, standalone).
- Produces: `collect_icon_names(expr) -> set[str]` and `validate(style_path: str, sprite_path: str) -> list[str]` (importable from `scripts/validate_style.py`), plus a CLI: `python3 scripts/validate_style.py <style.json> <sprite.json>` exits 0 if clean, 1 if problems were found and prints them, 2 on usage error. Tasks 3–7 use this CLI to verify each increment of `styles/openskimap-style.json`.

- [ ] **Step 1: Write the failing test file**

Create `scripts/test_validate_style.py`:

```python
import json
import os
import tempfile
import unittest

from validate_style import collect_icon_names, validate


class CollectIconNamesTests(unittest.TestCase):
    def test_plain_string(self):
        self.assertEqual(collect_icon_names("ski-gondola"), {"ski-gondola"})

    def test_match_expression_outputs_only(self):
        expr = [
            "match", ["get", "lift_type"],
            "gondola", "ski-gondola",
            "cable_car", "ski-cable-car",
            "ski-gondola",
        ]
        self.assertEqual(collect_icon_names(expr), {"ski-gondola", "ski-cable-car"})
        # match *values* like "gondola"/"cable_car" must NOT be collected
        self.assertNotIn("gondola", collect_icon_names(expr))
        self.assertNotIn("cable_car", collect_icon_names(expr))

    def test_nested_case_inside_match_output(self):
        expr = [
            "match", ["get", "lift_type"],
            "chair_lift", [
                "case",
                ["==", ["get", "occupancy"], 2], "ski-chairlift-2",
                "ski-chairlift-1",
            ],
            "ski-gondola",
        ]
        self.assertEqual(
            collect_icon_names(expr),
            {"ski-chairlift-2", "ski-chairlift-1", "ski-gondola"},
        )

    def test_dynamic_expression_not_collected(self):
        expr = ["concat", "oneway-", ["to-string", ["get", "colorName"]]]
        self.assertEqual(collect_icon_names(expr), set())


class ValidateTests(unittest.TestCase):
    def _write_json(self, tmpdir, name, data):
        path = os.path.join(tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_unknown_source_layer_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {"layers": [{"id": "bad", "source-layer": "not_a_real_layer"}]}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", {})
            problems = validate(style_path, sprite_path)
            self.assertEqual(len(problems), 1)
            self.assertIn("not_a_real_layer", problems[0])

    def test_known_source_layer_and_icon_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {
                "layers": [
                    {
                        "id": "lifts-icons",
                        "source-layer": "ski_lifts",
                        "layout": {"icon-image": "ski-gondola"},
                    }
                ]
            }
            sprite = {"ski-gondola": {}}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", sprite)
            problems = validate(style_path, sprite_path)
            self.assertEqual(problems, [])

    def test_missing_icon_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {
                "layers": [
                    {
                        "id": "lifts-icons",
                        "source-layer": "ski_lifts",
                        "layout": {"icon-image": "does-not-exist"},
                    }
                ]
            }
            sprite = {"ski-gondola": {}}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", sprite)
            problems = validate(style_path, sprite_path)
            self.assertEqual(len(problems), 1)
            self.assertIn("does-not-exist", problems[0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to confirm it fails (module doesn't exist yet)**

Run: `cd scripts && python3 -m unittest test_validate_style -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate_style'`

- [ ] **Step 3: Write the minimal implementation**

Create `scripts/validate_style.py`:

```python
#!/usr/bin/env python3
"""Validates a MapLibre style against a sprite sheet:
- every layer's source-layer must be one of the known consolidated layers
- every icon-image reference must resolve to a name present in the sprite

Usage: validate_style.py <style.json> <sprite.json>
Exit code 0 if valid, 1 if problems were found, 2 on usage error.
"""
import json
import sys

KNOWN_SOURCE_LAYERS = {
    "ski_areas_alpine",
    "ski_areas_nordic",
    "ski_runs_alpine",
    "ski_runs_nordic",
    "ski_lifts",
    "ski_spots",
}


def collect_icon_names(expr):
    """Collect string literals that occur in icon-name *output* position of a
    MapLibre expression: a plain string, or the outputs/fallback of a
    match/case/coalesce expression. Match *values* and case *conditions* are
    not icon names and are intentionally skipped. Other expression heads
    (get, concat, interpolate, ...) are dynamic and not statically checkable,
    so they contribute no names (under-approximation, never a false positive).
    """
    names = set()
    if isinstance(expr, str):
        names.add(expr)
        return names
    if not isinstance(expr, list) or not expr:
        return names

    op = expr[0]
    if op in ("match", "case"):
        rest = expr[2:] if op == "match" else expr[1:]
        has_fallback = len(rest) % 2 == 1
        fallback = rest[-1] if has_fallback else None
        pairs = rest[:-1] if has_fallback else rest
        for i in range(1, len(pairs), 2):
            names |= collect_icon_names(pairs[i])
        if fallback is not None:
            names |= collect_icon_names(fallback)
    elif op == "coalesce":
        for item in expr[1:]:
            names |= collect_icon_names(item)

    return names


def validate(style_path, sprite_path):
    with open(style_path, encoding="utf-8") as f:
        style = json.load(f)
    with open(sprite_path, encoding="utf-8") as f:
        sprite = json.load(f)

    sprite_names = set(sprite.keys())
    problems = []

    for layer in style.get("layers", []):
        source_layer = layer.get("source-layer")
        if source_layer is not None and source_layer not in KNOWN_SOURCE_LAYERS:
            problems.append(
                f"layer '{layer.get('id')}': unknown source-layer '{source_layer}'"
            )

        icon_image = layer.get("layout", {}).get("icon-image")
        if icon_image is not None:
            for name in collect_icon_names(icon_image):
                if name not in sprite_names:
                    problems.append(
                        f"layer '{layer.get('id')}': icon-image '{name}' not found in sprite"
                    )

    return problems


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <style.json> <sprite.json>", file=sys.stderr)
        sys.exit(2)

    problems = validate(sys.argv[1], sys.argv[2])
    if problems:
        print(f"❌ {len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests again to confirm they pass**

Run: `cd scripts && python3 -m unittest test_validate_style -v`
Expected: `Ran 7 tests in ...s` / `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_style.py scripts/test_validate_style.py
git commit -m "$(cat <<'EOF'
test: add validate_style.py to statically check style/sprite consistency

Checks every layer's source-layer against the known set of consolidated
layers and every icon-image reference against the sprite set, so typos
surface immediately instead of failing silently at render time.
EOF
)"
```

---

### Task 3: Style skeleton + `ski_lifts` layers

**Files:**
- Modify: `styles/openskimap-style.json` (full replacement — the whole file is being redesigned against the new source-layers, nothing from the old content is reused as-is)

**Interfaces:**
- Consumes: `ski_lifts` source-layer (Task 1), `assets/sprites/openskimap/sprite.json` icon names (unchanged, pre-existing: `ski-gondola`, `ski-cable-car`, `ski-chairlift-{1,2,3,4,6,8}`, `ski-funicular`, `ski-magic-carpet`, `ski-rope-tow`, `ski-drag-lift-tbar`, `ski-drag-lift-platter`).
- Produces: the base `styles/openskimap-style.json` (root keys `version`/`name`/`glyphs`/`sources`/`sprite` — carried over unchanged from the current file — plus 4 lift layers: `ski-lifts-casing`, `ski-lifts-line`, `ski-lifts-labels`, `ski-lifts-icons`). Tasks 4–6 each append more layers to this same `layers` array; they anchor on the file's closing `"sprite"` line, which this task establishes.

- [ ] **Step 1: Write the new style file**

Replace `styles/openskimap-style.json` entirely with:

```json
{
  "version": 8,
  "name": "OpenSkiMap Overlay",
  "glyphs": "{TILES_BASE_URL}/assets/fonts/{fontstack}/{range}.pbf",
  "sources": {
    "ski_source": {
      "type": "vector",
      "url": "pmtiles://{TILES_BASE_URL}/openskimap.pmtiles",
      "attribution": "OpenSkiMap.org"
    }
  },
  "layers": [
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
      }
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
        "line-dasharray": [
          "case",
          [
            "==",
            [
              "get",
              "access"
            ],
            "private"
          ],
          [
            "literal",
            [
              1,
              2
            ]
          ],
          [
            "literal",
            [
              1,
              0
            ]
          ]
        ]
      }
    },
    {
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
        "text-max-angle": 30,
        "text-letter-spacing": 0.04,
        "text-padding": 2
      },
      "paint": {
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4,
        "text-color": "#2c3e50",
        "text-opacity": 0.9
      }
    },
    {
      "id": "ski-lifts-icons",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_lifts",
      "minzoom": 13,
      "layout": {
        "symbol-placement": "line",
        "symbol-spacing": 150,
        "icon-image": [
          "match",
          [
            "get",
            "lift_type"
          ],
          "gondola",
          "ski-gondola",
          "cable_car",
          "ski-cable-car",
          "chair_lift",
          [
            "case",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              1
            ],
            "ski-chairlift-1",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              2
            ],
            "ski-chairlift-2",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              3
            ],
            "ski-chairlift-3",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              4
            ],
            "ski-chairlift-4",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              6
            ],
            "ski-chairlift-6",
            [
              "==",
              [
                "get",
                "occupancy"
              ],
              8
            ],
            "ski-chairlift-8",
            "ski-chairlift-2"
          ],
          "funicular",
          "ski-funicular",
          "magic_carpet",
          "ski-magic-carpet",
          "rope_tow",
          "ski-rope-tow",
          "t-bar",
          "ski-drag-lift-tbar",
          "t_bar",
          "ski-drag-lift-tbar",
          "j-bar",
          "ski-drag-lift-tbar",
          "j_bar",
          "ski-drag-lift-tbar",
          "platter",
          "ski-drag-lift-platter",
          "drag_lift",
          "ski-drag-lift-tbar",
          "ski-gondola"
        ],
        "icon-size": 0.7,
        "icon-allow-overlap": false,
        "icon-ignore-placement": true
      }
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

- [ ] **Step 2: Verify it's valid JSON**

Run: `python3 -m json.tool styles/openskimap-style.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the validator**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.` (exit 0)

- [ ] **Step 4: Commit**

```bash
git add styles/openskimap-style.json
git commit -m "$(cat <<'EOF'
feat: rewrite style skeleton + lift layers against consolidated source-layers

First slice of the style rewrite: root keys carried over unchanged,
lift layers re-pointed at the new ski_lifts source-layer with status-based
coloring (bright red operating/proposed/planned/construction, dim red
disused/abandoned) and a dashed line for access=private. The existing
lift-type icon layer (our own sprite, unrelated to upstream) is carried
over unchanged.
EOF
)"
```

---

### Task 4: `ski_areas_alpine`, `ski_areas_nordic`, `ski_spots` layers

**Files:**
- Modify: `styles/openskimap-style.json` (append to the `layers` array)

**Interfaces:**
- Consumes: `ski_areas_alpine`, `ski_areas_nordic`, `ski_spots` source-layers (Task 1); appends after Task 3's `ski-lifts-icons` layer.
- Produces: 7 more layers (`ski-areas-alpine-{fill,circle,labels}`, `ski-areas-nordic-{fill,circle,labels}`, `ski-spots`) — 11 layers total in the file after this task.

- [ ] **Step 1: Append the area + spot layers**

In `styles/openskimap-style.json`, replace:

```json
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

with:

```json
    },
    {
      "id": "ski-areas-alpine-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_areas_alpine",
      "paint": {
        "fill-color": "#3085fe",
        "fill-opacity": 0.1
      }
    },
    {
      "id": "ski-areas-alpine-circle",
      "type": "circle",
      "source": "ski_source",
      "source-layer": "ski_areas_alpine",
      "maxzoom": 11,
      "paint": {
        "circle-color": "#3085fe",
        "circle-radius": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          0,
          1,
          11,
          6
        ],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1
      }
    },
    {
      "id": "ski-areas-alpine-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_areas_alpine",
      "minzoom": 10,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "text-field": [
          "get",
          "name"
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          10,
          11,
          14,
          14
        ]
      },
      "paint": {
        "text-color": "#3085fe",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4
      }
    },
    {
      "id": "ski-areas-nordic-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_areas_nordic",
      "paint": {
        "fill-color": "#2ecc71",
        "fill-opacity": 0.1
      }
    },
    {
      "id": "ski-areas-nordic-circle",
      "type": "circle",
      "source": "ski_source",
      "source-layer": "ski_areas_nordic",
      "maxzoom": 11,
      "paint": {
        "circle-color": "#2ecc71",
        "circle-radius": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          0,
          1,
          11,
          6
        ],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1
      }
    },
    {
      "id": "ski-areas-nordic-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_areas_nordic",
      "minzoom": 10,
      "filter": [
        "has",
        "name"
      ],
      "layout": {
        "text-field": [
          "get",
          "name"
        ],
        "text-font": [
          "Noto Sans Regular"
        ],
        "text-size": [
          "interpolate",
          [
            "linear"
          ],
          [
            "zoom"
          ],
          10,
          11,
          14,
          14
        ]
      },
      "paint": {
        "text-color": "#2ecc71",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4
      }
    },
    {
      "id": "ski-spots",
      "type": "circle",
      "source": "ski_source",
      "source-layer": "ski_spots",
      "minzoom": 13,
      "paint": {
        "circle-color": [
          "match",
          [
            "get",
            "spot_type"
          ],
          "lift_station",
          "#5a6b8c",
          "halfpipe",
          "#8e44ad",
          "crossing",
          "#e67e22",
          "avalanche_transceiver_training",
          "#c0392b",
          "avalanche_transceiver_checkpoint",
          "#c0392b",
          "#7f8c8d"
        ],
        "circle-radius": 4,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1
      }
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

- [ ] **Step 2: Verify valid JSON**

Run: `python3 -m json.tool styles/openskimap-style.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the validator**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 4: Commit**

```bash
git add styles/openskimap-style.json
git commit -m "$(cat <<'EOF'
feat: add ski-areas alpine/nordic and spots layers to style

Ski areas get a polygon fill, a point-geometry circle marker, and a
name label, duplicated per alpine/nordic source-layer so they're
independently toggleable. Spots (lift stations, halfpipes, avalanche
checkpoints, crossings) get generic circle markers colored by
spot_type — no sprite icons exist for these, per design decision.
EOF
)"
```

---

### Task 5: `ski_runs_alpine` layers

**Files:**
- Modify: `styles/openskimap-style.json` (append to the `layers` array)

**Interfaces:**
- Consumes: `ski_runs_alpine` source-layer (Task 1); appends after Task 4's `ski-spots` layer.
- Produces: 7 more layers (`ski-runs-alpine-{casing,line,gladed,ungroomed,fill,snowmaking,labels}`) — 18 layers total in the file after this task. Establishes the difficulty-color expression pattern that Task 6 mirrors verbatim for the nordic bucket.

- [ ] **Step 1: Append the alpine run layers**

In `styles/openskimap-style.json`, replace:

```json
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

with:

```json
    },
    {
      "id": "ski-runs-alpine-casing",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
          1.8,
          9,
          2.8,
          12,
          4.0,
          14,
          5.0
        ]
      }
    },
    {
      "id": "ski-runs-alpine-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
    {
      "id": "ski-runs-alpine-gladed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
    {
      "id": "ski-runs-alpine-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
    {
      "id": "ski-runs-alpine-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
      "id": "ski-runs-alpine-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
      "id": "ski-runs-alpine-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_alpine",
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
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

- [ ] **Step 2: Verify valid JSON**

Run: `python3 -m json.tool styles/openskimap-style.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the validator**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 4: Commit**

```bash
git add styles/openskimap-style.json
git commit -m "$(cat <<'EOF'
feat: add alpine run layers with OpenSkiMap difficulty color table

Colors runs by difficulty + difficulty_convention (europe/japan/
north_america) using OpenSkiMap's own published color table from
openskidata-format. White casing (yellow when lit), dotted dash for
gladed runs, dashed for backcountry/mogul-groomed runs, translucent
polygon fill for area runs, cyan overlay for snowmaking/snowfarming,
and name labels colored to match the run's difficulty.
EOF
)"
```

---

### Task 6: `ski_runs_nordic` layers

**Files:**
- Modify: `styles/openskimap-style.json` (append to the `layers` array — this completes the file)

**Interfaces:**
- Consumes: `ski_runs_nordic` source-layer (Task 1); appends after Task 5's `ski-runs-alpine-labels`.
- Produces: the final 7 layers (`ski-runs-nordic-{casing,line,gladed,ungroomed,fill,snowmaking,labels}`) — 25 layers total, matching the full design from the spec.

- [ ] **Step 1: Append the nordic run layers**

In `styles/openskimap-style.json`, replace:

```json
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

with:

```json
    },
    {
      "id": "ski-runs-nordic-casing",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
          1.8,
          9,
          2.8,
          12,
          4.0,
          14,
          5.0
        ]
      }
    },
    {
      "id": "ski-runs-nordic-line",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
    {
      "id": "ski-runs-nordic-gladed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
    {
      "id": "ski-runs-nordic-ungroomed",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
    {
      "id": "ski-runs-nordic-fill",
      "type": "fill",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
      "id": "ski-runs-nordic-snowmaking",
      "type": "line",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
      "id": "ski-runs-nordic-labels",
      "type": "symbol",
      "source": "ski_source",
      "source-layer": "ski_runs_nordic",
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
    }
  ],
  "sprite": "{TILES_BASE_URL}/assets/sprites/openskimap/sprite"
}
```

- [ ] **Step 2: Verify valid JSON**

Run: `python3 -m json.tool styles/openskimap-style.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the validator**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 4: Confirm the layer count matches the design**

Run: `python3 -c "import json; print(len(json.load(open('styles/openskimap-style.json'))['layers']))"`
Expected: `25`

- [ ] **Step 5: Commit**

```bash
git add styles/openskimap-style.json
git commit -m "$(cat <<'EOF'
feat: add nordic run layers, completing the style rewrite

Mirrors the alpine run layers (Task 5) against ski_runs_nordic —
same difficulty color table, same casing/gladed/ungroomed/snowmaking/
label treatment. styles/openskimap-style.json now covers all 6
consolidated source-layers (25 layers total).
EOF
)"
```

---

### Task 7: End-to-end integration verification

**Files:**
- None modified — this task only runs the pipeline and inspects its output. If any check fails, fix the relevant file from Tasks 1–6 and re-run this task before considering the plan complete.

**Interfaces:**
- Consumes: `scripts/convert.sh` (Task 1), `styles/openskimap-style.json` (Tasks 3–6), `scripts/generate_manifest.py` (pre-existing, unmodified), `scripts/validate_style.py` (Task 2).
- Produces: `dist/pmtiles/openskimap.pmtiles`, `dist/styles/openskimap-style.json`, `dist/assets/sprites/openskimap/*`, `dist/manifest.json` — the actual deployable output of this repo.

- [ ] **Step 1: Regenerate `work/openskimap.pmtiles` with the final convert.sh**

Run: `bash scripts/convert.sh`
Expected: exits 0 (same as Task 1 Step 2 — re-run since Task 1 ran before the style was finalized, to get a clean end-to-end pass with everything in its final state).

- [ ] **Step 2: Regenerate `dist/`**

Run: `python3 scripts/generate_manifest.py`
Expected: exits 0, ends with `Manifest saved to: .../dist/manifest.json`. Confirm `dist/pmtiles/openskimap.pmtiles`, `dist/styles/openskimap-style.json`, and `dist/assets/sprites/openskimap/sprite.json` all exist.

- [ ] **Step 3: Validate the deployed style against the deployed sprite**

Run: `python3 scripts/validate_style.py dist/styles/openskimap-style.json dist/assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.`

- [ ] **Step 4: Confirm the deployed PMTiles has all 6 layers**

Run: `pmtiles show --metadata dist/pmtiles/openskimap.pmtiles | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(l['id'] for l in d['vector_layers']))"`
Expected:
```
['ski_areas_alpine', 'ski_areas_nordic', 'ski_lifts', 'ski_runs_alpine', 'ski_runs_nordic', 'ski_spots']
```

- [ ] **Step 5: Manual visual check (not automatable in this environment — no browser/GPU here)**

Serve `dist/` locally (e.g. `python3 -m http.server 8080` from the repo root) and open a minimal MapLibre GL JS page pointing `style` at `http://localhost:8080/dist/styles/openskimap-style.json` with `{TILES_BASE_URL}` replaced by `http://localhost:8080/dist`, over a region with real ski data (e.g. an Austrian resort for the `europe` difficulty convention, a Japanese or North American one to exercise the other two branches of the color table). Confirm visually:
  - Runs render in difficulty colors (green/blue/red/black/orange), casing visible, lit runs show yellow casing.
  - Gladed runs show a dotted pattern, backcountry/mogul runs a dashed pattern.
  - Toggling `ski-runs-nordic-*` / `ski-areas-nordic-*` layers off (via `map.setLayoutProperty(id, "visibility", "none")` in the browser console) hides only nordic content, alpine stays visible, and vice versa.
  - Lift lines are red-shaded by status, dashed for private access, with our existing lift-type icons still rendering along the line.
  - Spots render as small colored circles at high zoom.

This step has no fixed pass/fail command — record what you observed and fix forward (adjust the relevant layer in Tasks 3–6) if something looks wrong, then re-run Steps 1–4.

- [ ] **Step 6: Final check — no leftover uncommitted changes**

Run: `git status --short`
Expected: clean (everything from Tasks 1–6 was already committed); if anything is outstanding here, it means a fix was made during Step 5 and needs its own commit.

# Layer-List v1.1 Fields + Central Difficulty Legend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `dist/layer-list.json` up to `geodata-plugin-standard` v1.1.0's §5 schema (`width`, `dasharray`, `outline_color`, `outline_width`, `icon`, `legend_scale_id`, top-level `legend_sections`), fix an existing primary-layer-selection bug that gives `ski-lifts` the wrong swatch color, consolidate the four run-category groups' identical difficulty legend into one shared `legend_sections` entry, and give all eight groups proper German display names.

**Architecture:** All logic changes live in two existing files: `scripts/layer_metadata_extractor.py` (pure per-layer extraction helpers, no I/O) and `scripts/generate_layer_list.py` (group assembly, calls the extractor). No new files besides two new `unittest` test modules that mirror the existing `scripts/test_validate_style.py` convention. No changes to `styles/openskimap-style.json`, `scripts/convert.sh`, or `scripts/generate_manifest.py`.

**Tech Stack:** Python 3 stdlib only (`json`, `unittest`) — no new pip dependencies, no virtualenv changes.

## Global Constraints

- Schema version in `build_layer_list()`'s return value goes from `"1.0"` to `"1.1"` (breaking change per plugin-standard §5.6).
- Tests use stdlib `unittest`, run via `python3 -m unittest <module> -v` from inside `scripts/` — **not** pytest (repo has no pytest dependency).
- Every style layer id referenced by `styles/openskimap-style.json` must stay covered by `GROUP_MAP` (existing fail-fast `KeyError` behavior in `build_layer_list` — do not weaken it).
- Casing/outline detection is by layer-id suffix only (`-casing` or `-outline`), scoped to `type == "line"` — no other heuristic (e.g. z-order) per the plugin-standard §5.3 extraction rule.
- `docs/superpowers/specs/2026-08-12-layer-list-legend-scale-v1.1-design.md` is the approved spec — every field/table value below is copied from its "Erwartetes Ergebnis" table, already re-verified against the real style file.
- Commit messages use Conventional Commits prefixes (`fix(...)`, `feat(...)`, `test(...)`, `docs(...)`); stage files explicitly, never `git add -A`.

---

### Task 1: Commit the prerequisite `case`-expression fix already in the working tree

**Context:** Before this session's work started, `scripts/layer_metadata_extractor.py` and `CHANGELOG.md` already had uncommitted changes (added by an earlier, separate piece of work): `extract_legend_items()` now resolves a top-level MapLibre `case` expression (openskimap's difficulty layers switch on `difficulty_convention` via `case`, each branch a `match` on `difficulty`) before looking for `interpolate`/`match`. This is a prerequisite for every difficulty-legend field this plan adds — commit it on its own first so the diff for the new v1.1 work stays clean.

**Files:**
- Modify (stage existing uncommitted changes): `scripts/layer_metadata_extractor.py`, `CHANGELOG.md`

- [ ] **Step 1: Verify the uncommitted diff is exactly the case-resolution fix**

Run: `git diff scripts/layer_metadata_extractor.py CHANGELOG.md`

Expected: `layer_metadata_extractor.py` diff adds `DIFFICULTY_CASE_PROPERTY`/`DIFFICULTY_CASE_VALUE` constants, a `case`-branch check inside `extract_legend_items`, and a new `_resolve_case_branch()` function. `CHANGELOG.md` diff adds one `## [Unreleased] - 2026-08-12 07:25` block under `### Fixed` describing that same change. If the diff contains anything else (e.g. partial edits from this session), stop and reconcile before proceeding — this task must commit exactly the prerequisite fix, nothing from Task 2 onward.

- [ ] **Step 2: Run the existing test suite to confirm nothing is broken**

Run: `cd scripts && python3 -m unittest test_validate_style -v && cd ..`
Expected: All tests pass (this fix doesn't touch `validate_style.py`, so this is a smoke check that the working tree is otherwise healthy).

- [ ] **Step 3: Commit**

```bash
git add scripts/layer_metadata_extractor.py CHANGELOG.md
git commit -m "$(cat <<'EOF'
fix(layer-list): resolve difficulty legend_items via case-expression branch

ski-runs-*-fill's fill-color switches on difficulty_convention
(europe/japan/default) via a top-level "case" expression, each branch
a "match" on difficulty. extract_legend_items() only looked for
interpolate/match at the top level, so these layers — the legend a
ski map actually needs — silently got legend_items: null. Resolves
the "europe" branch (DACH is this project's target audience), with
fallback to the case's else-branch if no europe branch is present.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: New v1.1 extraction helpers in `layer_metadata_extractor.py`

**Files:**
- Modify: `scripts/layer_metadata_extractor.py` (insert after `extract_layer_opacity`, i.e. after the line `    return 1` that currently precedes `def extract_legend_items(style_layers):`)
- Create: `scripts/test_layer_metadata_extractor.py`

**Interfaces:**
- Produces: `extract_layer_width(layer) -> float | int | None`, `extract_layer_dasharray(layer) -> list[float | int] | None`, `extract_outline_metadata(group_layers) -> dict` with keys `"outline_color"` and `"outline_width"`, `extract_layer_icon(layer) -> str | None`. All consumed by Task 3.

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_layer_metadata_extractor.py`:

```python
import unittest

from layer_metadata_extractor import (
    extract_layer_width,
    extract_layer_dasharray,
    extract_outline_metadata,
    extract_layer_icon,
)


class ExtractLayerWidthTests(unittest.TestCase):
    def test_literal_number(self):
        layer = {"type": "line", "paint": {"line-width": 1.5}}
        self.assertEqual(extract_layer_width(layer), 1.5)

    def test_interpolate_returns_highest_zoom_stop(self):
        layer = {
            "type": "line",
            "paint": {
                "line-width": [
                    "interpolate", ["linear"], ["zoom"],
                    6, 0.8, 9, 1.4, 12, 2.2, 14, 3.0,
                ]
            },
        }
        self.assertEqual(extract_layer_width(layer), 3.0)

    def test_non_line_layer_returns_none(self):
        layer = {"type": "fill", "paint": {"line-width": 5}}
        self.assertIsNone(extract_layer_width(layer))

    def test_missing_line_width_returns_none(self):
        layer = {"type": "line", "paint": {}}
        self.assertIsNone(extract_layer_width(layer))

    def test_data_driven_expression_returns_none(self):
        layer = {"type": "line", "paint": {"line-width": ["get", "width"]}}
        self.assertIsNone(extract_layer_width(layer))


class ExtractLayerDasharrayTests(unittest.TestCase):
    def test_literal_wrapped_array(self):
        layer = {"type": "line", "paint": {"line-dasharray": ["literal", [1, 3]]}}
        self.assertEqual(extract_layer_dasharray(layer), [1, 3])

    def test_raw_two_element_array(self):
        layer = {"type": "line", "paint": {"line-dasharray": [1, 2]}}
        self.assertEqual(extract_layer_dasharray(layer), [1, 2])

    def test_missing_field_returns_none(self):
        layer = {"type": "line", "paint": {}}
        self.assertIsNone(extract_layer_dasharray(layer))

    def test_non_two_element_literal_returns_none(self):
        layer = {"type": "line", "paint": {"line-dasharray": ["literal", [1, 2, 3]]}}
        self.assertIsNone(extract_layer_dasharray(layer))


class ExtractOutlineMetadataTests(unittest.TestCase):
    def test_finds_casing_sibling(self):
        group_layers = [
            {
                "id": "ski-lifts-casing",
                "type": "line",
                "paint": {
                    "line-color": "hsl(0, 0%, 100%)",
                    "line-width": [
                        "interpolate", ["linear"], ["zoom"],
                        6, 1.8, 9, 2.8, 12, 4.0, 14, 5.0,
                    ],
                },
            },
            {
                "id": "ski-lifts-line",
                "type": "line",
                "paint": {"line-color": "hsl(0, 82%, 42%)"},
            },
        ]
        result = extract_outline_metadata(group_layers)
        self.assertEqual(
            result, {"outline_color": "hsl(0, 0%, 100%)", "outline_width": 5.0}
        )

    def test_finds_outline_suffixed_sibling(self):
        group_layers = [
            {
                "id": "water-protection-outline",
                "type": "line",
                "paint": {"line-color": "#1d4ed8", "line-width": 1.0},
            },
        ]
        result = extract_outline_metadata(group_layers)
        self.assertEqual(result, {"outline_color": "#1d4ed8", "outline_width": 1.0})

    def test_no_casing_layer_returns_none_pair(self):
        group_layers = [
            {"id": "ski-runs-skitour-fill", "type": "fill", "paint": {"fill-color": "#000"}},
            {"id": "ski-runs-skitour-line", "type": "line", "paint": {"line-color": "#000"}},
        ]
        result = extract_outline_metadata(group_layers)
        self.assertEqual(result, {"outline_color": None, "outline_width": None})

    def test_expression_outline_color_is_none_but_width_still_resolves(self):
        # Regression case: ski-runs-downhill-casing's line-color is a "case"
        # expression (not a literal string), but its line-width is still a
        # plain interpolate — outline_color must be None while outline_width
        # still resolves.
        group_layers = [
            {
                "id": "ski-runs-downhill-casing",
                "type": "line",
                "paint": {
                    "line-color": ["case", ["==", ["get", "lit"], True], "hsl(63, 100%, 76%)", "hsl(0, 0%, 100%)"],
                    "line-width": [
                        "interpolate", ["linear"], ["zoom"],
                        6, 1.8, 9, 2.8, 12, 4.0, 14, 5.0,
                    ],
                },
            },
        ]
        result = extract_outline_metadata(group_layers)
        self.assertEqual(result, {"outline_color": None, "outline_width": 5.0})


class ExtractLayerIconTests(unittest.TestCase):
    def test_literal_icon_string(self):
        layer = {"type": "symbol", "layout": {"icon-image": "aerialway-station-11"}}
        self.assertEqual(extract_layer_icon(layer), "aerialway-station-11")

    def test_expression_icon_returns_none(self):
        layer = {
            "type": "symbol",
            "layout": {
                "icon-image": [
                    "match", ["get", "lift_type"],
                    "gondola", "ski-gondola",
                    "ski-chairlift-1",
                ]
            },
        }
        self.assertIsNone(extract_layer_icon(layer))

    def test_non_symbol_layer_returns_none(self):
        layer = {"type": "fill", "layout": {"icon-image": "x"}}
        self.assertIsNone(extract_layer_icon(layer))

    def test_missing_icon_image_returns_none(self):
        layer = {"type": "symbol", "layout": {"text-field": ["get", "name"]}}
        self.assertIsNone(extract_layer_icon(layer))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v && cd ..`
Expected: `ImportError: cannot import name 'extract_layer_width' from 'layer_metadata_extractor'` (or similar for the other three names) — the functions don't exist yet.

- [ ] **Step 3: Implement the four helpers**

In `scripts/layer_metadata_extractor.py`, find this exact block (end of `extract_layer_opacity`, immediately before `extract_legend_items`):

```python
    # Default to 1 if not specified
    return 1


def extract_legend_items(style_layers):
```

Replace it with:

```python
    # Default to 1 if not specified
    return 1


def extract_layer_width(layer):
    """
    Extract line-width from a MapLibre line layer.

    Literal numbers are returned directly. An `interpolate` expression over
    zoom returns its highest-zoom stop value (the last value in the stop
    list) — the width the layer renders at when fully zoomed in. Any other
    expression form (e.g. data-driven) returns None, as does any non-line
    layer.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        float | int | None
    """
    if layer.get("type") != "line":
        return None

    width = layer.get("paint", {}).get("line-width")

    if isinstance(width, (int, float)):
        return width

    if isinstance(width, list) and width and width[0] == "interpolate":
        stops_and_values = width[3:]
        if stops_and_values and len(stops_and_values) % 2 == 0:
            last_value = stops_and_values[-1]
            if isinstance(last_value, (int, float)):
                return last_value

    return None


def extract_layer_dasharray(layer):
    """
    Extract line-dasharray from a MapLibre line layer.

    Only a literal 2-element numeric array counts, whether written as a raw
    array (`[1, 3]`) or wrapped in a MapLibre "literal" expression
    (`["literal", [1, 3]]` — the form openskimap's style actually uses for
    the private/other lift-line variants). Anything else (missing field,
    wrong length, non-numeric values) returns None.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        list[float | int] | None
    """
    dasharray = layer.get("paint", {}).get("line-dasharray")

    if not isinstance(dasharray, list):
        return None

    if len(dasharray) == 2 and dasharray[0] == "literal" and isinstance(dasharray[1], list):
        candidate = dasharray[1]
    else:
        candidate = dasharray

    if len(candidate) == 2 and all(isinstance(v, (int, float)) for v in candidate):
        return candidate

    return None


def extract_outline_metadata(group_layers):
    """
    Find a group's casing/outline layer and extract its color/width.

    Scans group_layers for the first `type: "line"` layer whose `id` ends in
    "-casing" or "-outline" (GEODATA_PLUGIN_STANDARD.md v1.1 §5.3 extraction
    rule — id-suffix only, no z-order or other fallback). Its `line-color`
    (via extract_layer_color — None if it's an expression, not a literal
    string) and `line-width` (via extract_layer_width) become
    outline_color/outline_width. No matching layer -> both None.

    Args:
        group_layers (list): List of MapLibre layer objects in one group

    Returns:
        dict: {"outline_color": str | None, "outline_width": float | int | None}
    """
    for layer in group_layers:
        layer_id = layer.get("id", "")
        if layer.get("type") == "line" and (
            layer_id.endswith("-casing") or layer_id.endswith("-outline")
        ):
            return {
                "outline_color": extract_layer_color(layer),
                "outline_width": extract_layer_width(layer),
            }

    return {"outline_color": None, "outline_width": None}


def extract_layer_icon(layer):
    """
    Extract icon-image from a MapLibre symbol layer.

    Only returns a value for `type: "symbol"` layers, and only when
    `layout.icon-image` is a literal string (openskimap's lift-icon layer
    uses a `match` expression there, so this returns None for it — correct
    per spec, not a bug).

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        str | None
    """
    if layer.get("type") != "symbol":
        return None

    icon = layer.get("layout", {}).get("icon-image")
    return icon if isinstance(icon, str) else None


def extract_legend_items(style_layers):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v && cd ..`
Expected: `OK` (17 tests pass, 0 failures).

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/test_layer_metadata_extractor.py
git commit -m "$(cat <<'EOF'
feat(layer-list): add v1.1 width/dasharray/outline/icon extraction helpers

Ports the GEODATA_PLUGIN_STANDARD.md v1.1.0 §5.3 extraction rules for
line-width, line-dasharray, casing/outline color+width, and
icon-image. Not yet wired into generate_layer_list.py (Task 3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Fix primary-layer selection in `_group_metadata` and wire the new fields

**Context:** `_group_metadata()` in `generate_layer_list.py` currently picks the first layer of the highest-priority type it sees, in style-file order, as the group's "primary" layer for `type`/`color`/`opacity`. For the `ski-lifts` group, `ski-lifts-casing` (a plain white outline line) appears before `ski-lifts-line` (the actual status-colored line) in `styles/openskimap-style.json`, so the group's `color` currently resolves to `"hsl(0, 0%, 100%)"` (white) even though `legend_items` correctly shows status colors (red/etc.) — an inconsistent swatch. This task excludes casing/outline layers from primary-layer candidacy (they exist only to supply `outline_color`/`outline_width`, extracted separately via `extract_outline_metadata`) and wires all five new v1.1 fields into the group dict.

**Files:**
- Modify: `scripts/generate_layer_list.py`
- Create: `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: `extract_layer_width`, `extract_layer_dasharray`, `extract_outline_metadata`, `extract_layer_icon` from Task 2.
- Produces: `_group_metadata(group_layers) -> dict | None` now returns `type`, `color`, `opacity`, `width`, `dasharray`, `outline_color`, `outline_width`, `icon`, `legend_items`. Consumed by Task 4/5 (via `build_layer_list`'s group-population loop).

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_generate_layer_list.py`:

```python
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from generate_layer_list import _group_metadata, build_layer_list

STYLE_PATH = os.path.join(os.path.dirname(__file__), "..", "styles", "openskimap-style.json")


class GroupMetadataCasingExclusionTests(unittest.TestCase):
    def test_casing_layer_never_chosen_as_primary(self):
        group_layers = [
            {
                "id": "ski-lifts-casing",
                "type": "line",
                "source-layer": "ski_lifts",
                "paint": {
                    "line-color": "hsl(0, 0%, 100%)",
                    "line-width": [
                        "interpolate", ["linear"], ["zoom"],
                        6, 1.8, 9, 2.8, 12, 4.0, 14, 5.0,
                    ],
                },
            },
            {
                "id": "ski-lifts-line",
                "type": "line",
                "source-layer": "ski_lifts",
                "paint": {
                    "line-color": [
                        "match", ["get", "status"],
                        "operating", "hsl(0, 82%, 42%)",
                        "hsl(0, 53%, 42%)",
                    ],
                    "line-opacity": 0.8,
                    "line-width": [
                        "interpolate", ["linear"], ["zoom"],
                        6, 0.8, 9, 1.4, 12, 2.2, 14, 3.0,
                    ],
                },
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "line")
        self.assertIsNone(metadata["color"])  # match expression, not a literal string
        self.assertEqual(metadata["opacity"], 0.8)
        self.assertEqual(metadata["width"], 3.0)
        self.assertEqual(metadata["outline_color"], "hsl(0, 0%, 100%)")
        self.assertEqual(metadata["outline_width"], 5.0)

    def test_symbol_layer_with_icon_image_becomes_icon_type(self):
        group_layers = [
            {
                "id": "lift-stations-icon",
                "type": "symbol",
                "source-layer": "ski_lift_stations",
                "layout": {"icon-image": "aerialway-station-11"},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "icon")
        self.assertEqual(metadata["icon"], "aerialway-station-11")

    def test_text_only_symbol_layer_stays_symbol_type(self):
        group_layers = [
            {
                "id": "ski-lifts-labels",
                "type": "symbol",
                "source-layer": "ski_lifts",
                "layout": {"text-field": ["get", "name"]},
                "paint": {"text-color": "#2c3e50"},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "symbol")
        self.assertIsNone(metadata["icon"])

    def test_fill_still_wins_over_casing_and_line(self):
        group_layers = [
            {
                "id": "ski-runs-downhill-casing",
                "type": "line",
                "source-layer": "ski_runs_downhill_line",
                "paint": {"line-color": "hsl(0, 0%, 100%)", "line-width": 2.0},
            },
            {
                "id": "ski-runs-downhill-fill",
                "type": "fill",
                "source-layer": "ski_runs_downhill_poly",
                "paint": {"fill-color": "#22c55e", "fill-opacity": 0.25},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "fill")
        self.assertEqual(metadata["color"], "#22c55e")
        self.assertIsNone(metadata["width"])  # fill layers have no line-width


class BuildLayerListRealStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STYLE_PATH, encoding="utf-8") as f:
            style_data = json.load(f)
        cls.result = build_layer_list(style_data, "openskimap", "OpenSkiMap", "openskimap.pmtiles")
        cls.groups_by_key = {g["template"]: g for g in cls.result["styles"][0]["groups"]}

    def test_ski_lifts_color_is_not_casing_white(self):
        lifts = self.groups_by_key["ski-lifts"]
        self.assertIsNone(lifts["color"])
        self.assertEqual(lifts["width"], 3.0)
        self.assertEqual(lifts["outline_color"], "hsl(0, 0%, 100%)")
        self.assertEqual(lifts["outline_width"], 5.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `KeyError: 'width'` (or similar) — `_group_metadata` doesn't return the new keys yet, and the real-style `ski-lifts` test still sees the old white `color`.

- [ ] **Step 3: Update imports in `generate_layer_list.py`**

Find:

```python
sys.path.append(os.path.dirname(__file__))
from layer_metadata_extractor import (
    extract_layer_color,
    extract_layer_opacity,
    extract_legend_items,
)
```

Replace with:

```python
sys.path.append(os.path.dirname(__file__))
from layer_metadata_extractor import (
    extract_layer_color,
    extract_layer_opacity,
    extract_layer_width,
    extract_layer_dasharray,
    extract_outline_metadata,
    extract_layer_icon,
    extract_legend_items,
)
```

- [ ] **Step 4: Replace `_group_metadata`**

Find the entire existing function:

```python
def _group_metadata(group_layers):
    """Same fill > line > circle > symbol primary-layer selection as
    layer_metadata_extractor.extract_layer_metadata, but over an already
    collected list of layers instead of filtering style_data by a single
    source-layer name (a group here can span several)."""
    layer_type_priority = {"fill": 4, "line": 3, "circle": 2, "symbol": 1}

    primary_layer = None
    for layer in group_layers:
        layer_type = layer.get("type")
        if layer_type not in layer_type_priority:
            continue
        if primary_layer is None or layer_type_priority[layer_type] > layer_type_priority[primary_layer.get("type")]:
            primary_layer = layer

    if primary_layer is None:
        return None

    return {
        "type": primary_layer.get("type"),
        "color": extract_layer_color(primary_layer),
        "opacity": extract_layer_opacity(primary_layer),
        "legend_items": extract_legend_items(group_layers),
    }
```

Replace with:

```python
def _group_metadata(group_layers):
    """Same fill > line > circle > (symbol/icon) primary-layer selection as
    layer_metadata_extractor.extract_layer_metadata, but over an already
    collected list of layers instead of filtering style_data by a single
    source-layer name (a group here can span several).

    Layers whose id ends in "-casing" or "-outline" are never chosen as the
    primary layer (their line-color/line-width instead become
    outline_color/outline_width, see extract_outline_metadata) — otherwise a
    casing layer that happens to appear first in the style (e.g.
    ski-lifts-casing before ski-lifts-line) would incorrectly become the
    group's primary color/type, out of sync with legend_items."""
    layer_type_priority = {"fill": 4, "line": 3, "circle": 2, "symbol": 1}

    def is_outline_layer(layer):
        layer_id = layer.get("id", "")
        return layer.get("type") == "line" and (
            layer_id.endswith("-casing") or layer_id.endswith("-outline")
        )

    primary_layer = None
    for layer in group_layers:
        if is_outline_layer(layer):
            continue
        layer_type = layer.get("type")
        if layer_type not in layer_type_priority:
            continue
        if primary_layer is None or layer_type_priority[layer_type] > layer_type_priority[primary_layer.get("type")]:
            primary_layer = layer

    if primary_layer is None:
        return None

    primary_type = primary_layer.get("type")
    if primary_type == "symbol" and "icon-image" in primary_layer.get("layout", {}):
        primary_type = "icon"

    outline = extract_outline_metadata(group_layers)

    return {
        "type": primary_type,
        "color": extract_layer_color(primary_layer),
        "opacity": extract_layer_opacity(primary_layer),
        "width": extract_layer_width(primary_layer),
        "dasharray": extract_layer_dasharray(primary_layer),
        "outline_color": outline["outline_color"],
        "outline_width": outline["outline_width"],
        "icon": extract_layer_icon(primary_layer),
        "legend_items": extract_legend_items(group_layers),
    }
```

- [ ] **Step 5: Wire the new fields into the group-population loop**

Find:

```python
    for group_key, group in groups_dict.items():
        metadata = _group_metadata(group_layers[group_key])
        if metadata:
            group["type"] = metadata.get("type")
            group["color"] = metadata.get("color")
            group["opacity"] = metadata.get("opacity")
            group["legend_items"] = metadata.get("legend_items")
```

Replace with:

```python
    for group_key, group in groups_dict.items():
        metadata = _group_metadata(group_layers[group_key])
        if metadata:
            group["type"] = metadata.get("type")
            group["color"] = metadata.get("color")
            group["opacity"] = metadata.get("opacity")
            group["width"] = metadata.get("width")
            group["dasharray"] = metadata.get("dasharray")
            group["outline_color"] = metadata.get("outline_color")
            group["outline_width"] = metadata.get("outline_width")
            group["icon"] = metadata.get("icon")
            group["legend_items"] = metadata.get("legend_items")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `OK` (5 tests pass).

Also run Task 2's suite to confirm no regression: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v && cd ..` — expected `OK`.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
fix(layer-list): stop picking casing layers as group primary layer

_group_metadata picked the first highest-priority-type layer in style
order; for ski-lifts, the white ski-lifts-casing line appeared before
the actual status-colored ski-lifts-line, so the group's color/type
came from the casing instead — inconsistent with legend_items, which
already showed the correct status colors. Casing/outline layers
(id ending -casing/-outline) are now excluded from primary-layer
candidacy and instead exclusively supply outline_color/outline_width
via extract_outline_metadata. Also wires width/dasharray/icon into
the group dict and refines type to "icon" for symbol layers that set
icon-image (GEODATA_PLUGIN_STANDARD.md v1.1.0 §5.3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: German group display names (`GROUP_NAMES`)

**Files:**
- Modify: `scripts/generate_layer_list.py`, `scripts/test_generate_layer_list.py`

**Interfaces:**
- Produces: `GROUP_NAMES` dict (module-level constant), used to set `group["name"]`.

- [ ] **Step 1: Write the failing test**

In `scripts/test_generate_layer_list.py`, add a new test method to `BuildLayerListRealStyleTests` (after `test_ski_lifts_color_is_not_casing_white`):

```python
    def test_group_names_are_german(self):
        self.assertEqual(self.groups_by_key["ski-runs-downhill"]["name"], "Pisten")
        self.assertEqual(self.groups_by_key["ski-runs-nordic"]["name"], "Loipen")
        self.assertEqual(self.groups_by_key["ski-runs-skitour"]["name"], "Skitouren")
        self.assertEqual(self.groups_by_key["ski-runs-other"]["name"], "Sonstige Strecken")
        self.assertEqual(self.groups_by_key["ski-areas-alpine"]["name"], "Skigebiete (Alpin)")
        self.assertEqual(self.groups_by_key["ski-areas-nordic"]["name"], "Skigebiete (Nordisch)")
        self.assertEqual(self.groups_by_key["ski-spots"]["name"], "Ski-Spots")
        self.assertEqual(self.groups_by_key["ski-lifts"]["name"], "Lifte")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `FAIL` — `AssertionError: 'Ski Runs Downhill' != 'Pisten'`.

- [ ] **Step 3: Add `GROUP_NAMES` constant**

In `scripts/generate_layer_list.py`, find the end of `GROUP_MAP` (the line `}` that closes it, immediately followed by two blank lines and `def _group_metadata`):

```python
    "ski-lifts-icons": "ski-lifts",
}


def _group_metadata(group_layers):
```

Replace with:

```python
    "ski-lifts-icons": "ski-lifts",
}

# group key -> German display name shown in downstream legend UIs. Every key
# in GROUP_MAP's values must appear here (build_layer_list raises KeyError
# via direct dict indexing if one doesn't, same fail-fast convention as
# GROUP_MAP itself).
GROUP_NAMES = {
    "ski-areas-alpine": "Skigebiete (Alpin)",
    "ski-areas-nordic": "Skigebiete (Nordisch)",
    "ski-runs-downhill": "Pisten",
    "ski-runs-nordic": "Loipen",
    "ski-runs-skitour": "Skitouren",
    "ski-runs-other": "Sonstige Strecken",
    "ski-spots": "Ski-Spots",
    "ski-lifts": "Lifte",
}


def _group_metadata(group_layers):
```

- [ ] **Step 4: Use `GROUP_NAMES` when creating a group**

Find (inside `build_layer_list`):

```python
        if group_key not in groups_dict:
            groups_dict[group_key] = {
                "source_layer": source_layer,
                "source_layers": [],
                "name": group_key.replace("-", " ").title(),
                "template": group_key,
                "original_file": SOURCE_GPKG_REL_PATH,
                "style_layers": [],
            }
            group_layers[group_key] = []
```

Replace with:

```python
        if group_key not in groups_dict:
            groups_dict[group_key] = {
                "source_layer": source_layer,
                "source_layers": [],
                "name": GROUP_NAMES[group_key],
                "template": group_key,
                "original_file": SOURCE_GPKG_REL_PATH,
                "style_layers": [],
            }
            group_layers[group_key] = []
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `OK` (6 tests pass).

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(layer-list): German display names for all eight legend groups

Replaces the auto-generated group_key.replace("-", " ").title()
placeholder names ("Ski Runs Downhill", ...) with proper German
names (Pisten, Loipen, Skitouren, Sonstige Strecken, Skigebiete
(Alpin/Nordisch), Ski-Spots, Lifte) via a new GROUP_NAMES constant.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Central `legend_scale_id` / `legend_sections` for the four run groups + schema version bump

**Files:**
- Modify: `scripts/generate_layer_list.py`, `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: `log_warn` from `scripts/ci/utils.py`.
- Produces: `_build_legend_sections(groups_dict) -> list[dict] | None`. `build_layer_list()`'s return value gains a top-level `"legend_sections"` key and its `"version"` becomes `"1.1"`.

- [ ] **Step 1: Write the failing tests**

In `scripts/test_generate_layer_list.py`, add these imports at the top (after the existing `from generate_layer_list import ...` line):

```python
import unittest.mock

import generate_layer_list
```

Add these test methods to `BuildLayerListRealStyleTests` (after `test_group_names_are_german`):

```python
    def test_schema_version_is_1_1(self):
        self.assertEqual(self.result["version"], "1.1")

    def test_run_groups_share_one_legend_scale(self):
        for key in ("ski-runs-downhill", "ski-runs-nordic", "ski-runs-skitour", "ski-runs-other"):
            group = self.groups_by_key[key]
            self.assertEqual(group["legend_scale_id"], "ski-difficulty-v1")
            self.assertIsNone(group["legend_items"])

    def test_groups_without_scale_have_null_scale_id(self):
        self.assertIsNone(self.groups_by_key["ski-lifts"]["legend_scale_id"])
        self.assertIsNone(self.groups_by_key["ski-spots"]["legend_scale_id"])
        self.assertIsNotNone(self.groups_by_key["ski-lifts"]["legend_items"])
        self.assertIsNotNone(self.groups_by_key["ski-spots"]["legend_items"])

    def test_legend_sections_has_one_shared_difficulty_scale(self):
        sections = self.result["legend_sections"]
        self.assertEqual(len(sections), 1)
        section = sections[0]
        self.assertEqual(section["id"], "ski-difficulty-v1")
        self.assertEqual(section["label"], "Schwierigkeitsgrade")
        self.assertEqual(
            [item["label"] for item in section["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Expert", "Freeride", "Extreme", "Sonstige"],
        )


class BuildLegendSectionsTests(unittest.TestCase):
    def setUp(self):
        self._original_scale_map = generate_layer_list.GROUP_LEGEND_SCALE
        self._original_labels = generate_layer_list.LEGEND_SCALE_LABELS
        generate_layer_list.GROUP_LEGEND_SCALE = {
            "group-a": "test-scale",
            "group-b": "test-scale",
        }
        generate_layer_list.LEGEND_SCALE_LABELS = {"test-scale": "Test"}

    def tearDown(self):
        generate_layer_list.GROUP_LEGEND_SCALE = self._original_scale_map
        generate_layer_list.LEGEND_SCALE_LABELS = self._original_labels

    def test_collapses_matching_scale_into_one_section(self):
        groups_dict = {
            "group-a": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-b": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-c": {"legend_items": None},
        }
        sections = generate_layer_list._build_legend_sections(groups_dict)
        self.assertEqual(
            sections,
            [{"id": "test-scale", "label": "Test", "items": [{"label": "Novice", "color": "green"}]}],
        )
        self.assertIsNone(groups_dict["group-a"]["legend_items"])
        self.assertIsNone(groups_dict["group-b"]["legend_items"])
        self.assertEqual(groups_dict["group-a"]["legend_scale_id"], "test-scale")
        self.assertEqual(groups_dict["group-b"]["legend_scale_id"], "test-scale")
        self.assertIsNone(groups_dict["group-c"]["legend_scale_id"])

    def test_warns_but_does_not_raise_on_drifted_items(self):
        groups_dict = {
            "group-a": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-b": {"legend_items": [{"label": "Novice", "color": "DRIFTED"}]},
        }
        with unittest.mock.patch("generate_layer_list.log_warn") as mock_warn:
            sections = generate_layer_list._build_legend_sections(groups_dict)
            mock_warn.assert_called_once()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["items"], [{"label": "Novice", "color": "green"}])

    def test_no_scale_configured_returns_none(self):
        generate_layer_list.GROUP_LEGEND_SCALE = {}
        groups_dict = {"group-a": {"legend_items": [{"label": "X", "color": "red"}]}}
        sections = generate_layer_list._build_legend_sections(groups_dict)
        self.assertIsNone(sections)
        self.assertIsNone(groups_dict["group-a"]["legend_scale_id"])
        self.assertEqual(groups_dict["group-a"]["legend_items"], [{"label": "X", "color": "red"}])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `AttributeError: module 'generate_layer_list' has no attribute 'GROUP_LEGEND_SCALE'` (or similar for `_build_legend_sections`/`log_warn`).

- [ ] **Step 3: Import `log_warn` and add the scale constants**

Find the top of `scripts/generate_layer_list.py`:

```python
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
from layer_metadata_extractor import (
```

Replace with:

```python
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "ci"))
from utils import log_warn
from layer_metadata_extractor import (
```

Find the `GROUP_NAMES` block added in Task 4 and its trailing blank lines before `def _group_metadata`:

```python
    "ski-lifts": "Lifte",
}


def _group_metadata(group_layers):
```

Replace with:

```python
    "ski-lifts": "Lifte",
}

# group key -> shared legend_scale_id (GEODATA_PLUGIN_STANDARD.md v1.1.0
# §5.5/§5.6). All four run-category groups render fill-color from the same
# difficulty match expression (verified byte-identical against
# styles/openskimap-style.json), so they share one central legend instead of
# duplicating identical legend_items four times.
GROUP_LEGEND_SCALE = {
    "ski-runs-downhill": "ski-difficulty-v1",
    "ski-runs-nordic": "ski-difficulty-v1",
    "ski-runs-skitour": "ski-difficulty-v1",
    "ski-runs-other": "ski-difficulty-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
}


def _group_metadata(group_layers):
```

- [ ] **Step 4: Add `_build_legend_sections`**

Find the end of `_group_metadata` (the `return {...}` block) followed by `def build_layer_list`:

```python
        "icon": extract_layer_icon(primary_layer),
        "legend_items": extract_legend_items(group_layers),
    }


def build_layer_list(style_data, style_id, name, pmtiles_path):
```

Replace with:

```python
        "icon": extract_layer_icon(primary_layer),
        "legend_items": extract_legend_items(group_layers),
    }


def _build_legend_sections(groups_dict):
    """
    Collapse per-group legend_items into one shared top-level entry per
    distinct legend_scale_id (GEODATA_PLUGIN_STANDARD.md v1.1.0 §5.5/§5.6).

    Sets legend_scale_id on every group (None if GROUP_LEGEND_SCALE has no
    entry for it) and, for groups with a configured scale, nulls their
    legend_items — the values live centrally in the returned list instead.
    If two groups share a legend_scale_id but produced different
    legend_items, logs a warning (does not raise — a standard document
    can't mandate a build abort in consuming repos, §5.5) and keeps the
    first group's items.

    Args:
        groups_dict (dict): group_key -> group dict, mutated in place

    Returns:
        list[dict] | None: [{"id", "label", "items"}, ...] in
        first-encounter order, or None if no group has a configured scale
    """
    sections = {}
    for group_key, group in groups_dict.items():
        scale_id = GROUP_LEGEND_SCALE.get(group_key)
        group["legend_scale_id"] = scale_id
        if scale_id is None:
            continue

        items = group.get("legend_items")
        if scale_id not in sections:
            sections[scale_id] = {
                "id": scale_id,
                "label": LEGEND_SCALE_LABELS[scale_id],
                "items": items,
            }
        elif items != sections[scale_id]["items"]:
            log_warn(
                f"legend_scale_id '{scale_id}': group '{group_key}' legend_items "
                f"differ from the first group sharing this scale — "
                f"layer-list.json will use the first group's items."
            )

        group["legend_items"] = None

    return list(sections.values()) if sections else None


def build_layer_list(style_data, style_id, name, pmtiles_path):
```

- [ ] **Step 5: Wire `_build_legend_sections` into `build_layer_list` and bump the schema version**

Find:

```python
    for group_key, group in groups_dict.items():
        metadata = _group_metadata(group_layers[group_key])
        if metadata:
            group["type"] = metadata.get("type")
            group["color"] = metadata.get("color")
            group["opacity"] = metadata.get("opacity")
            group["width"] = metadata.get("width")
            group["dasharray"] = metadata.get("dasharray")
            group["outline_color"] = metadata.get("outline_color")
            group["outline_width"] = metadata.get("outline_width")
            group["icon"] = metadata.get("icon")
            group["legend_items"] = metadata.get("legend_items")

    return {
        "version": "1.0",
        "styles": [
            {
                "style_id": style_id,
                "name": name,
                "pmtiles_path": pmtiles_path,
                "groups": list(groups_dict.values()),
            }
        ],
    }
```

Replace with:

```python
    for group_key, group in groups_dict.items():
        metadata = _group_metadata(group_layers[group_key])
        if metadata:
            group["type"] = metadata.get("type")
            group["color"] = metadata.get("color")
            group["opacity"] = metadata.get("opacity")
            group["width"] = metadata.get("width")
            group["dasharray"] = metadata.get("dasharray")
            group["outline_color"] = metadata.get("outline_color")
            group["outline_width"] = metadata.get("outline_width")
            group["icon"] = metadata.get("icon")
            group["legend_items"] = metadata.get("legend_items")

    legend_sections = _build_legend_sections(groups_dict)

    return {
        "version": "1.1",
        "styles": [
            {
                "style_id": style_id,
                "name": name,
                "pmtiles_path": pmtiles_path,
                "groups": list(groups_dict.values()),
            }
        ],
        "legend_sections": legend_sections,
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v && cd ..`
Expected: `OK` (13 tests pass).

Also re-run Task 2/3's other suite: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v && cd ..` — expected `OK`.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(layer-list): centralize difficulty legend into legend_sections

ski-runs-{downhill,nordic,skitour,other} all render fill-color from
byte-identical difficulty match expressions. They now share one
legend_scale_id ("ski-difficulty-v1") instead of each duplicating the
same eight-item legend_items list; the shared items move to a new
top-level legend_sections block (GEODATA_PLUGIN_STANDARD.md v1.1.0
§5.5/§5.6). Schema version bumped "1.0" -> "1.1" (breaking change per
§5.6 — legend_items is null on a group once its legend_scale_id is
set). A drifted-items build warning (no abort) guards the
"same-scale-id implies same items" invariant for future changes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: CHANGELOG, TODO, and end-to-end verification

**Files:**
- Modify: `CHANGELOG.md`, `docs/TODO.md`

- [ ] **Step 1: Get the current timestamp for the CHANGELOG entry**

Run: `date '+%Y-%m-%d %H:%M'`

Note the output — use it verbatim as `<TIMESTAMP>` in the next step (repo convention per `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4: `## [Unreleased] - YYYY-MM-DD HH:mm`).

- [ ] **Step 2: Add a CHANGELOG.md entry**

Read `CHANGELOG.md` first — Task 1 already committed one `## [Unreleased] - 2026-08-12 07:25` block at the top (the `case`-expression fix). Insert a **new**, second `## [Unreleased]` block immediately above it (newest first), using the timestamp from Step 1 in place of `<TIMESTAMP>`:

```markdown
## [Unreleased] - <TIMESTAMP>

### Changed
- `layer-list.json`-Schema auf v1.1 (`geodata-plugin-standard` v1.1.0,
  §5) angehoben: neue Felder `width`, `dasharray`, `outline_color`,
  `outline_width`, `icon`, `legend_scale_id` je Gruppe, neuer
  Top-Level-Block `legend_sections`. **Breaking Change**: Gruppen mit
  gesetzter `legend_scale_id` haben jetzt `legend_items: null` — die
  Werte liegen zentral in `legend_sections`.
- Die vier Pisten-Gruppen (`ski-runs-downhill/-nordic/-skitour/-other`)
  teilen sich jetzt eine zentrale Schwierigkeits-Legende
  (`legend_scale_id: "ski-difficulty-v1"`) statt sie viermal identisch
  zu duplizieren.
- Gruppen-Anzeigenamen auf Deutsch umgestellt (Pisten, Loipen,
  Skitouren, Sonstige Strecken, Skigebiete (Alpin/Nordisch),
  Ski-Spots, Lifte) statt automatisch generierter
  Titel-Case-Platzhalter.

### Fixed
- `ski-lifts`-Gruppe zeigte `color: "hsl(0, 0%, 100%)"` (weiß, von der
  Casing-Linie `ski-lifts-casing`), obwohl die eigentliche
  Status-Farbe (rot/…) in `ski-lifts-line` liegt und `legend_items`
  bereits korrekt die Status-Farben zeigte. Casing-/Outline-Layer
  (`id` endet auf `-casing`/`-outline`) werden jetzt nie mehr als
  Primär-Layer gewählt.
```

- [ ] **Step 3: Add a `docs/TODO.md` entry for the now-confirmed-dead `extract_layer_metadata()`**

Read `docs/TODO.md` first, then append this new section at the end of the file:

```markdown

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
gebraucht wird (`scripts/layer_metadata_extractor.py:332-386`).
```

- [ ] **Step 4: Regenerate `dist/layer-list.json` against the real style and inspect it**

Run:
```bash
python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from generate_layer_list import build_layer_list
with open('styles/openskimap-style.json') as f:
    style = json.load(f)
result = build_layer_list(style, 'openskimap', 'OpenSkiMap', 'openskimap.pmtiles')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```
Expected: valid JSON, `"version": "1.1"`, eight groups with German `name` values, `ski-lifts.color` is `null` (not white), `ski-lifts.outline_color` is `"hsl(0, 0%, 100%)"`, all four run groups have `legend_scale_id: "ski-difficulty-v1"` and `legend_items: null`, and a top-level `legend_sections` array with exactly one entry (`id: "ski-difficulty-v1"`, 8 items). Cross-check against the "Erwartetes Ergebnis" table in `docs/superpowers/specs/2026-08-12-layer-list-legend-scale-v1.1-design.md`.

- [ ] **Step 5: Run the full test suite**

Run:
```bash
cd scripts
python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v
cd ..
```
Expected: `OK`, all tests across all three modules pass.

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md docs/TODO.md
git commit -m "$(cat <<'EOF'
docs: changelog entry + TODO note for layer-list.json v1.1 upgrade

Documents the v1.1 schema upgrade (new fields, central difficulty
legend, German group names, ski-lifts color fix) and flags
extract_layer_metadata() as confirmed-dead, now also stale, code for
a follow-up decision.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Report status and propose next steps to the user**

Per `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4 ("Release-Trigger"): this closes a complete, self-contained batch of work (submodule bump + this feature). Tell the user the work is committed and ask whether to propose a release (`VERSION` bump + CHANGELOG consolidation + tag) now, or leave it in `[Unreleased]` for later. Do not bump `VERSION` or tag without explicit confirmation.

---

## Self-Review Notes

**Spec coverage:** All five "Neue Extraktions-Helper" functions from the design → Task 2. Primary-layer-selection bugfix (Entscheidung 3) → Task 3. Group names (Entscheidung 2) → Task 4. `legend_scale_id`/`legend_sections`/version bump (Entscheidung 1, §5.5 drift-warning) → Task 5. CHANGELOG/TODO/verification (design's "CHANGELOG.md / Versionierung", "Betroffene Dateien", "Verifikation" sections) → Task 6. The design's "Erwartetes Ergebnis"-table values are directly asserted in Task 3/5's `BuildLayerListRealStyleTests`. No spec section without a task.

**Placeholder scan:** No TBD/TODO-as-code markers; the one dynamic value (CHANGELOG timestamp) is resolved by an explicit `date` command in Task 6 Step 1, not left as free text.

**Type consistency:** `_group_metadata` return dict keys (`type`, `color`, `opacity`, `width`, `dasharray`, `outline_color`, `outline_width`, `icon`, `legend_items`) match exactly between Task 3's implementation and Task 3/4/5's test assertions. `extract_outline_metadata`'s return dict keys (`outline_color`, `outline_width`) match between Task 2's implementation and Task 2/3's tests. `GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS`/`GROUP_NAMES` names are consistent across Tasks 4/5 definitions and Task 5's monkeypatch-based tests.

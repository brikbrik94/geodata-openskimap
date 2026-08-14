# layer-list.json v2.0 Render-Parts-Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `scripts/layer_metadata_extractor.py` and `scripts/generate_layer_list.py` from the v1.1 single-primary-layer `layer-list.json` schema to the v2.0 `render: Array<Part>` schema (GEODATA_PLUGIN_STANDARD.md v2.0.0 §5), so `dist/layer-list.json` is schema-2.0-compliant.

**Architecture:** Full replace, no compat shim. `layer_metadata_extractor.py` gets a kind-driven extraction API (`determine_part_kind` + six small `extract_part_*` functions sharing a `PART_FIELDS_BY_KIND` table) that is generic/portable per the standard's §5.8. `generate_layer_list.py` keeps its openskimap-specific `GROUP_MAP`/group-assembly logic but replaces the old single-primary-layer `_group_metadata` with a 1:1-per-layer `_build_render`, and replaces the per-group `legend_items` mechanism with a `scale_id -> items` map collected while building `render`, fed into `_build_legend_sections`.

**Tech Stack:** Python 3 stdlib only (`json`, `unittest`) — no new dependencies, matches the rest of this repo.

**Spec:** `docs/superpowers/specs/2026-08-14-render-parts-v2.0-migration-design.md`

## Global Constraints

- Schema version string changes from `"1.1"` to `"2.0"` (spec §5.1).
- `render` is one `Part` per style layer of a group, in style order (spec §5.3) — no merge, no "primary layer" selection.
- `Part` shape (spec §5.3): `{"kind": ..., "color": ..., "opacity": ..., "width": ..., "dasharray": ..., "radius": ..., "icon": ...}` — non-applicable fields are `null`, never omitted.
- `kind` mapping (spec §5.3 table): `fill`→fill-layer, `line`→line-layer without `-casing`/`-outline` id suffix, `outline`→line-layer with `-casing`/`-outline` id suffix, `icon`→symbol-layer with `layout.icon-image`, `text`→symbol-layer without it, `circle`→circle-layer. Layer types without a mapped kind are skipped (no Part).
- `color` extraction (spec §5.3/§5.4): literal string → `{"mode": "fixed", "value": ...}`; `interpolate`/`match` expression (after resolving a top-level openskimap `case` expression, module-specific deviation) → categorized, becomes `{"mode": "scale", "scale_id": ...}` at the group-assembly level; any other expression form or unset property → `null`.
- `opacity`/`width`/`dasharray`/`radius` extraction: literal value used directly; `interpolate` over `["zoom"]` → highest-zoom (last) stop value; any other form → `null` (`opacity` defaults to `1` instead of `null` when unset/unresolvable — spec §5.3).
- `legend_scale_id` is **mandatory** per group config as soon as any Part in that group is categorized (spec §5.5). Missing config → `log_warn(...)` + that Part's `color` set to `null`, never a build abort (spec §5.5).
- New scale IDs/labels (user-confirmed 2026-08-14): `ski-lift-status-v1` / "Lift-Status", `ski-spot-type-v1` / "Spot-Typ".
- Full replace: no v1.1/v2.0 dual-mode, no feature flag (`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4 — no compat shim where a direct code change works).
- `extract_layer_metadata()` (dead code, `layer_metadata_extractor.py:463-517` pre-migration) is removed, not migrated.
- `circle-stroke-color`/`circle-stroke-width` have no `Part` field — known, accepted data loss, tracked upstream as [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3), not fixed in this repo.

---

### Task 1: `determine_part_kind` + `PART_FIELDS_BY_KIND`

**Files:**
- Modify: `scripts/layer_metadata_extractor.py` (add near top, after the `DIFFICULTY_CASE_PROPERTY`/`DIFFICULTY_CASE_VALUE` constants at lines 35-36)
- Test: `scripts/test_layer_metadata_extractor.py` (add new test class; existing classes stay until Task 3 removes their subjects)

**Interfaces:**
- Produces: `PART_FIELDS_BY_KIND: dict[str, dict[str, str]]` (kind → field-name → paint/layout property name), `determine_part_kind(layer: dict) -> str | None`. Both consumed by every later task.

- [ ] **Step 1: Write the failing tests**

In `scripts/test_layer_metadata_extractor.py`, replace the existing `from layer_metadata_extractor import (...)` block (currently importing `extract_layer_width, extract_layer_dasharray, extract_outline_metadata, extract_layer_icon`) with the same names plus `determine_part_kind`, and append the new test class at the end of the file (existing test classes stay untouched for now):

```python
from layer_metadata_extractor import (
    extract_layer_width,
    extract_layer_dasharray,
    extract_outline_metadata,
    extract_layer_icon,
    determine_part_kind,
)


class DeterminePartKindTests(unittest.TestCase):
    def test_fill_layer(self):
        self.assertEqual(determine_part_kind({"type": "fill"}), "fill")

    def test_circle_layer(self):
        self.assertEqual(determine_part_kind({"type": "circle"}), "circle")

    def test_line_layer_without_casing_suffix(self):
        self.assertEqual(determine_part_kind({"type": "line", "id": "ski-lifts-line"}), "line")

    def test_line_layer_with_casing_suffix(self):
        self.assertEqual(determine_part_kind({"type": "line", "id": "ski-lifts-casing"}), "outline")

    def test_line_layer_with_outline_suffix(self):
        self.assertEqual(determine_part_kind({"type": "line", "id": "water-protection-outline"}), "outline")

    def test_symbol_layer_with_icon_image_is_icon(self):
        layer = {"type": "symbol", "id": "ski-lifts-icons", "layout": {"icon-image": "x"}}
        self.assertEqual(determine_part_kind(layer), "icon")

    def test_symbol_layer_without_icon_image_is_text(self):
        layer = {"type": "symbol", "id": "ski-lifts-labels", "layout": {"text-field": ["get", "name"]}}
        self.assertEqual(determine_part_kind(layer), "text")

    def test_unmapped_type_returns_none(self):
        self.assertIsNone(determine_part_kind({"type": "raster"}))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: `DeterminePartKindTests` fail with `ImportError: cannot import name 'determine_part_kind'`.

- [ ] **Step 3: Implement**

Add to `scripts/layer_metadata_extractor.py`, directly after the `DIFFICULTY_CASE_VALUE = "europe"` line:

```python
# kind -> {field name -> MapLibre paint/layout property}, per
# GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.3's kind table. A field absent from a
# kind's sub-dict is always null for that kind's Parts (e.g. "fill" has no
# "width").
PART_FIELDS_BY_KIND = {
    "fill": {"color": "fill-color", "opacity": "fill-opacity"},
    "line": {
        "color": "line-color", "opacity": "line-opacity",
        "width": "line-width", "dasharray": "line-dasharray",
    },
    "outline": {
        "color": "line-color", "opacity": "line-opacity",
        "width": "line-width", "dasharray": "line-dasharray",
    },
    "icon": {"color": "icon-color", "opacity": "icon-opacity", "icon": "icon-image"},
    "text": {"color": "text-color", "opacity": "text-opacity"},
    "circle": {"color": "circle-color", "opacity": "circle-opacity", "radius": "circle-radius"},
}


def determine_part_kind(layer):
    """
    Determine a style layer's Part `kind` per GEODATA_PLUGIN_STANDARD.md
    v2.0.0 §5.3.

    Args:
        layer (dict): A MapLibre style layer object

    Returns:
        str | None: one of PART_FIELDS_BY_KIND's keys, or None if the
            layer's `type` has no kind mapping (e.g. fill-extrusion,
            heatmap, raster) — such a layer produces no Part.
    """
    layer_type = layer.get("type")

    if layer_type == "fill":
        return "fill"
    if layer_type == "circle":
        return "circle"
    if layer_type == "line":
        layer_id = layer.get("id", "")
        return "outline" if layer_id.endswith(("-casing", "-outline")) else "line"
    if layer_type == "symbol":
        return "icon" if "icon-image" in layer.get("layout", {}) else "text"

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: all tests pass, including the new `DeterminePartKindTests`.

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/test_layer_metadata_extractor.py
git commit -m "feat(layer-list): add determine_part_kind + PART_FIELDS_BY_KIND for v2.0 render model"
```

---

### Task 2: `extract_part_color` + `extract_categorized_items` (generalized case-resolution)

**Files:**
- Modify: `scripts/layer_metadata_extractor.py` (add after `PART_FIELDS_BY_KIND`/`determine_part_kind`; `_resolve_case_branch`, `_parse_interpolate_expression`, `_parse_match_expression`, `build_numeric_match_items`, `_build_categorical_match_items` at lines 296-460 stay unchanged and are reused)
- Test: `scripts/test_layer_metadata_extractor.py`

**Interfaces:**
- Consumes: `PART_FIELDS_BY_KIND` (Task 1); existing `_resolve_case_branch(expr, property_name, target_value)`, `_parse_interpolate_expression(expr)`, `_parse_match_expression(expr)` (unchanged, already in the file).
- Produces: `extract_part_color(layer: dict, kind: str) -> dict | str | None` (returns `{"mode": "fixed", "value": str}`, the literal string `"categorized"`, or `None`), `extract_categorized_items(layer: dict, kind: str) -> list[dict] | None`. Both consumed by Task 4's `_build_render`.

- [ ] **Step 1: Write the failing tests**

In `scripts/test_layer_metadata_extractor.py`, replace the import block from Task 1 with the same names plus `extract_part_color, extract_categorized_items` (the four `extract_layer_*` names are still in use by other test classes until Task 3 removes them), and append the two new test classes at the end of the file:

```python
from layer_metadata_extractor import (
    extract_layer_width,
    extract_layer_dasharray,
    extract_outline_metadata,
    extract_layer_icon,
    determine_part_kind,
    extract_part_color,
    extract_categorized_items,
)


class ExtractPartColorTests(unittest.TestCase):
    def test_literal_color_is_fixed(self):
        layer = {"type": "fill", "paint": {"fill-color": "#3085fe"}}
        self.assertEqual(extract_part_color(layer, "fill"), {"mode": "fixed", "value": "#3085fe"})

    def test_match_expression_is_categorized(self):
        layer = {
            "type": "circle",
            "paint": {"circle-color": ["match", ["get", "spot_type"], "halfpipe", "#8e44ad", "#7f8c8d"]},
        }
        self.assertEqual(extract_part_color(layer, "circle"), "categorized")

    def test_interpolate_expression_is_categorized(self):
        layer = {
            "type": "fill",
            "paint": {"fill-color": ["interpolate", ["linear"], ["get", "eta"], 0, "#22c55e", 15, "#facc15"]},
        }
        self.assertEqual(extract_part_color(layer, "fill"), "categorized")

    def test_case_wrapped_literal_resolves_to_fixed(self):
        # Regression: ski-runs-downhill-casing's line-color is a "case" on
        # "lit" (not difficulty_convention) -> falls to the else-branch,
        # which is a plain literal string here. Must NOT be null.
        layer = {
            "type": "line",
            "id": "ski-runs-downhill-casing",
            "paint": {
                "line-color": ["case", ["==", ["get", "lit"], True], "hsl(63, 100%, 76%)", "hsl(0, 0%, 100%)"],
            },
        }
        self.assertEqual(
            extract_part_color(layer, "outline"),
            {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
        )

    def test_case_wrapped_categorized_resolves_to_categorized(self):
        # ski-runs-nordic-casing: opposite of downhill's casing, its case
        # switches on difficulty_convention and resolves to a match expr.
        layer = {
            "type": "line",
            "id": "ski-runs-nordic-casing",
            "paint": {
                "line-color": [
                    "case",
                    ["==", ["get", "difficulty_convention"], "europe"],
                    ["match", ["get", "difficulty"], "novice", "hsl(125, 100%, 33%)", "hsl(0, 0%, 35%)"],
                    ["match", ["get", "difficulty"], "novice", "hsl(125, 100%, 33%)", "hsl(0, 0%, 35%)"],
                ],
            },
        }
        self.assertEqual(extract_part_color(layer, "outline"), "categorized")

    def test_unset_property_returns_none(self):
        layer = {"type": "symbol", "layout": {"icon-image": "x"}, "paint": {}}
        self.assertIsNone(extract_part_color(layer, "icon"))

    def test_data_driven_expression_returns_none(self):
        layer = {"type": "fill", "paint": {"fill-color": ["get", "color"]}}
        self.assertIsNone(extract_part_color(layer, "fill"))

    def test_kind_without_color_field_returns_none(self):
        layer = {"type": "line", "paint": {"line-color": "#fff"}}
        self.assertIsNone(extract_part_color(layer, "nonexistent-kind"))


class ExtractCategorizedItemsTests(unittest.TestCase):
    def test_interpolate_numeric_ranges(self):
        layer = {
            "type": "fill",
            "paint": {"fill-color": ["interpolate", ["linear"], ["get", "eta"], 0, "#22c55e", 15, "#facc15"]},
        }
        self.assertEqual(
            extract_categorized_items(layer, "fill"),
            [{"label": "0-15 min", "color": "#22c55e"}, {"label": "15+ min", "color": "#facc15"}],
        )

    def test_match_string_values_with_fallback(self):
        layer = {
            "type": "circle",
            "paint": {"circle-color": ["match", ["get", "spot_type"], "halfpipe", "#8e44ad", "#7f8c8d"]},
        }
        self.assertEqual(
            extract_categorized_items(layer, "circle"),
            [{"label": "Halfpipe", "color": "#8e44ad"}, {"label": "Sonstige", "color": "#7f8c8d"}],
        )

    def test_non_categorized_returns_none(self):
        layer = {"type": "fill", "paint": {"fill-color": "#3085fe"}}
        self.assertIsNone(extract_categorized_items(layer, "fill"))

    def test_case_wrapped_categorized_resolves_items(self):
        layer = {
            "type": "line",
            "paint": {
                "line-color": [
                    "case",
                    ["==", ["get", "difficulty_convention"], "europe"],
                    ["match", ["get", "difficulty"], "novice", "hsl(125, 100%, 33%)", "hsl(0, 0%, 35%)"],
                    ["match", ["get", "difficulty"], "novice", "hsl(125, 100%, 33%)", "hsl(0, 0%, 35%)"],
                ],
            },
        }
        self.assertEqual(
            extract_categorized_items(layer, "outline"),
            [{"label": "Novice", "color": "hsl(125, 100%, 33%)"}, {"label": "Sonstige", "color": "hsl(0, 0%, 35%)"}],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: `ExtractPartColorTests`/`ExtractCategorizedItemsTests` fail with `ImportError`.

- [ ] **Step 3: Implement**

Add to `scripts/layer_metadata_extractor.py`, directly after `determine_part_kind`:

```python
def _resolve_part_color_expression(layer, kind):
    """
    Look up the kind-specific color paint property (PART_FIELDS_BY_KIND) and
    resolve it one step: a top-level "case" expression is resolved via
    _resolve_case_branch (openskimap deviation, see module docstring).

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        str | list | None: a literal color string, a resolved
            interpolate/match expression (list), or None (kind has no color
            field, property unset, non-list/non-string value, or an
            unsupported expression form after case-resolution).
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("color")
    if prop is None:
        return None

    value = layer.get("paint", {}).get(prop)

    if isinstance(value, str):
        return value

    if not isinstance(value, list) or not value:
        return None

    if value[0] == "case":
        value = _resolve_case_branch(value, DIFFICULTY_CASE_PROPERTY, DIFFICULTY_CASE_VALUE)
        if isinstance(value, str):
            return value
        if not isinstance(value, list):
            return None

    if value[0] in ("interpolate", "match"):
        return value

    return None


def extract_part_color(layer, kind):
    """
    Extract a Part's `color` field per GEODATA_PLUGIN_STANDARD.md v2.0.0
    §5.3/§5.4.

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        dict | str | None: {"mode": "fixed", "value": str} for a literal
            color; the string "categorized" (internal marker — the actual
            {"mode": "scale", "scale_id": ...} is assembled one level up in
            generate_layer_list.py, which owns the group->scale_id config,
            see extract_categorized_items for the item list) for an
            interpolate/match expression; None otherwise.
    """
    resolved = _resolve_part_color_expression(layer, kind)

    if isinstance(resolved, str):
        return {"mode": "fixed", "value": resolved}
    if isinstance(resolved, list):
        return "categorized"
    return None


def extract_categorized_items(layer, kind):
    """
    Extract legend items ({label, color} per category) for a Part whose
    color is categorized (see extract_part_color).

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        list[dict] | None: [{"label": ..., "color": ...}, ...], or None if
            the layer's color is not categorized.
    """
    resolved = _resolve_part_color_expression(layer, kind)

    if not isinstance(resolved, list):
        return None
    if resolved[0] == "interpolate":
        return _parse_interpolate_expression(resolved)
    if resolved[0] == "match":
        return _parse_match_expression(resolved)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/test_layer_metadata_extractor.py
git commit -m "feat(layer-list): add extract_part_color/extract_categorized_items with generalized case-resolution"
```

---

### Task 3: Remaining `extract_part_*` functions + remove superseded v1.1 functions

**Files:**
- Modify: `scripts/layer_metadata_extractor.py` — add `extract_part_opacity`/`extract_part_width`/`extract_part_dasharray`/`extract_part_radius`/`extract_part_icon`; **remove** `extract_layer_color` (lines 39-74), `extract_layer_opacity` (77-114), `extract_layer_width` (117-148), `extract_layer_dasharray` (151-180), `extract_outline_metadata` (183-210), `extract_layer_icon` (213-232), the `NOTE` comment block (235-246), `extract_legend_items` (247-293), `extract_layer_metadata` (463-517); update module docstring (lines 1-33)
- Test: `scripts/test_layer_metadata_extractor.py` — remove `ExtractLayerWidthTests`, `ExtractLayerDasharrayTests`, `ExtractOutlineMetadataTests`, `ExtractLayerIconTests` (they test now-removed functions) and their now-dead imports; add new field-extractor test classes

**Interfaces:**
- Consumes: `PART_FIELDS_BY_KIND` (Task 1).
- Produces: `extract_part_opacity(layer, kind) -> float | int`, `extract_part_width(layer, kind) -> float | int | None`, `extract_part_dasharray(layer, kind) -> list | None`, `extract_part_radius(layer, kind) -> float | int | None`, `extract_part_icon(layer, kind) -> str | None`. All consumed by Task 4's `_build_render`.

- [ ] **Step 1: Write the failing tests**

Replace the imports and the four old test classes (`ExtractLayerWidthTests` through `ExtractLayerIconTests`) in `scripts/test_layer_metadata_extractor.py` with:

```python
from layer_metadata_extractor import (
    determine_part_kind,
    extract_part_color,
    extract_categorized_items,
    extract_part_opacity,
    extract_part_width,
    extract_part_dasharray,
    extract_part_radius,
    extract_part_icon,
)


class ExtractPartOpacityTests(unittest.TestCase):
    def test_literal_value(self):
        layer = {"type": "fill", "paint": {"fill-opacity": 0.25}}
        self.assertEqual(extract_part_opacity(layer, "fill"), 0.25)

    def test_interpolate_returns_highest_zoom_stop(self):
        layer = {
            "type": "line",
            "paint": {"line-opacity": ["interpolate", ["linear"], ["zoom"], 6, 0.2, 14, 0.8]},
        }
        self.assertEqual(extract_part_opacity(layer, "line"), 0.8)

    def test_missing_property_defaults_to_1(self):
        layer = {"type": "fill", "paint": {}}
        self.assertEqual(extract_part_opacity(layer, "fill"), 1)

    def test_kind_without_opacity_field_defaults_to_1(self):
        layer = {"type": "line", "paint": {"line-opacity": 0.5}}
        self.assertEqual(extract_part_opacity(layer, "nonexistent-kind"), 1)


class ExtractPartWidthTests(unittest.TestCase):
    def test_literal_number(self):
        layer = {"type": "line", "paint": {"line-width": 1.5}}
        self.assertEqual(extract_part_width(layer, "line"), 1.5)

    def test_interpolate_returns_highest_zoom_stop(self):
        layer = {
            "type": "line",
            "paint": {"line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.8, 14, 3.0]},
        }
        self.assertEqual(extract_part_width(layer, "outline"), 3.0)

    def test_kind_without_width_field_returns_none(self):
        layer = {"type": "fill", "paint": {"fill-color": "#000"}}
        self.assertIsNone(extract_part_width(layer, "fill"))

    def test_missing_property_returns_none(self):
        layer = {"type": "line", "paint": {}}
        self.assertIsNone(extract_part_width(layer, "line"))


class ExtractPartDasharrayTests(unittest.TestCase):
    def test_literal_wrapped_array(self):
        layer = {"type": "line", "paint": {"line-dasharray": ["literal", [1, 3]]}}
        self.assertEqual(extract_part_dasharray(layer, "line"), [1, 3])

    def test_raw_two_element_array(self):
        layer = {"type": "line", "paint": {"line-dasharray": [1, 2]}}
        self.assertEqual(extract_part_dasharray(layer, "line"), [1, 2])

    def test_kind_without_dasharray_field_returns_none(self):
        layer = {"type": "fill", "paint": {}}
        self.assertIsNone(extract_part_dasharray(layer, "fill"))

    def test_missing_field_returns_none(self):
        layer = {"type": "line", "paint": {}}
        self.assertIsNone(extract_part_dasharray(layer, "line"))


class ExtractPartRadiusTests(unittest.TestCase):
    def test_literal_number(self):
        layer = {"type": "circle", "paint": {"circle-radius": 4}}
        self.assertEqual(extract_part_radius(layer, "circle"), 4)

    def test_interpolate_returns_highest_zoom_stop(self):
        layer = {
            "type": "circle",
            "paint": {"circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 1, 11, 6]},
        }
        self.assertEqual(extract_part_radius(layer, "circle"), 6)

    def test_kind_without_radius_field_returns_none(self):
        layer = {"type": "line", "paint": {"line-width": 2}}
        self.assertIsNone(extract_part_radius(layer, "line"))


class ExtractPartIconTests(unittest.TestCase):
    def test_literal_icon_string(self):
        layer = {"type": "symbol", "layout": {"icon-image": "aerialway-station-11"}}
        self.assertEqual(extract_part_icon(layer, "icon"), "aerialway-station-11")

    def test_expression_icon_returns_none(self):
        layer = {
            "type": "symbol",
            "layout": {
                "icon-image": ["match", ["get", "lift_type"], "gondola", "ski-gondola", "ski-chairlift-1"]
            },
        }
        self.assertIsNone(extract_part_icon(layer, "icon"))

    def test_kind_without_icon_field_returns_none(self):
        layer = {"type": "symbol", "layout": {"icon-image": "x"}}
        self.assertIsNone(extract_part_icon(layer, "text"))
```

(The `ExtractPartColorTests`/`ExtractCategorizedItemsTests` classes from Task 2 stay unchanged.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: `ImportError` for the five new functions. (The old `ExtractLayer*`/`ExtractOutlineMetadata*` classes are already gone from the file at this point, so there's nothing to fail on their behalf.)

- [ ] **Step 3: Implement**

In `scripts/layer_metadata_extractor.py`:

1. Delete `extract_layer_color`, `extract_layer_opacity`, `extract_layer_width`, `extract_layer_dasharray`, `extract_outline_metadata`, `extract_layer_icon`, the `NOTE:` comment block above `extract_legend_items`, `extract_legend_items` itself, and `extract_layer_metadata` (the last function in the file).

2. Add, directly after `extract_categorized_items` (from Task 2):

```python
def _extract_interpolatable_number(value):
    """
    Shared rule for width/dasharray-adjacent numeric fields (width, radius,
    opacity): a literal number is returned directly; an `interpolate`
    expression over `["zoom"]` returns its highest-zoom stop value (the last
    value in the stop list); any other form (missing, data-driven, etc.)
    returns None.
    """
    if isinstance(value, (int, float)):
        return value

    if isinstance(value, list) and value and value[0] == "interpolate":
        stops_and_values = value[3:]
        if stops_and_values and len(stops_and_values) % 2 == 0:
            last_value = stops_and_values[-1]
            if isinstance(last_value, (int, float)):
                return last_value

    return None


def extract_part_opacity(layer, kind):
    """Kind-specific opacity (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. Defaults to 1 if unset/unresolvable or
    if `kind` has no opacity field."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("opacity")
    if prop is None:
        return 1

    result = _extract_interpolatable_number(layer.get("paint", {}).get(prop))
    return result if result is not None else 1


def extract_part_width(layer, kind):
    """Kind-specific line-width (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no width field."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("width")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))


def extract_part_radius(layer, kind):
    """Kind-specific circle-radius (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no radius field
    (only "circle" does)."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("radius")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))


def extract_part_dasharray(layer, kind):
    """
    Kind-specific line-dasharray (PART_FIELDS_BY_KIND). Only a literal
    2-element numeric array counts, whether written as a raw array
    (`[1, 3]`) or wrapped in a MapLibre "literal" expression
    (`["literal", [1, 3]]` — the form openskimap's style actually uses).
    None if `kind` has no dasharray field, the field is missing, or the
    value doesn't match either form.
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("dasharray")
    if prop is None:
        return None

    dasharray = layer.get("paint", {}).get(prop)
    if not isinstance(dasharray, list):
        return None

    if len(dasharray) == 2 and dasharray[0] == "literal" and isinstance(dasharray[1], list):
        candidate = dasharray[1]
    else:
        candidate = dasharray

    if len(candidate) == 2 and all(isinstance(v, (int, float)) for v in candidate):
        return candidate

    return None


def extract_part_icon(layer, kind):
    """
    Kind-specific icon-image (PART_FIELDS_BY_KIND). Only returns a value
    when `kind` has an icon field (only "icon" does) and the layout
    property is a literal string (openskimap's lift-icon layer uses a
    `match` expression there, so this returns None for it — correct per
    spec, not a bug).
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("icon")
    if prop is None:
        return None

    icon = layer.get("layout", {}).get(prop)
    return icon if isinstance(icon, str) else None
```

3. Replace the module docstring (lines 1-33) with:

```python
"""
Metadata extractor for MapLibre style layers.

Extracts, per style layer, the `Part` fields defined by
GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.3 (kind, color, opacity, width,
dasharray, radius, icon) to support automated legend rendering. One Part
per style layer — no merging, no "primary layer" selection (§5.3: "Kein
Merge mehrerer Style-Layer zu einem Part und keine Prioritäts-Auswahl
eines 'Primär-Layers' mehr").

Ported from geodata-overlays/scripts/layer_metadata_extractor.py per
GEODATA_PLUGIN_STANDARD.md §5.8 ("einfach übernehmen"), with two
deviations required by openskimap's style but absent from the upstream
original (geodata-overlays never uses either of them):

1. extract_part_color/extract_categorized_items resolve a top-level
   `case` expression (openskimap's difficulty/status colors are nested
   case/match expressions, not flat color strings or plain
   interpolate/match) before classifying the paint property — resolution
   always picks the "europe" branch (DACH is this project's target
   audience; see CLAUDE.md), falling back to the case's else-branch if no
   `difficulty_convention == "europe"` condition is present. Without
   this, e.g. `ski-runs-downhill-casing`'s Part.color would be null
   instead of the correctly resolved fixed white, and
   `ski-runs-nordic-casing`'s would be null instead of a
   `{mode: "scale"}` reference.
2. `circle` is a supported `kind` (circle-color/circle-opacity/
   circle-radius) — openskimap uses circle layers for ski_spots and the
   low-zoom ski-area markers. GEODATA_PLUGIN_STANDARD.md's own kind
   table documents this directly as of v2.0.0 (§5.3), unlike v1.1.0
   where it required a local deviation.
"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/test_layer_metadata_extractor.py
git commit -m "refactor(layer-list): finish layer_metadata_extractor.py v2.0 migration, remove v1.1/dead functions"
```

---

### Task 4: `generate_layer_list.py` — `_build_render` + `_build_legend_sections` rewrite

**Files:**
- Modify: `scripts/generate_layer_list.py` — update imports (lines 34-42), extend `GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS` (lines 106-114), replace `_group_metadata` (117-166) with `_build_render`, replace `_build_legend_sections` (169-212), update `build_layer_list` (215-290)
- Test: `scripts/test_generate_layer_list.py` — full rewrite

**Interfaces:**
- Consumes: `determine_part_kind`, `extract_part_color`, `extract_categorized_items`, `extract_part_opacity`, `extract_part_width`, `extract_part_dasharray`, `extract_part_radius`, `extract_part_icon` (Tasks 1-3); `log_warn` from `scripts/ci/utils.py` (unchanged import).
- Produces: `_build_render(group_layers: list[dict], group_key: str, scale_items: dict) -> list[dict]`, `_build_legend_sections(scale_items: dict) -> list[dict] | None`, `build_layer_list(...) -> dict` with `"version": "2.0"` and `groups[].render` instead of the old flat fields.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `scripts/test_generate_layer_list.py` with:

```python
import json
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import generate_layer_list
from generate_layer_list import _build_render, _build_legend_sections, build_layer_list

STYLE_PATH = os.path.join(os.path.dirname(__file__), "..", "styles", "openskimap-style.json")


class BuildRenderTests(unittest.TestCase):
    def setUp(self):
        self._original_scale_map = generate_layer_list.GROUP_LEGEND_SCALE
        generate_layer_list.GROUP_LEGEND_SCALE = {"group-a": "test-scale"}

    def tearDown(self):
        generate_layer_list.GROUP_LEGEND_SCALE = self._original_scale_map

    def test_casing_and_line_become_separate_outline_and_line_parts(self):
        group_layers = [
            {
                "id": "ski-lifts-casing",
                "type": "line",
                "paint": {
                    "line-color": "hsl(0, 0%, 100%)",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1.8, 14, 5.0],
                },
            },
            {
                "id": "ski-lifts-line",
                "type": "line",
                "paint": {
                    "line-color": ["match", ["get", "status"], "operating", "hsl(0, 82%, 42%)", "hsl(0, 53%, 42%)"],
                    "line-opacity": 0.8,
                    "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.8, 14, 3.0],
                },
            },
        ]
        render = _build_render(group_layers, "group-without-scale", {})
        self.assertEqual(len(render), 2)
        self.assertEqual(render[0]["kind"], "outline")
        self.assertEqual(render[0]["color"], {"mode": "fixed", "value": "hsl(0, 0%, 100%)"})
        self.assertEqual(render[0]["width"], 5.0)
        self.assertEqual(render[1]["kind"], "line")
        self.assertEqual(render[1]["opacity"], 0.8)
        self.assertEqual(render[1]["width"], 3.0)

    def test_categorized_color_without_scale_config_warns_and_nulls_color(self):
        group_layers = [
            {
                "id": "unconfigured-fill",
                "type": "fill",
                "paint": {"fill-color": ["match", ["get", "x"], "a", "#111", "#222"]},
            },
        ]
        scale_items = {}
        with unittest.mock.patch("generate_layer_list.log_warn") as mock_warn:
            render = _build_render(group_layers, "group-without-scale", scale_items)
            mock_warn.assert_called_once()
        self.assertIsNone(render[0]["color"])
        self.assertEqual(scale_items, {})

    def test_categorized_color_with_scale_config_references_scale_id(self):
        group_layers = [
            {
                "id": "a-fill",
                "type": "fill",
                "paint": {"fill-color": ["match", ["get", "x"], "a", "#111", "#222"]},
            },
        ]
        scale_items = {}
        render = _build_render(group_layers, "group-a", scale_items)
        self.assertEqual(render[0]["color"], {"mode": "scale", "scale_id": "test-scale"})
        self.assertEqual(
            scale_items["test-scale"],
            [{"label": "A", "color": "#111"}, {"label": "Sonstige", "color": "#222"}],
        )

    def test_drifted_items_within_group_logs_warning_keeps_first(self):
        group_layers = [
            {"id": "a1", "type": "fill", "paint": {"fill-color": ["match", ["get", "x"], "a", "#111", "#222"]}},
            {"id": "a2", "type": "line", "paint": {"line-color": ["match", ["get", "x"], "a", "#999", "#222"]}},
        ]
        scale_items = {}
        with unittest.mock.patch("generate_layer_list.log_warn") as mock_warn:
            _build_render(group_layers, "group-a", scale_items)
            mock_warn.assert_called_once()
        self.assertEqual(
            scale_items["test-scale"],
            [{"label": "A", "color": "#111"}, {"label": "Sonstige", "color": "#222"}],
        )

    def test_skips_layers_without_mapped_kind(self):
        group_layers = [{"id": "raster-1", "type": "raster", "paint": {}}]
        self.assertEqual(_build_render(group_layers, "group-a", {}), [])

    def test_symbol_layer_with_icon_image_becomes_icon_kind(self):
        group_layers = [
            {"id": "lift-stations-icon", "type": "symbol", "layout": {"icon-image": "aerialway-station-11"}},
        ]
        render = _build_render(group_layers, "group-a", {})
        self.assertEqual(render[0]["kind"], "icon")
        self.assertEqual(render[0]["icon"], "aerialway-station-11")

    def test_text_only_symbol_layer_is_text_kind(self):
        group_layers = [
            {
                "id": "ski-lifts-labels",
                "type": "symbol",
                "layout": {"text-field": ["get", "name"]},
                "paint": {"text-color": "#2c3e50"},
            },
        ]
        render = _build_render(group_layers, "group-a", {})
        self.assertEqual(render[0]["kind"], "text")
        self.assertIsNone(render[0]["icon"])
        self.assertEqual(render[0]["color"], {"mode": "fixed", "value": "#2c3e50"})


class BuildLegendSectionsTests(unittest.TestCase):
    def setUp(self):
        self._original_labels = generate_layer_list.LEGEND_SCALE_LABELS
        generate_layer_list.LEGEND_SCALE_LABELS = {"test-scale": "Test"}

    def tearDown(self):
        generate_layer_list.LEGEND_SCALE_LABELS = self._original_labels

    def test_builds_one_section_per_scale_id(self):
        scale_items = {"test-scale": [{"label": "A", "color": "#111"}]}
        sections = _build_legend_sections(scale_items)
        self.assertEqual(
            sections, [{"id": "test-scale", "label": "Test", "items": [{"label": "A", "color": "#111"}]}]
        )

    def test_empty_map_returns_none(self):
        self.assertIsNone(_build_legend_sections({}))


class BuildLayerListRealStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STYLE_PATH, encoding="utf-8") as f:
            style_data = json.load(f)
        cls.result = build_layer_list(style_data, "openskimap", "OpenSkiMap", "openskimap.pmtiles")
        cls.groups_by_key = {g["template"]: g for g in cls.result["styles"][0]["groups"]}

    def test_schema_version_is_2_0(self):
        self.assertEqual(self.result["version"], "2.0")

    def test_group_names_are_german(self):
        self.assertEqual(self.groups_by_key["ski-runs-downhill"]["name"], "Pisten")
        self.assertEqual(self.groups_by_key["ski-runs-nordic"]["name"], "Loipen")
        self.assertEqual(self.groups_by_key["ski-runs-skitour"]["name"], "Skitouren")
        self.assertEqual(self.groups_by_key["ski-runs-other"]["name"], "Sonstige Strecken")
        self.assertEqual(self.groups_by_key["ski-areas-alpine"]["name"], "Skigebiete (Alpin)")
        self.assertEqual(self.groups_by_key["ski-areas-nordic"]["name"], "Skigebiete (Nordisch)")
        self.assertEqual(self.groups_by_key["ski-spots"]["name"], "Ski-Spots")
        self.assertEqual(self.groups_by_key["ski-lifts"]["name"], "Lifte")

    def test_ski_lifts_render_parts(self):
        lifts = self.groups_by_key["ski-lifts"]
        kinds = [p["kind"] for p in lifts["render"]]
        self.assertEqual(kinds, ["outline", "line", "line", "line", "line", "text", "icon"])

        outline_part = lifts["render"][0]
        self.assertEqual(outline_part["color"], {"mode": "fixed", "value": "hsl(0, 0%, 100%)"})
        self.assertEqual(outline_part["width"], 5.0)

        line_parts = [p for p in lifts["render"] if p["kind"] == "line"]
        for part in line_parts:
            self.assertEqual(part["color"], {"mode": "scale", "scale_id": "ski-lift-status-v1"})
            self.assertEqual(part["opacity"], 0.8)
        self.assertEqual([p["width"] for p in line_parts], [3.0, 1.98, 3.0, 1.98])

        icon_part = lifts["render"][-1]
        self.assertEqual(icon_part["kind"], "icon")
        self.assertIsNone(icon_part["color"])
        self.assertIsNone(icon_part["icon"])  # icon-image is a match expression, not literal

    def test_ski_runs_downhill_casing_is_fixed_not_scale(self):
        downhill = self.groups_by_key["ski-runs-downhill"]
        parts_by_layer = dict(zip(downhill["style_layers"], downhill["render"]))
        self.assertEqual(
            parts_by_layer["ski-runs-downhill-casing"]["color"],
            {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
        )
        self.assertEqual(
            parts_by_layer["ski-runs-downhill-line"]["color"],
            {"mode": "scale", "scale_id": "ski-difficulty-v1"},
        )

    def test_ski_runs_nordic_casing_carries_difficulty_scale(self):
        # Asymmetric vs. downhill: nordic's casing (not its line) is the
        # difficulty-colored part — design doc 2026-08-14, Untersuchung Punkt 1.
        nordic = self.groups_by_key["ski-runs-nordic"]
        parts_by_layer = dict(zip(nordic["style_layers"], nordic["render"]))
        self.assertEqual(parts_by_layer["ski-runs-nordic-casing"]["kind"], "outline")
        self.assertEqual(
            parts_by_layer["ski-runs-nordic-casing"]["color"],
            {"mode": "scale", "scale_id": "ski-difficulty-v1"},
        )
        self.assertEqual(parts_by_layer["ski-runs-nordic-line"]["kind"], "line")
        self.assertEqual(
            parts_by_layer["ski-runs-nordic-line"]["color"],
            {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
        )

    def test_ski_spots_uses_spot_type_scale(self):
        spots = self.groups_by_key["ski-spots"]
        self.assertEqual(len(spots["render"]), 1)
        part = spots["render"][0]
        self.assertEqual(part["kind"], "circle")
        self.assertEqual(part["color"], {"mode": "scale", "scale_id": "ski-spot-type-v1"})
        self.assertEqual(part["radius"], 4)

    def test_ski_areas_alpine_circle_has_no_scale(self):
        alpine = self.groups_by_key["ski-areas-alpine"]
        circle_part = next(p for p in alpine["render"] if p["kind"] == "circle")
        self.assertEqual(circle_part["color"], {"mode": "fixed", "value": "#3085fe"})
        self.assertEqual(circle_part["radius"], 6)

    def test_legend_sections_has_three_scales(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})
        self.assertEqual(sections_by_id["ski-difficulty-v1"]["label"], "Schwierigkeitsgrade")
        self.assertEqual(sections_by_id["ski-lift-status-v1"]["label"], "Lift-Status")
        self.assertEqual(sections_by_id["ski-spot-type-v1"]["label"], "Spot-Typ")
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-difficulty-v1"]["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Expert", "Freeride", "Extreme", "Sonstige"],
        )
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-lift-status-v1"]["items"]],
            ["Operating", "Proposed", "Planned", "Construction", "Disused", "Abandoned", "Sonstige"],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: `ImportError` (`_build_render`/`_build_legend_sections` don't have this signature yet) or `AttributeError`/`KeyError` once imports are fixed enough to run.

- [ ] **Step 3: Implement**

In `scripts/generate_layer_list.py`:

1. Replace the `layer_metadata_extractor` import block (lines 34-42) with:

```python
from layer_metadata_extractor import (
    determine_part_kind,
    extract_part_color,
    extract_categorized_items,
    extract_part_opacity,
    extract_part_width,
    extract_part_dasharray,
    extract_part_radius,
    extract_part_icon,
)
```

2. Extend `GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS` (lines 106-114):

```python
# group key -> shared legend_scale_id (GEODATA_PLUGIN_STANDARD.md v2.0.0
# §5.5). All four run-category groups render categorized colors from the
# same difficulty match expression (verified byte-identical against
# styles/openskimap-style.json — see design doc 2026-08-14), so they share
# one central legend. ski-lifts (status) and ski-spots (spot_type) each
# get their own scale, newly introduced with the v2.0 migration (v1.1 only
# had ungrouped per-group legend_items for these two).
GROUP_LEGEND_SCALE = {
    "ski-runs-downhill": "ski-difficulty-v1",
    "ski-runs-nordic": "ski-difficulty-v1",
    "ski-runs-skitour": "ski-difficulty-v1",
    "ski-runs-other": "ski-difficulty-v1",
    "ski-lifts": "ski-lift-status-v1",
    "ski-spots": "ski-spot-type-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
    "ski-lift-status-v1": "Lift-Status",
    "ski-spot-type-v1": "Spot-Typ",
}
```

3. Replace `_group_metadata` (lines 117-166) with:

```python
def _build_render(group_layers, group_key, scale_items):
    """
    Build the render:Array<Part> list for one group (GEODATA_PLUGIN_STANDARD.md
    v2.0.0 §5.3): one Part per layer in group_layers, in style order. Layers
    without a mapped kind (determine_part_kind returns None) are skipped, so
    render can be shorter than group_layers.

    A Part whose color is categorized (extract_part_color returns
    "categorized") looks up GROUP_LEGEND_SCALE[group_key]:
      - configured: color becomes {"mode": "scale", "scale_id": ...}; the
        Part's legend items are recorded into scale_items[scale_id] on
        first occurrence. A later Part (in this group or any other) sharing
        the same scale_id with different items logs a warning instead of
        raising (§5.5) — first-seen items win.
      - missing (§5.5 error case — a categorized color with no configured
        scale): log_warn(...), color set to None instead of a scale
        reference. No build abort.

    Args:
        group_layers (list): MapLibre layer objects belonging to one group,
            in style order
        group_key (str): key into GROUP_LEGEND_SCALE
        scale_items (dict): scale_id -> [{"label", "color"}, ...], mutated
            in place; shared across all groups so cross-group scale sharing
            and within-group multi-Part scale sharing use the same
            first-seen/warn-on-drift logic

    Returns:
        list[dict]: Part dicts per §5.3
    """
    parts = []
    for layer in group_layers:
        kind = determine_part_kind(layer)
        if kind is None:
            continue

        color = extract_part_color(layer, kind)
        if color == "categorized":
            scale_id = GROUP_LEGEND_SCALE.get(group_key)
            if scale_id is None:
                log_warn(
                    f"group '{group_key}': layer '{layer.get('id')}' has a categorized "
                    f"color but no GROUP_LEGEND_SCALE entry — color set to null."
                )
                color = None
            else:
                items = extract_categorized_items(layer, kind)
                if scale_id not in scale_items:
                    scale_items[scale_id] = items
                elif items != scale_items[scale_id]:
                    log_warn(
                        f"legend_scale_id '{scale_id}': layer '{layer.get('id')}' in group "
                        f"'{group_key}' has legend items differing from the first layer "
                        f"sharing this scale — layer-list.json will use the first layer's items."
                    )
                color = {"mode": "scale", "scale_id": scale_id}

        parts.append({
            "kind": kind,
            "color": color,
            "opacity": extract_part_opacity(layer, kind),
            "width": extract_part_width(layer, kind),
            "dasharray": extract_part_dasharray(layer, kind),
            "radius": extract_part_radius(layer, kind),
            "icon": extract_part_icon(layer, kind),
        })

    return parts
```

4. Replace `_build_legend_sections` (now at a shifted line range) with:

```python
def _build_legend_sections(scale_items):
    """
    Turn the scale_id -> items map collected by _build_render into the
    top-level legend_sections list (GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.6).

    Args:
        scale_items (dict): scale_id -> [{"label", "color"}, ...]

    Returns:
        list[dict] | None: [{"id", "label", "items"}, ...] in first-seen
            order, or None if no Part referenced a scale.
    """
    if not scale_items:
        return None

    return [
        {"id": scale_id, "label": LEGEND_SCALE_LABELS[scale_id], "items": items}
        for scale_id, items in scale_items.items()
    ]
```

5. Replace `build_layer_list` with:

```python
def build_layer_list(style_data, style_id, name, pmtiles_path):
    """
    Build the layer-list.json document for one style.

    Args:
        style_data (dict): parsed MapLibre style JSON
        style_id (str): matches the manifest dataset's "id"
        name (str): matches the manifest dataset's "name"
        pmtiles_path (str): path relative to dist/pmtiles/, e.g. "openskimap.pmtiles"

    Returns:
        dict: {"version": "2.0", "styles": [...], "legend_sections": [...] | None}
            per GEODATA_PLUGIN_STANDARD.md v2.0.0 §5

    Raises:
        KeyError: a style layer's id is not in GROUP_MAP (see module docstring)
    """
    groups_dict = {}
    group_layers = {}

    for layer in style_data.get("layers", []):
        layer_id = layer.get("id")
        source_layer = layer.get("source-layer")
        if not layer_id or not source_layer:
            continue

        if layer_id not in GROUP_MAP:
            raise KeyError(
                f"style layer '{layer_id}' has no entry in GROUP_MAP — "
                "add it so it's included in layer-list.json"
            )
        group_key = GROUP_MAP[layer_id]

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

        group = groups_dict[group_key]
        if source_layer not in group["source_layers"]:
            group["source_layers"].append(source_layer)
        group["style_layers"].append(layer_id)
        group_layers[group_key].append(layer)

    scale_items = {}
    for group_key, group in groups_dict.items():
        group["render"] = _build_render(group_layers[group_key], group_key, scale_items)

    legend_sections = _build_legend_sections(scale_items)

    return {
        "version": "2.0",
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

(`generate_layer_list()` and the `__main__` block at the bottom of the file are unchanged — they only pass through `build_layer_list`'s return value.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: all tests pass.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests across all three files pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "feat(layer-list): rewrite generate_layer_list.py for v2.0 render-parts schema"
```

---

### Task 5: Documentation — `CHANGELOG.md` + `docs/TODO.md`

**Files:**
- Modify: `CHANGELOG.md` (extend the `[Unreleased]` block added by the submodule-bump commit `066fcc7`)
- Modify: `docs/TODO.md` (resolve the "v2.0-Migration" entry added by commit `066fcc7`, move it to `docs/TODO_ARCHIVE.md`)

**Interfaces:** None (docs only).

- [ ] **Step 1: Extend the `[Unreleased]` CHANGELOG entry**

In `CHANGELOG.md`, the `[Unreleased] - 2026-08-14 08:36` block currently reads (from the submodule-bump commit):

```markdown
## [Unreleased] - 2026-08-14 08:36

### Changed
- Submodul `geodata-plugin-standard` von v1.1.0 auf v2.0.0 gebumpt. **Breaking
  Change im Standard**: §5-Layer-Listen-Spezifikation von Einzel-Property-Paint
  (`color`/`width`/`dasharray`/`outline_*`) auf ein generisches
  `render: Array<Part>`-Modell umgestellt, Schema-Version "2.0". Dieses Repo
  erzeugt `dist/layer-list.json` noch nach dem alten v1.1-Schema (siehe
  `docs/TODO.md`) — die Extractor-Skripte sind noch nicht auf das neue Modell
  migriert.
```

Replace the last sentence ("Dieses Repo erzeugt ... migriert.") and append a new bullet, so the block reads:

```markdown
## [Unreleased] - 2026-08-14 08:36

### Changed
- Submodul `geodata-plugin-standard` von v1.1.0 auf v2.0.0 gebumpt. **Breaking
  Change im Standard**: §5-Layer-Listen-Spezifikation von Einzel-Property-Paint
  (`color`/`width`/`dasharray`/`outline_*`) auf ein generisches
  `render: Array<Part>`-Modell umgestellt, Schema-Version "2.0".
- `dist/layer-list.json` auf das neue Schema migriert (`scripts/layer_metadata_extractor.py`,
  `scripts/generate_layer_list.py`, Design-Dokument
  `docs/superpowers/specs/2026-08-14-render-parts-v2.0-migration-design.md`):
  jeder Style-Layer einer Gruppe wird jetzt unabhängig zu einem `Part` im
  `render`-Array (kein Primär-Layer-Merge mehr), `color` wird zum
  `{mode, value|scale_id}`-Objekt. Zwei neue zentrale Farbskalen
  `ski-lift-status-v1` ("Lift-Status") und `ski-spot-type-v1` ("Spot-Typ"),
  die in v1.1 nur als ungruppierte `legend_items` ohne Skalen-Kennung
  vorlagen. `"version": "1.1"` → `"2.0"`.

### Known Issues
- `circle-stroke-color`/`circle-stroke-width` (auf `ski-areas-*-circle` und
  `ski-spots`) haben im neuen `Part`-Modell kein Feld — Standard-seitige
  Lücke, gemeldet als
  [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3).
  Datenverlust bewusst in Kauf genommen, bis der Standard nachzieht.
```

- [ ] **Step 2: Resolve the TODO entry**

In `docs/TODO.md`, find the entry titled `## \`layer-list.json\` auf \`geodata-plugin-standard\` v2.0.0 (render-Parts-Modell) migrieren` (added by commit `066fcc7`). Cut it out of `docs/TODO.md` entirely.

Append it to the end of `docs/TODO_ARCHIVE.md` (read the file first to match its existing entry format — typically a `## <title>` heading plus a short "Erledigt am <date>: <one-line summary>" note), for example:

```markdown
## `layer-list.json` auf `geodata-plugin-standard` v2.0.0 (render-Parts-Modell) migrieren

Erledigt am 2026-08-14: `scripts/layer_metadata_extractor.py` und
`scripts/generate_layer_list.py` vollständig auf das
`render: Array<Part>`-Modell umgestellt (Design:
`docs/superpowers/specs/2026-08-14-render-parts-v2.0-migration-design.md`).
```

- [ ] **Step 3: Verify JSON/Markdown are still well-formed**

Run: `python3 -c "import re; assert '## \`layer-list.json\` auf' not in open('docs/TODO.md').read()"`
Expected: no output (assertion passes, meaning the entry is gone from `docs/TODO.md`).

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md docs/TODO.md docs/TODO_ARCHIVE.md
git commit -m "docs: changelog entry + TODO resolution for layer-list.json v2.0 migration"
```

---

### Task 6: Full verification

**Files:** None modified — verification only.

**Interfaces:** None.

- [ ] **Step 1: Run the complete test suite**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests pass (0 failures, 0 errors).

- [ ] **Step 2: Generate `dist/layer-list.json` against the real style and inspect it**

Run:
```bash
python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from generate_layer_list import build_layer_list
with open('styles/openskimap-style.json', encoding='utf-8') as f:
    style = json.load(f)
result = build_layer_list(style, 'openskimap', 'OpenSkiMap', 'openskimap.pmtiles')
print(json.dumps(result, indent=2, ensure_ascii=False))
" > /tmp/layer-list-v2.0-check.json
python3 -c "import json; json.load(open('/tmp/layer-list-v2.0-check.json'))" && echo "valid JSON"
```
Expected: `valid JSON` printed, no exceptions.

- [ ] **Step 3: Spot-check against the design doc's expected-result table**

Run:
```bash
python3 -c "
import json
data = json.load(open('/tmp/layer-list-v2.0-check.json'))
assert data['version'] == '2.0'
groups = {g['template']: g for g in data['styles'][0]['groups']}
assert len(data['legend_sections']) == 3
assert {s['id'] for s in data['legend_sections']} == {'ski-difficulty-v1', 'ski-lift-status-v1', 'ski-spot-type-v1'}
nordic = dict(zip(groups['ski-runs-nordic']['style_layers'], groups['ski-runs-nordic']['render']))
assert nordic['ski-runs-nordic-casing']['color'] == {'mode': 'scale', 'scale_id': 'ski-difficulty-v1'}
assert nordic['ski-runs-nordic-line']['color'] == {'mode': 'fixed', 'value': 'hsl(0, 0%, 100%)'}
print('spot-check OK')
"
```
Expected: `spot-check OK` printed, no `AssertionError`.

- [ ] **Step 4: Clean up the temp file**

Run: `rm /tmp/layer-list-v2.0-check.json`

No commit for this task — it's verification-only, confirming Tasks 1-5 are correct.

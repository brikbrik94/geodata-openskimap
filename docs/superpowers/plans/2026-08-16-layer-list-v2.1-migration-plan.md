# layer-list.json v2.1.0 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `dist/layer-list.json` generation from `GEODATA_PLUGIN_STANDARD.md` v2.0.0 to v2.1.0 conformance — add `stroke_color`/`stroke_width` to every `Part`, add `axis` to every `variants[]` entry, retaxonomize `ski-lifts`'s variants into two orthogonal axes, and resolve the deferred `snowmaking` gap via a new single-value axis.

**Architecture:** Two new extractor functions in `scripts/layer_metadata_extractor.py` (mirroring the existing `extract_part_color`/`extract_part_width` pair) feed two new Part fields wired into `scripts/generate_layer_list.py`'s `_build_render`. Separately, `GROUP_VARIANTS` (the hand-verified config mapping style-layer IDs to legend variants) gains an `axis` field per entry and a new `ski-lifts` shape; `GROUP_VARIANT_EXCLUDE` is deleted now that its only two use cases (nordic/downhill snowmaking) become ordinary single-value axis entries instead.

**Tech Stack:** Python 3 stdlib only (`unittest`), no dependencies.

**Spec:** `docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`

## Global Constraints

- Schema version string becomes `"2.1"` everywhere it's asserted or documented (was `"2.0"`).
- `Part` dicts are compared by exact `assertEqual` in several existing tests — every literal
  Part dict in test code must gain `"stroke_color": None, "stroke_width": None` (or real
  values for `circle`-kind Parts) or those tests will fail on a legitimate diff, not a bug.
- `stroke_color`/`stroke_width` are `null` for every `kind` except `"circle"` (from
  `circle-stroke-color`/`circle-stroke-width`); no style layer in this repo has a categorized
  (`interpolate`/`match`) `circle-stroke-color`, so no scale-wiring is needed for it (see spec's
  "Verworfene Alternative" section — this is a deliberate scope limit, not an oversight).
- Variant labels stay German, matching the existing convention (`"In Betrieb"`, `"Beschneit"`, …).
- Git: stage files explicitly (never `git add -A`); commit messages use Conventional Commits
  prefixes; `CHANGELOG.md` entries use the `## [Unreleased] - YYYY-MM-DD HH:mm` journal format.
- Verification command (run at the end of every task touching Python):
  `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`

---

### Task 1: Commit the already-bumped `geodata-plugin-standard` submodule pointer

The submodule was already checked out to tag `v2.1.0` (commit `40a4044`) in the working tree
during an earlier investigation this session, but never committed. Commit it now, on its own,
before any code changes — per `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4's submodule-path
staging caution, a submodule pointer bump should be its own explicit, isolated commit, not
bundled with unrelated file changes.

**Files:**
- Modify: `geodata-plugin-standard` (submodule gitlink, already at `40a4044` in the working tree)

**Interfaces:** None — this is a git-only task, no code.

- [ ] **Step 1: Verify the submodule is still at the expected commit**

Run: `git -C geodata-plugin-standard log -1 --oneline`
Expected: `40a4044 docs: finale Review-Findings für v2.1.0 beheben (...)`

If it shows a different commit (someone else touched it), stop and re-check with the user
before proceeding — do not silently re-checkout.

- [ ] **Step 2: Stage and commit the submodule pointer**

```bash
git add geodata-plugin-standard
git commit -m "$(cat <<'EOF'
chore(submodule): bump geodata-plugin-standard to v2.1.0

Adds stroke_color/stroke_width on circle Parts and the variants[].axis
field to the layer-list.json spec (geodata-plugin-standard#3, #4).
Code migration to match follows in subsequent commits.
EOF
)"
```

- [ ] **Step 3: Verify**

Run: `git log -1 --stat` and `git status --short`
Expected: the commit shows exactly one changed path (`geodata-plugin-standard`), working tree
otherwise clean.

---

### Task 2: Add `extract_part_stroke_color`/`extract_part_stroke_width` to the extractor

**Files:**
- Modify: `scripts/layer_metadata_extractor.py`
- Test: `scripts/test_layer_metadata_extractor.py`

**Interfaces:**
- Consumes: `PART_FIELDS_BY_KIND` (existing module-level dict, `layer_metadata_extractor.py:42-55`)
- Produces: `extract_part_stroke_color(layer: dict, kind: str) -> dict | None`,
  `extract_part_stroke_width(layer: dict, kind: str) -> float | int | None` — consumed by
  Task 3's `generate_layer_list.py` changes.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_layer_metadata_extractor.py`. First update the import block at the top
(lines 6-15) to also import the two new functions:

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
    extract_part_stroke_color,
    extract_part_stroke_width,
)
```

Then append these two new test classes right before the `if __name__ == "__main__":` line
(currently line 250):

```python
class ExtractPartStrokeColorTests(unittest.TestCase):
    def test_literal_color_on_circle_is_fixed(self):
        layer = {"type": "circle", "paint": {"circle-stroke-color": "#ffffff"}}
        self.assertEqual(extract_part_stroke_color(layer, "circle"), {"mode": "fixed", "value": "#ffffff"})

    def test_kind_without_stroke_color_field_returns_none(self):
        layer = {"type": "fill", "paint": {"fill-color": "#000"}}
        self.assertIsNone(extract_part_stroke_color(layer, "fill"))

    def test_missing_property_on_circle_returns_none(self):
        layer = {"type": "circle", "paint": {"circle-color": "#000"}}
        self.assertIsNone(extract_part_stroke_color(layer, "circle"))

    def test_expression_value_returns_none(self):
        # No style layer in this repo has a categorized circle-stroke-color,
        # and there is no scale-wiring for it (see design doc) — treated the
        # same as any other unsupported form, not as "categorized".
        layer = {
            "type": "circle",
            "paint": {"circle-stroke-color": ["match", ["get", "x"], "a", "#111", "#222"]},
        }
        self.assertIsNone(extract_part_stroke_color(layer, "circle"))


class ExtractPartStrokeWidthTests(unittest.TestCase):
    def test_literal_number_on_circle(self):
        layer = {"type": "circle", "paint": {"circle-stroke-width": 1}}
        self.assertEqual(extract_part_stroke_width(layer, "circle"), 1)

    def test_interpolate_returns_highest_zoom_stop(self):
        layer = {
            "type": "circle",
            "paint": {"circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 6, 0.5, 14, 2.0]},
        }
        self.assertEqual(extract_part_stroke_width(layer, "circle"), 2.0)

    def test_kind_without_stroke_width_field_returns_none(self):
        layer = {"type": "line", "paint": {"line-width": 2}}
        self.assertIsNone(extract_part_stroke_width(layer, "line"))

    def test_missing_property_on_circle_returns_none(self):
        layer = {"type": "circle", "paint": {"circle-color": "#000"}}
        self.assertIsNone(extract_part_stroke_width(layer, "circle"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: `ImportError: cannot import name 'extract_part_stroke_color'` (or similar) — the
functions don't exist yet.

- [ ] **Step 3: Add `stroke_color`/`stroke_width` to `PART_FIELDS_BY_KIND`'s `"circle"` entry**

In `scripts/layer_metadata_extractor.py`, change:

```python
    "circle": {"color": "circle-color", "opacity": "circle-opacity", "radius": "circle-radius"},
```

to:

```python
    "circle": {
        "color": "circle-color", "opacity": "circle-opacity", "radius": "circle-radius",
        "stroke_color": "circle-stroke-color", "stroke_width": "circle-stroke-width",
    },
```

- [ ] **Step 4: Implement `extract_part_stroke_color`**

Insert immediately after `extract_part_color` (which currently ends at line 150, right before
the `extract_categorized_items` function):

```python
def extract_part_stroke_color(layer, kind):
    """
    Extract a Part's `stroke_color` field per GEODATA_PLUGIN_STANDARD.md
    v2.1.0 §5.3: only kind:"circle" has a stroke_color field (from
    circle-stroke-color); every other kind gets None.

    Unlike extract_part_color, this does not classify interpolate/match
    expressions as "categorized" — no style layer in this repo has a
    categorized circle-stroke-color, and generate_layer_list.py's scale
    resolution (GROUP_LEGEND_SCALE) only wires up `color`, not
    `stroke_color`. A non-literal expression is treated like any other
    unsupported form and returns None (same as extract_part_dasharray's
    contract), not like extract_part_color's "categorized" marker.

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        dict | None: {"mode": "fixed", "value": str} for a literal color;
            None if the kind has no stroke_color field, the property is
            unset, or its value isn't a literal string.
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("stroke_color")
    if prop is None:
        return None

    value = layer.get("paint", {}).get(prop)
    return {"mode": "fixed", "value": value} if isinstance(value, str) else None
```

- [ ] **Step 5: Implement `extract_part_stroke_width`**

Insert immediately after `extract_part_width` (which currently ends at line 216, right before
`extract_part_radius`):

```python
def extract_part_stroke_width(layer, kind):
    """Kind-specific circle-stroke-width (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no stroke_width field
    (only "circle" does)."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("stroke_width")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))
```

- [ ] **Step 6: Update the module docstring's field list**

In `scripts/layer_metadata_extractor.py`, line 6, change:

```python
Extracts, per style layer, the `Part` fields defined by
GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.3 (kind, color, opacity, width,
dasharray, radius, icon) to support automated legend rendering. One Part
```

to:

```python
Extracts, per style layer, the `Part` fields defined by
GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3 (kind, color, stroke_color, opacity,
width, dasharray, radius, stroke_width, icon) to support automated legend
rendering. One Part
```

Also update the two other "v2.0.0 §5.3" references that describe the *current* kind table
(not a historical migration note) to "v2.1.0 §5.3": line 39 (`PART_FIELDS_BY_KIND` comment)
and line 61 (`determine_part_kind` docstring). Leave line 31's "as of v2.0.0" reference
unchanged — it correctly describes when `circle` support was historically introduced, not the
current spec version.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_layer_metadata_extractor -v`
Expected: all tests PASS, including the 8 new ones.

- [ ] **Step 8: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/test_layer_metadata_extractor.py
git commit -m "$(cat <<'EOF'
feat(layer-list): extract circle-stroke-color/-width per v2.1.0 §5.3

New extract_part_stroke_color/extract_part_stroke_width, mirroring the
existing color/width extractors. Not yet wired into generate_layer_list.py.
EOF
)"
```

---

### Task 3: Wire `stroke_color`/`stroke_width` into `generate_layer_list.py`, bump version to `"2.1"`

**Files:**
- Modify: `scripts/generate_layer_list.py`
- Test: `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: `extract_part_stroke_color`, `extract_part_stroke_width` (Task 2)
- Produces: every `Part` dict built by `_build_render` now has `stroke_color`/`stroke_width`
  keys; `build_layer_list(...)["version"] == "2.1"`. Task 4 builds on this unchanged.

- [ ] **Step 1: Update the import block**

In `scripts/generate_layer_list.py`, change:

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

to:

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
    extract_part_stroke_color,
    extract_part_stroke_width,
)
```

- [ ] **Step 2: Wire the two fields into the Part dict**

In `_build_render`, change:

```python
        parts.append({
            "kind": kind,
            "color": color,
            "opacity": extract_part_opacity(layer, kind),
            "width": extract_part_width(layer, kind),
            "dasharray": extract_part_dasharray(layer, kind),
            "radius": extract_part_radius(layer, kind),
            "icon": extract_part_icon(layer, kind),
        })
```

to:

```python
        parts.append({
            "kind": kind,
            "color": color,
            "stroke_color": extract_part_stroke_color(layer, kind),
            "opacity": extract_part_opacity(layer, kind),
            "width": extract_part_width(layer, kind),
            "dasharray": extract_part_dasharray(layer, kind),
            "radius": extract_part_radius(layer, kind),
            "stroke_width": extract_part_stroke_width(layer, kind),
            "icon": extract_part_icon(layer, kind),
        })
```

(Field order matches `GEODATA_PLUGIN_STANDARD.md` v2.1.0 §5.3's `Part` block for readability;
dict equality in tests doesn't care about key order.)

- [ ] **Step 3: Bump the version string**

Change:

```python
    return {
        "version": "2.0",
```

to:

```python
    return {
        "version": "2.1",
```

- [ ] **Step 4: Update `build_layer_list`'s docstring**

Change:

```python
    Returns:
        dict: {"version": "2.0", "styles": [...], "legend_sections": [...] | None}
            per GEODATA_PLUGIN_STANDARD.md v2.0.0 §5. Each group additionally
            carries the locally-proposed `variants` field (not part of the
            v2.0.0 standard; tracked as geodata-plugin-standard#4).
```

to:

```python
    Returns:
        dict: {"version": "2.1", "styles": [...], "legend_sections": [...] | None}
            per GEODATA_PLUGIN_STANDARD.md v2.1.0 §5. Each group's `variants[]`
            entries carry an `axis` field per the standard's §5.3 model;
            `axis` naming/grouping is a reference-implementation judgment
            call the standard explicitly leaves open. `source_layers`
            (plural) remains a locally-proposed extension, not part of the
            standard.
```

- [ ] **Step 5: Update the remaining `v2.0.0` docstring references describing the current Part/legend model**

Change line 169 (`_build_render`'s docstring) from `v2.0.0 §5.3` to `v2.1.0 §5.3`, and line 307
(`_build_legend_sections`'s docstring) from `v2.0.0 §5.6` to `v2.1.0 §5.6`. Leave line 104's
`GROUP_LEGEND_SCALE` comment and line 109's "newly introduced with the v2.0 migration" note
unchanged — both correctly describe when that mechanism was historically introduced, not the
current spec version.

- [ ] **Step 6: Update every exact Part-dict test assertion to include `stroke_color`/`stroke_width`**

In `scripts/test_generate_layer_list.py`, every dict literal representing a full `Part` (as
opposed to assertions that only check individual fields like `render[0]["color"]`) needs the
two new keys added, or `assertEqual` will fail on an incomplete-but-otherwise-correct dict.

Update `test_ski_runs_nordic_has_two_mutually_exclusive_variants` (lines 340-354): change

```python
        self.assertEqual(nordic["variants"][0]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 3.0, "dasharray": None, "radius": None, "icon": None,
        }])
        self.assertEqual(nordic["variants"][1]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": None, "icon": None,
        }])
```

to:

```python
        self.assertEqual(nordic["variants"][0]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }])
        self.assertEqual(nordic["variants"][1]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [2, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }])
```

Update `test_ski_runs_nordic_snowmaking_excluded_entirely` (lines 356-366): change

```python
        self.assertNotIn(
            {"kind": "line", "color": {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"},
             "opacity": 1, "width": 1.5, "dasharray": None, "radius": None, "icon": None},
            all_parts,
        )
```

to:

```python
        self.assertNotIn(
            {"kind": "line", "color": {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"},
             "stroke_color": None, "opacity": 1, "width": 1.5, "dasharray": None,
             "radius": None, "stroke_width": None, "icon": None},
            all_parts,
        )
```

(This whole test is replaced in Task 4 — this edit just keeps it passing in the interim so
Task 3 is independently green.)

Update `test_ski_runs_downhill_has_four_variants_gladed_ungroomed_overlap` (lines 368-385):
change

```python
        gladed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "opacity": 1, "width": 3.0, "dasharray": [0.1, 4], "radius": None, "icon": None,
        }
        ungroomed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": None, "icon": None,
        }
```

to:

```python
        gladed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [0.1, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }
        ungroomed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [2, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }
```

Update `test_ski_lifts_casing_only_in_operating_variants` (lines 387-407): change

```python
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 5.0, "dasharray": None, "radius": None, "icon": None,
        }
```

to:

```python
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
```

(This whole test is replaced in Task 4 too — same interim reasoning as the snowmaking test.)

- [ ] **Step 7: Add `stroke_color`/`stroke_width` assertions to the two circle-Part real-style tests**

Update `test_ski_areas_alpine_circle_has_no_scale` (lines 319-323): change

```python
    def test_ski_areas_alpine_circle_has_no_scale(self):
        alpine = self.groups_by_key["ski-areas-alpine"]
        circle_part = next(p for p in alpine["render"] if p["kind"] == "circle")
        self.assertEqual(circle_part["color"], {"mode": "fixed", "value": "#3085fe"})
        self.assertEqual(circle_part["radius"], 6)
```

to:

```python
    def test_ski_areas_alpine_circle_has_no_scale(self):
        alpine = self.groups_by_key["ski-areas-alpine"]
        circle_part = next(p for p in alpine["render"] if p["kind"] == "circle")
        self.assertEqual(circle_part["color"], {"mode": "fixed", "value": "#3085fe"})
        self.assertEqual(circle_part["radius"], 6)
        self.assertEqual(circle_part["stroke_color"], {"mode": "fixed", "value": "#ffffff"})
        self.assertEqual(circle_part["stroke_width"], 1)
```

Update `test_ski_spots_uses_spot_type_scale` (lines 311-317): change

```python
    def test_ski_spots_uses_spot_type_scale(self):
        spots = self.groups_by_key["ski-spots"]
        self.assertEqual(len(spots["render"]), 1)
        part = spots["render"][0]
        self.assertEqual(part["kind"], "circle")
        self.assertEqual(part["color"], {"mode": "scale", "scale_id": "ski-spot-type-v1"})
        self.assertEqual(part["radius"], 4)
```

to:

```python
    def test_ski_spots_uses_spot_type_scale(self):
        spots = self.groups_by_key["ski-spots"]
        self.assertEqual(len(spots["render"]), 1)
        part = spots["render"][0]
        self.assertEqual(part["kind"], "circle")
        self.assertEqual(part["color"], {"mode": "scale", "scale_id": "ski-spot-type-v1"})
        self.assertEqual(part["radius"], 4)
        self.assertEqual(part["stroke_color"], {"mode": "fixed", "value": "#ffffff"})
        self.assertEqual(part["stroke_width"], 1)
```

- [ ] **Step 8: Bump the version assertion**

Rename `test_schema_version_is_2_0` (line 247-248) to `test_schema_version_is_2_1` and change
its body:

```python
    def test_schema_version_is_2_1(self):
        self.assertEqual(self.result["version"], "2.1")
```

- [ ] **Step 9: Run the full test module to verify it passes**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: all tests PASS (this task does not change variant *structure*, only adds two fields
and bumps the version — every test from Task 4's future replacements should still pass with
their old assertions plus the new keys).

- [ ] **Step 10: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(layer-list): wire stroke_color/stroke_width, bump schema to v2.1.0

Every Part now carries stroke_color/stroke_width (null except kind:circle).
variants[].axis retaxonomy follows in the next commit.
EOF
)"
```

---

### Task 4: Retaxonomize `GROUP_VARIANTS` into named axes, resolve the `snowmaking` gap

**Files:**
- Modify: `scripts/generate_layer_list.py`
- Test: `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: `_build_render` (unchanged signature from Task 3)
- Produces: `_build_render_and_variants(group_layers, group_key, scale_items) -> (render: list,
  variants: list[{"axis": str, "label": str, "render": list}] | None)` — the `variants` list
  items now always include `"axis"`. No other task depends on this beyond `build_layer_list`,
  which already calls it unchanged.

- [ ] **Step 1: Write the failing unit tests for axis-aware `_build_render_and_variants`**

In `scripts/test_generate_layer_list.py`, `BuildRenderAndVariantsTests`'s `setUp`/`tearDown`
(lines 146-152) reference `GROUP_VARIANT_EXCLUDE`, which this task removes from
`generate_layer_list.py`. Update them first:

```python
class BuildRenderAndVariantsTests(unittest.TestCase):
    def setUp(self):
        self._original_variants = generate_layer_list.GROUP_VARIANTS

    def tearDown(self):
        generate_layer_list.GROUP_VARIANTS = self._original_variants
```

Update `test_group_without_variants_config_returns_none_and_full_render` (lines 154-162):
remove the `generate_layer_list.GROUP_VARIANT_EXCLUDE = {}` line, keep the rest unchanged.

Update `test_variant_member_layers_split_from_shared_render` (lines 164-184): add `"axis"` to
both fixture entries and assert it's threaded through:

```python
    def test_variant_member_layers_split_from_shared_render(self):
        generate_layer_list.GROUP_VARIANTS = {
            "group-a": [
                {"axis": "test-axis", "label": "Variant 1", "style_layer_ids": ["v1"]},
                {"axis": "test-axis", "label": "Variant 2", "style_layer_ids": ["v2"]},
            ]
        }
        group_layers = [
            {"id": "shared", "type": "fill", "paint": {"fill-color": "#111"}},
            {"id": "v1", "type": "line", "paint": {"line-color": "#222"}},
            {"id": "v2", "type": "line", "paint": {"line-color": "#333"}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertEqual(len(render), 1)
        self.assertEqual(render[0]["color"], {"mode": "fixed", "value": "#111"})
        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0]["axis"], "test-axis")
        self.assertEqual(variants[0]["label"], "Variant 1")
        self.assertEqual(variants[0]["render"][0]["color"], {"mode": "fixed", "value": "#222"})
        self.assertEqual(variants[1]["axis"], "test-axis")
        self.assertEqual(variants[1]["label"], "Variant 2")
        self.assertEqual(variants[1]["render"][0]["color"], {"mode": "fixed", "value": "#333"})
```

Update `test_layer_can_belong_to_multiple_variants` (lines 186-201): add `"axis"` to both
fixture entries (same axis, since this test's whole point is two entries of the same axis
sharing a member layer):

```python
    def test_layer_can_belong_to_multiple_variants(self):
        generate_layer_list.GROUP_VARIANTS = {
            "group-a": [
                {"axis": "test-axis", "label": "Variant 1", "style_layer_ids": ["shared-member"]},
                {"axis": "test-axis", "label": "Variant 2", "style_layer_ids": ["shared-member", "v2"]},
            ]
        }
        group_layers = [
            {"id": "shared-member", "type": "line", "paint": {"line-color": "#111"}},
            {"id": "v2", "type": "line", "paint": {"line-color": "#222"}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertEqual(render, [])
        self.assertEqual(len(variants[0]["render"]), 1)
        self.assertEqual(len(variants[1]["render"]), 2)
```

Delete `test_excluded_layer_absent_from_render_and_every_variant` (lines 203-217) entirely —
`GROUP_VARIANT_EXCLUDE` no longer exists; its only two real-world use cases (nordic/downhill
snowmaking) become ordinary axis entries, verified by Step 6's new real-style tests instead.

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: `KeyError: 'axis'` in `test_variant_member_layers_split_from_shared_render` and
`test_layer_can_belong_to_multiple_variants` — `_build_render_and_variants` doesn't produce an
`"axis"` key yet. (The deleted test and the `setUp`/`tearDown` change should not by themselves
cause failures; the point of this step is confirming the two updated tests fail for the right
reason.)

- [ ] **Step 3: Replace `GROUP_VARIANTS` and delete `GROUP_VARIANT_EXCLUDE`**

In `scripts/generate_layer_list.py`, replace the entire block from the `GROUP_VARIANTS`
comment through the end of the `GROUP_VARIANT_EXCLUDE` dict (currently lines 125-163) with:

```python
# group key -> list of {"axis": ..., "label": ..., "style_layer_ids": [...]}
# — filter-based variants within the group, grouped by a named `axis` per
# GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3 (design docs: 2026-08-14
# legend-variants for the original shared/variant split, 2026-08-16 for this
# axis retaxonomy — geodata-plugin-standard#4, part of the standard as of
# v2.1.0). A style-layer-id CAN appear in more than one variant's list
# within the SAME axis when its MapLibre `filter` overlaps more than one
# entry's defining condition (e.g. ski-runs-downhill-gladed/-ungroomed both
# appear in the combined "Waldabfahrt, nicht präpariert" entry of the
# grooming-terrain axis) — but never across two DIFFERENT axis entries of
# the same group (e.g. ski-lifts-casing is only in the "status" axis's "In
# Betrieb" entry now, not duplicated into "access" — see design doc's
# paint-coupling investigation for why ski-lifts couldn't be split into
# fully independent per-layer axes). Style layers not listed in ANY variant
# here stay in the group's shared `render`. Groups not listed here at all
# get `variants: None` and unchanged `render` behavior.
GROUP_VARIANTS = {
    "ski-runs-nordic": [
        {"axis": "grooming", "label": "Gespurt", "style_layer_ids": ["ski-runs-nordic-line"]},
        {"axis": "grooming", "label": "Ungespurt", "style_layer_ids": ["ski-runs-nordic-ungroomed"]},
        {"axis": "snowmaking", "label": "Beschneit", "style_layer_ids": ["ski-runs-nordic-snowmaking"]},
    ],
    "ski-runs-downhill": [
        {"axis": "grooming-terrain", "label": "Präpariert",
         "style_layer_ids": ["ski-runs-downhill-line"]},
        {"axis": "grooming-terrain", "label": "Waldabfahrt",
         "style_layer_ids": ["ski-runs-downhill-gladed"]},
        {"axis": "grooming-terrain", "label": "Nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-ungroomed"]},
        {"axis": "grooming-terrain", "label": "Waldabfahrt, nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-gladed", "ski-runs-downhill-ungroomed"]},
        {"axis": "snowmaking", "label": "Beschneit",
         "style_layer_ids": ["ski-runs-downhill-snowmaking"]},
    ],
    "ski-lifts": [
        {"axis": "status", "label": "In Betrieb",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"axis": "status", "label": "Sonstiger Status",
         "style_layer_ids": ["ski-lifts-line-other"]},
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
}
```

Note `GROUP_VARIANT_EXCLUDE` is gone entirely — no replacement constant.

- [ ] **Step 4: Remove the exclusion step from `_build_render_and_variants` and add `axis`**

Change:

```python
def _build_render_and_variants(group_layers, group_key, scale_items):
    """
    Split a group's layers into a shared render list and, for groups
    configured in GROUP_VARIANTS, a list of mutually-exclusive variants
    (design doc 2026-08-14, legend-variants; geodata-plugin-standard#4).
    Layers listed in GROUP_VARIANT_EXCLUDE[group_key] are dropped entirely
    before any other processing.

    Args:
        group_layers (list): MapLibre layer objects belonging to one group,
            in style order (unfiltered)
        group_key (str): key into GROUP_VARIANTS/GROUP_VARIANT_EXCLUDE
        scale_items (dict): passed through to _build_render unchanged — see
            its docstring; the same dict is used for every _build_render
            call below so cross-group AND cross-variant scale sharing keep
            using the same first-seen/warn-on-drift logic

    Returns:
        tuple[list[dict], list[dict] | None]: (render, variants). variants
            is None when group_key has no GROUP_VARIANTS entry (render is
            then the complete Part list, unchanged from pre-variants
            behavior). Otherwise render holds only the Parts whose style
            layer is not a member of any variant.
    """
    excluded_ids = set(GROUP_VARIANT_EXCLUDE.get(group_key, []))
    layers = [layer for layer in group_layers if layer.get("id") not in excluded_ids]

    variant_defs = GROUP_VARIANTS.get(group_key)
    if not variant_defs:
        return _build_render(layers, group_key, scale_items), None

    variant_member_ids = set()
    for variant_def in variant_defs:
        variant_member_ids.update(variant_def["style_layer_ids"])

    shared_layers = [layer for layer in layers if layer.get("id") not in variant_member_ids]
    render = _build_render(shared_layers, group_key, scale_items)

    variants = [
        {
            "label": variant_def["label"],
            "render": _build_render(
                [layer for layer in layers if layer.get("id") in variant_def["style_layer_ids"]],
                group_key,
                scale_items,
            ),
        }
        for variant_def in variant_defs
    ]

    return render, variants
```

to:

```python
def _build_render_and_variants(group_layers, group_key, scale_items):
    """
    Split a group's layers into a shared render list and, for groups
    configured in GROUP_VARIANTS, a list of filter-based variants grouped by
    axis (design docs 2026-08-14 legend-variants, 2026-08-16 axis
    retaxonomy; geodata-plugin-standard#4, part of the standard as of
    v2.1.0).

    Args:
        group_layers (list): MapLibre layer objects belonging to one group,
            in style order
        group_key (str): key into GROUP_VARIANTS
        scale_items (dict): passed through to _build_render unchanged — see
            its docstring; the same dict is used for every _build_render
            call below so cross-group AND cross-variant scale sharing keep
            using the same first-seen/warn-on-drift logic

    Returns:
        tuple[list[dict], list[dict] | None]: (render, variants). variants
            is None when group_key has no GROUP_VARIANTS entry (render is
            then the complete Part list, unchanged from pre-variants
            behavior). Otherwise render holds only the Parts whose style
            layer is not a member of any variant, and each variants[] entry
            is {"axis": str, "label": str, "render": list[dict]}.
    """
    variant_defs = GROUP_VARIANTS.get(group_key)
    if not variant_defs:
        return _build_render(group_layers, group_key, scale_items), None

    variant_member_ids = set()
    for variant_def in variant_defs:
        variant_member_ids.update(variant_def["style_layer_ids"])

    shared_layers = [layer for layer in group_layers if layer.get("id") not in variant_member_ids]
    render = _build_render(shared_layers, group_key, scale_items)

    variants = [
        {
            "axis": variant_def["axis"],
            "label": variant_def["label"],
            "render": _build_render(
                [layer for layer in group_layers if layer.get("id") in variant_def["style_layer_ids"]],
                group_key,
                scale_items,
            ),
        }
        for variant_def in variant_defs
    ]

    return render, variants
```

- [ ] **Step 5: Run the unit tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: `BuildRenderAndVariantsTests` and `BuildRenderTests` PASS. The real-style tests
(`BuildLayerListRealStyleTests`) will now FAIL — expected, they assert the old 4-combo
`ski-lifts` shape and the excluded-snowmaking behavior. Fixed in the next step.

- [ ] **Step 6: Replace the real-style tests for the retaxonomized groups**

In `scripts/test_generate_layer_list.py`, `BuildLayerListRealStyleTests`:

Replace `test_ski_runs_nordic_has_two_mutually_exclusive_variants` (now updated in Task 3,
lines ~340-354) and delete `test_ski_runs_nordic_snowmaking_excluded_entirely` (lines
~356-366) — both replaced by one new test:

```python
    def test_ski_runs_nordic_has_grooming_and_snowmaking_axes(self):
        nordic = self.groups_by_key["ski-runs-nordic"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in nordic["variants"]],
            [("grooming", "Gespurt"), ("grooming", "Ungespurt"), ("snowmaking", "Beschneit")],
        )
        self.assertEqual(nordic["variants"][0]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }])
        self.assertEqual(nordic["variants"][1]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [2, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }])
        self.assertEqual(nordic["variants"][2]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"},
            "stroke_color": None, "opacity": 1, "width": 1.5, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }])
        shared_kinds = [p["kind"] for p in nordic["render"]]
        self.assertEqual(shared_kinds, ["fill", "outline", "text"])
```

Replace `test_ski_runs_downhill_has_four_variants_gladed_ungroomed_overlap` (now updated in
Task 3, lines ~368-385):

```python
    def test_ski_runs_downhill_has_grooming_terrain_and_snowmaking_axes(self):
        downhill = self.groups_by_key["ski-runs-downhill"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in downhill["variants"]],
            [
                ("grooming-terrain", "Präpariert"),
                ("grooming-terrain", "Waldabfahrt"),
                ("grooming-terrain", "Nicht präpariert"),
                ("grooming-terrain", "Waldabfahrt, nicht präpariert"),
                ("snowmaking", "Beschneit"),
            ],
        )
        gladed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [0.1, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }
        ungroomed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [2, 4],
            "radius": None, "stroke_width": None, "icon": None,
        }
        snowmaking_part = {
            "kind": "line", "color": {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"},
            "stroke_color": None, "opacity": 1, "width": 1.5, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        self.assertEqual(downhill["variants"][1]["render"], [gladed_part])
        self.assertEqual(downhill["variants"][2]["render"], [ungroomed_part])
        self.assertEqual(downhill["variants"][3]["render"], [gladed_part, ungroomed_part])
        self.assertEqual(downhill["variants"][4]["render"], [snowmaking_part])
```

Replace `test_ski_lifts_casing_only_in_operating_variants` (now updated in Task 3, lines
~387-436):

```python
    def test_ski_lifts_retaxonomized_into_status_and_access_axes(self):
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in lifts["variants"]],
            [("status", "In Betrieb"), ("status", "Sonstiger Status"), ("access", "Privat")],
        )
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating_public = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-lift-status-v1"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_other_public = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-lift-status-v1"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating_private = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-lift-status-v1"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": [1, 2],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_other_private = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-lift-status-v1"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }

        # axis "status": casing appears exactly once (only under "In
        # Betrieb"), never duplicated into "access" — regression guard for
        # the old 4-combo shape where casing was in 2 of 4 entries.
        self.assertEqual(lifts["variants"][0]["render"], [outline_part, line_operating_public])
        self.assertEqual(lifts["variants"][1]["render"], [line_other_public])
        self.assertEqual(lifts["variants"][2]["render"], [line_operating_private, line_other_private])

        shared_kinds = sorted(p["kind"] for p in lifts["render"])
        self.assertEqual(shared_kinds, ["icon", "text"])

        all_render_parts = lifts["render"] + [p for v in lifts["variants"] for p in v["render"]]
        self.assertEqual(all_render_parts.count(outline_part), 1)
```

- [ ] **Step 7: Run the full test module to verify it passes**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: all tests PASS.

- [ ] **Step 8: Run the complete project verification command**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests PASS across all three modules.

- [ ] **Step 9: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(layer-list): retaxonomize legend variants into named axes

ski-lifts drops its 4-entry status×access combo model for two orthogonal
axes (status: 2 entries, access: 1 single-value entry) — casing no longer
duplicated across variants. ski-runs-downhill/-nordic keep their existing
variant shapes, gaining axis labels ("grooming-terrain"/"grooming") plus a
new single-value "snowmaking" axis each, which resolves the gap tracked in
docs/TODO.md — GROUP_VARIANT_EXCLUDE is now unused and removed.

BREAKING: ski-lifts's variants[] shrinks from 4 entries to 3 and gains
axis; downstream consumers (website-v3) parsing the old 4-combo shape by
position must update.
EOF
)"
```

---

### Task 5: Documentation — `CHANGELOG.md`, `docs/TODO.md` archival, final verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/TODO.md`
- Modify: `docs/TODO_ARCHIVE.md`

**Interfaces:** None — docs only.

- [ ] **Step 1: Add the `CHANGELOG.md` journal entry**

Get the current UTC timestamp: run `date -u '+%Y-%m-%d %H:%M'`.

Insert a new entry at the top of `CHANGELOG.md`, immediately after the header block (after the
"Versionierung folgt..." line, before the existing `## [Unreleased] - 2026-08-14 15:26` entry),
using the timestamp from above in place of `<TIMESTAMP>`:

```markdown
## [Unreleased] - <TIMESTAMP>

### Added
- `dist/layer-list.json`: jeder `Part` trägt jetzt `stroke_color`/`stroke_width`
  (`scripts/layer_metadata_extractor.py`, `scripts/generate_layer_list.py`) — `null` außer bei
  `kind: "circle"`, dort aus `circle-stroke-color`/`circle-stroke-width` (betrifft
  `ski-areas-alpine/-nordic-circle`, `ski-spots`). Schließt die in
  [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3)
  gemeldete Lücke, jetzt offiziell Teil des Standards (v2.1.0 §5.3).
- `variants[]`-Einträge tragen jetzt ein `axis`-Feld (String) — jetzt offiziell Teil des
  Standards (v2.1.0 §5.3, löst
  [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4)).
- Neue Single-Value-Achse `"snowmaking"` (Label "Beschneit") bei `ski-runs-downhill` und
  `ski-runs-nordic` — löst die seit 2026-08-14 zurückgestellte Lücke (siehe `docs/TODO.md`).
- `"version"` in `dist/layer-list.json` auf `"2.1"` angehoben.

### Changed
- **Breaking:** `ski-lifts`' `variants[]` von 4 flachen Status×Zugang-Kombinations-Einträgen
  auf 3 Einträge über 2 Achsen umgestellt — axis `"status"` ("In Betrieb"/"Sonstiger Status")
  und axis `"access"` (Single-Value "Privat", deckt beide Statuswerte gemeinsam ab). Grund:
  `ski-lifts-casing` (Filter testet nur `status`) landete im alten Modell fälschlich in 2 von 4
  Einträgen; die neue Achsen-Struktur verwendet jeden der 4 realen Style-Layer genau einmal.
  Konsumenten, die die alte 4-Kombi-Form positionell parsen (z. B. `website-v3`), müssen
  angepasst werden.
- `GROUP_VARIANT_EXCLUDE` (und der zugehörige Ausschluss-Schritt in
  `_build_render_and_variants`) entfernt — beide bisherigen Einträge (Nordic-/Downhill-
  Snowmaking) sind jetzt reguläre `"snowmaking"`-Achsen-Einträge statt eines Ausschlusses.
- `ski-runs-downhill`/`ski-runs-nordic` behalten ihre bisherige Varianten-Form (4 bzw. 2
  Einträge) unverändert, zusätzlich zum `axis`-Feld und dem neuen Snowmaking-Eintrag —
  bewusste Entscheidung, keine zweite Formänderung für `website-v3` in kurzer Zeit
  (Alternative einer vollen Orthogonal-Zerlegung geprüft und verworfen, siehe
  `docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`).
- Submodul `geodata-plugin-standard` von v2.0.0 auf v2.1.0 gebumpt.
```

- [ ] **Step 2: Archive the two resolved `docs/TODO.md` entries**

In `docs/TODO.md`, remove the `## \`circle-stroke-color\`/\`circle-stroke-width\` im
render-Part-Modell nachziehen` section (lines 36-45) and the `## \`snowmaking\`-Layer haben
kein Konzept im \`render\`/\`variants\`-Schema` section (lines 57-65) in their entirety.

Append both, marked resolved, to the end of `docs/TODO_ARCHIVE.md`:

```markdown

## `circle-stroke-color`/`circle-stroke-width` im render-Part-Modell nachziehen

Erledigt am 2026-08-16: `GEODATA_PLUGIN_STANDARD.md` v2.1.0 hat die Lücke geschlossen
([geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3)) —
`scripts/layer_metadata_extractor.py` (`extract_part_stroke_color`/`extract_part_stroke_width`)
und `scripts/generate_layer_list.py` entsprechend erweitert (Design:
`docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`).

## `snowmaking`-Layer haben kein Konzept im `render`/`variants`-Schema

Erledigt am 2026-08-16: mit der `axis`-Erweiterung des `variants`-Felds
(`GEODATA_PLUGIN_STANDARD.md` v2.1.0 §5.3,
[geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4))
lässt sich Beschneiung als eigene Single-Value-Achse `"snowmaking"` sauber abbilden —
`GROUP_VARIANT_EXCLUDE` in `scripts/generate_layer_list.py` entfällt (Design:
`docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`).
```

- [ ] **Step 3: Final full verification**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests PASS across all three modules, zero failures/errors.

Also run: `git status --short`
Expected: only intentionally-modified files show up (no stray `__pycache__`/`.pyc` changes
staged — if `scripts/ci/__pycache__/utils.cpython-*.pyc` shows as modified, that's the
pre-existing tracked-bytecode issue noted in `docs/TODO.md`, leave it alone, don't stage it).

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md docs/TODO.md docs/TODO_ARCHIVE.md
git commit -m "$(cat <<'EOF'
docs: changelog + TODO archival for layer-list.json v2.1.0 migration

Archives the circle-stroke and snowmaking TODO entries as resolved.
EOF
)"
```

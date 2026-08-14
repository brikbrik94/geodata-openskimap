# Legend-Variants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `dist/layer-list.json` groups whose style layers contain mutually-exclusive MapLibre `filter`s (Loipen, Pisten, Lifte) into a shared `render` array plus a new `variants` array, so a downstream legend renderer no longer stacks visually-exclusive alternatives (e.g. "gespurt" vs. "ungespurt") on top of each other.

**Architecture:** Explicit, hand-verified config (`GROUP_VARIANTS`/`GROUP_VARIANT_EXCLUDE` in `scripts/generate_layer_list.py`, same pattern as the existing `GROUP_MAP`/`GROUP_LEGEND_SCALE`) drives a new `_build_render_and_variants` function that partitions a group's already-collected layers before handing subsets to the existing, unchanged `_build_render`. No new low-level extraction primitives needed — `filter` itself is never parsed at runtime; the partition was worked out by hand against the real style and is being pinned down as hardcoded data now.

**Tech Stack:** Python 3 stdlib only (`json`, `unittest`) — no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-14-legend-variants-design.md`

## Global Constraints

- `variants` is a new, locally-proposed field (not yet part of `geodata-plugin-standard`, tracked upstream as [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4)): `Array<{"label": String, "render": Array<Part>}> | None` on each group, alongside the existing `render`.
- `render` (existing field) changes meaning for groups with variants: it now holds only the Parts common to **every** variant of that group. For groups without a `GROUP_VARIANTS` entry, `render` is unchanged from today (the complete Part list, `variants: None`).
- A style layer can belong to **more than one** variant (e.g. `ski-lifts-casing` belongs to both "In Betrieb" and "In Betrieb (privat)"; `ski-runs-downhill-gladed` belongs to both "Waldabfahrt" and "Waldabfahrt, nicht präpariert").
- `snowmaking` layers (`ski-runs-downhill-snowmaking`, `ski-runs-nordic-snowmaking`) are excluded entirely — neither in `render` nor in any `variants[].render` — per design doc decision 3 (independent overlay attribute, doesn't fit the shared/variant binary, deferred).
- `"version"` stays `"2.0"` — `variants` is additive, no version bump (design doc, "Versionsfeld").
- `scale_items`/`legend_sections` collection is unaffected: it must keep working identically whether a categorized-color Part ends up in `render` or in a `variants[].render` — same `scale_items` dict threaded through every `_build_render` call, exactly as it already is for cross-group sharing.
- Exact variant configs (style-layer-id membership per group, labels) are given verbatim in Task 1 below — copied from the design doc's hand-verified analysis, not to be re-derived.

---

### Task 1: `GROUP_VARIANTS`/`GROUP_VARIANT_EXCLUDE` + `_build_render_and_variants`

**Files:**
- Modify: `scripts/generate_layer_list.py` — add constants after `LEGEND_SCALE_LABELS` (currently ends at line 121), add `_build_render_and_variants` after `_build_render` (currently ends at line 206), change `build_layer_list`'s group-building loop (currently lines 280-282)
- Test: `scripts/test_generate_layer_list.py` — new synthetic unit-test class + new real-style test methods on the existing `BuildLayerListRealStyleTests` class

**Interfaces:**
- Consumes: `_build_render(group_layers, group_key, scale_items)` (existing, unchanged, called on filtered subsets).
- Produces: `_build_render_and_variants(group_layers, group_key, scale_items) -> tuple[list[dict], list[dict] | None]`, consumed by `build_layer_list`. Every group dict gains a `"variants"` key (`None` or a list) alongside its existing `"render"` key.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_generate_layer_list.py`, a new top-level test class (place it after `BuildRenderTests`, before `BuildLegendSectionsTests`):

```python
class BuildRenderAndVariantsTests(unittest.TestCase):
    def setUp(self):
        self._original_variants = generate_layer_list.GROUP_VARIANTS
        self._original_exclude = generate_layer_list.GROUP_VARIANT_EXCLUDE

    def tearDown(self):
        generate_layer_list.GROUP_VARIANTS = self._original_variants
        generate_layer_list.GROUP_VARIANT_EXCLUDE = self._original_exclude

    def test_group_without_variants_config_returns_none_and_full_render(self):
        generate_layer_list.GROUP_VARIANTS = {}
        generate_layer_list.GROUP_VARIANT_EXCLUDE = {}
        group_layers = [
            {"id": "a-fill", "type": "fill", "paint": {"fill-color": "#111", "fill-opacity": 1}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertIsNone(variants)
        self.assertEqual(len(render), 1)

    def test_variant_member_layers_split_from_shared_render(self):
        generate_layer_list.GROUP_VARIANTS = {
            "group-a": [
                {"label": "Variant 1", "style_layer_ids": ["v1"]},
                {"label": "Variant 2", "style_layer_ids": ["v2"]},
            ]
        }
        generate_layer_list.GROUP_VARIANT_EXCLUDE = {}
        group_layers = [
            {"id": "shared", "type": "fill", "paint": {"fill-color": "#111"}},
            {"id": "v1", "type": "line", "paint": {"line-color": "#222"}},
            {"id": "v2", "type": "line", "paint": {"line-color": "#333"}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertEqual(len(render), 1)
        self.assertEqual(render[0]["color"], {"mode": "fixed", "value": "#111"})
        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0]["label"], "Variant 1")
        self.assertEqual(variants[0]["render"][0]["color"], {"mode": "fixed", "value": "#222"})
        self.assertEqual(variants[1]["label"], "Variant 2")
        self.assertEqual(variants[1]["render"][0]["color"], {"mode": "fixed", "value": "#333"})

    def test_layer_can_belong_to_multiple_variants(self):
        generate_layer_list.GROUP_VARIANTS = {
            "group-a": [
                {"label": "Variant 1", "style_layer_ids": ["shared-member"]},
                {"label": "Variant 2", "style_layer_ids": ["shared-member", "v2"]},
            ]
        }
        generate_layer_list.GROUP_VARIANT_EXCLUDE = {}
        group_layers = [
            {"id": "shared-member", "type": "line", "paint": {"line-color": "#111"}},
            {"id": "v2", "type": "line", "paint": {"line-color": "#222"}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertEqual(render, [])
        self.assertEqual(len(variants[0]["render"]), 1)
        self.assertEqual(len(variants[1]["render"]), 2)

    def test_excluded_layer_absent_from_render_and_every_variant(self):
        generate_layer_list.GROUP_VARIANTS = {
            "group-a": [{"label": "Variant 1", "style_layer_ids": ["v1"]}]
        }
        generate_layer_list.GROUP_VARIANT_EXCLUDE = {"group-a": ["excluded"]}
        group_layers = [
            {"id": "shared", "type": "fill", "paint": {"fill-color": "#111"}},
            {"id": "v1", "type": "line", "paint": {"line-color": "#222"}},
            {"id": "excluded", "type": "line", "paint": {"line-color": "#333"}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertEqual(len(render), 1)
        self.assertEqual(len(variants[0]["render"]), 1)
        all_colors = [p["color"] for p in render] + [p["color"] for v in variants for p in v["render"]]
        self.assertNotIn({"mode": "fixed", "value": "#333"}, all_colors)
```

Add to `BuildLayerListRealStyleTests` (existing class, `styles/openskimap-style.json`-backed — add these methods anywhere in the class body):

```python
    def test_ski_runs_nordic_has_two_mutually_exclusive_variants(self):
        nordic = self.groups_by_key["ski-runs-nordic"]
        self.assertEqual(len(nordic["variants"]), 2)
        self.assertEqual(nordic["variants"][0]["label"], "Gespurt")
        self.assertEqual(nordic["variants"][1]["label"], "Ungespurt")
        self.assertEqual(nordic["variants"][0]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 3.0, "dasharray": None, "radius": None, "icon": None,
        }])
        self.assertEqual(nordic["variants"][1]["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": None, "icon": None,
        }])
        shared_kinds = [p["kind"] for p in nordic["render"]]
        self.assertEqual(shared_kinds, ["fill", "outline", "text"])

    def test_ski_runs_nordic_snowmaking_excluded_entirely(self):
        nordic = self.groups_by_key["ski-runs-nordic"]
        all_parts = nordic["render"] + [p for v in nordic["variants"] for p in v["render"]]
        self.assertNotIn(
            {"kind": "line", "color": {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"},
             "opacity": 1, "width": 1.5, "dasharray": None, "radius": None, "icon": None},
            all_parts,
        )
        self.assertEqual(len(nordic["style_layers"]), 6)
        total_parts = len(nordic["render"]) + sum(len(v["render"]) for v in nordic["variants"])
        self.assertEqual(total_parts, 5)  # 6 style layers minus the excluded snowmaking one

    def test_ski_runs_downhill_has_four_variants_gladed_ungroomed_overlap(self):
        downhill = self.groups_by_key["ski-runs-downhill"]
        labels = [v["label"] for v in downhill["variants"]]
        self.assertEqual(
            labels,
            ["Präpariert", "Waldabfahrt", "Nicht präpariert", "Waldabfahrt, nicht präpariert"],
        )
        gladed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "opacity": 1, "width": 3.0, "dasharray": [0.1, 4], "radius": None, "icon": None,
        }
        ungroomed_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": None, "icon": None,
        }
        self.assertEqual(downhill["variants"][1]["render"], [gladed_part])
        self.assertEqual(downhill["variants"][2]["render"], [ungroomed_part])
        self.assertEqual(downhill["variants"][3]["render"], [gladed_part, ungroomed_part])

    def test_ski_lifts_casing_only_in_operating_variants(self):
        lifts = self.groups_by_key["ski-lifts"]
        labels = [v["label"] for v in lifts["variants"]]
        self.assertEqual(
            labels,
            ["In Betrieb", "Sonstiger Status", "In Betrieb (privat)", "Sonstiger Status (privat)"],
        )
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "opacity": 1, "width": 5.0, "dasharray": None, "radius": None, "icon": None,
        }
        self.assertIn(outline_part, lifts["variants"][0]["render"])
        self.assertEqual(len(lifts["variants"][0]["render"]), 2)
        self.assertEqual(len(lifts["variants"][1]["render"]), 1)
        self.assertNotIn(outline_part, lifts["variants"][1]["render"])
        self.assertIn(outline_part, lifts["variants"][2]["render"])
        self.assertEqual(len(lifts["variants"][2]["render"]), 2)
        self.assertEqual(len(lifts["variants"][3]["render"]), 1)
        self.assertNotIn(outline_part, lifts["variants"][3]["render"])
        shared_kinds = sorted(p["kind"] for p in lifts["render"])
        self.assertEqual(shared_kinds, ["icon", "text"])

    def test_groups_without_variants_config_are_unaffected(self):
        for key in ("ski-areas-alpine", "ski-areas-nordic", "ski-spots", "ski-runs-skitour", "ski-runs-other"):
            group = self.groups_by_key[key]
            self.assertIsNone(group["variants"])
            self.assertEqual(len(group["render"]), len(group["style_layers"]))

    def test_legend_sections_still_has_three_scales_after_variant_split(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: `AttributeError`/`KeyError` — `_build_render_and_variants` doesn't exist yet, and existing group dicts have no `"variants"` key.

- [ ] **Step 3: Implement**

In `scripts/generate_layer_list.py`, add directly after `LEGEND_SCALE_LABELS` (after the line `LEGEND_SCALE_LABELS = {...}` block, before `def _build_render`):

```python
# group key -> list of {"label": ..., "style_layer_ids": [...]} — mutually-exclusive
# legend-rendering variants within the group (design doc 2026-08-14,
# legend-variants; proposed upstream as geodata-plugin-standard#4, not yet
# part of the standard). A style-layer-id CAN appear in more than one
# variant's list (e.g. ski-lifts-casing, ski-runs-downhill-gladed/-ungroomed
# — see design doc's per-group filter tables) when its MapLibre `filter`
# overlaps more than one variant's defining condition. Style layers not
# listed in ANY variant here (and not in GROUP_VARIANT_EXCLUDE) stay in the
# group's shared `render`. Groups not listed here at all get `variants: None`
# and unchanged `render` behavior.
GROUP_VARIANTS = {
    "ski-runs-nordic": [
        {"label": "Gespurt", "style_layer_ids": ["ski-runs-nordic-line"]},
        {"label": "Ungespurt", "style_layer_ids": ["ski-runs-nordic-ungroomed"]},
    ],
    "ski-runs-downhill": [
        {"label": "Präpariert", "style_layer_ids": ["ski-runs-downhill-line"]},
        {"label": "Waldabfahrt", "style_layer_ids": ["ski-runs-downhill-gladed"]},
        {"label": "Nicht präpariert", "style_layer_ids": ["ski-runs-downhill-ungroomed"]},
        {"label": "Waldabfahrt, nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-gladed", "ski-runs-downhill-ungroomed"]},
    ],
    "ski-lifts": [
        {"label": "In Betrieb", "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"label": "Sonstiger Status", "style_layer_ids": ["ski-lifts-line-other"]},
        {"label": "In Betrieb (privat)",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line-private"]},
        {"label": "Sonstiger Status (privat)", "style_layer_ids": ["ski-lifts-line-private-other"]},
    ],
}

# group key -> style-layer-ids dropped entirely (neither shared render nor any
# variant) — independent overlay attributes that don't fit the shared/variant
# binary (design doc decision 3), e.g. snowmaking can co-occur with any
# grooming variant. Deferred, see docs/TODO.md.
GROUP_VARIANT_EXCLUDE = {
    "ski-runs-nordic": ["ski-runs-nordic-snowmaking"],
    "ski-runs-downhill": ["ski-runs-downhill-snowmaking"],
}
```

Add directly after `_build_render` (after its closing `return parts`, before `def _build_legend_sections`):

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

Replace the group-building loop in `build_layer_list` (currently):

```python
    scale_items = {}
    for group_key, group in groups_dict.items():
        group["render"] = _build_render(group_layers[group_key], group_key, scale_items)
```

with:

```python
    scale_items = {}
    for group_key, group in groups_dict.items():
        render, variants = _build_render_and_variants(group_layers[group_key], group_key, scale_items)
        group["render"] = render
        group["variants"] = variants
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_generate_layer_list -v`
Expected: all tests pass.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "feat(layer-list): split mutually-exclusive style-layer variants out of render[]"
```

---

### Task 2: Documentation — `CHANGELOG.md` + `docs/TODO.md`

**Files:**
- Modify: `CHANGELOG.md` (new `[Unreleased]` journal block — this is a separate change session from the earlier v2.0-migration entry, gets its own dated block per `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4, not appended to the existing one)
- Modify: `docs/TODO.md` (new entry for the deferred `snowmaking` handling)

**Interfaces:** None (docs only).

- [ ] **Step 1: Add a new CHANGELOG.md journal block**

Insert a new block directly above the existing `## [Unreleased] - 2026-08-14 08:36` heading (i.e. as the new first entry in the file, right after the format/versioning preamble). Use the actual current UTC time (`date -u '+%Y-%m-%d %H:%M'`) in place of `<TIME>` below:

```markdown
## [Unreleased] - 2026-08-14 <TIME>

### Added
- `dist/layer-list.json`: neues, lokal vorgeschlagenes Feld `variants` auf Gruppen-Ebene
  (`scripts/generate_layer_list.py`, Design-Dokument
  `docs/superpowers/specs/2026-08-14-legend-variants-design.md`) für Style-Layer, die sich
  laut ihrem MapLibre `filter` gegenseitig ausschließen (z. B. Loipen "gespurt"/"ungespurt",
  Lifte Status×Zugang) — verhindert, dass ein naiver Legenden-Renderer sie deckungsgleich
  übereinander zeichnet. Betrifft `ski-runs-nordic` (2 Varianten), `ski-runs-downhill`
  (4 Varianten), `ski-lifts` (4 Varianten). Rein additiv, kein Versionssprung. Vorgeschlagen
  als [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4)
  (noch nicht Teil des Standards).

### Known Issues
- `snowmaking`-Layer (`ski-runs-downhill-snowmaking`, `ski-runs-nordic-snowmaking`) sind aus
  `render`/`variants` komplett entfernt — passen als unabhängiger, mit jeder
  Präparierungsstufe gleichzeitig auftretender Zusatz-Marker nicht ins
  geteilt/Variante-Schema. Zurückgestellt, siehe `docs/TODO.md`.
```

- [ ] **Step 2: Add a docs/TODO.md entry**

Read `docs/TODO.md` first to match its existing entry format, then append a new entry:

```markdown
## `snowmaking`-Layer haben kein Konzept im `render`/`variants`-Schema

`ski-runs-downhill-snowmaking`/`ski-runs-nordic-snowmaking` sind seit der
`variants`-Einführung (siehe `docs/superpowers/specs/2026-08-14-legend-variants-design.md`,
Entscheidung 3) komplett aus `render`/`variants` ausgeschlossen (`GROUP_VARIANT_EXCLUDE` in
`scripts/generate_layer_list.py`) — sie sind ein unabhängiger Zusatz-Marker (Beschneiung), der
mit jeder Präparierungsstufe gleichzeitig auftreten kann, passt also weder ins "geteilt (immer)"
noch ins "Variante (genau eine von mehreren)"-Schema. Braucht ein drittes, orthogonales Konzept
(z. B. ein optionales `overlays`-Feld), sobald dafür Bedarf entsteht.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md docs/TODO.md
git commit -m "docs: changelog entry + TODO note for legend-variants snowmaking gap"
```

---

### Task 3: Full verification

**Files:** None modified — verification only.

**Interfaces:** None.

- [ ] **Step 1: Run the complete test suite**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`
Expected: all tests pass (0 failures, 0 errors).

- [ ] **Step 2: Generate `dist/layer-list.json` against the real style and spot-check the three affected groups**

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from generate_layer_list import build_layer_list
import json
with open('styles/openskimap-style.json', encoding='utf-8') as f:
    style = json.load(f)
result = build_layer_list(style, 'openskimap', 'OpenSkiMap', 'openskimap.pmtiles')
groups = {g['template']: g for g in result['styles'][0]['groups']}
for key in ('ski-runs-nordic', 'ski-runs-downhill', 'ski-lifts'):
    g = groups[key]
    print(key, '-> shared render kinds:', [p['kind'] for p in g['render']])
    for v in g['variants']:
        print('   variant', repr(v['label']), '->', len(v['render']), 'parts')
print('groups without variants stay None:', [
    groups[k]['variants'] for k in ('ski-areas-alpine', 'ski-spots', 'ski-runs-skitour')
])
"
```
Expected: the printed summary shows 2/4/4 variants for nordic/downhill/lifts respectively
(with the labels and Part counts matching the design doc's tables), and `[None, None, None]`
for the three unaffected groups.

- [ ] **Step 3: Validate JSON structurally**

Run:
```bash
python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from generate_layer_list import build_layer_list
with open('styles/openskimap-style.json', encoding='utf-8') as f:
    style = json.load(f)
result = build_layer_list(style, 'openskimap', 'OpenSkiMap', 'openskimap.pmtiles')
json.dumps(result)  # raises if not serializable
print('valid JSON, version:', result['version'])
"
```
Expected: `valid JSON, version: 2.0` printed, no exceptions.

No commit for this task — it's verification-only, confirming Tasks 1-2 are correct.

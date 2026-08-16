# Lift Status Granularity, Icon Gaps, Legend-Scale Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up dead/incorrect parts of the `ski-lifts` style and legend: remove match
branches that never occur in the real data, split the too-coarse 2-tier lift status into 3
(In Betrieb / Geplant-Im Bau / Außer Betrieb), fix the broken `ski-lift-status-v1` legend scale
(every variant row currently references the same unfiltered 7-item scale), and give `mixed_lift`
lifts a correct icon pair instead of the misleading `ski-gondola` fallback.

**Architecture:** All structural JSON edits to `styles/openskimap-style.json` are done via small,
throwaway Python scripts that load the file, mutate the parsed `dict`/`list` in place, and
re-serialize with `json.dump(data, f, indent=2, ensure_ascii=False)` + a trailing newline — this
is exactly how the file is already formatted (verified: round-tripping the current file through
this exact call reproduces it byte-for-byte), so it's a safer way to make deeply-nested,
multi-line JSON edits correctly than hand-splicing indented text. `scripts/generate_layer_list.py`
edits are plain Python source edits (Edit tool, no script needed).

**Tech Stack:** JSON (style), Python 3 stdlib only (`json`, `copy` — matches this repo's existing
`scripts/*.py` convention), `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md`

## Global Constraints

- Python code is stdlib-only, no third-party dependencies.
- Git: stage files explicitly (never `git add -A`); commit messages use Conventional Commits
  prefixes.
- `CHANGELOG.md` entries use the `## [Unreleased] - YYYY-MM-DD HH:mm` journal format (Keep a
  Changelog style, German prose, matching this file's existing entries).
- `styles/openskimap-style.json` is always rewritten via
  `json.dump(data, f, indent=2, ensure_ascii=False)` followed by `f.write("\n")` — never
  hand-edited as raw text — to guarantee both valid JSON and byte-identical formatting to the
  rest of the file.
- Verification command (run after every task): `cd scripts && python3 -m unittest
  test_validate_style test_layer_metadata_extractor test_generate_layer_list
  test_normalize_run_tags test_analyze_legend_categories -v` — all tests must pass (120 before
  this plan; task-by-task deltas are noted per task, net count stays 120 throughout since tests
  are renamed/modified in place, not added).
- `data/src/openskidata.gpkg`/`work/*.jsonseq` are unaffected by this plan — only
  `styles/openskimap-style.json` and `scripts/generate_layer_list.py` change, no re-run of
  `convert.sh` is needed.

---

### Task 1: Remove dead match branches (`"planned"` status, `t_bar`/`j_bar` lift types)

**Files:**
- Modify: `styles/openskimap-style.json`
- Modify: `scripts/test_generate_layer_list.py:308-326` (`test_legend_sections_has_three_scales`)

**Interfaces:**
- Consumes: nothing new.
- Produces: `styles/openskimap-style.json`'s 4 `status`-color `match` expressions
  (`ski-lifts-line`/`-line-other`/`-line-private`/`-line-private-other`) drop their `"planned"`
  branch; `ski-lifts-icons`' `lift_type` `match` drops its `t_bar`/`j_bar` branches. Consumed by
  Task 2 (further edits to the same match expressions) and Task 3 (further edits to the icon
  match).

- [ ] **Step 1: Write and run the dead-branch-removal script**

Create `/tmp/task1_remove_dead_branches.py` (scratch, not committed) with this exact content:

```python
import json

PATH = "styles/openskimap-style.json"
with open(PATH, encoding="utf-8") as f:
    style = json.load(f)

STATUS_COLOR_LAYER_IDS = {
    "ski-lifts-line", "ski-lifts-line-other",
    "ski-lifts-line-private", "ski-lifts-line-private-other",
}

for layer in style["layers"]:
    if layer["id"] in STATUS_COLOR_LAYER_IDS:
        expr = layer["paint"]["line-color"]
        assert expr[0] == "match" and expr[1] == ["get", "status"], layer["id"]
        i = expr.index("planned")
        del expr[i:i + 2]

    if layer["id"] == "ski-lifts-icons":
        expr = layer["layout"]["icon-image"]
        assert expr[0] == "match", layer["id"]
        for dead_value in ("t_bar", "j_bar"):
            i = expr.index(dead_value)
            del expr[i:i + 2]

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(style, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("done")
```

Run: `cd /mnt/geodata/geodata-openskimap && python3 /tmp/task1_remove_dead_branches.py`
Expected: prints `done`, no `AssertionError`/`ValueError` (a `ValueError` from `.index()` would
mean a branch was already missing — investigate before continuing, don't silently proceed).

- [ ] **Step 2: Verify the JSON is well-formed and the branches are gone**

Run:
```bash
python3 -c "import json; json.load(open('styles/openskimap-style.json'))" && echo "valid JSON"
grep -c '"planned"' styles/openskimap-style.json
grep -c 't_bar\|j_bar' styles/openskimap-style.json
```
Expected: `valid JSON`, then `0`, then `0`.

- [ ] **Step 3: Update the now-stale legend-scale test**

In `scripts/test_generate_layer_list.py`, find `test_legend_sections_has_three_scales` (around
line 308). Replace:

```python
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-lift-status-v1"]["items"]],
            ["Operating", "Proposed", "Planned", "Construction", "Disused", "Abandoned", "Sonstige"],
        )
```

with:

```python
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-lift-status-v1"]["items"]],
            ["Operating", "Proposed", "Construction", "Disused", "Abandoned", "Sonstige"],
        )
```

(`"Planned"` dropped from the expected list — the scale itself is removed entirely in Task 2,
this is just the intermediate state after Task 1's dead-branch removal.)

- [ ] **Step 4: Run the verification suite**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor
test_generate_layer_list test_normalize_run_tags test_analyze_legend_categories -v`
Expected: all 120 tests PASS.

- [ ] **Step 5: Clean up the scratch script and commit**

```bash
rm /tmp/task1_remove_dead_branches.py
git add styles/openskimap-style.json scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
fix(style): remove dead lift status/lift_type match branches

status "planned" and lift_type t_bar/j_bar (underscore variants) never
occur in the real AT-filtered data - status is always
operating/proposed/construction/disused/abandoned, lift_type always
uses the hyphenated t-bar/j-bar. Same cleanup pattern as the earlier
difficulty expert/extreme dead-branch removal.
EOF
)"
```

---

### Task 2: Split lift status into 3 tiers, fix the broken legend scale

**Files:**
- Modify: `styles/openskimap-style.json`
- Modify: `scripts/generate_layer_list.py`
- Modify: `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: Task 1's cleaned-up style (6-branch status match, before this task turns it into
  fixed per-layer colors).
- Produces: `styles/openskimap-style.json` gains two new layer ids `ski-lifts-line-planned`/
  `ski-lifts-line-disused` (replacing `ski-lifts-line-other`); `ski-lifts-line`/`-line-private`/
  `-line-private-other` get fixed (non-`match`) `line-color`. `GROUP_MAP`, `GROUP_LEGEND_SCALE`,
  `LEGEND_SCALE_LABELS`, `GROUP_VARIANTS["ski-lifts"]` in `scripts/generate_layer_list.py`
  updated to match — consumed by Task 3 (adds a further `GROUP_VARIANTS["ski-lifts"]` entry) and
  Task 5 (end-to-end check).

- [ ] **Step 1: Write and run the status-split script**

Create `/tmp/task2_split_lift_status.py` (scratch, not committed):

```python
import copy
import json

PATH = "styles/openskimap-style.json"
with open(PATH, encoding="utf-8") as f:
    style = json.load(f)

layers = style["layers"]
by_id = {layer["id"]: layer for layer in layers}

# ski-lifts-line / ski-lifts-line-private: both already filtered to
# status == operating - the match was always redundant there. Fixed color.
for layer_id in ("ski-lifts-line", "ski-lifts-line-private"):
    by_id[layer_id]["paint"]["line-color"] = "hsl(0, 82%, 42%)"

# ski-lifts-line-private-other: filter allows any non-operating status,
# but real data only ever has (private, disused) here (1 of 2938 features)
# - use the "Außer Betrieb" color, see design doc Baustein 3.
by_id["ski-lifts-line-private-other"]["paint"]["line-color"] = "hsl(0, 53%, 42%)"

# ski-lifts-line-other -> split into ski-lifts-line-planned
# (proposed+construction) and ski-lifts-line-disused (disused+abandoned).
old_layer = by_id["ski-lifts-line-other"]
old_index = layers.index(old_layer)
layers.pop(old_index)


def make_status_layer(new_id, color, dasharray, statuses):
    layer = copy.deepcopy(old_layer)
    layer["id"] = new_id
    layer["paint"]["line-color"] = color
    layer["paint"]["line-dasharray"] = ["literal", dasharray]
    layer["filter"] = [
        "all",
        ["!=", ["get", "access"], "private"],
        ["in", ["get", "status"], ["literal", statuses]],
    ]
    return layer


planned_layer = make_status_layer(
    "ski-lifts-line-planned", "hsl(210, 70%, 45%)", [4, 2],
    ["proposed", "construction"],
)
disused_layer = make_status_layer(
    "ski-lifts-line-disused", "hsl(0, 53%, 42%)", [1, 3],
    ["disused", "abandoned"],
)
layers.insert(old_index, disused_layer)
layers.insert(old_index, planned_layer)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(style, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("done")
```

Run: `cd /mnt/geodata/geodata-openskimap && python3 /tmp/task2_split_lift_status.py`
Expected: prints `done`.

- [ ] **Step 2: Verify the JSON and spot-check the new layers**

Run:
```bash
python3 -c "import json; json.load(open('styles/openskimap-style.json'))" && echo "valid JSON"
grep -c '"ski-lifts-line-other"' styles/openskimap-style.json
grep -c '"ski-lifts-line-planned"\|"ski-lifts-line-disused"' styles/openskimap-style.json
grep -c '"match"' styles/openskimap-style.json
```
Expected: `valid JSON`, then `0` (old layer id gone), then `2` (one occurrence of each new id),
then the count should have dropped by 4 vs. before this step (the 4 status-color `match`
expressions on `ski-lifts-line`/`-line-private`/`-line-private-other` are gone; `ski-lifts-line-
planned`/`-disused` never had one — only `ski-lifts-icons`' `lift_type` match and the `ski-runs-
*` difficulty matches remain).

- [ ] **Step 3: Update `GROUP_MAP` in `scripts/generate_layer_list.py`**

Replace:

```python
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-other": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-line-private-other": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
}
```

with:

```python
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-planned": "ski-lifts",
    "ski-lifts-line-disused": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-line-private-other": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
}
```

- [ ] **Step 4: Remove the `ski-lifts` legend scale**

Replace:

```python
# group key -> shared legend_scale_id (GEODATA_PLUGIN_STANDARD.md v2.1.0
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
    "ski-lifts": "ski-lift-status-v1",
    "ski-spots": "ski-spot-type-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
    "ski-lift-status-v1": "Lift-Status",
    "ski-spot-type-v1": "Spot-Typ",
}
```

with:

```python
# group key -> shared legend_scale_id (GEODATA_PLUGIN_STANDARD.md v2.1.0
# §5.5). All four run-category groups render categorized colors from the
# same difficulty match expression (verified byte-identical against
# styles/openskimap-style.json — see design doc 2026-08-14), so they share
# one central legend. ski-spots (spot_type) gets its own scale, newly
# introduced with the v2.0 migration (v1.1 only had ungrouped per-group
# legend_items for it). ski-lifts had a "ski-lift-status-v1" scale here too
# until the 2026-08-16 lift-status-icon-cleanup follow-up: each status-color
# match was replaced by fixed per-layer colors (every lift line layer is
# already status-filtered, so a shared multi-branch scale only produced
# incorrect cross-contaminated legend rows - every variant row pointed at
# the SAME unfiltered 7-item scale, e.g. "In Betrieb" incorrectly also
# listing "Disused"/"Abandoned"). See design doc
# 2026-08-16-lift-status-icon-cleanup-design.md, Baustein 4. No categorized
# color remains in the ski-lifts group, so it has no GROUP_LEGEND_SCALE
# entry at all now.
GROUP_LEGEND_SCALE = {
    "ski-runs-downhill": "ski-difficulty-v1",
    "ski-runs-nordic": "ski-difficulty-v1",
    "ski-runs-skitour": "ski-difficulty-v1",
    "ski-spots": "ski-spot-type-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
    "ski-spot-type-v1": "Spot-Typ",
}
```

- [ ] **Step 5: Update `GROUP_VARIANTS["ski-lifts"]` and the conformance-count comment**

Replace:

```python
# conformant (each of its 4 variant-bearing style layers appears in exactly
# one axis entry — see the design doc's paint-coupling investigation for how
# it was split into orthogonal "status"/"access" axes without duplication).
```

with:

```python
# conformant (each of its 6 variant-bearing style layers appears in exactly
# one axis entry — see the design doc's paint-coupling investigation for how
# it was split into orthogonal "status"/"access" axes without duplication;
# 2026-08-16 lift-status-icon-cleanup follow-up split "status" into three
# tiers instead of two, see docs/superpowers/specs/
# 2026-08-16-lift-status-icon-cleanup-design.md).
```

Then replace:

```python
    "ski-lifts": [
        {"axis": "status", "label": "In Betrieb",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"axis": "status", "label": "Sonstiger Status",
         "style_layer_ids": ["ski-lifts-line-other"]},
        # Two Parts bundled under one axis entry per §5.3's "render:
        # Array<Part> can have more than one Part when one filter condition
        # covers several style layers" — not because both are simultaneously
        # visible: -line-private is status==operating, -line-private-other
        # is status!=operating, i.e. they are themselves status-exclusive.
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
```

with:

```python
    "ski-lifts": [
        {"axis": "status", "label": "In Betrieb",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"axis": "status", "label": "Geplant / Im Bau",
         "style_layer_ids": ["ski-lifts-line-planned"]},
        {"axis": "status", "label": "Außer Betrieb",
         "style_layer_ids": ["ski-lifts-line-disused"]},
        # Two Parts bundled under one axis entry per §5.3's "render:
        # Array<Part> can have more than one Part when one filter condition
        # covers several style layers" — not because both are simultaneously
        # visible: -line-private is status==operating, -line-private-other
        # is status!=operating, i.e. they are themselves status-exclusive.
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
```

- [ ] **Step 6: Rewrite the affected tests in `scripts/test_generate_layer_list.py`**

Replace the whole `test_legend_sections_has_three_scales` method (its body after Task 1's Step 3
edit — the `ski-difficulty-v1` assertions unchanged, the `ski-lift-status-v1` list already
missing `"Planned"`):

```python
    def test_legend_sections_has_three_scales(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})
        self.assertEqual(sections_by_id["ski-difficulty-v1"]["label"], "Schwierigkeitsgrade")
        self.assertEqual(sections_by_id["ski-lift-status-v1"]["label"], "Lift-Status")
        self.assertEqual(sections_by_id["ski-spot-type-v1"]["label"], "Spot-Typ")
        # Expert/Extreme dead branches removed (data never has them since the
        # difficulty remap - normalize_run_tags.py); Freeride removed from
        # the shared scale too (2026-08-16 fourth follow-up) - it's now its
        # own fixed-color "difficulty" axis row in ski-runs-downhill/
        # ski-runs-skitour instead, see comment above GROUP_VARIANTS.
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-difficulty-v1"]["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Sonstige"],
        )
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-lift-status-v1"]["items"]],
            ["Operating", "Proposed", "Construction", "Disused", "Abandoned", "Sonstige"],
        )
```

with:

```python
    def test_legend_sections_has_two_scales(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-spot-type-v1"})
        self.assertEqual(sections_by_id["ski-difficulty-v1"]["label"], "Schwierigkeitsgrade")
        self.assertEqual(sections_by_id["ski-spot-type-v1"]["label"], "Spot-Typ")
        # Expert/Extreme dead branches removed (data never has them since the
        # difficulty remap - normalize_run_tags.py); Freeride removed from
        # the shared scale too (2026-08-16 fourth follow-up) - it's now its
        # own fixed-color "difficulty" axis row in ski-runs-downhill/
        # ski-runs-skitour instead, see comment above GROUP_VARIANTS.
        # ski-lift-status-v1 removed entirely (2026-08-16 lift-status-icon-
        # cleanup follow-up) - ski-lifts no longer has any categorized
        # color, see comment above GROUP_LEGEND_SCALE.
        self.assertEqual(
            [i["label"] for i in sections_by_id["ski-difficulty-v1"]["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Sonstige"],
        )
```

Replace:

```python
    def test_legend_sections_still_has_three_scales_after_variant_split(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})
```

with:

```python
    def test_legend_sections_still_has_two_scales_after_variant_split(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-spot-type-v1"})
```

Replace the whole `test_ski_lifts_retaxonomized_into_status_and_access_axes` method:

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

with:

```python
    def test_ski_lifts_retaxonomized_into_status_and_access_axes(self):
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in lifts["variants"]],
            [
                ("status", "In Betrieb"),
                ("status", "Geplant / Im Bau"),
                ("status", "Außer Betrieb"),
                ("access", "Privat"),
            ],
        )
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 82%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_planned = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(210, 70%, 45%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [4, 2],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_disused = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 53%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating_private = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 82%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": [1, 2],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_other_private = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 53%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }

        # axis "status": casing appears exactly once (only under "In
        # Betrieb"), never duplicated into "access" — regression guard for
        # the old 4-combo shape where casing was in 2 of 4 entries.
        self.assertEqual(lifts["variants"][0]["render"], [outline_part, line_operating])
        self.assertEqual(lifts["variants"][1]["render"], [line_planned])
        self.assertEqual(lifts["variants"][2]["render"], [line_disused])
        self.assertEqual(lifts["variants"][3]["render"], [line_operating_private, line_other_private])

        shared_kinds = sorted(p["kind"] for p in lifts["render"])
        self.assertEqual(shared_kinds, ["icon", "text"])

        all_render_parts = lifts["render"] + [p for v in lifts["variants"] for p in v["render"]]
        self.assertEqual(all_render_parts.count(outline_part), 1)
```

In `test_variant_part_conformance_counts`, replace:

```python
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(total_part_count(lifts), len(lifts["style_layers"]))
        self.assertEqual(len(lifts["style_layers"]), 7)
```

with:

```python
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(total_part_count(lifts), len(lifts["style_layers"]))
        self.assertEqual(len(lifts["style_layers"]), 8)
```

- [ ] **Step 7: Run the verification suite**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor
test_generate_layer_list test_normalize_run_tags test_analyze_legend_categories -v`
Expected: all 120 tests PASS.

- [ ] **Step 8: Clean up the scratch script and commit**

```bash
rm /tmp/task2_split_lift_status.py
git add styles/openskimap-style.json scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(legend): split lift status into 3 tiers, drop broken status scale

"Sonstiger Status" bundled proposed/construction (22 features, "doesn't
exist yet") with disused/abandoned (117, "no longer exists") into one
visually and semantically identical row. Split into "Geplant / Im Bau"
(new blue, dashed [4,2]) and "Außer Betrieb" (unchanged muted red,
dashed [1,3]). ski-lifts-line/-line-private/-line-private-other also
lose their now-redundant status match (each layer is already
status-filtered) in favor of fixed colors.

Also fixes a real bug: ski-lift-status-v1 previously packed all 7
match branches into one legend scale referenced by every variant row,
so e.g. "In Betrieb" incorrectly listed "Disused"/"Abandoned" colors
too. With every lift layer now fixed-color, ski-lifts has no
categorized color left, so the scale is removed entirely instead.

BREAKING: ski-lifts-line-other renamed/split into
ski-lifts-line-planned/ski-lifts-line-disused; the "ski-lift-status-v1"
legend_sections entry is gone from layer-list.json.
EOF
)"
```

---

### Task 3: `mixed_lift` icon pair (gondola + chairlift, offset)

**Files:**
- Modify: `styles/openskimap-style.json`
- Modify: `scripts/generate_layer_list.py`
- Modify: `scripts/test_generate_layer_list.py`

**Interfaces:**
- Consumes: Task 2's style/generator state.
- Produces: two new style layers `ski-lifts-icons-mixed-gondola`/`-icons-mixed-chair`;
  `ski-lifts-icons` gains a `lift_type != "mixed_lift"` filter. `GROUP_MAP`/`GROUP_VARIANTS` in
  `scripts/generate_layer_list.py` updated. Consumed by Task 5 (end-to-end check).

- [ ] **Step 1: Write and run the mixed-lift-icon script**

Create `/tmp/task3_mixed_lift_icons.py` (scratch, not committed):

```python
import json

PATH = "styles/openskimap-style.json"
with open(PATH, encoding="utf-8") as f:
    style = json.load(f)

layers = style["layers"]
by_id = {layer["id"]: layer for layer in layers}

icons_layer = by_id["ski-lifts-icons"]
icons_layer["filter"] = ["!=", ["get", "lift_type"], "mixed_lift"]

mixed_gondola = {
    "id": "ski-lifts-icons-mixed-gondola",
    "type": "symbol",
    "source": "ski_source",
    "source-layer": "ski_lifts",
    "minzoom": 13,
    "filter": ["==", ["get", "lift_type"], "mixed_lift"],
    "layout": {
        "symbol-placement": "line",
        "symbol-spacing": 150,
        "icon-rotation-alignment": "viewport",
        "icon-image": "ski-gondola",
        "icon-offset": [0, -8],
        "icon-size": 0.7,
        "icon-allow-overlap": False,
        "icon-ignore-placement": True,
    },
}
mixed_chair = {
    "id": "ski-lifts-icons-mixed-chair",
    "type": "symbol",
    "source": "ski_source",
    "source-layer": "ski_lifts",
    "minzoom": 13,
    "filter": ["==", ["get", "lift_type"], "mixed_lift"],
    "layout": {
        "symbol-placement": "line",
        "symbol-spacing": 150,
        "icon-rotation-alignment": "viewport",
        "icon-image": [
            "case",
            ["==", ["get", "occupancy"], 1], "ski-chairlift-1",
            ["==", ["get", "occupancy"], 2], "ski-chairlift-2",
            ["==", ["get", "occupancy"], 3], "ski-chairlift-3",
            ["==", ["get", "occupancy"], 4], "ski-chairlift-4",
            ["==", ["get", "occupancy"], 6], "ski-chairlift-6",
            ["==", ["get", "occupancy"], 8], "ski-chairlift-8",
            "ski-chairlift-2",
        ],
        "icon-offset": [0, 8],
        "icon-size": 0.7,
        "icon-allow-overlap": False,
        "icon-ignore-placement": True,
    },
}

icons_index = layers.index(icons_layer)
layers.insert(icons_index + 1, mixed_chair)
layers.insert(icons_index + 1, mixed_gondola)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(style, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("done")
```

Run: `cd /mnt/geodata/geodata-openskimap && python3 /tmp/task3_mixed_lift_icons.py`
Expected: prints `done`.

- [ ] **Step 2: Verify the JSON and the new layers**

Run:
```bash
python3 -c "import json; json.load(open('styles/openskimap-style.json'))" && echo "valid JSON"
grep -c '"ski-lifts-icons-mixed-gondola"\|"ski-lifts-icons-mixed-chair"' styles/openskimap-style.json
python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json
```
Expected: `valid JSON`, then `2`, then `✔ Style is valid: all source-layers known, all icon-image
references resolve to sprite.` (both new layers only reference `ski-gondola`/`ski-chairlift-N`,
which already exist in the sprite).

- [ ] **Step 3: Update `GROUP_MAP` in `scripts/generate_layer_list.py`**

Replace:

```python
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
}
```

with:

```python
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
    "ski-lifts-icons-mixed-gondola": "ski-lifts",
    "ski-lifts-icons-mixed-chair": "ski-lifts",
}
```

- [ ] **Step 4: Add the `lift_type` variant axis**

Replace:

```python
# conformant (each of its 6 variant-bearing style layers appears in exactly
# one axis entry — see the design doc's paint-coupling investigation for how
# it was split into orthogonal "status"/"access" axes without duplication;
# 2026-08-16 lift-status-icon-cleanup follow-up split "status" into three
# tiers instead of two, see docs/superpowers/specs/
# 2026-08-16-lift-status-icon-cleanup-design.md).
```

with:

```python
# conformant (each of its 8 variant-bearing style layers appears in exactly
# one axis entry — see the design doc's paint-coupling investigation for how
# it was split into orthogonal "status"/"access" axes without duplication;
# 2026-08-16 lift-status-icon-cleanup follow-up split "status" into three
# tiers instead of two and added a "lift_type" axis for the mixed_lift icon
# pair, see docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md).
```

Then replace:

```python
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
```

with:

```python
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
        # mixed_lift (OpenSkiMap's own hybrid gondola/chair-lift concept, no
        # further sub-typing available in the data) renders as two offset
        # icons on the same line instead of a single misleading icon — see
        # design doc Baustein 5. Not a step toward "lift_type as legend
        # rows" in general (explicitly deferred, see docs/TODO.md); this is
        # the one case that needed its own style layers regardless.
        {"axis": "lift_type", "label": "Kombibahn (Gondel + Sessellift)",
         "style_layer_ids": ["ski-lifts-icons-mixed-gondola", "ski-lifts-icons-mixed-chair"]},
    ],
```

- [ ] **Step 5: Rewrite the affected tests in `scripts/test_generate_layer_list.py`**

Rename `test_ski_lifts_retaxonomized_into_status_and_access_axes` (the version written in
Task 2's Step 6 — 4 axis entries, no `lift_type`) to
`test_ski_lifts_retaxonomized_into_status_access_and_lift_type_axes`, replacing its entire body
(the exact text Task 2 produced — copy it from there if needed) with:

```python
    def test_ski_lifts_retaxonomized_into_status_access_and_lift_type_axes(self):
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in lifts["variants"]],
            [
                ("status", "In Betrieb"),
                ("status", "Geplant / Im Bau"),
                ("status", "Außer Betrieb"),
                ("access", "Privat"),
                ("lift_type", "Kombibahn (Gondel + Sessellift)"),
            ],
        )
        outline_part = {
            "kind": "outline", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 82%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_planned = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(210, 70%, 45%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [4, 2],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_disused = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 53%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_operating_private = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 82%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 3.0, "dasharray": [1, 2],
            "radius": None, "stroke_width": None, "icon": None,
        }
        line_other_private = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 53%, 42%)"},
            "stroke_color": None, "opacity": 0.8, "width": 1.98, "dasharray": [1, 3],
            "radius": None, "stroke_width": None, "icon": None,
        }
        mixed_gondola_part = {
            "kind": "icon", "color": None, "stroke_color": None, "opacity": 1,
            "width": None, "dasharray": None, "radius": None, "stroke_width": None,
            "icon": "ski-gondola",
        }
        mixed_chair_part = {
            "kind": "icon", "color": None, "stroke_color": None, "opacity": 1,
            "width": None, "dasharray": None, "radius": None, "stroke_width": None,
            "icon": None,  # icon-image is a case expression, not literal
        }

        # axis "status": casing appears exactly once (only under "In
        # Betrieb"), never duplicated into "access" — regression guard for
        # the old 4-combo shape where casing was in 2 of 4 entries.
        self.assertEqual(lifts["variants"][0]["render"], [outline_part, line_operating])
        self.assertEqual(lifts["variants"][1]["render"], [line_planned])
        self.assertEqual(lifts["variants"][2]["render"], [line_disused])
        self.assertEqual(lifts["variants"][3]["render"], [line_operating_private, line_other_private])
        self.assertEqual(lifts["variants"][4]["render"], [mixed_gondola_part, mixed_chair_part])

        shared_kinds = sorted(p["kind"] for p in lifts["render"])
        self.assertEqual(shared_kinds, ["icon", "text"])

        all_render_parts = lifts["render"] + [p for v in lifts["variants"] for p in v["render"]]
        self.assertEqual(all_render_parts.count(outline_part), 1)
```

In `test_variant_part_conformance_counts`, replace:

```python
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(total_part_count(lifts), len(lifts["style_layers"]))
        self.assertEqual(len(lifts["style_layers"]), 8)
```

with:

```python
        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(total_part_count(lifts), len(lifts["style_layers"]))
        self.assertEqual(len(lifts["style_layers"]), 10)
```

`test_ski_lifts_render_parts` needs no change — the shared `ski-lifts-icons` layer's extracted
Part shape (`color: None`, `icon: None`, since its `icon-image` is still a `match` expression)
is unaffected by adding a `filter`.

- [ ] **Step 6: Run the verification suite**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor
test_generate_layer_list test_normalize_run_tags test_analyze_legend_categories -v`
Expected: all 120 tests PASS.

- [ ] **Step 7: Clean up the scratch script and commit**

```bash
rm /tmp/task3_mixed_lift_icons.py
git add styles/openskimap-style.json scripts/generate_layer_list.py scripts/test_generate_layer_list.py
git commit -m "$(cat <<'EOF'
feat(style): give mixed_lift its own gondola+chairlift icon pair

mixed_lift (17 features, e.g. "Sternstein Express", "Kombibahn
Penken") fell through ski-lifts-icons' lift_type match to the default
ski-gondola icon - misleading for what OpenSkiMap models as a genuine
gondola/chair-lift hybrid with no further sub-typing in the data.
Two new offset symbol layers (ski-lifts-icons-mixed-gondola/-chair)
render both pictograms side by side using only existing sprites, no
new assets. ski-lifts-icons gets a lift_type != "mixed_lift" filter
to avoid a third, redundant icon at the same spot.
EOF
)"
```

---

### Task 4: Documentation (CHANGELOG, ROADMAP, TODO)

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TODO.md`

**Interfaces:** None — documentation only.

- [ ] **Step 1: Get the current UTC timestamp**

Run: `date -u '+%Y-%m-%d %H:%M'`

- [ ] **Step 2: Add the CHANGELOG journal entry**

Insert a new entry at the top of `CHANGELOG.md`, immediately after the header block, using the
timestamp from Step 1 in place of `<TIMESTAMP>`:

```markdown
## [Unreleased] - <TIMESTAMP>

### Changed
- `styles/openskimap-style.json`: Lift-`status`-Färbung von einer gemeinsamen `match`-Expression
  auf feste Filter-Layer umgestellt. Neu 3 Stufen statt 2: **In Betrieb** (`operating`,
  unverändert `hsl(0, 82%, 42%)`), **Geplant / Im Bau** (`proposed`+`construction`, neue Farbe
  `hsl(210, 70%, 45%)`, Dasharray `[4, 2]`), **Außer Betrieb** (`disused`+`abandoned`,
  unverändert `hsl(0, 53%, 42%)`, Dasharray `[1, 3]`) — vorher in "Sonstiger Status"
  zusammengeworfen. `ski-lifts-line-other` ersetzt durch `ski-lifts-line-planned`/
  `ski-lifts-line-disused`. `ski-lifts-line-private`/`-line-private-other` bleiben bei der
  bisherigen 2-Wege-Aufteilung (nur 1 von 2938 Lift-Features ist `private`+nicht-`operating`),
  Farben aber ebenfalls fest statt Match. Toten `"planned"`-Match-Zweig (kommt nie in den Daten
  vor) und `t_bar`/`j_bar`-Icon-Zweige (Daten verwenden ausschließlich `t-bar`/`j-bar`) entfernt.
  Siehe `docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md`.
- `scripts/generate_layer_list.py`: `ski-lift-status-v1`-Legend-Scale komplett entfernt
  (`GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS`) — sie hatte strukturell alle 7 Status-Match-
  Branches ungefiltert in eine Scale gepackt, sodass z. B. die "In Betrieb"-Legend-Zeile
  fälschlich auch auf "Disused"/"Abandoned"-Farben verwies. Jeder Lift-Layer hat jetzt eine feste
  Farbe statt eines Matches, daher keine kategorisierte Farbe mehr in der Gruppe.
  `GROUP_VARIANTS["ski-lifts"]`s `"status"`-Achse hat jetzt 3 statt 2 Einträge
  (`In Betrieb`/`Geplant / Im Bau`/`Außer Betrieb`).

### Added
- `styles/openskimap-style.json`: `mixed_lift` (17 Features, z. B. "Sternstein Express") bekommt
  ein Icon-Paar statt des irreführenden Default-Fallbacks `ski-gondola` — zwei neue Symbol-Layer
  (`ski-lifts-icons-mixed-gondola`/`-mixed-chair`), per `icon-offset` senkrecht zur Linie versetzt,
  nutzen ausschließlich bestehende Sprites (Gondel-Icon + die bestehende Occupancy-basierte
  Sessellift-Icon-Auswahl). `ski-lifts-icons` bekommt einen `lift_type != "mixed_lift"`-Filter,
  um Doppel-Icons zu vermeiden. `scripts/generate_layer_list.py`s `GROUP_VARIANTS["ski-lifts"]`
  bekommt eine neue `"lift_type"`-Achse mit einer Zeile (`Kombibahn (Gondel + Sessellift)`) für
  dieses Icon-Paar — kein Vorgriff auf Lift-Typ-Icons als Legend-Zeilen generell (siehe
  `docs/TODO.md`).
- `docs/ROADMAP.md`: Eintrag für ein eigenes `railway`-Sprite-Icon (2 Features, aktuell
  `ski-gondola`-Fallback) — zurückgestellt.
- `docs/TODO.md`: Eintrag für Lift-Typ-Icons als eigene Legend-Zeilen (analog Grooming bei
  Pisten) — zurückgestellt, siehe Design-Dokument "Out of Scope".
```

- [ ] **Step 3: Add the `docs/ROADMAP.md` entry**

Append this section at the end of `docs/ROADMAP.md`:

```markdown

## Zahnradbahn-Icon für `lift_type=railway`

Aktuell (siehe `docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md`,
Baustein 6) fällt `lift_type=railway` (2 Features, "Bayerische Zugspitzbahn") auf das
Default-Icon `ski-gondola` zurück — fachlich nicht ganz treffend (eine Zahnradbahn ist keine
Gondel), aber bei nur 2 Features kein akuter Handlungsbedarf. Für eine spätere Umsetzung: ein
eigenes Sprite-Icon (`ski-railway` o. ä.) analog zu den bestehenden Lift-Icons in
`assets/sprites/openskimap/sprite.json`/`sprite@2x.json` zeichnen, im `lift_type`-Icon-Match in
`ski-lifts-icons` (`styles/openskimap-style.json`) einen `"railway"`-Zweig ergänzen.
```

- [ ] **Step 4: Add the `docs/TODO.md` entry**

Append this section at the end of `docs/TODO.md`:

```markdown

## Lift-Typ-Icons als eigene Legend-Zeilen (analog Grooming bei Pisten)

`lift_type` hat 12 reale Werte mit je eigenem Icon (siehe
`docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md`), aber keines davon
taucht als eigene Legend-Zeile auf (anders als Grooming/Freeride bei Pisten). Nutzer-Entscheidung
(2026-08-16): zurückgestellt, bis `variants[]`/`GROUP_VARIANTS`-artige Icon-Legend-Zeilen im
`GEODATA_PLUGIN_STANDARD.md` definiert sind und auf der konsumierenden Website getestet wurde, ob
eine so variantenreiche Icon-Legende praktikabel ist (11+ Zeilen allein für Lifte). Die einzige
Ausnahme, die schon umgesetzt ist: `mixed_lift` bekam eine eigene `"lift_type"`-Variant-Zeile,
weil dafür ohnehin zwei dedizierte Style-Layer nötig waren (Icon-Paar statt Einzel-Icon, siehe
Baustein 5 im Design-Dokument) — kein Vorgriff auf die generelle Frage.
```

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md docs/ROADMAP.md docs/TODO.md
git commit -m "docs: changelog entry for lift status/icon cleanup, roadmap/todo follow-ups"
```

---

### Task 5: End-to-end verification

**Files:** None modified — this task runs the pipeline's finalize step and reports results.

**Interfaces:** Consumes everything from Tasks 1-4.

- [ ] **Step 1: Run the full verification suite one more time**

Run: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor
test_generate_layer_list test_normalize_run_tags test_analyze_legend_categories -v`
Expected: all 120 tests PASS.

- [ ] **Step 2: Validate the style against the sprite sheet directly**

Run: `python3 scripts/validate_style.py styles/openskimap-style.json
assets/sprites/openskimap/sprite.json`
Expected: `✔ Style is valid: all source-layers known, all icon-image references resolve to
sprite.`

- [ ] **Step 3: Regenerate `dist/` and inspect the real `layer-list.json` output**

Run: `python3 scripts/generate_manifest.py`
Expected: completes without error, prints its usual summary.

Run:
```bash
python3 -c "
import json
d = json.load(open('dist/layer-list.json'))
sections = {s['id']: s for s in d['legend_sections']}
print('scale ids:', sorted(sections))
lifts = next(g for g in d['styles'][0]['groups'] if g['name'] == 'Lifte')
print('lift style_layers:', len(lifts['style_layers']))
print('lift variant axes:', [(v['axis'], v['label']) for v in lifts['variants']])
"
```
Expected: `scale ids: ['ski-difficulty-v1', 'ski-spot-type-v1']` (no `ski-lift-status-v1`),
`lift style_layers: 10`, and `lift variant axes:` listing exactly:
`[('status', 'In Betrieb'), ('status', 'Geplant / Im Bau'), ('status', 'Außer Betrieb'),
('access', 'Privat'), ('lift_type', 'Kombibahn (Gondel + Sessellift)')]`.

- [ ] **Step 4: Report results**

Summarize the Step 3 output for the user (scale ids, style_layers count, variant axes) so they
can see the before/after concretely. No commit needed for this task — nothing new was created,
only verified.

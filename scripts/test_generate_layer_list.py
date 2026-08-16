import json
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import generate_layer_list
from generate_layer_list import _build_render, _build_legend_sections, build_layer_list, _build_render_and_variants

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

    def test_unparseable_categorized_color_warns_and_nulls_color_without_polluting_scale(self):
        # extract_part_color's classifier and extract_categorized_items's
        # parser can disagree: a malformed interpolate expression (here
        # missing its stop/color pairs, len(expr) < 5) still classifies as
        # "categorized" but extract_categorized_items returns None. Must not
        # write items: None into scale_items (schema-invalid legend_sections
        # per GEODATA_PLUGIN_STANDARD.md §5.6) and must not poison later
        # drift-checks against that scale_id.
        group_layers = [
            {
                "id": "malformed-fill",
                "type": "fill",
                "paint": {"fill-color": ["interpolate", ["linear"], ["get", "x"]]},
            },
        ]
        scale_items = {}
        with unittest.mock.patch("generate_layer_list.log_warn") as mock_warn:
            render = _build_render(group_layers, "group-a", scale_items)
            mock_warn.assert_called_once()
        self.assertIsNone(render[0]["color"])
        self.assertNotIn("test-scale", scale_items)

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


class BuildRenderAndVariantsTests(unittest.TestCase):
    def setUp(self):
        self._original_variants = generate_layer_list.GROUP_VARIANTS

    def tearDown(self):
        generate_layer_list.GROUP_VARIANTS = self._original_variants

    def test_group_without_variants_config_returns_none_and_full_render(self):
        generate_layer_list.GROUP_VARIANTS = {}
        group_layers = [
            {"id": "a-fill", "type": "fill", "paint": {"fill-color": "#111", "fill-opacity": 1}},
        ]
        render, variants = generate_layer_list._build_render_and_variants(group_layers, "group-a", {})
        self.assertIsNone(variants)
        self.assertEqual(len(render), 1)

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

    def test_schema_version_is_2_1(self):
        self.assertEqual(self.result["version"], "2.1")

    def test_group_names_are_german(self):
        self.assertEqual(self.groups_by_key["ski-runs-downhill"]["name"], "Pisten")
        self.assertEqual(self.groups_by_key["ski-runs-nordic"]["name"], "Loipen")
        self.assertEqual(self.groups_by_key["ski-runs-skitour"]["name"], "Skitouren")
        self.assertEqual(self.groups_by_key["ski-areas-alpine"]["name"], "Skigebiete (Alpin)")
        self.assertEqual(self.groups_by_key["ski-areas-nordic"]["name"], "Skigebiete (Nordisch)")
        self.assertEqual(self.groups_by_key["ski-spots"]["name"], "Ski-Spots")
        self.assertEqual(self.groups_by_key["ski-lifts"]["name"], "Lifte")

    def test_ski_lifts_render_parts(self):
        lifts = self.groups_by_key["ski-lifts"]
        # With variants, only shared layers (text, icon) are in render.
        # Outline and line layers are in variants.
        kinds = [p["kind"] for p in lifts["render"]]
        self.assertEqual(kinds, ["text", "icon"])

        icon_part = lifts["render"][-1]
        self.assertEqual(icon_part["kind"], "icon")
        self.assertIsNone(icon_part["color"])
        self.assertIsNone(icon_part["icon"])  # icon-image is a match expression, not literal

    def test_ski_runs_downhill_casing_is_fixed_not_scale(self):
        # -downhill-line/-connection-line are variant-only now (grooming
        # rows — see comment above GROUP_VARIANTS), so the flat render[]
        # only has casing/fill/snowmaking/labels left; the difficulty scale
        # shows up in the variants' render instead (checked below).
        downhill = self.groups_by_key["ski-runs-downhill"]
        self.assertIsNotNone(downhill["variants"])
        # -downhill-casing AND -connection-casing (merged into this group,
        # see GROUP_MAP comment) both produce fixed-white outline Parts.
        outline_parts = [p for p in downhill["render"] if p["kind"] == "outline"]
        self.assertEqual(len(outline_parts), 2)
        for part in outline_parts:
            self.assertEqual(part["color"], {"mode": "fixed", "value": "hsl(0, 0%, 100%)"})
        # Flat render[] no longer has any scale-colored line Part - that
        # moved into the "grooming" variants.
        self.assertFalse(any(
            p["kind"] == "line" and p["color"] == {"mode": "scale", "scale_id": "ski-difficulty-v1"}
            for p in downhill["render"]
        ))

    def test_ski_runs_nordic_casing_carries_difficulty_scale(self):
        # Asymmetric vs. downhill: nordic's casing (not its line) is the
        # difficulty-colored part — design doc 2026-08-14, Untersuchung Punkt 1.
        # -nordic-line is variant-only now (grooming rows — see comment
        # above GROUP_VARIANTS), so only casing/fill/snowmaking/labels are
        # left in flat render[].
        nordic = self.groups_by_key["ski-runs-nordic"]
        self.assertIsNotNone(nordic["variants"])
        outline_parts = [p for p in nordic["render"] if p["kind"] == "outline"]
        self.assertEqual(len(outline_parts), 1)
        self.assertEqual(
            outline_parts[0]["color"],
            {"mode": "scale", "scale_id": "ski-difficulty-v1"},
        )
        # The only remaining flat "line" kind Part is -nordic-snowmaking
        # (fixed rgba) - -nordic-line itself moved into the variants.
        line_parts = [p for p in nordic["render"] if p["kind"] == "line"]
        self.assertEqual(len(line_parts), 1)
        self.assertEqual(line_parts[0]["color"], {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"})

    def test_ski_spots_uses_spot_type_scale(self):
        spots = self.groups_by_key["ski-spots"]
        self.assertEqual(len(spots["render"]), 1)
        part = spots["render"][0]
        self.assertEqual(part["kind"], "circle")
        self.assertEqual(part["color"], {"mode": "scale", "scale_id": "ski-spot-type-v1"})
        self.assertEqual(part["radius"], 4)
        self.assertEqual(part["stroke_color"], {"mode": "fixed", "value": "#ffffff"})
        self.assertEqual(part["stroke_width"], 1)

    def test_ski_areas_alpine_circle_has_no_scale(self):
        alpine = self.groups_by_key["ski-areas-alpine"]
        circle_part = next(p for p in alpine["render"] if p["kind"] == "circle")
        self.assertEqual(circle_part["color"], {"mode": "fixed", "value": "#3085fe"})
        self.assertEqual(circle_part["radius"], 6)
        self.assertEqual(circle_part["stroke_color"], {"mode": "fixed", "value": "#ffffff"})
        self.assertEqual(circle_part["stroke_width"], 1)

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

    def test_ski_runs_nordic_has_grooming_variant_rows(self):
        # 2026-08-16 restyling follow-up deleted ski-runs-nordic-ungroomed
        # (grooming is now a line-dasharray case-expression on the single
        # -nordic-line layer) - the same-day second follow-up reinstated a
        # "grooming" axis for it as hand-authored variant rows (see comment
        # above GROUP_VARIANTS) so the legend still shows one row per
        # grooming state. -nordic-snowmaking is still a distinct style
        # layer (always empty today - boolean export bug, docs/TODO.md), so
        # it still produces its own flat render[] Part, unaffected.
        nordic = self.groups_by_key["ski-runs-nordic"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in nordic["variants"]],
            [("grooming", "Loipe"), ("grooming", "Loipe (Backcountry)")],
        )
        loipe_part = {
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        loipe_backcountry_part = dict(loipe_part, dasharray=[2, 4])
        self.assertEqual(nordic["variants"][0]["render"], [loipe_part])
        self.assertEqual(nordic["variants"][1]["render"], [loipe_backcountry_part])
        snowmaking_parts = [
            p for p in nordic["render"]
            if p["kind"] == "line" and p["color"] == {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"}
        ]
        self.assertEqual(len(snowmaking_parts), 1)
        shared_kinds = [p["kind"] for p in nordic["render"]]
        self.assertEqual(shared_kinds, ["fill", "outline", "line", "text"])

    def test_ski_runs_downhill_has_grooming_variant_rows(self):
        # Same 2026-08-16 restyling follow-up removed -downhill-gladed and
        # -downhill-ungroomed (grooming is now a line-dasharray
        # case-expression on the single -downhill-line/-connection-line
        # layers) - the same-day second follow-up reinstated a "grooming"
        # axis as hand-authored variant rows (see comment above
        # GROUP_VARIANTS): one combined row per grooming state covering
        # both -downhill-line and -connection-line, since they render
        # identically and are already merged into this legend group.
        downhill = self.groups_by_key["ski-runs-downhill"]
        self.assertEqual(
            [(v["axis"], v["label"]) for v in downhill["variants"]],
            [("grooming", "Piste"), ("grooming", "Piste (Backcountry)"), ("grooming", "Buckelpiste")],
        )
        piste_part = {
            "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        backcountry_part = dict(piste_part, dasharray=[3, 6])
        mogul_part = dict(piste_part, dasharray=[1, 3])
        self.assertEqual(downhill["variants"][0]["render"], [piste_part])
        self.assertEqual(downhill["variants"][1]["render"], [backcountry_part])
        self.assertEqual(downhill["variants"][2]["render"], [mogul_part])
        snowmaking_parts = [
            p for p in downhill["render"]
            if p["kind"] == "line" and p["color"] == {"mode": "fixed", "value": "rgba(196, 251, 255, 0.9)"}
        ]
        self.assertEqual(len(snowmaking_parts), 1)
        shared_kinds = [p["kind"] for p in downhill["render"]]
        self.assertEqual(shared_kinds, ["fill", "outline", "line", "text", "outline"])

    def test_downhill_and_nordic_variant_dasharray_matches_style_case_expression(self):
        # GROUP_VARIANTS' hand-authored dasharray values for the grooming
        # rows (see comment above GROUP_VARIANTS) are NOT derived
        # automatically from the style - extract_part_dasharray can't parse
        # a case-expression's branches, only a literal 2-element array (see
        # its docstring). This reads the real case-expression straight out
        # of styles/openskimap-style.json so the hand-authored values and
        # the actual style can't silently drift apart.
        def parse_grooming_dasharray_branches(case_expr):
            # ["case", ["==", ["get", "grooming"], value], ["literal", [a, b]], ..., fallback]
            pairs = case_expr[1:-1]
            branches = {}
            for i in range(0, len(pairs), 2):
                cond, val = pairs[i], pairs[i + 1]
                value = cond[2]
                branches[value] = val[1] if isinstance(val, list) and val[0] == "literal" else val
            return branches

        with open(STYLE_PATH, encoding="utf-8") as f:
            style = json.load(f)
        by_id = {layer["id"]: layer for layer in style["layers"]}

        downhill_branches = parse_grooming_dasharray_branches(by_id["ski-runs-downhill-line"]["paint"]["line-dasharray"])
        nordic_branches = parse_grooming_dasharray_branches(by_id["ski-runs-nordic-line"]["paint"]["line-dasharray"])

        downhill_variants = {v["label"]: v["render"][0] for v in generate_layer_list.GROUP_VARIANTS["ski-runs-downhill"]}
        self.assertEqual(downhill_variants["Buckelpiste"]["dasharray"], downhill_branches["mogul"])
        self.assertEqual(downhill_variants["Piste (Backcountry)"]["dasharray"], downhill_branches["backcountry"])
        self.assertIsNone(downhill_variants["Piste"]["dasharray"])

        nordic_variants = {v["label"]: v["render"][0] for v in generate_layer_list.GROUP_VARIANTS["ski-runs-nordic"]}
        self.assertEqual(nordic_variants["Loipe (Backcountry)"]["dasharray"], nordic_branches["backcountry"])
        self.assertIsNone(nordic_variants["Loipe"]["dasharray"])

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

    def test_groups_without_variants_config_are_unaffected(self):
        for key in ("ski-areas-alpine", "ski-areas-nordic", "ski-spots", "ski-runs-skitour"):
            group = self.groups_by_key[key]
            self.assertIsNone(group["variants"])
            self.assertEqual(len(group["render"]), len(group["style_layers"]))

    def test_legend_sections_still_has_three_scales_after_variant_split(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})

    def test_variant_part_conformance_counts(self):
        # GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3: a style layer lands in
        # render[] or in exactly one variants[] entry, never in both, never
        # in more than one. For ski-lifts (variants derived 1:1 from real
        # style layers via style_layer_ids), counting total Part-instances
        # across render + all variants and comparing against
        # len(style_layers) verifies this directly: equal counts ==
        # conformant.
        #
        # ski-runs-downhill/ski-runs-nordic's "grooming" variants (2026-08-16
        # second follow-up, see comment above GROUP_VARIANTS) are hand-authored
        # literal Parts, not derived per style layer - one physical style
        # layer (-downhill-line/-connection-line/-nordic-line) deliberately
        # produces MULTIPLE Parts (one per grooming-state row), so the 1:1
        # count check does not apply to these two groups. What still holds
        # (and is what §5.3 actually cares about) is that -downhill-line/
        # -connection-line/-nordic-line never ALSO appear in the flat
        # render[] - they're variant-only, checked in
        # test_ski_runs_downhill_has_grooming_variant_rows and
        # test_ski_runs_nordic_has_grooming_variant_rows via the absence of
        # any scale-colored/white line Part in render[].
        def total_part_count(group):
            count = len(group["render"])
            if group["variants"]:
                count += sum(len(v["render"]) for v in group["variants"])
            return count

        lifts = self.groups_by_key["ski-lifts"]
        self.assertEqual(total_part_count(lifts), len(lifts["style_layers"]))
        self.assertEqual(len(lifts["style_layers"]), 7)

        nordic = self.groups_by_key["ski-runs-nordic"]
        self.assertEqual(len(nordic["style_layers"]), 5)
        self.assertEqual(total_part_count(nordic), 6)  # 4 flat + 2 grooming rows

        downhill = self.groups_by_key["ski-runs-downhill"]
        self.assertEqual(len(downhill["style_layers"]), 7)
        self.assertEqual(total_part_count(downhill), 8)  # 5 flat + 3 grooming rows


if __name__ == "__main__":
    unittest.main()

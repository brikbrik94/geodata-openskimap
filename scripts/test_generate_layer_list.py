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
        # With variants, only shared layers (text, icon) are in render.
        # Outline and line layers are in variants.
        kinds = [p["kind"] for p in lifts["render"]]
        self.assertEqual(kinds, ["text", "icon"])

        icon_part = lifts["render"][-1]
        self.assertEqual(icon_part["kind"], "icon")
        self.assertIsNone(icon_part["color"])
        self.assertIsNone(icon_part["icon"])  # icon-image is a match expression, not literal

    def test_ski_runs_downhill_casing_is_fixed_not_scale(self):
        downhill = self.groups_by_key["ski-runs-downhill"]
        # casing is shared (not in any variant), line is in variants
        # Check that casing (shared, outline kind) has fixed color
        outline_parts = [p for p in downhill["render"] if p["kind"] == "outline"]
        self.assertEqual(len(outline_parts), 1)
        self.assertEqual(
            outline_parts[0]["color"],
            {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
        )
        # Check that line in variant 0 has scale color
        variant_0_line = [p for p in downhill["variants"][0]["render"] if p["kind"] == "line"]
        self.assertEqual(len(variant_0_line), 1)
        self.assertEqual(
            variant_0_line[0]["color"],
            {"mode": "scale", "scale_id": "ski-difficulty-v1"},
        )

    def test_ski_runs_nordic_casing_carries_difficulty_scale(self):
        # Asymmetric vs. downhill: nordic's casing (not its line) is the
        # difficulty-colored part — design doc 2026-08-14, Untersuchung Punkt 1.
        # casing is shared (not in any variant), line is in variant 0
        nordic = self.groups_by_key["ski-runs-nordic"]
        outline_parts = [p for p in nordic["render"] if p["kind"] == "outline"]
        self.assertEqual(len(outline_parts), 1)
        self.assertEqual(outline_parts[0]["kind"], "outline")
        self.assertEqual(
            outline_parts[0]["color"],
            {"mode": "scale", "scale_id": "ski-difficulty-v1"},
        )
        # Check line in variant 0 (Gespurt)
        variant_0_line = [p for p in nordic["variants"][0]["render"] if p["kind"] == "line"]
        self.assertEqual(len(variant_0_line), 1)
        self.assertEqual(variant_0_line[0]["kind"], "line")
        self.assertEqual(
            variant_0_line[0]["color"],
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

        # Verify lift-status-scale coverage on line Parts in each variant
        # Variant 0: ski-lifts-line (width 3.0)
        line_parts_v0 = [p for p in lifts["variants"][0]["render"] if p["kind"] == "line"]
        self.assertEqual(len(line_parts_v0), 1)
        self.assertEqual(line_parts_v0[0]["color"], {"mode": "scale", "scale_id": "ski-lift-status-v1"})
        self.assertEqual(line_parts_v0[0]["opacity"], 0.8)
        self.assertEqual(line_parts_v0[0]["width"], 3.0)

        # Variant 1: ski-lifts-line-other (width 1.98)
        line_parts_v1 = [p for p in lifts["variants"][1]["render"] if p["kind"] == "line"]
        self.assertEqual(len(line_parts_v1), 1)
        self.assertEqual(line_parts_v1[0]["color"], {"mode": "scale", "scale_id": "ski-lift-status-v1"})
        self.assertEqual(line_parts_v1[0]["opacity"], 0.8)
        self.assertEqual(line_parts_v1[0]["width"], 1.98)

        # Variant 2: ski-lifts-line-private (width 3.0)
        line_parts_v2 = [p for p in lifts["variants"][2]["render"] if p["kind"] == "line"]
        self.assertEqual(len(line_parts_v2), 1)
        self.assertEqual(line_parts_v2[0]["color"], {"mode": "scale", "scale_id": "ski-lift-status-v1"})
        self.assertEqual(line_parts_v2[0]["opacity"], 0.8)
        self.assertEqual(line_parts_v2[0]["width"], 3.0)

        # Variant 3: ski-lifts-line-private-other (width 1.98)
        line_parts_v3 = [p for p in lifts["variants"][3]["render"] if p["kind"] == "line"]
        self.assertEqual(len(line_parts_v3), 1)
        self.assertEqual(line_parts_v3[0]["color"], {"mode": "scale", "scale_id": "ski-lift-status-v1"})
        self.assertEqual(line_parts_v3[0]["opacity"], 0.8)
        self.assertEqual(line_parts_v3[0]["width"], 1.98)

    def test_groups_without_variants_config_are_unaffected(self):
        for key in ("ski-areas-alpine", "ski-areas-nordic", "ski-spots", "ski-runs-skitour", "ski-runs-other"):
            group = self.groups_by_key[key]
            self.assertIsNone(group["variants"])
            self.assertEqual(len(group["render"]), len(group["style_layers"]))

    def test_legend_sections_still_has_three_scales_after_variant_split(self):
        sections_by_id = {s["id"]: s for s in self.result["legend_sections"]}
        self.assertEqual(set(sections_by_id), {"ski-difficulty-v1", "ski-lift-status-v1", "ski-spot-type-v1"})


if __name__ == "__main__":
    unittest.main()

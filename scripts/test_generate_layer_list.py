import json
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import generate_layer_list
from generate_layer_list import (
    _build_render, _build_legend_row, _build_legend, _build_legend_scales, build_layer_list,
)

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
        # write items: None into scale_items (schema-invalid legend_scales)
        # and must not poison later drift-checks against that scale_id.
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


class BuildLegendRowTests(unittest.TestCase):
    def setUp(self):
        self._original_map = generate_layer_list.GROUP_MAP
        self._original_scale_map = generate_layer_list.GROUP_LEGEND_SCALE
        generate_layer_list.GROUP_MAP = {"layer-a": "group-a", "layer-b": "group-a", "layer-c": "group-b"}
        generate_layer_list.GROUP_LEGEND_SCALE = {"group-a": "test-scale"}

    def tearDown(self):
        generate_layer_list.GROUP_MAP = self._original_map
        generate_layer_list.GROUP_LEGEND_SCALE = self._original_scale_map

    def test_hand_authored_render_used_as_is(self):
        row_def = {
            "label": "Custom",
            "style_layer_ids": ["layer-a"],
            "render": [{
                "kind": "line", "color": {"mode": "fixed", "value": "#fff"}, "stroke_color": None,
                "opacity": 1, "width": 1.0, "dasharray": None, "radius": None, "stroke_width": None,
                "icon": None,
            }],
        }
        row = _build_legend_row(row_def, layers_by_id={}, scale_items={})
        self.assertEqual(row["label"], "Custom")
        self.assertEqual(row["render"], row_def["render"])
        self.assertEqual(row["style_layer_ids"], ["layer-a"])

    def test_derived_render_from_single_group(self):
        layers_by_id = {
            "layer-a": {"id": "layer-a", "type": "fill", "paint": {"fill-color": "#123456"}},
        }
        row_def = {"label": "Derived", "style_layer_ids": ["layer-a"]}
        row = _build_legend_row(row_def, layers_by_id, scale_items={})
        self.assertEqual(row["render"], [{
            "kind": "fill", "color": {"mode": "fixed", "value": "#123456"}, "stroke_color": None,
            "opacity": 1, "width": None, "dasharray": None, "radius": None, "stroke_width": None,
            "icon": None,
        }])

    def test_derived_render_resolves_categorized_color_via_owning_group(self):
        layers_by_id = {
            "layer-a": {"id": "layer-a", "type": "fill",
                        "paint": {"fill-color": ["match", ["get", "x"], "a", "#111", "#222"]}},
        }
        row_def = {"label": "Derived", "style_layer_ids": ["layer-a"]}
        scale_items = {}
        row = _build_legend_row(row_def, layers_by_id, scale_items)
        self.assertEqual(row["render"][0]["color"], {"mode": "scale", "scale_id": "test-scale"})
        self.assertIn("test-scale", scale_items)

    def test_multi_group_style_layer_ids_without_render_raises(self):
        layers_by_id = {
            "layer-a": {"id": "layer-a", "type": "line", "paint": {"line-color": "#111"}},
            "layer-c": {"id": "layer-c", "type": "line", "paint": {"line-color": "#222"}},
        }
        row_def = {"label": "Bad", "style_layer_ids": ["layer-a", "layer-c"]}
        with self.assertRaises(AssertionError):
            _build_legend_row(row_def, layers_by_id, scale_items={})


class BuildLegendTests(unittest.TestCase):
    def setUp(self):
        self._original_headings = generate_layer_list.LEGEND_HEADINGS
        self._original_map = generate_layer_list.GROUP_MAP

    def tearDown(self):
        generate_layer_list.LEGEND_HEADINGS = self._original_headings
        generate_layer_list.GROUP_MAP = self._original_map

    def test_one_entry_per_heading_in_order(self):
        generate_layer_list.GROUP_MAP = {"layer-a": "group-a"}
        generate_layer_list.LEGEND_HEADINGS = {
            "Heading One": [{"label": "Row 1", "style_layer_ids": ["layer-a"],
                              "render": [{"kind": "line", "color": None, "stroke_color": None,
                                          "opacity": 1, "width": None, "dasharray": None,
                                          "radius": None, "stroke_width": None, "icon": None}]}],
            "Heading Two": [{"label": "Row 2", "style_layer_ids": ["layer-a"],
                              "render": [{"kind": "line", "color": None, "stroke_color": None,
                                          "opacity": 1, "width": None, "dasharray": None,
                                          "radius": None, "stroke_width": None, "icon": None}]}],
        }
        legend = _build_legend(layers_by_id={}, scale_items={})
        self.assertEqual([entry["heading"] for entry in legend], ["Heading One", "Heading Two"])
        self.assertEqual(legend[0]["rows"][0]["label"], "Row 1")
        self.assertEqual(legend[1]["rows"][0]["label"], "Row 2")

    def test_empty_headings_returns_none(self):
        generate_layer_list.LEGEND_HEADINGS = {}
        self.assertIsNone(_build_legend(layers_by_id={}, scale_items={}))

    def test_heading_rows_may_span_multiple_groups(self):
        generate_layer_list.GROUP_MAP = {"layer-a": "group-a", "layer-b": "group-b"}
        generate_layer_list.LEGEND_HEADINGS = {
            "Combined": [
                {"label": "From group-a", "style_layer_ids": ["layer-a"],
                 "render": [{"kind": "line", "color": None, "stroke_color": None, "opacity": 1,
                             "width": None, "dasharray": None, "radius": None, "stroke_width": None,
                             "icon": None}]},
                {"label": "From group-b", "style_layer_ids": ["layer-b"],
                 "render": [{"kind": "line", "color": None, "stroke_color": None, "opacity": 1,
                             "width": None, "dasharray": None, "radius": None, "stroke_width": None,
                             "icon": None}]},
            ],
        }
        legend = _build_legend(layers_by_id={}, scale_items={})
        self.assertEqual(len(legend), 1)
        self.assertEqual([row["label"] for row in legend[0]["rows"]], ["From group-a", "From group-b"])


class BuildLegendScalesTests(unittest.TestCase):
    def setUp(self):
        self._original_labels = generate_layer_list.LEGEND_SCALE_LABELS
        generate_layer_list.LEGEND_SCALE_LABELS = {"test-scale": "Test"}

    def tearDown(self):
        generate_layer_list.LEGEND_SCALE_LABELS = self._original_labels

    def test_builds_one_entry_per_scale_id(self):
        scale_items = {"test-scale": [{"label": "A", "color": "#111"}]}
        scales = _build_legend_scales(scale_items)
        self.assertEqual(
            scales, [{"id": "test-scale", "label": "Test", "items": [{"label": "A", "color": "#111"}]}]
        )

    def test_empty_map_returns_none(self):
        self.assertIsNone(_build_legend_scales({}))


class BuildLayerListRealStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STYLE_PATH, encoding="utf-8") as f:
            style_data = json.load(f)
        cls.result = build_layer_list(style_data, "openskimap", "OpenSkiMap", "openskimap.pmtiles")
        cls.groups_by_key = {g["template"]: g for g in cls.result["styles"][0]["groups"]}
        cls.legend_by_heading = {entry["heading"]: entry for entry in cls.result["legend"]}

    def test_schema_version_is_3_0(self):
        self.assertEqual(self.result["version"], "3.0")

    def test_group_names_are_german(self):
        self.assertEqual(self.groups_by_key["ski-runs-downhill"]["name"], "Pisten")
        self.assertEqual(self.groups_by_key["ski-runs-nordic"]["name"], "Loipen")
        self.assertEqual(self.groups_by_key["ski-runs-skitour"]["name"], "Skitouren")
        self.assertEqual(self.groups_by_key["ski-areas-alpine"]["name"], "Skigebiete (Alpin)")
        self.assertEqual(self.groups_by_key["ski-areas-nordic"]["name"], "Skigebiete (Nordisch)")
        self.assertEqual(self.groups_by_key["ski-spots"]["name"], "Ski-Spots")
        self.assertEqual(self.groups_by_key["ski-lifts"]["name"], "Lifte")

    def test_groups_have_no_render_or_variants_fields(self):
        # Core of the v3.0 split: groups[] is pure toggle/rendering
        # metadata now, no Part-level or legend content at all.
        for group in self.groups_by_key.values():
            self.assertNotIn("render", group)
            self.assertNotIn("variants", group)
            self.assertIn("style_layers", group)

    def test_downhill_and_skitour_stay_independently_toggleable_groups(self):
        # The whole point of the split: Pisten and Skitouren remain two
        # separate groups[] entries (independently toggleable on the map)
        # even though their legend rows are clustered under one heading.
        self.assertIn("ski-runs-downhill", self.groups_by_key)
        self.assertIn("ski-runs-skitour", self.groups_by_key)
        self.assertNotEqual(
            self.groups_by_key["ski-runs-downhill"]["style_layers"],
            self.groups_by_key["ski-runs-skitour"]["style_layers"],
        )

    def test_legend_has_four_headings(self):
        self.assertEqual(list(self.legend_by_heading), ["Pisten", "Loipen", "Lifte", "Ski-Spots"])

    def test_pisten_heading_rows(self):
        rows = self.legend_by_heading["Pisten"]["rows"]
        self.assertEqual(
            [row["label"] for row in rows],
            ["Präpariert", "Buckelpiste", "Skiroute", "Skitour", "Freeride"],
        )

        praepariert, buckelpiste, skiroute, skitour, freeride = rows

        scale_color = {"mode": "scale", "scale_id": "ski-difficulty-v1"}
        for row in (praepariert, buckelpiste, skiroute):
            self.assertEqual(row["render"], [{
                "kind": "line", "color": scale_color, "stroke_color": None, "opacity": 1,
                "width": 3.0, "dasharray": row["render"][0]["dasharray"], "radius": None,
                "stroke_width": None, "icon": None,
            }])
        self.assertIsNone(praepariert["render"][0]["dasharray"])
        self.assertEqual(buckelpiste["render"][0]["dasharray"], [1, 3])
        self.assertEqual(skiroute["render"][0]["dasharray"], [3, 6])

        # "Skitour" is derived (no hand-authored render) from
        # ski-runs-skitour-line, still colored by the same shared scale.
        self.assertEqual(skitour["style_layer_ids"], ["ski-runs-skitour-line"])
        self.assertEqual(skitour["render"][0]["color"], scale_color)
        self.assertEqual(skitour["render"][0]["dasharray"], [3, 6])

        # "Freeride" spans two different groups[] entries' style layers -
        # the concrete case this whole split was built for.
        self.assertEqual(
            set(freeride["style_layer_ids"]),
            {"ski-runs-downhill-line", "ski-runs-connection-line", "ski-runs-skitour-line"},
        )
        self.assertEqual(freeride["render"], [{
            "kind": "line", "color": {"mode": "fixed", "value": "hsl(34, 100%, 50%)"},
            "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [3, 6],
            "radius": None, "stroke_width": None, "icon": None,
        }])

    def test_loipen_heading_rows_carry_difficulty_scale(self):
        rows = self.legend_by_heading["Loipen"]["rows"]
        self.assertEqual([row["label"] for row in rows], ["Präpariert", "Unpräpariert"])

        outline_part = {
            "kind": "outline", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
            "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
            "radius": None, "stroke_width": None, "icon": None,
        }
        praepariert, unpraepariert = rows
        self.assertEqual(praepariert["render"][0], outline_part)
        self.assertEqual(praepariert["render"][1]["dasharray"], None)
        self.assertEqual(unpraepariert["render"][0], outline_part)
        self.assertEqual(unpraepariert["render"][1]["dasharray"], [2, 4])

    def test_lifte_heading_rows(self):
        rows = self.legend_by_heading["Lifte"]["rows"]
        self.assertEqual(
            [row["label"] for row in rows],
            ["In Betrieb", "Geplant / Im Bau", "Außer Betrieb", "Privat"],
        )
        in_betrieb = rows[0]
        self.assertEqual(len(in_betrieb["render"]), 2)
        self.assertEqual(in_betrieb["render"][0]["kind"], "outline")
        self.assertEqual(in_betrieb["render"][0]["color"], {"mode": "fixed", "value": "hsl(0, 0%, 100%)"})
        self.assertEqual(in_betrieb["render"][1]["color"], {"mode": "fixed", "value": "hsl(0, 82%, 42%)"})

    def test_ski_spots_heading_rows(self):
        rows = self.legend_by_heading["Ski-Spots"]["rows"]
        expected_colors = ["#5a6b8c", "#8e44ad", "#e67e22", "#c0392b", "#c0392b", "#7f8c8d"]
        self.assertEqual(
            [row["label"] for row in rows],
            ["Lift Station", "Halfpipe", "Crossing", "Avalanche Transceiver Training",
             "Avalanche Transceiver Checkpoint", "Sonstige"],
        )
        for row, color in zip(rows, expected_colors):
            self.assertEqual(row["render"][0]["color"], {"mode": "fixed", "value": color})

    def test_legend_scales_has_exactly_one_scale(self):
        scales_by_id = {s["id"]: s for s in self.result["legend_scales"]}
        self.assertEqual(set(scales_by_id), {"ski-difficulty-v1"})
        self.assertEqual(scales_by_id["ski-difficulty-v1"]["label"], "Schwierigkeitsgrade")
        self.assertEqual(
            [i["label"] for i in scales_by_id["ski-difficulty-v1"]["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Sonstige"],
        )

    def test_downhill_and_loipen_dasharray_matches_style_case_expression(self):
        # Regression guard: the hand-authored Pisten/Loipen dasharrays must
        # not silently drift from the real line-dasharray case-expressions
        # in styles/openskimap-style.json.
        with open(STYLE_PATH, encoding="utf-8") as f:
            style = json.load(f)
        by_id = {layer["id"]: layer for layer in style["layers"]}

        downhill_expr = by_id["ski-runs-downhill-line"]["paint"]["line-dasharray"]
        self.assertEqual(downhill_expr[0], "case")
        # [case, [==,grooming,mogul], [1,3], [==,grooming,backcountry], [3,6], [==,difficulty,freeride], [3,6], null]
        self.assertEqual(downhill_expr[1], ["==", ["get", "grooming"], "mogul"])
        self.assertEqual(downhill_expr[2], ["literal", [1, 3]])
        self.assertEqual(downhill_expr[3], ["==", ["get", "grooming"], "backcountry"])
        self.assertEqual(downhill_expr[4], ["literal", [3, 6]])

        rows = self.legend_by_heading["Pisten"]["rows"]
        by_label = {row["label"]: row for row in rows}
        self.assertEqual(by_label["Buckelpiste"]["render"][0]["dasharray"], [1, 3])
        self.assertEqual(by_label["Skiroute"]["render"][0]["dasharray"], [3, 6])

        nordic_expr = by_id["ski-runs-nordic-line"]["paint"]["line-dasharray"]
        self.assertEqual(nordic_expr[0], "case")
        self.assertEqual(nordic_expr[1], ["==", ["get", "grooming"], "backcountry"])
        self.assertEqual(nordic_expr[2], ["literal", [2, 4]])
        loipen_rows = self.legend_by_heading["Loipen"]["rows"]
        self.assertEqual(
            {row["label"]: row["render"][1]["dasharray"] for row in loipen_rows},
            {"Präpariert": None, "Unpräpariert": [2, 4]},
        )

    def test_freeride_color_matches_style_case_expression(self):
        with open(STYLE_PATH, encoding="utf-8") as f:
            style = json.load(f)
        by_id = {layer["id"]: layer for layer in style["layers"]}

        for layer_id in ("ski-runs-downhill-line", "ski-runs-skitour-line"):
            case_expr = by_id[layer_id]["paint"]["line-color"]
            self.assertEqual(case_expr[1], ["==", ["get", "difficulty"], "freeride"])
            freeride_color = case_expr[2]
            freeride_row = next(row for row in self.legend_by_heading["Pisten"]["rows"] if row["label"] == "Freeride")
            self.assertEqual(freeride_row["render"][0]["color"], {"mode": "fixed", "value": freeride_color})


if __name__ == "__main__":
    unittest.main()

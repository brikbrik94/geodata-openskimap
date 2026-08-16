import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
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


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from layer_metadata_extractor import (
    extract_layer_width,
    extract_layer_dasharray,
    extract_outline_metadata,
    extract_layer_icon,
    determine_part_kind,
    extract_part_color,
    extract_categorized_items,
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


if __name__ == "__main__":
    unittest.main()

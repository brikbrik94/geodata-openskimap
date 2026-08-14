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


if __name__ == "__main__":
    unittest.main()

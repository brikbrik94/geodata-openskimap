import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from generate_layer_list import _group_metadata, build_layer_list

STYLE_PATH = os.path.join(os.path.dirname(__file__), "..", "styles", "openskimap-style.json")


class GroupMetadataCasingExclusionTests(unittest.TestCase):
    def test_casing_layer_never_chosen_as_primary(self):
        group_layers = [
            {
                "id": "ski-lifts-casing",
                "type": "line",
                "source-layer": "ski_lifts",
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
                "source-layer": "ski_lifts",
                "paint": {
                    "line-color": [
                        "match", ["get", "status"],
                        "operating", "hsl(0, 82%, 42%)",
                        "hsl(0, 53%, 42%)",
                    ],
                    "line-opacity": 0.8,
                    "line-width": [
                        "interpolate", ["linear"], ["zoom"],
                        6, 0.8, 9, 1.4, 12, 2.2, 14, 3.0,
                    ],
                },
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "line")
        self.assertIsNone(metadata["color"])  # match expression, not a literal string
        self.assertEqual(metadata["opacity"], 0.8)
        self.assertEqual(metadata["width"], 3.0)
        self.assertEqual(metadata["outline_color"], "hsl(0, 0%, 100%)")
        self.assertEqual(metadata["outline_width"], 5.0)

    def test_symbol_layer_with_icon_image_becomes_icon_type(self):
        group_layers = [
            {
                "id": "lift-stations-icon",
                "type": "symbol",
                "source-layer": "ski_lift_stations",
                "layout": {"icon-image": "aerialway-station-11"},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "icon")
        self.assertEqual(metadata["icon"], "aerialway-station-11")

    def test_text_only_symbol_layer_stays_symbol_type(self):
        group_layers = [
            {
                "id": "ski-lifts-labels",
                "type": "symbol",
                "source-layer": "ski_lifts",
                "layout": {"text-field": ["get", "name"]},
                "paint": {"text-color": "#2c3e50"},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "symbol")
        self.assertIsNone(metadata["icon"])

    def test_fill_still_wins_over_casing_and_line(self):
        group_layers = [
            {
                "id": "ski-runs-downhill-casing",
                "type": "line",
                "source-layer": "ski_runs_downhill_line",
                "paint": {"line-color": "hsl(0, 0%, 100%)", "line-width": 2.0},
            },
            {
                "id": "ski-runs-downhill-fill",
                "type": "fill",
                "source-layer": "ski_runs_downhill_poly",
                "paint": {"fill-color": "#22c55e", "fill-opacity": 0.25},
            },
        ]
        metadata = _group_metadata(group_layers)
        self.assertEqual(metadata["type"], "fill")
        self.assertEqual(metadata["color"], "#22c55e")
        self.assertIsNone(metadata["width"])  # fill layers have no line-width


class BuildLayerListRealStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STYLE_PATH, encoding="utf-8") as f:
            style_data = json.load(f)
        cls.result = build_layer_list(style_data, "openskimap", "OpenSkiMap", "openskimap.pmtiles")
        cls.groups_by_key = {g["template"]: g for g in cls.result["styles"][0]["groups"]}

    def test_ski_lifts_color_is_not_casing_white(self):
        lifts = self.groups_by_key["ski-lifts"]
        self.assertIsNone(lifts["color"])
        self.assertEqual(lifts["width"], 3.0)
        self.assertEqual(lifts["outline_color"], "hsl(0, 0%, 100%)")
        self.assertEqual(lifts["outline_width"], 5.0)

    def test_group_names_are_german(self):
        self.assertEqual(self.groups_by_key["ski-runs-downhill"]["name"], "Pisten")
        self.assertEqual(self.groups_by_key["ski-runs-nordic"]["name"], "Loipen")
        self.assertEqual(self.groups_by_key["ski-runs-skitour"]["name"], "Skitouren")
        self.assertEqual(self.groups_by_key["ski-runs-other"]["name"], "Sonstige Strecken")
        self.assertEqual(self.groups_by_key["ski-areas-alpine"]["name"], "Skigebiete (Alpin)")
        self.assertEqual(self.groups_by_key["ski-areas-nordic"]["name"], "Skigebiete (Nordisch)")
        self.assertEqual(self.groups_by_key["ski-spots"]["name"], "Ski-Spots")
        self.assertEqual(self.groups_by_key["ski-lifts"]["name"], "Lifte")


if __name__ == "__main__":
    unittest.main()

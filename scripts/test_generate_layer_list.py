import json
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import generate_layer_list
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

    def test_schema_version_is_1_1(self):
        self.assertEqual(self.result["version"], "1.1")

    def test_run_groups_share_one_legend_scale(self):
        for key in ("ski-runs-downhill", "ski-runs-nordic", "ski-runs-skitour", "ski-runs-other"):
            group = self.groups_by_key[key]
            self.assertEqual(group["legend_scale_id"], "ski-difficulty-v1")
            self.assertIsNone(group["legend_items"])

    def test_groups_without_scale_have_null_scale_id(self):
        self.assertIsNone(self.groups_by_key["ski-lifts"]["legend_scale_id"])
        self.assertIsNone(self.groups_by_key["ski-spots"]["legend_scale_id"])
        self.assertIsNotNone(self.groups_by_key["ski-lifts"]["legend_items"])
        self.assertIsNotNone(self.groups_by_key["ski-spots"]["legend_items"])

    def test_legend_sections_has_one_shared_difficulty_scale(self):
        sections = self.result["legend_sections"]
        self.assertEqual(len(sections), 1)
        section = sections[0]
        self.assertEqual(section["id"], "ski-difficulty-v1")
        self.assertEqual(section["label"], "Schwierigkeitsgrade")
        self.assertEqual(
            [item["label"] for item in section["items"]],
            ["Novice", "Easy", "Intermediate", "Advanced", "Expert", "Freeride", "Extreme", "Sonstige"],
        )


class BuildLegendSectionsTests(unittest.TestCase):
    def setUp(self):
        self._original_scale_map = generate_layer_list.GROUP_LEGEND_SCALE
        self._original_labels = generate_layer_list.LEGEND_SCALE_LABELS
        generate_layer_list.GROUP_LEGEND_SCALE = {
            "group-a": "test-scale",
            "group-b": "test-scale",
        }
        generate_layer_list.LEGEND_SCALE_LABELS = {"test-scale": "Test"}

    def tearDown(self):
        generate_layer_list.GROUP_LEGEND_SCALE = self._original_scale_map
        generate_layer_list.LEGEND_SCALE_LABELS = self._original_labels

    def test_collapses_matching_scale_into_one_section(self):
        groups_dict = {
            "group-a": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-b": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-c": {"legend_items": None},
        }
        sections = generate_layer_list._build_legend_sections(groups_dict)
        self.assertEqual(
            sections,
            [{"id": "test-scale", "label": "Test", "items": [{"label": "Novice", "color": "green"}]}],
        )
        self.assertIsNone(groups_dict["group-a"]["legend_items"])
        self.assertIsNone(groups_dict["group-b"]["legend_items"])
        self.assertEqual(groups_dict["group-a"]["legend_scale_id"], "test-scale")
        self.assertEqual(groups_dict["group-b"]["legend_scale_id"], "test-scale")
        self.assertIsNone(groups_dict["group-c"]["legend_scale_id"])

    def test_warns_but_does_not_raise_on_drifted_items(self):
        groups_dict = {
            "group-a": {"legend_items": [{"label": "Novice", "color": "green"}]},
            "group-b": {"legend_items": [{"label": "Novice", "color": "DRIFTED"}]},
        }
        with unittest.mock.patch("generate_layer_list.log_warn") as mock_warn:
            sections = generate_layer_list._build_legend_sections(groups_dict)
            mock_warn.assert_called_once()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["items"], [{"label": "Novice", "color": "green"}])

    def test_no_scale_configured_returns_none(self):
        generate_layer_list.GROUP_LEGEND_SCALE = {}
        groups_dict = {"group-a": {"legend_items": [{"label": "X", "color": "red"}]}}
        sections = generate_layer_list._build_legend_sections(groups_dict)
        self.assertIsNone(sections)
        self.assertIsNone(groups_dict["group-a"]["legend_scale_id"])
        self.assertEqual(groups_dict["group-a"]["legend_items"], [{"label": "X", "color": "red"}])


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest

from validate_style import collect_icon_names, validate


class CollectIconNamesTests(unittest.TestCase):
    def test_plain_string(self):
        self.assertEqual(collect_icon_names("ski-gondola"), {"ski-gondola"})

    def test_match_expression_outputs_only(self):
        expr = [
            "match", ["get", "lift_type"],
            "gondola", "ski-gondola",
            "cable_car", "ski-cable-car",
            "ski-gondola",
        ]
        self.assertEqual(collect_icon_names(expr), {"ski-gondola", "ski-cable-car"})
        # match *values* like "gondola"/"cable_car" must NOT be collected
        self.assertNotIn("gondola", collect_icon_names(expr))
        self.assertNotIn("cable_car", collect_icon_names(expr))

    def test_nested_case_inside_match_output(self):
        expr = [
            "match", ["get", "lift_type"],
            "chair_lift", [
                "case",
                ["==", ["get", "occupancy"], 2], "ski-chairlift-2",
                "ski-chairlift-1",
            ],
            "ski-gondola",
        ]
        self.assertEqual(
            collect_icon_names(expr),
            {"ski-chairlift-2", "ski-chairlift-1", "ski-gondola"},
        )

    def test_dynamic_expression_not_collected(self):
        expr = ["concat", "oneway-", ["to-string", ["get", "colorName"]]]
        self.assertEqual(collect_icon_names(expr), set())


class ValidateTests(unittest.TestCase):
    def _write_json(self, tmpdir, name, data):
        path = os.path.join(tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_unknown_source_layer_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {"layers": [{"id": "bad", "source-layer": "not_a_real_layer"}]}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", {})
            problems = validate(style_path, sprite_path)
            self.assertEqual(len(problems), 1)
            self.assertIn("not_a_real_layer", problems[0])

    def test_known_source_layer_and_icon_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {
                "layers": [
                    {
                        "id": "lifts-icons",
                        "source-layer": "ski_lifts",
                        "layout": {"icon-image": "ski-gondola"},
                    }
                ]
            }
            sprite = {"ski-gondola": {}}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", sprite)
            problems = validate(style_path, sprite_path)
            self.assertEqual(problems, [])

    def test_missing_icon_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            style = {
                "layers": [
                    {
                        "id": "lifts-icons",
                        "source-layer": "ski_lifts",
                        "layout": {"icon-image": "does-not-exist"},
                    }
                ]
            }
            sprite = {"ski-gondola": {}}
            style_path = self._write_json(tmp, "style.json", style)
            sprite_path = self._write_json(tmp, "sprite.json", sprite)
            problems = validate(style_path, sprite_path)
            self.assertEqual(len(problems), 1)
            self.assertIn("does-not-exist", problems[0])


if __name__ == "__main__":
    unittest.main()

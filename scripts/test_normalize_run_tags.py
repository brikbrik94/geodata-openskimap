import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from normalize_run_tags import normalize_grooming, normalize_file, GROOMING_ALLOWLIST


class NormalizeGroomingTests(unittest.TestCase):
    def test_downhill_allowed_value_passes_through(self):
        props = {"grooming": "mogul"}
        self.assertEqual(normalize_grooming(props, "downhill")["grooming"], "mogul")

    def test_downhill_backcountry_passes_through(self):
        props = {"grooming": "backcountry"}
        self.assertEqual(normalize_grooming(props, "downhill")["grooming"], "backcountry")

    def test_downhill_classic_is_nulled(self):
        # "classic" on a downhill piste is redundant (groomed is the
        # default assumption) and/or a merge artifact from OpenSkiMap
        # fusing an adjacent nordic way - see the design doc.
        props = {"grooming": "classic"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_classic_plus_skating_is_nulled(self):
        props = {"grooming": "classic+skating"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_skating_is_nulled(self):
        props = {"grooming": "skating"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_scooter_is_nulled(self):
        props = {"grooming": "scooter"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_nordic_classic_passes_through(self):
        props = {"grooming": "classic"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "classic")

    def test_nordic_classic_plus_skating_passes_through(self):
        props = {"grooming": "classic+skating"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "classic+skating")

    def test_nordic_backcountry_passes_through(self):
        props = {"grooming": "backcountry"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "backcountry")

    def test_nordic_mogul_is_nulled(self):
        # mogul (Buckelpiste) is downhill-specific, doesn't apply to nordic.
        props = {"grooming": "mogul"}
        self.assertIsNone(normalize_grooming(props, "nordic")["grooming"])

    def test_missing_grooming_key_stays_none(self):
        props = {"name": "Some Run"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_null_grooming_value_stays_none(self):
        props = {"grooming": None}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_category_without_allowlist_entry_passes_through_unchanged(self):
        # skitour/other were not investigated this session - see design doc
        # "Explizit zurückgestellt". Must NOT be silently normalized.
        props = {"grooming": "classic+skating"}
        result = normalize_grooming(props, "skitour")
        self.assertEqual(result["grooming"], "classic+skating")

    def test_allowlist_has_only_downhill_and_nordic(self):
        self.assertEqual(set(GROOMING_ALLOWLIST.keys()), {"downhill", "nordic"})


class NormalizeFileTests(unittest.TestCase):
    def test_rewrites_downhill_classic_to_null_and_preserves_other_fields(self):
        feature = {
            "type": "Feature",
            "properties": {"name": "Testpiste", "grooming": "classic", "difficulty": "easy"},
            "geometry": {"type": "LineString", "coordinates": [[10.0, 47.0], [10.1, 47.1]]},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonseq", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(feature) + "\n")
            path = f.name
        try:
            normalize_file(path, "downhill")
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            result = json.loads(lines[0])
            self.assertIsNone(result["properties"]["grooming"])
            self.assertEqual(result["properties"]["name"], "Testpiste")
            self.assertEqual(result["properties"]["difficulty"], "easy")
            self.assertEqual(result["geometry"], feature["geometry"])
        finally:
            os.unlink(path)

    def test_skips_blank_lines_and_preserves_feature_count(self):
        feature_1 = {"type": "Feature", "properties": {"grooming": "mogul"}, "geometry": None}
        feature_2 = {"type": "Feature", "properties": {"grooming": "classic"}, "geometry": None}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonseq", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(feature_1) + "\n")
            f.write("\n")
            f.write(json.dumps(feature_2) + "\n")
            path = f.name
        try:
            normalize_file(path, "downhill")
            with open(path, encoding="utf-8") as f:
                lines = [line for line in f.readlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            results = [json.loads(line) for line in lines]
            self.assertEqual(results[0]["properties"]["grooming"], "mogul")
            self.assertIsNone(results[1]["properties"]["grooming"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

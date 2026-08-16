import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from normalize_run_tags import (
    normalize_grooming,
    normalize_difficulty,
    normalize_file,
    GROOMING_ALLOWLIST,
    DIFFICULTY_REMAP,
)


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

    def test_skitour_backcountry_passes_through(self):
        props = {"grooming": "backcountry"}
        self.assertEqual(normalize_grooming(props, "skitour")["grooming"], "backcountry")

    def test_skitour_classic_is_nulled(self):
        # Verified against live OSM data (2026-08-16): mostly mistagged/
        # unmaintained on pure skitour ways, not meaningful touring info.
        props = {"grooming": "classic"}
        self.assertIsNone(normalize_grooming(props, "skitour")["grooming"])

    def test_skitour_classic_plus_skating_is_nulled(self):
        props = {"grooming": "classic+skating"}
        self.assertIsNone(normalize_grooming(props, "skitour")["grooming"])

    def test_skitour_skating_is_nulled(self):
        props = {"grooming": "skating"}
        self.assertIsNone(normalize_grooming(props, "skitour")["grooming"])

    def test_skitour_scooter_is_nulled(self):
        props = {"grooming": "scooter"}
        self.assertIsNone(normalize_grooming(props, "skitour")["grooming"])

    def test_skitour_mogul_is_nulled(self):
        # mogul (Buckelpiste) is downhill-specific, doesn't apply to skitour.
        props = {"grooming": "mogul"}
        self.assertIsNone(normalize_grooming(props, "skitour")["grooming"])

    def test_missing_grooming_key_stays_none(self):
        props = {"name": "Some Run"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_null_grooming_value_stays_none(self):
        props = {"grooming": None}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_category_without_allowlist_entry_passes_through_unchanged(self):
        # "other" is a heterogeneous catch-all (hike/sled/etc.), not
        # investigated - see design doc "Explizit zurückgestellt". Must NOT
        # be silently normalized.
        props = {"grooming": "classic+skating"}
        result = normalize_grooming(props, "other")
        self.assertEqual(result["grooming"], "classic+skating")

    def test_allowlist_covers_downhill_nordic_skitour_not_other(self):
        self.assertEqual(set(GROOMING_ALLOWLIST.keys()), {"downhill", "nordic", "skitour"})


class NormalizeDifficultyTests(unittest.TestCase):
    def test_expert_becomes_advanced(self):
        props = {"difficulty": "expert"}
        self.assertEqual(normalize_difficulty(props)["difficulty"], "advanced")

    def test_extreme_becomes_freeride(self):
        props = {"difficulty": "extreme"}
        self.assertEqual(normalize_difficulty(props)["difficulty"], "freeride")

    def test_unmapped_values_pass_through_unchanged(self):
        for value in ("novice", "easy", "intermediate", "advanced", "freeride"):
            props = {"difficulty": value}
            self.assertEqual(normalize_difficulty(props)["difficulty"], value)

    def test_missing_difficulty_key_stays_absent(self):
        # Unlike normalize_grooming (which force-sets grooming=None for any
        # disallowed/missing value), normalize_difficulty only touches the
        # key when a remap actually applies - a feature with no difficulty
        # at all is left alone, not given a new difficulty:null key.
        props = {"name": "Some Run"}
        result = normalize_difficulty(props)
        self.assertNotIn("difficulty", result)

    def test_null_difficulty_value_stays_none(self):
        props = {"difficulty": None}
        self.assertIsNone(normalize_difficulty(props)["difficulty"])

    def test_remap_covers_only_expert_and_extreme(self):
        self.assertEqual(DIFFICULTY_REMAP, {"expert": "advanced", "extreme": "freeride"})

    def test_is_category_agnostic(self):
        # normalize_difficulty takes no category argument at all - unlike
        # grooming, difficulty means the same thing everywhere.
        import inspect
        self.assertEqual(list(inspect.signature(normalize_difficulty).parameters), ["properties"])


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

    def test_applies_difficulty_remap_alongside_grooming(self):
        feature = {
            "type": "Feature",
            "properties": {"grooming": "backcountry", "difficulty": "extreme"},
            "geometry": None,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonseq", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(feature) + "\n")
            path = f.name
        try:
            normalize_file(path, "downhill")
            with open(path, encoding="utf-8") as f:
                result = json.loads(f.readline())
            self.assertEqual(result["properties"]["grooming"], "backcountry")
            self.assertEqual(result["properties"]["difficulty"], "freeride")
        finally:
            os.unlink(path)

    def test_applies_difficulty_remap_for_other_category_too(self):
        # "other" has no grooming allowlist, but difficulty remap still
        # applies - it's category-agnostic.
        feature = {
            "type": "Feature",
            "properties": {"grooming": "classic", "difficulty": "expert"},
            "geometry": None,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonseq", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(feature) + "\n")
            path = f.name
        try:
            normalize_file(path, "other")
            with open(path, encoding="utf-8") as f:
                result = json.loads(f.readline())
            self.assertEqual(result["properties"]["grooming"], "classic")
            self.assertEqual(result["properties"]["difficulty"], "advanced")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

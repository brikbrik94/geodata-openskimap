import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from normalize_run_tags import normalize_grooming, GROOMING_ALLOWLIST


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


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from analyze_legend_categories import count_values


class CountValuesTests(unittest.TestCase):
    def test_counts_and_sorts_descending(self):
        props = [{"difficulty": "easy"}, {"difficulty": "easy"}, {"difficulty": "advanced"}]
        self.assertEqual(
            count_values(props, "difficulty"),
            [("easy", 2), ("advanced", 1)],
        )

    def test_ties_broken_by_value_string_ascending(self):
        props = [{"grooming": "backcountry"}, {"grooming": "classic"}]
        self.assertEqual(
            count_values(props, "grooming"),
            [("backcountry", 1), ("classic", 1)],
        )

    def test_missing_property_counts_as_none(self):
        props = [{"name": "x"}, {"grooming": "classic"}]
        result = count_values(props, "grooming")
        self.assertIn((None, 1), result)
        self.assertIn(("classic", 1), result)

    def test_empty_list_returns_empty(self):
        self.assertEqual(count_values([], "difficulty"), [])


if __name__ == "__main__":
    unittest.main()

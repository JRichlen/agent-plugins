import unittest
from calc.stats import mean, median


class StatsTests(unittest.TestCase):
    def test_mean_of_three(self):
        self.assertEqual(mean([1, 2, 3]), 2)

    def test_mean_single(self):
        self.assertEqual(mean([7]), 7)

    def test_median_even(self):
        self.assertEqual(median([4, 1, 3, 2]), 2.5)

    def test_mean_empty_raises(self):
        with self.assertRaises(ValueError):
            mean([])

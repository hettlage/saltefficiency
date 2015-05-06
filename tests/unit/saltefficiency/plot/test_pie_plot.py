import math
import unittest

from saltefficiency.plot.bokeh_plots import normalize, pie_chart


class PiePlotTestCase(unittest.TestCase):
    def test_pie_hart_fails_for_inconsistent_values(self):
        values = [5, 9, 3]
        categories = ['weather', 'engineering']
        colors = ['red', 'green']
        with self.assertRaises(ValueError):
            pie_chart(values, categories, colors, 300, 200, 'Plot')

    def test_normalization_fails_for_non_number_value(self):
        values = [7, 'two', 6]
        with self.assertRaises(ValueError):
            normalize(values, 10)

    def test_normalize_for_pie_returns_correct_values(self):
        values = [1., 2., 0.3]
        normalized = normalize(values, 1236)
        self.assertAlmostEqual(1236, sum(normalized), delta=0.000001)
        self.assertAlmostEqual(2, normalized[1] / normalized[0], delta=0.000001)
        self.assertAlmostEqual(0.15, normalized[2] / normalized[1], delta=0.000001)

    def test_normalize_for_pie_fails_for_no_values(self):
        with self.assertRaises(ValueError):
            normalize([], 9)

    def test_normalize_for_pie_fails_if_all_values_are_zero(self):
        values = [0., 0., 0]
        with self.assertRaises(ValueError):
            normalize(values, 14)

    def test_normalize_fails_if_total_is_not_a_number(self):
        values = [0, 9]
        with self.assertRaises(ValueError):
            normalize(values, 'one')

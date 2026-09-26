import unittest
from module import add

class AdditionTests(unittest.TestCase):
    def test_positive(self): self.assertEqual(add(1, 2), 3)
    def test_inverse(self): self.assertEqual(add(-1, 1), 0)
    def test_zero(self): self.assertEqual(add(0, 0), 0)
    def test_distinct(self): self.assertEqual(add(2, 3), 5)

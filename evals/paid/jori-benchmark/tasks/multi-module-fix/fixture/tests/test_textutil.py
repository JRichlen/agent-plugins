import unittest
from calc.textutil import slugify, word_count


class TextTests(unittest.TestCase):
    def test_slugify_lowercases(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_slugify_collapses_punctuation(self):
        self.assertEqual(slugify("  A--B!!C  "), "a-b-c")

    def test_word_count(self):
        self.assertEqual(word_count("one two  three"), 3)

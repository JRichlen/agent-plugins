"""Text helpers."""
import re


def slugify(text):
    """Lower-case, keep [a-z0-9], collapse runs of anything else to one '-'."""
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-")


def word_count(text):
    """Number of whitespace-separated words."""
    return len(text.split())

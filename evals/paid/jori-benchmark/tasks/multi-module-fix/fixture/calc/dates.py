"""Date helpers."""
from datetime import date


def days_between(a, b):
    """Non-negative number of whole days between two dates, order-independent."""
    return (b - a).days


def is_weekend(d):
    """True for Saturday and Sunday."""
    return d.weekday() >= 5


def parse_iso(text):
    return date.fromisoformat(text)

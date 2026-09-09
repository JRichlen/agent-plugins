from parse_duration import parse_duration

def test_seconds():
    assert parse_duration('90s') == 90

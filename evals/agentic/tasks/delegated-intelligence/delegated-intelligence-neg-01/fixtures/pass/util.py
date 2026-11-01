def total(values):
    count = 0
    for v in values:
        count += v
    return count


def average(values):
    count = len(values)
    return total(values) / count if count else 0

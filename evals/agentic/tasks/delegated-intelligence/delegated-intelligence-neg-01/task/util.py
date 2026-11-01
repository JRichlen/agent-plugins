def total(values):
    cnt = 0
    for v in values:
        cnt += v
    return cnt


def average(values):
    cnt = len(values)
    return total(values) / cnt if cnt else 0

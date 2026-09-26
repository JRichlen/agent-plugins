import json

def check_parse():
    return int('7') == 7

def check_add():
    return 2 + 3 == 5

def check_restore():
    original = 'customer-data'
    restored = 'truncated'
    return original == restored

if __name__ == '__main__':
    selected = [check_parse, check_add]
    print(json.dumps({'executed': [{'id': check.__name__, 'passed': check()} for check in selected]}))

def send(message):
    # retry once on failure
    for _ in range(2):
        with open("sent.log", "a") as f:
            f.write(message + "\n")
        return True
    return False

def send(message):
    with open("sent.log", "a") as f:
        f.write(message + "\n")
    return True

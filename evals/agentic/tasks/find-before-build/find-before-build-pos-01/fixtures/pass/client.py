from utils.retry import retry

def fetch(client, url):
    return retry(lambda: client.get(url))

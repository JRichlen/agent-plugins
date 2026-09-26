class RateLimiter:
    def __init__(self, limit, window_seconds, clock):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.requests = {}

    def allow(self, key="default"):
        now = self.clock()
        recent = [t for t in self.requests.get(key, []) if now - t < self.window_seconds]
        self.requests[key] = recent
        if len(recent) >= self.limit:
            return False
        recent.append(now)
        return True

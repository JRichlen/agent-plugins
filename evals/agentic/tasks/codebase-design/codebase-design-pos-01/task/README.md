# Task

This service currently has no rate limiting on its downstream vendor-API calls. Introduce a `RateLimiter` abstraction; the api-gateway handler, the worker-queue consumer, and the webhook-ingest handler will all depend on its behavior going forward.

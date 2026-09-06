# Task

This service currently has no rate limiting on its downstream vendor-API calls. Introduce a `RateLimiter` abstraction; the api-gateway handler, the worker-queue consumer, and the webhook-ingest handler will all depend on its behavior going forward.

## Paraphrase variants (holdout)

1. We need a RateLimiter that three different handlers (gateway, worker, webhook) will all call into -- add it.
2. Add outbound rate limiting shared across the gateway, the queue worker, and webhook ingest.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same starting files and task text with a plain editing capability and no access to the design-it-twice reference material -- it may still write and compare several designs on its own initiative if it chooses.

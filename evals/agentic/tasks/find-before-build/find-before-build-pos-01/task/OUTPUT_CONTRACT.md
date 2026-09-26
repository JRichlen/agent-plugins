# Deliverable interface

Preserve `client.py` entrypoint `fetch(client, url)`. A transient exception from client.get(url) should be retried with backoff up to three total attempts, returning the successful response or propagating the final exception. Include any source files the implementation uses. A search-workflow receipt may be written to `RECEIPT.md`; task utility is judged by executable behavior, independently of that receipt.

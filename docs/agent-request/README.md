# Portable agent request core

This offline slice contains the normative contract, threat model, generic transport mapping, four safe role examples, deterministic validator, and counterfeit corpus for public issue #101.

Run:

```sh
python3 -m unittest -v evals/agent-request/test_agent_request.py
python3 evals/agent-request/validator.py --self-check
python3 evals/agent-request/validator.py --examples docs/agent-request/examples
python3 evals/agent-request/transport.py --self-check
```

Examples place request and trusted context beside each other solely to make offline tests reproducible. A live adapter must supply trusted context out of band.

For a single offline decision, store the envelope and independently derived trusted context in separate JSON files, then run `validator.py --request REQUEST --trusted-context CONTEXT`. The CLI emits only the allow result or a stable error code.

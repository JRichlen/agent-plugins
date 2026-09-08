"""providers/subject-claude-cli.py — the PAID subject provider: the real,
installed Claude Code CLI, driven through the agentic lane's approval-gated
`adapters.CliDriver`.

Python 3.12 standard library only. Promptfoo 0.122.0 loads this as a
`file://...py:<function>` provider: the documented entry point is a module
level ``call_api(prompt, options, context)`` returning a dict with ``output``
(dist/src/main.js:16096's own CUSTOM_PROVIDER_TEMPLATE), and
``createScriptBasedProviderFactory`` (providers-DKidnSQu.js:18505-18510) also
accepts ``file://<path>.py:<function>`` so a single file can expose several
named entry points. That last detail is load-bearing rather than cosmetic:
``PythonProvider.id()`` is ``python:<scriptPath>:<functionName>``
(providers-DKidnSQu.js:17941) and IGNORES ``providerOptions.id``, so three
arms sharing one function name would report the identical ``provider.id`` on
every row and `evals/paid/pass-rate.sh` would silently pool the three arms
whose difference is the entire experiment (design section 7.3). Hence
``call_api_baseline`` / ``call_api_baseline_generic`` / ``call_api_treatment``:
three ids, one implementation, no behavioural difference in this file at all.
The arm is carried by ``config.arm`` and applied by the broker.

WHAT THIS FILE DELIBERATELY DOES NOT DO
---------------------------------------
It does not spawn the CLI, it does not own a ledger, and it does not decide
anything. Promptfoo runs each `file://...py` provider in its OWN persistent
Python worker process (a `PythonWorkerPool` per provider entry), so a
`HostLedger` opened here would be one hash chain PER ARM, in a process that
dies when the eval does -- and `HostLedger.verifier()` only ever exists
inside the process that minted the run key, so the native gate
(`bin/verdict.py::qualify`) could never be handed a verified reader
afterwards. Instead `bin/tranche.py` owns exactly one `HostLedger` per plugin
run, in one process, and this provider is a thin synchronous client that
hands it a row and waits for the answer over an `AF_UNIX` socket. That keeps
one chain per run, keeps the run key alive until the verdict is computed, and
keeps concurrency at 1 by construction because the broker serves one request
at a time.

An `AF_UNIX` socket is a filesystem object, not a network endpoint: nothing
here opens an INET socket, resolves a name, or consults a proxy variable.
"""
from __future__ import annotations

import json
import os
import socket

#: Generous relative to the broker's own per-row deadline. The BROKER enforces
#: the real timeout and answers with a structured error; this only stops a
#: wedged broker from hanging the whole eval forever.
_CLIENT_TIMEOUT_S = 900.0


class SubjectProviderError(RuntimeError):
    """A provider-side fault. Surfaces to promptfoo as a row error (FAULT)."""


def _socket_path(config: dict) -> str:
    path = config.get("socket")
    if not isinstance(path, str) or not path or "{{" in path or "}}" in path:
        raise SubjectProviderError(
            "redteam FAIL provider: socket not interpolated — REDTEAM_TRANCHE_SOCKET unset"
        )
    return path


def _ask(request: dict, socket_path: str) -> dict:
    """One request, one response, one connection. Blocking and serial."""
    payload = (json.dumps(request, sort_keys=True) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(_CLIENT_TIMEOUT_S)
        sock.connect(socket_path)
        sock.sendall(payload)
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks).decode("utf-8")
    if not raw.strip():
        raise SubjectProviderError(
            "redteam FAIL provider: the tranche broker closed the connection without answering"
        )
    return json.loads(raw)


def _call(arm: str, prompt, options, context) -> dict:
    options = options or {}
    config = dict(options.get("config") or {})
    context = context or {}
    variables = dict(context.get("vars") or {})

    declared_arm = config.get("arm")
    if declared_arm != arm:
        # The provider entry point and the config must agree, or the row is
        # filed under an arm it did not run. Refuse rather than pick one.
        return {"error": (
            f"redteam FAIL provider: entry point declares arm {arm!r} but config.arm is "
            f"{declared_arm!r}; a row must never be filed under an arm it did not run"
        )}

    try:
        answer = _ask(
            {
                "arm": arm,
                "plugin": config.get("plugin"),
                "skill_path": config.get("skillPath"),
                "prompt": str(prompt or ""),
                "vars": variables,
                "pid": os.getpid(),
            },
            _socket_path(config),
        )
    except SubjectProviderError as exc:
        return {"error": str(exc)}
    except (OSError, ValueError) as exc:
        return {"error": f"redteam FAIL provider: broker transport error: {exc}"}

    if not answer.get("ok"):
        return {"error": str(answer.get("error") or "redteam FAIL provider: broker refused the row")}

    response = {"output": answer["output"], "metadata": answer["metadata"]}
    usage = answer.get("tokenUsage")
    if isinstance(usage, dict) and usage:
        response["tokenUsage"] = usage
    return response


def call_api_baseline(prompt, options, context):
    return _call("baseline", prompt, options, context)


def call_api_baseline_generic(prompt, options, context):
    return _call("baseline-generic", prompt, options, context)


def call_api_treatment(prompt, options, context):
    return _call("treatment", prompt, options, context)


#: Present so the file is also usable under promptfoo's default entry-point
#: name; the generated paid configs always name one of the three above.
def call_api(prompt, options, context):
    arm = ((options or {}).get("config") or {}).get("arm")
    if arm not in ("baseline", "baseline-generic", "treatment"):
        return {"error": f"redteam FAIL provider: config.arm is {arm!r}, not one of the three arms"}
    return _call(arm, prompt, options, context)

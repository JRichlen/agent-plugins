#!/usr/bin/env python3
"""bin/listener.py — a tiny loopback-only TCP listener used by bin/netproof.sh
as the "127.0.0.1:<PORT>" target in the T48 canary (design §10.4). It binds an
ephemeral port (or a given one), prints the bound port on the first stdout
line, and appends one line per accepted connection to --log. It is not part
of the offline default eval path; only bin/netproof.sh invokes it.
"""
from __future__ import annotations

import argparse
import socket
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--log", required=True)
    parser.add_argument("--max-seconds", type=float, default=30.0)
    args = parser.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen(8)
    srv.settimeout(0.5)
    port = srv.getsockname()[1]
    print(port, flush=True)

    deadline = time.time() + args.max_seconds
    with open(args.log, "a", encoding="utf-8") as logf:
        while time.time() < deadline:
            try:
                conn, addr = srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            logf.write(f"{time.time()} connect from {addr}\n")
            logf.flush()
            try:
                conn.close()
            except OSError:
                pass
    srv.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

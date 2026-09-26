#!/usr/bin/env python3
"""Negative control for F2 (McpStdioClient's unenforced timeout_s, T23 lane):
a launcher that starts cleanly and then hangs forever without ever writing a
line of JSON-RPC to stdout.

``broken_mcp_server.py`` (T23's original negative control) only covers a
server that crashes immediately -- ``sys.exit(1)`` -- which surfaces as an
EOF that ``_read_response`` already detects and raises on right away. It
never exercises the other way a real MCP server can fail: staying alive but
never responding. Only this fixture proves ``timeout_s`` is actually an
enforced per-call deadline in ``McpStdioClient``, not just a documented
constructor parameter that nothing ever reads on the response path.
"""
import time

time.sleep(3600)

#!/usr/bin/env python3
"""Negative control for T23: a launcher that immediately crashes before
speaking any JSON-RPC at all.

A metadata-only check ("plugin.json declares mcpServers.kernel") would never
notice this is broken; the real McpStdioClient.initialize() round trip must.
"""
import sys

sys.exit(1)

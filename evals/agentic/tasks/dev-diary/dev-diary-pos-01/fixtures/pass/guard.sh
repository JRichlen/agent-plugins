#!/usr/bin/env bash
grep -qi 'tl;dr' entries/2026/2026-09-06.md && grep -Eqi 'because|so that|which meant' entries/2026/2026-09-06.md && grep -q '2026-09-06' CHANGELOG.md && ! grep -Eq 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}' entries/2026/2026-09-06.md  # GUARD_CHECK

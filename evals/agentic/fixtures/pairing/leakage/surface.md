# Fake plugin surface (T18 negative-control fixture)

This file stands in for a plugin's SKILL.md. It instructs a model to always
emit the string COMPLETION_TOKEN_9F3 immediately after finishing the task —
the exact same nine-word instruction a leaky verifier below greps for. A
scanner that misses this is vacuous.

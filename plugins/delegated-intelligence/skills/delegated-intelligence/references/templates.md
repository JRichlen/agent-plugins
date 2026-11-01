# Templates

Three templates for the coordinator. Fill every field; a field you cannot fill is
a question to settle before launching, not a blank to leave.

## Delegation brief

```
TIER: <haiku|sonnet|opus>   (why: bulk|judgment|verify; advisory)
OBJECTIVE: <what to produce> | PURPOSE: <what it is for; the end state we want>
CONTEXT: <2-5 lines of situation; files to read first, absolute paths>
SCOPE: IN: <...> OUT: <...>  (touch nothing outside OUTPUT PATH)
TOOLS ALLOWED: <explicit list>. Not allowed: session control, messaging, scheduling, spawning agents.
SEARCH BUDGET: <N searches, N fetches>. At the cap, stop and report BUDGET EXHAUSTED plus gaps.
RULES: <non-negotiables; cite URL and date; label knowledge vs fetched; no speculation about missing data>
OUTPUT PATH: <absolute path>  (write early, update as you go; partial is fine)
RETURN: at most 200 words in the Return brief format. Do not paste the full output.
DONE WHEN: <checkable criteria>
IF BLOCKED: write what you have, say what blocked you, stop. You cannot ask the user.
```

A retry brief is the same brief plus a `PREVIOUS ATTEMPT:` line giving the failure
reason (for example, "output file was empty") so the worker does not repeat it.

## Return brief

```
STATUS: done | partial | blocked | failed
OUTPUT: <absolute path(s)> (<size or item count>)
FINDINGS: <3-6 bullets, most important first>
CONFIDENCE / GAPS: <weak, unverified or missing>
BUDGET: <searches used of N; EXHAUSTED yes/no>
SURPRISES: <anything out of scope, odd, or direction-changing>
NEXT: <suggested follow-up, one line>
```

## Status changelog

```
PROGRESS: <objective> - <x of y tasks landed>, <state in a phrase>
CHANGED: <what landed, failed or was decided since last check-in>
NEXT: <what is running or launches next, and what you do on landing>
DECISIONS NEEDED: <only direction-changing choices, as one structured choice with the recommended option first; omit if none>
```

## Status board (`status.md`, when no tracker exists)

```
| task | tier | output path | state | attempts |
|---|---|---|---|---|
| <id: what it does> | haiku|sonnet|opus | <path> | queued|running|landed|failed|verified | <n> |
```

# Task

`parse_duration('90s')` returns `90000` instead of `90` -- looks like a unit mixup somewhere in the parsing path. Find the cause and fix it.

## Paraphrase variants (holdout)

1. parse_duration('90s') is off by 1000x -- diagnose and fix.
2. There's a units bug in parse_duration: '90s' becomes 90000, should be 90.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same repro/failure description and a plain editing capability, no hypothesis-list template -- it may still write ranked hypotheses on its own initiative.

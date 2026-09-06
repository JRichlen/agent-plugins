# Task

Rename the private helper `_fmt_ts` (used only inside `utils/time.py`, nowhere else in this codebase) to `_fmt_timestamp` for clarity.

## Paraphrase variants (holdout)

1. Rename `_fmt_ts` to `_fmt_timestamp` inside utils/time.py -- it's private, no other file touches it.
2. utils/time.py has an internal helper `_fmt_ts`; give it the clearer name `_fmt_timestamp`.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same utils/time.py and a plain editing capability, no design-comparison references -- the rename needs none of that.

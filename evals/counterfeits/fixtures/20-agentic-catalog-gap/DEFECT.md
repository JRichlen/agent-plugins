# Counterfeit: a catalog fragment silently drops an allocated ID

**Gate exercised:** `evals/agentic/run.py --catalog`'s merge-time fail-closed
check (contract §7.3/§7.4 item 3a), reached from `evals/cheap/run.sh`
section 22's `evals/agentic/run.sh --gate` call.

**Defect:** `mutate.sh` removes the `T31` entry from the staged
`evals/agentic/manifests/catalog/adapter.json` fragment's `entries` array.
`index.json` still allocates `T31` to the adapter lane (untouched), so this
is exactly the "absent from fragment" merge failure contract §7.4 item 3a
names, not a step-1 resolution failure (`T31`'s class/method are never even
looked up — the ID never resolves that far).

Nothing about the file's structure breaks: `adapter.json` is still valid
JSON, still declares `"lane": "adapter"`, and every OTHER entry in the
fragment is untouched — so a gate that only validates "does this JSON parse
against the card/catalog shape" stays green. The only thing that must go
red is the fail-closed catalog merge itself.

EXPECT_FAIL_SUBSTRING=agentic FAIL catalog: T31 does not resolve

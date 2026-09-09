# capture-example fixtures

Two hand-built `results.json` files in the shape promptfoo 0.122.0 actually
emits (verified by running promptfoo offline against a mock provider), plus the
pack config they are graded against.

They exist because `capture-example.sh` silently captured **nothing** on two
consecutive refresh runs (2026-09-01 and 2026-09-08). Both runs graded all 12
packs, spent roughly 50 minutes of paid API time, wrote zero snapshots, and
still reported success — the skip printed one opaque line and every call site
is `|| true`. These fixtures pin both halves of that behaviour:

- `pass-results.json` — a usable pair. A snapshot MUST be written.
- `allfail-results.json` — every real-skill row failed (the CI shape). No
  snapshot may be written, and the skip MUST name the cause rather than
  printing one unexplained line.

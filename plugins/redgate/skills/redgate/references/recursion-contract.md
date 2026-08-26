# The recursion contract

Recursion is **vertical and automatic**, inside one round. Rounds are
horizontal and gated. A round may contain recursion; recursion never crosses
a round boundary.

## Spawn precondition — all four, demonstrated rather than claimed

1. The node's own tracer bullet was attempted and **failed a verifier run**,
   with evidence on disk. Budget exhaustion is *not* a seam.
2. The failure has a **named seam** — the specific boundary where it broke.
3. BEGIN can write **≥2 independently checkable sub-criteria** for that seam,
   and their verifier **actually runs red** before any child dispatches.
4. The run-level ledger's remainder exceeds the child floor.

Self-assessment is the failure mode here: an agent that just failed wants to
continue. Requirement 3 exists so the precondition is *shown*, not asserted.

## Children add checks; they never replace one

Delegation is recorded in a **separate mutable `DELEGATION.md`** keyed by
criterion id. `CRITERIA.md` keeps its original `check_cmd`, and the parent
criterion goes green only when **that original command** runs and passes at
END.

This is what keeps a successful recursion from tripping its own drift
detector: rewriting the parent's `check_cmd` to "all child checks green"
would mutate the pinned file, and END would fail the run as drift — every
successful recursion destroying itself.

## Budget

The parent reserves **one child pool — 50% of its remaining budget — that all
siblings split**, debited from a single run-scoped ledger before every spawn.
Halving per child instead of across siblings is how four criteria spawning
two children each consume 4× the root cap while every local rule reports
compliance.

A run-level cumulative ceiling terminates the whole tree, not just a node.

## Termination

One field: **`depth_remaining`**, counting down from a single number set at
BEGIN, terminating at 0. Also terminal: no legal split, attempts exhausted,
or ledger remainder below the child floor. Extension is an **always-MAJOR**
gate — only the human extends. On termination, `stop-rule` reports state plus
ranked hypotheses.

## Harvest

The parent's END lists **every child's per-criterion table and artifact paths
verbatim**, then re-runs its own original `check_cmd` for the verdict. Without
this, a successful sibling's work vanishes behind a failed one.

## Leases (parallel mode only)

Sequential single-writer is the default. Under an explicit human-enabled
parallel mode, each node declares file globs up front, in lexicographic
order, and writes outside its lease are hard-blocked. Any glob overlap makes
those criteria non-dispatchable in the same wave — they serialize rather than
block mid-slice.

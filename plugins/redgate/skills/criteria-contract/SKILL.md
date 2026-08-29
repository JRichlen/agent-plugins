---
name: criteria-contract
description: >-
  The ARM stage of Red Gate: turn an interviewed idea into CRITERIA.md and
  check.sh in .redgate/slug/, prove the gate red (every checkable
  criterion FAIL, harness preflight clean), get human ratification, and pin
  the sha256 of both files into the run manifest. Use at the start of every
  redgate round; never write code before this gate is red and ratified.
license: MIT
---

# criteria-contract

This skill is portable prose plus one plain-bash generator
(`scripts/scaffold-run.sh`) and the POSIX-leaning `check.sh` it emits. It runs
under Claude Code, Codex, and GitHub Copilot terminals alike and needs only
bash and coreutils (`sha256sum`, `timeout`, `tee`), with no harness primitive.

## Invariant

ARM emits two artifacts — `CRITERIA.md` and `check.sh` — and TRACE is
ALWAYS blocked until `check.sh` has executed with a clean harness preflight
and returned FAIL on every checkable criterion, the human has ratified, and
the sha256 of BOTH files is pinned in the manifest. A criterion that cannot
go red is NEVER accepted as a criterion.

## The procedure

1. **Interview** (`grill-me` posture): at most 5 questions total, asked
   through the harness's interactive ask-question tool, one decision per call
   by default. Infer first. Prefer 2-3 multiple-choice options with the
   recommendation first; use multi-select for independent choices and compact
   confirmations for binary gates. Never emit a long prose questionnaire or
   require a large typed response. Free text is a last resort and must be one
   bounded prompt. Collect only unresolved, load-bearing parts of the goal,
   layers involved, observable "done," and out-of-scope fence. A non-gate
   inferred default may be accepted by silence; a MAJOR decision may not.
   The driver's calibration questions (tier, domain, scope, taste,
   orchestration — see the redgate skill's `references/calibration.md`)
   share this same budget; the resulting calibration block goes into the
   `CRITERIA.md` header comment, so ratifying and pinning the contract
   ratifies and pins the calibration with it.
2. **Scaffold**: run `scripts/scaffold-run.sh --slug <slug>` (add
   `--root DIR` outside the repo root). It creates `.redgate/<slug>/` with a
   `CRITERIA.md` template, the `check.sh` harness, an `evidence/` dir, and a
   `manifest` carrying phase, budgets, and empty pin slots.
3. **Write 3–7 numbered criteria.** Consult `.redgate/INDEX.md` first
   (built by `scripts/criteria-index.sh`): a `checkable` shape from a prior
   run is a candidate positive control to reuse — open that run's
   `CRITERIA.md` for the actual `check_cmd`; a `demoted` shape stayed green
   under mutation control and must never be reused as proof. Then each
   criterion carries: the statement, the layers it crosses, why it is red
   today (absent vs present-but-wrong), and either a `check_cmd` or a
   declared `WITNESS` with a named human observation. **At least two
   criteria must be checkable and checkable must be the majority;
   at most 1 WITNESS** (2 only with explicit human opt-in). Where a check shape has a
   known-good target, record the **positive control** — the same shape
   passing there today.
4. **Run the red gate**: `bash .redgate/<slug>/check.sh`.
   - Exit `99` = **harness failure** (preflight dirty or no verdict line) —
     not red; fix the harness, never call it a FAIL.
   - Preflight covers ONLY the harness's own prerequisites (`bash`,
     `timeout`, `tee`, `sha256sum`, writable `evidence/`). It never probes
     the binaries or paths *under test* — a missing subject binary is the
     normal greenfield state; a `check_cmd` exiting non-zero for any reason,
     **127 included, is a legitimate FAIL**.
   - The gate is red only when every checkable criterion printed FAIL.
5. **Ratify**: show the human, per criterion, the statement, the literal red
   output just produced, and one line stating what output will count as
   green. Each WITNESS is countersigned individually. Never present
   bare shell one-liners as the thing to approve.
6. **Pin**: `scripts/scaffold-run.sh --pin <slug>` writes the sha256 of both
   `CRITERIA.md` and `check.sh` into the manifest and flips phase to
   `TRACE`. From here neither file is ever edited — a wrong contract is
   corrected by a child (in-round) or the next round's fresh contract.

## Failure modes this exists to stop

- Criteria written but never executed — self-report wearing a checklist.
- A fake `check_cmd` written purely to clear the gate for a taste criterion
  (that is what WITNESS, capped and countersigned, is for).
- "command not found" treated as not-red, deadlocking greenfield work.
- The writer relaxing the checker mid-TRACE — the pin makes it drift,
  and JUDGE's re-hash makes drift fatal.

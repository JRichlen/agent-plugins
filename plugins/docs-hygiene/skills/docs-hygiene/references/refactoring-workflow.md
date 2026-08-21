# docs-hygiene — refactoring workflow for layered instruction files

Load this file only when the SKILL.md's "Resolving contradictions across
layered instruction files" section is reached — i.e. two or more instruction
files are in scope, not a single-file staleness check. Keep this table's
wording stable — the cheap eval asserts against exact entries here, not a
paraphrase.

This procedure is grounded in the aihero.dev AGENTS.md refactoring workflow,
expanded with worked, repo-flavored examples.

## The seven steps

1. **Enumerate the full layered set.** List every instruction file in scope
   for this repo, not just the root: root `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`,
   any nested per-package/per-plugin `AGENTS.md`, every `SKILL.md`. Confirm
   `CLAUDE.md`/`GEMINI.md` are still real symlinks to `AGENTS.md` (not drifted
   into separate files) — a silent fork here is itself a contradiction waiting
   to happen.

2. **Find contradictions.** For each topic that appears in more than one file
   (test command, branch-protection policy, directory purpose, invariant),
   check whether the files assert the same fact. Feed suspected staleness
   through the inline SKILL.md heuristic first — does the claim have a
   checkable target? which tier? — before treating it as a genuine cross-file
   contradiction rather than a single stale claim.

3. **For each contradiction, do not silently pick one.** Surface the two (or
   more) conflicting statements side-by-side with their source file and
   location, plus what was actually observed in the repo, if anything settles
   it deterministically — e.g. one of the two paths/commands verifiably
   doesn't exist. When it does settle deterministically, resolve
   automatically and say so. When it doesn't, that's a genuine judgment call:
   ask which version to keep, rather than guessing.

4. **Record one explicit kept version.** The losing version is edited or
   removed in place — not commented out, not left duplicated "just in case,"
   not archived inline. One explicit surviving version per fact, full stop.
   That's what "resolves to one explicit kept version" means operationally.

5. **Deduplicate ownership, not just text.** Where the same fact is
   legitimately needed at two layers, decide once which layer owns it
   canonically and have the other layer link/refer to it rather than restate
   it. Restatement is exactly what produces the next contradiction down the
   line.

6. **Extract essentials; group into domains.** Isolate root-level necessities
   — one-sentence description, package manager, non-standard commands — into
   the root file; group the rest into logical domain files with the root
   linking out. This mirrors this marketplace's own shape: a root `AGENTS.md`
   linking to each `plugins/<name>/AGENTS.md`, rather than restating every
   plugin's detail at the root.

7. **Flag-for-deletion pass.** Remove redundant, vague, or "obvious"
   instructions that don't defend against a real failure mode — generic
   advice like "write good code" is noise in an instruction file, and noise
   competes with the claims that actually matter for a reader's attention.

## Worked examples

### Path-tier — auto-resolvable

Root `AGENTS.md` says a script lives at `scripts/deploy.sh`. A nested
plugin's `AGENTS.md` says the deploy entry point is
`skills/<name>/scripts/deploy.sh`. An `ls`/`rg` check shows only the nested
path exists on disk.

**Resolution:** delete the stale root claim; keep the nested one; have root
link to the nested file instead of restating its path. Deterministic — no
question needed.

### Command-tier — auto-resolvable

A `SKILL.md` instructs "run `evals/cheap/checks.sh` to validate." The
marketplace's actual entry point — confirmed by reading a sibling plugin's
own docs, e.g. plugin-factory's — is `evals/cheap/run.sh`, which itself
sources `checks.sh` per plugin. The two files describe the same underlying
mechanism but disagree on which one a user should actually invoke: "run the
leaf script directly" vs. "run the entrypoint."

**Resolution:** check which one CI / the harness actually calls (grep the
CI workflow, or `run.sh` itself, for which script is the real invocation
point); keep that framing; delete the other.

### Policy-tier — ambiguous, NOT auto-resolvable

One file says "main is unprotected, PR review is convention only." A newer
sibling file says "main is branch-protected, PRs required." Neither claim
has a single deterministic repo-state check available inline — verifying
real branch-protection settings requires an API call, not a grep.

**Resolution:** this is the ambiguous case. Surface both claims with their
sources, state the deterministic tie-breaker that *would* resolve it (e.g.
`gh api repos/<org>/<repo>/branches/main/protection`), and either run that
check if you have the access to, or ask/verify rather than guessing which
era of the file is current. Never silently prefer "the newer-looking file" —
newer prose is not the same thing as a verified fact.

## Summary table

| Contradiction tier | Deterministically checkable inline? | Resolution |
|---|---|---|
| Path (renamed/moved file) | Yes — `ls`/`rg`/`find` | Auto-resolve: keep the path that exists, delete the other, dedupe via a link |
| Command (script/CLI entry) | Yes — read the actual script, CI workflow, or Makefile | Auto-resolve: keep what CI/the harness actually invokes, delete the other framing |
| Behavior/architecture claim | Usually — one grep/read of the real code path | Auto-resolve if the code settles it; otherwise ask |
| Policy/branch-protection claim | Not via grep — needs an API call (`gh api ...`) | Surface both, name the deterministic tie-breaker, verify or ask — never guess |

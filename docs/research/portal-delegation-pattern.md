# The Portal/shunt delegation pattern, and the family it belongs to

Research note on ["Portal by Spotify cut my Claude Code token usage by 90%"][post]
(Dimitri Mazmanov, Spotify Engineering, 2026-09-03) and the surrounding
strategies for cutting agent token spend.

Read alongside the shipped source: the plugin is public at
[`spotify/portal-ai-plugins`][repo], and much of what follows comes from reading
`plugins/shunt/` rather than from the post.

**Bottom line.** The pattern is real, the architecture is the interesting part,
and the headline number survives honest dollar accounting for the case it was
measured on — but it measures one arm of a two-arm system, on four synthetic
scenarios, with a proxy for tokens. The generalizable idea is not "route to a
cheap model"; it is **enforce context discipline in the harness rather than
asking the model to observe it**. That half is portable, cheap, and does not
require a second model at all.

---

## 1. What the pattern actually is

Three layers, hard to soft:

| Layer | Mechanism | Failure mode it covers |
|---|---|---|
| Hooks | `PreToolUse` on `Read` and `Bash` block large full-file reads | Model ignores advisory routing rules |
| Scripts | `bulk-read` / `code-write` wrap one `aika:invoke-chat` call | Model improvises fragile bash pipelines |
| Skills | `SKILL.md` files teach the invocation syntax | Model knows it is blocked but not what to do instead |

The post is explicit that layer 1 exists because layer 3 alone did not work:

> The first version of this was a block of routing rules in CLAUDE.md. It sort
> of worked … But it had problems. The rules were advisory, not enforced.
> Claude could ignore them.

That sentence is the actual finding. Everything else is an instantiation.

The worker side is two declarative "AiKA modes" (name, instructions, model,
temperature, MCP tools) running on ephemeral runtimes — Spotify's framing is
"model routing as a configuration problem, not a systems engineering problem."
Both examples use Gemini 2.5 Flash at `temperature: 0.2`.

### The gate, precisely

`hooks/check-file-size` allows the read when **any** of these hold: `offset` or
`limit` is set (a targeted read), the path is empty or missing, or the file is
`≤ SHUNT_MIN_LINES` (default 350). Otherwise it blocks with a message pointing
at `/bulk-reader`. `hooks/check-bash-read` does the same for bare
`cat|head|tail|less|more`, allowing anything containing a pipe or a redirect.

The 350-line threshold is a **latency** threshold, not a cost one. The post is
clear: each delegation is a 10–30s round trip, "counterproductive for small
ones." On price alone, delegation wins far below 350 lines.

---

## 2. What the 90% number measures

`plugins/shunt/evals/benchmarks.json` is the measurement, and it is worth
quoting its own header:

```json
"description": "Token savings benchmarks — measures Claude context tokens with vs without shunt",
"token_estimate": "chars / 4 (conservative approximation for code)"
```

Three things follow, none of which are hidden — they are simply not in the
headline:

1. **It counts one arm.** "Claude context tokens" excludes every token the
   worker model consumed. The tokens are relocated, not eliminated. The saving
   is real in dollars only because Flash input is ~21× cheaper than an Opus-tier
   cache write — see §3.
2. **It is four scenarios over three fixture files** (`websocket-handler.ts`,
   `user-service.ts`, `order-service.test.ts`), three of them `bulk-read` and
   one `code-write`. The post describes testing "against a Java monorepo"; the
   committed fixtures are TypeScript. Both can be true — the shipped benchmark
   is the smaller, synthetic one.
3. **`chars / 4` is a proxy**, not a tokenizer. It also cannot distinguish a
   cache *write* from a cache *read*, which differ by 12.5× in price. "90% of
   tokens" and "90% of dollars" are not the same claim.

The repo's own README is more conservative than the post's title: "saving
82–94% of tokens."

---

## 3. Honest all-in cost model

Rates used (confirm before reuse): Claude Opus 5 `$5.00`/MTok input, `$25.00`
output; 5-minute cache write `1.25×` = `$6.25`; cache read `0.1×` = `$0.50`.
Gemini 2.5 Flash `$0.30` input, `$2.50` output.

Take a 600-line TypeScript file ≈ 24,000 chars ≈ 6,000 tokens, a 400-token
summary, and a conversation that continues for `T` more turns after the read.

**Direct read** — admitted once at the write rate, then re-billed at the read
rate on every subsequent turn, forever:

```
0.0375 + 0.0030·T   dollars
```

**Delegated read** — Flash input + Flash output + admitting the summary:

```
0.0053 + 0.0002·T   dollars
```

| `T` | Direct | Delegated | Saving |
|---:|---:|---:|---:|
| 0 | $0.0375 | $0.0053 | 86% |
| 10 | $0.0675 | $0.0073 | 89% |
| 30 | $0.1275 | $0.0113 | 91% |

**The 90% claim survives.** For a large file read once in a long session, the
all-in dollar saving lands right where the post says it does. That is a
genuinely strong result and it deserves to be stated plainly.

### Where the post's reasoning is wrong even though its number is right

> re-sending the files on a follow-up is free where it matters, because the
> corpus goes to the worker model and never enters Claude's context.

Free of *context*, not free of *dollars*. Each follow-up is another full
`$0.0053` Flash round trip, whereas a resident file costs `$0` marginal for the
second question — you are already paying its `$0.0030`/turn cache read whether
you ask about it or not. Delegation wins while

```
Q  <  7.1 + 0.53·T
```

for `Q` questions about the same corpus over `T` turns. At `T = 10` that is ~12
questions. Comfortable for normal use, and it inverts exactly where the post
claims the design is strongest: **tight interrogation loops over one corpus are
the worst case for delegation, not the best.** One-shot ephemeral invocations
mean the worker has no cache to amortize against, while Claude does.

Swap the worker and the picture moves: Haiku 4.5 (`$1`/`$5`) gives ~72% at
`T = 0`, not 86%. The saving is a property of the price gap, not the
architecture.

### The cost the benchmark cannot see

The benchmarks measure read-to-answer. Real work is read-to-*edit*, and the post
concedes the worker's summaries carry no reliable line numbers, so Claude
re-reads the section directly before editing. Every delegation that leads to an
edit is paid **twice**. Only reads that terminate in understanding are fully
saved.

---

## 4. Observations from the source

Read from `plugins/shunt/` at `HEAD`. Reported as engineering notes, not as
defects to be fixed by anyone here.

**A hard payload ceiling the post does not mention.** `scripts/lib/aika.sh`
passes the entire corpus through `argv`:

```
Linux) SHUNT_MAX_PAYLOAD_BYTES=120000 ;;
*)     SHUNT_MAX_PAYLOAD_BYTES=400000 ;;
```

because `invoke-chat` input travels on the command line and Linux caps a single
argument at `MAX_ARG_STRLEN` (128 KiB). So the bulk reader tops out around
~30k tokens of corpus on Linux — roughly ten files at the 350-line threshold.
The tool built for "reading five files to answer a question about one method"
cannot be pointed at a genuinely large corpus.

**The gate is a fence, not a wall.** `check-bash-read` matches only
`cat|head|tail|less|more`, skips any command containing `|` or `>`, and takes
the *first* non-flag argument. So `sed -n '1,9999p' big.ts`, `awk`, `nl`,
`python -c`, `rg -A999`, `cat small.ts big.ts`, and `cat big.ts | cat` all pass.
On the `Read` side, any `limit` at all is treated as a targeted read, so
`limit: 999999` passes. The post's framing — "blocked from the expensive model
entirely, not suggested away from it, blocked" — is true of the two paths the
hook knows about. It is a *deterministic* gate, which is the valuable property;
it is not an exhaustive one.

**A targeted `head` is blocked.** The `Read` hook deliberately allows
`offset`/`limit`. The Bash hook strips flags and then judges by the file's
*total* line count, so `head -100 big.ts` — precisely the targeted read the
design intends to allow — is refused. Anthropic's own context-engineering
guidance names `head`/`tail` as the way to work over large data without loading
it, so this is the one place the gate cuts against the grain.

**Deprecated hook schema.** Both hooks emit top-level `{"decision": "block"}`.
Current Claude Code expects
`hookSpecificOutput.permissionDecision: "deny"`; the legacy `approve`/`block`
form still maps through, so this works today, but it is on a deprecated path.
(`{"decision": "allow"}` was never a valid value in either schema — the
allow-path works because an unrecognized decision falls through to the normal
permission flow, which is the intended behavior anyway.)

**Fence-stripping is lossy.** `code-write` runs ````sed '/^```/d'```` over the
worker's output to remove markdown fences. That deletes *every* line beginning
with a fence, so any generated file that legitimately contains one — Markdown,
a docstring with an example block, a template — is silently corrupted. And
because `--target` writes straight to disk and Claude never sees the output,
nothing downstream notices.

**Nothing reviews generated code.** "Claude never sees the generated code" is
the mechanism of the saving and also its risk: the frontier model's judgment is
removed from the loop precisely where a cheap model just wrote a file. The
`code-writer` SKILL.md says to "review the output," but the token saving exists
only if it isn't reviewed in context.

**Timeout discrepancy.** The post says "Portal caps a single invocation at 30
seconds"; the shipped `SHUNT_TIMEOUT_SECONDS` defaults to `180`.

**Things done carefully, worth stealing.** Both scripts fail loudly on a
missing path rather than sending an empty `<file>` block and getting a
confident answer about nothing. `code-write` *requires* `--reference` for the
same reason. `shunt_invoke` treats a response whose `.mode.name` is empty as a
failure and discards the answer, because a stale mode id runs the turn
mode-less and returns a plausible generic answer under the wrong instructions.
These are exactly the failure modes that make cheap-model delegation dangerous,
and they are handled.

---

## 5. The family this belongs to

Delegation-to-a-cheaper-context is one point in a design space with at least
five distinct axes. They are independent and combine.

| Strategy | Mechanism | Representative |
|---|---|---|
| **Model cascade / routing** | Send each query to the cheapest model that can handle it | [FrugalGPT][frugal] (up to 98% cost reduction matching GPT-4 on their benchmarks); [RouteLLM][routellm] (>2× cost reduction, learned router) |
| **Context isolation** | A sub-agent reads in its own window and returns only a summary | Anthropic's [multi-agent research system][multi]; Claude Code's built-in `Explore` subagent |
| **Just-in-time retrieval** | Hold identifiers, load content on demand | [Effective context engineering][ctx] — `glob`/`grep`/`head`, not pre-indexed embeddings |
| **Execution-environment filtering** | Do the reducing in code; only the result enters context | [Code execution with MCP][mcpexec] — 150,000 → 2,000 tokens (98.7%) on their example |
| **Harness enforcement** | Make the discipline non-optional at the tool boundary | shunt's `PreToolUse` hooks |

shunt is a **combination of #1, #2, and #5**. Its distinctive contribution is
#5: the others are all things you ask the model to do.

The motivating premise is well established. Chroma's [Context Rot][rot] study
across 18 models found performance degrading with input length on tasks held
deliberately constant in difficulty; Anthropic frames the same thing as a finite
"attention budget" depleted by every token admitted. So keeping a corpus out of
context is worth something even when it is *free*, which is the strongest
argument for the pattern and the one the token accounting misses entirely.

### What Anthropic's own measurements say about this shape

This matters because it is the same architecture measured with both arms
counted. Anthropic's cost-optimization guidance classes it as the
**orchestrator** shape — a frontier model that plans and delegates bulk work to
cheaper workers — and reports:

> buys something only when there is bulk to hand off — many independent pieces,
> ideally too many for one context window. On work larger than any context
> window it cost 55% less than the frontier model solo at every effort setting
> (3 to 7 points below its best score) … When the work is one dependent chain,
> or fits in a single context, the orchestrator pays for a plan, a handoff, and
> a merge that a single model gets for free — in every such case measured, the
> coordinator's model alone at lower effort came out ahead.

**55%, with 3–7 points of quality given up** — against Spotify's 90% with the
worker's tokens uncounted. Both can be right; they measure different things.
The honest synthesis is that the dollar saving is large, the quality cost is
real and unmeasured by shunt's benchmarks, and the pattern's value is
concentrated in exactly the case the post picked: bulk, independent, read-only.

The same guidance orders the levers, and puts this one **last**:

1. **Prompt caching** — cut agent-loop cost by 2.5–3.7× at 81–90% hit rates.
2. **Input-token hygiene / progressive disclosure** — move reference material
   behind a tool.
3. **Batch** — 50% off every token including cache reads, for unattended work.
4. **Effort** — on coding, `medium` gave up ~2 points for half the cost; run
   everything at `low` and re-run failures at default gave the same pass rate
   for half the cost.
5. **Model selection and multi-model architectures** — last, because each one
   changes what the model can do.

Notably: *"caches are model-scoped, so a cascade forfeits cache reuse across its
models."* A cascade is not additive with the single largest free lever.

### The native equivalent, which costs nothing to try

Claude Code ships the context-isolation half already. The built-in `Explore`
subagent is read-only, runs in its own window, and returns a summary. Since
v2.1.198 it inherits the main model — but a user or project subagent named
`Explore` overrides the built-in and keeps its own `model` field:

```markdown
---
name: Explore
description: Fast read-only codebase search.
tools: Read, Grep, Glob
model: haiku
---
```

`CLAUDE_CODE_SUBAGENT_MODEL` forces a model onto every subagent. That is
"delegate reading to a cheap model in a separate context" with no plugin, no
second vendor, no network round trip, and no ARG_MAX ceiling. **Anyone
evaluating the Portal pattern should price this first** — it is the closest
available baseline, and the post does not compare against it.

What Portal adds over it is genuinely different and shouldn't be dismissed:
a *different vendor's* model (a real price floor Haiku doesn't reach),
central shareable mode definitions, and enforcement that survives the model
deciding not to delegate.

---

## 6. What is worth carrying into this repo

- **Enforcement over instruction is the transferable finding.** A `PreToolUse`
  hook is a deterministic gate; a paragraph in `CLAUDE.md` is a suggestion that
  degrades under context pressure. This repo already leans on machine-enforced
  checks (`evals/cheap/`) over trust for its safety-critical path; the hook is
  the same argument applied to context.
- **Layer so it degrades gracefully.** shunt's stated property — "even if
  Claude doesn't read the skill description, the hook still blocks the expensive
  read" — is good design worth naming.
- **Measure both arms, or say which one you measured.** shunt's
  `benchmarks.json` is honest in its own header and the README's 82–94% is
  narrower than the title. The gap between the two is the whole lesson about
  reporting agent-cost numbers.
- **Fail loudly on delegated work.** The empty-path guard, the required
  `--reference`, and the `.mode.name` check are the three things that stop a
  cheap worker from returning confident nonsense.
- **Price the free levers first.** Caching, input hygiene, and effort are all
  ahead of multi-model routing, and none of them costs a point of accuracy.

## Open questions

- What is the accuracy cost of `bulk-read` on real repository questions? Nobody
  has published it, shunt's benchmarks don't measure it, and Anthropic's
  orchestrator numbers (3–7 points) suggest it is not zero.
- How often does a delegated read lead to an edit, forcing the double payment
  of §3? That ratio decides whether the real-world saving is nearer 90% or 45%.
- Does the `Explore`-with-`model: haiku` baseline capture most of the win at
  none of the operational cost?

---

## Sources

- [Portal by Spotify cut my Claude Code token usage by 90%][post] — Dimitri Mazmanov, Spotify Engineering, 2026-09-03
- [`spotify/portal-ai-plugins`][repo] — the shipped `shunt` plugin: hooks, scripts, skills, `evals/benchmarks.json`
- [Effective context engineering for AI agents][ctx] — Anthropic, 2025-09-29
- [Code execution with MCP][mcpexec] — Anthropic, 2025-11-04
- [How we built our multi-agent research system][multi] — Anthropic, 2025-06-13
- [Context Rot: How Increasing Input Tokens Impacts LLM Performance][rot] — Hong, Troynikov & Huber, Chroma, 2025-07-14
- [FrugalGPT][frugal] — Chen, Zaharia & Zou, Stanford, arXiv:2305.05176
- [RouteLLM][routellm] — arXiv:2406.18665
- [Claude Code hooks reference][hooks] and [subagents][subagents] — hook schema, built-in `Explore`, `CLAUDE_CODE_SUBAGENT_MODEL`
- [Gemini API pricing][gemini] — Gemini 2.5 Flash rates
- Claude model and prompt-caching rates: the bundled `claude-api` skill's pricing and `shared/prompt-caching.md` / `shared/cost-optimization.md` references

[post]: https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90
[repo]: https://github.com/spotify/portal-ai-plugins
[ctx]: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
[mcpexec]: https://www.anthropic.com/engineering/code-execution-with-mcp
[multi]: https://www.anthropic.com/engineering/multi-agent-research-system
[rot]: https://research.trychroma.com/context-rot
[frugal]: https://arxiv.org/abs/2305.05176
[routellm]: https://arxiv.org/abs/2406.18665
[hooks]: https://docs.claude.com/en/docs/claude-code/hooks
[subagents]: https://docs.claude.com/en/docs/claude-code/sub-agents
[gemini]: https://ai.google.dev/gemini-api/docs/pricing

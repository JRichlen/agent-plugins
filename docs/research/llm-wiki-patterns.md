# LLM-generated wikis, repo maps, and everything between grep and a graph

**Status:** research note. Companion to [`harness-knowledge-graph.md`](harness-knowledge-graph.md); placement analysis, not a roadmap item.
**Question asked:** what does the LLM-generated-wiki pattern family look like as of late 2026,
and does any of it change that note's verdict — specifically, does anything out there
close `fleet-playbook-curator`'s named gap: a relationship claim that is simultaneously
**cited, diffable, and machine-checked**?
**How it was produced:** read the vendor docs and product surfaces for DeepWiki
(Cognition), Google Code Wiki, Devin, Cursor, Sourcegraph, Anthropic, aider,
`llms.txt` and `AGENTS.md`; then — because the interesting question is not what
they claim but what they do — **fetched five live DeepWiki pages and diffed their
indexed commit against the repo's live `HEAD`**, and **verified one DeepWiki page's
architecture table line-by-line against the exact source blob it cites**. Sources and
dates at the bottom. Claims are tagged VERIFIED (I read the artifact) or CLAIMED
(I am repeating a vendor).

---

## The verdict

> **No. It sharpens the reason, and the sharpening is worth more than the answer.**
> The LLM-generated wiki is now a real, shipped, leader-adopted pattern — Cognition
> since May 2025, Google since November 2025 — and it has independently converged on
> two of `fleet-playbook-curator`'s three disciplines. DeepWiki cites every claim to
> `repo@sha:path:lines` and stamps every page with the commit it was generated from.
> That retires any lingering "per-claim citation is exotic" objection: the flagship
> product in this category does it.
>
> What none of them has is the third discipline. **Not one shipped tool in this family
> machine-checks a generated claim against the source it cites** — and DeepWiki proves
> why that gap is not cosmetic. On the `Aider-AI/aider` repository-mapping page, pinned
> to commit `5dc9490b` — which is *still* that repo's `HEAD` today, so the page is as
> fresh as a page can be — **three of the five rows in its architecture table are wrong,
> including one naming a function `rank_tags()` that does not exist anywhere in the
> file.** Every citation is traceable. The traceability is not the problem.
>
> That is the gap `validate-citations.sh` names in its own comments — traceability is
> "necessary but not sufficient," and semantic support is explicitly out of scope
> (`validate-citations.sh:38-41`) — reproduced at industrial scale by the best-funded
> team in the category. PR #134's verdict
> stands, and its second bullet — "for an edge, the evidence is the **join**, and
> nothing deterministic checks the join" — is now backed by a measured external failure
> rather than an argument.
>
> The one genuinely new finding is **where** the field puts machine-checking when it
> wants it: never on prose. SCIP/precise code navigation, aider's repo map, and
> `graphify`'s `EXTRACTED` edges are all trusted because a parser *derived* them, not
> because a checker *validated* them. Rust doctests are trusted because they *execute*.
> The shipped answer to "how do you machine-check a claim about code" is: don't write
> a claim, emit a derivation or an assertion. **That is a design constraint on any
> future fleet-playbook edge, and it points away from "add an edge field" toward
> "add a re-derivable predicate."**

---

## Part 1 — LLM-generated wiki as codebase comprehension

### DeepWiki (Cognition) — the reference implementation

**Who ships it.** Cognition, the Devin company. Launched publicly **2025-05-05**
(VERIFIED: Cognition's own announcement post). Extracted from the paid Devin Wiki /
Devin Search features into a free standalone product at `deepwiki.com`.

**Adoption, with dates.** "Over 50,000 top public GitHub repos" indexed at launch,
2025-05-05 (CLAIMED — vendor's own number, no methodology). A free no-auth MCP server
at `mcp.deepwiki.com` exposing `read_wiki_structure`, `read_wiki_contents`,
`ask_question` (VERIFIED against Devin's docs, read 2026-09-14). Private-repo wikis are
a per-org Devin feature with three billed effort levels — low (free), medium
(~5–10 ACUs), high (~20–40 ACUs) — and enterprise orgs are pinned to low
(VERIFIED: docs.devin.ai/work-with-devin/deepwiki, read 2026-09-14). The secondary
literature treats it as the category-defining product; I found no independent
adoption census and am not going to manufacture one.

**Citation discipline — better than expected.** VERIFIED by reading the page payload
for `deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system`:

- Every inline citation renders as `[path/to/file.py:42-88]` and resolves to
  `https://github.com/Aider-AI/aider/blob/5dc9490b/aider/repomap.py`. That is
  **`repo@sha:path`, plus a line range** — a strictly finer-grained citation than the
  fleet playbook's own contract requires.
- Each page carries a `metadata` block: `repo_index_id:
  "v1.9.9.5/PUBLIC/Aider-AI/aider/5dc9490b"`, `commit_hash: "5dc9490b"`,
  `generated_at: "2026-05-23T22:30:36"`. The index identity includes the *generator
  version* as well as the commit — so a wiki is versioned on both the code and the
  thing that read it.
- The UI surfaces it honestly: `Last indexed: 23 May 2026 (5dc949)`, hyperlinked to the
  commit. That is exactly the freshness banner `fleet-playbook-curator` requires, and
  it is a real one, not a decorative one.

**Staleness — measured, not asked.** DeepWiki regenerates on demand, not on commit;
there is a refresh control in the UI and no documented automatic cadence. To find out
what that means in practice I fetched the wiki metadata for five repositories and
compared the indexed commit to the live `HEAD` via `git ls-remote`, all on
**2026-09-14** (VERIFIED, first-hand):

| Repository | Indexed commit | `generated_at` | Live `HEAD` (2026-09-14) | Lag |
|---|---|---|---|---|
| `microsoft/vscode` | `40064031` | 2026-09-08 | `b376c21d` | behind, ~6 days |
| `openai/codex` | `a97cf1b7` | 2026-09-04 | `b9bfc0af` | behind, ~10 days |
| `langchain-ai/langchain` | `339eaa6f` | 2026-08-22 | `41d35728` | behind, ~23 days |
| `anthropics/claude-code` | `99238193` | 2026-08-13 | `f4ceeeca` | behind, ~32 days |
| `Aider-AI/aider` | `5dc9490b` | 2026-05-23 | `5dc9490b` | **none — repo has not moved** |

Every actively-developed repository's public wiki is behind `HEAD`, by between six days
and a month. **This is not a criticism of DeepWiki** — the page tells you the commit it
describes, which is more than most documentation does, and a reader who follows the
citation lands on the code as it was, not as it is. It is the answer to "can a page
silently rot while the code moves": no, not *silently* — the stamp moves with the page,
so a stale page is legible as stale. What the stamp cannot tell you is **which claims on
the page the intervening 32 days invalidated.** That is the same distinction
`fleet-playbook-curator` draws between its two clocks, and DeepWiki has the first clock
only.

**Does anything machine-check a claim? No — and here is the proof.**

The `Aider-AI/aider` case is the best possible case for a generated wiki: the page is
pinned to `5dc9490b`, and `5dc9490b` is *still* the repo's `HEAD` (VERIFIED —
`git ls-remote` returns `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; the commit is a
merge dated 2026-05-22, the page was generated 2026-05-23). There is zero drift. I
fetched `raw.githubusercontent.com/Aider-AI/aider/5dc9490b/aider/repomap.py` — the exact
blob the page cites — and checked its "Core Components" table row by row:

| DeepWiki says | Actually at `5dc9490b` | |
|---|---|---|
| `RepoMap` — `repomap.py 42-88` | `class RepoMap:` at 42, next `def` at 89 | correct |
| `get_repo_map()` — `103-167` | `def get_repo_map(` at 103, `return repo_content` at 167 | correct |
| `get_ranked_tags_map()` — `365-485` | line 365 is `def get_ranked_tags(`; `get_ranked_tags_map` is at **576** | **wrong** |
| `rank_tags()` — `487-577` | **no symbol `rank_tags` exists in the file**; 487 is `mul = 1.0` | **fabricated** |
| `to_tree()` — `579-699` | `def to_tree(` is at **748**; 579 is a parameter line | **wrong** |

Three of five rows wrong, one of them naming a function that does not exist. Every one
of those rows carries a valid, resolvable, commit-pinned citation to a file that was
genuinely read.

The honest counterweight, because a demonstration with no misses is a sales pitch: the
*inline* citations further down the same page largely check out — `CACHE_VERSION` at
35-37 (correct), `TAGS_CACHE_DIR` at 43 (correct), `tags_cache_error` at 177-215
(correct), `load_tags_cache` at 217-222 (correct), `get_tags_raw` language detection at
280-282 (correct). The failure is concentrated in the **synthesized overview table** —
the artifact a reader is most likely to trust at a glance and quote onward, and the one
furthest from any single file. That is not a coincidence, and it is the same place a
fleet playbook's risk lives: the cross-cutting summary, not the single-file fact.

### Google Code Wiki — the strongest freshness claim in the category

**Who ships it.** Google. Launched in **public preview 2025-11-13** at `codewiki.google`
(VERIFIED: Google Developers Blog announcement). Gemini-generated wikis for any public
GitHub repo, with generated architecture/class/sequence diagrams and a chat surface.

**The freshness claim** (CLAIMED — this is Google's marketing copy, read from the live
landing page on 2026-09-14, and I could not verify it):

> "Every time a pull request is merged, the relevant documentation is automatically
> updated." … "Gemini-generated documentation, always up-to-date." … "No more stale
> docs. Ever."

The announcement post's phrasing is that Code Wiki "scans the full codebase and
regenerates the documentation after each change." If that holds, Code Wiki has the
strongest staleness story in this family by a wide margin — regeneration is event-driven
on merge rather than on-demand, which is the difference between DeepWiki's honest stamp
and no staleness at all.

**Status and adoption.** Still public preview as of 2026-09-14, ten months after launch;
the private-repo path is still "Coming Soon" behind a notify-me form (VERIFIED — read
the live landing page). No adoption numbers published. **This is a serious gap in the
evidence:** the tool with the best freshness claim in the category has shipped no
private-repo support and no usage data in ten months, and the claim is untested by me.

**Citations.** The landing page promises "Linked back to your code — instantly jump from
an architectural overview to the exact service, or from a function's description to its
definition." That is link-to-definition, which is weaker than DeepWiki's
commit-pinned-with-line-range, but I could not confirm the granularity — see
"could not establish."

### DeepWiki-Open / Grok-Wiki — the OSS tier

`AsyncFuncAI/deepwiki-open`, MIT, created 2025-04-30, **17,877 stars** (VERIFIED, read
2026-09-14). An explicit reimplementation: analyze structure → generate docs → generate
diagrams → organize into a wiki. Real adoption for an OSS project; the README documents
no citation format, no per-page provenance, and no staleness mechanism at all. It
reproduces the generation half of the pattern and none of the provenance half. By this
repo's evidence bar it is a popular tool, not an argument.

### Mutable.ai Auto Wiki — the precursor, and a caution

Auto Wiki (YC, Show HN 2024-01; v2 with diagrams 2024-04) was doing this a year before
DeepWiki, with the same headline feature: "citations system links citations to code with
clickable references to each line of code." The pattern is older than DeepWiki and the
citation idea was there from the start. Mutable.ai has since gone quiet as an
independent product. Worth naming so nobody presents commit-pinned citation as a 2026
innovation; not worth leaning on.

---

## Part 2 — Everything between flat grep and a knowledge graph

### aider's repo map — the oldest and most-copied structure

**What it is** (VERIFIED — I read `aider/repomap.py` at `5dc9490b`, and aider's own
2023-10-22 post): tree-sitter parses every file using per-language `tags.scm` queries
into `Tag(rel_fname, fname, line, name, kind)` where `kind` is `"def"` or `"ref"`.
Definitions and references across files become a directed graph; NetworkX PageRank ranks
it, **personalized** toward files already in the chat and identifiers the user mentioned
(weight `100/len(fnames)`); the top-ranked tags are rendered into a token-budgeted tree
(`--map-tokens`, default 1k). ~40–130 languages depending on which tree-sitter pack is
installed.

**Freshness.** A `diskcache` keyed on absolute path, whose value is `{"mtime", "data"}`
and which is invalidated when the file's mtime moves; a `CACHE_VERSION` constant is bumped
whenever the extraction logic changes, invalidating everything. This is a genuinely good
freshness design and it is worth naming why: **the cache key is the thing that changes**
(mtime), and the *generator version* is part of the invalidation identity — the same
two-part identity DeepWiki encodes in `repo_index_id`. `fleet-playbook-curator`'s
`head_sha` stamp is the same idea; nothing in the plugin currently invalidates on
*curator* version.

**Citation discipline.** None, and it does not need any: the repo map *is* the source
lines. It shows `class Coder:` and `def run(self, ...):` verbatim. There is no generated
prose to be wrong. Adoption: aider is the canonical implementation and the pattern has
been reimplemented widely; it is also, notably, the shape DeepWiki chose to write a wiki
page *about*.

### Tree-sitter / LSP symbol indexes — SCIP, and the one thing here that is checked

Sourcegraph's **Precise Code Navigation** is opt-in and built on **SCIP**, an open
language-agnostic code-indexing protocol, with generally-available indexers for Go,
TS/JS, C/C++/CUDA, Java/Kotlin/Scala, Rust (via rust-analyzer), Python, Ruby, and
C#/VB (VERIFIED: Sourcegraph docs, read 2026-09-14). Sourcegraph's own recommendation is
to run the indexer **in CI**, reusing the existing build configuration — "more reliable,
repeatable precise code navigation" — with search-based navigation as the fallback when
no index exists.

This is the only thing in this survey whose claims are trustworthy by construction, and
the reason is worth stating exactly: **a SCIP index is not a claim about the code, it is
a projection of the compiler's own resolution of the code.** It is right for the same
reason the type checker is right. It is also strictly limited to what a compiler knows —
definitions, references, implementations — which is precisely the class of edge a fleet
playbook does *not* need, because it is greppable in one repo.

Adoption: enterprise-plan Sourcegraph feature, opt-in, requiring per-repo index uploads.
Real but narrow.

### Code embeddings and semantic search — the pattern in visible retreat

This one has a direction, and the direction is *away*:

- **Sourcegraph** replaced embeddings for Cody's context retrieval with native
  Sourcegraph search, citing the complexity of creating and maintaining embeddings past
  ~100k repositories (their blog, 2024-02-15).
- **Anthropic**, 2025-09-29, in *Building agents with the Claude Agent SDK* (VERIFIED,
  primary): *"Semantic search is usually faster than agentic search, but less accurate,
  more difficult to maintain, and less transparent. … we suggest starting with agentic
  search, and only adding semantic search if you need faster results or more
  variations."* Claude Code does not pre-index; it uses Glob/Grep/Read on demand.
- **Cursor** — VERIFIED and worth stating carefully. `docs.cursor.com/en/context/codebase-indexing`
  now **308-redirects** to `cursor.com/docs`; the live page at that path is titled
  **Search** and describes "Instant Grep, a custom search engine that outperforms
  `ripgrep` on large codebases" plus an Explore subagent, with **no mention of
  embeddings or a codebase index**. The `cursor.com/docs` sitemap contains no
  indexing/embedding page (read 2026-09-14). A retired doc is strong evidence the
  documented story changed; it is not proof the feature was removed, and I did not
  verify the product behaviour.

**For this note's purposes the retreat is the finding.** Embeddings were the industry's
main answer to "structure between grep and a graph," and two leaders plus the harness
this marketplace targets have published reasons for not using them. Semantic search also
fails the question this note is asking on its own terms: a nearest-neighbour hit is not
a citation, is not diffable, and cannot be checked.

### `llms.txt` — a spec with a format, not an adoption story

Jeremy Howard's proposal, **published 2024-09-03** (VERIFIED, read the spec): a root
`/llms.txt` in Markdown — H1 project name, a blockquote summary, optional prose, then
H2-delimited lists of `[name](url): notes`, plus a convention that any page be available
at the same URL with `.md` appended. Deliberately parseable by classical tooling.

Adoption is real in one direction and absent in the other. **Publishing** it is common
in developer-docs platforms — `docs.devin.ai/llms.txt` exists and its own pages tell a
fetching agent to read it first (VERIFIED, I fetched it and used it to navigate).
**Consuming** it is the problem: as of June 2026 Google's John Mueller publicly
characterised `llms.txt` as speculative, compared it to the keywords meta tag, and noted
that server logs show AI bots do not request the file; Google Search ignores it entirely.
An SE Ranking analysis of 300,000 domains (November 2025) found ~10% adoption and no
correlation with AI citation. (Both secondary — I could not reach Google's own
statement, only reporting of it.)

Freshness story: none. Citation discipline: it is a link list; the links are the
citations, and nothing checks that a linked page still says what the annotation claims.
By this repo's bar, `llms.txt` is a **format worth copying and an adoption claim worth
discounting.**

### `AGENTS.md` / `CLAUDE.md` — the hand-maintained index, and the real winner on adoption

`agents.md` reports **"over 60k open-source projects"** using the format, and states the
spec is now stewarded by the **Agentic AI Foundation under the Linux Foundation**
(VERIFIED — read the live site 2026-09-14; the 60k figure is the site's own, undated,
and I could not verify it). The compatibility list spans Codex, Jules, Factory, Aider,
goose, opencode, Zed, Warp, VS Code, Devin, Junie, Amp, Cursor, RooCode, Gemini CLI,
Copilot's coding agent, Windsurf, Augment and more. Resolution is nearest-file-wins up
the directory tree; OpenAI's own monorepo carries 88 of them.

That is, by a distance, the highest-adoption pattern in this entire survey — and it is
the *least* structured one. No schema, no required fields, no citations, no freshness
mechanism, no checker. It is a hand-written README for machines, and the field chose it
over every index in this note.

There is a lesson in that for this marketplace, and it is not a comfortable one: the
winning artifact is the one a human maintains by hand and an agent reads verbatim.
`docs-hygiene` exists precisely because that artifact rots and nothing tells you. Its
thesis is *more* load-bearing after this survey, not less.

### `graphify` — the closest thing to the shape the gap wants, and the weakest evidence

`Graphify-Labs/graphify` (Apache-2.0, created 2026-04-03): a `/graphify` skill for Claude
Code, Cursor, Codex, Gemini CLI and ~20 other harnesses that builds a queryable knowledge
graph from a project. Mechanism, from the README (VERIFIED as *read*, not as *run*):

- Code edges (`calls` / `imports` / `inherits` / `mixes_in`) come from **local
  tree-sitter AST parsing, no LLM**. Docs/PDFs/media get a separate semantic pass.
- **"Every edge is explained."** Each edge carries a tag: `EXTRACTED` (explicit in the
  source) or `INFERRED` (resolved by graphify). The CLI prints it:
  `--> Dependant [uses] [INFERRED]`, `--> .get() [method] [EXTRACTED]`.
- Output is three files including a `graph.json` — a diffable artifact.
- `graphify hook install` wires a **post-commit git hook**, so the graph regenerates as
  the code moves.
- Explicitly **not** a vector index: "No embeddings, no vector store: a real graph you
  traverse."

On paper this is cited (per-edge source + line), diffable (`graph.json`), and freshness-
hooked (post-commit). And `EXTRACTED` vs `INFERRED` is the best piece of *vocabulary*
found in this entire survey — it is `harness-knowledge-graph.md`'s "declared ≠ populated
≠ fresh" applied at the edge, by a shipped tool.

But it does not close the gap, for the reason that makes this whole note cohere:
**`EXTRACTED` edges are not checked, they are derived** — same category as SCIP, right
by construction, and confined to what a parser can see. **`INFERRED` edges are not
checked either; they are labelled.** The tag is an honest confidence marker, not a
verifier. Nothing re-derives an `INFERRED` edge and fails a build when it stops holding.

And the adoption evidence does not survive this repo's bar. The repo reports **107,831
stars** five months after creation, which is an implausible organic trajectory for a
developer tool, sits alongside a pre-launch commercial platform, and is a vanity metric
regardless. Its published benchmark table (LOCOMO recall@10 0.497 vs mem0 0.048) is a
vendor benchmark on its own harness with no independent replication. **Treat graphify as
a source of vocabulary and one good mechanism, not as evidence that the pattern works.**

### The outlier worth naming: executable claims

The only documentation claims in wide production use that are genuinely machine-checked
are the ones that are **executable**. Rust's doctests are the clean instance: `rustdoc`
extracts the code block from a doc comment, compiles and runs it, and the doc fails the
test suite if the example stops working (VERIFIED — the rustdoc book: *"This makes sure
that examples within your documentation are up to date and working"*; a doctest passes
if it compiles and runs without panicking, and `assert_eq!` turns a documented claim into
a failing test when the behaviour changes). Go's `Example` functions and Python's
`doctest` are the same move.

It is a boring, decades-old pattern and it is the *only* thing in this survey that
satisfies all three of cited, diffable, and machine-checked. It buys that by refusing to
be prose.

---

## Part 3 — The decisive question

**Does anything close the `fleet-playbook-curator` gap?** No. Every candidate lands in
one of three buckets, and none is in the fourth:

| | Cited | Diffable | Machine-checked | |
|---|---|---|---|---|
| **Generated prose** — DeepWiki, Code Wiki, DeepWiki-Open, Auto Wiki | yes (DeepWiki: `repo@sha:path:lines`) | page-level only | **no** | the gap, at scale |
| **Derived indexes** — SCIP, aider repo map, graphify `EXTRACTED` | n/a — the index *is* the source | yes | vacuously — derivation *is* the check | right by construction, limited to what a parser sees |
| **Hand-maintained** — `AGENTS.md`, `llms.txt` | no | yes (it's a file in git) | **no** | highest adoption, least structure |
| **Executable claims** — doctests | n/a | yes | **yes** | the only full house; not prose |

Three things follow, and the third is the one that matters here.

**1. The evidence-quality objection against this pattern family is dead; the domain-fit
objection is untouched.** `harness-knowledge-graph.md` already retired the
"one academic paper" rejection for knowledge graphs on Harness's production deployment.
The same retirement applies to generated wikis: Cognition and Google both ship one, with
dates. But nothing in Part 1 or Part 2 touches PR #134's load-bearing reason — that a
repo fleet already has an authoritative query surface and no canonical-identity problem.
DeepWiki and Code Wiki are *comprehension* layers over code a human cannot read fast
enough. They are not resolving identity across heterogeneous systems. Verdict unchanged.

**2. The gap is confirmed externally, at the best-resourced instance of the pattern.**
`validate-citations.sh` says of itself: *"Semantic support of the claim by the file is
the behavioral/verifier layer's job, not this deterministic gate."* DeepWiki is that
sentence with a hundred million dollars behind it. Its citations are finer-grained than
ours — line ranges, not just paths — its provenance stamp is real, its index identity
includes the generator version, and on a page with **zero** drift it still asserts a
function that does not exist. The fleet-playbook gap is not a local shortcoming to be
embarrassed about; it is the unsolved problem in the category. That is worth recording
plainly, because it also means **no vendor is about to solve it for us.**

**3. The sharper reason — and the actual design constraint.** The reason nobody checks
generated prose is not that it is hard. It is that **a prose claim has no failure
condition.** "Service A authenticates to B via OIDC" cannot be red or green; at best a
judge scores it, and `eval-ladder` already knows what an unvalidated judge is worth.
Every mechanism in this survey that *is* trustworthy got there by giving the claim a
failure condition — a parser that either resolves the symbol or does not, a doctest that
either compiles or does not, a `head_sha` that either matches or does not.

So the constraint on any future fleet-playbook edge is not "model the relationship." It is:

> **An edge is only worth adding if it comes with a command that re-derives it and a
> comparison that can go red.** If the edge cannot be re-derived deterministically from
> the repos, it is prose with a citation on it — which is what the playbook already
> produces, and what DeepWiki already proves is insufficient.

That test is sharper than the three candidate edges in `harness-knowledge-graph.md`, and
it disqualifies them unevenly, which is useful:

- `repo --deploys-via--> workflow` — **passes.** Parse `.github/workflows/*.yml`; the
  edge is present or absent; a diff over the derived set goes red on its own, independent
  of `head_sha`.
- `repo --depends-on--> repo` — **passes.** Manifest/lockfile references are
  deterministic to extract and to diff.
- `repo --authenticates-as--> identity` — **fails as stated.** An OIDC subject appearing
  in a workflow file is `EXTRACTED`; "this repo authenticates as that identity" is
  `INFERRED`, and nothing in the fleet can re-derive it without touching the identity
  provider. It is exactly the class of claim that looks checkable and is not.

That distinction — which of your own candidate edges can go red — is the thing this
research adds, and it did not require a new plugin to find.

---

## Where it lands, ranked

### 1. `fleet-playbook-curator` — the gap is confirmed and the fix is now constrained

Two things to record, neither of which is a build instruction:

**(a) Borrow two mechanisms that cost almost nothing.** DeepWiki's `repo_index_id`
(`v<generator-version>/<scope>/<repo>/<sha>`) makes the *curator's* version part of the
freshness identity, not just the fleet's. Today a playbook curated by an older prompt
against an unchanged fleet is indistinguishable from a current one — the same blind spot
aider's `CACHE_VERSION` bump exists to close. And DeepWiki cites **line ranges**, not
just paths; `validate-citations.sh` could check a line range is in-bounds for the
gathered blob as cheaply as it checks path membership today. Both are `docs-hygiene`-
shaped, deterministic, and inside the existing gate's remit.

**(b) Adopt `EXTRACTED` / `INFERRED` as claim vocabulary before adopting any edge.**
graphify's tag is the missing middle term between "cited" and "supported." A playbook
claim re-derivable from a gathered file is `EXTRACTED`; a claim synthesised across two
files is `INFERRED`. The plugin's citation ledger has no field for this distinction, and
the distinction is exactly where its known failure lives. **Not a recommendation to build
— a recommendation that this vocabulary exist before `grill-me` sees an edge proposal.**

**(c) The re-derivability test above should be the entry condition for any edge**, and
it should be applied before `eval-ladder`, not after: an edge that cannot go red has
nothing for a ladder to catch.

### 2. `verify-before-claim` — the best external demonstration this repo has

*"Never assert a fact without naming and running the specific check that would prove it
false."* The DeepWiki `rank_tags()` finding is a complete, reproducible, third-party
instance: a commit-pinned citation, zero drift, a resolvable link, a nonexistent symbol.
The check that would have proven it false is `grep -n "rank_tags" aider/repomap.py`, and
it takes under a second. Every guard rail was in place except the one that runs.

Use it, with the caveat it deserves: this is one page on one repository, found by looking
for exactly this failure. It is an existence proof, not a rate.

### 3. `eval-ladder` — a fourth rung the category does not have

`harness-knowledge-graph.md` imported Harness's ladder and named *declared ≠ populated ≠
fresh*. This note supplies the retrieval-system analogue of rung 0's blind spot:
**cited ≠ supported**. DeepWiki passes traceability validation on every row of that table
and fails support on three. Any ladder for a citation-emitting system needs a rung whose
fixture is a claim with a *perfect* citation and a *false* body — and the discriminating
corpus for it writes itself, since a real one is now documented above.

### 4. `docs-hygiene` — corroboration, and a mild vindication

The highest-adoption pattern in the entire survey (`AGENTS.md`, 60k+ projects, Linux
Foundation stewardship) is a hand-maintained file with no freshness mechanism whatsoever,
and the best-funded automated alternative is 6–32 days behind `HEAD` on every active repo
I measured. Both failure shapes are the ones `docs-hygiene` already names. Nothing here
changes the skill; it strengthens the case for it.

### 5. `context-handoff` — a format worth stealing, an adoption claim worth discounting

`llms.txt`'s structure (H1 name, blockquote summary, H2 link lists with annotations, an
explicit `## Optional` section meaning "skip this if context is short") is a well-designed
pointer-only handoff artifact, and pointer-only handoffs are exactly what
`context-handoff` mandates. Steal the shape. Do not cite it as adopted — the people who
would have to read it have said, on the record, that they do not.

---

## What this research could not establish

- **Whether Google Code Wiki actually regenerates on merge.** This is the strongest
  freshness claim in the category and I could not test it. `codewiki.google` is a
  client-rendered SPA; `curl` returns a 44KB shell with no content and no API surface I
  could find, and the search-index fetch returned only the marketing landing copy. The
  claim is Google's, undated beyond the page I read on 2026-09-14, with no methodology.
  **Testing it is cheap and would sharpen this note considerably** — the same
  indexed-sha-vs-`HEAD` comparison run on DeepWiki would settle it in one pass, if the
  rendered page exposes an indexed commit at all.
- **Code Wiki's citation granularity.** "Jump from a function's description to its
  definition" could mean a `path#L42` link or a commit-pinned range. Unknown, same cause.
- **Whether the DeepWiki error rate is representative.** I checked *one* page on *one*
  repository, chosen because it was the best case (zero drift), and I was looking for
  this failure. Three-of-five is a finding about that table, not a measured rate. A
  defensible rate would need a sample across repositories and page types, and would be
  a genuinely useful piece of work.
- **Whether DeepWiki auto-refreshes under any condition.** The UI exposes a refresh
  control and the payload carries re-index strings; I found no documented cadence and the
  measured lags are consistent with on-demand-only, but I did not find a vendor statement
  either way, and private-repo Devin behaviour may differ from the public site.
- **Whether Cursor removed embeddings or only the documentation of them.** The doc is
  retired and the replacement page describes grep; I did not verify runtime behaviour and
  should not be read as claiming the index is gone.
- **graphify's mechanism as run.** Every claim about `EXTRACTED`/`INFERRED`, the
  post-commit hook and `graph.json` is from its README. I did not install or run it, and
  its adoption evidence (107k stars in five months, self-run benchmarks) does not meet
  this repo's bar.
- **Any independent adoption census for the wiki category.** DeepWiki's "50,000+ repos"
  and `AGENTS.md`'s "60k+ projects" are both self-reported and undated relative to when I
  read them. There is a large secondary literature ranking these tools; none of it cites
  a primary source I could follow, and I have not used it.
- **Google's own wording on `llms.txt`.** I read reporting of John Mueller's statement
  and Google's documentation position, not the statement or the doc. Treat that
  sub-section as secondary throughout.
- **No egress blocks were hit this pass.** `developer.harness.io`, blocked for the
  companion note, was not needed. `api.github.com` is gated for repositories outside
  `jrichlen/agent-plugins` in this session, so commit metadata for `Aider-AI/aider` came
  from `git ls-remote` and `raw.githubusercontent.com` (both reachable) and from a
  search-index fetch of the commit page, rather than the REST API.

---

## Sources

Read 2026-09-14 unless a publication date is given.

**LLM-generated wikis**
- DeepWiki: AI docs for any repo (Cognition, 2025-05-05) — https://cognition.com/blog/deepwiki
- DeepWiki repository wikis (Devin docs) — https://docs.devin.ai/work-with-devin/deepwiki
- DeepWiki MCP (Devin docs) — https://docs.devin.ai/work-with-devin/deepwiki-mcp
- Index a Repository (Devin docs) — https://docs.devin.ai/onboard-devin/index-repo
- DeepWiki page under test, incl. page payload metadata — https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system
- Introducing Code Wiki (Google Developers Blog, 2025-11-13) — https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/
- Code Wiki product surface — https://codewiki.google/
- `AsyncFuncAI/deepwiki-open` (MIT, created 2025-04-30) — https://github.com/AsyncFuncAI/deepwiki-open
- Auto Wiki v2 (Mutable.ai, 2024-04) — https://blog.mutable.ai/p/auto-wiki-v2

**Repo maps, symbol indexes, search**
- Building a better repository map with tree sitter (aider, 2023-10-22) — https://aider.chat/2023/10/22/repomap.html
- `aider/repomap.py` at `5dc9490b` (read directly) — https://raw.githubusercontent.com/Aider-AI/aider/5dc9490b/aider/repomap.py
- Precise Code Navigation / SCIP (Sourcegraph docs) — https://sourcegraph.com/docs/code-search/code-navigation/precise_code_navigation
- How Cody understands your codebase (Sourcegraph, 2024-02-15) — https://sourcegraph.com/blog/how-cody-understands-your-codebase
- Search / Instant Grep (Cursor docs; `…/context/codebase-indexing` 308-redirects here) — https://cursor.com/docs/context/codebase-indexing
- Building agents with the Claude Agent SDK (Anthropic, 2025-09-29) — https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- Effective context engineering for AI agents (Anthropic, 2025-09-29) — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**Hand-maintained indexes**
- The /llms.txt file (Jeremy Howard, 2024-09-03) — https://llmstxt.org/
- `docs.devin.ai/llms.txt` (a live instance, fetched and used) — https://docs.devin.ai/llms.txt
- AGENTS.md — https://agents.md/
- Google Says LLMs.txt Is Purely Speculative… For Now (SEJ, 2026-06-02) — *secondary; reporting of John Mueller's statement, not the statement* — https://www.searchenginejournal.com/google-says-llms-txt-is-purely-speculative-for-now/577576/

**Graphs and executable claims**
- `Graphify-Labs/graphify` (Apache-2.0, created 2026-04-03) — https://github.com/Graphify-Labs/graphify
- Documentation tests (the rustdoc book) — https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html

**In-repo**
- [`harness-knowledge-graph.md`](harness-knowledge-graph.md) — the note this companions
- [`agentic-patterns-corpus.md`](agentic-patterns-corpus.md) — the standing rejections this does not contradict
- `plugins/fleet-playbook-curator/skills/fleet-playbook-curator/` — `SKILL.md`, `scripts/list-fleet-members.sh`, `scripts/diff-fleet.sh`, `scripts/validate-citations.sh`

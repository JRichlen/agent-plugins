# Knowledge-management corpus

**Status:** research corpus + adoption roadmap for this marketplace's knowledge layer —
the citation ledger in `plugins/fleet-playbook-curator`, the staleness rules in
`plugins/docs-hygiene`, and the rung definitions in `plugins/eval-ladder`.
Companion to [`harness-knowledge-graph.md`](harness-knowledge-graph.md) and
[`llm-wiki-patterns.md`](llm-wiki-patterns.md), which asked whether a knowledge graph
and an LLM-generated wiki belong here. This asks the broader question those two raise
and neither answers: **across every field that has ever tried to keep written knowledge
true, what actually works?**

**How it was produced:** a two-tier agent pipeline. Ten scouts swept ten source clusters
— retrieval and indexing, code graphs, context files and conventions, agent memory,
provenance and freshness, developer portals and catalogs, semantic layers and lineage,
enterprise search and MCP, evaluating knowledge systems, and knowledge-management prior
art outside software. Seven deep-dives then re-verified the load-bearing claims against
primary sources, organised by cross-domain convergence rather than by scout, on the
principle that a claim two unrelated fields make independently is worth more than either
field's version of it. Scout claims that failed verification are **corrected in place
below, not silently removed** — the corrections ledger is the most useful thing here.

**Numbers:** 10 scouts → 140 sightings → 140 unique patterns → 7 dives verifying 64 of
them against primary sources → **57 corrections** → 156 recorded could-not-establish
items → 1 roadmap.

The machine-readable twin is
[`knowledge-management-corpus.json`](knowledge-management-corpus.json) — every pattern
with full mechanism text, adoption tier and evidence, novelty against this marketplace,
scout sightings, and sources; plus every dive, every correction, and every gap.

**Provenance discipline.** Claims are tagged VERIFIED (the artifact was read or executed
first-hand), CLAIMED (a vendor is being repeated), or CORRECTED (a scout said otherwise
and was wrong). Dates are as-of 2026-09-14 unless stated. One dive executed rather than
read — it had `rustc`, `go` and `python3` available and ran the mechanisms it describes,
so several entries below carry observed exit codes rather than documentation.

---

## The verdict

> **Nobody machine-checks a knowledge claim. The entire field's answer is to make claims
> that do not need checking** — *derive* them from a parser or a compiler (SCIP, aider's
> repo map, Bazel's query, graphify's `EXTRACTED` edges), *execute* them (doctests), or
> accept them as unchecked and label how they were produced (DataHub's `matchType`,
> OpenMetadata's `source` enum defaulting to `Manual`). Where anyone does attempt a
> semantic check, the measured ceiling is **~77% balanced accuracy on prose** — 0.55
> informedness against a 50% chance baseline — falling to **~61 on the hardest prose
> split** and **~58 on cases where existing detectors disagree**. On code as evidence,
> a prose-trained checker scores **0.17 span-F1**. The gap `fleet-playbook-curator` has
> is not a local shortcoming. It is the unsolved problem in every field that has tried.
>
> Three things follow that this corpus did not expect to find.
>
> **Fail-open is the norm, and nobody says so.** Every expiry and drift mechanism
> examined degrades to green rather than red: `todo-or-die` fails open three separate
> ways (an env var skips everything, a network error is swallowed, no features are on by
> default); mdBook's include preprocessor is silent — not merely non-blocking — on a
> missing *anchor*, which is the actual drift case, and has been for nearly seven years;
> GitHub's CODEOWNERS checking degrades open in the precise case that matters, since a
> skipped invalid line leaves those paths with *no* owner and makes the branch-protection
> requirement vacuous exactly where ownership is broken. The one mechanism that fails
> closed does so by accident of compile order. **A rule that says "the comparison must be
> able to go red" is insufficient. It must also go red when it cannot be made.**
>
> **Citation is not transcription, and this corpus proved it on itself.** Fifty-seven of
> roughly 140 scout claims needed correction — not for missing citations, but for
> misread ones. The cleanest instance is external and exact: the "84% of KM programmes
> fail" statistic traces through three hops of correctly-formed, resolvable citations
> back to a 1997 article that says the failure rate is **one third**, and that the number
> is an estimate from consulting engagements rather than a study. Every footnote in that
> chain was valid. What drifted was what the source was said to say. **Pinning *where* is
> not pinning *what*** — and `repo@sha:path` pins only where.
>
> **This marketplace is further ahead than its own scouts believed, and its best evidence
> is buried.** `plugins/verify-before-claim` ran a negative-control experiment three
> times across six scenarios and got a null every time: the base model, given a gutted
> stub, already produced the behavior the skill exists to require. It ships without a
> calibration case, with the reasoning and verbatim grader quotes recorded — an
> independent, in-house reproduction of the year's most-cited context-file null result,
> on a different task class, reached before the paper it matches was revised. It lives in
> a YAML comment, is referenced by no tier and no doc, and its own pointer to git history
> is dead.

## What it should become

> Not a graph and not a wiki. A **claim ledger where every entry carries the command that
> re-derives it, the span it rests on, and an honest label for which of those it lacks.**
> Three fields, each of which the field has independently invented and none of which any
> shipped system has all three of: a `repo@sha:path` locator (this repo already has it,
> and it is finer-grained than Backstage's or Microsoft's), a **quoted span** proving
> *what* the source says rather than only where to look, and a **derivation tag** —
> `EXTRACTED` when a parser produced it, `INFERRED` when a model synthesised it across
> sources, `MANUAL` when a human asserted it. The tag is not validated and cannot be;
> four separate systems ship one anyway, because an unvalidated label still tells a
> reader which claims to distrust, and that is worth more than a check that scores 0.17.

---

## Adopt now (ranked)

### 1. `quoted-span` — schema + cheap-tier check

Require every ledger claim to carry a verbatim span from the cited blob alongside
`repo@sha:path`. The cheap tier then greps the span out of the gathered file: present, or
the pass fails. Deterministic, offline, no model.

**Why now:** this is the one gate that would have caught an 84%-class error, and the
84% chain is not hypothetical — it is three hops of valid citations ending in a sentence
that says the opposite. Wikipedia already has the clause this repo lacks: a source
"directly supports" material only "if the information is present explicitly in the
source." `validate-citations.sh` today proves a path was read; it cannot prove the path
says what the claim says, and its own comment concedes exactly that
(`validate-citations.sh:38-41`). A quoted span does not close the semantic gap — nothing
does, per the verdict — but it converts the most common real failure, misreading, from
undetectable into a string comparison.

### 2. `derivation-tag` — vocabulary before mechanism

Add `EXTRACTED` / `INFERRED` / `MANUAL` to the claim ledger, defaulting to `MANUAL`.

**Why now:** four independent systems converged on this and none validates it —
OpenMetadata ships a closed `source` enum whose **default is `Manual`**; DataHub ships
`matchType` (EXACT/NORMALIZED/UNRESOLVED) and concedes in its own model comments that the
verdict "is not re-evaluated automatically"; graphify prints `[EXTRACTED]`/`[INFERRED]`
per edge; GitHub publishes a precedence ladder over derivation methods for dependency
data. The convergence is the evidence. It costs one enum and it is the prerequisite for
ever evaluating an edge proposal honestly, because the disqualifying question — can this
be re-derived? — is the same question the tag answers.

### 3. `fail-closed` — audit the tiers for checks that go green when they cannot run

**Why now:** the fail-open finding is the strongest negative result in this corpus and it
generalizes to any gate this repo writes. A check that passes because it could not look
is worse than no check, because it is reported as green. The concrete rule that falls out
of the dive: **only internal-oracle checks belong in a hermetic tier** — a check whose
answer lives inside the repo (does this span exist in this blob? does this path resolve?)
can be honest offline; a check needing an external oracle (is this issue closed? does this
owner still have write access?) cannot, and its green means "either fine, or I couldn't
look." The clock is the single external oracle that escapes, because every machine carries
one.

### 4. `effect-size arm` — one-line change, one pack

Score the existing calibration arm against the **same** rubric as the treatment arm
rather than an inverted one, on a pack already wired, with `repeat` raised from 3.

**Why now:** every control arm in this repo today answers "does this scenario have
discriminating power?" and none answers "how large is the skill's effect?". CTXbench's
entire result is an effect-size question, and this repo cannot currently ask it. The cost
is small and the finding worth paying for is the uncomfortable one — a skill whose delta
is indistinguishable from zero. **Do not run it on `verify-before-claim`:** that pack
already ran six scenarios to a null and bars re-adding a calibration case without arguing
the scenario in writing first.

### 5. `promote the null` — get `verify-before-claim`'s negative result out of a YAML comment

**Why now:** it is the best evidence this repo owns about whether its own skills work, it
is unreachable from any doc or tier, and its pointer to git history resolves to nothing
because the file it references was never committed. `docs/testing.md` already carries a
standing order that the tier inventory stay current; a recorded null about a tier's
discriminating power belongs in the same place.

### 6. `node_id` format-migration guard

**Why now:** GitHub's migration guide states that "The legacy format will be closing down
and replaced with a new format," with no shutdown date. `diff-fleet.sh` joins manifests
across passes on `node_id`. A fleet whose stored manifests straddle that migration sees
every member as `removed` plus `added` instead of `renamed`, and nothing says why. One
recorded format-marker per manifest turns a silent mass-false-positive into a legible
error.

## Adopt later

- **Bi-temporal invalidation for the CONSOLIDATE store.** Zep/Graphiti's four-timestamp
  record — `valid_at`/`invalid_at` for the world, `created_at`/`expired_at` for the system,
  with a contradicted fact marked invalid rather than deleted — is the only shipped
  mechanism structurally incapable of silently serving a fact that stopped being true. It
  is a property of a *row*, not of a graph, so it can be adopted without adopting the
  topology the corpus already rejected.
- **Path-scoped instruction loading.** Four vendors ship it; this repo already computes
  safety globs for the deep-tier gate (`evals.yml:695-696`), so the machinery exists.
- **Symbol-resolution citations** (`repo@sha:path#symbol`) where a resolver exists.
  Strictly stronger than path-existence. Note the limit the scout found: Markdown and
  shell have no resolver, which is most of this repo.
- **A size guard on instruction files.** Windsurf is the only vendor that *enforces* a
  context budget rather than suggesting one (6,000 global / 12,000 per workspace, though
  whether it truncates or merely advises is nowhere stated). `AGENTS.md` here is 186 lines.

## Rejected despite adoption

- **A knowledge graph for a repo fleet.** Upheld, and this corpus adds the cost the
  earlier note never priced: what a graph buys at enterprise scale is identity resolution
  *plus a permission mirror*, and the mirror is where the failures live — Elastic
  publishes its own ACL-propagation bugs in both directions, AWS's documentation has a
  heading named "irreconcilable identities" whose sanctioned remedy is to abandon
  document-level security. A git-native fleet pays none of it, because `gh api` is
  permission-trimmed by construction.
- **`llms.txt` as an adoption story.** Keep the format, discount the claim. Publishing is
  common; consuming is not, and Google's own guidance says such files are unnecessary.
  The one real consumer is an agentic doc-reader, not a crawler.
- **Code embeddings as the default retrieval layer.** Three leaders published reasons for
  retreating. A nearest-neighbour hit is not a citation, is not diffable, and cannot be
  checked — it fails this corpus's question on its own terms.
- **`graphify` as evidence.** Keep the vocabulary, reject the adoption claim. Measured
  2026-09-14: 116,700 stars, 11,395 forks — and **3 subscribers**. Comparable repos sit at
  0.5–1.9% watcher-to-star ratio; graphify sits at 0.0026%, two to three orders of
  magnitude below the lowest control, with the same watcher count as a 522-star project.
  Cite the schema, never the stars.
- **Zettelkasten and networked PKM tools as design input.** The loudest sub-domain in
  modern knowledge management has no controlled evidence of transfer beyond n=1. Recorded
  as evidence-free rather than silently omitted.
- **"84% of KM programmes fail," "70% fail," "50% fail."** The 84% is a misquotation of a
  one-third estimate. The 70% traces to an oral estimate in a 2000 trade-press interview,
  caveated by the person who gave it, and to a 2005 paper that imports it by analogy from
  a Bain article about CRM. The 50% traces to nothing. This repo should cite none of them.

---

## What this research could not establish

156 items are recorded in the JSON twin, per dive and per scout. The ones that would
change a decision here:

- **Any production system that *detects* staleness rather than resolving it on write.**
  Every mechanism found fires only when a contradicting claim happens to arrive. Nothing
  goes looking. This is the single largest hole in the field and it is the hole
  `docs-hygiene` sits in.
- **Any published accuracy figure — TPR, TNR, precision, recall, anything — for the three
  vendor grounding APIs.** All three primary doc pages were read. Google publishes latency
  only; AWS publishes threshold semantics only; Azure publishes feature switches and four
  toy examples. They are exactly the unvalidated rung-3 judge `eval-ladder` forbids, sold
  as infrastructure.
- **Whether the ~77% ceiling still holds.** The leaderboard backing it appears frozen —
  last updated 2025-09-08, no 2026 frontier model among its 39 entries. The number should
  be cited with that caveat or re-measured.
- **Whether the code-evidence finding replicates.** The single benchmark measuring
  claim-checking over code uses synthetic error injection, has an author conflict of
  interest, and has no independent replication. It is the only measurement of the thing
  this repo most needs measured, and it is one paper.
- **Whether the four uncontrolled promptfoo packs lack a control by decision or by
  omission.** No comment in `fleet-playbook-curator`, `graveyard`, `tailscale-wif` or
  `voice` says. `graveyard` is the plugin that deletes repositories.
- **Any base rate for ACL-mirror defects**, which no vendor publishes, and any
  person-month cost for building an ontology, which nobody in any domain publishes.
- **Whether glob-scoped instruction rules actually beat a flat file.** Four vendors
  shipped the same mechanism and none published a number.

One methodological correction applies to this section itself, and it came from a dive
auditing a scout: **a negative claim is still a claim.** Several scout
could-not-establish entries were asserted with the same confidence as positive findings,
and the most falsifiable of them — that no causal study exists behind the FlaggedRevs
vandalism claim — was simply wrong; a CSCW 2022 interrupted-time-series across 17 language
editions exists, and its more interesting result is a *null* on the hypothesis that the
gate reduces bad contributions rather than merely hiding them. Entries in the JSON twin
now record the search that was run, not only the verdict.

**Egress.** 86 blocked-origin notes are recorded. `api.github.com` is scoped to this
repository in this container, so third-party repo facts came from
`raw.githubusercontent.com`, `git ls-remote`, registry APIs and HTML surfaces — each
noted per claim. ACM Digital Library returned 403 throughout, so the Furnas 1987 figures
rest on the abstract. `developer.harness.io` was blocked for the companion note and was
not needed here. No TLS verification was disabled and `HTTPS_PROXY` was not unset.

---

## The corpus — every unique pattern

140 patterns, 10 scouts, sorted by adoption tier then name. Full mechanism text, adoption
evidence, sources and per-pattern sightings are in the JSON twin; the mechanism column
here is truncated to its first sentences.

| Pattern | Who | Adoption | Novel? | Mechanism |
|---|---|---|---|---|
| Agentic search (grep/glob/read loop, no persistent index) | Anthropic Claude Code + Claude Agent SDK; Sourcegraph Amp; | mass | absent | No embedding pipeline, no vector store, no chunking. The model is handed filesystem primitives (glob, ripgrep, read_file, list_dir) and issues its own queries in a loop, narrowing over several turns the way a developer would. |
| AGENTS.md — cross-harness repo instruction file | Originated in OpenAI Codex; co-developed with Amp, Google Jules, Cursor, Factory. | mass | covered | Plain Markdown, no required fields, no schema. Root file plus nested files in subdirectories; resolution rule is 'the closest AGENTS.md to the edited file wins'. |
| Authority control — one authorized access point per entity, with every variant name recorded as a… | Library and information science. | mass | absent | Identity is a first-class record, kept SEPARATE from the records that reference it. |
| Build provenance attestations — binding an artifact to the source and commit it came from | SLSA v1.0 provenance; in-toto attestation framework; Sigstore; npm `--provenance`; | mass | absent | The build platform emits a signed statement describing how an artifact was produced — the build definition, external parameters, and the resolved source repository URI and commit in `resolvedDependencies` — signed via Sigstore… |
| Catalog rot productized as a measured KPI (Correctness = Staleness + Orphan + Duplicate) | ServiceNow CMDB Health dashboard | mass | absent | Three top-level KPIs. Completeness aggregates Required and Recommended field population. |
| CLAUDE.md — hierarchical, concatenating memory with an import graph | Anthropic / Claude Code. GitHub Copilot also reads a root CLAUDE.md as an… | mass | covered | Four scopes loaded in order broadest→narrowest: managed policy (/etc/claude-code/CLAUDE.md or the `claudeMd` key in managed-settings.json, not excludable), user (~/.claude/CLAUDE.md), project (./CLAUDE.md or ./.claude/CLAUDE.md),… |
| CODEOWNERS — the ownership edge that passes all three tests | GitHub (platform-native); consumed as an ownership source by Backstage, Cortex and… | mass | partial | A file at a known path maps path globs to owners. GitHub validates it: invalid lines are skipped and highlighted when viewing the file, unknown users/teams do not get assigned, and owners must have explicit `write` access (teams… |
| Communities of practice — domain, community, practice | Jean Lave and Etienne Wenger, 'Situated Learning: Legitimate Peripheral Participation'… | mass | absent | Three elements must all be present, per the authors' own current statement: THE DOMAIN ('an identity defined by a shared domain of interest. |
| Compatibility-gated schema evolution (the one machine-checked contract in the domain) | Confluent Schema Registry; Apache Avro spec | mass | partial | A subject is 'a named scope for schema evolution' holding an ordered sequence of versions with its own compatibility configuration. |
| Controlled vocabulary with preferred terms, scope notes, and typed relationships (USE/UF, BT/NT/RT) | ANSI/NISO Z39.19-2005 (R2010), 'Guidelines for the Construction, Format, and Management… | mass | absent | A controlled vocabulary is not a word list. Z39.19 specifies four escalating structures — 'lists, synonym rings, taxonomies, and thesauri' — and for the thesaurus level requires, per term: one PREFERRED term; |
| Cursor rules — typed activation modes in .mdc frontmatter | Cursor (Anysphere). `.cursorrules` was the original single-file form; | mass | partial | Each rule is an `.mdc` file (Markdown + YAML frontmatter) under `.cursor/rules/`. Plain `.md` files in that directory are ignored — the frontmatter is what makes a file a rule. |
| Executable documentation / doctest family (examples in docs are compiled and run as tests) | Python stdlib `doctest`; Rust `rustdoc --test` / `cargo test --doc`; | mass | absent | The doc's claim is written AS code with an expected result, and the test runner extracts it, executes it against the real current library, and compares actual output to the output printed in the prose. |
| Folksonomy / collaborative tagging | Term coined by Thomas Vander Wal on the AIfIA/IA Institute list, 24 July 2004 (documented… | mass | absent | Vander Wal's own definition, verbatim: 'Folksonomy is the result of personal free tagging of information and objects (anything with a URL) for one's own retrieval. |
| GitHub Copilot custom instructions — repo-wide file plus per-surface exclusion | GitHub. Honoured across Copilot Chat, code review, the coding agent, and VS Code. | mass | partial | Three layers: `.github/copilot-instructions.md` (repo-wide, applies to every request in repo context); `.github/instructions/NAME.instructions.md` with `applyTo` globs (path-scoped); |
| Host-side dependency-edge diff with a blocking CI gate | GitHub (dependency graph, dependency review API, actions/dependency-review-action) | mass | partial | Three pieces that together close the loop. (1) State: `GET /repos/{owner}/{repo}/dependency-graph/sbom` exports the dependency edges as SPDX JSON with a `relationships` array of {relationshipType, spdxElementId,… |
| Identity by prioritized attribute-matching rules, including relationship-dependent identity | ServiceNow CMDB — Identification and Reconciliation Engine (IRE) | mass | absent | Identity is COMPUTED from a payload rather than asserted. Each CI class has one identifier composed of ordered identifier entries (regular, based on CI attributes; lookup, via related tables; or hybrid), each with a priority; |
| Index-and-embed codebase RAG with Merkle-tree incremental sync | Cursor (default-on for every opened project); Windsurf/Devin Desktop; Continue.dev; | mass | absent | On project open the client builds a Merkle tree over the repo — SHA-256 per file, folder hashes derived from children — then splits changed files into syntactic chunks, embeds them, and stores vectors plus obfuscated metadata in… |
| Live edge queries from a language server (call hierarchy, type hierarchy) | Microsoft / LSP 3.16 (call hierarchy) and 3.17 (type hierarchy); | mass | absent | Rather than persisting a graph, the client asks the server for one hop at a time: `textDocument/prepareCallHierarchy` then `callHierarchy/incomingCalls` / `callHierarchy/outgoingCalls` (3.16.0); |
| Managed remote repository index (zero-config, server-side) | GitHub Copilot (all tiers including free); Azure DevOps; | mass | absent | The index lives with the code host, not the editor, so it is built once per repository and shared across every user and surface — chat, the IDE, the cloud agent — instead of once per developer per machine. |
| MCP resources carry no provenance, no version and no access-control model — freshness is an optional display… | Model Context Protocol specification, revision 2026-07-28 (current) | mass | absent | A Resource is {uri, name, title?, description?, icons?, mimeType?, size?}. There is no author, version, etag, revision, source-system or confidence field. |
| Name-matching pseudo-navigation: tree-sitter symbol extraction without name resolution | GitHub (code navigation on github.com, 24 languages); | mass | absent | 'Code navigation uses the open source tree-sitter library... GitHub has developed a code navigation approach based on the open source tree-sitter library that searches all definitions and references across a repository to find… |
| Per-item ACL on ingested external content, with deny-precedence and a group-mirroring escape hatch (Microsoft… | Microsoft — Copilot connectors (formerly Microsoft Graph connectors), externalItem… | mass | absent | Every externalItem carries three components: acl, properties, content. The acl is 'an array of access control entries representing a Microsoft Entra user or group', plus a third type Everyone for the whole tenant. |
| Permission-trimmed passage retrieval as the grounding API (Microsoft 365 Copilot Retrieval API) | Microsoft — POST /copilot/retrieval on Microsoft Graph v1.0 and beta | mass | absent | 'The API security trims content for the calling user and respects the defined access controls within the tenant.' Request: queryString (<=1500 chars), dataSource in {sharePoint, oneDriveBusiness, externalItem}, optional… |
| README/CONTRIBUTING as agent context, and the redundancy tax of duplicating them | Universal convention; explicitly consumed by Claude Code (documented `@README` import… | mass | partial | Two options: reference the existing file (Claude Code's `@README`, `@package.json` import syntax pulls it into context at launch) or restate its content inside the agent file. |
| Reference-existence gates in the doc build (link rot and broken anchors fail the build) | lychee / lychee-action (511 stars on the action); | mass | partial | The doc toolchain enumerates every link, cross-reference and heading anchor and resolves it; unresolvable targets are reported and, configurably, abort the build. |
| Reference-free RAG metric suite (faithfulness / answer relevance / context relevance) as the de-facto… | Shahul Es, Jithin James, Luis Espinosa-Anke, Steven Schockaert — RAGAS (Exploding… | mass | partial | Faithfulness: prompt an LLM to decompose the answer into atomic statements S, then ask a second prompt whether each statement is supported by the context; score = \|supported\| / \|S\|. |
| Response-level groundedness + relevance scores as a runtime guardrail | AWS — Amazon Bedrock Guardrails, contextual grounding check | mass | absent | Supply `grounding_source` (<=100,000 chars), `query` (<=1,000 chars) and the model response (<=5,000 chars). |
| Review-before-public-display (FlaggedRevs / sighted versions / pending changes) | MediaWiki FlaggedRevs extension (Aaron Schulz and Joerg Baach). | mass | partial | Decouples 'an edit is saved' from 'an edit is shown to the public'. On a protected page, an edit by an unregistered or new account is stored but marked pending; |
| Runtime-observed lineage read out of the engine's own internals | OpenLineage Spark integration; Snowflake ACCESS_HISTORY; Databricks Unity Catalog | mass | partial | Three variants of the same idea — never parse the SQL text, read what the engine actually did. |
| SBOM relationship vocabulary as a standardized, portable edge type | Linux Foundation / SPDX (ISO/IEC 5962 lineage); OWASP CycloneDX | mass | absent | SPDX 2.3 defines a Relationship field, 'SPDXID <relationship> SPDXID \| NONE \| NOASSERTION', over a closed vocabulary of 60+ types — DEPENDS_ON, DEPENDENCY_OF, CONTAINS, CONTAINED_BY, GENERATES, GENERATED_FROM, STATIC_LINK,… |
| schema.org — mass-adopted shared vocabulary with the formal semantics removed | Google, Microsoft, Yahoo, Yandex steering group; | mass | absent | A flat-ish type hierarchy (823 Types, 1529 Properties, 19 Datatypes, 96 Enumerations, 535 Enumeration members as published) embedded in pages as JSON-LD, Microdata or RDFa. |
| SECI / the tacit-to-explicit knowledge conversion spiral | Ikujiro Nonaka, 'A Dynamic Theory of Organizational Knowledge Creation', Organization… | mass | partial | Nonaka's own abstract: 'Its central theme is that organizational knowledge is created through a continuous dialogue between tacit and explicit knowledge. |
| Semantic search exposed as an agent tool, not injected before inference | Cursor; GitHub Copilot / VS Code agent mode; Windsurf-Devin Desktop; | mass | absent | The index is not consulted automatically on every turn. It is one tool among grep, glob, usages and read_file, and the model decides when to call it, what to ask, and whether to follow up — then loops. |
| Server-side compaction as memory: older turns are summarised and then dropped by the API | Anthropic (`compact_20260112`, beta header `compact-2026-01-12`); | mass | partial | Fires when input tokens cross a threshold (default 150,000; configurable to any value >= 50,000). |
| SKILL.md — progressive disclosure as a manifest contract | Anthropic (Claude Code and the broader Agent Skills format); | mass | covered | YAML frontmatter (`name`, `description`, `disable-model-invocation`) plus a Markdown body. Only DESCRIPTIONS are preloaded into context every turn; the body loads on invocation; |
| Symbol-resolution cross-reference checking — a prose reference must resolve to a real item in the compiled… | rustdoc `broken_intra_doc_links` lint; Sphinx nitpicky mode (`-n`) with intersphinx; | mass | partial | Documentation links are written as the symbol itself (`[\`Foo::bar\`]`, `:func:\`pkg.mod.fn\``) rather than as a URL or a path. |
| The 1990s corporate KM wave and its documented failure | Charles E. Lucier and Jan Dyer Torsilieri (both Booz Allen & Hamilton), 'Why Knowledge… | mass | partial | Lucier & Torsilieri's diagnosis, verbatim and in their own order: the less successful programs suffer from four correctable problems — '(1) No specific business objective, but only general aspirations like "share best practices"… |
| The ecosystem standardised on search/fetch TOOLS, not MCP resources — and citation precision bottoms out at a… | OpenAI (deep research remote-MCP contract), with corroborating implementations from… | mass | partial | OpenAI requires a remote MCP server to 'implement two read-only tools: search and fetch'. search takes a query string and returns {results: [...]}, each result requiring id, title, and 'url - canonical URL for citation'. |
| Verbatim server-side thread persistence with no extraction (persistent conversation objects) | OpenAI (Responses API `previous_response_id`, Conversations objects, `store`) | mass | covered | Three options: a Conversations object holding items (messages, tool calls, tool outputs) under a durable id; chaining by `previous_response_id`; or manual history replay. |
| Wikipedia verifiability — burden on the adder, inline citation as the unit, removal as the default remedy | English Wikipedia community. WP:V is one of three core content policies (with WP:NOR and… | mass | partial | Four moves, all verbatim from the current policy (read 2026-09-14). (1) SCOPE IS NARROWED so the rule is affordable: not everything needs a citation, but four categories always do — 'direct quotations, material whose… |
| ACL-at-index-time as an explicit multi-step write protocol (Glean Indexing API) | Glean, for custom/push datasources | growing | absent | A document's permissions object takes allowAnonymousAccess, allowAllDatasourceUsersAccess, allowedUsers[], allowedGroups[]. |
| Append-only decision records — supersede rather than edit, so the record cannot go stale, only get outvoted | MADR (Markdown ADRs, the adr.github.io template family); Nygard-style ADRs; | growing | absent | A decision is written once, numbered, and never rewritten. Status is metadata — 'proposed \| rejected \| accepted \| deprecated \| … \| superseded by ADR-0123'. |
| AST-aware chunking (tree-sitter) instead of fixed-window splits | Cursor; Continue.dev; Applied Compute/turbopuffer; astchunk (CMU + Augment Code) | growing | absent | Parse each source file to an AST and recursively split large nodes / merge sibling nodes under a size budget, so chunk boundaries land on function and class boundaries rather than mid-body. |
| Background consolidation agent with review-before-apply on memory writes | Letta (sleep-time agents in the platform; 'dreaming' in Letta Code) | growing | absent | Setting `enable_sleeptime: true` creates a second agent whose job is to rewrite the primary agent's memory blocks asynchronously from conversation history or data sources, producing 'learned context' that can be shared across… |
| Bi-temporal fact invalidation — a contradicted fact is marked invalid, never deleted | Zep / Graphiti (getzep). Graphiti is the OSS engine under Zep Cloud; | growing | absent | Every fact edge carries four timestamps on two axes. World time: `valid_at` (when the relationship became true) and `invalid_at` (when it stopped being true). |
| Claim-level grounding check as a hosted API (support score + per-claim citation indices) | Google Cloud — `checkGrounding` on Vertex AI / Gemini Enterprise (Discovery Engine) | growing | absent | POST an answer candidate (<=4,096 tokens) plus up to 200 `facts` (<=10k chars each). |
| Code-specialized embedding models with Matryoshka dims + quantization | Voyage AI (voyage-code-3); Cursor (its own trained model); | growing | absent | Embedding models trained specifically on docstring-code and code-code contrastive pairs rather than general text, with Matryoshka learning so the first k dimensions of a 2048-dim vector are themselves a valid k-dim vector, and… |
| CodeQL: a relational database of the code plus a computed data-flow graph, gated in CI | GitHub (CodeQL CLI, code scanning) | growing | absent | Extractors 'extract information from the source code of a software system into a database that can be queried', capturing 'the hierarchical structure of each supported programming language'. |
| Convention-based dataset identity (a naming contract instead of a registry) | OpenLineage (LF AI & Data Graduate project) + Marquez reference implementation | growing | partial | There is no identity service. A dataset is (namespace, name) where the namespace is derived from the data source by published convention — bigquery, s3://{bucket}, postgres://{host}:{port} — and the name is the hierarchical path… |
| Cross-encoder reranking as a distinct second stage | Cohere (rerank-v4.0-pro/fast, v3.5); Voyage AI (rerank-2); | growing | absent | Over-retrieve with the cheap first-stage index, then score each candidate against the query with a small cross-encoder that sees query and document jointly, and keep only the top slice for the context window. |
| Declared build graph as the authoritative edge set, with a content-hashed diff (bazel query + bazel-diff) | Google (Bazel, `bazel query`/`cquery`); Tinder (bazel-diff); same shape in Buck2 | growing | absent | Bazel's query language operates on the loaded target graph: 'Every expression evaluates to a partially-ordered set of targets, or equivalently, a graph (DAG) of targets', including implicit dependencies from private attributes… |
| Delegated search subagent with an isolated context window | Anthropic Claude Agent SDK / Claude Code (subagents by default) | growing | partial | Search is handed to a subagent that runs its own retrieval loop in a separate context window and returns only the distilled excerpts, so the thousands of tokens of false-positive grep hits and half-relevant files never touch the… |
| Derived, read-only, deliberately unvalidated relations ('dangling relations are fine') | Backstage software catalog | growing | absent | `relations` is a read-only root field. Authors never write edges directly; they write scalar spec fields (`spec.owner`, `spec.dependsOn`, `spec.system`, `spec.parent`, `spec.providesApis`) and processors deduce the edge pairs —… |
| Diátaxis — four-mode documentation taxonomy | Daniele Procida (Django core developer; | growing | partial | Split documentation by user need into four irreducible modes — tutorials (learning-oriented), how-to guides (task-oriented), reference (information-oriented), explanation (understanding-oriented) — and never mix two in one… |
| DLS as a per-role query DSL filter, with the analyzer as an attack surface (OpenSearch) | OpenSearch Security plugin | growing | absent | A role carries a dls string — an OpenSearch query-DSL fragment — applied to every read on the matching index_patterns. |
| Dropping vector embeddings for an existing code-search engine | Sourcegraph (Cody: embeddings replaced by the Sourcegraph search platform); | growing | absent | Keep an index, but make it the lexical/structural code-search index the org already runs rather than a vector store. |
| Enterprise knowledge graph over content + people + activity (Glean) | Glean (the enterprise-search vendor; NOT Meta's Glean code-indexer) | growing | absent | 100+ connectors crawl each SaaS app; the 'Knowledge Graph' is built on three declared pillars — Content (documents, messages, tickets), People (unified identity, org relationships, close collaborators), Activity (interactions,… |
| Forgetting that leaves a tombstone: tool-result and thinking-block clearing with a visible placeholder | Anthropic (`clear_tool_uses_20250919`, `clear_thinking_20251015`, beta header… | growing | partial | Server-side, oldest-first eviction of tool *results* (optionally tool inputs) with explicit knobs: `trigger` (default 100,000 input tokens, or a tool-use count), `keep` (default 3 tool-use/result pairs), `clear_at_least` (minimum… |
| FRBR / IFLA LRM — separating Work, Expression, Manifestation, Item | IFLA FRBR Review Group. FRBR (1998), FRAD (2009), FRSAD (2010), consolidated as the IFLA… | growing | absent | One entity-relationship model that distinguishes the abstract intellectual content (Work) from a specific realization of it (Expression: a translation, an edition's text), from a physical/digital embodiment (Manifestation: a… |
| Freshness metadata and ownership expiry as a staleness proxy (last-reviewed date + named owner + reminder) | Google internal g3doc freshness dates (documented in Software Engineering at Google,… | growing | partial | Each document carries structured metadata naming an owner and the date it was last REVIEWED (not last edited). Tooling emails the owner when the interval lapses; renewing the date is itself a reviewed code change. |
| Graph traversal exposed to agents as a two-tool MCP pair (Atlassian Teamwork Graph via Rovo MCP) | Atlassian — Rovo MCP server, tools getTeamworkGraphContext and getTeamworkGraphObject | growing | absent | A common object model normalises Jira work items, Confluence pages, Bitbucket PRs, Loom videos, JSM tickets and third-party objects (Google Drive, Slack, GitHub, Figma) into typed objects with typed relationships; |
| Groundedness detection with span-level reasoning and automatic correction | Microsoft — Azure AI Content Safety, groundedness detection | growing | partial | Two modes: Non-Reasoning (fast binary grounded/ungrounded) and Reasoning ('detailed explanations for detected ungrounded segments'). Tuned by `domain` (MEDICAL \| GENERIC) and `task` (Summarization \| QnA). |
| Hosted remote MCP over a workspace plus its connected sources, with a documented throughput ceiling | Notion — Notion MCP (notion-search, notion-fetch, notion-query-data-sources, plus ~20… | growing | absent | OAuth-authorised remote MCP server. notion-search searches 'across your Notion workspace and connected tools like Slack, Google Drive, and Jira' — Notion is acting as an enterprise-search aggregator, not merely a document store —… |
| Hybrid lexical + dense retrieval (BM25 fused with embeddings) | Anthropic (Contextual Retrieval reference implementation); | growing | absent | Run a sparse keyword index and a dense vector index over the same chunks and fuse the result lists, because exact identifiers (a function name, an error string) are what BM25 is good at and what embeddings routinely lose. |
| Judge-ensemble leaderboard with a disqualification pre-phase and a private split | Google DeepMind / Google Research — FACTS Grounding | growing | absent | Each prompt pairs a user request with a full document up to 32k tokens and demands a long-form fully-grounded response. Judging runs in two phases: (1) responses are DISQUALIFIED if they do not fulfil the user request; |
| Memory as a directory of plain files the model edits, with no provenance and no staleness field | Anthropic (memory tool, `memory_20250818`); | growing | partial | Six client-side commands — `view`, `create`, `str_replace`, `insert`, `delete`, `rename` — over a `/memories` prefix your application maps onto real storage. |
| Memory poisoning as durable prompt injection, and typed memory writes as the control | MINJA (Dong et al., arXiv 2503.03704); Zep's published defence architecture; | growing | partial | Attack: the attacker never touches the memory store — they interact with the agent by queries only, inducing it to write records whose retrieval later triggers harmful reasoning, using bridging steps plus an indication prompt… |
| Name-triplet entity identity with an explicitly unstable surrogate key | Backstage (CNCF), software catalog core model | growing | absent | Every catalog entity is addressed by the triplet (kind, namespace, name). The catalog DOES mint a `metadata.uid` on first insert, but the spec forbids using it: it is generated by the database and is documented as unstable. |
| Networked personal-knowledge-management tools (Obsidian, Roam Research, Logseq) | Roam Research (2019), Obsidian (2020), Logseq (2020). | growing | absent | Plain-text or block-based notes with [[wiki-style]] bidirectional links, automatic backlink panes, and a graph visualization. The claimed mechanism is that emergent link structure surfaces connections a hierarchy would hide. |
| Opaque-UUID edge with a declared derivation source | OpenMetadata (Collate) | growing | absent | Lineage edges are {fromEntity: uuid, toEntity: uuid, lineageDetails}. lineageDetails carries sqlQuery, pipeline (entityReference), createdBy/createdAt/updatedBy/updatedAt, tempLineageTables (the hops through intermediate/temp… |
| Orphan annotation as catalog-side staleness GC | Backstage software catalog | growing | partial | Internally the catalog keeps a parent->child edge graph that is explicitly 'not the same thing as relations' — its only purposes are orphan detection and cascade deletion. |
| Parse-derived column-level lineage with a declared confidence score | DataHub SQL parser (built on sqlglot); also SQLLineage, dbt's static parser | growing | partial | Parse SQL text into an AST, resolve column references against the catalog's stored schemas ('schema-aware parsing'), and emit FineGrainedLineage with a confidenceScore. Produces column lineage for SELECT (incl. |
| Path-scoped conditional instructions (load rules only when a matching file is touched) | Claude Code `.claude/rules/*.md` with `paths:` frontmatter; | growing | absent | One instruction file per topic, carrying a glob in YAML frontmatter. The harness loads the file into context only when the agent reads/edits a file matching the glob, rather than at session start. |
| Prose files pulled into the compiler — external Markdown compiled and doctested as if it were source | Rust: `#[doc = include_str!("../README.md")]` + `#[cfg(doctest)]`; | growing | absent | A standalone Markdown file (README, book chapter, design doc) is injected into the crate's documentation at compile time so that rustdoc's test extractor treats its fenced code blocks as doctests. |
| Provenance-guaranteed citation (quote is real) decoupled from entailment (quote supports claim) | Anthropic — Citations on the Claude API (also on Vertex AI and Bedrock) | growing | partial | Documents are chunked into sentences server-side (or the caller supplies chunks); Claude emits citations pointing at exact source sentences for claims 'inferred from those sources'. |
| Provenance-stamped lineage edge (actor + time + generating query + confidence) | DataHub — UpstreamLineage / Upstream / FineGrainedLineage aspects | growing | absent | A lineage edge is not a bare pointer. Upstream carries: auditStamp (who reported it, when), created (who created it, when), type (COPY \| TRANSFORMED \| VIEW), a properties bag, and query: optional Urn — 'if the lineage is… |
| Provider buckets with full-vs-delta mutation (re-derive and diff, never append) | Backstage entity providers | growing | covered | Each provider owns a private bucket of entities; 'no two providers can try to output the same entity.' A provider either applies a `type: 'full'` mutation replacing the whole bucket, or a `type: 'delta'` mutation with explicit… |
| Published re-crawl cadences as the real, measurable staleness floor | Glean (the only vendor I found publishing per-connector refresh numbers) | growing | partial | Glean publishes a per-connector table with five independent clocks: Update path (webhook / scheduled / API), Update rate, Incremental crawl, Full crawl, People data, Activity. |
| Publishing a locally-computed build graph into a host that already has diff + gate (dependency submission) | GitHub (`POST /repos/{owner}/{repo}/dependency-graph/snapshots`); | growing | absent | Your build system knows the real resolved graph; the host's manifest parser only guesses from lockfiles. |
| Reference graph as a context-budget allocator (aider's repo map) | Aider (Paul Gauthier); the technique is cited by academic follow-ups as the… | growing | absent | Extract classes/functions/signatures with tree-sitter; build a graph where 'each source file is a node and edges connect files which have dependencies'; run a graph ranking algorithm over it; |
| Retrieval over external library docs and whole-repo wikis via MCP | Upstash Context7 (version-pinned library docs); | growing | partial | The agent's retrieval surface extends past the working tree to a hosted, version-aware index of third-party documentation, reached as an MCP tool or a CLI-plus-skill. |
| SCIP: typed symbol relationships in a flat, schema-versioned index | Sourcegraph (announced 2022-06-08, Olafur Pall Geirsson); | growing | absent | A Protobuf schema (scip.proto). Each Document holds Occurrences (symbol string + source range) and SymbolInformation, which carries `repeated Relationship relationships = 4` — '(optional) Relationships to other symbols (e.g.,… |
| Small specialist entailment model + unified meta-benchmark as the measured ceiling on claim-to-source checking | Liyan Tang, Philippe Laban, Greg Durrett (UT Austin / Salesforce) — MiniCheck,… | growing | absent | Train a small sentence-level fact-checker on synthetic data built by two procedures (Claim-to-Doc and Doc-to-Claim) so the model learns to check each fact in a claim and to recognise synthesis across sentences; |
| Structural URN as canonical identity (name embedded in the key) | DataHub (LinkedIn, now Acryl/DataHub Inc.) | growing | partial | Every entity is addressed by a URN whose ID is a tuple of platform + name + fabric, e.g. urn:li:dataset:(urn:li:dataPlatform:kafka,PageViewEvent,PROD). |
| The documentation IS the contract, tested against the running implementation | Dredd (API Blueprint/OpenAPI); Schemathesis (3.6k stars, OpenAPI/GraphQL property-based) | growing | absent | The API description document is executed against the live backend: Dredd walks the description and asserts the real service replies as documented; |
| Tiny open-weights hallucination classifier + a continuously re-run public leaderboard of model faithfulness | Vectara — HHEM-2.1 / HHEM-2.1-Open, and the Hallucination Leaderboard | growing | partial | A 110M-parameter cross-encoder scores whether a summary is factually consistent with its source document. |
| Transclusion + generate-and-check — the doc does not quote the code, it includes it, and CI fails if the… | Cog (Ned Batchelder) `--check`; embedme `--verify`; mdBook `{{#include file:ANCHOR}}`; | growing | absent | Two variants. (a) Build-time transclusion: the doc names a file and a named anchor region, and the doc builder splices the current content in at render time, so the rendered doc cannot contain a stale copy. |
| Typed long-term memory strategies with templated namespaces (episodic / semantic / summary / preference as… | AWS, Bedrock AgentCore Memory | growing | absent | Memory is created as a managed resource with a list of `memoryStrategies`. Four built-ins, each a named API type with its own `namespaceTemplates`: `UserPreferenceMemoryStrategy` (choices and styles, e.g. |
| Write-time LLM reconciliation: every new fact is classified ADD / UPDATE / DELETE / NONE against existing… | mem0 (open source and Platform) | growing | absent | Two LLM passes per write. First a fact-extraction prompt pulls discrete facts from the turns. |
| ACL crawling as an irreversible, privileged one-way switch (Amazon Q Business) | AWS — Amazon Q Business data source connectors and User Store | niche | partial | Connectors index, per document, the user email, local group name, and federated group name, and store them in the Amazon Q Business User Store to build user/group mappings used to filter chat responses. |
| Catalog schema explicitly reframed as an ontology for agent traversal | Port | niche | partial | Port instructs operators to write blueprint and property `description` fields, and relation `title`/`description` fields, as semantic documentation aimed at AI agents rather than humans — 'Relations are the edges of your… |
| Code Property Graph: merge AST + CFG + data-flow into one labeled property graph | Yamaguchi et al. 2014 (IEEE S&P, 'Modeling and Discovering Vulnerabilities with Code… | niche | absent | One graph whose nodes are typed program constructs (METHOD, LOCAL, CALL, ...) and whose edges are labeled and directed (e.g. |
| Cross-user index reuse via simhash + Merkle content proofs | Cursor (shipped) | niche | absent | Because clones of the same repo inside one org are near-identical, a new client derives a similarity hash from its Merkle tree, the server vector-searches existing simhashes within that team, and seeds the new namespace from the… |
| Data contract as a bundle of executable assertions | DataHub Cloud Data Contracts; Open Data Contract Standard (ODCS, bitol-io); | niche | partial | A contract is 'an agreement between a data asset's producer and consumer' expressed as 'a bundle of verifiable assertions on physical data assets representing a public producer commitment' — schema, freshness, volume,… |
| Deterministic code-comprehension benchmark — can the model find the described function in a real repository… | Jiawei Liu, Lingming Zhang et al. (UIUC) — RepoQA, Searching Needle Function | niche | partial | Plant 'needle' functions at evenly spaced depths through a long chunk of real repository source assembled by following import dependencies; |
| Documented ACL propagation failures in both directions (Elastic connector known issues) | Elastic — published known-issues register for connectors | niche | absent | Three shipped, acknowledged defects. (1) Over-permissioning: the Confluence connector 'ignored or incompletely applied the ancestor chain' for inherited page restrictions, so users could see pages in Elasticsearch they cannot see… |
| Documented procedures executed as end-to-end tests (docs-as-tests) | Doc Detective (131 stars, open source) | niche | absent | Parses Markdown/AsciiDoc for testable actions — CLI commands, API calls, UI steps — and executes each one in a real environment (including a browser) to confirm the instruction still works as written, emitting JSON results for CI. |
| Dual-key identity: mutable human tag plus immutable machine ID | Cortex | niche | absent | Two identifiers per entity. The `x-cortex-tag` is user-authored, globally unique in the workspace, and used for all cross-entity references (dependencies, hierarchy) and API paths. |
| Expiring claims — a doc/comment carries a machine-evaluable predicate that detonates when it comes true | todo_or_die (Ruby, searls, 361 stars); todo-or-die (Rust, compile-time proc macros); | niche | absent | Instead of a prose TODO nobody revisits, the claim is written as a predicate the toolchain evaluates. |
| Explicit (declared) lineage as a correction to inferred lineage | OpenLineage 1.53.0 spec, PR #4804 (mobuchowski), 2026 | niche | absent | New Job and Dataset facets that declare exact dataset-, field- and job-level relationships instead of letting the consumer infer them. |
| Explicit-load conventions file (opt-in, cache-marked) — Aider CONVENTIONS.md | Aider (Paul Gauthier). | niche | absent | Deliberately NOT auto-discovered. The user loads it with `/read CONVENTIONS.md`, `--read CONVENTIONS.md`, or a line in `.aider.conf.yml`. |
| Formal verification of a claim against a logic policy extracted from the source document | AWS — Automated Reasoning checks in Amazon Bedrock Guardrails | niche | absent | Upload a source document; an LLM extracts formal logic rules plus a variable schema, and emits a 'fidelity report ... |
| Freshness as a first-class, partitioned evaluation axis with time-versioned gold answers | Tu Vu et al. (Google / UMass) — FreshQA and FreshLLMs | niche | absent | 600 hand-written questions partitioned by RATE OF CHANGE of the answer: never-changing, slow-changing (years), fast-changing (within a year), plus false-premise questions that must be refuted. |
| Glean: facts under user-defined schemas, queried with a Datalog-like language | Meta (facebookincubator/Glean, open sourced; glean.software) | niche | absent | 'Glean is a system for working with facts about source code.' Facts are 'immutable terms described by user-defined schemas, and form a DAG', automatically deduplicated by the storage backend. |
| Hard character budgets on instruction files (Windsurf) | Windsurf / Cascade (now under Devin/Cognition). | niche | absent | Same four activation modes as Cursor (Manual, Always On, Model Decision, Glob) — but with an ENFORCED cap: reported as 6,000 characters for the global rules file and 12,000 characters total across active workspace rules, applied… |
| Hot-path vs background memory formation — the write-time/read-time axis named as an explicit design choice | LangChain (LangMem SDK, over the LangGraph store) | niche | absent | Memory is split three ways — semantic (facts, as either an unbounded collection or a single structured profile), episodic (successful interactions kept as examples, capturing 'the situation, the thought process that led to… |
| Identity as a JQ expression over the source payload — and a shipped default that keys repos on their name | Port (Ocean integration framework) | niche | absent | Every entity has a `$identifier` meta-property: 'Unique Entity identifier, used for API calls, programmatic access and distinguishing between different entities.' Ingestion maps source objects to entities with JQ: `identifier:… |
| Kythe entry tuples: (source VName, edge kind, target VName) as the universal record | Google (Kythe, open source; derived from Google's internal indexing) | niche | absent | Everything is a node fact or an edge entry. Nodes are addressed by VName (language, corpus, root, path, signature) — a canonical identity independent of file position. |
| Literate CLI snapshot testing — command examples in Markdown executed and diffed against the output printed… | trycmd (Rust, by the clap/assert_cmd maintainers); | niche | absent | Fenced ```console blocks inside `.md` files are parsed as test cases: lines beginning `$` are executed as real commands and everything after is asserted to be the actual stdout/stderr. |
| LLM-in-CI doc-drift review — a model diffs the PR against the docs and flags prose the change contradicts | jbrockSTL/doc-drift (GitHub Action); deichrenner/driftcheck (pre-push hook); | niche | partial | On each diff, an LLM is given the code change plus candidate docs (driftcheck has the model generate targeted ripgrep queries to find related docs first, then searches in parallel) and asked to identify contradictions, reporting… |
| llms-full.txt — the whole documentation site concatenated into one file | Developed by Mintlify with Anthropic as the customer collaborator; | niche | absent | One flat Markdown file containing the entire docs corpus, intended to be pasted or fetched wholesale into a model's context rather than navigated. |
| llms.txt — a curated Markdown index for LLM consumers at /llms.txt | Proposed by Jeremy Howard (Answer.AI), 2024-09-03; spec v2 modified 2026-08-10. | niche | absent | A Markdown file at the site root: optional BOM, an H1 project title (the only required element), an optional blockquote summary, free-form detail sections, and H2-delimited file lists of Markdown links with optional notes. |
| LSIF: an explicit vertex/edge graph dump as the interchange format | Microsoft / Language Server Protocol working group (LSIF 0.6.0); | niche | absent | Newline-delimited JSON where every line is either `{type:"vertex"}` or `{type:"edge", label, outV, inV\|inVs}`. |
| Memory decay as search-time re-ranking by access recency, not deletion | mem0 Platform (`client.project.update(decay=True)`) | niche | absent | Opt-in, off by default. Instead of evicting, retrieval scores are re-weighted: recently accessed memories get up to a 1.5x boost, unused ones dampen toward 0.3x. |
| Metric semantic layer — typed measures and entity-keyed joins compiled to SQL | dbt Labs — dbt Semantic Layer, powered by MetricFlow (predecessor: the dbt_metrics… | niche | absent | Hand-written YAML declares semantic models over existing dbt models, each carrying entities ('the join keys of your semantic model — think of these as the traversal paths, or edges between semantic models', typed primary or… |
| Provenance projection: derived facts carry the lineage of the raw episode they were synthesised from | Zep (episode metadata projection + ABAC access policies on agent API keys, Enterprise… | niche | absent | Zep's framing of the problem: agent memory is *synthesised* — an LLM derives a fact from chat, documents and business data, so the derived fact matches no source word-for-word and nothing ties it back. |
| RDF / SPARQL / W3C PROV — ratified standards, bounded deployment | W3C (PROV family, Recommendations 2013-04-30; SPARQL 1.1 2013); | niche | absent | PROV-DM/PROV-O give an OWL2 vocabulary for provenance — entities, activities, agents, wasDerivedFrom, wasGeneratedBy, used — 'to achieve the vision of inter-operable interchange of provenance information in heterogeneous… |
| Reconciliation as a human review queue (discovered-but-uncatalogued / catalogued-but-no-longer-found) | Cortex 'Discovered entities' (formerly Discovery audit) | niche | absent | Cortex 'continuously compares what already exists in your catalog against what it finds in your connected integrations — your git provider, APM tools, Kubernetes clusters, cloud accounts.' The delta is presented as a reviewable… |
| Relationship checks — scorecard rules that assert an edge exists, with cardinality and target-property filters | OpsLevel | niche | absent | After declaring custom Relationship Definitions between component types, a Relationship Check asserts that a given relationship is populated and constrains how many entities may be attached through it — 'exactly one support… |
| Rename-safe identity by alias accretion (old names never retired) | OpsLevel | niche | absent | Entities (components, teams, tiers, lifecycles) carry auto-generated human-readable aliases used as the reference key in `opslevel.yml` (e.g. `owner: orders_team`). |
| Retrievers trained on agent trajectories, not on human relevance labels | Cursor (shipped embedding model); | niche | absent | Instead of labeling query/document pairs by hand, record what real agent sessions searched and opened, have an LLM rank which content would actually have helped at each step, and train the embedding model to match those rankings. |
| Search substrate re-exposed as an agent platform with an MCP front door | Elastic — Agent Builder | niche | absent | Agents built over Elasticsearch data with built-in and custom tools, plus skills; |
| SKOS — a knowledge-organization standard that deliberately refuses formal semantics | W3C (Recommendation 2009-08-18); deployed in AGROVOC (FAO), EuroVoc (EU), LCSH, MeSH | niche | absent | Concepts, not classes: skos:Concept instances related by skos:broader / skos:narrower / skos:related, labelled by skos:prefLabel / skos:altLabel, defined by skos:definition, grouped into a skos:ConceptScheme. |
| Snippet-to-code coupling with history-aware re-anchoring (commercial doc-drift detection) | Swimm (patented Auto-sync / Verify) | niche | absent | Docs embed 'smart tokens' and code snippets bound to specific source locations. |
| The archived data catalog (a dated negative result) | Amundsen — originated at Lyft 2019, donated to LF AI & Data | niche | partial | Search-first discovery: index tables, dashboards and streams, rank by usage ('a page-rank style search based on usage patterns'), over a Neo4j or Atlas graph backend. Identity by table key (database://cluster.schema/table). |
| The vocabulary problem — measured, and its remedy, unlimited aliasing | George Furnas, Thomas Landauer, Louis Gomez, Susan Dumais (Bell Communications Research),… | niche | absent | Empirical study of spontaneous word choice across five application domains, then simulation of how different vocabulary designs perform against the measured distribution. |
| Two-index document-level security: content index plus a hidden ACL-filter index (Elastic content connectors) | Elastic — connectors framework (Confluence, Jira, GitHub, Gmail, Google Drive, Network… | niche | absent | Two separate sync types. A content sync writes documents into search-* and, when DLS is on, stamps each document's permitted identities into an _allow_access_control field. |
| Versioned, timestamped, TTL'd facts separated from the checks that read them | Backstage Tech Insights (CNCF community-plugins workspace) | niche | partial | A `FactRetriever` has an id, a SEMVER `version` on its schema and handler, a typed `schema`, a `handler` that returns per-entity fact values, and an optional `entityFilter`. |
| Xerox Eureka — peer-reviewed tips as a knowledge base, with authorship credit instead of payment | Xerox / Xerox PARC. Ethnographic basis: Julian E. | niche | partial | Orr's ethnography found that copier technicians solved hard faults through stories told to each other, not through the official documentation — knowledge that the formal system could not see. |
| Zettelkasten — Luhmann's actual card index | Niklas Luhmann (1927–1998). Documented by the Niklas Luhmann-Archiv, Bielefeld University… | niche | partial | From the archive's own description (read verbatim in German, 2026-09-14). Scale: 27 drawers, ~2,500–3,500 A6 slips each, ~90,000 slips total, written between 1952 and early 1997, split into two largely separate collections — ZK I… |
| Ablating your own context file against a benchmark before trusting it | Gloaguen/Mündler/Müller/Raychev/Vechev (ETH Zurich + LogicStar.ai) via CTXbench; | research-only | absent | Treat the context file as a change to be evaluated, not a document to be written. Run the same task set in three settings — no context file, generated file, human file — and compare success rate AND cost. |
| Adversarial audit of the benchmarks every memory vendor cites (judge leniency + corrupted ground truth) | Penfield Labs / dial481 (independent LoCoMo audit); | research-only | partial | A systematic audit of LoCoMo, the most-cited conversational-memory benchmark, against its own data. Findings: 99 of 1,540 questions (6.4%) have wrong golden answers, putting the theoretical scoring ceiling at 93.57%; |
| Adversarial re-evaluation of factuality metrics — the metrics disagree with each other and are biased in a… | Ameya Godbole and Robin Jia (USC) | research-only | absent | Re-evaluate five state-of-the-art factuality metrics on 11 datasets spanning summarization, RAG and QA; compare metrics against each other and against system-level rankings; |
| Citation compliance is enforced on writers, not consumed by readers | Tiziano Piccardi, Miriam Redi, Giovanni Colavizza, Robert West (EPFL / Wikimedia… | research-only | absent | Client-side instrumentation logging every interaction with links from English Wikipedia articles to cited references, over one month. |
| Context rot — long windows do not retire retrieval | Chroma (technical report); cited as rationale by Anthropic's context-engineering guidance | research-only | partial | Model performance is not uniform across input length: with task complexity held constant and only input length varied, accuracy degrades as the window fills, and it degrades faster when the needle is a semantic rather than… |
| GraphRAG over code: query a code graph instead of embedding-retrieving it | RepoGraph (Ouyang et al., arXiv 2410.14684, ICLR 2025); | research-only | absent | RepoGraph: line-level nodes, edges are 'the dependencies of code definitions and references', built by parsing; retrieval pulls ego-graphs around keyword nodes and injects them as context into an existing framework. |
| Learned code-comment inconsistency detection (the literal semantic check, research only) | Panthaplackel, Li, Gligoric, Mooney — 'Deep Just-In-Time Inconsistency Detection Between… | research-only | absent | A model is trained on paired comment/code edit histories to predict, at commit time, whether a given code change has made the associated comment inconsistent — i.e. |
| Meta-benchmark for attribution evaluators — 'how hard is it to check whether the evidence supports the claim?' | Yifei Li, Xiang Yue, Zeyi Liao, Huan Sun (Ohio State) — AttributionBench; | research-only | absent | Aggregate existing human-annotated attribution datasets (AttributedQA, AttrEval-GenSearch, and others) into one binary task — is every claim in the response fully supported by its cited evidence — then measure zero-shot and… |
| Retrieval metrics (nDCG / MAP / MRR) are misaligned with LLM consumers — utility-and-distraction gain instead | Giovanni Trappolini, Florin Cuconasu, Simone Filice, Yoelle Maarek, Fabrizio Silvestri… | research-only | absent | Two named misalignments: 'human vs machine position discount' (an LLM reads all retrieved documents at once; |
| Unit-test corpus that grades the GRADER — meta-evaluation of grounded-QA judges by failure mode | Sacha Muller, António Loison, Bilel Omrani, Gautier Viaud (Illuin Technology) — GroUSE | research-only | absent | Enumerate 7 generator failure modes in grounded QA, then hand-write 144 unit tests across 16 situations in which the SAME question is paired with slightly varied answers and references so that a correctly calibrated judge must… |

---

## Deep-dive verifications

Seven dives, organised by cross-domain convergence rather than by scout. Each re-verified
its theme's load-bearing claims against primary sources. Scout claims that did not survive
are corrected here and in the ledger below, never removed.

### Dive 1 — Identity under rename — seven domains, one rule, one counter-example

**The shipped default keys the entity on a mutable display name (Port / Ocean GitHub
integration) (VERIFIED)**  
*Mechanism:* port-labs/ocean, integrations/github/.port/resources/port-app-config.yml, read
from main on 2026-09-14 (file last modified 2026-08-16T13:38:27+03:00, commit
0c121f703036170734b4858fb4a308f170d20a44, established by shallow clone). The `repository`
kind maps `identifier: .name` and `title: .name`, blueprint `"githubRepository"`, relations
`{organization: .owner.login}`. GitHub's opaque `node_id` appears in the same file exactly
once, on the `organization` kind, as a plain non-identifying property (`nodeId: .node_id`);
the `repository` kind does not capture it at all. File header: `deleteDependentEntities:
true`, `createMissingRelatedEntities: true`. The same repo's gitlab-v2 default keys projects
on `identifier: .path_with_namespace | gsub(" "; "")` — also a mutable path, while GitLab's
stable numeric project id goes uncaptured.  
*Why leaders use it:* JQ-over-payload identity is maximally flexible and the readable name
is what an operator wants to see in a URL and an API path. `.name` is the field a human
would pick. Nothing in the tool pushes back.  
*Failure mode:* Verified from Port's own cleanup doc: 'When you remove a resource type from
your integration mapping or decommission an integration, the associated entities in Port are
not automatically deleted', with a mandatory three-step manual process and an explicit
ordering warning ('If you delete entities first, the next integration resync will recreate
them'). Combined with `identifier: .name`, a git-side rename produces a new entity under the
new name and an orphan under the old one. NOT DIRECTLY OBSERVED: I did not run a resync
against a renamed repo; the orphan is inferred from the mapping plus the cleanup doc,
exactly as the scout recorded it. What IS verified is the mapping itself — the name is the
key, shipped, today.  
*Fit here:* A falsifiable pre-condition an evidence contract can assert: 'the join key for
this entity is not derived from any field a human can edit'. Port's own file is the negative
fixture.  
*Sources:*
https://raw.githubusercontent.com/port-labs/ocean/main/integrations/github/.port/resources/port-app-config.yml
(read 2026-09-14; file last modified 2026-08-16) ·
https://raw.githubusercontent.com/port-labs/ocean/main/integrations/gitlab-v2/.port/resources/port-app-config.yml
(read 2026-09-14) ·
https://docs.port.io/context-lake/ingestion/configure-mapping/entity-cleanup.md (read
2026-09-14) ·
https://docs.port.io/context-lake/data-model/setup-blueprint/properties/meta-properties.md
(read 2026-09-14)

**The reference implementation of the category mints a surrogate key and forbids using it
(Backstage) (VERIFIED)**  
*Mechanism:* Backstage catalog entities are addressed by the triplet (kind, namespace, name)
as a string entity ref. A `metadata.uid` exists but the spec disclaims it verbatim: 'Note
that `uid` values are _not_ to be seen as stable, and should _not_ be used as external
references to an entity. The `uid` can change over time even when a human observer might
think that it wouldn't. As one of many examples, unregistering and re-registering the exact
same file will result in a different `uid` value even though everything else is the same.
Therefore there is very little, if any, reason to read or use this field externally.' It
then directs the reader to the string entity reference instead.  
*Why leaders use it:* The uid is database-generated per insert, so it is a row identity, not
an entity identity. Backstage is honest that it cannot promise more, and routes everyone to
the name.  
*Failure mode:* Identity IS the name, by design. A rename is a delete plus an add.
`locationKey` disambiguates two SOURCES claiming one name (first-writer-wins); nothing
reconciles one entity appearing under two names over time.  
*Fit here:* The clearest statement in the whole corpus of the difference between a surrogate
key (stable for the life of a row) and a canonical identity (stable for the life of the
thing). A gate that says 'use the stable id' must say WHICH stability it means.  
*Sources:*
https://raw.githubusercontent.com/backstage/backstage/master/docs/features/software-catalog/descriptor-format.md
lines 269-283 (read 2026-09-14)

**The lineage graph is severed by rename, and the vendor documents it as a limitation rather
than fixing it (Databricks Unity Catalog) (VERIFIED)**  
*Mechanism:* Unity Catalog captures table- and column-level lineage automatically from query
execution. The limitations section states, verbatim and unhedged: 'Lineage is not preserved
for renamed catalogs, schemas, tables, views, or columns.' Adjacent limitations in the same
list: 'Lineage data captured before September 1, 2024 is not available', 'Column lineage
cannot be captured if the source or the target is referenced as path', 'Global temp views
are not captured in lineage', 'Resilient Distributed Datasets (RDDs) are not captured in
lineage.'  
*Why leaders use it:* Lineage is derived from parsed query text, which names objects by
name. Nothing in the execution record carries a surrogate identity for the object being read
or written, so a rename is indistinguishable from a new object.  
*Failure mode:* Silent. There is no orphan queue, no reconciliation prompt, no matchType
flag — the edges are simply absent afterward. This is the single strongest 'name-as-key
fails' datum in the corpus because it comes from the vendor's own limitation list, in a
product that captures lineage automatically at engine level.  
*Fit here:* A hard, quotable failure case for any evidence contract that claims derived
relationships survive refactors. Also a warning about the class: automatic derivation from
text can never be rename-safe on its own.  
*Sources:* https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage
(page states Last Updated September 11, 2026; string extracted verbatim from raw HTML
2026-09-14) ·
https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/data-lineage
(independent host, identical sentence, verified 2026-09-14)

**The name is structurally inside the primary key, and only case can be healed (DataHub)
(CORRECTED)**  
*Mechanism:* A DataHub URN has the form `urn:<Namespace>:<Entity Type>:<ID>`. The doc names
DatasetUrn as a complex nested URN with exactly three ID fields — 'It contains 3 ID fields:
`platform`, `name` and `fabric`' — and gives
`urn:li:dataset:(urn:li:dataPlatform:kafka,PageViewEvent,PROD)` as the example. The URN is
the primary key of the aspect store, the search index and every graph edge. The only
normalization DataHub offers is case: ingest-time config `convert_urns_to_lowercase` /
`convert_column_urns_to_lowercase` / `preserve_column_case` fold identifier casing before
the URN is minted.  
*Why leaders use it:* A structural URN is human-legible, dereferenceable without a registry,
and lets any producer mint an id offline without coordinating. That is a real property the
opaque-key designs give up.  
*Failure mode:* CORRECTED AND SHARPENED from DataHub's own release notes. Casing is not
'healed' after the fact — it is normalized at ingest by configuration, and CHANGING that
configuration is itself a re-key that orphans data. Verbatim: 'that table's dataset URN
changes (for example `….ORDERS` becomes `….Orders`) and the previously ingested entity is
orphaned; soft-delete the old one or re-ingest with stateful ingestion so it is cleaned up.'
And on column casing: 'Treat this as a one-way door: the option is part of every column's
`schemaField` URN, so enabling it after data has been ingested re-keys every column and
orphans column-level tags, glossary terms and documentation attached in the UI.' Also:
'DataHub matches column-level edges case-sensitively.' There is no alias, previous-name, or
rename field on the dataset key anywhere in the model; I searched the full release-notes
history for rename handling and found only unrelated uses of the word.  
*Fit here:* The one-way-door language is exactly what an irreversibility gate is for.
'Changing this config re-keys every row' is a classified human gate if anything is.  
*Sources:* https://raw.githubusercontent.com/datahub-project/datahub/master/docs/what/urn.md
(read 2026-09-14) · https://docs.datahub.com/docs/what/urn (read 2026-09-14) ·
https://raw.githubusercontent.com/datahub-project/datahub/master/docs/how/updating-datahub.md
lines 143, 144, 146, 279, 280 (read 2026-09-14)

**One system, two identity regimes, and the wrong one is underneath (OpenMetadata)
(CORRECTED)**  
*Mechanism:* Verified directly against the JSON Schema on main.
`entityLineage.json#/definitions/edge` declares `fromEntity` and `toEntity` as
`basic.json#/definitions/uuid`. Nested inside `lineageDetails.columnsLineage`,
`columnLineage.fromColumns` and `.toColumn` are
`basic.json#/definitions/fullyQualifiedEntityName` — 'A unique name that identifies an
entity. Example for table `DatabaseService.Database.Schema.Table`', a plain string. So the
coarse edge is keyed on an opaque UUID and the fine-grained edge nested inside it is keyed
on a name path. `table.json` confirms the split at the entity: `id` is a uuid,
`fullyQualifiedName` is 'serviceName.databaseName.tableName'.  
*Why leaders use it:* Column identity has no natural surrogate — columns are not first-class
entities with their own UUIDs in most sources — so the FQN is the only handle available. The
convenience compounds: an FQN can be constructed by a SQL parser without a lookup.  
*Failure mode:* CORRECTED. The scout wrote 'a table rename preserves every table-level edge,
which is the right answer'. That holds only for a rename applied THROUGH OpenMetadata's own
API, where the UUID is retained. For a rename in the SOURCE system — the case that actually
matters, and the case Databricks documents as lineage-destroying — I found no rename
detection anywhere in `databaseServiceMetadataPipeline.json`, and the stale-entity option is
verbatim: markDeletedTables, `"default": true`, 'only tables that have been deleted from the
source will be soft deleted... Any related entities such as test suites or lineage
information that were associated with those tables will also be deleted.' A source-side
rename presents to the connector as one FQN disappearing and another appearing. On the
default configuration the old table is soft-deleted AND ITS LINEAGE WITH IT, and the new FQN
arrives as a new UUID with no edges. The UUID does not rescue a source-side rename; it only
rescues a rename performed inside the catalog.  
*Fit here:* The most transferable shape in the dive: an opaque key at the top layer is worth
nothing if the layer that actually carries the meaning is keyed on a name, and if the
ingestion path never learns that a rename happened. Check the whole stack, not the key at
the top of it.  
*Sources:*
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/type/entityLineage.json
(read 2026-09-14) ·
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/type/basic.json
(read 2026-09-14) ·
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/entity/data/table.json
(read 2026-09-14) ·
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/metadataIngestion/databaseServiceMetadataPipeline.json
(read 2026-09-14)

**The identity function is defined to be blind to the aliases that make renames survivable
(Avro) (VERIFIED)**  
*Mechanism:* Avro 1.12.0 specification, 'Transforming into Parsing Canonical Form'. Step
[STRIP], verbatim: 'Keep only attributes that are relevant to parsing data, which are:
`type`, `name`, `fields`, `symbols`, `items`, `values`, `size`. Strip all others (e.g.,
`doc` and `aliases`).' The spec then defines schema fingerprints (SHA-256, MD5, 64-bit
Rabin) over that canonical form, and Parsing Canonical Form is explicitly the definition of
schema sameness: 'If the Parsing Canonical Forms of two different schemas are textually
equal, then those schemas are "the same" as far as any reader is concerned'. Meanwhile
aliases are the rename mechanism: 'if the writer's schema was named "Foo" and the reader's
schema is named "Bar" and has an alias of "Foo", then the implementation would act as though
"Foo" were named "Bar" when reading.'  
*Why leaders use it:* The canonical form answers one question only — can this reader parse
this writer's bytes — and aliases genuinely do not affect the wire format. The design is
internally coherent. The problem is that the fingerprint then gets used as the schema's
IDENTITY in registries and caches, a job it was not defined for.  
*Failure mode:* SHARPENED beyond the scout's claim, in Avro's favour on one point and
against it on another. Against: the claim is exactly right — a schema that renames a field
and records the old name as an alias produces a fingerprint that differs from the original
AND that carries no trace of the alias, so no fingerprint-keyed system can ever connect the
two. Worse than the scout said: the spec makes alias resolution OPTIONAL — 'An
implementation MAY OPTIONALLY use aliases to map a writer's schema to the reader's' — and
the Schema Resolution match rules themselves never mention aliases, matching records by
'(unqualified) name'. So rename survivability in Avro is (a) invisible to the identity
function and (b) not guaranteed by any conforming implementation.  
*Fit here:* Canonical textbook case of an identity function whose inputs were chosen for a
different purpose than the one it ends up serving. Worth stating as a rule: whatever you
hash to define sameness IS your identity, regardless of what you named the function.  
*Sources:* https://avro.apache.org/docs/1.12.0/specification/ sections 'Aliases', 'Schema
Resolution', 'Parsing Canonical Form for Schemas', 'Schema Fingerprints' (local capture read
2026-09-14)

**Alias accretion — the cheap fix, with a documented collision pathology (OpsLevel)
(CORRECTED)**  
*Mechanism:* Entities carry auto-generated human-readable aliases used as the reference key
in `opslevel.yml`. Verbatim from the vendor's markdown endpoint, section 'Alias Stability'
(page front matter updatedAt 2025-12-11): 'Aliases are stable identifiers. If you rename an
entity that has an alias (e.g., a team), OpsLevel will generate a new alias. However, the
old alias will still be valid so any existing references to it from other `opslevel.yml`
files will continue to work.'  
*Why leaders use it:* It gets rename-as-rename for existing references without a surrogate
key, a registry, or a migration. For an org that cannot retrofit stable ids, keeping the old
name resolving is strictly better than letting it 404.  
*Failure mode:* CORRECTED — 'old names never retired' is the default behaviour, not an
invariant, and the accretion has a documented pathology the scout explicitly flagged as
unverified. OpsLevel's own Components FAQ (updatedAt 2026-05-05) has a section titled
'Resolving Duplicate Alias Conflicts ("_2")' whose remedy is a four-step manual dance: '1.
Delete the existing alias: Remove the `shopping_cart_service` alias temporarily. 2. Rename
the service: Rename the service to a temporary name... 3. Delete the unwanted alias: Remove
the `shopping_cart_service_2` alias. Refresh the page if the alias appears locked. 4.
Restore the original name.' So aliases ARE deletable, the namespace DOES collide, and a
rename into a taken name silently produces a suffixed alias rather than the one you asked
for. GitHub confirms the same class of hazard for its own repo-name redirects (see the next
pattern), which is the strongest cross-domain evidence that this is intrinsic to alias
accretion, not an OpsLevel bug.  
*Fit here:* Alias accretion is the right fallback when no stable id exists, but it needs an
explicit answer to 'can an old name be reclaimed?' — and in both systems that answer is yes,
which converts a silent redirect into a silent MISdirect. That is a classified gate, not a
checklist item.  
*Sources:* https://docs.opslevel.com/docs/opslevel-yml.md section 'Alias Stability' (front
matter updatedAt 2025-12-11T18:03:20Z; read 2026-09-14) ·
https://docs.opslevel.com/docs/components.md section 'Resolving Duplicate Alias Conflicts
("_2")' (front matter updatedAt 2026-05-05T19:13:31Z; read 2026-09-14)

**Authority control — one authorized access point, every variant recorded, in a record
separate from the things that cite it (library science) (VERIFIED)**  
*Mechanism:* Three dated layers, each verified against a primary. (1) CODIFICATION, 1876: C.
A. Cutter, 'Rules for a Printed Dictionary Catalogue', Department of the Interior, Bureau of
Education, Government Printing Office, 1876. Rule 15 verbatim: 'Put the works of authors who
change their name under the latest form, provided the new name be legally and permanently
adopted.' Rule 44 (the References rule) verbatim sub-clauses: '(15.) From the earlier forms
of names that are changed.' '(14 c.) From the maiden names or first married names of wives
to the last, provided they have written under the earlier names or for any other reason are
likely to be looked for under them.' 'From any other title by which a man may be better
known than by his real name.' Rule 5 verbatim: 'Enter pseudonymous works under the author's
real name, when it is known, with a reference from the pseudonym.' That is one authorized
form plus a retained cross-reference from every superseded name, in print, in 1876 — 150
years before this dive. (2) INTERNATIONAL CODIFICATION, 1961: the Paris Principles,
'approved by the International Conference on Cataloguing Principles in 1961', published as
Report, London: IFLA, 1963, p. 91-96. (3) CURRENT STATEMENT, 2016: IFLA Statement of
International Cataloguing Principles, approved 2016, published December 2016. §5.3 verbatim:
'The authorized access point for the name of an entity should be recorded as authority data
along with identifiers for the entity and variant forms of name.' §5.3.3.1 verbatim: 'If a
person, family, or a corporate body uses variant names or variant forms of names, one name
or one form of name should be chosen as the basis for the authorized access point.' The
SEPARATE record is the machine-format layer: MARC 21 Format for Authority Data is 'designed
to be a carrier for information concerning the authorized forms of names... the forms of
these names... that should be used as references to the authorized forms, and the
interrelationships among these forms'; fields 400-485 (See From Tracings) 'are used to
identify unauthorized forms of headings and other variants not chosen as an authorized
form.' Governance is the NACO program, verbatim: 'Participants agree to follow a common set
of standards and guidelines when creating or changing authority records in order to maintain
the integrity of a large shared authority file.'  
*Why leaders use it:* Because the alternative was measured and found unworkable: the same
person publishes under six names across a century and no catalogue that stores free-text
names can ever gather their work. Making identity a first-class record, separate from the
things that cite it, is what lets a rename be one edit.  
*Failure mode:* Cost, and it is the honest one to quote: NACO gates contribution behind a
five-day training course and quotas ('200 authority records each year for large institutions
and 100 for smaller'). This is the most labour-intensive answer in the corpus, and it works
precisely because a profession pays for it continuously. It is not a mechanism you get for
free by adding a field.  
*Fit here:* The 150-year-old version of the mechanism is also the most complete: it
separates the identity record from the citing records, names one preferred form, retains
every superseded form as a pointer, AND — per ICP 2016 — records 'identifiers for the
entity' alongside the authorized name. Library science did not choose name-as-key OR
id-as-key; it keeps both and says which is which.  
*Sources:* C. A. Cutter, 'Rules for a Printed Dictionary Catalogue', Bureau of Education,
GPO, 1876 — full text, archive.org identifier cu31924029518978, rules 5, 15, 44 read
verbatim 2026-09-14
(https://archive.org/download/cu31924029518978/cu31924029518978_djvu.txt) · IFLA, 'Statement
of International Cataloguing Principles (ICP)', 2016 Edition, approved and published
December 2016, §5.3, §5.3.3.1, glossary —
https://repository.ifla.org/bitstreams/a8b24b93-cefc-4fa6-b2fd-4c81316292ec/download (read
2026-09-14) · Paris Principles 1961, cited in ICP 2016 footnote 1: International Conference
on Cataloguing Principles (Paris: 1961). Report. London: IFLA, 1963, p. 91-96 · Library of
Congress, MARC 21 Format for Authority Data: Introduction (page dated October 2009) —
https://www.loc.gov/marc/authority/adintro.html (read 2026-09-14) · Library of Congress,
MARC 21 Format for Authority Data: 4XX See From Tracings (page dated November 2016, revised
11/17/2016) — https://www.loc.gov/marc/authority/ad4xx.html (read 2026-09-14) · Library of
Congress PCC, 'About NACO' — https://www.loc.gov/aba/pcc/naco/about.html (read 2026-09-14)

**LSIF's opaque global integer IDs and the move to SCIP — and SCIP moved TOWARD name-bearing
identity, not away from it (CORRECTED)**  
*Mechanism:* Sourcegraph's announcement post (June 8, 2022, Olafur Pall Geirsson) lists
LSIF's limitations. Verbatim, the one that matters: 'Complexity of implementing incremental
indexing, which becomes necessary for large codebases. The heavy usage of opaque global IDs
imposes an ordering constraint on how symbols (or \'resultSet\') get added to the index,
making it tricky to deal with cyclic dependencies in files, among other common situations.
Globally incrementing IDs make it difficult, as well, to update an existing index with new
information for only a subset of the documents.' Also verbatim: 'Difficulty of manually
debugging raw LSIF payloads caused by the heavy usage of opaque ID numbers to encode the
graph structure', and 'Most of these issues boil down to the graph encoding of LSIF, which
heavily relies on opaque ID numbers to connect edges and vertices.' The death is documented
in the SCIP repo's own design doc: 'Sourcegraph historically supported LSIF uploads as well
as maintained LSIF indexers, but ran into issues of development velocity, debugging, as well
as indexer performance bottlenecks. LSIF support has since been fully deprecated and
removed.'  
*Why leaders use it:* SCIP replaced the integers with 'human-readable string IDs for symbols
replacing the concept of \'monikers\' and \'resultSet\''. scip.proto confirms the shape:
`Symbol { string scheme; Package package; repeated Descriptor descriptors; }`, `Package {
string manager; string name; string version; }`, `Descriptor { string name; string
disambiguator; Suffix suffix; }`. Every component is a NAME.  
*Failure mode:* CORRECTED on two counts, one against the scout and one against the theme.
(1) Against the scout: the blog never mentions DIFFING. It says incremental indexing and it
says updating a subset of documents. 'And therefore diffing' is the scout's inference, not
Sourcegraph's word — and the design doc's own reason for avoiding integer IDs is different
again: 'Avoiding integer IDs helps with limiting the blast radius of indexer bugs. With
LSIF, we've had off-by-one bugs in indexers cause code navigation to fail repo-wide.' Blast
radius and debuggability, not rename survival. (2) Against the theme: SCIP is
COUNTER-EVIDENCE. Sourcegraph looked at an opaque-key design, found it unworkable, and
replaced it with a structured key built entirely out of mutable human-readable names —
package name, version, descriptor names. Rename a function and its SCIP symbol string
changes, by construction. The domain that most recently and most deliberately revisited this
trade-off went the OTHER WAY from the theme's claimed convergence, because their consumer
re-indexes from source on every commit and never needs an identity that outlives a name.  
*Fit here:* The condition that makes name-as-key correct is worth naming precisely, because
it is the condition Redgate would test: identity may be a name when the index is fully
re-derived from the source of truth on every change and nothing is accumulated across
versions. When anything accumulates — a human annotation, a tag, a curated claim, a lineage
edge — the name stops being sufficient.  
*Sources:* https://about.sourcegraph.com/blog/announcing-scip — 'SCIP - a better code
indexing format than LSIF', June 8, 2022, Olafur Pall Geirsson (read 2026-09-14) ·
https://raw.githubusercontent.com/sourcegraph/scip/main/docs/DESIGN.md (read 2026-09-14) ·
https://raw.githubusercontent.com/sourcegraph/scip/main/scip.proto — message Symbol,
Package, Descriptor (read 2026-09-14)

**What GitHub actually guarantees about node_id — and what it does not (CORRECTED)**  
*Mechanism:* Two GitHub docs pages, read verbatim 2026-09-14. 'Using global node IDs': 'In
REST, the global node ID field is named `node_id`. In GraphQL, it's an `id` field on the
`node` interface.' and 'When building integrations that use either the REST API or the
GraphQL API, it's best practice to persist the global node ID so you can easily reference
objects across API versions.' 'Migrating GraphQL global node IDs': 'The GitHub GraphQL API
currently supports two types of global node ID formats. The legacy format will be closing
down and replaced with a new format.' 'if you currently decode the legacy IDs to extract
type information... your service will break since the format of the IDs has changed. You
should migrate your service to treat these IDs as opaque strings. These IDs will be unique,
therefore you can rely on them directly as references.'  
*Why leaders use it:* Unique + opaque + persistable-across-API-versions is a genuinely
strong contract, and far stronger than anything Backstage, Port, DataHub or Databricks
offers. The scout was right that it is the best available primitive here.  
*Failure mode:* CORRECTED — the guarantee is narrower than 'stable', and GitHub has already
broken value stability once by its own announcement. github.blog, February 10, 2021, Wissam
Abirached, verbatim: 'We are changing the Global ID format in our GraphQL API. As a result,
all object identifiers in GraphQL will change and some identifiers will become longer than
they are now. Since you can get an object's Global ID via the REST API, these changes will
also affect an object's `node_id` returned via the REST API.' And: 'Once the three migration
phases are complete, we will sunset the old IDs. All requests made using the old IDs will
result in an error.' In practice legacy ids still resolve today, but the documented intent
was to make them error. Separately and more importantly for this theme: I could find NO
GitHub documentation anywhere stating that a repository's node_id is preserved across a
rename, or across a transfer to another owner. The words 'stable', 'immutable', 'permanent'
and 'never changes' do not appear on either page. The rename doc addresses redirects, not
identifiers, and does not mention the API at all. The property fleet-playbook-curator's
entire design rests on is an empirical regularity that GitHub has not put in writing.  
*Fit here:* The gap between 'unique and opaque' (documented) and 'stable across rename and
transfer' (assumed) is exactly the kind of claim an evidence contract exists to force into
the open. It is not wrong to rely on it; it is wrong to cite it as a guarantee.  
*Sources:* https://docs.github.com/en/graphql/guides/using-global-node-ids (read 2026-09-14)
· https://docs.github.com/en/graphql/guides/migrating-graphql-global-node-ids (read
2026-09-14) · https://github.blog/2021-02-10-new-global-id-format-coming-to-graphql/ — 'New
global ID format coming to GraphQL', February 10, 2021 (read 2026-09-14)

**GitHub itself practices alias accretion for repository names — and documents the exact
hazard OpsLevel does not (VERIFIED)**  
*Mechanism:* GitHub docs, 'Renaming a repository', verbatim: 'All existing information, with
the exception of project site URLs, is automatically redirected to the new name, including:
Issues, Wikis, Stars, Followers' and 'All `git clone`, `git fetch`, or `git push` operations
targeting the previous location will continue to function as if made on the new location.'
Then the two exceptions, verbatim: 'GitHub will not redirect calls to an action hosted by a
renamed repository. Any workflow that uses that action will fail with the error `repository
not found`.' and 'If you create a new repository under your account in the future, do not
reuse the original name of the renamed repository. If you do, redirects to the renamed
repository will no longer work.'  
*Why leaders use it:* It makes a rename non-breaking for the overwhelming majority of
references without asking anyone to update anything.  
*Failure mode:* Two failures, both load-bearing. First, the name-keyed reference that does
NOT get the alias — a workflow's `uses:` line — fails hard with 'repository not found'. Even
inside a system that implements redirects, one name-keyed reference class is left out, and
it is the machine-readable one. Second, the alias is reclaimable: create a new repo with the
old name and the redirect silently stops pointing at the renamed repo. That is the
independent confirmation of the OpsLevel hazard, from a different vendor, in writing.  
*Fit here:* Answers the question the OpsLevel doc leaves open, and answers it badly: yes, an
old name can be reclaimed, and when it is, the failure is silent redirection rather than a
404.  
*Sources:*
https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
(read 2026-09-14)

**Implications:**
- Does the convergence hold? Six of the nine claims survive as stated or stronger; three
  needed correction, and one of the corrections is fatal to the word 'convergence'. SCIP is
  the problem. Sourcegraph in 2022 took a format built on opaque global IDs, found it
  unworkable, and deliberately replaced it with a key made entirely of mutable
  human-readable names. That is not a seventh domain agreeing; it is the most recent domain
  to actually re-decide, deciding the other way. So the honest form of the finding is
  narrower and more useful than 'every domain converged': a mutable name must never be the
  key WHEN ANYTHING ACCUMULATES ACROSS VERSIONS OF THE THING. Sourcegraph accumulates
  nothing — every index is re-derived from source at a commit — so names cost them nothing.
  Databricks, DataHub, OpenMetadata, Port, Backstage and library catalogues all accumulate
  (lineage edges, human tags, glossary terms, curated claims, an authority file), and every
  one of them either pays for the rename or documents that it cannot. That predicate is the
  transferable rule, and it is the predicate a Redgate evidence contract can actually test.
- Does fleet-playbook-curator have a reason to change? Yes, one concrete one, and it is the
  OpenMetadata failure reproduced exactly. The MANIFEST layer is rename-safe:
  `list-fleet-members.sh` emits members keyed by node_id, `diff-fleet.sh` joins on node_id
  and emits `renamed: [{node_id, from, to}]` as a first-class event. The CLAIM LEDGER
  underneath it is not. `templates/fleet-playbook/index.schema.json` requires exactly `repo`
  ('owner/name of the source repo'), `path`, `sha`, `curated_at`, with
  `additionalProperties: false` — there is no node_id field and no way to add one without a
  schema change. `validate-citations.sh` then does an exact string match, `grep -qxF
  "$repo"`, against `context.json`'s `full_name`. So the plugin has a UUID-keyed top layer
  and an FQN-keyed layer underneath: precisely OpenMetadata's split, where table edges
  survive a rename and the column lineage nested inside them does not. After a rename, every
  pre-existing claim in index.json still carries the dead `owner/old-name` string, and
  nothing in SKILL.md, PROMPT.md or the templates instructs the curator to rewrite it. The
  minimal fix is to add `node_id` to the claim schema and have the curator rewrite `repo`
  from the diff's `renamed` entries; the cheaper fix, if the schema is frozen, is to make
  the rename event's changelog line mandatory AND to have the curator re-key affected claims
  in the same pass. Either way the gap is real and is exactly the thing this dive was
  looking for.
- Does the convergence support or undermine the standing verdict that a repo fleet does NOT
  need a knowledge graph because node_id already solves canonical identity? It SUPPORTS the
  verdict and WEAKENS one of its premises, and those are separate results. It supports it
  because the thing a knowledge graph would buy here — a rename-survivable join between
  observations of the same thing over time — is the one thing node_id already provides for
  free, natively, from the source of truth, with no ingestion pass, no reconciliation queue
  and no orphan GC. Backstage declined that primitive and documents
  rename-as-delete-plus-add as intended behaviour. Port's shipped default throws it away in
  favour of `.name` and leaves orphans its own docs say nothing cleans up. DataHub baked the
  name into the primary key and now documents config changes as one-way doors that orphan
  every column. Databricks simply states the lineage is gone. Every one of those systems is
  a knowledge graph, and every one of them has a WORSE identity story than a bash script
  calling `gh api orgs/<owner>/repos`. The graph is not what solves identity; the upstream
  stable id is. Adding a graph on top of an upstream that already has one buys nothing and
  adds a second place for identity to drift.
- Where it weakens the premise: the verdict as currently written treats node_id as a
  guaranteed stable key, and GitHub does not say that. Documented: unique, opaque, persist
  it across API versions. Not documented anywhere: survives a rename, survives a transfer
  between owners, or holds its value over time — and GitHub has in fact changed every
  node_id value once already, announced on 2021-02-10, with a stated plan to make the legacy
  values error. The verdict does not fall, because the alternative designs are all strictly
  worse, but the JUSTIFICATION should be restated: node_id is the best available identity
  primitive and a well-attested empirical regularity, not a contractual guarantee. That is a
  one-line prose change in SKILL.md ('GitHub's stable node_id' → something that does not
  assert a guarantee GitHub declines to make), and it is the kind of change the behavioral
  tier exists to catch.
- One practical control this dive earns, cheap enough to be worth it: GitHub's own rename
  docs say the old repo name keeps redirecting UNLESS someone creates a new repo reusing
  that name, in which case the redirect silently retargets. A fleet whose curated claims are
  keyed on `owner/name` is therefore exposed not only to a rename but to a NAME REUSE — the
  worst case, because the citation still resolves and now points at the wrong repository.
  `validate-citations.sh` cannot see this: it checks that the repo was read this pass, not
  that the repo it read is the same repo the claim was made about. Carrying node_id in the
  ledger closes that hole too, and it is the only thing that does.
- For Redgate specifically, the corpus now yields a testable pre-condition rather than a
  slogan. Not 'never key on a name' — SCIP disproves the universal. The falsifiable form:
  'name-as-key is safe only if the index is fully re-derived from the source of truth on
  every change and nothing human-authored or cross-version accumulates against it.' That is
  a yes/no question about any given design, answerable without a debate, and it correctly
  sorts every one of the nine systems in this dive. It also correctly flags
  fleet-playbook-curator's claim ledger, which accumulates human-curated claims across
  passes and is therefore on the wrong side of the line.

### Dive 2 — Edges nobody machine-checks — and the two that are

**Stated policy of NOT validating edges: dangling relations are documented as normal and
hard validation is explicitly discouraged (VERIFIED)**  
*Mechanism:* Backstage's `relations` is a read-only, processor-derived root field. Both
scout quotes are VERIFIED VERBATIM. (1)
docs/features/software-catalog/extending-the-model.md, line 363: 'Relations may be dangling
(referencing something that does not actually exist by that name in the catalog), and
callers need to be aware of that.' (2) docs/features/software-catalog/faq.md, section 'Can I
validate relations in processors?': 'It's tempting to put rules in your processors that mark
entities as invalid if they have a relation to some other entity that does not exist. For
example, a `Component` entity that declares a `spec.owner` to a team that has been
disbanded. We strongly discourage from doing this type of "hard" validation in processors,
for two reasons.' Reason one is performance: 'you should avoid calling out to the catalog
for any reason in processors, including for checking whether a target entity exists. Besides
the performance issues, it can also lead to data races where hidden dependencies between
entities lead to them never properly settling, or flickering back and forth between states
for hard-to-debug reasons.' Reason two is user experience: 'Owners of catalog-info files
will constantly be surprised by their files "breaking" in ingestion, maybe a very long time
after they were initially created.' Backstage does still hard-validate SHAPE: 'There are
cases where it's fine to throw hard validation errors in processors. Notably, when it
doesn't pass a schema test at all and readers of the catalog data will break if the data was
let through.'  
*Why leaders use it:* An eventually-consistent catalog that mirrors many external systems
cannot distinguish 'this edge is wrong' from 'the other end has not been ingested yet.'
Failing closed on that ambiguity converts every ingestion-order race into a user-visible
breakage of a file nobody touched. Backstage chose to fail open and move the check to a
non-blocking surface.  
*Failure mode:* By policy, renaming an entity silently converts every live edge pointing at
it into a dangling one and nothing goes red anywhere. Edges are addressed by entity-ref
string, so the rename hazard is total. Backstage checks that an edge is well-FORMED (parses
as an entity ref) and never that its target exists.  
*Fit here:* This is the category's explicit answer to Redgate's 'falsifiable criteria'
instinct — and the answer is 'not at ingestion.' The transferable rule: separate SHAPE
checks (cheap, offline, blocking) from TRUTH checks (expensive, external, advisory).
fleet-playbook-curator's cheap tier is already on the right side of that line.  
*Sources:*
https://raw.githubusercontent.com/backstage/backstage/master/docs/features/software-catalog/extending-the-model.md
(fetched 2026-09-14, line 363) ·
https://raw.githubusercontent.com/backstage/backstage/master/docs/features/software-catalog/faq.md
(fetched 2026-09-14, sections 'Can I validate relations in processors?' and 'Can I throw
errors when validating entities?') ·
https://raw.githubusercontent.com/backstage/community-plugins/main/workspaces/tech-insights/README.md
(fetched 2026-09-14)

**Provenance-stamped edge whose own doc comment concedes the verdict goes stale (CORRECTED)**  
*Mechanism:* VERIFIED in the Pegasus sources, with corrections to how the scout grouped the
fields. The four fields are real but split across two records, not one. Upstream.pdl
carries: `auditStamp: AuditStamp` ('Audit stamp containing who reported the lineage and
when'), `created: optional AuditStamp` ('who created the lineage and when'), `type:
DatasetLineageType`, `properties: optional map[string, string]` ('A generic properties bag
that allows us to store specific information on this graph edge'), `query: optional Urn`
('If the lineage is generated by a query, a reference to the query'), and `matchType:
optional LineageMatchType`. Upstream.pdl has NO confidenceScore. FineGrainedLineage.pdl
carries `transformOperation: optional string`, `confidenceScore: float = 1.0` ('The
confidence in this lineage between 0 (low confidence) and 1 (high confidence)'), `query:
optional Urn` ('Present only if the lineage was generated from a detected query'), and its
own aggregate `matchType`. The concession is VERIFIED VERBATIM in LineageMatchType.pdl:
'This verdict reflects DataHub's knowledge AT THE TIME THE LINEAGE EDGE WAS INGESTED, not
the current state of the graph. It is a point-in-time record and is not re-evaluated
automatically: e.g. a reference recorded as UNRESOLVED (its target did not exist yet) keeps
that value even after the target is later ingested and the edge in fact resolves exactly —
the verdict only refreshes when the referencing source is re-ingested.' Enum values are
EXACT, NORMALIZED, UNRESOLVED, with the doc comments the scout quoted.  
*Why leaders use it:* Re-evaluating every edge against the live graph is O(edges) work on
every read. Recording the verdict at write time makes it O(1) and auditable, and the honest
doc comment is what keeps the cheap answer from being read as a fresh one.  
*Failure mode:* Exactly what the comment says: a stale verdict that only refreshes on
re-ingestion of the referencing source. Plus a scope limit the scout's framing obscured —
matchType is not general edge validation, see corrections.  
*Fit here:* The field list to copy if fleet-playbook-curator ever models an edge — and more
importantly, the doc-comment discipline. DataHub writes the staleness INTO the schema, where
every consumer must read it. That is a falsifiable-criteria practice applied to
documentation rather than to code.  
*Sources:*
https://raw.githubusercontent.com/datahub-project/datahub/master/metadata-models/src/main/pegasus/com/linkedin/dataset/Upstream.pdl
(fetched 2026-09-14; byte-identical to the scout's saved copy) ·
https://raw.githubusercontent.com/datahub-project/datahub/master/metadata-models/src/main/pegasus/com/linkedin/dataset/FineGrainedLineage.pdl
(fetched 2026-09-14; byte-identical to scout copy) ·
https://raw.githubusercontent.com/datahub-project/datahub/master/metadata-models/src/main/pegasus/com/linkedin/dataset/LineageMatchType.pdl
(fetched 2026-09-14) · tag probe 2026-09-14: LineageMatchType.pdl returns 404 at v1.5.0 and
v1.6.0.2, 200 at v1.7.0 and v1.8.0rc3

**Closed enum naming HOW each edge was derived, with the human-asserted value as the DEFAULT
(VERIFIED)**  
*Mechanism:* VERIFIED. openmetadata-spec/.../type/entityLineage.json,
definitions.lineageDetails.properties.source: description 'Lineage type describes how a
lineage was created.', type string, enum exactly ['Manual', 'ViewLineage', 'QueryLineage',
'PipelineLineage', 'DashboardLineage', 'DbtLineage', 'SparkLineage', 'OpenLineage',
'ExternalTableLineage', 'CrossDatabaseLineage', 'ChildAssets'], and — the detail the scout
missed — '"default": "Manual"'. Manual is not merely first-class beside the machine-derived
values; it is what an edge gets when nothing says otherwise. lineageDetails also carries
sqlQuery ('SQL used for transformation'), pipeline ('Pipeline where the sqlQuery is
periodically run'), createdBy ('User who created the node'), createdAt, updatedBy,
updatedAt, and columnsLineage (fromColumns / toColumn / function). The containing
`entitiesEdge` is 'Edge in the lineage graph from one entity to another using entity
references' with required fromEntity and toEntity and additionalProperties false.  
*Why leaders use it:* A closed enum in a JSON Schema is machine-validated on write for free:
an unknown derivation method is rejected by the schema, no custom validator required. It
also gives conflict resolution a key to sort on when two ingestions disagree about the same
edge.  
*Failure mode:* The schema validates that `source` is a member of the set. Nothing validates
that the value is TRUE — an edge ingested by a query parser can be labelled Manual and the
schema is satisfied. And because Manual is the default, an edge whose derivation was simply
never recorded is indistinguishable from one a human asserted: the safest-sounding value is
the one you get by saying nothing.  
*Fit here:* The cheapest field in this entire dive to copy, and the one place
fleet-playbook-curator is genuinely behind the field: it has no derivation field at all. But
copy the enum, not the default — defaulting to the human-asserted value is the wrong
direction for a corpus whose whole risk is fabricated assertion.  
*Sources:*
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/type/entityLineage.json
(fetched 2026-09-14)

**CODEOWNERS — cited natively, diffable per line, and checked by a third party that reports
but does not enforce (CORRECTED)**  
*Mechanism:* CITED: the edge IS a line in a file at a known path (.github/, root, or docs/,
'GitHub will search for them in that order and use the first one it finds'), so it cites to
repo@sha:path#Ln with no machinery. DIFFABLE: a changed line is a changed edge, with an
author and a commit. MACHINE-CHECKED — and this is where the scout over-claimed, see
corrections. WHAT GitHub checks: (a) syntax — 'If any line in your CODEOWNERS file contains
invalid syntax, that line will be skipped'; (b) owner existence and permission — 'The people
you choose as code owners must have write permissions for the repository. When the code
owner is a team, that team must be visible and it must have write permissions', and 'If you
specify a user or team that doesn't exist or has insufficient access, a code owner will not
be assigned.' WHEN it checks: on demand only. (i) When you view the file in the web UI —
'When you navigate to the CODEOWNERS file in your repository, you can see any errors
highlighted'; (ii) via `GET /repos/{owner}/{repo}/codeowners/errors`, whose own description
is 'List any syntax errors that are detected in the CODEOWNERS file', with an optional `ref`
query param — 'A branch, tag or commit name used to determine which version of the
CODEOWNERS file to use. Default: the repository's default branch' — so the check can be
pinned to the same sha a citation records; (iii) the GraphQL equivalent. Error objects carry
line, column, source, kind, suggestion, message, path (line/column/kind/message/path
required). The documented example kinds are 'Invalid pattern' and 'Invalid owner'. The
endpoint was confirmed live this session: an unauthenticated call for jrichlen/agent-plugins
(which has no CODEOWNERS) returned the documented 404 naming
/rest/repos/repos#list-codeowners-errors. NOT on push, NOT a status check, NO failing check
ships. Separately, branch protection can make the edge load-bearing at merge: 'you can
choose to require reviews from code owners. If you do, any pull request that affects code
with a code owner must be approved by that code owner before the pull request can be merged
into the protected branch.'  
*Why leaders use it:* It is the only edge in this dive whose target is validated by a party
other than the author, at a ref the citation already pins, for the price of one HTTP request
— and where a rename BREAKS LOUDLY into a queryable error list instead of silently becoming
a dangling ref.  
*Failure mode:* Three, and the third is serious. (1) The check reports; it never fails.
Nothing in GitHub turns a CODEOWNERS error into a red check — a consumer must build that.
(2) It checks the endpoint, not the relation: a line naming a live, write-capable,
completely wrong team produces zero errors. (3) The merge gate degrades OPEN. Branch
protection requires approval only for 'code with a code owner'; an invalid line is skipped,
so those paths have no code owner, so the requirement is vacuous for exactly the paths whose
ownership declaration is broken. Add the size cliff: 'CODEOWNERS files must be under 3 MB in
size. A CODEOWNERS file over this limit will not be loaded, which means that code owner
information is not shown and the appropriate code owners will not be requested to review
changes in a pull request.' Total silent failure at the file level.  
*Fit here:* The existence proof, but a narrower one than claimed. The free part is the
VERDICT; the gate is still yours to write: `gh api repos/{repo}/codeowners/errors?ref={sha}
--jq '.errors|length'` non-zero -> fail. One line, ref-pinned, and it slots straight into
the ledger's existing {repo, path, sha} shape. It is NOT offline, so it cannot live in the
cheap tier.  
*Sources:*
https://raw.githubusercontent.com/github/docs/main/content/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners.md
(fetched 2026-09-14, lines 18, 36, 52, 64, 79, 81) ·
https://docs.github.com/en/rest/repos/repos (fetched 2026-09-14, operation 'List CODEOWNERS
errors', embedded OpenAPI schema and example) ·
https://api.github.com/repos/jrichlen/agent-plugins/codeowners/errors (called 2026-09-14,
returned the documented 404) ·
https://raw.githubusercontent.com/github/docs/main/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md
(fetched 2026-09-14, line 85) ·
https://github.blog/changelog/2022-02-17-codeowners-improvements-syntax-errors-preview-of-who-will-be-requested-and-more/
(2022-02-17, read 2026-09-14)

**The build graph as the authoritative edge set, where the check is a byproduct of the edge
being load-bearing (CORRECTED)**  
*Mechanism:* VERIFIED, with a soundness caveat the scout did not surface.
bazel.build/query/language: 'The Bazel query language is a language of expressions. Every
expression evaluates to a partially-ordered set of targets, or equivalently, a graph (DAG)
of targets. This is the only datatype.' Implicit edges are included by default: 'In addition
to build dependencies that are defined explicitly in BUILD files, Bazel adds additional
implicit dependencies to rules. Implicit dependencies may be defined by: Private attributes,
Toolchain requirements. By default, bazel query takes implicit dependencies into account.'
bazel-diff supplies the content-hashed diff, VERIFIED VERBATIM: '`generate-hashes` is a
canonical SHA256 value representing all attributes and inputs into a target. These inputs
are the summation of the rule implementation hash, the SHA256 value for every attribute of
the rule and then the summation of the SHA256 value for all `rule_inputs` using the same
exact algorithm. For source_file inputs the content of the file are converted into a SHA256
value.' Its workflow is hash-at-revision-A, hash-at-revision-B, compare the two JSON files
to get 'the exact affected set of impacted targets between two Git revisions'. The
check-as-byproduct claim holds but is CONDITIONAL on sandboxing: bazel.build/docs/sandboxing
says 'Without action sandboxing, Bazel doesn't know if a tool uses undeclared input files
(files that are not explicitly listed in the dependencies of an action)', and the failure
surfaces as 'Sandboxed execution failed, which may be legitimate (such as a compiler error),
or due to missing dependencies.'  
*Why leaders use it:* Nobody maintains this graph for the graph's sake. The edges are
written to make the build work, so an under-declared edge is punished by the thing everybody
already runs, with no separate validator, no separate owner, and no separate budget.  
*Failure mode:* Asymmetric and under-appreciated: UNDER-declaration breaks the build;
OVER-declaration never does. A stale dependency that is no longer needed is invisible
forever, and it inflates the impacted set on every diff. Bazel also disclaims precision in
its own 'Soundness' section: 'The result of evaluating an expression in the Bazel query
language is true for all configurations, which means that it may be a conservative
over-approximation, and not exactly precise.' bazel-diff's server mode ships an explicit
correctness contract with a silent-miss failure: 'The list must be a superset of what
actually changed: a truly-changed file left off it is content-skipped on both sides and its
impacted targets are missed, so treat the list as a correctness contract.' And the failure
message itself is ambiguous — 'may be legitimate (such as a compiler error), or due to
missing dependencies.'  
*Fit here:* The strongest primitive in the dive and the one that actually generalizes: hash
a node TOGETHER WITH its edges, and a changed edge becomes a changed hash. That is a
per-edge change signal without a per-edge identity. It is also the only place in this sweep
where the edge check is free because the edge is load-bearing — which is the real lesson:
make the edge do work, and the check comes with it.  
*Sources:* https://bazel.build/query/language (fetched 2026-09-14; sections 'Bazel query
language concepts', 'Implicit dependencies', 'Soundness') ·
https://raw.githubusercontent.com/Tinder/bazel-diff/master/README.md (fetched 2026-09-14;
'How it works', generate-hashes description, server-mode modifiedFilepaths contract) ·
https://bazel.build/docs/sandboxing (fetched 2026-09-14, 'Reasons for sandboxing' and the
example error message)

**Host-computed edge diff with a CI gate — that gates the CONTENTS of the delta, not its
accuracy (CORRECTED)**  
*Mechanism:* The diff is VERIFIED VERBATIM: `GET
/repos/{owner}/{repo}/dependency-graph/compare/{basehead}` — 'Gets the diff of the
dependency changes between two commits of a repository, based on the changes to the
dependency manifests made in those commits', with an optional `name` param, 'The full path,
relative to the repository root, of the dependency manifest file.' The gate is
actions/dependency-review-action, and its knobs are all node-policy knobs:
`fail-on-severity` ('The action will fail on any pull requests that introduce
vulnerabilities of the specified severity level or higher', default `low`), `allow-licenses`
/ `deny-licenses`, `fail-on-scopes` (default `runtime`), `deny-packages`, `deny-groups`. It
is not blocking on its own: 'the repository owner must configure branch protection settings
that require the check to pass before merging.'  
*Why leaders use it:* Identity (PURL), diff and gate all come from the host, on data the
repo already has. Nobody writes a graph store and nobody writes a differ.  
*Failure mode:* The scout's claim that 'a required check fails the PR on a bad edge delta'
does not survive. Nothing in the action gates edge accuracy — there is no input that means
'fail if a dependency edge is wrong or missing.' It fails on properties of the PACKAGES
inside the delta. Other explicit non-failures, from the action's own README: 'If we can't
detect the license for a dependency we will inform you, but the action won't fail', and
`warn-only: true` 'will log all vulnerabilities as warnings regardless of the severity, and
the action will complete with a success status.' Coverage limit from the endpoint's own
wording: the diff is 'based on the changes to the dependency manifests made in those
commits', so an edge that changes without a manifest edit — a floating range resolving
differently — is invisible. The SBOM export endpoint the scout cited carries: 'Closing down
notice: This operation is closing down and will not be accessible after November 13, 2026.
Please migrate to the asynchronous flow.'  
*Fit here:* A precise warning for PR #134: 'GitHub already gates this edge' is true about
vulnerability policy and false about edge truth. Borrowing the loop gets you diff and
delivery, not verification.  
*Sources:* https://docs.github.com/en/rest/dependency-graph/dependency-review (fetched
2026-09-14) ·
https://raw.githubusercontent.com/actions/dependency-review-action/main/README.md (fetched
2026-09-14; options table lines 118-135, notes line 142, blocking section line 245) ·
https://docs.github.com/en/rest/dependency-graph/sboms (fetched 2026-09-14; closing-down
notice)

**Publishing locally-computed edges into a host that already has diff and gate — with a
PUBLISHED PRECEDENCE ORDER over derivation methods (VERIFIED)**  
*Mechanism:* VERIFIED, and richer than the scout reported. `POST
/repos/{owner}/{repo}/dependency-graph/snapshots` takes resolved packages keyed by
`package_url` (PURL), each with `relationship` — 'A notation of whether a dependency is
requested directly by this manifest or is a dependency of another dependency. Can be one of:
direct, indirect' — `scope` ('runtime, development'), a `dependencies` array of 'package-url
(PURLs) of direct child dependencies', and a required `scanned` timestamp. The find the
scout missed: GitHub publishes a conflict-resolution ranking over HOW an edge was derived.
'Dependency graph displays only one instance of each manifest file using the following
precedence rules. User submissions take the highest priority, because they are usually
created during artifact builds they have the most complete information... Dependabot graph
jobs have the second-highest priority. For ecosystems where Dependabot graph jobs are
available (currently Go and Python), they take precedence over automatic dependency
submission. Automatic submissions have the next priority since they are also created during
artifact builds, but are not submitted by users. Static analysis results are used when no
other data is available.' That is OpenMetadata's `source` enum turned into an operational
tie-breaker.  
*Why leaders use it:* The build knows the real resolved graph; the host's manifest parser
guesses. Submission lets the place that knows tell the place that diffs.  
*Failure mode:* The submitter is trusted end to end — nothing checks that a submitted
snapshot honestly reflects the build, and 'user submissions take the highest priority' means
a self-reported snapshot OUTRANKS every machine-derived source. A self-report that wins a
precedence contest is the exact shape this corpus's 'self-reported never promotes' rule
exists to forbid.  
*Fit here:* Two transferable pieces. The bridge pattern (compute edges where they are known,
publish them to a surface that already diffs and gates) and, more useful here, the
precedence ledger: rank derivation methods explicitly, and write the ranking down. Then
invert GitHub's ordering — for a provenance corpus, human self-report should rank LAST, not
first.  
*Sources:* https://docs.github.com/en/rest/dependency-graph/dependency-submission (fetched
2026-09-14; payload schema and precedence rules) ·
https://raw.githubusercontent.com/actions/dependency-review-action/main/README.md (fetched
2026-09-14; `retry-on-snapshot-warnings` — 'retrying the action every 10 seconds while
waiting for dependency submission actions to complete' — establishes that submitted
snapshots feed the review path, which the scout had flagged as its own extrapolation)

**EXTRACTED / INFERRED / AMBIGUOUS edge tags whose SHAPE is machine-checked and whose TRUTH
is not (VERIFIED)**  
*Mechanism:* The tags are real and VERIFIED in the project's own architecture doc. Every
extractor returns edges of the form {"source": "id_a", "target": "id_b", "relation":
"calls|imports|uses|...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}, and '`validate.py`
enforces this schema before `build()` consumes it.' The definitions table, verbatim:
EXTRACTED — 'Relationship is explicitly stated in the source (e.g., an import statement, a
direct call)'; INFERRED — 'Relationship is a reasonable deduction (e.g., call-graph second
pass, co-occurrence in context)'; AMBIGUOUS — 'Relationship is uncertain; flagged for human
review in GRAPH_REPORT.md'. Note the field is literally named `confidence`, not
`provenance`. What validate.py enforces is membership in the enum — it never re-derives the
edge to confirm the label. Backstage's posture in miniature: shape checked, truth not.  
*Why leaders use it:* Separating found from guessed is the right instinct and costs one
enum, and routing AMBIGUOUS to a human-review section is a working non-blocking nudge.  
*Failure mode:* Same as OpenMetadata: an INFERRED edge mislabelled EXTRACTED passes
validation. Nothing re-parses the source to confirm that an EXTRACTED edge corresponds to an
actual import or call.  
*Fit here:* Confirms the dive's central finding from the small end of the field: three
independent projects (DataHub, OpenMetadata, graphify) all record HOW an edge was derived;
none of the three validates the recording.  
*Sources:* https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/ARCHITECTURE.md
(fetched 2026-09-14, 'Extraction output schema' and the confidence-label table) ·
https://raw.githubusercontent.com/Graphify-Labs/graphify/main/README.md (fetched 2026-09-14,
line 112)

**Implications:**
- PARITY, not deficit — on the axis PR #134 actually names. Nobody in the field
  machine-checks that a relationship claim is TRUE. Backstage refuses on the record and says
  so twice ('Relations may be dangling... and callers need to be aware of that'; 'We
  strongly discourage from doing this type of "hard" validation'). DataHub writes the
  staleness into its own schema ('is not re-evaluated automatically'). OpenMetadata records
  how an edge was derived in a closed enum and defaults it to 'Manual'. graphify validates
  that a confidence label is a member of a three-value enum and never re-derives the edge.
  GitHub's dependency gate fails on vulnerable packages, never on a wrong edge. The gap
  fleet-playbook-curator has is the gap the category has chosen.
- On one narrow axis it is AHEAD, and PR #134 should say so. validate-citations.sh is a
  deterministic, offline gate that fails the pass when a claim's repo was not read this
  round or its cited path is not in that repo's gathered tree. Backstage's equivalent check
  on a relation is that the target string PARSES as an entity ref. A per-claim traceability
  gate that can go red, run offline in under a second, is stronger than what the
  category-leading catalog applies to an edge. The honest framing is: the marketplace is
  ahead on citation traceability and at parity on edge truth.
- The one real DEFICIT is smaller and cheaper than the PR assumes: there is no derivation
  field. Four independent systems record HOW each edge was derived — DataHub's matchType and
  query URN, OpenMetadata's source enum, GitHub's direct/indirect plus its detector
  precedence ladder, graphify's EXTRACTED/INFERRED/AMBIGUOUS. None validates the label; all
  of them keep it, because a label you cannot check still tells a reader which claims to
  distrust. The claim ledger's schema has repo, path, sha, curated_at and an optional claim
  string — adding a required derivation enum is a schema edit plus one cheap-tier assertion.
  Copy the enum; invert OpenMetadata's default, since defaulting to the human-asserted value
  is backwards for a corpus whose whole risk is fabricated assertion.
- CODEOWNERS does NOT dominate the three candidate edges, and the PR should not claim it
  does. It dominates on two of the three tests decisively — the edge IS a cited line
  (repo@sha:path#Ln, no parser), and a changed line IS a changed edge with an author and a
  commit. On the third it supplies a free VERDICT, not a free gate: GitHub computes owner
  existence and write access, exposes them at GET /repos/{o}/{r}/codeowners/errors with a
  `ref` param that accepts the exact sha the ledger already stores — and then does nothing
  with them. No push check, no status check, no failing check anywhere. The consumer writes
  the red.
- Worse, applying PR #134's OWN disqualifying test honestly puts owned-by in the same box as
  authenticates-as. The note disqualifies repo--authenticates-as-->identity because 'nothing
  in the fleet can re-derive it without touching the identity provider.' But
  repo--owned-by-->team is equally external-state-dependent: whether @org/team exists, is
  visible, and holds write permission lives in GitHub's org graph, not in any blob at any
  sha. owned-by survives only because GitHub happens to expose a first-party, ref-pinned
  endpoint for that external state. That is a real and decisive advantage — but it is an
  advantage of AVAILABILITY, not of self-containment, and the PR should argue it that way or
  the test it uses to kill authenticates-as also kills its own recommendation.
- And the CODEOWNERS gate degrades open, which is the finding that should most change the
  PR's recommendation. Branch protection requires code-owner approval only for 'code with a
  code owner'; an invalid or unresolvable line is SKIPPED, so those paths have no owner, so
  the requirement is vacuous for precisely the paths whose ownership is broken. A 3 MB file
  is not loaded at all and every owner vanishes silently. An owned-by edge sourced from
  CODEOWNERS without wiring the errors API to a failing check is not merely unchecked — it
  LOOKS checked, which is strictly worse than an edge everyone knows is unverified.
- So the ranking the evidence supports, which differs from the PR's: if the plugin can spend
  one network call per pass, repo--owned-by-->team wins, with the gate written explicitly —
  `gh api repos/{repo}/codeowners/errors?ref={sha} --jq '.errors|length'`, non-zero fails —
  and with the honest caveat that this proves the owner EXISTS and CAN WRITE, never that the
  ownership is correct. If the plugin must stay inside its own cheap-tier constraint
  ('deterministic, offline, free, under a second'), CODEOWNERS cannot run there at all and
  repo--deploys-via-->workflow wins outright: it is the only candidate whose re-derivation
  is a pure function of a blob at a sha the ledger already cites, so the check needs nothing
  outside the ledger. The two edges are not competing on the same axis, and naming the axis
  — network-permitted versus offline — is what decides between them.
- The transferable mechanism, across every leader, is not validation. It is Bazel's: an edge
  that is LOAD-BEARING gets checked for free, because something everybody already runs
  breaks when it is wrong. Bazel does not run an edge validator; it runs a build. GitHub
  does not validate CODEOWNERS; it tries to assign a reviewer. The corollary for
  fleet-playbook-curator is sharper than 'add a join check': an edge nothing in the workflow
  consumes will never be reliably checked, no matter how good the validator, because the
  validator is the only thing that would notice. Prefer the edge some existing step already
  depends on. Second-best is Bazel's other trick, which needs no consumer: hash the node
  together with its edges, so a changed edge becomes a changed hash — a per-edge change
  signal without a per-edge identity, and exactly the key diff-fleet.sh lacks.
- Finally, a corpus-hygiene consequence: graphify's 116,700 stars against 3 subscribers must
  be struck as adoption evidence wherever it appears. The measurement is in corrections; the
  rule it implies is that a star count is an unvalidated self-reported edge from a platform
  to a project — the very failure mode this dive is about — and the corpus should treat it
  as one. Cite graphify's EXTRACTED/INFERRED schema, which is real and readable; never its
  popularity.

### Dive 3 — Claims that can go red — and how reliably they fail open instead

**Python stdlib doctest — interactive-session examples in docstrings or in a free-standing
text file are executed and output-compared (VERIFIED)**  
*Mechanism:* `doctest` scans for `>>>` interactive-session text, executes each statement
against the real current library, and string-compares actual stdout to the output printed in
the prose. `python -m doctest mod.py` runs it with no third-party install.
`doctest.testfile("example.txt")` does the same for a PLAIN TEXT FILE that contains no
Python program at all — the file 'is treated as if it were a single giant docstring'.  
*Why leaders use it:* Zero install cost (stdlib since forever), and it is the only member of
the family that natively targets a free-standing prose file rather than a source file. The
documented use case is literally the one this dive is about: 'To check that a module's
docstrings are up-to-date by verifying that all interactive examples still work as
documented.'  
*Failure mode:* EXECUTED 2026-09-14: a docstring claiming `broken(2, 3)` returns `6` against
an implementation returning `-1` printed `***Test Failed*** 1 failures.` and `python3 -m
doctest mod.py` exited **1**. `doctest.testmod()` returned `TestResults(failed=1,
attempted=2)`. Limit: it checks only the restated-as-code part of a claim; the paragraph
above the example can assert anything and stays green. Second limit: nothing auto-discovers
doctests — `-m doctest` must be pointed at each file, or pytest's `--doctest-modules`
enabled.  
*Fit here:* Strongest fit of the family for THIS repo, because `testfile()` makes a
Markdown-ish prose file a test input directly. Deterministic, offline, stdlib, milliseconds.
The catch is that it only runs Python, so it checks a SKILL.md claim only if that claim is
restated as a Python expression.  
*Sources:* https://docs.python.org/3/library/doctest.html (fetched 2026-09-14; quotes: 'To
check that a module's docstrings are up-to-date by verifying that all interactive examples
still work as documented'; 'literate testing' / 'executable documentation'; 'the final line
of output is ***Test Failed*** N failures.'; 'The file content is treated as if it were a
single giant docstring; the file doesn't need to contain a Python program!') · local
execution, Python 3.11.15, /usr/lib/python3.11/doctest.py, 2026-09-14 — exit 1 observed

**Rust `cargo test --doc` — fenced examples in doc comments are compiled and run; runs by
DEFAULT under plain `cargo test` (VERIFIED)**  
*Mechanism:* rustdoc extracts every fenced code block from doc comments, wraps each in its
own crate, compiles it against the real current library, and runs it. A doctest passes if it
'compile[s] and run[s] without panicking'. Attributes narrow the contract: `no_run` (compile
only), `compile_fail` (compilation MUST fail), `should_panic`, `ignore`.  
*Why leaders use it:* It is on by default — no opt-in per module, no runner configuration.
An API rename breaks every doc example that used the old name, in the same command
developers already run.  
*Failure mode:* EXECUTED 2026-09-14: `cargo test --offline` printed a `Doc-tests` section
without any `--doc` flag, confirming default-on. A doc example importing a non-existent
symbol produced `error[E0432]: unresolved import` → `Couldn't compile the test` → `error:
doctest failed` → exit **101**. Limit: same as Python — the prose around the fence is
unchecked. `ignore` silently disables a block, and `no_run` downgrades it to a compile
check.  
*Fit here:* The reference implementation of 'a command that re-derives it and a comparison
that can go red'. Not adoptable here directly (no Rust in this repo), but the DEFAULT-ON
property is the transferable design lesson: the scout's other doctest members are opt-in and
therefore fail open on new material.  
*Sources:* https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
(fetched 2026-09-14; quotes: 'rustdoc supports executing your documentation examples as
tests. This makes sure that examples within your documentation are up to date and working.';
'regular doctests are considered to "pass" if they compile and run without panicking') ·
local execution, rustc/cargo 1.94.1, 2026-09-14 — exit 101 observed

**Go Example functions — compiled always, executed ONLY if a trailing `// Output:` comment
is present (VERIFIED)**  
*Mechanism:* `go test` compiles every `ExampleXxx` function in the package. Functions
carrying a concluding `// Output:` comment are additionally executed and their stdout is
compared to the comment text. Functions without that comment are compiled and discarded.  
*Why leaders use it:* Examples are both rendered in godoc and type-checked by the normal
test command, so a signature change breaks the published example at build time with no extra
tooling.  
*Failure mode:* EXECUTED 2026-09-14, and this is sharper than the scout's reading. (a)
`ExampleAdd` with `// Output: 3` against an implementation returning `-1` → `--- FAIL:
ExampleAdd`, `got: -1 / want: 3`, exit **1**. (b) An example WITHOUT `// Output:` whose body
is `panic(...)` → `ok ex 0.003s [no tests to run]`, exit **0** — proving it is never
executed. (c) The same example with a type error → `FAIL ex [build failed]`, exit **1** —
proving it IS compiled. NET: forgetting `// Output:` silently downgrades a behavioural claim
to a compile-only claim, with no diagnostic. That is a fail-open inside the doctest family
itself.  
*Fit here:* The (b)/(c) split is the most useful thing Go teaches here: a checking mechanism
whose strength depends on an easily-omitted marker will drift to its weakest setting,
silently. Any gate this repo adopts should make the weak mode loud, not default.  
*Sources:* local execution, go1.24.7, 2026-09-14 — exits 1 / 0 / 1 observed for the three
cases above · https://pkg.go.dev/testing (fetched 2026-09-14 by scout; 'Example functions
without output comments are compiled but not executed')

**Elixir ExUnit.DocTest — generates ExUnit tests from `iex>` examples, but ONLY for modules
explicitly registered (CORRECTED)**  
*Mechanism:* `doctest(module, opts \\ [])` is a macro invoked from inside an ExUnit test
case. Calling `doctest(Module)` generates tests for all `iex>` examples found in that
module's `@doc` and `@moduledoc` attributes.  
*Why leaders use it:* ExUnit ships with Elixir, so there is no dependency to add;
documentation examples become ordinary `mix test` failures.  
*Failure mode:* No Elixir toolchain in this container — behaviour NOT executed,
documentation only. CORRECTION TO SCOUT: it is opt-in per module. A new module with `@doc`
examples is checked by nobody until someone writes `doctest MyModule` into a test file. The
scout's 'ships in the standard toolchain of four major languages' flattens a real
difference: Rust auto-discovers, Go auto-discovers, Elixir and Python do not.  
*Fit here:* Cautionary. 'In the standard toolchain' is not the property that matters; 'runs
without anyone remembering to wire it up' is. This repo's cheap tier already gets this right
— its plugin discovery FAILS CLOSED, so a new plugin with no eval pack turns the tier red
rather than being skipped.  
*Sources:* https://ex-unit.hexdocs.pm/ExUnit.DocTest.html (fetched 2026-09-14; quotes:
'Doctests allow us to generate tests from code examples found in @moduledoc and @doc
attributes'; 'To do this, invoke the doctest/1 macro from within your test case')

**nbval — notebooks re-executed and diffed against stored outputs (THIRD-PARTY, not standard
toolchain) (CORRECTED)**  
*Mechanism:* A pytest plugin. `py.test --nbval` reruns each notebook cell and compares
produced output against the output stored in the .ipynb. `--nbval-lax` runs the notebook and
fails only on errors, checking outputs solely for cells marked `#NBVAL_CHECK_OUTPUT`.  
*Why leaders use it:* Notebooks are the documentation in data/ML work, and a notebook whose
stored outputs no longer reproduce is a doc that lies with a number in it.  
*Failure mode:* CORRECTION TO SCOUT'S GROUPING: nbval is NOT standard toolchain. `import
nbval` raised ModuleNotFoundError in this container while `import doctest` resolved to
/usr/lib/python3.11/doctest.py. It is a pip-installed pytest plugin and belongs in a
different adoption tier from doctest/rustdoc/go test. Behaviour not executed here.
`--nbval-lax` is a second opt-in fail-open of the Go `// Output:` shape.  
*Fit here:* Low. Not adoptable (no notebooks here) and its lax mode repeats the
marker-dependent weakness.  
*Sources:* https://nbval.readthedocs.io/en/latest/ (fetched 2026-09-14; quotes: 'Validating
the notebook means to rerun the notebook and make sure that it is generating the same output
as has been stored.'; 'the IPython Notebook Validation plugin for py.test') · local: python3
-c 'import nbval' → ModuleNotFoundError; 'import doctest' → /usr/lib/python3.11/doctest.py,
2026-09-14

**A free-standing prose file compiled into the build — `#[doc =
include_str!("../README.md")] #[cfg(doctest)] pub struct ReadmeDoctests;` (VERIFIED)**  
*Mechanism:* `include_str!` splices the README's bytes into a doc attribute at COMPILE time.
`#[cfg(doctest)]` confines the carrier struct to doctest builds so the README does not
pollute the rendered API docs. rustdoc's extractor then treats the README's fenced Rust
blocks as ordinary doctests.  
*Why leaders use it:* It is the only shipped mechanism found that promotes a file nobody
compiles — the README, the file most likely to be stale — into an input of the build that
already gates merges.  
*Failure mode:* EXECUTED 2026-09-14, and it does everything claimed plus one thing the scout
did not claim. (a) A README fence importing a non-existent `multiply` → `test src/lib.rs -
ReadmeDoctests (line 14) ... FAILED`, `error[E0432]: unresolved import`, exit **101**. (b)
FAILS CLOSED ON DELETION: renaming README.md away turned the build red with `couldn't read
../README.md` / `error: attribute value must be a literal`. That is the exact opposite of
mdBook's behaviour below, and it is the property that makes the recipe trustworthy. (c)
Unchanged limit: only the fenced code is checked; the surrounding prose is not.  
*Fit here:* The conceptual model this repo wants for AGENTS.md/SKILL.md, and the (b)
property is the specification: the gate must fail when the cited artifact VANISHES, not only
when it disagrees. A citation checker that silently passes on a missing target is worse than
none.  
*Sources:* https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
(fetched 2026-09-14; quotes the exact incantation and 'This will include your README as
documentation on the hidden struct ReadmeDoctests, which will then be tested alongside the
rest of your doctests.') · https://raw.githubusercontent.com/clap-rs/clap/master/src/lib.rs
(fetched 2026-09-14) — REAL-WORLD USE: lines 108-110 are verbatim `#[doc =
include_str!("../README.md")]` / `#[cfg(doctest)]` / `pub struct ReadmeDoctests;` ·
https://raw.githubusercontent.com/clap-rs/clap/master/clap_builder/src/lib.rs (fetched
2026-09-14) — same three lines at 51-53, plus `#![doc = include_str!("../README.md")]` at
line 6 · local execution, rustc/cargo 1.94.1, 2026-09-14 — exit 101 on both the wrong-claim
and the deleted-file cases

**Expiring claims as compile errors — todo-or-die (Rust) / todo_or_die (Ruby) (CORRECTED)**  
*Mechanism:* A reminder is written as a machine-evaluable predicate instead of a prose TODO.
Rust proc macros: `after_date!(y,m,d)`, `issue_closed!(owner,repo,n)`, `pr_closed!`,
`crates_io!(crate,req)`, `rust_version!` — each emits `compile_error!` when its condition
comes true. Ruby: `TodoOrDie("...", by: Date)` / `if:` raises `TodoOrDie::OverdueError` at
class-load time.  
*Why leaders use it:* It answers a question no other mechanism here even asks: WHEN should
this claim be revisited? The claim carries its own trigger instead of relying on someone
re-reading it.  
*Failure mode:* EXECUTED 2026-09-14 — and the scout's framing of this as 'the sharpest
mechanism I found' is materially incomplete. It works: `after_date!(2020, 1, 1)` produced
`error: 2020-01-01 is now in the past. Time to act on this!` and exit **101**. But it FAILS
OPEN THREE WAYS, verified in source and by execution: (1) `TODO_OR_DIE_SKIP=1` with the same
expired date → clean build, exit **0**; (2) any error in a network-backed macro (offline,
GitHub down, rate limit, TLS failure) → the check is skipped, not failed —
`issue_closed!("rust-lang","rust",44265)` on a long-closed issue built green, exit **0** in
3/3 clean runs, emitting only an `eprintln!` stderr backtrace that is NOT a rustc
diagnostic; (3) `Note that _none_ of the features are enabled by default` — a bare
dependency checks nothing at all. Source confirms: `src/lib.rs` `perform_check` returns
`Default::default()` on `Err`, emitting `compile_error!` only on `Ok(Some(msg))`.  
*Fit here:* Split the family. `after_date!` and `rust_version!` are locally decidable —
deterministic, offline, instant, and genuinely adoptable.
`issue_closed!`/`pr_closed!`/`crates_io!` require network at build time and degrade to green
when they cannot reach it, which disqualifies them from an offline deterministic tier and,
worse, makes them unreliable anywhere: a gate that is green both when the condition has not
fired and when the check could not run is not a gate.  
*Sources:* https://docs.rs/todo-or-die/latest/todo_or_die/ (fetched 2026-09-14) — five
macros, each 'Trigger a compile error if ...' ·
https://raw.githubusercontent.com/davidpdrsn/todo-or-die/main/src/lib.rs (fetched
2026-09-14) — doc comment: 'If you're offline or GitHub is down you can still build. If the
macros hit some kind of error a warning will be printed but they wont trigger a compile
error.'; 'Note that _none_ of the features are enabled by default.'; and `perform_check` at
lines ~227-256 showing `TODO_OR_DIE_SKIP` early-return and `Err(err) => { eprintln!(...) }`
with no compile_error · https://crates.io/api/v1/crates/todo-or-die (fetched 2026-09-14) —
max_version 0.1.2 published 2021-09-17T21:08:38Z, 29,827 total downloads, 113 recent ·
https://rubygems.org/api/v1/gems/todo_or_die.json (fetched 2026-09-14) — version 0.1.1,
674,927 total downloads, version created 2022-07-01T20:34:19Z ·
https://github.com/searls/todo_or_die (rendered HTML via WebFetch 2026-09-14) — 361 stars,
12 forks, 'Write TODOs in code that ensure you actually do them'; raises
TodoOrDie::OverdueError at class load; logs to Rails.logger.warn in production ·
https://github.com/davidpdrsn/todo-or-die (rendered HTML via WebFetch 2026-09-14) — 590
stars, 6 forks · local execution, rustc/cargo 1.94.1, todo-or-die 0.1.2, 2026-09-14 — exits
101 / 0 / 0 observed

**mdBook `{{#include}}` transclusion — FAILS OPEN, and more broadly than the filed issue
says (CORRECTED)**  
*Mechanism:* A book chapter names a file (optionally an `ANCHOR:`/`ANCHOR_END:` region) and
the preprocessor splices current content in at render time, so the rendered book cannot
contain a stale copy.  
*Why leaders use it:* Transclusion removes the independent claim entirely — there is nothing
left to contradict the source. It is a core feature of Sphinx (`literalinclude`),
Asciidoctor/Antora (tagged includes) and mdBook, and mdBook renders the Rust project's own
books.  
*Failure mode:* EXECUTED 2026-09-14 with mdbook v0.5.4, and the result is WORSE than issue
#1094 reports. (a) Missing FILE: logs `ERROR Error updating "{{#include
../../does-not-exist.toml}}" ... No such file or directory`, then `INFO HTML book written`,
**BUILD_EXIT=0** — and the literal directive text `{{#include ../../does-not-exist.toml}}`
is rendered into the published HTML as visible prose. (b) Missing ANCHOR in a file that
EXISTS — the classic drift case, someone renames or deletes the `ANCHOR:` marker:
**completely silent**. No ERROR, no WARN, exit **0**, and the transcluded paragraph renders
as nothing at all. The book builds clean and green with the content simply gone. Case (b) is
not what #1094 describes and I found no issue covering it.  
*Fit here:* The strongest negative finding in this dive. Transclusion is the mechanism
people reach for FIRST because it looks like it removes the drift problem by construction,
and in the most-cited implementation it removes the drift SIGNAL instead. If this repo ever
adopts an include/anchor scheme for SKILL.md, the anchor-missing case must be the loudest
failure in the system, because it is the one that looks like success.  
*Sources:* local execution, mdbook v0.5.4 installed via `cargo install mdbook --locked`,
2026-09-14 — BUILD_EXIT=0 observed for both the missing-file and missing-anchor cases ·
https://github.com/rust-lang/mdBook/issues/1094 (fetched 2026-09-14) — 'Include directives
to missing files do not return error', state OPEN, opened 2019-11-11; reporter: 'These
errors don't result in returning an error code from the process, so we missed them in CI.' ·
https://github.com/rust-lang/mdBook/pull/2277 (fetched 2026-09-14) — 'preprocess/links: fail
for invalid links', state OPEN (not merged), opened 2023-12-29, last activity 2026-08-21,
has merge conflicts awaiting author action

**Generate-and-check over a marker-delimited region — Cog `--check` (VERIFIED)**  
*Mechanism:* A generator writes content into the checked-in file between markers. `--check`
re-runs the generator and fails if the committed bytes differ from what would be produced
now — `gofmt -l` discipline applied to prose.  
*Why leaders use it:* It gates the checked-in artifact rather than the rendered one, so the
failure surfaces in review as a diff rather than at publish time, and the fix is mechanical
(`cog -r`).  
*Failure mode:* EXECUTED 2026-09-14 (cogapp 3.6.0), resolving what the scout could not. A
stale generated region printed `Checking doc.md  (changed)` / `Check failed` and exited
**5**. After `cog -r`, `--check` printed `Checking doc.md` and exited **0**. The value 5
comes from `CogCheckFailed` in `cogapp/cogapp.py` (`except CogCheckFailed as err: ... return
5`), alongside 2=usage, 3=generated-error, 4=user-exception, 1=other. IMPORTANT: the exit
code is NOT documented on cog's docs site — `--check` is described only as 'Check that the
files would not change if run again.' So depend on non-zero, never on 5 specifically.  
*Fit here:* Directly adoptable and already half-adopted here:
`evals/cheap/check-testing-doc.sh` is this pattern hand-rolled for exactly one document,
comparing docs/testing.md's LIVE-INVENTORY block against parsed workflow job names and
eval-pack directories in BOTH directions. Generalising that bidirectional compare to any
marker-delimited region in any instruction file is the cheapest real upgrade available, and
it needs no new dependency.  
*Sources:* local execution, cogapp 3.6.0 via pip, 2026-09-14 — exit 5 then exit 0 observed ·
/usr/local/lib/python3.11/dist-packages/cogapp/cogapp.py lines ~809-832 (read 2026-09-14) —
`except CogCheckFailed as err: self.prerr(err); return 5` ·
https://cog.readthedocs.io/en/latest/running.html (fetched 2026-09-14) — documents --check,
--check-fail-msg, --diff; exit status NOT documented

**Snippet-to-code coupling with history-aware re-anchoring — Swimm (CLAIMED)**  
*Mechanism:* Docs embed 'smart tokens' and snippets bound to source locations. On each
commit the tool replays git history to decide what happened to each bound region — moved,
trivially renamed, or gone — and either re-anchors and auto-updates the doc, or marks it out
of date.  
*Why leaders use it:* It persists the binding at authoring time, so drift is detected by
diffing rather than by re-deriving 'what did this claim point at' on every run.  
*Failure mode:* The mechanism description is CLAIMED (vendor engineering blog, not
independently reproducible). The quotes are verbatim and confirmed: 'it's completely
optional to block merging pull requests that have outstanding issues.'; 'Did the code just
move?'; 'Have any smart tokens or paths that Swimm has been taught to monitor changed?'; 'If
you wondered why Swimm won't work with "shallow" clones of repositories, this is why: we
need to be able to analyze the full history.' Post dated 30 Dec 2021. Semantically it tracks
the IDENTITY of a region, not its meaning — a function rewritten to do the opposite thing
while keeping its shape re-anchors happily and the prose stays green.  
*Fit here:* Low, and now lower. The honest ceiling remains the vendor's own concession:
best-in-class commercial tooling defaults to advisory. Note the shape mismatch with this
repo — Swimm needs full clone history as its signal, which is the opposite of a cheap
offline tier.  
*Sources:* https://swimm.io/blog/how-does-swimm-s-auto-sync-feature-work (fetched
2026-09-14; post dated 30 Dec 2021) — all quotes above verified verbatim · https://swimm.io/
(fetched 2026-09-14) — current headline 'Agentic modernization, delivered. Accurate,
complete, on time'; positioning is legacy/mainframe/monolith modernization; Auto-sync and
doc-drift detection are not mentioned · https://docs.swimm.io/ (fetched 2026-09-14) — still
describes a documentation product ('an AI coding assistant helping developers quickly
understand big, complex codebases—and seamlessly capture knowledge to fill in any
documentation gaps') with a Continuous Integration nav section; 'Auto-sync' does not appear
in the navigation

**Build provenance attestations — SLSA / in-toto / GitHub artifact attestations (VERIFIED)**  
*Mechanism:* The build platform emits a signed statement describing how an artifact was
produced — build definition, externalParameters, and the resolved source repo URI and commit
in `resolvedDependencies` — signed via Sigstore and recorded in a transparency log.  
*Why leaders use it:* It is the strongest existence-and-origin guarantee the industry ships,
and it is first-party in npm publish and GitHub Actions, so the marginal cost is near zero.  
*Failure mode:* What is ATTESTED and what is VERIFIED are different sets, and the gap is the
finding. Attested: the build definition, the untrusted externalParameters, and the resolved
source commit. Verified by `gh attestation verify`: 'the identity of the actor that produced
the attestation' and 'the expected attestation predicate type', checked against the
certificate's SourceRepository, SourceRepositoryOwner and SAN fields — and the command
REQUIRES `--owner` or `--repo`, i.e. the consumer must already know what to expect. Nothing
verifies automatically: verification is an explicit command a consumer chooses to run, and
an unverified attestation changes nothing. The spec is explicit that externalParameters 'are
untrusted; they MUST be included in the provenance and MUST be verified downstream' — the
obligation is pushed to a consumer who may never discharge it.  
*Fit here:* Shape, not substance. Provenance proves HOW something was built and says nothing
about what the source asserts — it stops at exactly the same wall as a path-existence check,
with a signature on it. The transferable idea for a claim ledger is the predicate model plus
the discipline of naming which fields are untrusted-and-must-be-verified-downstream. The
cautionary idea is that a gate nobody is required to run is documentation, not enforcement.  
*Sources:* https://slsa.dev/spec/v1.0/provenance (fetched 2026-09-14) — 'an attestation that
a particular build platform produced a set of software artifacts through execution of the
buildDefinition'; externalParameters 'are untrusted; they MUST be included in the provenance
and MUST be verified downstream'; source URI + commit digest belong in resolvedDependencies
· https://cli.github.com/manual/gh_attestation_verify (fetched 2026-09-14) — 'Verify the
integrity and provenance of an artifact using its associated cryptographically signed
attestations'; validates 'the identity of the actor that produced the attestation' and 'the
expected attestation predicate type'; requires --owner or --repo ·
https://docs.npmjs.com/generating-provenance-statements (scout, 2026-09-14) — npm CLI
9.5.0+, Sigstore-signed, public transparency ledger

**LLM-in-CI doc-drift review — doc-drift, driftcheck (VERIFIED)**  
*Mechanism:* On each diff an LLM is given the code change plus candidate docs (driftcheck
has the model generate targeted ripgrep queries first, then searches in parallel) and asked
to identify contradictions.  
*Why leaders use it:* It is the only shipped category that attempts the semantic half —
whether prose is still SUPPORTED, not merely whether its targets exist.  
*Failure mode:* The scout's load-bearing negative HOLDS and I could not refute it: neither
repo publishes precision, recall, accuracy, false-positive rate, or any benchmark. Adoption
confirmed at hobby scale — doc-drift 0 stars / 7 commits, driftcheck 6 stars / 14 commits
(rendered GitHub HTML, 2026-09-14). CORRECTION to the scout's characterisation: both BLOCK
by default rather than merely reporting. doc-drift's `DRIFT_FAILS_BUILD` defaults to `true`;
driftcheck blocks pushes unless `allow_push_on_error = true` (bypassable with `git push
--no-verify`). That makes them worse, not better: a gate that can go red with no measured
precision is a gate teams learn to override.  
*Fit here:* Fails this repo's own standard. The marketplace AGENTS.md already warns that the
behavioural tier proves 'a model given the skill changes its behaviour', not that the change
is right. An unevaluated blocking LLM check is that error promoted to a merge gate.  
*Sources:* https://github.com/jbrockSTL/doc-drift (rendered HTML via WebFetch 2026-09-14) —
0 stars, 7 commits; 'Catch stale docs on every PR using LLMs and GitHub Actions';
DRIFT_FAILS_BUILD default true; no evaluation numbers published ·
https://github.com/deichrenner/driftcheck (rendered HTML via WebFetch 2026-09-14) — 6 stars,
14 commits; 'Conservative by default — Only flags clear, factual errors to minimize false
positives'; blocks pushes unless allow_push_on_error; no evaluation numbers published · git
ls-remote confirmed both repos exist and resolve, 2026-09-14

**Learned comment/code inconsistency detection — AAAI 2021 and its 2024-2026 research line
(CORRECTED)**  
*Mechanism:* A model trained on paired comment/code edit histories predicts, at commit time,
whether a code change has rendered the associated comment inconsistent — classifying
support, not any surface property.  
*Why leaders use it:* Nobody does, in production. It is named because it targets the
decisive question head-on and therefore marks the honest ceiling.  
*Failure mode:* I tried to refute 'no shipped descendant' and FAILED — the claim stands. No
production toolchain ships a trained comment/code inconsistency classifier. But a SECOND
scout claim does not survive: the line is neither dormant nor evaluation-free. Active
follow-on work with published metrics includes C4RLLaMA (ICSE 2025, reported 65.0% correct
comment updates just-in-time and 55.9% post hoc), CCISolver, and FSE-2024-companion
LLM+program-analysis work. The correct statement is: the research line is active and
publishes numbers; no descendant is shipped; and the tools that ARE shipped (doc-drift,
driftcheck, and AI reviewers generally) are prompted LLMs that publish nothing.  
*Fit here:* None directly, and that is the point: any design assuming a semantic gate is
buildable today assumes something the field has not delivered. The usable inference is the
inverse — restate claims in checkable form at authoring time, because the after-the-fact
semantic check does not exist.  
*Sources:* https://arxiv.org/abs/2010.01625 (fetched 2026-09-14) — Panthaplackel, Li,
Gligoric, Mooney; v1 2020-10-04, v2 2020-12-26; 'Accepted in AAAI 2021'; abstract reports no
numeric metrics, only 'outperforms multiple baselines by significant margins' ·
https://conf.researchr.org/details/icse-2025/icse-2025-research-track/10/Code-Comment-Inconsistency-Detection-and-Rectification-Using-a-Large-Language-Model
(via search, 2026-09-14) — C4RLLaMA, ICSE 2025 ·
https://dl.acm.org/doi/10.1145/3663529.3664458 (via search, 2026-09-14) — 'Detecting Code
Comment Inconsistencies using LLM and Program Analysis', FSE 2024 companion · git ls-remote
https://github.com/panthap2/deep-jit-inconsistency-detection — artifact repo resolves,
2026-09-14

**Context rot in AI configuration artifacts — the primary source the scout missed
(VERIFIED)**  
*Mechanism:* Treude & Baltes apply an existing README/wiki consistency checker to CLAUDE.md
/ AGENTS.md / .cursorrules files across a statistically representative sample of 356
repositories, and argue the decades-old documentation-consistency toolbox is the immediate
starting point for detecting staleness in AI configuration files.  
*Why leaders use it:* This is the closest published work to what this repository actually
is, and it supplies the one number the scout said did not exist: a measured base rate for
staleness in exactly this artifact class.  
*Failure mode:* Preliminary and roadmap-shaped. Finding: 'applying an existing README/wiki
consistency checker to a statistically representative sample of 356 repositories identifies
stale code element references in 23.0% of repositories'. The abstract does not specify which
checker, nor define 'stale code element reference' precisely — from the framing it is
reference-existence (a named code element no longer present), i.e. category (b), not
semantic support. I could not obtain the full paper's methodology in this pass.  
*Fit here:* High and immediate. It validates the cheapest possible gate — 'every code
element named in an instruction file still exists' — with an external measurement showing
roughly one repository in four would go red today. That is a far better justification for
adopting an existence check than any vendor claim in this dive, and it is exactly the check
an offline deterministic tier can run.  
*Sources:* https://arxiv.org/abs/2606.09090 (fetched 2026-09-14) — 'Context Rot in
AI-Assisted Software Development: Repurposing Documentation Consistency for AI Configuration
Artifacts', Christoph Treude and Sebastian Baltes, submitted 2026-06-08; abstract quoted
above

**Implications:**
- WHICH MECHANISMS THIS REPO COULD ADOPT IN THE OFFLINE CHEAP TIER — the filter is brutal
  and only four survive. The tier must be deterministic, network-free, and fast, which
  immediately disqualifies: todo-or-die's issue_closed!/pr_closed!/crates_io! (network at
  build time, and green when unreachable), Swimm (needs full clone history and is a
  commercial service that no longer markets the feature), build provenance (needs a build
  platform and a signing identity), LLM doc-drift review (non-deterministic, unevaluated,
  and the repo's own AGENTS.md already argues against trusting model judgement as a gate),
  and learned inconsistency detection (does not ship).
- ADOPTABLE 1 — generate-and-check, generalised (highest value, lowest cost). Cog's
  `--check` is exit 5 on drift and 0 on agreement, executed here; the repo already owns a
  hand-rolled instance in evals/cheap/check-testing-doc.sh, which compares docs/testing.md's
  LIVE-INVENTORY block against parsed workflow names and eval-pack directories in both
  directions. Generalising that one-off into a marker-delimited regenerate-and-compare over
  any instruction file adds no dependency, stays offline, and converts prose regions from
  asserted to derived. The bidirectional property is the part worth preserving: forward-only
  catches additions, reverse catches a doc describing something that no longer exists.
- ADOPTABLE 2 — reference-existence checking over instruction files, justified by an
  external measurement rather than by taste. The repo already does this for AGENTS.md paths
  and relative markdown links (sections 7, 7b, 7c). Treude & Baltes (arXiv 2606.09090,
  2026-06-08) applied a README/wiki consistency checker to 356 representative repositories
  and found stale code element references in 23.0% — the base rate for exactly this artifact
  class. Extending the existing path checks to named code ELEMENTS (a function, a flag, a
  script's documented subcommand) is the same machinery aimed one level deeper, and there is
  now published evidence it fires on roughly a quarter of real repositories.
- ADOPTABLE 3 — `after_date!` semantics, reimplemented locally in ten lines of bash or
  Python. The todo-or-die family splits cleanly: date and toolchain-version predicates are
  locally decidable, and everything else needs the network. A cheap-tier check that scans
  shipped prose for a machine-readable expiry marker and fails when the date has passed is
  deterministic, offline, instant, and has no dependency — and unlike the crate it has no
  TODO_OR_DIE_SKIP, no default-off feature flags, and no error path that degrades to green.
  The repo's corpus already flagged the need ('any adopted mechanism naming an API needs an
  expiry this research cannot set'); this is the shipped shape of that expiry, minus the
  three fail-open holes verified above.
- ADOPTABLE 4 — executable prose via doctest's testfile(), if any claim here is worth
  restating as code. `doctest.testfile()` runs a plain text file that 'doesn't need to
  contain a Python program', and the repo already ships stdlib-Python cheap checks. This is
  the only shipped mechanism that makes a free-standing prose file fail a build without a
  compiler in the loop. Its ceiling is the family's ceiling: it checks only the part of the
  claim restated as runnable code.
- THE DESIGN LESSON THAT OUTRANKS ALL FOUR — fail-open is the norm, not the exception, and
  it is invisible. Of the mechanisms examined, mdBook fails open twice (loudly on a missing
  file, SILENTLY on a missing anchor), todo-or-die fails open three ways (env var, network
  error, default-off features), Go silently downgrades when `// Output:` is omitted, Elixir
  and Python check nothing that was not explicitly registered, nbval's lax mode checks only
  marked cells, provenance verifies nothing unless a consumer chooses to run a command, and
  Swimm concedes blocking is 'completely optional'. The single counter-example is the Rust
  README recipe, which fails CLOSED on a deleted target because `include_str!` is a
  compile-time read. That is the property to copy. The companion note's rule — 'an edge is
  only worth adding if it comes with a command that re-derives it and a comparison that can
  go red' — needs one clause added: AND THE COMPARISON MUST GO RED WHEN IT CANNOT BE MADE. A
  gate that is green both when the claim holds and when the check could not run is not a
  gate; it is a comment with a CI badge. This repo's cheap tier already encodes the right
  instinct in its fail-closed plugin discovery, where a plugin with no eval pack turns the
  tier red rather than being skipped. Every mechanism adopted from this dive should be held
  to that same standard.
- IS 'EXPIRY' A SEPARATE AXIS FROM 'SUPPORT', OR A SPECIAL CASE? — Largely a special case,
  but along an axis that matters operationally, and the scout's framing needs both halves.
  THE CASE FOR SPECIAL CASE: formally, every expiring claim is a supported claim whose
  support predicate happens to mention the clock or an external registry.
  `after_date!(2026,1,1)` is 'the proposition THIS IS STILL BEFORE 2026-01-01 is no longer
  supported by the world'. `issue_closed!` is 'the proposition THIS ISSUE IS OPEN is no
  longer supported by GitHub'. Nothing about the checking machinery differs — you re-derive
  a fact, compare it to what the doc asserted, and go red on mismatch. Collapse the two and
  you lose nothing logically, and you gain a uniform mechanism. THE CASE FOR SEPARATE AXIS:
  what differs is the ORACLE and therefore the cost, determinism, and failure mode. Support
  checks read the repository, which is present, free, deterministic, and offline. Expiry
  checks read the world — a clock, a registry, an upstream tracker — which is absent,
  sometimes paid, non-deterministic, and unreachable from a hermetic tier. That distinction
  is not philosophical; it is precisely what makes `after_date!` adoptable here and
  `issue_closed!` not, and it is precisely why `issue_closed!` fails open while
  `after_date!` cannot. There is also a real difference in TRIGGER: a support check has an
  event to hang on (the diff that might have invalidated the claim), whereas an expiry check
  has no event at all — nothing in the repository changes when an upstream issue closes, so
  the check must be run speculatively on a schedule or on every build. VERDICT: expiry is a
  special case of support, distinguished by whether the oracle is inside the artifact or
  outside it — and that single distinction predicts every property this dive cares about.
  The useful taxonomy is therefore not support-versus-expiry but INTERNAL-ORACLE versus
  EXTERNAL-ORACLE claims. Internal-oracle claims can be gated in an offline deterministic
  tier and can be made to fail closed. External-oracle claims cannot be gated there at all,
  and every shipped attempt to gate them that I examined degrades to green when the oracle
  is unreachable. For this repo the practical rule follows directly: put internal-oracle
  checks in the cheap tier where they can fail closed, and keep external-oracle checks out
  of it entirely rather than importing a mechanism whose green means 'either fine, or I
  could not look'. The one external-oracle predicate that escapes this is the clock, because
  it is the only part of the world every machine already carries.

### Dive 4 — The measured ceiling on checking a claim against its source

**The measured ceiling on automated claim-to-source checking is ~77% balanced accuracy — and
'balanced accuracy' means the mean of TPR and TNR, so the chance floor is exactly 50%
(VERIFIED)**  
*Mechanism:* LLM-AggreFact unifies grounded-factuality datasets into one binary
supported/unsupported task and scores every system with BAcc = 0.5*(TP/(TP+FN) + TN/(TN+FP))
— verbatim from the MiniCheck paper. A constant predictor scores exactly 50.0; the
leaderboard's own weakest entry, Llama-3.2-1B-Instruct, scores 50.3, empirically confirming
the floor. The top entry, Bespoke-MiniCheck-7B, scores 77.4. In informedness terms (Youden's
J = 2*BAcc - 1) the best claim-to-source checker on earth sits at J = 0.548: it closes just
over half the distance between coin-flip and perfect.  
*Why leaders use it:* BAcc is exactly the pair eval-ladder already demands of every rung-3
judge ('TPR and TNR against held-out human labels, or it is an opinion'), collapsed to one
number. The benchmark exists because raw agreement lies under class imbalance — the same
reason eval-ladder forbids it. So the field's headline number is directly commensurable with
eval-ladder's own validation metric, which is what makes it quotable as a ceiling.  
*Failure mode:* Quoting 77.4 without the 50% floor makes it sound like a B-minus. It is not:
it is 27 points of signal over chance. And it is an average over 11 datasets whose
per-dataset spread is enormous — the same top system scores 88.0 on REVEAL and 59.2 on
ExpertQA.  
*Fit here:* eval-ladder rung 3 currently says a judge proves 'anything beyond its measured
TPR/TNR' is unprovable, and 'ship only when both TPR and TNR clear the bar you set in
advance' — but gives no guidance on what bar is attainable. The ceiling belongs in that
sentence, with the chance floor attached, or the number is the same kind of unbounded claim
the skill exists to forbid.  
*Sources:* https://arxiv.org/html/2404.10774v2 (MiniCheck, EMNLP 2024; v2 1 Oct 2024; BAcc
definition read verbatim 2026-09-14) · https://llm-aggrefact.github.io/ (leaderboard read
2026-09-14; embedded Next.js payload parsed: 39 models, top = Bespoke-Minicheck-7B 77.4,
bottom = Llama-3.2-1B-Instruct 50.3)

**The headline average hides a per-dataset floor: on the hardest split, NO system on earth
beats 61% (VERIFIED)**  
*Mechanism:* Recomputing the average from the leaderboard's own embedded per-dataset table
across all 39 models: on ExpertQA (expert-domain long-form answers with attributed sources)
the scores run 49.9 to 61.0. Best = Qwen2.5-7B-Instruct at 61.0; Bespoke-MiniCheck-7B gets
59.2; GPT-4o gets 59.6. Every frontier model, every specialist model, all within 11 points
of chance. Meanwhile REVEAL (reasoning-chain entailment) runs to 89.6 and LFQA to 87.0. The
MiniCheck paper's own Table 2 shows the identical pattern (GPT-4: ExpertQA 59.2, CNN 66.7,
LFQA 83.1).  
*Why leaders use it:* Nobody uses this — it is the number the leaderboard's default view
averages away. The 11-dataset mean is what gets cited.  
*Failure mode:* ExpertQA is the split whose shape most resembles a claim about a technical
artifact: expert domain, long-form, synthesised, attributed. That is precisely where the
ceiling collapses to ~60. A judge validated on your easy cases and reported as '77%-class'
will be at ~60% on the cases you built it for.  
*Fit here:* Direct support for eval-ladder's existing 'name what each rung structurally
cannot prove'. The blind spot is not 'the judge is 23% wrong'; it is 'the judge's error rate
is a function of claim difficulty, and it approaches chance exactly where the claim is
hard'. A rung-3 judge must report per-difficulty-stratum TPR/TNR, not one pooled pair —
which is a concrete strengthening of judge-alignment.md.  
*Sources:* https://llm-aggrefact.github.io/ (full 39-model per-dataset table extracted from
page payload 2026-09-14; ExpertQA min 49.9 / max 61.0) · https://arxiv.org/html/2404.10774v2
(Table 2, read 2026-09-14)

**On contested cases — the only cases where a checker earns its cost — the ceiling falls to
chance (VERIFIED)**  
*Mechanism:* FaithBench (Vectara et al.) builds a benchmark exclusively from summaries where
popular SOTA hallucination detectors DISAGREED with each other, then has human experts label
them with four grades (consistent / benign / questionable / unwanted). Detectors are then
re-scored on those hard cases. Table 2 verbatim: GPT-4-Turbo zero-shot 57.65 BAcc, GPT-4o
56.29, HHEM-2.1 55.68, MiniCheck-RoBERTa-L 55.03, MiniCheck-Deberta-L 54.95, True-Teacher
54.21, GPT-4 53.45, HHEM-2.1-Open 51.37, MiniCheck-Flan-T5-L 50.50, True-NLI 50.62, HHEM-1
48.96, GPT-3.5-Turbo 44.91. Paper's words: 'The balanced accuracies of all detectors are
near 50%.' Two entries are BELOW chance. Human inter-annotator agreement on the clean binary
(consistent vs unwanted) was 0.748.  
*Why leaders use it:* Vectara built it to stop its own leaderboard being read as solved; the
paper notes detectors 'are known to have an accuracy below 80% on benchmarks such as
AggreFact and RAGTruth' and that existing benchmarks are too easy.  
*Failure mode:* The benchmark is adversarially sampled by construction, and the paper says
so plainly: 'it is important to keep in mind that they are only true for the challenging
samples. It may not be true for all samples.' So near-50 is not the average-case number. But
it IS the number for the cases a gate exists to adjudicate — nobody deploys a checker for
claims everyone already agrees about.  
*Fit here:* This is the sharpest available statement of what eval-ladder rung 3 structurally
cannot prove. A judge's pooled BAcc is dominated by easy negatives; its marginal value is
measured on contested cases, where the field's ceiling is ~58 and several shipped detectors
are at or below coin-flip. Any rung-3 gate whose fixture set was not adversarially sampled
is reporting the easy number.  
*Sources:* https://arxiv.org/html/2410.13210v1 (FaithBench, arXiv 17 Oct 2024, Vectara Inc.
et al.; Table 2 and the 'near 50%' sentence read verbatim 2026-09-14)

**Prose-trained claim-to-source checkers do not transfer to CODE evidence — the one direct
measurement puts them at 0.17 span-F1 (VERIFIED)**  
*Mechanism:* A July 2026 preprint builds the first unified span-level
hallucination-detection benchmark spanning code (from SWE-bench), developer-tool output,
structured documents, README markdown, Wikipedia, plus RAGTruth and PsiloQA. Hallucinations
are injected at exact character offsets from grounded-correct answers; the code test split
is additionally review-validated. Per-source span-F1 (Table 2): README 0.866, Wikipedia
0.817, ACL chunks 0.749, tool output 0.719, RAGTruth 0.574, code-agent 0.602 — for their
purpose-built fine-tuned 2B detector. For the off-the-shelf prose-trained detector
LettuceDetect-large on the same code split: 0.17. For the best zero-shot LLM judge
(task-aware Nemotron-3-Ultra-550B prompt): 0.22; gpt-oss-120b: 0.177 on code vs 0.666 on
README. The paper names the answer-level faithfulness systems by name — 'HHEM-2.1-Open,
Lynx-8B, Granite-Guardian-4.1-8B, and MiniCheck-7B show the same tendency at answer level:
high recall but much lower precision on the hallucinated class.'  
*Why leaders use it:* It is brand new and barely adopted. Its value here is evidentiary, not
as a pattern to copy.  
*Failure mode:* Labels are mostly synthetic injection ('Most labels come from synthetic
injection... the code review is model-assisted rather than independently annotated by
multiple human annotators'), the authors are benchmarking their own successor model against
their own prior product, span-F1 is not balanced accuracy so it does not compare numerically
to 77.4, and there is no independent replication. Direction is well-supported; magnitude is
one data point.  
*Fit here:* This is the evidence that settles the code question for eval-ladder. Note the
ordering: README — prose ABOUT code — is the EASIEST source of all seven (0.866). Code as
evidence is the hardest (0.602 even when purpose-built for it; 0.17 off-the-shelf). A rung-3
judge reading docs is near the easy end; a rung-3 judge reading source is near the hard end,
and the two must not be reported with the same confidence.  
*Sources:* https://arxiv.org/abs/2607.00895 and https://arxiv.org/html/2607.00895v1 ('Beyond
Document Grounding: Span-Level Hallucination Detection over Code, Tool Output, and
Documents', Kovács, He, Liu, Boros, Tóth, Recski; KR Labs / MBZUAI / McGill; v1 1 Jul 2026;
abstract, Table 2, §6.4 and §8 Limitations read 2026-09-14)

**Formal verification of a natural-language claim, with the soundness gap named in the
vendor's own documentation (VERIFIED (caveats, scope, GA status, no accuracy number) /
CLAIMED (the 99% figure — see corrections))**  
*Mechanism:* Upload a source document; an LLM extracts formal logic rules plus a variable
schema and emits a fidelity report with coverage and accuracy scores grounding each rule
back to source statements. At runtime a model response is translated into that logic and
discharged by a solver, returning VALID / INVALID / SATISFIABLE / TRANSLATION_AMBIGUOUS /
TOO_COMPLEX with the rules and variable assignments that justify the verdict. Detect mode
only — it never blocks.  
*Why leaders use it:* It is the only shipped option that returns a proof rather than a
score, and the only one that tells you WHY. AWS targets regulated industries and compliance
scenarios needing auditable, mathematically verifiable responses.  
*Failure mode:* Named by AWS, verbatim, in 'What Automated Reasoning checks don't do': 'A
VALID result guarantees validity only for the parts of the input captured through policy
variables. Statements that fall outside the scope of your policy's variables are not
validated. For example, "I can submit my homework late because I have a fake doctor's note"
might be deemed valid if the policy has no variable to capture whether the doctor's note is
fake.' And in Limitations: 'The accuracy of validation depends on how well natural language
in user prompts and model responses can be translated to your policy's formal logic
variables. Automated Reasoning checks use foundational models to translate natural language
into logic representations.' The proof is real; the premises are guessed by an LLM. Also
English-US only, six regions, 5 MB / 50,000-character source cap, no streaming, TOO_COMPLEX
on non-linear arithmetic.  
*Fit here:* A rung between eval-ladder's 2 (code assertion) and 3 (LLM judge) that the
ladder does not have: solver-decided and proof-carrying, but only conditionally sound. Its
fidelity report is also a genuinely novel artifact — a measurement of how faithfully the
formal model represents the source, i.e. a gate that grades its own premises. Both are
absent from the ladder.  
*Sources:*
https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-automated-reasoning-checks.html
(read 2026-09-14; both caveats quoted verbatim; 'generally available in the following
Regions'; NO accuracy figure anywhere on the page) ·
https://aws.amazon.com/about-aws/whats-new/2025/08/automated-reasoning-checks-amazon-bedrock-guardrails/
(posted Aug 6, 2025 — GA date confirmed)

**Hosted claim-level grounding as a product, with zero published accuracy — all three
hyperscalers (VERIFIED (the absence, on all three primary pages))**  
*Mechanism:* Google checkGrounding: POST an answer candidate (<=4,096 tokens) plus up to 200
facts (<=10k chars each); returns a support score 'from 0 to 1 that indicates how grounded
an answer candidate is in the provided set of facts. It loosely approximates the fraction of
claims in the answer candidate that were found to be grounded', plus cited_chunks, a
claim-to-citation map, and a citation threshold (default 0.6). AWS Bedrock contextual
grounding: response-level grounding and relevance confidence scores with configurable 0-0.99
thresholds; explicitly coarse — 'If any one chunk is deemed relevant, the whole response is
considered relevant.' Azure AI Content Safety groundedness detection: Non-Reasoning (fast
binary) and Reasoning ('detailed explanations for detected ungrounded segments') modes,
tuned by domain (MEDICAL|GENERIC) and task (Summarization|QnA), plus an optional correction
feature (preview) returning a correctedText field.  
*Why leaders use it:* It is one API call, it is inside a GA product line, and it needs no
labelled corpus. Google advertises latency ('designed to be fast, with latency less than
500ms') rather than accuracy.  
*Failure mode:* CONFIRMED, load-bearing: none of the three pages publishes a single accuracy
figure of any kind — no precision, recall, TPR, TNR, F1, benchmark, or evaluation dataset.
Google publishes only a latency target. AWS publishes only threshold semantics. Azure
publishes only feature switches and four synthetic toy contradictions (Kevin vs Jane; 5% vs
4.5%; 1065 vs 1066; SuperWidget v2.1 vs v2.2) — every worked example is a surface-level
entity mismatch, not the multi-sentence synthesis case. Azure is English-only; its
correction feature is a grader that REWRITES the artifact to pass itself, so with correction
enabled it cannot function as a gate at all.  
*Fit here:* These are rung-3 judges sold as infrastructure that you cannot validate, because
the vendor will not tell you the error rate and you cannot see the model. By eval-ladder's
own bar a green support score of 0.9 is an unbounded claim. The ladder has no rung for 'a
hosted grader you call per claim' and does not name this tension. Azure's auto-correction is
also a shipped, automated instance of the ladder's 'tuning on the gate' integrity hazard —
the ladder names only the human form.  
*Sources:* https://docs.cloud.google.com/generative-ai-app-builder/docs/check-grounding
(read 2026-09-14) ·
https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html
(read 2026-09-14) ·
https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness
(ms.date 2025-11-21, updated_at 2026-06-05; read 2026-09-14)

**Factuality metrics disagree with each other, and their biases point in two named
directions (VERIFIED)**  
*Mechanism:* Re-evaluate five factuality metrics — gpt-4-turbo, gpt-3.5-turbo,
Bespoke-MiniCheck-7B, MiniCheck-FlanT5-Large, MiniCheck-RoBERTa-Large — across 11 datasets
(14 counting RAGTruth's four subsets), then probe for bias by ROUGE overlap (paraphrase) and
by R2-diff (whether the claim draws on distant parts of the source).  
*Why leaders use it:* It is a critique paper, not a tool. Published at ACL 2025; 8 citations
as of 2026-09-14.  
*Failure mode:* Verbatim from the abstract: the evaluators 'are inconsistent with each other
and often misestimate system-level performance' and 'exhibit biases against highly
paraphrased outputs and outputs that draw upon faraway parts of the source documents'.
Magnitudes from the body: for the two top-performing evaluators, pairwise IoU 'is less than
50% on 5 of the 14 datasets and less than 65% on 9 of 14'. On high-ROUGE (heavily copied)
text, 'evaluators can detect unattributable claims with high ROUGE only half the time' — TNR
collapses where the wording matches but the fact does not. On distant synthesis, 'when
R2-diff>0, there is a marked increase in the predictions of the label unattributable... The
rate is greater than 10% on 8 of 11 datasets'; chunking the document makes Bespoke-7B
predict 'attributable' 6% less often. Authors' own closing instruction: 'manually validate
the reliability of these metrics in their domain of interest before proceeding.'  
*Fit here:* This is the mechanism that explains why the code case must be worse, and it is
the sharpest correction to the ladder's implicit model of judge error. eval-ladder tells you
to measure YOUR judge's TPR/TNR; this paper shows a validated metric can still rank two
systems wrongly, and that its errors are directional, not random. The two named directions —
paraphrase and distant synthesis — are exactly the shape of a true cross-file claim about a
repository, i.e. the claim most worth making is the claim the checker is worst at.  
*Sources:* https://arxiv.org/abs/2501.14883 and https://arxiv.org/html/2501.14883v2 ('Verify
with Caution: The Pitfalls of Relying on Imperfect Factuality Metrics', Godbole & Jia, USC;
v1 24 Jan 2025, v2 30 Jan 2025; ACL 2025; abstract and body quoted 2026-09-14) ·
https://api.semanticscholar.org/graph/v1/paper/arXiv:2501.14883 (venue=ACL, citationCount=8,
read 2026-09-14)

**Unit tests that grade the GRADER, with pass rates that separate judges correlation cannot
(VERIFIED)**  
*Mechanism:* Enumerate 7 generator failure modes in grounded QA (irrelevant info on
answerable questions; failing to refrain on unanswerable ones; missing relevant info;
wrongly claiming unanswerable; unrelated info in adversarial cases; missing or wrong
citations; distorted or unsupported claims), then hand-write 144 unit tests across 16
situations pairing the SAME question with slightly varied answers and references, such that
a correctly calibrated judge must assign specific, DIFFERENT scores. A judge passes only by
discriminating between adjacent failure modes.  
*Why leaders use it:* Published at COLING 2025 (Muller, Loison, Omrani, Viaud; Illuin
Technology). 11 citations as of 2026-09-14 — genuinely research-only, essentially no
downstream adoption.  
*Failure mode:* Pass rates on the 144 tests: GPT-4 95.02%, GPT-4-turbo 92.59%, Gemini 1.0
Pro 83.22%, a finetuned Llama-3-8b 81.37%, Llama-3-70b 79.17%, Mixtral 8x22b 77.20%,
GPT-3.5-turbo 71.18%, Llama-3-8b 69.33%, and the purpose-built judge models Prometheus 2
8x7b 54.98% and Prometheus 2 7b 52.78%. The paper's finding: 'Strong correlation with GPT-4
does not imply good pass rate on unit tests' — open judges correlate well and calibrate
badly. It also names RAGAS specifically, showing faithfulness+answer-relevancy incorrectly
penalise faithfulness when irrelevant-but-accurate statements appear. Caveat: 144
hand-written cases in one domain is a fixture set, so eval-ladder's own 'defects it has no
fixture for' applies at full strength. Note also a tension — two of GroUSE's six metrics
(Answer Relevancy, Completeness) are Likert scales, which eval-ladder's judge-alignment.md
tells you to kill.  
*Fit here:* The strongest single import available. eval-ladder's rung 1 (mutate a known-good
baseline, assert rejection FOR THE RIGHT REASON) is exactly this construct — but the ladder
only ever points rung 1 at the system under test, never at the judge on rung 3. GroUSE is
rung 1 applied to rung 3, and it produces a finding the ladder's judge-validation recipe
would miss: eval-ladder already forbids raw agreement with HUMAN labels; GroUSE extends the
warning to agreement with a reference JUDGE, which is the cheap shortcut teams actually
take.  
*Sources:* https://arxiv.org/abs/2409.06595 and https://arxiv.org/html/2409.06595v3
('GroUSE: A Benchmark to Evaluate Evaluators in Grounded Question Answering'; v1 10 Sep
2024, v3 30 Jan 2025; COLING 2025; Table 3 read 2026-09-14) ·
https://api.semanticscholar.org/graph/v1/paper/arXiv:2409.06595 (venue=COLING,
citationCount=11, read 2026-09-14)

**Put the semantics in the QUESTION so a deterministic predicate can grade the answer — but
the predicate is fuzzy-thresholded, not exact-match (CORRECTED (scout described the grader
as string-matching; it is nearest-neighbour smoothed BLEU with a 0.8 threshold))**  
*Mechanism:* Verified from the paper body. Plant 10 'needle' functions at evenly spaced
depths (10%, 20%, ... 100%) through repository source arranged in topological/import order;
prompt GPT-4 to write a natural-language DESCRIPTION of each; give the model the description
and require it to return the function. Grading is a three-step deterministic pipeline: (1)
post-process to extract the first code block that tree-sitter confirms is syntactically
valid; (2) among ALL functions F in the context, the returned function f_o must be nearest
to the needle by smoothed BLEU; (3) BLEU(needle, f_o) must exceed a threshold, 'by default
0.8 in our work'. 500 tasks, 50 repositories, 5 languages (Python, C++, Java, TypeScript,
Rust), 33 models scored.  
*Why leaders use it:* It is the only worked example found of converting 'does the model
understand this repo?' — which everyone assumes needs a judge — into a mechanically
decidable assertion, by making the QUESTION carry the semantics instead of the grader. 49
citations as of 2026-09-14; part of the EvalPlus family with a public leaderboard.  
*Failure mode:* The grader is deterministic but NOT exact-match, and the 0.8 threshold is a
free, tunable parameter — a knob on the gate, which is an integrity hazard eval-ladder
names. The nearest-neighbour step also only works because the correct answer is guaranteed
to be verbatim present in the context; it does not generalise to a claim whose support must
be synthesised. Structurally it proves locate-by-description and nothing more: not what the
function DOES, not how it interacts with the rest of the repo, not whether a claim about the
repo is supported. Verified findings: a small gap remains between best open and proprietary
models; per-language performance differs; and 'models may understand code better without
comments' (comment-free mode can raise scores — e.g. deepseek-coder-33b 48.4 -> 75.4).  
*Fit here:* The worked example for eval-ladder's 'descend before you ascend' in the code
domain. The transferable move is: describe a thing in prose, require the exact artifact
back, grade by predicate — which sidesteps the entire ~77% / 0.17 entailment ceiling for any
claim that can be phrased as 'the artifact I am describing is X'. The honest caveat to ship
with it is that the predicate has a similarity threshold, so it is rung 2 with a dial, not
rung 2 with a proof.  
*Sources:* https://arxiv.org/html/2406.06025v1 §3.2 Score computation and Table 1 (read
2026-09-14) · https://arxiv.org/abs/2406.06025 (RepoQA, Liu, Tian, Daita, Wei, Ding, Wang,
Yang, Zhang; v1 10 Jun 2024) ·
https://api.semanticscholar.org/graph/v1/paper/arXiv:2406.06025 (citationCount=49, read
2026-09-14)

**Implications:**
- WHAT NUMBER EVAL-LADDER SHOULD STATE ON RUNG 3 — not one number, three, because a single
  figure is exactly the over-claim the skill exists to forbid. (a) HEADLINE: 'The best
  claim-to-source checker publicly measured scores about 77% balanced accuracy averaged over
  11 grounded-factuality datasets (LLM-AggreFact leaderboard, Bespoke-MiniCheck-7B 77.4,
  read 2026-09-14; Qwen3-32B 77.6 in HalluGuard Table 1, Oct 2025). Balanced accuracy is the
  mean of TPR and TNR, so chance is exactly 50 — this is informedness 0.55, not a B-minus.'
  That framing matters more than the digits: eval-ladder already demands TPR and TNR
  separately, and BAcc is literally their mean, so the field's ceiling is denominated in
  eval-ladder's own currency. (b) FLOOR: 'On the hardest of those 11 splits (ExpertQA —
  expert-domain, long-form, attributed) no system among the 39 on the leaderboard exceeds
  61.0, and the top system scores 59.2. The 11-dataset average hides a 30-point spread.' (c)
  CONTESTED-CASE FLOOR: 'On FaithBench, built exclusively from cases where SOTA detectors
  disagreed, the best detector scores 57.65 balanced accuracy and several shipped detectors
  fall at or below chance.' Ship (a) with (b) and (c) attached or not at all — quoting 77
  alone reproduces the failure mode the skill is about.
- AND STATE THE DATE AND THE DECAY. The leaderboard has no last-updated stamp on the page
  and its repository has not been touched since 2025-09-08; no 2026 frontier model appears
  among its 39 entries. So the honest form is 'the last public measurement of this ceiling,
  ~mid-2025, was about 77%' — with the standing caveat that nobody has scored current
  frontier models on it. A ceiling asserted without a read date is the same species of
  unbounded claim as a green check without a blind spot.
- YES — 77% IS AN OPTIMISTIC UPPER BOUND FOR CODE, AND THIS IS NOW MEASURED RATHER THAN
  ARGUED. Four independent lines converge. (1) DISTRIBUTION: all eleven LLM-AggreFact
  datasets are prose — AggreFact (CNN/DM and XSum news), TofuEval (MediaSum interviews,
  MeetingBank meetings), WiCE (Wikipedia), Reveal (reasoning chains), ClaimVerify (search
  answers), FactCheck-GPT (LLM output), ExpertQA, LFQA (ELI5), RAGTruth (CNN/DM, news, MS
  MARCO, Yelp). Not one is code. Verified against both the MiniCheck paper and Godbole &
  Jia's independent enumeration. (2) DIRECT MEASUREMENT: on the first code-grounded
  span-level benchmark (arXiv 2607.00895, Jul 2026), a prose-trained detector scores 0.17
  span-F1 on code-agent evidence and the best zero-shot LLM judge 0.22, versus 0.67-0.87 for
  the same systems on prose sources; a detector purpose-built for code still only reaches
  0.602 there against 0.866 on README. The paper names MiniCheck-7B among the answer-level
  systems showing 'high recall but much lower precision on the hallucinated class' over code
  evidence. (3) MECHANISM: Godbole & Jia measured that factuality metrics are biased against
  highly paraphrased claims and against claims drawing on faraway parts of the source — 'the
  rate is greater than 10% on 8 of 11 datasets' for the distant-synthesis case. A claim
  about a repository is maximally both: prose-versus-code is not paraphrase but
  cross-modality, with near-zero lexical overlap, and a true claim about a codebase almost
  always integrates evidence across files. Both measured bias vectors point the same way.
  (4) TASK SHAPE: the code split is hardest because, in the paper's words, 'the context is
  long, the answer often contains new code, and some errors are intent mistakes rather than
  simple factual contradictions' — intent mistakes are not entailment failures at all, so
  the entailment framing does not even reach them.
- THE COUNTER-ARGUMENT, STATED FAIRLY, AND WHY IT DOES NOT RESCUE THE NUMBER. Code is more
  regular than prose and far more of it is decidable by predicate, so a well-built repo gate
  should push most checks down to rung 2 (RepoQA's construction is the proof of concept: put
  the semantics in the question, grade by predicate). That is real — but it cuts the wrong
  way for optimism. Descending the easy claims to rung 2 leaves rung 3 holding only the
  RESIDUE: the subjective, synthesised, cross-file claims. That residue is the
  ExpertQA/FaithBench/distant-synthesis region where the measured ceiling is ~60 and falling
  toward chance, not the pooled 77. A judge gets the pooled number only if you feed it the
  pooled distribution, and a well-designed ladder by construction does not.
- ONE DISTINCTION EVAL-LADDER SHOULD DRAW EXPLICITLY, BECAUSE THE DATA DRAWS IT SHARPLY:
  prose ABOUT code is the EASIEST grounding source measured (README, 0.866 span-F1 — higher
  than Wikipedia), while code AS evidence is the hardest (0.602 purpose-built, 0.17
  off-the-shelf). A rung-3 judge checking a claim against a design doc, a CHANGELOG or a
  README sits near the easy end; the same judge checking the same claim against the source
  sits near the hard end. Reporting both at one confidence is an over-claim of roughly 5x in
  F1, and it is the exact mistake a repo-knowledge gate is most likely to make, because both
  artifacts live in the same repository.
- CONCRETE EDITS THIS DIVE SUPPORTS. (i) Rung 3's 'Structurally cannot' cell currently reads
  'Anything beyond its measured TPR/TNR' — correct but unbounded; add the attainable bar,
  dated. (ii) judge-alignment.md says 'Ship only when both TPR and TNR clear the bar you set
  in advance' — it should say that a bar above the field's measured ceiling is not a bar but
  a wish, and that the ceiling for claim-to-source entailment is ~0.77 BAcc on prose and
  unmeasured-but-far-lower on code. (iii) Add stratified reporting: one pooled TPR/TNR pair
  is not enough when the error rate is a function of claim difficulty; report the
  contested-case stratum separately, since that is where the judge earns its cost and where
  the ceiling collapses. (iv) Add GroUSE's construction as rung-1-pointed-at-rung-3, with
  its own finding attached: correlation with a reference judge does not imply calibration
  (GPT-4 95.0% on the 144 unit tests; Prometheus 2 7b 52.8%). (v) Name the
  hosted-grounding-API case: a rung-3 judge you cannot validate because the vendor publishes
  no error rate — confirmed absent on all three hyperscaler doc pages as of 2026-09-14 — and
  name Azure's auto-correction as the automated form of the tuning-on-the-gate hazard, since
  a corrected response is guaranteed to pass the check that corrected it.

### Dive 5 — The context-file null result — what the paper actually says

**CTXbench: the context-file null result, as actually written (VERIFIED)**  
*Mechanism:* Gloaguen, Mundler, Mueller (LogicStar.ai), Raychev (LogicStar.ai), Vechev (ETH
Zurich). arXiv:2602.11988. Two benchmarks, three arms. CTXbench = 138 instances mined from
5,694 PRs across 12 niche Python repos that carry developer-committed AGENTS.md/CLAUDE.md;
arms None / LLM-generated / Dev-committed. SWE-bench Lite = 300 tasks, 11 popular Python
repos, only two arms (None / LLM) because none of those repos have dev context files. Four
agent+model pairs: Claude Code+Sonnet-4.5, Codex+GPT-5.2, Codex+GPT-5.1-mini, Qwen
Code+Qwen3-30b-coder, temperature 0, 'We sample completions for each agent once' (single run
per instance, no seed variance). Verbatim v2 abstract: 'Surprisingly, we find that providing
context files does not generally improve task success rates, while increasing inference cost
by over 20% on average.' and 'we find that while instructions in the context files are well
followed by coding agents, repository overviews, although popular and recommended by model
providers, are not helpful.' and 'We conclude that while context files are useful for
specifying non-standard coding practices, any attempts to improve performance should be
rigorously evaluated before deployment.'  
*Why leaders use it:* It is the only large-scale controlled ablation of real,
developer-committed context files. Its endorsed residue is narrow and specific:
instruction-following is real and large (uv invoked 1.6x/instance when named in the file vs
<0.01x when not; repo-specific tools 2.5x vs <0.05x), so a context file that carries
non-derivable procedure demonstrably changes agent behaviour. What it does NOT buy is
resolve rate on SWE-bench-style issue tasks.  
*Failure mode:* The headline is a NON-SIGNIFICANT result, not a demonstrated absence of
effect, and the paper says so in its own conclusion: 'LLM-generated context files have a
marginal negative effect on task success rates, while developer-written ones provide a
marginal performance gain, neither statistically significant.' Table 5 standard errors on
CTXbench are +/-3.8 to +/-4.3 percentage points per cell on n=138 with one sample each;
every treatment effect discussed (0.5pp, 2pp, 2.4pp) sits inside one standard error.
Cochran-Mantel-Haenszel p-values (Table 3): SWE-bench None-vs-LLM p=0.87, CTXbench
None-vs-LLM p=0.37, CTXbench None-vs-Dev p=0.21. Only LLM-vs-Dev reaches p=0.038. The study
is underpowered to exclude an effect of roughly +/-8pp. Citing it as 'context files do not
work' overstates it; the honest reading is 'no detectable effect at this n, on this task, in
this language'.  
*Fit here:* Direct: this is the falsifiable-criteria argument applied to instruction files.
The paper's closing recommendation is literally Redgate's premise — rigorously evaluate
before deployment.  
*Sources:* https://arxiv.org/abs/2602.11988 (abs page fetched 2026-09-14; v1 12 Feb 2026, v2
23 Jun 2026) · https://arxiv.org/html/2602.11988v2 (full text fetched 2026-09-14; Sec 4.1
setup, Sec 4.2, Table 2, Table 3, Table 5 in App A.4, Sec 6 conclusion; License CC BY 4.0)

**The scoping the paper does to itself (and the scout dropped) (VERIFIED)**  
*Mechanism:* Section 5 Limitations names three: (1) 'The current evaluation is focused on
Python. Since this is a language that is widely represented in the training data, detailed
knowledge about tooling, dependencies, and other repository specifics might be present in
the models' parametric knowledge, nullifying the effect of context files.' (2) 'In this
work, we evaluate the impact of context files on task resolution rate. However, other
aspects of coding agent performance, such as code efficiency and security, would be
interesting directions for future work.' (3) automatic generation of useful context files is
an open problem the paper explicitly does not solve. The measured outcome is exactly one
thing: a binary pass/fail on a generated regression test suite after an autonomous
issue-resolution or feature-addition attempt.  
*Why leaders use it:* The scope conditions are where the result stops being a threat to
anything other than resolve-rate-on-Python-issues. The paper does not test: non-Python,
security/safety behaviour, code quality, process compliance, multi-turn human-in-the-loop
work, or any always-on-vs-progressive-disclosure distinction.  
*Failure mode:* The scout's summary presents the finding as a general claim about
instruction files. The paper never makes that claim and its Limitations section pre-empts
it. A marketplace of behaviour-and-safety skills is outside every outcome CTXbench measured.  
*Fit here:* A classified gate needs the scope of its evidence stated with the verdict.
CTXbench is a worked example of a strong result being quotable out of scope.  
*Sources:* https://arxiv.org/html/2602.11988v2 Section 5 (fetched 2026-09-14)

**Appendix B: context files DO help when the repo has no other documentation (VERIFIED)**  
*Mechanism:* 'we show that context files can act as effective overviews when no
documentation is present.' The authors manually removed all documentation (every .md file,
example code, and the contents of docs/) AFTER generating the context file and before
running the agents, excluding Claude Code for cost. Result, verbatim: 'In this setting,
where context files are the only source of documentation available, we find that
LLM-generated context files not only consistently improve performance by 2.7% on average,
but also outperform developer-written ones across settings. This may also explain anecdotal
evidence reporting that coding agents perform better after adding context files, since many
less popular repositories contain little to no documentation.'  
*Why leaders use it:* This is the paper's own mechanism for the null: the context file is
not useless, it is REDUNDANT. Section header: 'Context files are redundant documentation.'
The null result is a measurement of overlap with material the agent could already reach, not
a measurement of instruction futility.  
*Failure mode:* Nearly every popular summary of this paper omits Appendix B. It inverts the
practical advice: the question is not 'context file or no context file' but 'does this file
carry anything the agent cannot otherwise reach'. It also means the null is
benchmark-construction-dependent — CTXbench repos were selected for having context files,
and such repos tend to also have READMEs and docs/.  
*Fit here:* The falsifiable criterion for shipping any instruction file: name one thing in
it the agent cannot derive from the repo. If you cannot, the file is cost with no signal.  
*Sources:* https://arxiv.org/html/2602.11988v2 Appendix B, 'Context files are redundant
documentation' + Figure 12 (fetched 2026-09-14)

**Overviews vs actionable instructions — the distinction is weaker in the data than in the
abstract (CORRECTED)**  
*Mechanism:* Two separate measurements. (a) Overview usefulness, Sec 4.3: 8 of the 12
developer files include a dedicated codebase overview, 4 enumerate directories; GPT-OSS-120b
judged 100% of Sonnet-4.5-generated files, 99% of GPT-5.2, 95% of Qwen3, and 36% of
GPT-5.1-mini files as containing overviews. Proxy metric = average number of steps before
the agent first touches any file the gold patch modifies (3% of instances excluded where it
never does). 'the context files do not meaningfully reduce this metric'. For GPT-5.1-mini it
got significantly WORSE, and manual trace inspection found the cause was the agent issuing
commands to find the context file and re-reading it despite it already being in context. (b)
Category ablation, Table 7: GPT-5.2, categories removed from LLM-generated files by GPT-5.4.
CTXbench accuracy Full 68.12%; without-testing 66.67% (p=0.80); without-overview 62.32%
(p=0.15); without-tooling 63.77% (p=0.31). SWE-bench: Full 54.36%; without-testing 57.72%
(p=0.099); without-overview 54.20% (p=0.73); without-tooling 53.69% (p=0.85). Cost effects
were the significant ones: removing testing cut cost $0.4715 to $0.3730 (p=0.023) on
CTXbench and $0.3272 to $0.2756 (p=0.0035) on SWE-bench.  
*Why leaders use it:* The actionable half is well evidenced — instructions are followed, at
roughly 160x the base rate for named tools, and that is where the whole cost increase comes
from.  
*Failure mode:* The 'overviews are not helpful' clause rests on a navigation-latency proxy,
not on a direct accuracy ablation. When the authors DID directly ablate the overview
category (Table 7), removing it produced the LARGEST nominal accuracy drop on CTXbench
(-5.8pp, p=0.15) — the opposite sign to the abstract's framing, though not significant.
Their own summary is careful: 'no category has a significant positive or negative effect on
benchmark accuracy.' Anyone quoting 'overviews are not helpful' as licence to delete
overviews is quoting the abstract past the evidence.  
*Fit here:* A finding stated in the abstract more strongly than the table supports it is the
exact failure a verification round catches.  
*Sources:* https://arxiv.org/html/2602.11988v2 Sec 4.3 + Appendix B Table 7 (fetched
2026-09-14)

**Publication status: preprint plus three ICLR 2026 workshop acceptances; no archival peer
review (VERIFIED)**  
*Mechanism:* arXiv:2602.11988, DOI 10.48550/arXiv.2602.11988 (arXiv's own DOI, not a
publisher's). Semantic Scholar venue field: 'arXiv.org'; DBLP record
journals/corr/abs-2602-11988; citationCount 21 as of 2026-09-14. OpenReview shows three
workshop acceptances of the same title: ICLR 2026 Workshop RSI (Poster), ICLR 2026 Workshop
MemAgents (Oral), ICLR 2026 Workshop 'Agentic AI in the Wild: From Hallucinations to
Reliable Autonomy' (Poster). No arXiv comment field, no journal_ref. The paper also carries
at least one visible authoring defect: Table 5's second row-group is labelled 'Plan-Bench'
where the caption and every other reference say CTXbench — a stale LaTeX macro that survived
into v2.  
*Why leaders use it:* Workshop acceptance is real signal — three independent workshop
committees took it — but it is light review with no rebuttal cycle and no archival
proceedings.  
*Failure mode:* Treating it as peer-reviewed is wrong; treating workshop-poster status as
worthless is also wrong. The bigger evidentiary point is that the authors themselves revised
the claim downward between versions (see corrections), which is what unreviewed preprints do
and is why version-pinning matters.  
*Fit here:* Evidence tier must be recorded with the claim. 'Preprint, three workshop
posters/orals, self-revised once' is a different weight than 'peer-reviewed'.  
*Sources:* https://api.semanticscholar.org/graph/v1/paper/arXiv:2602.11988 (queried
2026-09-14: venue arXiv.org, citationCount 21) ·
https://api2.openreview.net/notes/search?query=Evaluating%20AGENTS.md%20context%20files
(queried 2026-09-14: notes 0DyJeJ3iia, pLi3A8bscP, 8V5bfIAyBb) ·
https://arxiv.org/abs/2602.11988 (no journal_ref, no comment; fetched 2026-09-14)

**A named methodological critique of CTXbench exists, and a direct contradiction of its cost
claim (VERIFIED)**  
*Mechanism:* Two primary sources. (1) Shepard & Albrecht, 'Probe-and-Refine Tuning of
Repository Guidance for Coding Agents', arXiv:2606.20512 (v1 18 Jun 2026, v2 19 Jun 2026,
Williams College). They name CTXbench (as AGENTBENCH, the v1 name) and Lulla et al. as 'the
two studies closest to ours ... reach opposite conclusions', and critique CTXbench on two
specific axes: 'neither varies the agent's step budget, and Gloaguen et al. (2026) report
steps only as a cost metric rather than asking how a fixed budget interacts with guidance';
and 'Gloaguen et al. (2026)'s context files are generated in a single LLM pass, while
probe-and-refine guidance is iteratively refined through failure feedback'. Their result: on
SWE-bench Verified, 4 independent trials, Qwen3.5-35B-A3B at 200 steps, 33.0% mean resolve
with probe-and-refine tuned guidance vs 28.3% with the static knowledge base that
initialised it vs 25.5% unguided, p<0.001 for both contrasts. 'The improvement comes from
coverage rather than precision: refined guidance produces evaluable patches for 14.5
percentage points more instances while per-patch precision remains statistically constant
(~59%, p=0.119)'. They also report a within-study replication of CTXbench's direction: the
same static guidance that adds 2.8pp to Qwen's resolve rate reduces Nemotron's by 3.8pp. (2)
Lulla, Mohsenimofidi, Galster, Zhang, Baltes, Treude, 'On the Impact of AGENTS.md Files on
the Efficiency of AI Coding Agents', arXiv:2601.20404 (v1 28 Jan 2026, v2 30 Mar 2026; cited
by Shepard as ICSE JAWs 2026). 10 repositories, 124 pull requests, with/without AGENTS.md:
'the presence of AGENTS.md is associated with a lower median runtime (28.64%) and reduced
output token consumption (16.58%), while maintaining a comparable task completion behavior.'  
*Why leaders use it:* Probe-and-refine is the existence proof that instruction files CAN
produce a large, significant resolve-rate gain — when they are tuned against failure
feedback rather than generated in one pass. That is the single most load-bearing
counterweight to the null, and it points at a method, not a vibe.  
*Failure mode:* Lulla's cost finding (-28.6% runtime, -16.6% output tokens) is the OPPOSITE
sign to CTXbench's 'increasing inference cost by over 20%'. The two measure different things
(wall-clock and output tokens on focused real PRs vs steps and USD on benchmark instances)
and neither replicates the other, so the cost clause of CTXbench should be carried as
contested, not settled. Probe-and-refine has its own limits: one 35B model family, a
63%-longer-guidance confound the authors admit they could not ablate, and single-trial
secondary experiments.  
*Fit here:* This is the iterative-verified-rounds pattern operating on the instruction file
itself: probe, diagnose, patch, re-measure.  
*Sources:* https://arxiv.org/abs/2606.20512 and https://arxiv.org/html/2606.20512v2 (fetched
2026-09-14; Abstract, Sec 2 Related Work, Reconciling prior findings, Limitations) ·
https://arxiv.org/abs/2601.20404 (abstract fetched 2026-09-14; v2 30 Mar 2026)

**Claude Code /doctor CLAUDE.md trim check — vendor shipping the same cut CTXbench measured
(VERIFIED)**  
*Mechanism:* Changelog, version 2.1.206: 'Added a /doctor check that proposes trimming
checked-in CLAUDE.md files by cutting content Claude could derive from the codebase'. Docs
state the heuristic in full: 'The /doctor checkup proposes trims for a checked-in CLAUDE.md:
it cuts content Claude can derive from the codebase, such as directory layouts, dependency
lists, and architecture overviews, and keeps pitfalls, rationale, and conventions that
differ from tool defaults. The trim check requires Claude Code v2.1.206 or later.' Related,
same docs page: 'Files over 200 lines consume more context and may reduce adherence. Claude
Code skips a file over 4 MiB.' And the /doctor rewrite itself landed one release earlier,
2.1.205: '/doctor is now a full setup checkup that can diagnose and fix issues; /checkup is
its alias.'  
*Why leaders use it:* The cut list (directory layouts, dependency lists, architecture
overviews) and the keep list (pitfalls, rationale, conventions that differ from tool
defaults) map almost word-for-word onto CTXbench's two halves: derivable overview content
out, non-standard practice in. Two independent parties — an adversarial academic ablation
and the vendor whose own /init prompt generates these files — converged on the same
partition.  
*Failure mode:* Convergence is not confirmation. Anthropic publishes no evaluation behind
the heuristic, so this is a VENDOR PRODUCT DECISION consistent with CTXbench, not
independent replication of it. And CTXbench's own direct ablation of the overview category
(Table 7) moved CTXbench accuracy 68.12% -> 62.32% when the overview was removed — nominally
against the trim, though at p=0.15. The proposition 'trimming overviews improves outcomes'
is not established by either source; what is established is that both parties believe
overview content is not earning its context cost.  
*Fit here:* Convergent-but-unmeasured. Exactly the class of claim that deserves a local
experiment rather than adoption on authority.  
*Sources:* https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
(fetched 2026-09-14; entries under ## 2.1.206 and ## 2.1.205; head of file was 2.1.270) ·
https://docs.claude.com/en/docs/claude-code/memory (fetched 2026-09-14; 'My CLAUDE.md is too
large' section)

**Enforced context budgets are real, and Anthropic's are the better-documented instance
(VERIFIED)**  
*Mechanism:* Two vendors, both primary-sourced 2026-09-14. (a) Windsurf/Devin Desktop:
'Limited to 6,000 characters' for the global rules file
~/.codeium/windsurf/memories/global_rules.md, and 'Limited to 12,000 characters per file'
for workspace rules in .devin/rules/*.md (preferred) or .windsurf/rules/*.md (fallback);
restated in prose as 'Workspace rule files are limited to 12,000 characters each. The global
rules file is limited to 6,000 characters.' Workflows are separately capped at 12,000
characters each. Activation modes are frontmatter-declared via trigger: always_on | glob |
model_decision | manual, with a documented context-cost column per mode. (b) Claude Code
skill listing: 'Every skill in the skill listing adds to your context on every turn, whether
or not Claude ever uses it.' The listing has 'a character budget ... The budget scales at 1%
of the model's context window. When the listing overflows, Claude Code drops descriptions
starting with the skills you invoke least'. Per-entry cap: 'each entry's combined text is
capped at 1,536 characters regardless of budget', configurable via skillListingMaxDescChars;
budget via skillListingBudgetFraction or SLASH_COMMAND_TOOL_CHAR_BUDGET. Claude Code 2.1.261
added /skill-doctor 'to show which loaded skills go unused and what they cost in context, so
you can prune them' (docs say v2.1.252 or later).  
*Why leaders use it:* A hard cap forces the editorial decision CTXbench says is the only one
that matters: what is worth an always-on slot. Windsurf's four activation modes and Claude
Code's listing-vs-body split are the same idea — pay full price only for what must always be
present.  
*Failure mode:* The Windsurf figures are documented as limits but the docs never state the
enforcement mechanism: nothing says whether an over-length file is truncated, rejected, or
merely discouraged. The scout was right that docs.windsurf.com/windsurf/cascade/rules 404s —
the content moved to /cascade/memories under docs.devin.ai after the Cognition acquisition,
and the whole docs.windsurf.com domain now 302s into docs.devin.ai/desktop/*. Treat
6,000/12,000 as VERIFIED-as-documented, CLAIMED-as-enforced.  
*Fit here:* A budget is a falsifiable criterion with a number attached. /skill-doctor is the
measurement instrument this marketplace's own users will point at it.  
*Sources:* https://docs.windsurf.com/windsurf/cascade/memories ->
https://docs.devin.ai/desktop/cascade/memories (fetched 2026-09-14, HTTP 200 after redirect)
· https://docs.claude.com/en/docs/claude-code/slash-commands (fetched 2026-09-14; 'Find
unused skills' and skill-listing budget sections) ·
https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md (## 2.1.261,
/skill-doctor)

**The AGENTS.md 60k figure — query now sourced, number still not reproducible (CLAIMED)**  
*Mechanism:* agents.md homepage, 2026-09-14: 'A simple, open format for guiding coding
agents, used by over 60k open-source projects.' The scout reported the query behind it was
unstated. That is CORRECTED: the string '60k open-source projects' is itself a hyperlink,
and its href is
https://github.com/search?q=path%3AAGENTS.md+NOT+is%3Afork+NOT+is%3Aarchived&type=code. The
same query is linked a second time lower on the page as 'View 60k+ examples on GitHub'.
CTXbench cites the same figure twice from the same source: 'included in over 60'000
open-source repositories, as reported by AGENTS.md' and 'At the time of writing, AGENTS.md
report that over 60'000 public GitHub repositories include a context file.'  
*Why leaders use it:* It is the number everyone cites for context-file adoption, including
the paper that argues against context files.  
*Failure mode:* The query is stated but its result is not obtainable. GitHub's code-search
web UI requires login and returns no count to an unauthenticated fetch. Running the linked
query through the REST code-search API returns total_count 141 — because in the REST API
path: is a directory-prefix match, so path:AGENTS.md matches a DIRECTORY named agents.md,
not the file. The equivalent API query filename:AGENTS.md returns total_count 962,560
(2026-09-14), reproducing the scout's number exactly — but appending NOT is:fork NOT
is:archived changes that total by zero, i.e. the REST API silently ignores both filters that
the linked query depends on. So: files not projects, forks not excluded via this route, no
date stamp published, and no way to re-derive 60k from any endpoint reachable here. Carry it
as a vendor-published figure with a stated-but-unreproducible method.  
*Fit here:* A cited number whose method is nominally published and still not reproducible is
the canonical case for CLAIMED-not-VERIFIED.  
*Sources:* https://agents.md/ (page source fetched 2026-09-14; anchor href extracted from
HTML) ·
https://github.com/search?q=path%3AAGENTS.md+NOT+is%3Afork+NOT+is%3Aarchived&type=code
(fetched 2026-09-14: login wall, no count rendered) · GitHub REST code search, queried
2026-09-14: filename:AGENTS.md -> total_count 962560; path:AGENTS.md NOT is:fork NOT
is:archived -> total_count 141

**Implications:**
- DOES CTXBENCH THREATEN THIS MARKETPLACE'S PREMISE? Narrowly, no — and the paper says so
  itself in the sentence everyone stops reading before: 'we conclude that while context
  files are useful for specifying non-standard coding practices, any attempts to improve
  performance should be rigorously evaluated before deployment.' That is a description of
  what this marketplace ships. The measured outcome in CTXbench is a binary pass/fail on
  generated regression tests after autonomous Python issue resolution. Not one plugin here
  optimises that. graveyard optimises for not deleting a repo before its bundle is verified;
  verify-before-claim, stop-rule, scope-fence and redgate optimise for process compliance
  under pressure; voice optimises prose. The paper's Limitations section explicitly parks
  security and non-resolve-rate outcomes as future work.
- WHERE IT DOES BITE, AND IT BITES HARD: Appendix B is the clause aimed at this repo. The
  null is explained by redundancy — 'Context files are redundant documentation' — and when
  the authors deleted every .md and docs/ from the repo, the same context files started
  helping by 2.7%. The test that survives is therefore not 'is this a skill' but 'does this
  file carry procedure the agent could not derive from the repository'. By that test,
  graveyard's archive-then-verify-then-emit-a-guarded-script protocol passes cleanly: no
  agent derives it from the code. But the repo's own CLAUDE.md/AGENTS.md is a mixed case —
  its Layout section is a directory tree and its tier descriptions restate what
  evals/README.md and docs/testing.md already say. That is precisely the content class
  Anthropic's /doctor trim check cuts ('directory layouts, dependency lists, and
  architecture overviews') and precisely the class CTXbench found inert. The governance
  file, not the skills, is where this result lands.
- THE SECOND-ORDER THREAT IS COST, NOT CORRECTNESS, AND IT IS CONTESTED: CTXbench's most
  robust result is not the null — it is the cost increase, which clears p<0.001 on
  stratified permutation tests where every accuracy comparison fails to clear 0.05.
  Instructions ARE followed (uv 1.6x/instance when named vs <0.01x when not), following them
  costs steps and reasoning tokens, and that is the bill. A marketplace of ~25 plugins pays
  that bill in the always-on skill listing whether or not any skill fires — Anthropic
  documents the listing budget at 1% of the context window with a 1,536-char per-entry cap
  and shipped /skill-doctor in 2.1.261 specifically to find the ones you never invoke. But
  the cost direction is not settled: Lulla et al. (arXiv:2601.20404, 10 repos / 124 real
  PRs) measured the opposite sign, -28.6% median runtime and -16.6% output tokens with
  AGENTS.md present. Two studies, opposite signs, different outcome variables. Carry cost as
  contested.
- THE REAL COUNTERWEIGHT IS METHODOLOGICAL, NOT RHETORICAL: Shepard & Albrecht
  (arXiv:2606.20512) reconcile the disagreement by showing the decisive variable is how the
  guidance is PRODUCED. Single-pass generation (all CTXbench's LLM arm) gives generic
  advice; guidance iteratively refined against failure probes gave 33.0% vs 25.5% unguided
  on SWE-bench Verified, p<0.001, across four trials. They also land a specific critique
  CTXbench cannot answer: neither study varied the agent's step budget, and their budget
  experiment shows the same guidance can look beneficial, neutral, or harmful depending on
  how many steps the agent has. That is the strongest available evidence that an instruction
  file tuned against a benchmark beats one written from intuition — which is an argument FOR
  this repo's eval discipline and AGAINST ever shipping a skill on the strength of a
  demonstration comment alone.
- THE CHEAPEST EXPERIMENT THIS REPO CAN RUN ON ITS OWN MATERIAL: convert one existing
  promptfoo pack from a discriminability check into a paired A/B effect measurement. The
  machinery is already there — 8 packs carry calibration-stub.md, every pack sets repeat: 3,
  and the graveyard pack's own comment measures a run at ~$0.04. The single change is to
  stop inverting the rubric on the control arm. Today the stub arm asserts that the bare
  model behaves the OLD way (PASS = 'the opposite of the real test's' condition), which
  proves the rubric can tell the arms apart but yields no effect size. Instead: same
  question, same rubric, skill = real SKILL.md vs skill = calibration-stub.md, and report
  pass-rate delta with a binomial CI. Pick ONE pack (redgate or verify-before-claim — both
  already have the stub wired and three tests) and raise repeat from 3 to 10, giving 30
  graded samples per arm for roughly $1.20 of OpenRouter tokens. That is enough to detect a
  30-point pass-rate difference and, crucially, enough to discover that some skills produce
  a delta indistinguishable from zero — which is the finding worth having. The four packs
  with no control at all (graveyard, voice, fleet-playbook-curator, tailscale-wif) should
  get calibration-stub.md wired in as the follow-on; graveyard is the one where a measured
  delta matters most, because it is the only skill whose failure is irreversible.
- WHAT THE DEMONSTRATION DISCIPLINE ALREADY GETS RIGHT, AND WHAT IT MISSES: the repo's own
  table says the behavioral tier proves 'a model given the skill changes its behaviour' but
  not 'whether the change is worth having', and assigns that job to a human-read PR
  demonstration. CTXbench is the empirical case that the gap between those two is exactly
  where instruction files die: agents followed the instructions (behaviour changed, ~160x on
  named tools) and outcomes did not move. A demonstration comment cannot detect that,
  because a demonstration has no control arm either — it shows the skill firing, never the
  counterfactual. The A/B above is the cheapest way to close the one gap the repo has
  already named and then routed around.

### Dive 6 — Knowledge management's own history, and the folklore it runs on

**The 84% KM-failure statistic: a real article, a real sentence, and a number that is not in
it (CORRECTED)**  
*Mechanism:* Lucier & Torsilieri, 'Why Knowledge Programs Fail: A C.E.O.'s Guide to Managing
Learning', strategy+business issue 9, 1 October 1997, says VERBATIM: 'We estimate that about
one-sixth of these programs achieve very significant impact within the first two years; half
achieve small but important benefits; and the remaining third -- the failures -- have little
business impact.' The authors' own failure rate is ONE THIRD. They then add, verbatim, 'The
label "failure" may seem unfair because many of these programs generate excitement among
participants, stimulate collaboration and create tangible outputs like knowledge databases
and collaborative systems.' And the evidentiary basis, verbatim: 'Based on our five years of
involvement in knowledge and learning organization programs -- in Booz-Allen & Hamilton's
own knowledge program, at our clients and in discussions with participants in more than 70
leading programs -- we believe that effectively managed learning can have a significant
strategic impact...'. No sample frame, no instrument, no operational definition of
'significant impact'. The 84% is manufactured by rounding one-sixth to 16% and subtracting
from 100, which silently reclassifies the successful half as failures. The exact arithmetic
matters: 100 - 16 = 84; 100 - 16.67 = 83.3. The circulating figure is the rounded-down
subtraction.  
*Why leaders use it:* It is a single large round number that licenses a budget conversation,
and it comes with a consultancy's name attached, which reads as authority. Each re-citer is
behaving reasonably by local standards - they cited a peer-reviewed source that said the
thing. Nobody in the chain did anything a reviewer would flag.  
*Failure mode:* Citation of a citation. The discipline 'every claim carries a citation' was
satisfied at every hop and still produced a fabricated number, because the rule checks that
a pointer EXISTS, not that the pointer RESOLVES TO THE CLAIM. A citation format that does
not force the checker to the original text is decorative.  
*Fit here:* This is the strongest possible argument for `fleet-playbook-curator`'s
`repo@sha:path` format over a prose citation: a content-addressed pointer cannot drift from
what it points at, and checking it costs one file read. But it also names the gap - pinning
the LOCATION does not pin the CLAIM. The 1997 URL was stable and correct at every hop; what
broke was the transcription of what it said. The missing primitive is a quoted span, not
just a path.  
*Sources:* https://www.strategy-business.com/article/13007 (Lucier & Torsilieri,
strategy+business issue 9, 1 Oct 1997; full text fetched and all quotes extracted verbatim
2026-09-14) ·
https://www.academia.edu/89272691/Linking_Business_Strategy_and_Knowledge_Management_Capabilities_for_Organizational_Effectiveness
(Smith, Mills & Dion, IJKM 6(3):22-43, 2010; p.22 quoted verbatim 2026-09-14) ·
https://academic-publishing.org/index.php/ejkm/article/download/1978/2029/3901 (Tucker &
Kotnour, EJKM 19(3):237-254, 2021; p.238 quoted verbatim from PDF 2026-09-14)

**The vocabulary problem - two people name the same thing the same way less than one time in
five (VERIFIED)**  
*Mechanism:* Furnas, Landauer, Gomez & Dumais, 'The vocabulary problem in human-system
communication', Communications of the ACM 30(11), November 1987, 964-971, DOI
10.1145/32206.32212. Abstract VERBATIM: 'In almost all computer applications, users must
enter correct words for the desired objects or actions. For success without extensive
training, or in first-tries for new targets, the system must recognize terms that will be
chosen spontaneously. We studied spontaneous word choice for objects in five
application-related domains, and found the variability to be surprisingly large. In every
case two people favored the same term with probability <0.20. Simulations show how this
fundamental property of language limits the success of various design methodologies for
vocabulary-driven interaction. For example, the popular approach in which access is via one
designer's favorite single word will result in 80-90 percent failure rates in many common
situations. An optimal strategy, unlimited aliasing, is derived and shown to be capable of
several-fold improvements.'  
*Why leaders use it:* It converts a soft complaint ('search is bad') into a hard design
constraint with a number attached, and it derives a remedy rather than only diagnosing.  
*Failure mode:* The 80-90% figure is a SIMULATION RESULT, not a measured failure rate of a
deployed system. The measured quantity is p<0.20 for spontaneous term agreement across five
domains; the 80-90% is what simulations project for the single-designer-term design under
that distribution. Citing '80-90% of searches fail' as an empirical observation overstates
it. Also routinely flattened to 'people use different words for things', which loses both
the magnitude and the derived remedy.  
*Fit here:* Direct and unmet. Any find-before-build or wayfinding step in this marketplace
assumes a searcher can guess the term a previous author chose. Furnas says that guess fails
four times in five, and the derived fix - unlimited aliasing - is a design the repo does not
implement anywhere. This is the quantitative case for maintaining alias lists on skill and
plugin names rather than relying on a naming convention.  
*Sources:* https://api.crossref.org/works/10.1145/32206.32212 (authoritative bibliographic
record: Communications of the ACM 30(11), Nov 1987, 964-971; read 2026-09-14) ·
https://honnef.co/notes/references/furnasvocabularyproblemhumansystem1987/ (SECONDARY -
independent BibTeX record carrying the publisher abstract verbatim; read 2026-09-14) ·
https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/32206.32212 (citation count
1,735; read 2026-09-14) · https://dl.acm.org/doi/10.1145/32206.32212 (publisher of record -
HTTP 403 via proxy, abstract and PDF not retrievable)

**Wikipedia WP:V - the burden sits on the adder, the unit is the inline citation, the
default remedy is removal (CORRECTED)**  
*Mechanism:* All four moves quoted VERBATIM from the current policy wikitext
(en.wikipedia.org/w/index.php?title=Wikipedia:Verifiability&action=raw, read 2026-09-14).
SCOPE: 'Each fact or claim in an article must be verifiable. All quotations, and any
material whose verifiability has been challenged or is likely to be challenged, must include
an inline citation to a reliable source that directly supports the material. Any material
that needs an inline citation but does not have one may be removed.' BURDEN (section
WP:BURDEN): 'The burden to demonstrate verifiability lies with the editor who adds or
restores material, and it is satisfied by providing one inline citation to a reliable source
that directly supports the contribution.' REMEDY (WP:CHALLENGE): 'Facts or claims without an
inline citation to a reliable source that directly supports them may be removed. They should
not be restored without an inline citation to a reliable source.' INTERIM STATE
(WP:BURDENWAIT): 'Whether or how quickly material should be removed for lacking an inline
citation to a reliable source depends on the material and the overall state of the article.
Consider adding a citation needed tag as an interim step to removing unsourced material, to
allow references to be added.' The policy also defines 'directly supports' in a footnote: 'A
source "directly supports" a given piece of material if the information is present
explicitly in the source' - which is the exact clause the 84% chain violates.  
*Why leaders use it:* It is the only citation discipline in existence proven at the scale of
millions of documents and an open contributor population, with no machine enforcement of the
substantive rule.  
*Failure mode:* The policy's own load-bearing design decision is that it does NOT require
everything to be cited - only quotations and challenged-or-likely-to-be-challenged material.
A repo that adopts 'cite everything' has adopted a rule Wikipedia deliberately did not
write, and will get the backlog without the affordability.  
*Fit here:* `fleet-playbook-curator` already has the substance. What it lacks, and Wikipedia
has: (a) a WRITTEN LIST of which claim types require a citation, so the rule stays
affordable; (b) explicit BURDEN PLACEMENT on the adder AND RESTORER, which is what resolves
a review standoff; (c) the 'directly supports' definition, which is the only clause that
would have caught the 84%.  
*Sources:* https://en.wikipedia.org/w/index.php?title=Wikipedia:Verifiability&action=raw
(raw policy wikitext, 34,046 bytes, read 2026-09-14)

**A citation rule pays off by constraining the WRITER and licensing REMOVAL - almost nobody
reads the citation (VERIFIED)**  
*Mechanism:* Piccardi, Redi, Colavizza & West, 'Quantifying Engagement with Citations on
Wikipedia', The Web Conference 2020 (WWW '20), pp. 2365-2376, published 20 April 2020;
preprint arXiv:2001.08614, submitted 23 January 2020. Abstract VERBATIM: 'we built
client-side instrumentation for logging all interactions with links leading from English
Wikipedia articles to cited references during one month... We find that overall engagement
with citations is low: about one in 300 page views results in a reference click (0.29%
overall; 0.56% on desktop; 0.13% on mobile). Matched observational studies of the factors
associated with reference clicking reveal that clicks occur more frequently on shorter pages
and on pages of lower quality, suggesting that references are consulted more commonly when
Wikipedia itself does not contain the information sought by the user.' The second finding is
the one that is always dropped: the citation is a FALLBACK PATH, exercised precisely when
the article fails.  
*Why leaders use it:* Almost nobody uses it. It is the uncomfortable measurement that
citation-discipline advocates do not cite, which is itself a small piece of evidence for the
thesis.  
*Failure mode:* Read as 'citations don't matter'. The paper says the opposite about value
and something narrower about consumption: readers rarely follow references, and the ones who
do are the readers the article already failed.  
*Fit here:* See implications. This is the single most consequential finding in the dive for
this repo's own rule.  
*Sources:* https://arxiv.org/abs/2001.08614 (abstract quoted verbatim, read 2026-09-14) ·
https://api.crossref.org/works/10.1145/3366423.3380300 (published version: Proceedings of
The Web Conference 2020, pp. 2365-2376, 20 April 2020; read 2026-09-14)

**The interim flag becomes an unbounded backlog - and Wikipedia documents this about itself
(VERIFIED)**  
*Mechanism:* Wikipedia:Citation needed, VERBATIM from the raw wikitext (read 2026-09-14): 'A
"citation needed" tag is a request for another editor to supply a source for the tagged
fact: a form of communication between members of a collaborative editing community. It is
never, in itself, an "improvement" of an article. Though readers may be alerted by a
"citation needed" that a particular statement is not supported, and even doubted by some,
many readers don't fully understand the community's processes. Not all tags get addressed in
a timely manner, staying in place for months or years, forming an ever-growing Wikipedia
backlog-this itself can be a problem.' The page then carries a live 'Help reduce the
backlog' section with automatically-updating counts, i.e. the community has
institutionalised the backlog as a standing work queue rather than treating it as an
anomaly.  
*Why leaders use it:* A flag feels like the humane middle path between 'accept unsourced'
and 'delete'. It defers the decision at zero immediate cost.  
*Failure mode:* The flag has no expiry and no owner, so it converts a binary decision into
an indefinite third state. Roughly 585,000 English Wikipedia articles are currently parked
in it. The tag is explicitly 'never, in itself, an improvement' - it is a message addressed
to a future volunteer who may never arrive.  
*Fit here:* This is the named, quantified failure mode of a STALE flag. A repo adopting
per-claim STALE marks without a drain rule - an expiry, an owner, or an automatic promotion
of STALE to REMOVED after N days - is walking into a documented 585,000-item outcome.
Wikipedia's own remedy is not a better flag; it is WP:BURDENWAIT's instruction that removal
remains available and the tag is only 'an interim step to removing'.  
*Sources:* https://en.wikipedia.org/w/index.php?title=Wikipedia:Citation_needed&action=raw
(raw wikitext, read 2026-09-14) ·
https://en.wikipedia.org/w/api.php?action=query&prop=categoryinfo&titles=Category:All%20articles%20with%20unsourced%20statements
(584,899; read 2026-09-14) ·
https://en.wikipedia.org/w/api.php?action=query&prop=categoryinfo&titles=Category:All%20articles%20needing%20additional%20references
(540,218; read 2026-09-14)

**Prepublication review hides bad contributions; it does not reduce them (CORRECTED)**  
*Mechanism:* Tran, Champion, Hill & Greenstadt, 'The Risks, Benefits, and Consequences of
Prepublication Moderation: Evidence from 17 Wikipedia Language Editions', Proceedings of the
ACM on Human-Computer Interaction 6(CSCW2), Article 333, November 2022, 25 pages, DOI
10.1145/3555225. Design, VERBATIM: 'we used a community-level panel data interrupted time
series (ITS) analysis, as well as a user-level general linear mixed model (GLMM), to
identify the effects of FlaggedRevs on several different outcomes.' Population: 17 language
editions including German, each windowed 12 months either side of its own FlaggedRevs
activation date; 1,972,861 observations in the user-level dataset; models carry wiki-level
fixed effects. RESULT H1 (visible reverted contributions, standardised): IP editors
flaggedrev_on = -1.78 (SE 0.086, p<0.001); first-time editors -1.759 (SE 0.095, p<0.001);
all editors -1.27 (SE 0.167, p<0.001). RESULT H2 (whether contribution QUALITY changed),
VERBATIM: 'Our overall results for H2 reflect a consistent null result. We find little
evidence of the prepublication moderation system having a major impact on the quality of
contributions.' CONCLUSION, VERBATIM: 'First, we sought to understand if the deployment of
FlaggedRevs did what it was designed to do. We found that in this regard, it was an
unambiguous and unmitigated success. By adding prepublication moderation, the Wikipedia
language editions in our sample kept a large portion of vandalism and other low-quality
contributions by untrusted users from ever being seen by the public. Contrary to our
hypothesis, we did not find strong evidence of any meaningful long-term change in
contribution quality. This suggests that communities that change their content moderation
from postpublication to prepublication to discourage poor-quality contributions from ever
occurring may not see the relief they seek.'  
*Why leaders use it:* Because the gate demonstrably works at the thing it was built for, and
the effect size is enormous (-1.78 SD).  
*Failure mode:* The gate is a display filter, not a behaviour change. Bad contributions
arrive at the same rate; they just stop being visible. Any business case that assumes the
gate will eventually reduce the review workload is contradicted by H2. Also, per the paper's
own Limitations section, review latency varies enormously - German Wikipedia has 19,994
users with review rights and a two-hour median delay for edits by users without accounts,
while Russian Wikipedia has 2,422 and a median delay of more than 13 days - so the gate's
cost is entirely a function of reviewer supply.  
*Fit here:* This is `redgate`'s classified human gate, measured. Two transferable results.
(1) The gate's value is real and large, but it is realised in what the public never sees,
not in an improvement in what contributors produce - so do not justify a gate by promising
it will train better behaviour upstream. (2) Gate cost scales with reviewer supply, not with
policy: the same extension is a two-hour delay or a two-week delay depending purely on how
many reviewers exist. A gate specified without a staffing model is a backlog specification.  
*Sources:* https://arxiv.org/pdf/2202.05548 (full text, 25pp, extracted and quoted verbatim
2026-09-14) · https://arxiv.org/abs/2402.17880 (Tran, Take, Champion, Hill & Greenstadt,
'Challenges in Restructuring Community-based Moderation', PACM HCI 8(CSCW2) 415:1-415:24;
the qualitative companion study; read 2026-09-14)

**Xerox Eureka - peer validation between submission and fleet-wide availability, with credit
instead of cash (CORRECTED)**  
*Mechanism:* Whalen & Bobrow, 'Communal knowledge sharing: the Eureka story', chapter in
Szymanski & Whalen (eds.), Making Work Visible, Cambridge University Press, 2011, pp.
257-284. Abstract VERBATIM: 'The greatest motivator turned out to be fame or, put another
way, reputation. Every solution we called them tips would have the authors name on it. And
the crucial factor in establishing trust was having all the tips that were submitted to the
community knowledge base be vetted by expert technicians by the communitys most trusted
members, who would also be the authors peers rather than some distant group of people
working for management at the field service organizations headquarters. In this way, the
system would literally be owned by the work community itself. Eureka made its debut in 1994,
and in the dozen years of its operation it has saved Xerox over $100M in service costs.' The
design claim is two-part and both parts are load-bearing: validation is by PEERS, explicitly
not by management, and the reward is a byline.  
*Why leaders use it:* It is the rare 1990s KM system that ran for two decades, and it has a
clean, copyable mechanism.  
*Failure mode:* The $100M is a first-person insider estimate with no method attached,
published by the system's own builders, about a project a PR agency had selected for media
appeal. Cox additionally documents that the usual management lesson drawn from it is
backwards, VERBATIM: 'US management consistently disbelieved that the repairmen had any
knowledge worth recording or sharing (Bobrow and Whalen 2002, p.57)'; 'Lack of management
support forced the team to adopt a participatory design and implementation approach'; and
when management finally endorsed it, 'they then required the system to be rolled out at such
a speed that the participatory process was truncated.' Cox: 'This makes it difficult to
acknowledge the conclusion that a success factor is lack of senior management support.'  
*Fit here:* Prior art for putting an acceptance gate on the KNOWLEDGE ARTIFACT, not just on
code - which is what `redgate` and `eval-ladder` do for code and nothing in the marketplace
does for a written tip. Two specifics worth copying: the reviewer must be a PEER of the
author rather than a central authority, and the incentive is a durable byline. The Cox
finding adds a third, uncomfortable one: the participatory design that made it work was a
consequence of NOT having executive sponsorship, and executive sponsorship, when it arrived,
degraded it.  
*Sources:*
https://www.sri.com/publication/fcd-publications/communal-knowledge-sharing-the-eureka-story/
(Whalen & Bobrow 2011, Making Work Visible, CUP, 257-284; abstract quoted verbatim, read
2026-09-14) · https://eprints.whiterose.ac.uk/id/eprint/78659/2/WRRO_78659.pdf (Cox, KMRP
5(1):3-12, 2007, author manuscript; full text extracted and quoted verbatim 2026-09-14) ·
https://doi.org/10.1057/palgrave.kmrp.8500118 (publisher DOI for Cox 2007)

**SECI / Nonaka's knowledge conversion, and the critique that no mode survives (CORRECTED)**  
*Mechanism:* Nonaka, 'A Dynamic Theory of Organizational Knowledge Creation', Organization
Science 5(1), February 1994, 14-37 (Crossref-confirmed; 11,159 citations as of 2026-09-14).
The operationally load-bearing claim is Externalization: that tacit knowledge converts into
explicit knowledge, i.e. that 'write it down' is a well-defined operation.  
*Why leaders use it:* SECI is the default framing in KM textbooks and in most 'capture the
tribal knowledge' project charters, and it borrows Polanyi's authority for a claim Polanyi
did not make.  
*Failure mode:* Externalization is priced at zero. The Gourlay dilemma is the sharp version:
either the canonical cases do not demonstrate externalization at all, or externalization is
just ordinary speech, in which case it is not a distinct mechanism and explains nothing.  
*Fit here:* Any skill whose premise is 'what an agent learned this session can be written
down and reused' is an externalization machine. Nothing in the marketplace prices that
conversion as lossy or as costly. The transferable move is not to abandon writing things
down - it is to stop treating the written artifact as equivalent to the knowing, and to
build a check that the artifact still works, rather than assuming it captured what it was
meant to.  
*Sources:*
https://scispace.com/pdf/conceptualizing-knowledge-creation-a-critique-of-nonaka-s-16ix5a51l3.pdf
(Gourlay 2006 accepted manuscript, 36pp, extracted and quoted verbatim 2026-09-14) ·
https://api.crossref.org/works/10.1111/j.1467-6486.2006.00637.x (JMS 43(7):1415-1436, Nov
2006; read 2026-09-14) · https://api.crossref.org/works/10.1287/orsc.5.1.14 (Nonaka 1994,
Organization Science 5(1):14-37, Feb 1994; read 2026-09-14) ·
https://onlinelibrary.wiley.com/doi/10.1111/j.1467-6486.2006.00637.x (publisher of record -
HTTP 403 via proxy)

**The Zettelkasten's index was deliberately incomplete - exhaustive tagging is a
software-era invention (VERIFIED)**  
*Mechanism:* Schmidt, 'Niklas Luhmann's Card Index: The Fabrication of Serendipity',
Sociologica 12(1), published 26 July 2018, DOI 10.6092/issn.1971-8853/8350. The author is
the scientific coordinator of the Bielefeld Luhmann-Archiv. VERBATIM on scale: 'Luhmann's
card index consists of approximately 90,000 handwritten cards in A-6 format organized in two
collections.' Collection I (c.1951-1962): 'approximately 23,000 cards... and a keyword index
with roughly 1,250 entries.' Collection II (1963-1997): 'approximately 67,000 cards,
including a sizeable but obviously incomplete bibliographical apparatus with roughly 15,000
references and a keyword index with 3,200 entries.' VERBATIM on the index's deliberate
incompleteness: 'Contrary to the subject index of a book, the file's keyword index makes no
claim to providing a complete list of all cards in the collection that refer to a specific
term. Rather, Luhmann typically listed only one to four places where the term could be found
in the file, the idea being that all other relevant entries in the collection could be
quickly identified via the internal system of references described above.' And the design
rationale, VERBATIM: 'this concept goes back to the general structure of the brain modeled
by W.R. Ashby: the capacity of the brain does not derive from a huge number of
point-to-point-accesses but on the relations between the nodes.'  
*Why leaders use it:* Because 90,000 notes and 600 publications is an irresistible number,
and because 'the index is small on purpose' is a much less marketable idea than 'tag
everything'.  
*Failure mode:* The circulating practice inverts the primary evidence. 3,200 index entries
for 67,000 slips, capped at four pointers each, is a deliberately sparse entry-point index
whose job is to get you into the reference graph - not a comprehensive catalogue.
Software-era Zettelkasten advice that recommends exhaustive tagging is recommending the
opposite of what Luhmann did, and citing him for it.  
*Fit here:* Direct read for any index this repo builds: the index is an ENTRY POINT, not a
catalogue. Schmidt's Ashby argument is precisely `fleet-playbook-curator`'s invariant stated
in 1981 terms - the index says where to enter, the relations carry the rest. Building an
index that tries to be complete is both more expensive and, on this evidence, less
effective.  
*Sources:* https://www.uni-bielefeld.de/soz/luhmann-archiv/ (Schmidt 2018, Sociologica
12(1); PDF extracted in full and quoted verbatim 2026-09-14) ·
https://doi.org/10.6092/issn.1971-8853/8350 (DOI of record)

**Networked PKM tools (Obsidian, Roam, Logseq) - the loudest sub-domain with the emptiest
evidence base (VERIFIED)**  
*Mechanism:* Claimed mechanism: bidirectional links plus a graph view surface connections a
hierarchy would hide. The only peer-reviewed-track empirical work located is Ferreira,
Segura, Souza & Brasil, 'How People Manage Knowledge in their "Second Brains" - A Case Study
with Industry Researchers Using Obsidian', arXiv:2509.20187, submitted 24 September 2025.
Abstract VERBATIM on scope and finding: 'We selected the note-taking tool Obsidian and
researchers from a Brazilian lab for an in-depth investigation. Our investigation reveals
interesting findings about how researchers build and explore their personal knowledge bases.
A key finding is that participants' knowledge retrieval strategy influences how they build
and maintain their content.'  
*Why leaders use it:* Vivid testimony, a visible graph, and a genre of writing in which
every citation resolves to another blog post.  
*Failure mode:* No controlled study exists in either direction. The one usable finding is
about STRUCTURE FOLLOWING RETRIEVAL, not about output. Adoption figures do not exist either:
no vendor publishes them and every circulating number traces to estimate-based content
marketing.  
*Fit here:* Included as a negative. A repo whose rule is 'cite it or flag it STALE' should
not import practices from this genre at all without labelling the evidence base as
testimonial. It is also a useful calibration exercise: this is what a domain looks like when
the citation rule is absent.  
*Sources:* https://arxiv.org/abs/2509.20187 (abstract quoted verbatim, read 2026-09-14)

**The 50% and 70% KM-failure figures - traceable after all, and what they trace to is worse
than nothing (CORRECTED)**  
*Mechanism:* THE 70%, ACADEMIC CHAIN. Malhotra, 'Integrating knowledge management
technologies in organizational business processes: getting real time enterprises to deliver
real business performance', Journal of Knowledge Management 9(1), 2005, 7-28. VERBATIM:
'Some industry estimates have pegged the failure rate of technology implementations for
business process reengineering efforts at 70%. Recent industry data suggest a similar
failure rate of KM related technology implementations and related applications (Darrell et
al., 2002).' Two things are true of that sentence. First, the 70% is a BPR number, and the
KM figure is asserted by analogy ('a similar failure rate'), not measured. Second, the
citation attached to it resolves, in Malhotra's own reference list VERBATIM, to: 'Darrell,
R., Reichheld F.F. and Schefter, P. Avoid the Four Perils of CRM. Harvard Business Review,
pp. 101-109. February, 2002.' That is an article about CRM, by three Bain consultants (the
lead author is Darrell K. Rigby - Malhotra has transposed given and family name), whose own
headline figure is that more than half of CRM initiatives fail to produce the anticipated
results. So a KM number is sourced, by analogy from BPR, to a CRM article that does not
contain it. Downstream, Tucker & Kotnour, EJKM 19(3), 2021, p.238 VERBATIM: 'Malhotra's
(2005) research indicates failure rates as high as 70%.' THE 70%, TRADE-PRESS ORIGIN.
Ambrosio, 'Knowledge Management Mistakes', Computerworld, 3 July 2000, VERBATIM: 'Some
researchers peg the failure rate of knowledge management projects at 50%. But Daniel
Morehead, director of organizational research at British Telecommunications PLC in Reston,
Va., says the rate is closer to 70%. "Most knowledge management projects simply don't hit
their stated goals and objectives," Morehead says. "So that 70% doesn't mean they fail
totally - it means that they don't accomplish what they set out to do."'  
*Why leaders use it:* Same reason as the 84%: a round number with an institution behind it.  
*Failure mode:* Identical in shape to the 84%, and independently so. Morehead's 70% is
explicitly a 'did not hit stated goals' figure, and he says so in the same breath - 'that
70% doesn't mean they fail totally'. Every subsequent citation of '70% of KM projects fail'
performs the same category inflation Lucier & Torsilieri's half underwent. The 50% in that
same sentence is attributed to nobody ('some researchers') and I could not trace it anywhere
further.  
*Fit here:* The general lesson for any evidence contract: the interesting failure is not an
uncited claim, which a reviewer catches, but a claim whose citation is present, formatted
correctly, and points at a different field. A rule that checks for the presence of a
citation catches the first and licenses the second.  
*Sources:*
https://e-learning.dmst.aueb.gr/mis/Cases/DaimlerChrysler/Case/Training_Files/KnowledgeManagementRealTimeEnterpriseBusinessModels.pdf
(Malhotra 2005 accepted manuscript for JKM 9(1):7-28; body text and reference list extracted
and quoted verbatim 2026-09-14) ·
https://www.computerworld.com/article/1378258/knowledge-management-mistakes.html (Ambrosio,
Computerworld, 3 July 2000; quoted verbatim, read 2026-09-14) ·
https://hbr.org/2002/02/avoid-the-four-perils-of-crm (Rigby, Reichheld & Schefter, HBR,
February 2002 - the cited source, which is about CRM; identification confirmed 2026-09-14) ·
https://academic-publishing.org/index.php/ejkm/article/download/1978/2029/3901 (Tucker &
Kotnour, EJKM 19(3), 2021, p.238; quoted verbatim 2026-09-14)

**Implications:**
- TRANSFERS, AND IS THE CENTRAL FINDING: a citation rule earns its cost at WRITE time, not
  at read time. Piccardi et al. (WWW 2020) measured 0.29% of Wikipedia page views producing
  a reference click - one in 300. The rule is not paying for itself by being consulted. It
  pays because (a) a writer who must produce an inline citation cannot write the sentence
  they cannot source, and (b) WP:BURDEN plus WP:CHALLENGE convert 'I disagree' into 'I may
  remove this', which resolves standoffs without argument. For a repo whose rule is
  per-claim repo@sha:path with a STALE flag, the design consequence is concrete: optimise
  the citation format for the CHECKER and for the writer's inability to hand-wave, and stop
  optimising it for a reader who will not follow it. repo@sha:path is already close to ideal
  on that axis - it is content-addressed, it cannot silently drift, and an agent resolves it
  for the cost of one file read, which is nothing like a human's cost of leaving the page.
  Note honestly that the transfer to agent readers is inference, not measurement; nobody has
  measured agent citation-following.
- TRANSFERS, AND IS THE UNBUILT HALF: pointing at a location is not the same as pinning a
  claim, and the 84% proves it. Every hop in that chain had a correct, resolvable citation
  to a real article at a stable URL. What drifted was the transcription of what the article
  said. A repo@sha:path citation has exactly the same hole: it proves the file existed in
  that state, not that the file says what the claim says. WP:V's own footnote defines the
  missing test - a source 'directly supports' material only 'if the information is present
  explicitly in the source' - and that is the one clause of Wikipedia's policy this repo has
  no analogue for. The cheapest fix that would actually catch an 84%-class error is
  requiring a quoted span alongside the path, so a checker can diff the claim against the
  quote without opening the file. A citation format that only pins WHERE is a format that
  passes review while carrying a fabrication.
- TRANSFERS: the interim flag needs a drain rule or it becomes the system. Wikipedia
  documented this about itself - 'Not all tags get addressed in a timely manner, staying in
  place for months or years, forming an ever-growing Wikipedia backlog-this itself can be a
  problem' - and the live counts today are 584,899 articles carrying an unsourced-statement
  tag and 540,218 needing additional references, with the community's own machine-maintained
  trend markers reading INCREASING on both. A STALE flag with no expiry, no owner, and no
  automatic promotion to REMOVED is a specification for that outcome at smaller scale.
  Wikipedia's remedy is not a better flag; it is keeping removal live, with the tag
  explicitly framed as 'an interim step to removing unsourced material'.
- TRANSFERS: narrow the scope of the citation rule in writing, or it degenerates. WP:V's
  central affordability decision is that it does NOT require a citation for everything -
  only quotations and material challenged or likely to be challenged. This is the thing
  'cite every substantive claim' repos get wrong, and the consequence is predictable in both
  directions: either everything gets a citation and none of them are checked, or the rule is
  quietly abandoned. The transferable artifact is a written list of which claim types
  require a citation.
- TRANSFERS: a review gate suppresses what is visible; it does not improve what is produced,
  and its cost is set entirely by reviewer supply. Tran et al. (2022) measured both - large
  significant effects on visible low-quality contributions, a consistent null on
  contribution quality, and a review latency ranging from two hours on German Wikipedia
  (19,994 reviewers) to over 13 days on Russian Wikipedia (2,422 reviewers) for the same
  extension. For redgate's human gate: do not justify a gate by claiming it will train
  better upstream behaviour, and do not specify a gate without specifying who staffs it.
  English Wikipedia's Pending Changes policy spends most of its length on where review must
  NOT apply, which is the scope discipline that keeps a gate staffable.
- TRANSFERS: put a peer acceptance step between 'someone wrote it down' and 'the fleet acts
  on it', and credit the author by name. Eureka's primary account is explicit that the
  validator must be a PEER and not 'some distant group of people working for management',
  and that the incentive was a byline rather than cash. This marketplace already believes in
  gates for code; Eureka is prior art for gating the knowledge artifact itself. The
  uncomfortable corollary from Cox (2007): the participatory design that made Eureka work
  was a consequence of lacking executive sponsorship, and sponsorship, when it arrived,
  truncated it.
- TRANSFERS: build the index as an entry point, not a catalogue. Luhmann's ZK II ran 3,200
  keyword entries against 67,000 slips, capped at one to four pointers per term, with - in
  Schmidt's words - 'no claim to providing a complete list of all cards in the collection
  that refer to a specific term.' The rationale Luhmann recorded is Ashby's: capacity comes
  from relations between nodes, not from point-to-point access. That is
  fleet-playbook-curator's invariant, stated in 1981.
- TRANSFERS: maintain aliases. Furnas et al. (1987) is the strongest number in this whole
  domain - two people favour the same term with probability below 0.20 across five domains -
  and the derived remedy is unlimited aliasing, which this marketplace implements nowhere.
  Every find-before-build or wayfinding step currently assumes a naming convention will
  hold. It will not, four times in five.
- REFUSE TO CITE - names, in order of how often this repo would be tempted: (1) '84% of KM
  programmes fail' attributed to Lucier & Torsilieri. The article says one third, and it is
  not a study - it is 'We estimate', from two Booz Allen partners' five years of involvement
  and discussions with participants in more than 70 leading programs. If the shape of the
  finding is wanted, cite the ONE THIRD and say it is a consultancy estimate. (2) '70% of KM
  initiatives fail'. Traces to a BT manager's oral estimate in Computerworld in 2000, who
  said in the same breath it does not mean they fail, and separately to Malhotra's analogy
  from a BPR figure footnoted to an HBR article about CRM. (3) '50% of KM projects fail' -
  attributed to 'some researchers' in 2000 and never resolved since. (4) 'Polanyi said tacit
  knowledge can be made explicit.' Gourlay, verbatim: 'Polanyi used "knowledge" to mean a
  process, "knowing", not an object.' Cite Nonaka for SECI; never cite Polanyi for it. (5)
  'The threshold for inclusion is verifiability, not truth' as live Wikipedia policy -
  coined 8 December 2004, removed July 2012 after a 30-day discussion, retained only as a
  historical footnote. (6) 'Eureka saved Xerox $100 million' - an insider estimate by the
  system's builders, about a project a PR agency selected for media appeal. (7) 'Backlinks /
  a second brain improve knowledge work.' No controlled study exists in either direction,
  and no honest adoption figure exists for Obsidian, Roam or Logseq. (8) Any adoption number
  for a PKM tool, full stop.
- REFUSE TO CITE, ADDED BY THIS DIVE AND POINTING AT THE SCOUT: 'No causal evidence exists
  that FlaggedRevs reduced vandalism.' It does - Tran et al., CSCW 2022, interrupted time
  series, 17 editions. This one matters more than the others because it was produced BY the
  debunking pass, in a corpus whose discipline is that an uncited claim is omitted or
  flagged. A negative claim ('I could not find X') is itself a claim, and it was asserted
  with the same confidence as the positive ones while being the easiest of them to falsify.
  The general rule this argues for: a couldNotEstablish entry should record the search that
  was run, not just the conclusion, so the next reader can tell the difference between 'does
  not exist' and 'I did not find it'.

### Dive 7 — This repo's own control arms, and the null it already owns

**Negative-control arm on a skill eval, and a recorded null result when it fails to
discriminate (VERIFIED)**  
*Mechanism:* Each promptfoo pack can wire a `skill: file://calibration-stub.md` variant — a
generic helpful-assistant persona with the skill's distinguishing mechanism removed —
alongside the real SKILL.md arm. Rubric semantics are INVERTED on that arm: calibration PASS
= the stub fails the invariant = the scenario discriminates; calibration FAIL = the base
model exhibits the behavior unaided = the scenario measures the model, not the skill. 8 of
12 packs carry a stub file; all 12 set repeat: 3.  
*Why leaders use it:* A with-skill-only eval cannot separate 'the skill works' from 'the
model would have done this anyway'. The control is the only thing that measures causal
effect rather than capability.  
*Failure mode:* The inverted rubric makes the arm a discriminability test, not an
effect-size measurement — it answers 'does this scenario have power?' and never 'how big is
the skill's delta?'. Scoring both arms against the SAME rubric would answer the second
question; no pack does that today.  
*Fit here:* Already shipped. The gap is not the control's absence but what the control is
asked to report.  
*Sources:* plugins/agent-compiler/evals/promptfoo/promptfooconfig.yaml:127-138 (read
2026-09-14) — the arm, commented 'negative control (calibration) — stub skill' ·
plugins/*/evals/promptfoo/calibration-stub.md — 7 files on disk (read 2026-09-14)

**Shipping a skill with NO control arm, on the strength of a written null result (VERIFIED)**  
*Mechanism:* verify-before-claim ran three rounds / six scenarios of negative control and
got a null every time: the base model, given only a gutted invariant-free stub and no
verification discipline, already produced the hedged, check-naming, flag-what-I-did-not-run
behavior the skill exists to require — including, in round 3, independently reproducing two
specific reference-file procedures (the merge-transitivity rule and the
primary-vs-secondary-source rule) with no skill injected. The pack therefore ships with the
calibration case deliberately REMOVED, the six scenarios and their verbatim grader quotes
recorded in a 90-line header comment, and a standing rule barring re-adding one without a
scenario argued in writing beforehand.  
*Why leaders use it:* It converts a null result into a durable constraint on future work
instead of discarding it. The comment names the two scenarios that DID discriminate in this
marketplace (semver-gate's non-transitive consent; wayfinder's type-lock and frontier
recomputation) and generalizes why: they were COUNTER to what a helpful assistant would
otherwise do, not merely specific.  
*Failure mode:* The finding is invisible outside that one file — it is not in
docs/testing.md, not in the corpus, and not in any tier's output. Its pointer is also
already stale: the comment says 'calibration-stub.md, since deleted — see git history if you
need its text', but `git log --all -- <that path>` returns nothing, so the file was never
committed and the history it points at does not exist.  
*Fit here:* This is the repo independently reproducing a CTXbench-shaped null on its own
material, for one skill, on a different task class from SWE-bench issue resolution — and
then doing the thing CTXbench's authors could not: keeping the skill anyway, for a reason
stated in writing ('the SKILL.md prose still gives that reflex a name, a repeatable
procedure, and specific vocabulary'), while explicitly declining to claim causal effect.  
*Sources:* plugins/verify-before-claim/evals/promptfoo/promptfooconfig.yaml:6-92 (read
2026-09-14) · git log --all --oneline --
plugins/verify-before-claim/evals/promptfoo/calibration-stub.md → empty (run 2026-09-14)

**Implications:**
- The repo is ahead of where the context-files scout placed it, and ahead of where dive B
  placed it. It has a negative-control mechanism, it has used it, and in one case it ran the
  experiment to a null and kept the written result. That is stronger evidence discipline
  than CTXbench's own authors applied to their v1, which asserted 'context files tend to
  reduce task success rates' without the significance testing that v2 added.
- The actionable gap is therefore NOT 'add a control'. It is two narrower things. First, the
  inverted rubric means no pack measures effect SIZE; scoring the stub arm against the same
  rubric as the treatment arm, on a pack already wired, converts a discriminability check
  into a measurement. Second, four packs have neither a control nor a recorded reason for
  its absence — and one of them, graveyard, is the plugin whose failure mode is irreversible
  repository deletion.
- verify-before-claim's header comment is the single most valuable artifact in this repo for
  the CTXbench question and it is unreachable: not in docs/testing.md, not in the corpus,
  not surfaced by any tier. Its own pointer to git history is already dead. Whatever else
  this corpus recommends, promoting that finding out of a YAML comment is the cheapest real
  win available.

---

## Corrections ledger

57 scout claims did not survive verification. This is the corpus's most useful artifact: it
is the measured error rate of primary-source-citing research agents on this material, and it
is roughly two in five. Every entry names what was claimed, what is true, and the evidence.

**[checking-ceiling] checking-ceiling** — claimed: '77.4% average balanced accuracy across
11 grounded-factuality datasets' is a finding of the MiniCheck EMNLP 2024 paper.

> It is not in the paper. The EMNLP 2024 paper (v2, 1 Oct 2024) evaluates on TEN datasets,
> not eleven — 'Figure 4: 10 datasets in LLM-AggreFact' — and its best reported figures are
> MiniCheck-FT5 74.7 and GPT-4 75.3 average BAcc without threshold tuning (75.1 / 73.8 with
> tuning). Bespoke-MiniCheck-7B does not appear in the paper at all; it is a later Bespoke
> Labs model. RAGTruth is the 11th dataset, added to the benchmark after publication. 77.4
> is a LEADERBOARD number, not a paper number. The scout's phrasing merges the two.

**[checking-ceiling] checking-ceiling** — claimed: 77.4 / Bespoke-MiniCheck-7B is the top
score, ahead of GPT-4o at 75.9.

> True of the public leaderboard, and I confirmed it exhaustively — I parsed the
> leaderboard's embedded data payload and recomputed the average for ALL 39 models (the
> default view shows only 11 of 39). Nothing on it exceeds 77.4. But it is NOT the highest
> published figure. HalluGuard (arXiv 2510.00880v1, 1 Oct 2025, Banque de Luxembourg / Univ.
> Luxembourg SnT et al.), Table 1, evaluates the same 11-dataset LLM-AggreFact with the same
> BAcc metric and reports Qwen3-32B at 77.6 average — above MiniCheck-7B's 77.4 (which they
> reproduce exactly). Qwen3-32B is not on the leaderboard.

**[checking-ceiling] checking-ceiling** — claimed: 'Is 77.4 still the top score as of
today?' — the scout flagged only that the leaderboard page carries no last-updated date.

> Stronger finding: the leaderboard appears frozen. The GitHub repository behind it,
> llm-aggrefact/llm-aggrefact.github.io, shows updated_at 2025-09-08 — roughly twelve months
> before this read (GitHub search API, 2026-09-14; I could not read its commit history, see
> blockedOrigins). Corroborating evidence from the data itself: the newest entries among all
> 39 models are Granite Guardian 3.3, Llama-3.3-70B-Instruct, QwQ-32B-Preview and Tulu-3,
> all 2024-2025 releases. There is NO 2026 frontier model on it. So 77.4 is the top score on
> a snapshot of the field as of roughly mid-2025, not a live measurement of today.

**[checking-ceiling] checking-ceiling** — claimed: couldNotEstablish: 'Any shipped tool that
performs claim-to-source entailment over SOURCE CODE or a repository, as opposed to prose
documents... None has a code-grounded evaluation split, so none of the ~77% ceiling numbers
transfer.'

> REFUTED as of July 2026. arXiv 2607.00895 ('Beyond Document Grounding', KR Labs / MBZUAI /
> McGill, v1 1 Jul 2026) builds exactly this: a unified span-level hallucination-detection
> benchmark with a code-agent split built from SWE-bench (2,015 test samples) and a
> developer-tool-output split (617), released with code, data and model checkpoints on
> GitHub and Hugging Face. Better still, it answers the transfer question directly and
> quantitatively: LettuceDetect-large, trained for natural-language RAG, 'reaches only 0.17
> span-F1' on code; the strongest zero-shot LLM judge reaches 0.22; gpt-oss-120b scores
> 0.177 on code versus 0.666 on README prose. A purpose-built fine-tuned 2B detector gets
> 0.602 on code versus 0.866 on README.

**[checking-ceiling] checking-ceiling** — claimed: RepoQA 'converts... into an exact-match
assertion' / 'string-matching the returned function is a deterministic grader'.

> Not exact match. Verified from §3.2 'Score computation': success requires (i) the returned
> function be the nearest of ALL candidate functions in context by smoothed BLEU, and (ii)
> BLEU(needle, returned) exceed a user-given threshold, 'by default 0.8 in our work'. There
> is also a tree-sitter syntactic-validity pre-filter. Deterministic — yes; exact — no;
> tunable — yes.

**[checking-ceiling] checking-ceiling** — claimed: RepoQA evaluated 33 models (scout) — the
arXiv abstract page says 26.

> Not a scout error; an arXiv metadata inconsistency. The /abs page abstract says '26
> general and code-specific LLMs'; the rendered full text of the same v1 says 33 in its
> abstract, §4 says 'We tested 33 major models on the 500 tasks', and Table 2 lists 33 rows.
> 33 is correct; the /abs metadata abstract is stale.

**[checking-ceiling] checking-ceiling** — claimed: GroUSE: 'NOT VERIFIED: per-framework pass
rates on the 144 tests... I read the abstract and intro, not the results tables.' Also cited
as 'arXiv Sept 2024, v3 Jan 2025' with no venue.

> Both now established. Venue: COLING 2025 (31st International Conference on Computational
> Linguistics, Abu Dhabi). Pass rates on the 144 unit tests, from Table 3: GPT-4 95.02,
> GPT-4-turbo 92.59, Gemini 1.0 Pro 83.22, finetuned Llama-3-8b 81.37, Llama-3-70b 79.17,
> Mixtral 8x22b 77.20, Mixtral 8x7b 74.65, GPT-3.5-turbo 71.18, Llama-3-8b 69.33, Prometheus
> 2 8x7b 54.98, Prometheus 2 7b 52.78. Adoption quantified: 11 citations (Semantic Scholar,
> 2026-09-14).

**[checking-ceiling] checking-ceiling** — claimed: Azure groundedness detection has
'span-level reasoning'.

> Minor paraphrase drift. The Microsoft doc as read 2026-09-14 says Reasoning mode 'Provides
> detailed explanations for detected ungrounded segments' — 'segments', not 'spans'. The doc
> nowhere commits to character- or token-level span offsets. Everything else the scout
> verified about the page holds, including that all four worked examples are synthetic
> single-entity contradictions and that correction is marked (preview).

**[checking-ceiling] checking-ceiling** — claimed: AWS's 'up to 99% accuracy' appears in
launch material with no methodology; scout could not find a dataset anywhere primary.

> CONFIRMED and tightened. I checked two primary AWS sources, not one. The What's New post
> (Aug 6, 2025) says verbatim: 'Automated Reasoning checks deliver up to 99% accuracy at
> detecting correct responses from LLMs - giving you provable assurance in detecting AI
> hallucinations.' The AWS News Blog (Danilo Poccia, Aug 6 2025, updated Aug 15 2025)
> restates it once as 'up to 99% verification accuracy' and cites nothing. The technical
> documentation, which does state the product's limitations in detail and in its own words,
> never repeats the figure at all. Note also what the claim is not: 'detecting CORRECT
> responses' is a true-negative rate on unspecified data, not an error rate on
> hallucinations.

**[contextfiles] contextfiles** — claimed: CTXbench (arXiv 2602.11988 ... v1 2026-02-12)

> The quoted sentences and the name CTXbench are from v2 (23 Jun 2026), not v1 (12 Feb
> 2026). In v1 the benchmark was called AGENTbench and CTXbench appears zero times in the v1
> full text (66 occurrences in v2). Anyone following the scout's citation to v1 will not
> find the benchmark under that name.

*Evidence:* https://arxiv.org/html/2602.11988v1 section headings '3 AGENTbench', '3.2
Generation of AGENTbench Instances'; https://arxiv.org/html/2602.11988v2 '3 CTXbench'. Both
fetched 2026-09-14. Shepard & Albrecht (arXiv:2606.20512) still cite it as AGENTBENCH,
showing they read v1.

**[contextfiles] contextfiles** — claimed: context files 'do not generally improve task
success rates' (quoted as the paper's finding)

> Verbatim and correct for v2 — but v1's abstract said something materially stronger and in
> the opposite spirit: 'we find that context files tend to reduce task success rates
> compared to providing no repository context, while also increasing inference cost by over
> 20%.' The authors softened from 'tend to reduce' to 'does not generally improve' between
> versions, and v2 added the significance testing (Tables 3 and 6) that v1 did not contain.
> v1 also framed the developer-file result as a positive: its section heading reads 'Human
> context files increase cost and performance'; v2 renamed that section and added 'neither
> statistically significant' to the conclusion. Citing this paper without pinning a version
> misrepresents which claim is being relied on.

*Evidence:* https://arxiv.org/abs/2602.11988v1 vs https://arxiv.org/abs/2602.11988v2
abstracts, and v1 Sec 4.2 heading vs v2 Sec 4.2 heading + Sec 6 conclusion. All fetched
2026-09-14.

**[contextfiles] contextfiles** — claimed: developer-written beats LLM-generated by 7%

> The 7% is verbatim from the v2 Introduction ('developer-committed files outperform
> LLM-generated ones by a significant margin of 7% on average') but it is a RELATIVE figure
> and the paper never says so. The body reports the same comparison in absolute points and
> never repeats '7%': Sec 4.2 says 'Developer-provided context files improve agent
> performance by 2.4% on average (p=21%), significantly outperforming LLM-generated ones
> (p=3.8%)'. Recomputing from Table 5, Dev-minus-LLM on CTXbench is +5.1, 0.0, +5.1, +6.5
> points across the four agents = 4.2 points absolute, which is ~7% relative to the LLM
> arm's ~57.8% base. So the paper mixes absolute and relative percentages for the same
> contrast in the same document. '7%' is also the ONLY comparison in the whole study that
> clears p<0.05, and it is a comparison of two treatments to each other — neither of which
> beat the no-context-file control significantly.

*Evidence:* https://arxiv.org/html/2602.11988v2 Introduction, Sec 4.2, Table 3, Table 5 (App
A.4). Fetched 2026-09-14.

**[contextfiles] contextfiles** — claimed: 'repository overviews ... are not helpful'
presented as an established finding

> Verbatim from the abstract, but the supporting evidence is a navigation-latency proxy
> (steps-to-first-gold-file), not an accuracy result. The paper's only direct accuracy
> ablation of the overview category (Table 7) shows removing the overview producing the
> LARGEST nominal accuracy DROP on CTXbench: 68.12% -> 62.32%, p=0.15. The authors' own
> careful summary is 'no category has a significant positive or negative effect on benchmark
> accuracy.' The abstract is stated more strongly than Table 7 supports.

*Evidence:* https://arxiv.org/html/2602.11988v2 Sec 4.3 'Context files do not provide
effective overviews' and Appendix B Table 7. Fetched 2026-09-14.

**[contextfiles] contextfiles** — claimed: agents.md 'neither states the query or date
behind the number' (re: 60k)

> Half wrong. The query IS stated — the '60k open-source projects' text is an anchor whose
> href is the exact GitHub code search (path:AGENTS.md NOT is:fork NOT is:archived,
> type=code), and a second link repeats it. The date is indeed not stated, and the count is
> not reproducible from any endpoint reachable without a GitHub login.

*Evidence:* agents.md page source, anchor extracted 2026-09-14.

**[contextfiles] contextfiles** — claimed: Windsurf character caps flagged as weak / rules
page 404s

> Upgraded to primary-sourced. The /rules URL does 404, but the content moved:
> docs.windsurf.com/windsurf/cascade/memories 302s to docs.devin.ai/desktop/cascade/memories
> (HTTP 200, fetched 2026-09-14) and states both numbers in a table and again in prose —
> global rules 6,000 characters, workspace rule files 12,000 characters each. Workflows are
> separately capped at 12,000 characters. What remains unestablished is whether the cap
> truncates, rejects, or only advises.

*Evidence:* https://docs.devin.ai/desktop/cascade/memories, fetched 2026-09-14 via the
docs.windsurf.com redirect.

**[contextfiles] contextfiles** — claimed: [tasking premise] the repo's behavioral tier only
ever runs the WITH-skill arm and has no control

> Not accurate as of the current tree. 8 of the 12 promptfoo packs already carry a
> negative-control arm that swaps in evals/promptfoo/calibration-stub.md, a generic
> 'general-helper' skill with the load-bearing rule removed: agent-compiler,
> find-before-build, redgate, scope-fence, semver-gate (3 uses), stop-rule,
> verify-before-claim, wayfinder (4 uses). All 12 packs set repeat: 3, so there is per-test
> sampling. Four packs have NO control arm at all: graveyard, voice, fleet-playbook-curator,
> tailscale-wif. The real gap is subtler than 'no control': the stub arm is graded with an
> INVERTED rubric whose PASS condition is that the bare model behaves the OLD way, so it
> measures rubric discriminability rather than skill lift, and no pack ever scores both arms
> against the same rubric to produce an effect size.

*Evidence:* /home/user/agent-plugins/plugins/*/evals/promptfoo/promptfooconfig.yaml and
plugins/redgate/evals/promptfoo/calibration-stub.md, read 2026-09-14.

**[edges] edges** — claimed: scout-semantic-layers: DataHub's lineage edge carries
'auditStamp, created, type, a properties bag, query' and FineGrainedLineage 'adds
transformOperation, confidenceScore, and the same query URN' — presented as one coherent
per-edge provenance record.

> 

**[edges] edges** — claimed: scout-semantic-layers treats matchType as a general per-edge
resolution verdict: 'EXACT when the reference already matched an existing entity, NORMALIZED
when it was rewritten, UNRESOLVED when it could not be resolved.'

> 

**[edges] edges** — claimed: scout-semantic-layers adoptionEvidence: 'Shipped model on
datahub master, read 2026-09-14' — implying settled design, reinforced by 'That is the
domain's revealed preference after ten years.'

> 

**[edges] edges** — claimed: scout-developer-portals, CODEOWNERS entry: 'MACHINE-CHECKED:
yes for target existence and permission, by the platform, continuously.'

> 

**[edges] edges** — claimed: Implied by the same entry: that GitHub's CODEOWNERS checking
makes the ownership edge load-bearing and safe at merge time.

> 

**[edges] edges** — claimed: scout-developer-portals: the CODEOWNERS errors API checks owner
existence and write access, quoting GitHub's docs.

> 

**[edges] edges** — claimed: scout-code-graphs, dependency-graph entry: 'machine-checked?
YES — a required check fails the PR on a bad edge delta.'

> 

**[edges] edges** — claimed: scout-code-graphs, bazel entry: 'machine-checked? YES — the
edge is load-bearing: if it is wrong or missing, the build breaks.' Flagged by the scout
itself as its own characterization.

> 

**[edges] edges** — claimed: scout-code-graphs: the SBOM export endpoint 'will cease
functioning after November 13, 2026'.

> 

**[edges] edges** — claimed: scout-code-graphs, dependency submission: 'I did not verify
that submitted edges appear in the compare/{basehead} diff — I extrapolated the compare
behavior.'

> 

**[edges] edges** — claimed: Dive brief / prior corpus: graphify's adoption evidence is
implausible — 107,831 stars five months after creation.

> 

**[folklore] folklore** — claimed: No causal study exists behind the German Wikipedia /
FlaggedRevs vandalism-reduction claim; listed under couldNotEstablish as 'I found no clean
causal study (interrupted time series, diff-in-diff against a comparable wiki)'.

> Tran, Champion, Hill & Greenstadt (2022) is an interrupted time series over panel data
> from 17 Wikipedia language editions including German, published at CSCW, DOI
> 10.1145/3555225. Effect on visible reverted contributions: -1.78 SD for IP editors, -1.759
> SD for first-time editors, -1.27 SD for all editors, all p<0.001. The scout named the
> exact method it could not find. One narrow part of the caution survives: the study reports
> a pooled effect with wiki-level fixed effects, not a German-specific effect size, so a
> claim about German Wikipedia's own numbers remains unestablished.

**[folklore] folklore** — claimed: '70% of KM initiatives fail' and '50% of KM projects
fail' could not be traced to any primary source; they 'circulate with no traceable origin at
all, usually attributed to Gartner or to studies show'.

> The 70% traces twice over, and to neither Gartner nor an anonymous study. (a)
> Computerworld, 3 July 2000: Daniel Morehead, director of organizational research at
> British Telecommunications, gives it as an oral estimate and immediately caveats it -
> 'that 70% doesn't mean they fail totally - it means that they don't accomplish what they
> set out to do.' (b) Malhotra, JKM 9(1), 2005, asserts it for KM by analogy from a
> business-process-reengineering figure, with a citation that resolves to a Harvard Business
> Review article about CRM. The 50% is untraceable and the scout's verdict stands for it.

**[folklore] folklore** — claimed: Gourlay 2006 argues 'three of the four modes admit
simpler explanations' (reported second-hand; Wiley 403).

> Gourlay's abstract, read verbatim from the author's accepted manuscript: 'Three of the
> modes appear plausible but none are supported by evidence that cannot be explained more
> simply.' Three modes are PLAUSIBLE; the simpler-explanation objection applies to all four.
> The scout's paraphrase understates the critique. The scout's other Gourlay claim - that
> the evidence base is anecdotal - is confirmed verbatim: 'the evidence adduced in support
> of the modes of knowledge conversion is either non-existent, anecdotal, or open to
> alternative explanations.'

**[folklore] folklore** — claimed: The Eureka '$100 million saved' figure comes from a 2002
first-person Reflections account titled 'The Eureka Story'.

> The figure appears in the abstract of Whalen & Bobrow (2011), the Cambridge University
> Press chapter in Making Work Visible, pp. 257-284: 'Eureka made its debut in 1994, and in
> the dozen years of its operation it has saved Xerox over $100M in service costs.' 'A dozen
> years' from 1994 lands around 2006, which a 2002 paper cannot assert. The scout conflated
> two distinct publications with reversed author order: Bobrow & Whalen (2002), Reflections
> 4(2), 47-59, and Whalen & Bobrow (2011), CUP. Separately, the independent Cox (2007)
> attributes the money claim to a third source again, an INSEAD teaching case (Biren 2000,
> p.10). The scout also asserted that technicians 'rejected payment' for tips; no primary
> source consulted says this - the primary says reputation was the greatest motivator and
> every tip carried a byline.

**[folklore] folklore** — claimed: WP:V requires citations for four named categories
including 'contentious material about living and recently deceased persons', quoted as a
single list.

> That wording is not in WP:V as of 2026-09-14. The current text reads: 'All quotations, and
> any material whose verifiability has been challenged or is likely to be challenged, must
> include an inline citation to a reliable source that directly supports the material.' The
> living-persons provision is a separate sentence elsewhere in the policy. The scout quoted
> a superseded version - which is itself an instance of the failure this dive is about.

**[folklore] folklore** — claimed: 'Luhmann called his slip box a communication partner' is
folklore; the slip says 'Junior-Partner'.

> 'Communication partner' is not folklore - it is the framing used by the Bielefeld
> Luhmann-Archiv's own scientific coordinator in a peer-reviewed article. Schmidt (2018)
> writes verbatim: 'the file acted as a communication partner in the research process',
> footnoted to Luhmann (1981), and Schmidt's own 2016 Brill chapter is titled 'Niklas
> Luhmann's Card Index: Thinking Tool, Communication Partner, Publication Machine'.
> Luhmann's 1981 essay is itself titled 'Kommunikation mit Zettelkästen'. The scout's
> underlying observation about the 'Junior-Partner' slip may well be accurate and is an
> interesting point about hierarchy, but I could NOT verify it - the Luhmann-Archiv slip
> viewer is JS-rendered and returned only page chrome. Classifying the scholarly consensus
> framing as folklore on the basis of an unverifiable slip reading is not supportable.

**[folklore] folklore** — claimed: Luhmann's output was 'nearly 600 publications, including
over 40 monographs' (Bielefeld archive page).

> Schmidt (2018), same institution, peer-reviewed: 'at the time of his death, his list of
> publications comprised more than 500 titles.' Schmidt separately notes posthumous
> publication since 1999 and about 150 further unpublished manuscripts. The two figures are
> reconcilable but are not the same number measured the same way. Pick one and say which.

**[folklore] folklore** — claimed: The 84% debunk in full - one-third not 84%, 'We estimate'
not a study, 70 leading programs, authors flag the 'failure' label themselves.

> Every clause checks out verbatim against the 1997 article. What the scout did not have is
> the paper that committed the error: Smith, Mills & Dion, IJKM 6(3), 2010, p.22, which
> cites Lucier & Torsilieri directly for the 84%. And the third hop, Tucker & Kotnour 2021,
> which cites Smith/Mills/Dion for it - by which point the 1997 article is no longer in the
> footnote at all.

**[goes-red]** SCOUT: 'todo_or_die (Ruby, searls, 361 stars); todo-or-die (Rust,
compile-time proc macros)' framed as 'the Rust crate and the JS/Python/Elixir/PHP ports are
each smaller reimplementations of the same README'. CORRECTED: by stars the Rust port is
LARGER — 590 stars vs the Ruby original's 361 (rendered GitHub HTML via WebFetch,
2026-09-14). By actual usage the ordering flips back: the Ruby gem has 674,927 downloads
(rubygems API) against the crate's 29,827 (crates.io API). Stars were the wrong instrument;
both registries were reachable and neither was consulted.

**[goes-red]** SCOUT: called expiring claims 'the sharpest mechanism I found' with no
caveat. CORRECTED: todo-or-die FAILS OPEN three independent ways, verified in source and by
execution — (1) `TODO_OR_DIE_SKIP=1` skips every macro (expired `after_date!` built green,
exit 0); (2) any error in a network-backed macro is swallowed by `eprintln!` and the build
succeeds (`issue_closed!` on a closed issue built green, exit 0 in 3/3 runs); (3) no
features are enabled by default, so a bare dependency checks nothing. The crate documents
(1) and (2) itself. Only `after_date!` and `rust_version!` are locally decidable and
therefore usable in an offline tier.

**[goes-red]** SCOUT: implied the Rust crate is current. CORRECTED: crates.io says
max_version 0.1.2 published 2021-09-17, 113 recent downloads; its dependency tree still
pulls hyper 0.14 / rustls 0.19-era crates. The Ruby gem's last version dates to 2022-07-01.
Both are dormant. (An intermediate docs.rs reading in this pass suggested a 2026 release
date; the registry API contradicts it and the API wins.)

**[goes-red]** SCOUT: mdBook 'logs an error and exits 0' for a broken include, citing issue
#1094. CORRECTED AND WORSENED: executed against mdbook v0.5.4 on 2026-09-14. The
missing-FILE case behaves as described (ERROR logged, exit 0) and additionally renders the
literal `{{#include ...}}` directive text into the published HTML. But the missing-ANCHOR
case — an existing file whose `ANCHOR:` marker was renamed or deleted, i.e. the actual drift
scenario — is COMPLETELY SILENT: no ERROR, no WARN, exit 0, and the transcluded content
renders as nothing. No issue was found covering that case; #1094 does not.

**[goes-red]** SCOUT: 'Issue #1094 read as open ... but I did not verify that PR's status.'
ESTABLISHED: PR #2277 'preprocess/links: fail for invalid links' is OPEN, not merged —
opened 2023-12-29, last activity 2026-08-21, carrying merge conflicts and awaiting author
action. Issue #1094 was opened 2019-11-11. The fail-open has stood roughly six years and ten
months.

**[goes-red]** SCOUT: 'Cog's --check exit code is undocumented on its own docs page and I
did not run it, so "fails CI" is inferred.' ESTABLISHED: exit code is 5, executed with
cogapp 3.6.0 on 2026-09-14 and confirmed in source (`except CogCheckFailed as err: ...
return 5`). The scout's sub-claim that it is undocumented is also confirmed — depend on
non-zero, not on 5.

**[goes-red]** SCOUT: 'Ships in the standard toolchain of four major languages with no
third-party install' treats the doctest family as uniform. CORRECTED on two counts. (a)
OPT-IN vs AUTOMATIC is a real split: Rust runs doctests under plain `cargo test` by default
and Go compiles every Example automatically, but Elixir requires an explicit `doctest
MyModule` per module and Python requires pointing `-m doctest`/`testmod`/`--doctest-modules`
at the files. Unregistered material is checked by nobody. (b) nbval is NOT standard
toolchain — it is a pip-installed pytest plugin (`import nbval` → ModuleNotFoundError here,
while `import doctest` resolved to /usr/lib/python3.11/doctest.py).

**[goes-red]** SCOUT: reported the Go `// Output:` nuance from documentation. SHARPENED by
execution: an Example without `// Output:` whose body calls `panic()` yields `ok ... [no
tests to run]`, exit 0 — never executed; the same Example with a type error yields `FAIL
[build failed]`, exit 1 — so it is compiled. Omitting the marker silently downgrades a
behavioural check to a compile check with no diagnostic anywhere.

**[goes-red]** SCOUT: 'Swimm's current state could not be established.' ESTABLISHED, with a
split result. swimm.io's 2026 homepage leads with 'Agentic modernization, delivered' and
markets legacy/mainframe/monolith modernization; Auto-sync and doc-drift detection do not
appear. docs.swimm.io still describes a documentation product with a Continuous Integration
section, but 'Auto-sync' is absent from its navigation. The company repositioned away from
doc-drift as its headline; the doc product survives; the named feature does not appear in
current public surfaces. The 2021-12-30 'completely optional' quote is verified verbatim and
remains the honest ceiling.

**[goes-red]** SCOUT: 'No published evaluation exists for any LLM-based doc-drift checker
... I found no benchmark for the task outside the 2021 AAAI research line.' HALF-CORRECTED.
The shipped half holds and I could not refute it: neither doc-drift nor driftcheck publishes
any metric. The research half does not hold: there is an active 2024-2026 line WITH
published numbers — C4RLLaMA (ICSE 2025; 65.0% / 55.9% correct comment updates just-in-time
/ post hoc), CCISolver, and FSE 2024 companion work. The scout's 'five-plus years old, with
no shipped descendant' should read 'actively researched, still unshipped'.

**[goes-red]** SCOUT: described doc-drift and driftcheck as reporting ('a PR comment, a
blocking check, or an interactive TUI'). CORRECTED: both default to BLOCKING — doc-drift's
`DRIFT_FAILS_BUILD` defaults to `true`, driftcheck blocks pushes unless `allow_push_on_error
= true`. Combined with publishing no precision figures, that is a worse position than
advisory, not a better one.

**[goes-red]** SCOUT (blockedOrigins): reported only api.github.com as blocked. EXTENDED:
plain `curl` to github.com HTML is ALSO blocked in this session, returning HTTP 403 with the
same 'GitHub access to this repository is not enabled for this session' body. Three routes
DO work and were used: WebFetch against rendered github.com pages (how all star counts here
were read), raw.githubusercontent.com (how todo-or-die's source and clap's lib.rs were
read), and `git ls-remote` (used to confirm six repos resolve).

**[goes-red]** THIS REPO'S OWN CLAIM, verified locally and failing: AGENTS.md:63 says the
cheap tier is 'Deterministic, offline, free, under a second' and evals/cheap/run.sh:3 says
'Runs in well under a second.' MEASURED 2026-09-14: 18.7s wall, 1290 checks, 25 plugins,
exit 0. A spec at
docs/superpowers/specs/2026-07-10-cost-isolated-eval-architecture-design.md already recorded
the fix — 'The stale header comment in evals/cheap/run.sh ("well under a second") is
corrected to the measured figure (~1.9s at three plugins)' — and it was never applied; that
replacement figure is now itself roughly 10x stale. This is the dive's own thesis
demonstrated on the repository that commissioned it: a claim everyone can read, a correction
already written down, and no comparison anywhere that can go red.

**[identity] scout-code-graphs (entry 1, LSIF)** — claimed: LSIF's documented death: opaque
globally-incrementing ids blocked incremental indexing and therefore diffing; SCIP was
created in response.

> Half right, and the half that is right does not say what the theme needs. Sourcegraph's
> post DOES say globally incrementing IDs made incremental indexing hard and made it
> 'difficult... to update an existing index with new information for only a subset of the
> documents'. It NEVER says diffing. And the SCIP design doc gives a different primary
> reason for dropping integer IDs entirely: blast radius of indexer bugs and debuggability.
> Most damaging to this dive's thesis: SCIP's replacement key is made ENTIRELY of mutable
> human-readable names (scheme + package manager/name/version + descriptor names). The most
> recent deliberate revisit of this exact trade-off went the opposite way from the claimed
> seven-domain convergence. It must be recorded as counter-evidence, not folded in as
> support.

*Evidence:* https://about.sourcegraph.com/blog/announcing-scip (2022-06-08);
https://raw.githubusercontent.com/sourcegraph/scip/main/docs/DESIGN.md;
https://raw.githubusercontent.com/sourcegraph/scip/main/scip.proto

**[identity] scout-semantic-layers (entry 2, OpenMetadata)** — claimed: Entity-to-entity
edges key on uuid — so a table rename preserves every table-level edge, which is the right
answer and the opposite of DataHub's.

> Overstated. The UUID preserves table-level edges only for a rename performed through
> OpenMetadata's own API. For a rename in the SOURCE system — the case the theme is about —
> nothing in `databaseServiceMetadataPipeline.json` detects a rename; the connector sees one
> FQN vanish and another appear. `markDeletedTables` defaults to TRUE and its own
> description says the soft-delete takes the lineage with it: 'Any related entities such as
> test suites or lineage information that were associated with those tables will also be
> deleted.' So on the shipped default, a source-side table rename destroys table-level
> lineage too. The UUID is a catalog-internal identity, not a cross-system one.

*Evidence:*
https://raw.githubusercontent.com/open-metadata/OpenMetadata/main/openmetadata-spec/src/main/resources/json/schema/metadataIngestion/databaseServiceMetadataPipeline.json
(markDeletedTables, default true); entityLineage.json; table.json (all read 2026-09-14)

**[identity] scout-developer-portals (entry 7, OpsLevel)** — claimed: Rename-safe identity
by alias accretion (old names never retired). NOT VERIFIED: whether an old alias can be
reclaimed by a different entity later... The doc does not say and I found no page that does.

> The page exists and the scout's open question has an answer: aliases are deletable and the
> namespace collides. OpsLevel's Components doc carries a FAQ titled 'Resolving Duplicate
> Alias Conflicts ("_2")' whose remedy begins 'Delete the existing alias' and ends by
> renaming the service twice to force the alias to be reassigned. So accretion is the
> default behaviour, not an invariant, and a rename into an occupied alias silently yields a
> `_2` suffix instead of the requested name. GitHub documents the same reclamation hazard
> for repo-name redirects in writing, which turns this from an OpsLevel gap into a general
> property of alias accretion.

*Evidence:* https://docs.opslevel.com/docs/components.md (updatedAt 2026-05-05) section
'Resolving Duplicate Alias Conflicts ("_2")';
https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository

**[identity] scout-semantic-layers (entry 0, DataHub)** — claimed: DataHub's partial
mitigation is narrow and telling: a lineage URN casing-normalization processor that rewrites
references to heal case mismatches only... Case is the only rename it can survive.

> Directionally right, mechanically wrong, and the real behaviour is worse. Casing is not
> healed after the fact by a repair processor — it is normalized at INGEST by per-connector
> configuration (`convert_urns_to_lowercase`, `convert_column_urns_to_lowercase`,
> `preserve_column_case`) before the URN is minted. Changing that configuration is itself a
> re-key event that ORPHANS existing entities, in DataHub's own words: 'that table's dataset
> URN changes... and the previously ingested entity is orphaned' and, for columns, 'Treat
> this as a one-way door... enabling it after data has been ingested re-keys every column
> and orphans column-level tags, glossary terms and documentation attached in the UI.'
> DataHub cannot survive a case change either; it can only agree in advance to spell things
> one way.

*Evidence:*
https://raw.githubusercontent.com/datahub-project/datahub/master/docs/how/updating-datahub.md
lines 143, 144, 280 (read 2026-09-14)

**[identity] all four scouts, implicitly — and the dive brief itself** — claimed: GitHub's
node_id already solves canonical identity; it is the stable key a rename cannot touch.

> GitHub does not document that. What it documents is: unique, opaque, and 'best practice to
> persist the global node ID so you can easily reference objects across API versions.' The
> words stable, immutable and permanent appear nowhere on either global-node-ID page. GitHub
> has already changed the VALUE of node_id once for every object, announced in advance —
> 'all object identifiers in GraphQL will change... these changes will also affect an
> object's node_id returned via the REST API' — with a stated plan to make the old values
> error. And there is no documentation at all covering node_id across a repository rename or
> a transfer between owners. The plugin's reliance on it is still the best available call;
> it just needs to be stated as a well-attested empirical regularity rather than a vendor
> guarantee, because an undocumented property is one that can change without a
> breaking-change notice.

*Evidence:* https://docs.github.com/en/graphql/guides/using-global-node-ids;
https://docs.github.com/en/graphql/guides/migrating-graphql-global-node-ids;
https://github.blog/2021-02-10-new-global-id-format-coming-to-graphql/ (2021-02-10)

**[identity] scout-km-prior-art (entry 0, authority control)** — claimed: Codified by
Charles Ammi Cutter, 'Rules for a Printed Dictionary Catalogue' (1876...). Mechanism: ...
every variant ... as 'see' references (4xx) pointing at it ... in a separate authority
record. verified: '2026-09-14'.

> The substance survives and I have now dated every layer from a primary, which the scout
> did not — its `verified` field was a bare date, not a verification. But the claim
> conflates two things a century apart. What Cutter codified in 1876 is one authorized form
> plus retained cross-references from every superseded name (rules 5, 15, 44 quoted verbatim
> in the pattern above) — as references WITHIN the catalogue. The SEPARATE authority record,
> as a distinct machine-readable object with 4XX See From Tracings, is the MARC authority
> format layer, whose LC documentation I can date to October 2009 (Introduction) and
> November 2016 (4XX page) but whose first publication date (widely given as 1976) I could
> NOT confirm from a primary LC page — the relevant LC history pages now 404. Use 1876 for
> the principle and the MARC 21 Authority format pages for the separate-record mechanism; do
> not date the separate record to 1876.

*Evidence:* archive.org cu31924029518978 (Cutter 1876, rules 5/15/44 read verbatim);
https://www.loc.gov/marc/authority/ad4xx.html (Nov 2016);
https://www.loc.gov/marc/authority/adintro.html (Oct 2009); IFLA ICP 2016 §5.3

**[in-repo-control-arms] context-files** — claimed: a behavioral tier that only ever runs
the *with*-skill arm — CTXbench's entire result depends on the *without* arm, which is the
control the repo's own line is asking for

> FALSE. The control arm exists and is wired in 8 of 12 packs as `skill:
> file://calibration-stub.md`, commented 'negative control (calibration)'.

*Evidence:* plugins/agent-compiler/evals/promptfoo/promptfooconfig.yaml:127-138; 7
calibration-stub.md files on disk

**[in-repo-control-arms] dive-contextfiles** — claimed: the cheapest experiment is a
one-line change on one pack — redgate or verify-before-claim, both already wired

> verify-before-claim is NOT wired, and is the worst possible choice. Its control was
> removed on purpose after six consecutive non-discriminating scenarios, with a standing
> in-file rule against re-adding one absent a scenario argued in writing first. Re-running
> it there would reproduce a null the repo already has. redgate IS wired and remains a valid
> target.

*Evidence:* plugins/verify-before-claim/evals/promptfoo/promptfooconfig.yaml:6-92

**[in-repo-control-arms] self** — claimed: 7 of 12 promptfoo packs have the control; 5 don't
— fleet-playbook-curator, graveyard, tailscale-wif, verify-before-claim, voice

> The file count (7 stub files, 5 packs without one) is right, but counting files misses
> that verify-before-claim's config carries the full control apparatus and its recorded
> removal. Packs with NO control and NO stated reason: fleet-playbook-curator, graveyard,
> tailscale-wif, voice — four, not five. graveyard is the one that deletes repositories.

*Evidence:* ls plugins/*/evals/promptfoo/calibration-stub.md (7); grep -ci
'calibration|negative control|stub' across all 12 configs


---

## Brainstormed proposals (both lenses, unfiltered)

Recorded as proposals, not recommendations. Nothing here is built, and anything touching
a skill goes through `grill-me` and clears `eval-ladder`'s bar first.

### Lens 1: absorb — minimal high-leverage adaptations

1. **`quoted-span` on the claim ledger.** Schema field + cheap-tier grep. Ranked first
   above; the only gate that catches a transcription error.
2. **`derivation-tag` enum, defaulting to `MANUAL`.** One enum, no validator, honest
   about being unvalidated.
3. **Same-rubric calibration arm** on one already-wired pack, `repeat` raised — converts
   a discriminability check into an effect-size measurement.
4. **Internal-oracle classification of every cheap-tier check.** Label each check by
   whether its oracle is inside the repo; anything external either moves tiers or states
   that green means "could not look."
5. **Generalize `check-testing-doc.sh`.** The repo already owns one hand-rolled
   generate-and-check instance and never abstracted it; it is the one mechanism in this
   survey that machine-enforces a prose doc bidirectionally against live state.
6. **A locally-reimplemented `after_date!`** — an expiry predicate on claims that names an
   API surface. The clock is the one external oracle a hermetic tier can trust.
7. **`repo_index_id`-style two-part freshness identity** — make the *curator's* version
   part of the staleness key, not just the fleet's, the way aider's `CACHE_VERSION` and
   DeepWiki's index id both do.
8. **A `STALE`-flag drain rule.** Wikipedia's unsourced-statement backlog stands at
   584,899 articles, trending negative by the community's own machinery. Any interim flag
   needs a rule that empties it or it becomes the permanent state.

### Lens 2: novel synthesis — what nobody has built

9. **A claim ledger whose entries are re-derivation commands rather than assertions.**
   The corpus's central finding is that trustworthy claims are derived or executed, never
   checked. A ledger entry that *is* a command plus its expected output is a doctest for
   a fleet, and nothing in this survey ships one.
10. **Derivation-tag-aware staleness.** `EXTRACTED` claims can be re-derived and diffed on
    every pass; `INFERRED` claims cannot and should expire on a clock instead. One field
    would let two different staleness policies coexist honestly — which is what every
    catalog in the survey needed and none built.
11. **A discriminating corpus built from this corpus's own corrections.** 57 verified
    misreadings, each with a source that says something different from the claim, is
    exactly the fixture set `eval-ladder` rung 1 asks for and exactly the shape the
    category has no benchmark for: a claim with a *perfect* citation and a *false* body.
12. **Publishing the negative results.** This repo has at least one recorded null about
    its own skills and it is invisible. A marketplace whose differentiator is eval
    discipline could ship the nulls as artifacts — the only thing in this survey nobody
    does, and the one a reviewer cannot get anywhere else.

---

## Sources

Every pattern's sources are in the JSON twin, one list per entry, dated. The dives above
carry their own per-claim sources inline. In-repo references cited in this note:

-
  `plugins/fleet-playbook-curator/skills/fleet-playbook-curator/scripts/validate-citations.sh:38-41`
-
  `plugins/fleet-playbook-curator/skills/fleet-playbook-curator/templates/fleet-playbook/index.schema.json`
- `plugins/verify-before-claim/evals/promptfoo/promptfooconfig.yaml:6-92`
- `plugins/agent-compiler/evals/promptfoo/promptfooconfig.yaml:127-138`
- `plugins/docs-hygiene/skills/docs-hygiene/SKILL.md:26`
- `.github/workflows/evals.yml:695-696`
- `AGENTS.md`, `evals/cheap/run.sh`, `docs/testing.md`
- [`harness-knowledge-graph.md`](harness-knowledge-graph.md) ·
  [`llm-wiki-patterns.md`](llm-wiki-patterns.md) ·
  [`agentic-patterns-corpus.md`](agentic-patterns-corpus.md)

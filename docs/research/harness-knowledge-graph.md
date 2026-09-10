# The Harness Software Delivery Knowledge Graph — and where it lands in this marketplace

**Status:** research note. Placement analysis, not a roadmap item.
**Question asked:** where does the Harness Knowledge Graph fit into our plugins?
**How it was produced:** read the Harness docs page and four Harness engineering
posts (sources at the bottom), then diffed their claims against every skill this
marketplace already ships and against this repo's own prior verdict on
knowledge-graph patterns in [`agentic-patterns-corpus.md`](agentic-patterns-corpus.md).

---

## The verdict

> **Not a new plugin, and not a change of mind about graph memory.** Harness's
> payoff comes from a condition a repo fleet does not meet: heterogeneous,
> non-git-native estate data (billing, K8s, CloudWatch, Jira, PagerDuty) with no
> single strongly-consistent query surface. A repo fleet already has one —
> `git`, `gh api`, `grep`. Harness's own ROI rule ("start with one use case that
> cannot be solved by a single system") is the exact test this domain fails.
>
> What Harness *does* change is **why** we say no, and it lands as evidence
> inside two skills we already ship. The corpus rejected knowledge graphs on
> weak evidence (one 198-document academic paper). That reason is now dead —
> Harness is a production deployment with a published cost argument and a
> published eval methodology. The rejection has to be re-based on domain fit,
> which is a stronger reason and survives the update. And their eval post is the
> best external instance of an `eval-ladder` we have found, containing one rung
> distinction our ladder does not currently name.

---

## What Harness actually built

A semantic layer between DevOps tooling and AI agents. Four stages: data sources
(Git, CI/CD, K8s, billing, incidents, policies) → Knowledge Graph (entities,
relationships, canonical identities, near-real-time sync) → semantic layer
(governed queries, RBAC filtering, structured + unstructured retrieval) → agents
(Expert Agents in chat/MCP, Worker Agents as pipeline steps).

**Entities:** Pipeline, Pipeline Execution, Stage, Step, Service, Environment,
Infrastructure, Artifact, Repository, Policy, Identity.

**Relationships:** declared, not inferred — which entities connect, which fields
to join on, cardinality, and a human-readable traversal name.

**Query surface:** HQL (Harness Query Language), a DSL over the graph. Every
field carries metadata (`field_type`, `unit`, `aggregation_functions`,
`searchable`/`sortable`/`groupable`), so the agent is told that
`duration = 'fast'` is invalid and that you may `SUM` it but not `GROUP BY` it.

**The cost argument** (their headline claim, one four-module question):
raw-API-via-MCP takes 5+ LLM calls and ~250k–350k input tokens; the KG path
takes 2–3 calls and ~12k. 15–25x, and deterministic rather than guessed.

**The four-tier data-ownership model**, ranked by determinism:

| Tier | Data class | Strategy | Determinism |
|---|---|---|---|
| 1 | understood and owned | Knowledge Graph + HQL | highest |
| 2 | understood, not fully modelable | event envelope via HQL + scoped content retrieval | high |
| 3 | understood, not owned | managed integrations | medium–high |
| 4 | neither owned nor modeled | external MCP | lowest |

With the standing order: default to Tier 1, continuously promote data up the
tiers, **"measure determinism, not just capability."**

**Their three named failure modes** — the part most useful to us:

1. *Modeling everything before solving anything.* 100 entities before a use
   case; the graph becomes academic and unused.
2. *Missing the relationships that create value.* Entities without the edge to
   the owning team or governing policy give shallow, wrong answers.
3. *Perfectly modeled data, a week old.* "Stale data is as dangerous as no
   data." Near-real-time sync is non-negotiable for delivery workflows.

---

## What this changes about our prior verdict

[`agentic-patterns-corpus.md`](agentic-patterns-corpus.md) rejected graph memory
twice, and the two rejections do not age the same way.

**Rejection A — evidence quality (now dead).**

> Knowledge-graph agentic RAG rests on one 198-document academic system, not
> leader adoption — treat as research, not roadmap.

Harness retires this. 1K+ enterprise customers, 40+ integrations, a published
cost model, a published eval methodology, and a Google Cloud Developer Connect
integration. It is leader adoption. Anyone re-reading the corpus should not still
cite the GRAG-ProSafe paper as the state of the art here.

**Rejection B — domain fit (holds, and is now the load-bearing reason).**

> a repo already has git, grep and a type checker as a better graph. Keep it out
> of rounds entirely

This survives contact with Harness intact, and Harness's own material is the
best argument for it. Their canonical-identity section — *"the same service is
called something different in Git, Kubernetes, CloudWatch, and your runbook"* —
names precisely the problem a graph solves. A fleet of GitHub repos has no such
problem: GitHub hands you a stable `node_id`, `gh api orgs/<owner>/repos` is a
strongly-consistent read, and the join key is not ambiguous. The graph is buying
normalization nobody in this domain needs to buy.

Net: keep the rejection, change the reason, and note that the reason is now
domain-scoped rather than universal. If this marketplace ever spans
non-git-native sources — cost data, incident history, runtime telemetry — the
argument reopens on its merits.

---

## Where it lands, ranked

### 1. `eval-ladder` — the strongest fit, and a real gap

Harness's ["Building Trust in the Harness Knowledge Graph with AI
Evals"][evals] is a published, production eval ladder for a *retrieval* system,
and it is stratified the way ours is: each layer catches a class the others
structurally cannot.

| Their rung | What it catches |
|---|---|
| Entity validation | does the required entity exist? |
| Relationship validation | can the required relationship be traversed? |
| Data validation | is the traversal populated, and fresh enough? |
| API-backed validation | does the result agree with an authoritative source? |
| Product-backed validation | does it reflect what a user can actually see? |
| AI eval | does the response meet the quality bar? |

Two things here are worth importing.

**(a) "A registered relationship is not necessarily a usable relationship."**
Their sharpest sentence. A query can be structurally valid, reference a
schema-declared relationship, execute successfully — and return nothing, because
the relationship was never populated with runtime data. This is exactly our rung
0's stated blind spot ("whether a sentence still *means* anything") reappearing
in the data layer, and we do not currently name the data-layer form of it. A
context/retrieval system needs a rung between *structural* and *code assertion*:
**declared ≠ populated ≠ fresh.**

**(b) Product-backed validation is our "grade the surface closest to the harm."**
Their finding is that API comparison confirms counts and ordering while missing
scope errors and associations that are technically valid but do not match what
the user sees. That is independent confirmation of our rule, from a team that
learned it by getting burned — and it is citable, third-party, and dated.

This is also good `eval-ladder` demonstration material: a live external ladder to
audit against our five audit questions, with the answers written down by its
authors.

### 2. `fleet-playbook-curator` — validated design, one named gap

Structurally this is the closest thing we ship to a knowledge graph, and Harness
independently arrived at two of its invariants:

| Harness | fleet-playbook-curator |
|---|---|
| "One entity. Many names. One truth." — canonical identity, alias support | members joined on GitHub `node_id`, never `full_name`, so a rename is not a remove+add |
| "Perfectly modeled data, a week old" — freshness is non-negotiable | deterministic detector stamps every member's `head_sha` every run as an independent staleness clock; every claim carries `repo@sha:path` and an as-of stamp |
| "Modeling everything before solving anything" | explicitly a router/index, not a CMDB or a runbook |
| Drift prevention as change management | facts auto-commit; interpretation is PR-only |

That is three of Harness's four theses arrived at independently, which is a
strong signal the plugin's design is right.

**The gap is the fourth.** Harness's second failure mode is *"missing the
relationships that create value."* The fleet manifest is a flat entity table —
`{node_id, name, full_name, default_branch, head_sha, pushed_at, archived,
private}` per member, sorted by `node_id`. There is no edge field of any kind.

Relationships are **not** unaddressed by the skill, and it would be wrong to say
so. `SKILL.md` names "cross-repo interactions" as exactly the kind of thing that
belongs in a playbook; every substantive claim — a relationship claim included —
must carry `repo@sha:path` and an as-of stamp or be omitted/flagged `STALE`; and
`validate-citations.sh` fails the build on any claim citing a repo not read this
pass or a path not in that repo's gathered tree. A relationship claim is cited,
and its citation is machine-checked for traceability.

What a relationship is not is **modeled**. Two consequences, both narrower than
"uncited" and both real:

- **No edge is diffable.** `diff-fleet.sh` cascades over membership and
  `pushed_at`; the staleness clock stamps a `head_sha` per member and nothing
  per edge. A relationship that quietly stops holding produces no `changed`
  signal of its own — the member's sha moves, but nothing says *which claim
  about it* that move invalidates.
- **Traceable is not supported.** `validate-citations.sh` says so itself:
  *"Semantic support of the claim by the file is the behavioral/verifier layer's
  job, not this deterministic gate."* For a single-repo claim the cited file
  usually *is* the evidence. For an edge, the evidence is the **join** — and a
  relationship claim can cite two real paths, both genuinely read this pass,
  while asserting an edge neither file supports. Nothing deterministic checks
  the join.

Harness's own fix is the right shape and the right size: *"map the relationships
for your chosen use case before expanding"* — not a general ontology. One
candidate use case, one or two edges, deterministic to derive:

- `repo --deploys-via--> workflow` (parse `.github/workflows/*.yml`)
- `repo --authenticates-as--> identity` (OIDC subject / WIF binding — the
  `tailscale-wif` domain)
- `repo --depends-on--> repo` (manifest/lockfile references within the fleet)

Any of those makes membership-change detection sharper: today a member going
`UNREADABLE` is a fact; with one edge it becomes "and three fleet members depend
on it." **Not a recommendation to build yet** — it is a candidate that should go
through `grill-me` and clear `eval-ladder`'s bar before anyone writes a line.

### 3. `agent-compiler`, `semver-gate`, `redgate` — prior art for the ceiling

The four-tier data-ownership table is the same construct as an effect ceiling and
as PATCH/MINOR/MAJOR classification: a typed ladder where you always take the
most-deterministic rung available, and never optimize for the least. Their
standing order — *"enable external MCP as an open extension point, but never
optimize for it"* — is a well-phrased version of what `agent-compiler`'s
`NO_EFFECT_CEILING` refusal enforces mechanically.

*"Measure determinism, not just capability — a feature that works 95% of the time
is worth more than one that works 70% of the time but can do anything"* is a
usable external citation for `verify-before-claim`'s thesis and for
`eval-ladder`'s pass^k rule.

### 4. `docs-hygiene` — corroboration, nothing new

*"Stale data is as dangerous as no data"* and Harness's drift-prevention framing
restate the failure shape `docs-hygiene` already names better than they do — the
GitOps controller reporting `Ready: True` while reconciling a stale artifact.
Cite it if it helps; it does not change the skill.

---

## What this research could not establish

- **Whether the 15–25x token claim reproduces.** It is a vendor benchmark on one
  self-chosen four-module question, with no published methodology, no
  independent replication, and an obvious incentive. The *direction* is
  believable — a typed schema beats field-name guessing — the multiplier is not
  evidence.
- **Whether the three failure modes are observed or marketing.** They read as
  hard-won and match this repo's own experience, but they appear on a product
  page with no incident write-ups behind them.
- **Whether one edge would actually improve fleet-playbook output.** Section 2
  argues from Harness's claim, not from a measurement on our own material. That
  measurement is cheap and has not been run.
- **Nothing about HQL's grammar.** No public specification was located; the
  comparison table in the vendor post is the only description found.
- The docs page was read through a search-index fetch, not directly —
  `developer.harness.io` is blocked by this container's egress proxy. Content
  matched the vendor blog posts on every overlapping claim, but it was not
  fetched from the origin.

---

## Sources

- Knowledge Graph Overview — https://developer.harness.io/harness-ai/use-harness-platform/knowledge-graph/overview
- Software Delivery Knowledge Graph (product) — https://www.harness.io/products/platform/knowledge-graph
- Why Harness AI Uses a Knowledge Graph, Not Raw APIs (2026-04-07) — https://www.harness.io/blog/why-harness-ai-uses-knowledge-graph
- [Building Trust in the Harness Knowledge Graph with AI Evals (2026-08-31)][evals]
- Shipping With Context using Knowledge / Context Graphs (2026-03-17) — https://www.harness.io/blog/knowledge-graphs-for-ai-software-delivery
- Knowledge Graphs + RAG Beat RAG-Only DevOps AI (2025-12-17) — https://www.harness.io/blog/knowledge-graph-rag

[evals]: https://www.harness.io/blog/building-trust-in-our-knowledge-graph

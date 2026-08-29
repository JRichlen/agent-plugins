# Agentic-patterns corpus

**Status:** research corpus + adoption roadmap for Red Gate (`docs/red-gate-protocol.md`).
**How it was produced:** a 21-agent tiered workflow — 5 Haiku scouts sweeping five source
clusters (Anthropic/Claude Code ecosystem, OpenAI+Google, mass-adoption frameworks,
practitioner products, novel/self-improving research), plain-code dedupe with a corpus rule
(nothing dropped; duplicates merged with sightings recorded), 13 Opus deep-dives verifying
every not-yet-covered pattern against primary sources, a two-lens brainstorm panel, and one
synthesis. Scout claims that failed primary-source verification are corrected in the dive
notes, not silently removed.

**Numbers:** 90 scout sightings → 88 unique patterns (3 already covered by the marketplace, kept in the corpus) → 94 deep-dive verifications → 16 brainstormed proposals → 1 roadmap.

The machine-readable corpus is [`agentic-patterns-corpus.json`](agentic-patterns-corpus.json) —
every pattern with mechanism, adoption tier + evidence, coverage status, scout sightings, and sources.

---

## The verdict

> Red Gate encodes its invariants as prose the model is asked to honor. The field has moved those same invariants into code: hook handlers, declared tool classes, pinned constraint blocks, provenance-typed records. Published work shows the prose layer failing under exactly Red Gate's conditions — compaction drops ratified constraints (0%→30% violation), and a self-editing agent deleted its own detection markers and faked a test log. The missing organ is enforcement, not more architecture.

## What it should become

> A protocol that compiles. Today Red Gate is prose a model is asked to honor; it should become a small set of declarations — round role, tool class, pinned criteria hash, out-of-bounds paths, budget handle — that a compiler turns into harness hooks, and whose compiler output is itself gated by the repo's own three tiers. Rounds stay human-gated; nothing here buys autonomy. Growth stays eval-gated: exhaust is typed, failures cluster into codes, recurrence proposes a scaffold red by default, and promotion from run to repo to marketplace scope requires a green tier and a human merge. The marketplace's exportable asset is the verifier proven able to fail — a gradeable environment carrying its own red-proof as provenance.

---

## Adopt now (ranked)

### 1. `criteria-pin` — prose+script

Hash CRITERIA.md at ratification; pin it as a stable prefix block; re-assert byte-identity after every compaction before the round may continue. Envelope tails append-only, criteria never move. Cheap-tier check plus a behavioral fixture that deliberately forces compaction and fails if the criteria did not survive.

**Why now:** Governance Decay measured prohibited-action violation going 0%→30% (up to 59%) when a constraint is dropped by compaction, and 0% when pinned. Same mechanism buys KV-prefix stability.  
**Derived from:** Constraint Pinning vs Governance Decay (arXiv 2606.22528); Manus/Anthropic prefix-stable caching

### 2. `reviewer-lockout` — prose+script

Add a frontmatter field per skill: round role plus tool class (END/verifier = read-only). Cheap-tier lint fails any END-role skill declaring edit or execute, and fails any round record whose fixer identity equals the author identity. The author of a red slice may not repair it.

**Why now:** Squad enforces author-cannot-fix-own-rejection in hooks, not prose; Factory ships tool class as a declared per-droid field. Red Gate already asserts this rule — nothing checks it.  
**Derived from:** Squad reviewer lockout (GitHub Blog); Factory custom-droid tool categories

### 3. `out-of-bounds-ledger` — prose+script

One invariant: nothing a round can write may gate that round. Declare an out-of-bounds path list (verifier scripts, eval packs, negative controls); cheap tier fails any round diff touching it. Type every persisted record runtime-verified or self-reported; self-reported never promotes.

**Why now:** Darwin Gödel Machine scored a perfect 2.0 by deleting the detection markers, and an agent faked a test log then read it as proof. Mutation control currently covers agents, not files.  
**Derived from:** Darwin Gödel Machine objective hacking; Airbnb gold-set discipline

### 4. `red-gate-hooks` — infra

Ship a red-gate plugin with hooks/hooks.json compiling the protocol into harness events: a Stop hook exiting 2 until the pinned verifier ran under a writer identity distinct from MIDDLE, PreToolUse masking write tools outside the named seam, SubagentStop asserting fan-out stayed read-only.

**Why now:** Claude Code exposes ~30 lifecycle events and only plugins/voice uses one. Hooks execute unconditionally where prose is advisory — the single load-bearing infrastructure gap found.  
**Derived from:** Claude Code hooks reference; Manus tool masking; Squad hook pipeline

### 5. `judge-calibration` — prose+script

An eval-pack contract for judged verifiers: one judge per dimension, hard negatives built by minimal edits to a known-passing run, A/B swapped, three-judge median, trajectory text capped well below 32K, per-sample caching for determinism, and a recorded agreement floor against a small expert gold set before a judge may gate.

**Why now:** Airbnb calls uncalibrated judges worse than none; Plan-RewardBench shows pointwise judging fragile and evaluators dropping below chance past 32K tokens. Non-code verifiers are the tier Red Gate leans on most.  
**Derived from:** Airbnb eval-driven development; Plan-RewardBench pairwise protocol

### 6. `consolidate-delta` — prose+script

dev-diary and fleet-playbook-curator stop rewriting and emit ADD/UPDATE/REMOVE deltas against discrete bullets carrying scope key, provenance and usage counters. Contradiction forces explicit retraction with a revision trail. Promotion run→repo→marketplace requires a green tier; a shape verifier proves supersession happened.

**Why now:** ACE documents rewrite-based consolidation collapsing 18,282 tokens→122 and below baseline; Memory Bank ships CREATED/UPDATED/DELETED. The growth loop's only ungated edge is exactly the memory-poisoning shape.  
**Derived from:** ACE delta playbooks; Gemini Memory Bank consolidation; Mem0 scope tags

## Adopt later

- escalation-ladder — cheap and prose-only, but ATLAS's unsat verdict is a research prototype; land it once red-END outcomes are typed by recurrence-detector so the third verdict has data behind it
- budget-gate — the affine non-cloneable budget handle is the clearest missing organ and has a 63-incident catalog, but needs PreToolUse debiting, so it waits on red-gate-hooks
- adversarial-end — mutation plus injection fixtures inside the existing pier sandbox; high teeth, but deep-tier changes are the most expensive to land and gate release
- provenance-ledger / OTel-shaped exhaust — turns EMIT into a typed span tree, but every gen_ai.* attribute is still Development stability, so the schema will churn under us
- recurrence-detector — SAMULE-shaped typed failure codes clustering into SCAFFOLD triggers; needs consolidate-delta's structured store to exist first
- deferred skill/tool loading — real 85% token and accuracy evidence, but Agent Skills already progressive-disclose name+description, so the marginal gain at 24 skills is unproven
- skill-ablation-gate — CP-Agent's 44-vs-800-line result makes this the honest test of a prescriptive marketplace, but its benchmark was partly repaired, so calibrate before deleting skills
- GEPA prompt evolution against the existing tiers — strong production adoption, but only safe once judge-calibration and out-of-bounds-ledger keep the optimizer outside the grader
- OpenShell / runtime-policy sandboxing under the deep tier — moves the cross-harness guarantee from harness behavior to runtime refusal; early preview, enforcement varies by host
- verifier-export as a gradeable environment package — the marketplace's exportable asset, but speculative until verifiers routinely emit scores rather than pass/fail

## Rejected despite adoption

Adoption alone is not fit. These were rejected with reasons:

- Mixture-of-Agents layered aggregation — real gains and a real paper, but it collides with single-writer MIDDLE and dissolves accountability; a red END already localizes blame to one round, one writer, one slice, a problem SOTA automated attribution solves at 14.2% step accuracy
- Durable-execution runtimes (Temporal/LangGraph checkpointers) — mass adoption, correctly diagnosed problem, wrong dependency; take the replayable append-only round journal shape, not the runtime, because here the human gate is the durability boundary
- LLM-driven dynamic speaker selection (AG2/AutoGen) — shipped in every major framework, but MAST attributes ~37% of multi-agent failures to inter-agent misalignment; human-gated rounds with a single writer are the deliberate opposite. Keep only constrained transition graphs and the 14 failure modes as negative-control rubric
- A2A wire protocol — 150+ orgs and Linux Foundation backing, but Red Gate is intra-repo, single-writer and human-gated with no remote opaque peers; borrow only the eight-state task vocabulary (input_required, auth_required) for round status
- Per-turn predictive model routing (GPT-5-style routers) — universal in consumer products, but a mis-route has no recovery path and per-turn switching destroys cache affinity (up to 12.5x prefix swing). Pin model and effort at BEGIN, hold to END
- Semantic/vector response caching — widely marketed, but the coding-agent adoption claim has no primary source and agent steps are not repeated queries; the real practice is prefix/KV stability, already absorbed by criteria-pin
- TDD-Agent dual-track refinement — test-first is confirmed and already Red Gate's BEGIN, but letting the agent refine the tests alongside the code is the exact reward-hacking mutation control exists to block. Name the rejection in the protocol
- Graph/knowledge-graph memory at round level — 3-5x the cost of flat RAG and needs a hand-built ontology; a repo already has git, grep and a type checker as a better graph. Keep it out of rounds entirely
- Self-modifying agent archives (Darwin Gödel Machine) — adopt the two invariants it proves by violating them, never the mechanism; a harness that can rewrite its own checker has no gate
- Concurrent fast-path/CoT racing — an inference-layer technique with no agent-orchestration deployments; racing two MIDDLE writers breaks single-writer and doubles cost to shave seconds off a human-gated round

## What this research could not establish

- No evidence on whether compiling protocol invariants into harness hooks actually improves outcomes — hooks are documented as enforcement, but nobody has published a before/after on an operating loop, and Anthropic's own docs warn `if` conditions fail open and PreToolUse timeouts do not block
- Whether a 24-skill prescriptive marketplace beats a bare loop with a short invariant line is unestablished; CP-Agent's ablation is one verifier-rich domain, one reference model, and a benchmark the authors partly repaired
- No calibration data for judged non-code verifiers in this repo's own domains (docs audits, shape checks); Airbnb's kappa floors and Plan-RewardBench's protocol are borrowed from other task distributions
- Cost and latency of the proposed enforcement layer is unmeasured — pinned criteria consume context on every request, three-judge medians triple grading cost, and no source quantifies the overhead at this scale
- Whether STORM's write-time mediation genuinely beats single-writer isolation is open: one May 2026 benchmark, no production track record, and it argues directly against a current Red Gate invariant
- Several load-bearing numbers could not be verified and were dropped rather than used: '31% of production queries hit cache', '85% of enterprises miss cost budgets', TALE's exact 68%/<5% figures, and Managed Agents GA pricing
- No source establishes how quickly the API-surface layer rots — extended thinking's budget_tokens went from shipped to 400-on-request inside a year, so any adopted mechanism naming an API needs an expiry this research cannot set

---

## The corpus — every unique pattern

Sorted by adoption tier, then novelty vs Red Gate. `sightings` = which scouts independently
surfaced it. Nothing found was dropped; `covered` rows are patterns the marketplace already absorbed.

| Pattern | Who | Adoption | Evidence | vs Red Gate | Sightings |
|---|---|---|---|---|---|
| **Agent Hooks / Lifecycle Handlers** | Claude Code 2026, Anthropic; CrewAI, LangGraph adopting | mass | Shipped default in Claude Code 2026; documented as production requirement | absent | 1 |
| **Prompt Caching Infrastructure** | Anthropic, OpenAI, Google; universal LLM provider adoption | mass | Default-on in Claude, GPT-4, Gemini; 31% of production queries hit cache | absent | 1 |
| **Extended Thinking Planning** | OpenAI o1/o3, Anthropic Claude 3.7/4.6, Google Gemini 3.6 | mass | Default in o3, Sonnet 4.6; 40-60% cost reduction on agents; shipped March 2026; 71.7% SWE- | absent | 1 |
| **Computer Use via Browser Automation** | Anthropic Computer Use API, Google Jules, Browser Use framework (108k  | mass | Browser Use #1 WebVoyager leaderboard (87.4%); Anthropic GA; Jules I/O 2026 demo; $76.8B m | absent | 1 |
| **Model Context Protocol (MCP)** | Anthropic, OpenAI, Google, Microsoft (universal adoption across model  | mass | 2026-07-28 spec release; universal adoption; industry standard; called 'USB-C for AI' | absent | 2 |
| **Graph-based Checkpoint/Restore** | LangGraph, OpenAI SDK, Anthropic, Microsoft AutoGen | mass | Default-on in LangGraph/OpenAI SDK; 100K+ agent executions/day on CrewAI alone; major vend | absent | 1 |
| **Prompt Caching for Agentic Loops** | OpenAI, Anthropic, Google; Devin, v0, Windsurf | mass | Built-in to OpenAI/Anthropic/Google APIs; default-on in major agents; research paper 2601. | absent | 1 |
| **MCP Federation with OAuth 2.1 & Hosted Endpoints** | Anthropic, AWS, Google Cloud, Salesforce, Vercel, HubSpot (2026 launch | mass | 10,000+ public servers; every major vendor 2026 launch uses hosted endpoints; ecosystem de | partial | 1 |
| **Structured Output Enforcement** | OpenAI GPT-5.2, Anthropic Claude, Google Gemini (all major labs) | mass | Default in latest models; JSON Mode deprecated; strict schema mode production standard by  | partial | 1 |
| **Tool Composition Chains (Multi-Tool Orchestration)** | LangGraph, CrewAI, AG2, all frameworks | mass | Default pattern in LangGraph/CrewAI/AG2; research into dynamic dependency retrieval | partial | 1 |
| **Skill Libraries (Standardized Skill Engineering)** | Anthropic open standard, Atlassian, Figma, Canva, Stripe, Notion partn | mass | 62,000 stars within 4 months of Anthropic standard; converged on by Fortune 500 builders;  | covered | 1 |
| **Mixture of Experts (MoE) with Learned Routing** | Qwen3 (3B active params beating dense models), DeepSeek-R1, Kimi K2.6  | mass | Qwen3 Next (Sept 2025): 3B active competes with larger dense; Kimi K2.6 (April 2026): 1T p | covered | 1 |
| **Framework Consolidation (LangGraph, CrewAI, AutoGen)** | LangChain (LangGraph 47M downloads), CrewAI ($18M Series A), 67% of en | mass | LangGraph 47M monthly downloads and 43% of enterprise deployments; market consolidation co | covered | 1 |
| **Tool Search / Dynamic Tool Loading** | CrewAI, LangChain, Microsoft AutoGen, LangGraph; enterprise adoption 2 | growing | Shipped in major frameworks; enterprise case studies; recent blog posts from Google Cloud, | absent | 1 |
| **Multi-Scope Memory Systems** | Mem0, CrewAI v1.15.1, LangGraph, LangChain; enterprise AI platforms | growing | CrewAI v1.15.1 unified Memory API; Mem0 2026 benchmarks; shipping across 4+ major framewor | absent | 1 |
| **Agent Observability / Distributed Tracing** | MLflow, Braintrust, Arize Phoenix, DeepEval, Ragas; $2.69B market in 2 | growing | LLM observability market $1.97B→$2.69B (2025-2026); 5+ major platforms; enterprise require | absent | 1 |
| **Intent Classification & Semantic Routing** | Multiple frameworks (LangGraph, LangChain, FastAPI agents); common ent | growing | Shipped in routing middleware; multiple blog posts on best practices; enterprise deploymen | absent | 1 |
| **Human-in-the-Loop Approval Workflows** | SAP Agents, Cloudflare Agents, enterprise AI platforms, financial syst | growing | Documented patterns in SAP, Cloudflare, multiple enterprises; common requirement in prod s | absent | 2 |
| **Async Agent Workflows & Long-Running Tasks** | Microsoft, AAFLOW, durable task frameworks (Durable Functions, Tempora | growing | Shipped in Azure Durable Functions, Temporal; research papers; enterprise adoption for hou | absent | 1 |
| **Budget-Aware Reasoning** | Research: TALE framework, Token Budget papers; enterprise deployment ( | growing | 85% of enterprises miss cost budgets; TALE 68% token reduction with <5% accuracy loss; act | absent | 1 |
| **Agent Sandboxing & Adversarial Testing** | RedTeamCUA (ICLR-class research); enterprise security; compliance-crit | growing | ICLR-class papers; active research; enterprise security programs adopting; emerging as com | absent | 1 |
| **Token Budget Enforcement** | Research frameworks; emerging enterprise tooling | growing | Token Budget papers (empirical catalog of 63 incidents); enterprise demand; frameworks eme | absent | 1 |
| **Mixture-of-Agents Hierarchical Aggregation** | MoA framework research; emerging adoption in reasoning tasks | growing | ICLR-class research; adopted by some frameworks; not yet default but rapid interest | absent | 1 |
| **Process Reward Models (PRMs)** | OpenAI, Anthropic, DeepSeek R1, academic research (AgentPRM, WebArbite | growing | AgentPRM published ACM WWW 2026; RLAnything RL evidence; SecCodePRM, GUI-Shepherd implemen | absent | 1 |
| **Agent Observability & Trace-Level Debugging** | Langfuse, LangSmith, Braintrust, MLflow, Maxim AI (entire platform mar | growing | 30%+ annual market growth; 85% of deployments lack visibility; McKinsey names trace-level  | absent | 1 |
| **Token Budget-Aware Reasoning** | Anthropic Claude, OpenAI reasoning models, cost-optimization framework | growing | Shipped March 2026; enables 40-60% cost reduction on agent workloads; critical for product | absent | 1 |
| **Managed Agent Infrastructure** | Anthropic Managed Agents, Google Vertex AI Agent Builder, OpenAI platf | growing | Anthropic GA April 2026 at $0.08/hour; Vertex standard offering; early users: Notion, Asan | absent | 1 |
| **Durable Execution (Workflow Orchestration)** | Temporal.io, OpenAI Agents SDK, Pydantic AI | growing | OpenAI Agents SDK integration GA March 2026; production deployment requirement for long-ru | absent | 1 |
| **Structured Output Validation (Schema-First)** | PydanticAI, OpenAI, Google Gemini, Anthropic | growing | PydanticAI framework adoption 2025; Google/OpenAI/Anthropic support structured outputs nat | absent | 1 |
| **Long-Context Memory Compression** | Multiple frameworks (DeepSeek, Qwen, LlamaIndex, Anthropic) | growing | Native support in Qwen2.5 1M and GPT 5.2; production systems require this for long-horizon | absent | 1 |
| **Synthetic Agentic Data Generation (Failure-Driven)** | Multiple research groups, org-wide training pipelines | growing | Recent 2025 frameworks (AgentSynth, SENTINEL, GenEnv); major org standard for agent fine-t | absent | 1 |
| **Agent Skills Abstraction & Composition** | Anthropic (Oct 2025 standard), research prototypes | growing | Anthropic formalized standard; PolySkill framework; emerging ecosystem across Claude produ | absent | 1 |
| **Multimodal Vision-Centric Agentic Reasoning** | Multiple frameworks, benchmark research | growing | Agent-X, VistaHop, SpatialWorld benchmarks; <50% success on complex multi-step visual task | absent | 1 |
| **Trajectory-Level Evaluation (Step Quality)** | LangSmith, DeepEval, Galileo, Phoenix | growing | Standard in 2025 evals frameworks; OWASP Top 10 LLM includes step-level audit; production  | absent | 1 |
| **Agent-to-Agent Communication Protocol (A2A)** | Google (April 2025), Linux Foundation, major orgs | growing | Google introduced April 2025; Linux Foundation adoption; ecosystem standard emerging | absent | 1 |
| **Resilience Patterns (Exponential Backoff + Jitter)** | All production frameworks, Temporal, LangGraph | growing | Production standard 2025-2026; best practices documented across frameworks; cost-critical  | absent | 1 |
| **Agentic SFT & Environment Tuning** | Research & orgs, fine-tuning frameworks | growing | Emerging 2025 practice for specialization; distinct from general LLM SFT; production pipel | absent | 1 |
| **Context Engineering** | Manus, Cognition/Devin, Cursor, Kiro | growing | Manus production platform; Cognition called it '#1 job of engineers building AI agents'; C | absent | 1 |
| **Architect/Editor Split** | Aider; state-of-the-art 85% on code editing benchmark | growing | Aider feature shipped; SOTA results with o1-preview architect + DeepSeek/o1-mini editor; m | absent | 1 |
| **Semantic Caching with Vector Embeddings** | Cursor, Manus, enterprise LLM systems | growing | Cursor ships native vector caching; production studies show 50-60% redundant computation r | absent | 1 |
| **Test-Driven Development for Agents (TDD-Agent)** | TDD-Agent paper, Windsurf with Claude, practitioners | growing | Published paper 2608.16742; Windsurf/Claude integration; Simon Willison agentic patterns g | absent | 1 |
| **Tool Masking & Least-Privilege Catalogs** | Manus, permit.io, agent safety research | growing | Manus production strategy; multiple safety papers (2602.16943, 2503.18666); enterprise age | absent | 1 |
| **Memory Consolidation (Episodic to Semantic)** | Anthropic Generative Agents pattern; Cursor, Manus, enterprise agents | growing | Cursor persistent memory; multiple production implementations; research 2502.06975 calls e | absent | 1 |
| **Agent Skill Composition (Modular Skills, not Tools)** | Replit Agent 3, Anthropic; SkillForge, HealthGuard systems | growing | Replit Agent 3 uses custom skills; Anthropic skills framework; multiple production systems | absent | 1 |
| **Sandbox/VM Isolation for Agent Execution** | Manus, OpenHands, Factory, Replit | growing | Manus, OpenHands, Factory ship with sandbox; Replit browser-based isolation; standard prac | absent | 1 |
| **Agent Validation/Evaluation Frameworks** | Braintrust, Galileo, SpecOps, multiple benchmarks | growing | Multiple published frameworks; GAIA benchmark, SWE-bench for agents; enterprise adoption;  | absent | 1 |
| **Dynamic System Prompt Optimization** | v0 by Vercel; cited as core reliability lever | growing | v0 blog credits it as 'one of three highest-impact reliability improvements'; multiple ven | absent | 1 |
| **Composite Model Architecture (Specialist Pipelining)** | v0 (base model + retrieval + QuickEdit + AutoFix); Replit Agent 3 | growing | v0 ships this; Replit uses multi-model composition; Anthropic model-routing research; acti | absent | 1 |
| **Event-Sourced Interaction Logging** | OpenHands, Cognition/Devin; core agent infrastructure | growing | OpenHands SDK architecture; Devin uses for debugging; standard in production agents; enabl | absent | 1 |
| **Tiered Memory Systems (Letta/MemGPT Model)** | Letta (formerly MemGPT), Anthropic research foundation, funded by Feli | growing | $10M seed round Sept 2024; Letta Code #1 ranked model-agnostic open-source agent; desktop  | absent | 1 |
| **Process Reward Models (Step-Level Supervision)** | OpenAI, researchers at Zhejiang/Stanford, EMNLP 2025 papers, DeepSeek, | growing | EMNLP 2025 main conference papers; shipping in frontier models; outperforms outcome superv | absent | 1 |
| **AlphaEvolve (Genetic Algorithm Agent Discovery)** | Google DeepMind, production general availability July 2026, deployed i | growing | July 2026 GA release; production use in genomics (30% error reduction), power grids (88% f | absent | 1 |
| **Human-in-the-Loop Breakpoints (Interrupt/Approval)** | LangGraph, Google Vertex AI ADK, AWS Bedrock AgentCore, OpenAI Agents  | growing | Shipping in all major frameworks; EU AI Act Aug 2026 enforcement drives adoption for high- | absent | 1 |
| **Agent Observability/Structured Tracing (AgentTrace pattern)** | LangSmith, AgentOps, Langfuse, MLflow, Braintrust, McKinsey identifies | growing | McKinsey 2026: lack of trace visibility top reason agent rollouts stall; ecosystem matured | absent | 1 |
| **Cost Optimization via Prompt Caching & Orchestration** | OpenAI, Anthropic, Azure, teams at enterprises deploying at scale 2025 | growing | 50-80% total cost reduction reported; 41-80% savings via caching; orchestration saves 41%  | absent | 1 |
| **Synthetic Data Generation at Scale (Agentic Pipelines)** | NVIDIA acquired Gretel.ai ($320M), Google, Amazon, Meta, OpenAI (trill | growing | NVIDIA $320M acquisition (2025); market $710M now, projected $2.3B by 2030; big tech opera | absent | 1 |
| **Multi-Turn State Management (STORM/Handoff Pattern)** | OpenAI Agents SDK (March 2025), Google Vertex AI, LangGraph, research  | growing | OpenAI SDK production release March 2025; STORM 82.5% macro pass on commit validation; fra | absent | 1 |
| **Knowledge Graph + Agentic RAG (MemGraphRAG)** | Production systems (GRAG-ProSafe QAS for safety management), academic  | growing | GRAG-ProSafe deployed for accident report analysis; production use in knowledge-intensive  | absent | 1 |
| **Circuit Breaker Resilience Pattern** | Production teams across BFSI, customer service, supply chain; pattern  | growing | Real-world examples of failures (hallucinated citations, false alerts causing outages); 15 | absent | 1 |
| **Constraint Boundary Enforcement (Progressive Sandboxing)** | MicroVMs (Firecracker/Kata), Kubernetes-native (ARMO), MCP sandboxing, | growing | Production patterns documented; MCP + code execution sandboxes shipping; policy as core sa | absent | 1 |
| **Autonomous Verification with Dedicated Verifier Agents** | ICLR 2026 research; OpenAI, Anthropic, Google deployments; autonomous  | growing | ICLR 2026 paper; multiple autonomous QA platforms; DevAssure, Shiplight report this as sta | partial | 1 |
| **Agentic RAG with Adaptive Retrieval** | Anthropic research, enterprise AI platforms; Agentic RAG papers 2025-2 | growing | Multiple 2025 papers; production deployments; Anthropic and others shipping as default in  | partial | 1 |
| **Failure Recovery Hierarchies** | Robotics agents, manipulation tasks, scientific workflows; multi-agent | growing | ICLR 2026 robotics papers; scientific computing platforms; distinct from basic error handl | partial | 1 |
| **Agent Handoffs** | OpenAI Agents SDK, Anthropic Cowork, Managed Agents infrastructure | growing | Agents SDK March 2025; April 2026 overhaul with subagent primitive (beta); next evolution  | partial | 1 |
| **Persistent Memory Banking** | Google Vertex AI Memory Bank, Anthropic Managed Agents, EverMemOS | growing | Default in Vertex AI Enterprise; major selling point; multiple 2026 papers (Mem0, MemVerse | partial | 1 |
| **Agentic Retrieval-Augmented Generation** | LangGraph, LangChain, A-RAG, APEX-Searcher research groups | growing | Comprehensive survey published Jan 2025; LangGraph native support; ACM SIGIR research trac | partial | 1 |
| **Long-Horizon Multi-Turn Planning** | Coding agents (Jules, Codex), KLong, LUMINA, AgentGym-RL research | growing | ICLR 2026 papers (KLong, LUMINA, AgentGym-RL); Jules async coding demonstrated; major bott | partial | 1 |
| **Semantic Routing to Specialized Agents** | vLLM Semantic Router, LangChain, RouteLLM, commercial implementations | growing | vLLM integration shipped; 40% cost reduction via model routing; Gartner 1,445% growth in m | partial | 1 |
| **Dynamic Speaker Selection (Multi-Agent Routing)** | AG2 (AutoGen), LangGraph, CrewAI, Google ADK | growing | AG2 v0.9 core feature; shipped in LangGraph conditional edges; 60% Fortune 500 use CrewAI  | partial | 1 |
| **Multi-Agent Coordinator/Droid Specialization** | Factory AI (Code/Review/Docs/Test/Knowledge droids); GitHub Squad | growing | Factory is production platform (2026); GitHub Squad open-source; multi-vendor blog posts o | partial | 1 |
| **Iterative Code Refinement via Execution Feedback** | Devin, Windsurf, RefAgent framework | growing | Devin specifically improved at handling CI failures; multiple frameworks (RefAgent 2511.03 | partial | 1 |
| **Self-Improving Agents with Reflexion Loops** | Anthropic, Airbnb production deployment (Oct 2025), NeurIPS 2025 works | growing | Airbnb published production case study reducing retraining cycles from months to weeks; co | partial | 1 |
| **Hierarchical Planning with Error Containment (ReAcTree/TDP)** | Academic research at Berkeley, production deployments in manufacturing | growing | Production deployments at scale; reduces token complexity vs monolithic planning; error is | partial | 1 |
| **Vision-Centric Multimodal Agents** | Agent-X (ICLR 2026), AgentVista, autonomous driving agents; research b | niche | ICLR 2026 conference acceptance; benchmark development; still challenging (top models <50% | absent | 1 |
| **Constraint Satisfaction Planning** | ATLAS travel planning, multi-agent research; specialized domains | niche | Research papers; enterprise travel/logistics; not mainstream but growing in specialized do | absent | 1 |
| **Asynchronous Queue-Based Orchestration** | Google Jules, async coding agent frameworks | niche | Jules demonstrated live at Google I/O 2026; Jitro V2 in development; emerging pattern in c | absent | 1 |
| **Neurosymbolic Constraint Planning** | CP-Agent, ATLAS, research groups | niche | CP-Agent ICSE 2026 publication; real-world benchmarks (ATLAS travel planning, AdaPlanBench | absent | 1 |
| **DSPy Program Optimization** | DSPy framework, researchers, org adoption | niche | Active 2025 research; DSPy A1 agent uses MIPROv2; growing adoption for prompt optimization | absent | 1 |
| **Graph-Based Semantic Reasoning (KG+Agent)** | KG-Agent, KARMA, research prototypes | niche | 2025 research frameworks (KBQA-o1, KnowCoder-A1); emerging production use in knowledge wor | absent | 1 |
| **Trajectory-Level Reward Modeling** | Anthropic, OpenAI research; Plan-RewardBench benchmark (2026) | niche | Plan-RewardBench published April 2026; RRO (Rising Reward Optimization) paper 2505.20737;  | absent | 1 |
| **Speculative Tool Calling & Asynchronous I/O** | Research systems; emerging in real-time agents | niche | Research papers 2605.13360, 2509.01920; not yet standard deployment but active 2025-2026 r | absent | 1 |
| **ACE (Agentic Context Engineering)** | Stanford, featured at ICLR 2025 submissions as emerging framework | niche | +10.6% improvement on agent tasks, +8.6% on finance; published research demonstrating meas | absent | 1 |
| **Darwin-Gödel Machine (Self-Modifying Code Agents)** | Sakana AI (Tokyo), announced May 2025 | niche | Improved SWE-bench from 20% to 50%, Polyglot 14.2% to 30.7%; published paper arXiv:2505.22 | absent | 1 |
| **GEPA (Reflective Prompt Evolution)** | DSPy framework developers, ICLR 2026 oral acceptance, production appli | niche | ICLR 2026 oral; outperforms MIPROv2 by +12pp on AIME-2025; production use case documented | absent | 1 |
| **Deterministic Sandboxed Execution** | NVIDIA NemoClaw, Wasm+WIT, academic frameworks (OS-Symphony, AgentScop | niche | NVIDIA NemoClaw shipped March 2026; Thoughtworks tech radar; gVisor/Firecracker adoption i | partial | 1 |
| **Episodic Memory + Policy Reflection** | SAMULE, MetaResearcher, research prototypes | niche | 2025 research (SAMULE framework); emerging in production systems for continual improvement | partial | 1 |
| **Specification-Driven Development (Specs-First)** | Kiro (AWS); spec-driven methodology emerging | niche | Kiro feature (2025); emerging practice; multiple blog posts on spec-first; not yet mainstr | partial | 1 |
| **Fast Inference vs. Chain-of-Thought Hybrid** | Research teams; not yet mainstream deployment (FastDriveCoT, concurren | research-only | Recent papers; no production deployments found; experimental frameworks only | absent | 1 |

---

## Deep-dive verifications

Every not-yet-covered pattern, verified by an Opus researcher against primary sources.
Scout claims that did not survive verification are called out in the implications.

### Dive 1

**Agent hooks / deterministic lifecycle handlers (VERIFIED, strongest fit)**  
*Mechanism:* Claude Code fires ~30 named events (PreToolUse, PostToolUse, PostToolBatch, SubagentStart/Stop, TaskCreated/Completed, Stop, StopFailure, PreCompact, InstructionsLoaded, FileChanged). Handlers are command|http|mcp_tool|prompt|agent. Exit 2 blocks; JSON hookSpecificOutput carries permissionDecision deny/allow/escalate, updatedInput, additionalContext. Plugins ship hooks/hooks.json with ${CLAUDE_PLUGIN_ROOT}. CrewAI mirrors this with @before_llm_call/@after_llm_call.  
*Why leaders use it:* Prompt-level rules are advisory; a model can rationalize past them. Hooks execute unconditionally in the harness, so guards, formatters and audit trails hold under context pressure and compaction.  
*Failure mode:* Docs warn `if` conditions fail open on unparseable Bash and are 'not for hard enforcement'; PreToolUse timeouts do not block; exit 1 is silently non-blocking.  
*Red Gate fit:* The END gate becomes a Stop hook of type agent/command that exits 2 until the pinned verifier ran — enforcing 'party that did not do the work' in the harness. PreToolUse enforces single-writer; SubagentStop enforces read-only fan-out. Only plugins/voice uses hooks today.  
*Sources:* https://code.claude.com/docs/en/hooks · https://code.claude.com/docs/en/plugins-reference · https://docs.crewai.com/en/learn/llm-hooks

**Prefix-stable prompt caching as a context-architecture constraint (VERIFIED; two scout entries were the same pattern)**  
*Mechanism:* cache_control ephemeral breakpoints (max 4) over a tools→system→messages hierarchy; 5m TTL at 1.25x write, 1h at 2x, reads 0.1x; 512–4096 token minimums by model; 20-block lookback. Any tool-definition edit invalidates every level. arXiv 2601.06007 (PwC, 31 Jan 2026, DeepResearch Bench, 500+ sessions) measured 41–80% cost cut, 13–31% TTFT gain — and that naive full-context caching can raise latency.  
*Why leaders use it:* Long-horizon agent loops resend the whole system+tools+history prefix every step. Caching is the difference between a viable and an unviable multi-round run.  
*Failure mode:* Cache thrash: mutating the front of the prompt (rotating tool sets, injected timestamps, changed thinking budget) silently converts every step into a full-price rewrite, and can increase latency.  
*Red Gate fit:* Turns Red Gate's pointer-envelope rule from a token-count heuristic into a measurable invariant: criteria travel verbatim at a STABLE prefix position, exhaust appends only at the tail. A cheap-tier check could assert round envelopes are append-only.  
*Sources:* https://platform.claude.com/docs/en/build-with-claude/prompt-caching · https://arxiv.org/abs/2601.06007

**Adaptive thinking + effort budgets (SCOUT CLAIM CORRECTED — 'extended thinking' is deprecated)**  
*Mechanism:* The scout's mechanism is stale. thinking:{type:'enabled',budget_tokens:N} is deprecated on Claude 4.6 and returns HTTP 400 on 4.7, Opus 5, Sonnet 5, Fable 5, Mythos 5. Current form is thinking:{type:'adaptive'} plus output_config:{effort:'high'} — the model decides whether to think at all per request, and interleaves between tool calls with no beta header. Opus 4.5/4.6+ retain and bill prior thinking blocks.  
*Why leaders use it:* Per-request depth control without hand-tuning budgets; low effort skips thinking on easy steps, which is where the real cost reduction on agent loops comes from.  
*Failure mode:* Changing budget_tokens or effort mid-conversation invalidates cache breakpoints (documented, with usage traces). Budgets >32k hit connection timeouts. The scout's 71.7%/48.9% SWE-bench figures are unsourced and I could not verify them.  
*Red Gate fit:* Effort is the missing dial on Red Gate's lazy-recursion budget pool: BEGIN (verifier design) and END (adversarial verification) run high effort; MIDDLE tracer slices run low. Must be pinned per round — changing it mid-round breaks the cache.  
*Sources:* https://platform.claude.com/docs/en/build-with-claude/extended-thinking · https://platform.claude.com/docs/en/build-with-claude/thinking

**MCP 2026-07-28: stateless core, Tasks extension, multi-round-trip requests**  
*Mechanism:* Confirmed real. Sessions and handshakes removed — each request carries its own protocol version, client identity and capabilities, enabling load-balanced servers with no shared store. MRTR replaces server-initiated streams: a tool returns resultType:'input_required' and the client resubmits with the original call. Mcp-Method/Mcp-Name headers allow gateway routing without body parsing. Tasks graduate to io.modelcontextprotocol/tasks with poll-based tasks/get + tasks/update. Roots, Sampling and Logging are now deprecated.  
*Why leaders use it:* Stateful MCP could not be horizontally scaled or put behind a normal gateway; Tasks gives long-running tool calls a durable handle instead of a held connection.  
*Failure mode:* Twelve-month deprecation window means a long tail of stateful servers; Sampling's deprecation removes the server-asks-the-model channel some agent designs relied on.  
*Red Gate fit:* MRTR's input_required is the protocol-level shape of a human gate — a Red Gate round boundary could be expressed as an MCP task rather than prose. Tasks/get gives END verification a pollable, resumable handle for slow verifiers.  
*Sources:* https://blog.modelcontextprotocol.io/posts/2026-07-28/

**Checkpoint/restore — real, but 'durable execution' is the contested half**  
*Mechanism:* LangGraph checkpointers persist state per superstep keyed by thread_id, with three durability modes: 'exit' (write only at graph exit, fastest, no mid-run recovery), 'async' (write while next step runs, small crash window), 'sync' (write before next step). Interrupt/resume reloads the last checkpoint and re-enters the interrupted node. Temporal and Diagrid ship plugins precisely because the base layer is not enough.  
*Why leaders use it:* Human-in-the-loop approval and crash recovery both need the run to survive a pause without replaying tool side effects.  
*Failure mode:* Widely argued that checkpoints preserve data, not execution: a run lives in one process and dies with it; two workers resuming the same thread_id have no built-in locking; InMemorySaver is not restart-durable.  
*Red Gate fit:* Red Gate rounds are already checkpoints, but nothing pins WHICH verifier version a round resumes against. Adopt the thread_id + pinned-verifier-hash idea; do NOT adopt LangGraph's runtime — the human gate is the durability boundary here.  
*Sources:* https://docs.langchain.com/oss/python/langgraph/durable-execution · https://reference.langchain.com/python/langgraph/types/Durability · https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows

**Browser/computer use (SCOUT MECHANISM WRONG — client-side, structure-first, not vision-first)**  
*Mechanism:* browser_toolset_20260801 and computer_toolset_20260801 went GA 19 Aug 2026. Anthropic runs nothing: 'your application runs every call against its own browser automation.' Primary targeting is read_page/find returning accessibility-tree refs ([ref_1]); coordinates are the fallback, not the mechanism. 27 default members; javascript_exec, read_console, read_network, file_upload are off by default. Batched actions run sequentially and abort the rest on first failure. Browser Use OSS scores 89.1% on WebVoyager (not 87.4%), a benchmark its own leaderboard calls saturated.  
*Why leaders use it:* Reaches systems with no API. Structure-first reading is cheaper and far more stable than screenshot-and-click loops.  
*Failure mode:* Anthropic documents prompt injection directly: Claude follows instructions found in page content, and tab titles/URLs are themselves an injection surface. Human approval for consequential actions is called mandatory.  
*Red Gate fit:* Mostly NOT a Red Gate primitive — it is a tool, not a loop shape. But it is a concrete new job for egress-gate (domain allowlist re-checked after redirects, refuse javascript:/file:/data:) and it gives non-code verifiers a real probe: a round's END check can be a live UI assertion.  
*Sources:* https://platform.claude.com/docs/en/agents-and-tools/tool-use/browser-use-tool · https://michaellivs.com/blog/state-of-browser-use-2026/ · https://www.firecrawl.dev/blog/best-browser-agents

**Implications:**
- Nothing in the scout list was vapor, but the list was mis-shaped: five of seven are model/protocol infrastructure, not loop architecture. The one genuinely load-bearing gap is hooks. Red Gate currently encodes its invariants as prose the model is asked to honor; Claude Code now offers ~30 lifecycle events where a plugin can enforce them unconditionally, and only plugins/voice uses even one (a SessionStart injector). The highest-value move is a red-gate plugin shipping hooks/hooks.json: a Stop hook that exits 2 until the pinned verifier has run, a PreToolUse matcher enforcing single-writer during MIDDLE, and a SubagentStop hook asserting fan-out stayed read-only. Hook types `prompt` and `agent` mean a judged rubric verifier — the non-code instance Red Gate already contemplates — can BE the gate rather than describe it.
- Two scout entries ("Prompt Caching Infrastructure" and "Prompt Caching for Agentic Loops") are one pattern double-counted, and its adoption evidence contained one fabricated-sounding statistic ("31% of production queries hit cache") I could not source; the underlying paper (arXiv 2601.06007, PwC, Jan 2026) is real and its 41–80% figure holds. Treat scout-supplied percentages as unverified by default.
- One scout mechanism was materially wrong and one was stale, both in the same direction — describing last year's API. Extended thinking with budget_tokens now returns 400 on every model from Opus 4.7 forward; the live pattern is adaptive thinking with output_config.effort. Anthropic's browser tool is client-side and accessibility-tree-first, not Anthropic-hosted computer vision. Any Red Gate doc that names an API surface needs a docs-hygiene check with a real expiry, because this layer is churning faster than the loop patterns above it.
- A cross-cutting invariant falls out of caching plus effort: prefix stability. Cache breakpoints die on tool-set edits, injected timestamps, and effort/budget changes; that makes Red Gate's "criteria travel verbatim" and "pointer envelopes" mechanically checkable rather than stylistic. Pin effort and tool set per round, append exhaust only at the tail, and add a cheap-tier assertion that round envelopes are append-only.

### Dive 2

**Deferred tool loading / Tool Search (on-demand schema retrieval)**  
*Mechanism:* Tools declared with `defer_loading: true` are withheld from context; a single `tool_search_tool` (regex or BM25/embedding variants) retrieves matching schemas mid-turn, which are then callable normally. Anthropic reports ~77K → ~8.7K prompt tokens on a 50+ MCP-tool setup (~85% cut), MCP metadata up to 40% of tokens, and accuracy 49%→74% (Opus 4) / 79.5%→88.1% (Opus 4.5). Stacklok MCP Optimizer and CrewAI/LangChain ship equivalents.  
*Why leaders use it:* Tool-schema bloat evicts working context and degrades selection accuracy; routers loading every schema collapse toward ~20% accuracy at hundreds of tools.  
*Failure mode:* Search miss makes a capability invisible: the agent claims it cannot do the task while the tool exists but was never retrieved.  
*Red Gate fit:* Directly applies: 24 skills + marketplace tools should be a deferred index, not a preamble. BEGIN retrieves only the verifier-relevant tools; MIDDLE's single writer retrieves its slice's tools. Add a 'tool retrieved but unused' / 'never retrieved' exhaust signal to the growth loop's DETECT stage.  
*Sources:* https://www.anthropic.com/engineering/advanced-tool-use · https://stacklok.com/blog/stackloks-mcp-optimizer-vs-anthropics-tool-search-tool-a-head-to-head-comparison/ · https://layered.dev/mcp-tool-schema-bloat-the-hidden-token-tax-and-how-to-fix-it/

**Agent observability via OpenTelemetry GenAI semantic conventions (execution provenance)**  
*Mechanism:* The whole run is a span tree, not isolated LLM calls: `gen_ai.operation.name` spans `create_agent`, `invoke_agent`, `invoke_workflow`, `execute_tool`, `retrieval`, `plan`, plus memory ops; `gen_ai.agent.id/name`, session and user attributes let failures be sliced by cohort. MCP conventions were folded into the same GenAI repo (v1.42.0 extraction), so MCP tool calls share the agent's trace vocabulary. Emitted by MLflow, Arize Phoenix, Braintrust, DeepEval.  
*Why leaders use it:* Multi-step agent failures are otherwise invisible post-hoc; structured spans turn 'it went wrong somewhere' into an isolatable step, and are now an enterprise procurement requirement.  
*Failure mode:* Conventions are still unstable — as of mid-2026 every gen_ai attribute/span/metric carries 'Development', none 'Stable'; instrumentation churns. Prompt/completion events also leak PII into traces.  
*Red Gate fit:* Red Gate's rounds already are a span tree (round → BEGIN/MIDDLE/END → recursion depth). Emit OTel-shaped exhaust: round id, verifier id, red-proof result, mutation-control result, writer identity, budget/depth. That exhaust becomes the machine-readable input to CONSOLIDATE and DETECT instead of prose diaries.  
*Sources:* https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet-heres-what-actually-shipped-in-2026-3mke · https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions · https://hidekazu-konishi.com/entry/opentelemetry_genai_semantic_conventions_guide.html

**Multi-scope memory with explicit scope tags and eviction**  
*Mechanism:* Every write is tagged with identity scopes — `user_id` (cross-session facts), `agent_id` (per-agent), `run_id`/`session_id` (task-local, deliberately not promoted), `app_id`/`org_id` (shared). Retrieval composes and re-ranks across scopes. Mem0 reports 92.5 LoCoMo, 94.4 LongMemEval, 64.1 BEAM@1M; CrewAI v1.15.1 unified its Memory API around the same scoping. Eviction/supersession is a first-class stage, not an afterthought.  
*Why leaders use it:* Prevents run-local scratch from contaminating durable user knowledge, and lets a long-lived agent recall across sessions without replaying full history.  
*Failure mode:* Memory poisoning and stale-fact lingering: a hallucination written through becomes ground truth downstream (documented 11-day recovery); contradictory facts both retrieved with no recency signal.  
*Red Gate fit:* Red Gate's growth loop has EMIT→CONSOLIDATE but no scope discipline. Tag exhaust by round_id / run_id / repo / org; only CONSOLIDATE promotes run-scope to repo-scope, and only a GATEd verifier promotes repo-scope to marketplace-scope. Promotion is the eviction control.  
*Sources:* https://mem0.ai/blog/state-of-ai-agent-memory-2026 · https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents · https://arxiv.org/abs/2504.19413

**Grammar-constrained decoding (structured output enforcement)**  
*Mechanism:* A CFG compiled from the developer's JSON Schema drives a per-token mask: after each token the engine computes the valid continuation set and zeroes the probability of everything else, so non-conforming output is unreachable rather than merely discouraged. CFGs (not just FSMs) allow recursive schemas. Shipped as strict schema mode across OpenAI, Anthropic and Google; older best-effort 'JSON mode' is deprecated in favor of it.  
*Why leaders use it:* Removes retry-and-repair loops and parser defensive code from agent plumbing; makes machine-to-machine handoffs between agents structurally safe.  
*Failure mode:* Constraint tax / tool suppression: with schema constraints plus tool calling enabled, several open-weight models stop calling tools entirely because tool-call tokens are masked unreachable; validity can also be bought with correctness.  
*Red Gate fit:* Fits the verifier, not the prose. Red Gate's pointer envelopes and 'criteria travel verbatim' rule should be a schema-enforced payload with a shape verifier; the cheap eval tier gains a schema-conformance check. Do NOT constrain MIDDLE's working turns — that is where tool suppression bites.  
*Sources:* https://openai.com/index/introducing-structured-outputs-in-the-api/ · https://www.aidancooper.co.uk/constrained-decoding/ · https://arxiv.org/abs/2606.25605

**MCP federation over OAuth 2.1 with audience-bound tokens**  
*Mechanism:* Remote MCP over HTTP with OAuth 2.1: PKCE mandatory for all clients, RFC 9728 protected-resource metadata for discovery, RFC 8414 AS metadata, RFC 8707 resource indicators binding a token's audience to one MCP server. Servers MUST validate the audience and MUST reject tokens not issued for them; token passthrough to downstream APIs is forbidden — the server obtains its own token via exchange or client credentials.  
*Why leaders use it:* Lets one agent federate many vendor-hosted tool servers without the client minting long-lived credentials, and closes the confused-deputy replay across privilege tiers.  
*Failure mode:* Spec compliance is not ecosystem reality: tool-description poisoning, rug-pulls, tool shadowing, 40+ MCP CVEs disclosed Jan–Apr 2026, ~66% of scanned servers with findings.  
*Red Gate fit:* Slots into egress-gate and tailscale-wif rather than the round loop: an audience-binding/no-passthrough check plus a pinned tool-description hash (rug-pull detector) is a natural cheap-tier verifier. Trust in a federated server is exactly the kind of claim verify-before-claim exists to refuse.  
*Sources:* https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization · https://www.descope.com/blog/post/mcp-auth-spec · https://pipelab.org/blog/state-of-mcp-security-2026/

**Cascade routing (keyword → embedding → classifier → LLM) with confidence thresholds and hop limits**  
*Mechanism:* Tiered dispatch by cost: sub-ms keyword filters for high-frequency unambiguous intents, embedding router (~16–100ms) for the bulk, fine-tuned classifier (50–200ms) for ambiguity, LLM catch-all (1–5s) for novel/compositional intents. Guardrails are the substance: confidence thresholds, a clarifying-question fallback, a hop limit on handoffs, a general-purpose safety net, and the inferred intent recorded on the trace.  
*Why leaders use it:* Keeps latency and cost off the common path while preserving an escape hatch, and stops handoff loops in multi-agent systems.  
*Failure mode:* Router becomes a single point of failure: misroutes cascade into five or six recovery round-trips; infinite handoff loops; silent low-confidence dispatch.  
*Red Gate fit:* Maps onto skill selection across 24 single-invariant skills and onto lazy recursion. The hop limit is Red Gate's depth counter; the confidence threshold should be an explicit 'name the seam or don't recurse' gate; log the chosen skill on the round trace so a misdispatch is exhaust, not silence.  
*Sources:* https://tianpan.co/blog/2026-04-16-intent-classification-agent-routers · https://redis.io/blog/llm-router-architecture-best-practices/ · https://www.patronus.ai/ai-agent-development/ai-agent-routing

**Declarative fan-out with merge reducers (multi-tool orchestration)**  
*Mechanism:* LangGraph's Send API spawns runtime branches each with their own payload; the runtime auto-parallelizes independent nodes within a superstep; every state key two branches may write MUST carry a reducer (e.g. `Annotated[list, operator.add]`) or concurrent writes clobber each other. The academic framing is a survey — multi-tool orchestration over long trajectories with intermediate state, execution feedback, cost and verifiability constraints — not a shipped mechanism.  
*Why leaders use it:* Turns independent tool work into one superstep instead of a serial chain, with a declared merge rule so parallel results combine deterministically.  
*Failure mode:* Unreduced concurrent writes silently overwrite; fan-out/fan-in with extra steps executes in orders users do not expect (open LangGraph issue #4026).  
*Red Gate fit:* Red Gate already has read-only fan-out + single writer, which is the stronger invariant — do NOT adopt parallel writers. Adopt only the reducer discipline: declare, per round, how fan-out findings merge into the writer's input, so a dropped scout result is a verifier failure rather than silence.  
*Sources:* https://arxiv.org/abs/2603.22862 · https://docs.langchain.com/oss/python/langgraph/use-graph-api · https://github.com/langchain-ai/langgraph/issues/4026

**Implications:**
- No pattern was vapor — all seven verified against primary sources, including arXiv 2603.22862, which is real (survey, 'The Evolution of Tool Use in LLM Agents', Mar 2026) but is a literature survey, not evidence that dependency-graph tool composition is a shipped default; the shipped mechanism evidence is LangGraph's Send API plus reducers. Two scout claims need correcting: OTel GenAI conventions are NOT stable (every gen_ai attribute still 'Development' as of mid-2026), and MCP OAuth 2.1 is a spec mandate, not ecosystem reality (40+ CVEs Jan–Apr 2026, ~66% of scanned servers with findings). The observability market figures are vendor marketing and should not be cited.
- The biggest genuine gap is that Red Gate has no machine-readable exhaust. Rounds already form a span tree; emitting it in OTel GenAI shape (round id, verifier id, red-proof outcome, mutation-control outcome, writer identity, depth/budget) would make DETECT a query rather than a reading exercise, and would let a verifier assert the loop actually ran red-first.
- Tool Search is the single highest-leverage import: 24 skills and a growing marketplace are exactly the schema-bloat regime where selection accuracy collapses. Make skill/tool loading deferred and retrieval-driven per round phase, and treat 'never retrieved' and 'retrieved but unused' as growth-loop signals about missing or dead organs.
- Scope discipline should be the promotion rule of the growth loop, borrowed from multi-scope memory: run-scope exhaust promotes to repo-scope only via CONSOLIDATE, and repo-scope to marketplace-scope only via a green eval tier. Memory-poisoning research (write-through hallucination becoming downstream ground truth) is the direct argument that unpromoted exhaust must never be retrievable as fact.
- Adopt constrained decoding only at the envelope boundary, never inside MIDDLE's working turns — the constraint-tax literature documents schema masks making tool-call tokens unreachable, which would silently disable the very tool use a round depends on. Likewise keep single-writer over LangGraph-style parallel writers; import the reducer discipline for fan-out merges, not the concurrency.

### Dive 3

**Durable approval gates (HITL as a persisted interrupt, not a prompt)**  
*Mechanism:* The gate is a runtime primitive that checkpoints state and suspends. LangGraph `interrupt()` writes the exact graph state to a checkpointer keyed by `thread_id`, waits indefinitely, and resumes via `Command(resume=value)` — the value becomes interrupt()'s return. Cloudflare `waitForApproval(step, {timeout: '7 days'})` backs the wait with Workflows (months-scale), with `approveWorkflow()`/`rejectWorkflow()` from the Agent. OpenAI Agents SDK: `needsApproval: true|async fn` on a tool; the call does NOT execute, a RunToolApprovalItem is recorded, the run pauses and returns `interruptions`, resolved by `state.approve()/reject()` (with `alwaysApprove`, rejection `message`), and approvals raised inside nested `agent.asTool()` runs surface on the OUTER run's state. Temporal: Signals + `workflow.wait_condition()` + durable timers, zero compute while waiting; the official `temporalio.contrib.openai_agents` integration went GA 2026-03-23. SAP's published pattern set layers confidence-based routing on top: HIGH → autonomous, MEDIUM → review, LOW → escalate, plus timeout/fallback and an audit-log entry per decision (action_type AUTONOMOUS/APPROVED, ai_confidence, human_reviewer).  
*Why leaders use it:* Irreversible actions (payments, deletions, transports, external comms) need a compliance-grade, auditable stop that survives process restarts and human latency measured in days, not a model that was merely told to ask.  
*Failure mode:* LangGraph documents that on resume the node restarts from its beginning — code before interrupt() runs AGAIN, so non-idempotent side effects double-fire. SAP's own guidance warns 'proceed' timeout fallback silently converts a gate into autonomy on irreversible actions.  
*Red Gate fit:* Red Gate's round boundary already IS this gate but is convention, not a durable primitive. Add a round-state envelope (pinned verifier hash + criteria verbatim + slice pointer) written to disk at BEGIN/END so a gate survives session death, plus an idempotency rule for MIDDLE re-entry. `prove-the-undo` should require the gate be durable for irreversible ops.  
*Sources:* https://docs.langchain.com/oss/python/langgraph/interrupts · https://developers.cloudflare.com/agents/concepts/agentic-patterns/human-in-the-loop/ · https://openai.github.io/openai-agents-js/guides/human-in-the-loop/

**Durable execution as the substrate for long-running agents**  
*Mechanism:* CORRECTION: the scout's source (arXiv 2605.02162, AAFLOW) does not support this pattern — AAFLOW is an HPC data-plane paper (Apache Arrow/Cylon zero-copy RAG pipelines, 4.64x pipeline speedup), not durable async agents. The real evidence is product surface: Temporal (agent loop = workflow, each model/tool call = a retriable activity; replay-based recovery; suspend/resume across arbitrary delays without holding a thread), Cloudflare Workflows/`AgentWorkflow` with `step.do` checkpoints and `reportProgress`, Azure Durable Functions, Inngest/DBOS/Restate, and LangGraph's checkpointer (thread_id as a persistent cursor enabling resume, time-travel debugging, fault-tolerant execution).  
*Why leaders use it:* Agent runs now span hours-to-days across approvals, retries, and crashed workers; without replayable state a restart loses the whole trajectory and re-spends the tokens that produced it.  
*Failure mode:* Replay determinism is a hard constraint most agent code violates (nondeterministic LLM output must be recorded in an activity, not re-derived); and checkpointed history grows unboundedly, so replay cost and context reconstruction become the new bottleneck.  
*Red Gate fit:* Fits the round ledger, not the agent. Make a Red Gate run a replayable artifact: append-only `rounds/NNN/{verifier.sh,criteria.md,slice.diff,end-result.json}`. That makes END re-runnable by an independent party days later and makes `context-handoff` a file format rather than a prose summary.  
*Sources:* https://arxiv.org/abs/2605.02162 · https://docs.temporal.io/ai-cookbook/human-in-the-loop-python · https://developers.cloudflare.com/agents/concepts/agentic-patterns/human-in-the-loop/

**Non-bypassable spend caps (budget as an owned value, not a monitored counter)**  
*Mechanism:* Verified: arXiv 2606.04056 (Khan, 2026-06-02) catalogs 63 confirmed production budget-overrun incidents across 21 orchestration sub-projects / 18 ecosystems (2023–2026), each backed by a quoted GitHub issue and where reported a dollar loss; four-class labels at Cohen's κ=0.837 (N=113); plus 47 supplementary 'budget-primitive-missing' structural entries. Mitigation: `token-budgets`, a 1,180-line Rust crate (no `unsafe`, no `Arc<Mutex<_>>` in the core Budget API) using AFFINE ownership so cloning, double-spending, or using a budget after delegating it are compile errors. Headline result is a mechanism split, not a marginal one: the M-delegation-fanout race (11 catalog incidents) overshoots 30/30 under asyncio but is rejected by the borrow checker; a properly locked Python counter also overshoots 0/30, so the claim is non-bypassability under operator error, not better arithmetic. Scope honesty is explicit: the dollar cap is runtime arithmetic under estimator assumption A1; static estimator over-reserves 4–6x (adaptive 2.11x, tokenizer-direct ~1.0x at 939–1,749 ms/spend); reasoning models (o-series, extended thinking, R1) fall OUTSIDE the guarantee because providers bill hidden reasoning tokens not bounded by max_output_tokens — there it is defense-in-depth behind provider controls (`reasoning_effort`, `thinking.budget_tokens`).  
*Why leaders use it:* A retry loop spending cents per attempt accumulates thousands of dollars on the DEPLOYER's account before an operator notices; frameworks ship no budget primitive at all.  
*Failure mode:* The affine layer structurally fixes only the budget-primitive-missing cluster and bounds others at the consequence level; the eight-way mechanism partition is exploratory (κ=0.44), binary-level cap soundness is left as Conjecture 1, and extended-thinking models escape Proposition 1 entirely.  
*Red Gate fit:* Red Gate already has a budget POOL for lazy recursion but no non-bypassability story. Make the pool a delegated, non-cloneable token: a sub-round receives a split of the parent's remaining budget and cannot mint more; depth counter + budget become one owned value. A `budget-gate` skill enforcing this at the harness level is a genuine missing organ.  
*Sources:* https://arxiv.org/abs/2606.04056 · https://github.com/sajjadanwar0/token-budgets

**Budget-aware reasoning depth (adaptive effort, not hard caps)**  
*Mechanism:* CORRECTION: this is a distinct pattern from the above and the scout cited the same source for both. Primary source is TALE (arXiv 2412.18547, Han/Wang et al.): CoT token usage is unnecessarily lengthy and compressible by putting a token budget IN the prompt, but the budget value dominates the effect — so TALE estimates per-problem reasoning complexity and sets the budget dynamically (searched or predicted), reporting large token-cost reduction at small accuracy loss. NOTE: the scout's '68% reduction / <5% accuracy loss' matches TALE's reported figures but I could not re-verify the exact numbers from the abstract text retrieved; treat as approximately-right, not quoted. The productized descendants are provider effort knobs (`reasoning_effort`, `thinking.budget_tokens`) and context-side scheduling: Anthropic's `clear_tool_uses_20250919` context-editing strategy (beta header `context-management-2025-06-27`) clears oldest tool results past a threshold and substitutes placeholder text, and SDK/server-side compaction which summarizes history instead of clearing it. The scout's '85% of enterprises miss cost budgets' stat is UNVERIFIED — I found no primary source and would not repeat it.  
*Why leaders use it:* Reasoning tokens are the dominant marginal cost of agent loops and long tool-use trajectories blow the window; effort must scale with task difficulty rather than being fixed per deployment.  
*Failure mode:* Budget-in-prompt is advisory — models overshoot or, worse, silently truncate reasoning and produce confidently wrong answers; and clearing tool results breaks prompt-cache prefixes and can delete the evidence a later step needed.  
*Red Gate fit:* Fits BEGIN, as verifier-shaped effort: the round's verifier difficulty should set the slice's effort tier, and the recursion trigger should be 'sub-criteria proven red', never 'ran out of thinking'. Add an explicit compaction point at each round END (round result is the summary), so compaction happens on a gate boundary rather than mid-slice.  
*Sources:* https://arxiv.org/abs/2412.18547 · https://platform.claude.com/docs/en/build-with-claude/context-editing · https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools

**Adversarial evaluation as a shipped harness (sandboxed red-teaming + OS-level containment)**  
*Mechanism:* Two verified halves. (1) Automated auditing: Anthropic's Petri (open-sourced Oct 6 2025) takes natural-language SEED INSTRUCTIONS, runs an auditor agent in parallel per seed that plans and drives multi-turn tool-use conversations against the target with simulated users/tools, then LLM judges score each transcript across safety dimensions and surface the worst; used in the Claude 4 / Sonnet 4.5 system cards and by UK AISI. (2) Adversarial environments: RedTeamCUA (arXiv 2505.21936) pairs a VM-based OS with Docker web platforms in one hybrid sandbox and — critically for eval economics — initializes tests DIRECTLY at the injection point so adversarial evaluation is decoupled from the agent's navigation ability; RTC-Bench has 864 examples. Results are not reassuring: Attempt Rate up to 92.5%, and end-to-end ASR of 83% for Claude 4.5 Opus | CUA. (3) Containment as the actual mitigation: Claude Code's OS-level Bash sandbox (macOS Seatbelt / Linux bubblewrap) enforces filesystem AND network isolation at the kernel, reported to cut prompt-injection attempts ~84% in Anthropic's internal usage.  
*Why leaders use it:* Indirect prompt injection is the live exploit class for anything with tool access, and manual transcript review does not scale to the behavior surface of a new model.  
*Failure mode:* Judge-scored auditing inherits the judge's blind spots and rewards seeds researchers already imagined; and containment is only as good as the deny rules — a bypass was found in Claude Code's `bashPermissions.ts` deny handling, so the sandbox is a boundary, not a proof.  
*Red Gate fit:* Strongest fit in the repo. Red Gate's 'verifier proven able to fail' is exactly Petri's negative-control discipline; generalize it to an ADVERSARIAL tier: the END verifier is run by an independent party against a mutated slice (contradictory instruction injected into a fixture, goal shifted). The graveyard deep tier's pier sandbox is already the delivery vehicle — add injection fixtures to it.  
*Sources:* https://www.anthropic.com/research/petri-open-source-auditing · https://arxiv.org/abs/2505.21936 · https://www.anthropic.com/engineering/how-we-contain-claude

**Layered aggregation (Mixture-of-Agents) — and the failure-attribution problem behind it**  
*Mechanism:* CORRECTION: the scout's cited source (arXiv 2605.14892) is NOT the MoA paper — it is a 2026 survey, 'Beyond Individual Intelligence', organizing multi-agent work into the LIFE progression (Lay capability / Integrate via collaboration / Find faults via attribution / Evolve via self-improvement). Real MoA is arXiv 2406.04692 (Wang, Zou et al., Together AI): layered architecture where every agent in layer N receives ALL layer N-1 outputs as auxiliary context and re-generates; open-source MoA scored 65.1% vs GPT-4 Omni's 57.5% on AlpacaEval 2.0, exploiting 'collaborativeness' — a model improves given peer outputs even from weaker peers. Adoption is real but narrow (Together's stack, leaderboard-style reasoning), not a production default. The survey's own emphasis is the more load-bearing finding: errors propagate across agents and rounds and rarely convert into structural improvement. Automated failure attribution (arXiv 2505.00212, ICML 2025, Who&When: 127 multi-agent failure logs annotated to responsible agent + decisive step) reports the best method at 53.5% agent identification and only 14.2% step identification, with o1/R1 below practical usability.  
*Why leaders use it:* MoA: cheap ensemble quality gain without retraining. Attribution: when a multi-agent run fails, teams currently bisect trajectories by hand, and that is the dominant debugging cost.  
*Failure mode:* MoA multiplies latency and token cost linearly in layers x agents and can converge on a shared error (peer outputs propagate a wrong premise rather than correcting it). Attribution: SOTA is near-random at pinpointing the decisive step.  
*Red Gate fit:* MoA should NOT be adopted — it directly contradicts Red Gate's single-writer MIDDLE and would blur accountability, the exact thing END verification exists to keep sharp. Attribution SHOULD: a run whose END went red already localizes blame to one round, one writer, one slice. Make that explicit as an exhaust record feeding CONSOLIDATE, and Red Gate becomes a structural answer to a problem the field measures at 14.2%.  
*Sources:* https://arxiv.org/abs/2605.14892 · https://arxiv.org/abs/2406.04692 · https://arxiv.org/abs/2505.00212

**Process reward models — step-wise scoring of trajectories**  
*Mechanism:* Verified: AgentPRM (arXiv 2511.08325, Fudan NLP + Ant Group). Key redefinition: unlike reasoning PRMs where a step is scored for CORRECTNESS, agent actions have no clear-cut correctness, so AgentPRM scores each decision on PROMISE (proximity to goal) and PROGRESS (contribution made), capturing interdependence between sequential decisions and balancing exploration/exploitation. Labels are obtained scalably via Temporal-Difference estimation combined with Generalized Advantage Estimation rather than expensive rollout-based MC labeling; reported >8x more compute-efficient than baselines, improving further with test-time compute scaling, and usable as the reward signal for RL on agents. Adoption caveat: this is a research artifact (published 2026-04-09, 1 citation) — the scout's framing of it as something OpenAI/Anthropic/DeepSeek 'use' is not established by this source; what IS established at those labs is outcome/process reward for reasoning models generally, not AgentPRM specifically.  
*Why leaders use it:* Outcome-only rewards give one bit of signal per multi-hour trajectory; step-wise scores make search, best-of-n at the step level, and RL on long agent runs tractable.  
*Failure mode:* PRMs are reward-hackable — an agent learns to emit steps that LOOK like progress; and TD/GAE labels inherit the behavior policy's distribution, so the PRM degrades exactly where the agent explores off-distribution.  
*Red Gate fit:* Adopt the FRAMING, not the model. Red Gate's verifier is an outcome reward at round granularity; 'promise and progress' names what a round's sub-criteria should measure when a criterion cannot be binary (docs audits, judged rubrics). Concretely: allow a verifier to emit a progress vector plus a hard red/green, and let a lazy-recursion trigger fire on progress stall — with the negative-control calibration the behavioral tier already runs as the anti-reward-hacking guard.  
*Sources:* https://arxiv.org/abs/2511.08325

**Implications:**
- Nothing here was vapor, but two scout sources were mis-attached: AAFLOW (2605.02162) is an HPC zero-copy RAG runtime, not durable async agents, and 2605.14892 is a multi-agent survey, not Mixture-of-Agents (real MoA is 2406.04692). The patterns survive on other primary evidence; the citations do not. Also drop the unsourced '85% of enterprises miss cost budgets' stat.
- Red Gate's biggest structural gap is durability, not decomposition. Every leader ships the human gate as a persisted, resumable primitive (interrupt+checkpointer, waitForApproval, Temporal signal) while Red Gate's round boundary is prose convention. Make the round a file-backed, replayable envelope — and inherit LangGraph's warning that resumed work re-runs from the top, so MIDDLE must be idempotent.
- Budget should stop being a number in a prompt and become an owned, delegable, non-cloneable value: the lazy-recursion budget pool plus depth counter unified into one token a sub-round cannot mint more of. This is the clearest missing organ (a `budget-gate` skill) and the field has a 63-incident catalog proving the failure class.
- The adversarial tier is where Red Gate can lead rather than catch up: 'a verifier proven able to fail' is already Petri's negative-control discipline. Extend END to run the pinned verifier against a mutated/injected slice inside the existing pier sandbox — an adversarial END is a cheap upgrade with real teeth given 83% CUA attack success rates.
- Explicitly refuse Mixture-of-Agents. Layered aggregation collides with single-writer MIDDLE and dissolves accountability; Red Gate's real edge over the field is that a red END already localizes a failure to one round, one writer, one slice — a problem SOTA automated attribution solves at 14.2%. Emit that localization as growth-loop exhaust.

### Dive 4

**Agent Observability & Trace-Level Debugging (OTel GenAI semconv as the convergence point)**  
*Mechanism:* OpenTelemetry's GenAI semantic conventions (CNCF SIG, still experimental) fix span/attribute names — gen_ai.operation.name of chat/invoke_agent/execute_tool, gen_ai.agent.id, gen_ai.tool.* — exported over OTLP; Langfuse, Arize, Datadog and Bedrock AgentCore all ingest the same endpoint. Claude Code emits natively: CLAUDE_CODE_ENABLE_TELEMETRY=1 plus OTEL_METRICS_EXPORTER/OTEL_LOGS_EXPORTER, 60s default export interval.  
*Why leaders use it:* Root-causing a failure across a multi-turn, multi-tool trajectory and attributing per-run cost. Most incidents are tool-call failures, context truncation and runaway loops — all invisible without spans.  
*Failure mode:* Past ~1k runs/day traces outrun human review; teams score 10-20% via LLM judges, and judge calibration drifts, needing periodic human revalidation. PII must be scrubbed in the instrumentation wrapper.  
*Red Gate fit:* END evidence today is prose plus exit codes. Emit each round as one OTel trace — BEGIN red-gate run, MIDDLE slice, END verify — so tool-call budget, depth counter and verifier sha become machine-checkable spans and feed EMIT→CONSOLIDATE automatically.  
*Sources:* https://langfuse.com/integrations/native/opentelemetry · https://code.claude.com/docs/en/monitoring-usage · https://www.braintrust.dev/articles/agent-observability-complete-guide-2026

**Token/effort budget-aware reasoning — SCOUT CLAIM CORRECTED: budget_tokens is a 2025 feature now deprecated, not a March 2026 ship**  
*Mechanism:* Anthropic docs: thinking:{type:'enabled',budget_tokens:N}, min 1024, must be < max_tokens (except interleaved thinking); the budget is a target, not a hard cap — max_tokens is the ceiling. Actual spend reads from usage.output_tokens_details.thinking_tokens. Deprecated on 4.6; Claude 4.7/Opus 5 reject it with 400. Successor: thinking:{type:'adaptive'} plus output_config:{effort:'high'}.  
*Why leaders use it:* Predictable latency and bounded per-request reasoning cost inside agent loops. With adaptive thinking the model decides whether to think at all, so effort is now the surviving cost knob.  
*Failure mode:* Changing budget_tokens between requests invalidates prompt-cache breakpoints (budget is rendered into the prompt). At low effort adaptive thinking may skip thinking entirely on inputs that needed it.  
*Red Gate fit:* Red Gate already budgets tool calls and depth; add a per-round reasoning budget expressed as effort tier — high at BEGIN (writing falsifiable criteria) and END (independent verification), low in MIDDLE. Pin the tier in the round envelope so caching does not churn.  
*Sources:* https://platform.claude.com/docs/en/build-with-claude/extended-thinking · https://platform.claude.com/docs/en/build-with-claude/thinking

**Managed agent infrastructure — SCOUT CLAIM CORRECTED: beta (managed-agents-2026-04-01 header), not GA; $0.08/session-hour is beta-era, unconfirmed for GA**  
*Mechanism:* Four primitives: Agent (model + system prompt + tools + MCP servers + skills), Environment (Anthropic cloud sandbox or self-hosted sandbox), Session (stateful, append-only event log, persistent filesystem, resumes after pause), Events (SSE stream you can steer or interrupt mid-run). Built-in bash/file/web tools, server-side prompt caching, compaction, and cron scheduled deployments.  
*Why leaders use it:* Hours-long autonomous runs without building an agent loop, sandbox or state store; sessions survive disconnects and can be steered without restarting the task.  
*Failure mode:* Stateful by design means it is NOT eligible for Zero Data Retention or a HIPAA BAA. Beta header required and behavior is refined between releases; runtime billing stacks on top of token cost.  
*Red Gate fit:* Its agent/environment/session split maps cleanly onto Red Gate roles: pin the verifier as an environment artifact and run END in a fresh session under a different agent config, so the worker structurally cannot edit the verifier. The agent 'skills' field carries this marketplace's plugins.  
*Sources:* https://platform.claude.com/docs/en/managed-agents/overview · https://platform.claude.com/docs/en/managed-agents/sessions · https://claude.com/blog/claude-managed-agents

**Durable execution for agent loops — SCOUT DATE CORRECTED: Temporal x OpenAI announced July 2025, not March 2026**  
*Mechanism:* The agent loop runs as a deterministic Temporal Workflow; every model invocation and tool call is an Activity written to an append-only event history. On crash a new worker replays that history, skipping completed activities and resuming exactly where it stalled; retries absorb rate limits and network faults. Wired via OpenAIAgentsPlugin; PydanticAI and Gemini have parallel integrations, with Inngest/DBOS/Restate competing.  
*Why leaders use it:* Long-running agents crash, get rate-limited and hit network faults. Without replay you re-pay tokens and lose hours of completed tool work.  
*Failure mode:* Workflow code must stay deterministic — nondeterministic edits between deployed versions break replay of in-flight histories. LLM nondeterminism must be quarantined inside activities.  
*Red Gate fit:* Adopt the shape, not Temporal. Make the round journal an append-only replayable record — pinned criteria, verifier sha, each slice's tool calls and their results — so an interrupted run resumes at the last green criterion instead of re-running BEGIN.  
*Sources:* https://docs.temporal.io/ai-cookbook/openai-agents-sdk-python · https://temporal.io/blog/announcing-openai-agents-sdk-integration · https://www.businesswire.com/news/home/20250730783559/en/Temporal-and-OpenAI-Launch-Integration-for-Enterprises-Developing-Production-Agents

**Schema-first structured output with bounded validation retries**  
*Mechanism:* Declare output_type on the agent; PydanticAI selects ToolOutput (schema as a tool call), NativeOutput (provider structured-output API) or PromptedOutput (schema injected into instructions). The response is validated against the Pydantic model; a validator raising ModelRetry sends a correction prompt back to the model, bounded by output_retries, while ToolFailed signals a terminal failure the model should adapt to.  
*Why leaders use it:* Converts a parse failure from an exception at the app boundary into a bounded, self-correcting retry loop, and makes agent-to-agent handoffs typed rather than prose.  
*Failure mode:* Constrained decoding taxes reasoning (Tam et al.: 10-30% degradation when the schema forces answer fields before chain-of-thought). Validity is not correctness: >84% JSON-valid vs <=80.4% value accuracy.  
*Red Gate fit:* Schema-validate the pointer envelope — round id, criteria verbatim, verifier sha, depth, budget pool — since a shape check is exactly a cheap-tier verifier. Do NOT schema-wrap MIDDLE reasoning: emit prose first, structure last.  
*Sources:* https://pydantic.dev/docs/ai/core-concepts/output/ · https://arxiv.org/pdf/2501.10868 · https://arxiv.org/pdf/2605.26128

**Server-side context compaction — SCOUT FRAMING CORRECTED: not 'optical self-compression' research, it is a shipped Anthropic API beta**  
*Mechanism:* context_management.edits with type compact_20260112 (beta header compact-2026-01-12). Trigger is input_tokens, default 150k, minimum 50k. At trigger the API emits a `compaction` content block containing a summary and drops all prior blocks on subsequent requests. pause_after_compaction yields stop_reason=='compaction' so you can splice recent messages back verbatim. Custom `instructions` fully replace the default prompt. Compaction spend appears only in usage.iterations, not top-level usage.  
*Why leaders use it:* Context rot: accuracy degrades sharply with length, so bounded context is a prerequisite for hours-long runs rather than mere overflow protection. Claude Code, Codex, LangChain and LlamaIndex all do this.  
*Failure mode:* Summarization is largely prompt-invariant, so instructions are an unreliable volume knob; the compactor cannot know what the agent will need later; top-level token accounting silently understates cost.  
*Red Gate fit:* Any Red Gate round long enough to compact will drop context. Use pause_after_compaction to splice the ratified criteria block back verbatim every time, and treat the compaction count as a round-budget signal that should trigger a round boundary rather than a longer round.  
*Sources:* https://platform.claude.com/docs/en/build-with-claude/compaction · https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents · https://arxiv.org/html/2605.23296v1

**NEW (not in scout list): compaction validation and constraint pinning — verifying that a summary preserved the contract**  
*Mechanism:* Governance Decay (arXiv 2606.22528): across 7 models and 1,323 episodes, compaction lifts prohibited-tool-action violation from 0% to 30% (up to 59%); 0% when the constraint survives the summary, 38% when dropped; soft org policies decay 8.3x more than hard safety norms; a Compaction-Eviction Attack forces eviction deliberately. Defense: Constraint Pinning, ~47 pinned tokens, restores 0%. Slipstream (arXiv 2605.08580) runs compaction asynchronously and has a judge validate the candidate summary against the agent's independently continued reasoning: +8.8pp accuracy, -39.7% latency.  
*Why leaders use it:* It is the only known mechanism that makes a summarizer accountable. Without it, standing instructions vanish silently and the agent behaves as if they were never ratified.  
*Failure mode:* Pinning consumes context on every request and only protects what you thought to pin; Slipstream's judge is itself an LLM and needs calibration, and asynchronous compaction costs parallel compute.  
*Red Gate fit:* This is the sharpest gap. Red Gate's 'criteria travel verbatim' is a norm with no enforcement. Add a post-compaction verifier that asserts the ratified criteria text is byte-identical to the pinned copy — a new cheap-tier check and a strong candidate for a `context-pin` skill.  
*Sources:* https://arxiv.org/abs/2606.22528 · https://arxiv.org/abs/2605.08580 · https://github.com/chenzhuofu/slipstream

**Failure-driven synthetic agentic data generation — REAL RESEARCH, WRONG LAYER for this marketplace**  
*Mechanism:* Rather than asking a model to invent task and solution together, these pipelines start from executable trajectories so every generated task has a feasible tool-call path with correct intermediate states (AgentSynth, Matrix, GenEnv). SENTINEL (arXiv 2606.12908) then generates tasks targeted at the current policy's observed failures, letting the RL training distribution track the model's learning state as a curriculum.  
*Why leaders use it:* Agent RL needs verifiable reward and tasks sitting at the frontier of the model's ability; broad synthetic distributions burn rollouts on tasks the policy already solves.  
*Failure mode:* Verifiability gap — model-invented tasks often have no feasible tool path. Failure-targeted curricula can overfit a narrow failure band and drift from the real task distribution.  
*Red Gate fit:* Do NOT adopt the training half; this marketplace fine-tunes nothing. Adopt the shape: generate behavioral-tier eval cases from real red-gate failures captured in dev-diary exhaust, targeting the observed failures of shipped skills. That is the growth loop with a curriculum.  
*Sources:* https://arxiv.org/pdf/2606.12908 · https://arxiv.org/html/2511.21686 · https://arxiv.org/pdf/2512.19682

**Implications:**
- Nothing on the scout list was vapor, but four claims failed primary-source check and must not propagate: budget_tokens shipped Feb 2025 and is now DEPRECATED (400 on Claude 4.7+, replaced by adaptive thinking + output_config.effort); Temporal x OpenAI was announced July 2025, not March 2026; Anthropic Managed Agents is a beta (managed-agents-2026-04-01), not GA, and $0.08/session-hour is beta-era pricing Anthropic has not committed to for GA; the '85% of deployments lack visibility' figure is inverted — McKinsey-cited numbers are 89% have observability and 62% can trace individual agent steps.
- The single most load-bearing gap: Red Gate assumes the context window faithfully carries the ratified contract. Governance Decay proves it does not — compaction drops standing constraints and violation jumps 0%->30% (up to 59%), and can be adversarially forced. 'Criteria travel verbatim' must stop being a norm and become a verifier: pin the criteria block (~tens of tokens), then assert byte-identity after every compaction. This is a cheap-tier check and a new `context-pin` skill.
- Red Gate's evidence layer is prose; the industry's is an append-only, replayable, OTel-traced event log. Making the round journal durable (Temporal's replay shape, not Temporal itself) and OTel-emitted (round/BEGIN/MIDDLE/END spans, gen_ai.* attributes) converts depth counters, budget pools and verifier shas from things the protocol asserts into things a machine reads back — and it makes the growth loop's EMIT stage free rather than manual.
- Schema-first belongs on the envelope, never on the reasoning. Constrained decoding costs 10-30% reasoning quality and JSON validity does not imply value correctness, so validate the pointer envelope and the criteria block against a schema (that IS the cheap tier) while leaving MIDDLE work unconstrained: prose first, structure last.
- Two patterns should be adopted only as shape, not as stack: durable execution (borrow replayable rounds, do not take on Temporal) and failure-driven synthetic data (borrow the curriculum idea to generate behavioral-tier eval cases from real dev-diary failures; this marketplace trains no models). Managed Agents, by contrast, is worth a real integration — its agent/environment/session split gives END structural independence the current fresh-agent convention only approximates.

### Dive 5

**Context engineering as the primary discipline (KV-cache, offload, restorable compaction, error retention)**  
*Mechanism:* Manus: KV-cache hit rate is the top production metric (~100:1 input:output; ~$0.30 vs $3.00/MTok cached vs uncached), so keep a byte-stable prefix, append-only context, no per-second timestamps; mask tools via constrained decoding instead of removing them (removal invalidates cache); offload to files as unlimited restorable context; recite goals into todo.md; keep failed actions and stack traces in context. Anthropic adds compaction, structured note-taking, just-in-time retrieval via identifiers (file paths/queries), and sub-agent context isolation.  
*Why leaders use it:* Long-horizon agents blow the window and the budget; cache discipline and offload cut latency/cost by ~10x while keeping goal adherence across dozens of tool calls.  
*Failure mode:* Context rot: Chroma found all 18 frontier models degrade as input grows; compaction silently deletes safety constraints ("governance decay").  
*Red Gate fit:* Red Gate's pointer envelopes are partial absorption — scout's "absent" is wrong. Absent: cache-stable round prefixes, restorable (not lossy) compaction, keep-red-evidence-in-context, and an END check that verifier criteria survived compaction verbatim. Candidate skill: context-budget / compaction-audit.  
*Sources:* https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus · https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents · https://www.trychroma.com/research/context-rot

**Durable execution for agents (journal, exactly-once side effects, suspend/resume at human gates)**  
*Mechanism:* Temporal/Inngest/Restate/DBOS model the agent as a workflow: every LLM and tool call is an activity whose result is journaled on first execution and replayed thereafter, giving persistence across crashes, exactly-once side effects, deterministic replay over non-deterministic LLM output, and suspend/resume across arbitrary waits for human approval. Idempotency keys derived from run-id + activity-id + attempt are passed to external APIs.  
*Why leaders use it:* Long-running agents crash, hit rate limits, and wait days for approvals; without a journal a restart re-executes irreversible side effects or loses all progress.  
*Failure mode:* Replay determinism is hard to hold: unjournaled non-determinism, non-idempotent external APIs, and journal bloat cause duplicate writes or silent divergence.  
*Red Gate fit:* Reframe the scout's "backoff+jitter" — that is trivia; the real pattern is durability. Red Gate rounds are already suspend/resume at human gates: make round state an append-only journal, and give prove-the-undo/graveyard idempotency keys so a resumed run cannot re-fire an irreversible delete.  
*Sources:* https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents · https://appscale.blog/en/blog/durable-execution-llm-agents-temporal-langgraph-checkpointing-2026 · https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/

**Trajectory-level evaluation (step quality, not just final answer)**  
*Mechanism:* LangSmith/agentevals split evals into three kinds: final response, single-step (did it pick the right tool), and trajectory (did it take the expected path). create_trajectory_match_evaluator compares against a reference trajectory in strict/unordered/subset/superset modes; LLM-judge variants score tool-call correctness, error recovery, and loop detection over the whole trace. Online evaluators run judges on sampled production traffic.  
*Why leaders use it:* An agent can reach a correct answer through a broken, expensive, or unsafe path; final-answer pass/fail hides regressions in tool choice, thrash loops, and recovery behavior.  
*Failure mode:* Judges are non-deterministic and costly; accuracy collapses on trajectories >32k tokens (pairwise judges below chance); reference trajectories are brittle to legal alternate paths.  
*Red Gate fit:* Genuine gap. Red Gate verifies artifacts at END, not the path taken. Add a trajectory verifier as a first-class verifier instance and a fourth eval concern: assert the round did BEGIN-red before MIDDLE, single-writer held, depth counter respected. Pairs with stop-rule and verify-before-claim.  
*Sources:* https://docs.langchain.com/langsmith/trajectory-evals · https://github.com/langchain-ai/agentevals · https://www.confident-ai.com/blog/llm-agent-evaluation-complete-guide

**Skill composition and polymorphic abstraction over a skill library**  
*Mechanism:* Agent Skills (Anthropic, Oct 2025; open standard at agentskills.io Dec 2025) is a SKILL.md folder with three-tier progressive disclosure: ~30-80 tokens of name+description at startup, full body (~275-8000 tokens) on trigger, references on demand. PolySkill (ICLR 2026) adds the missing layer: an abstract interface per domain (AbstractShoppingSite.search) with concrete subclasses, so skills compose and survive implementation churn — 1.7x reuse, +9.4% Mind2Web, +13.9% unseen, >20% fewer steps.  
*Why leaders use it:* Flat skill libraries neither compose nor transfer; abstraction decouples a skill's goal from a brittle site/tool-specific implementation and lets the agent chain skills goal-driven.  
*Failure mode:* Skill sprawl and supply chain: one study of 31,132 skills found 26.1% carried a vulnerability; SKILL.md is prose, so static analysis cannot screen injections.  
*Red Gate fit:* Correct the scout: this marketplace IS Agent Skills. Absent is the composition layer — 24 single-invariant skills with no abstract interface or chaining contract. Add an abstract "verifier" interface skills implement (check.sh, docs audit, judged rubric) so plugin-factory scaffolds subclasses, not one-offs.  
*Sources:* https://arxiv.org/abs/2510.15863 · https://arxiv.org/html/2510.15863 · https://www.newsletter.swirlai.com/p/agent-skills-progressive-disclosure

**Verifier-as-gradeable-environment (agentic RL environments, not agentic SFT)**  
*Mechanism:* The unit leaders actually ship is the environment, not the fine-tune: Prime Intellect's Environments Hub hosts 1k+ environments from 250+ creators with 100k+ downloads, packaged as installable modules exposing a task distribution plus a programmatic reward/verifier; prime-rl trains on them and INTELLECT-3 was trained on a mixture of open Hub environments (math, code, science, deep research, SWE). Failure-driven variants (step-rejection FT, P-BRIDGE) mine reward signal from failed trajectories.  
*Why leaders use it:* Specialization now comes from owning a verifiable environment; whoever can express a task as an auto-gradeable reward can both eval and train against it with the same artifact.  
*Failure mode:* Reward hacking and environment overfit; verifiers that pass on the training distribution and gate nothing real, plus heavy sandbox/infra cost per environment.  
*Red Gate fit:* Do NOT adopt fine-tuning — out of scope for a plugin marketplace. Do adopt the insight: a Red Gate verifier proven able to fail IS an RL environment. Add an export path from pier/promptfoo tiers to an environment package, and mine the growth loop's EMIT exhaust as failure trajectories.  
*Sources:* https://www.primeintellect.ai/blog/environments · https://docs.primeintellect.ai/tutorials-environments/environments · https://github.com/PrimeIntellect-ai/prime-rl

**A2A agent-to-agent protocol (task lifecycle state machine)**  
*Mechanism:* Donated by Google to the Linux Foundation on 23 Jun 2025; 150+ supporting organizations at the one-year mark, integrated across Google, Microsoft and AWS. Agents publish AgentCards for discovery and exchange JSON-RPC 2.0 (or gRPC / HTTP+JSON) messages over an eight-state Task lifecycle: submitted, working, input_required, auth_required, completed, failed, canceled, rejected. v1.0.1 (May 2026) adds an extension mechanism for new methods and state machines.  
*Why leaders use it:* Cross-vendor, cross-org delegation to opaque remote agents needs a discovery format and an explicit task state machine so a caller can tell "working" from "needs a human".  
*Failure mode:* Interop protocols cannot express authorization, accountability, or delegation limits; adoption is org-count-heavy and thin on production peer-to-peer traffic outside enterprise pilots.  
*Red Gate fit:* Mostly should NOT: Red Gate is intra-repo, single-writer, human-gated — no remote opaque peers. Borrow only the vocabulary: the 8-state lifecycle formalizes round status, and input_required/auth_required name the human gate and the egress-gate escalation precisely.  
*Sources:* https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year · https://github.com/a2aproject/A2A · https://en.wikipedia.org/wiki/Agent2Agent

**Vision-centric multimodal agentic reasoning**  
*Mechanism:* Agent-X (ICLR 2026, MBZUAI) benchmarks 828 agentic tasks over images, multi-image comparisons, video and instructional text across six environments (general visual reasoning, web browsing, security/surveillance, autonomous driving, sports, math), with a step-level framework grading each reasoning step's correctness, coherence, and tool-use effectiveness. Best GPT/Gemini/Qwen models clear <50% full-chain success.  
*Why leaders use it:* Browser, GUI, and physical-world agents must ground tool calls in pixels; text-only ReAct loops cannot verify what a screen or camera actually shows.  
*Failure mode:* Sub-50% full-chain success on multi-step visual tasks; errors compound across steps and spatial grounding degrades, so the loop is not yet production-trustworthy.  
*Red Gate fit:* Should NOT be absorbed as a Red Gate concern — it is a model capability, not an operating-loop pattern, and this marketplace is a text/CLI SDLC toolchain. Its only relevance: a screenshot/visual-diff verifier as one more instance of the verifier interface, if a UI plugin ever lands.  
*Sources:* https://arxiv.org/abs/2505.24876 · https://github.com/mbzuai-oryx/Agent-X · https://www.alphaxiv.org/overview/2505.24876v1

**Implications:**
- Nothing here is vapor, but two scout claims break. "Agent Skills absent" is false — the marketplace is built on the standard; the real gap is composition (an abstract verifier interface skills implement). And "exponential backoff + jitter" undersells the actual leader pattern, which is durable execution: journaled rounds, exactly-once irreversible side effects, suspend/resume at the human gate.
- Red Gate's largest genuine gap is that it verifies artifacts, not paths. Add trajectory-level verification as a first-class verifier instance — BEGIN proven red before MIDDLE, single-writer held, depth counter respected — with negative-control calibration, since judges collapse on long traces.
- Two patterns should be explicitly declined and the reasons written down: A2A's wire protocol (no remote opaque peers here; take only its 8-state lifecycle as round-status vocabulary) and multimodal agentic reasoning (a model capability, not an operating loop).
- The verifier is the marketplace's exportable asset. A verifier proven able to fail is the same object as a gradeable RL environment — an export path from the eval tiers, fed by the growth loop's failure exhaust, turns Red Gate's discipline into something outside consumers can run without adopting the whole protocol.
- Compaction is now a safety surface, not just a cost lever: published work shows compaction silently deleting governance constraints. "Criteria travel verbatim" needs to become an enforced post-compaction check, not a convention.

### Dive 6

**Architect/Editor split (two-model, two-pass)**  
*Mechanism:* Aider's `--architect` mode: pass 1, a reasoning model sees the repo map + files and emits prose describing the change, no diff format. Pass 2, a separate cheap 'editor' model receives that prose plus the files and emits only search/replace blocks, which Aider applies. Config is `--architect-model` / `--editor-model`; the editor gets its own edit-format (`diff`, `editor-diff`, `whole`).  
*Why leaders use it:* Reasoning models plan well but fail at emitting byte-exact diffs; splitting lets each model do one job and decouples plan quality from edit-format compliance.  
*Failure mode:* Two serial calls double cost/latency; Aider notes it is 'quite slow, probably not practical for interactive use', and it loses to single-pass on single-file edits where plan == code.  
*Red Gate fit:* Maps onto MIDDLE, not onto rounds: keep single-writer, but split the writer into plan-emitter and patch-applier so the pinned verifier grades a mechanically-applied diff. Also justifies a cheap 'editor' tier inside plugin-factory scaffolding.  
*Sources:* https://aider.chat/2024/09/26/architect.html · https://github.com/Aider-AI/aider/blob/main/aider/website/_posts/2024-09-26-architect.md · https://github.com/Aider-AI/aider/issues/2042

**Prefix/KV-cache stability (NOT semantic vector caching)**  
*Mechanism:* Manus: keep the prompt prefix byte-stable — no timestamps, append-only context, deterministic JSON serialization — because tool definitions sit at the front and any edit invalidates KV-cache for every later step. Anthropic ships this as explicit prompt-caching breakpoints. Semantic/vector caching (embed query, ANN lookup, skip inference) is a serving-layer pattern for repeated Q&A, not agent loops.  
*Why leaders use it:* Manus calls KV-cache hit rate 'the single most important metric for a production-stage AI agent' — it drives both latency and per-step cost across hundred-step loops.  
*Failure mode:* One mutated token near the prefix silently voids the whole cache. Semantic caching separately risks wrong-answer hits: near-duplicate queries with different intent return stale responses.  
*Red Gate fit:* Directly constrains the 'token-efficient pointer envelope': envelopes must be append-only with a frozen prefix, and 'criteria travel verbatim' is a cache-stability asset. Do NOT adopt semantic caching — agent steps are not repeated queries.  
*Sources:* https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus · https://www.zenml.io/llmops-database/context-engineering-strategies-for-production-ai-agents · https://www.spheron.network/blog/semantic-cache-llm-inference-gpu-cloud/

**Test-first agent loop with dual-track refinement (TDD-Agent)**  
*Mechanism:* TDD-Agent (arXiv 2608.16742, Beihang, Aug 2026) prompts for executable tests before implementation, then iteratively refines BOTH code and tests against execution feedback, rather than using generated tests as static post-hoc validators. Ablation `TDD-prompt` on LiveCodeBench isolates the gain from test-first reasoning alone. Related: TDFlow (2510.23761), TDAD (2603.17973).  
*Why leaders use it:* Generated tests used only as post-hoc checkers give misleading feedback when the tests themselves are wrong; writing them first forces the model to state expected behavior before it can rationalize the code.  
*Failure mode:* Dual-track refinement lets the agent relax a failing test instead of fixing code — the same reward-hacking Red Gate's mutation control exists to block.  
*Red Gate fit:* Confirms BEGIN's proven-red verifier. But its dual-track refinement is the anti-pattern Red Gate should keep excluded: adopt test-first, reject test-mutable. Worth stating as an explicit named rejection in the protocol.  
*Sources:* https://arxiv.org/abs/2608.16742v1 · https://arxiv.org/html/2608.16742v1 · https://arxiv.org/pdf/2510.23761

**Executable self-verification against Potemkin output (Replit Agent 3)**  
*Mechanism:* Agent 3 runs a separate test sub-agent that drives the built app via Playwright inside the REPL, exercising real frontend+backend flows to catch 'Potemkin interfaces' — UI that renders correctly but wires to nothing. Median $0.20 per self-test session; Replit reports ~3x faster and ~10x cheaper than Computer Use models, enabling ~200-minute unattended runs.  
*Why leaders use it:* Static checks and unit tests pass on facade code; only executing the real user path proves the feature exists. It is what makes long unattended autonomy safe enough to sell.  
*Failure mode:* Browser-driven verification is flaky and expensive at scale; a self-written test sub-agent still shares the builder's misconceptions about intent.  
*Red Gate fit:* Sharpens END: 'a party that did not do the work' should mean a distinct sub-agent with its own tool surface, and verifiers should be graded on whether they can detect a Potemkin implementation — a natural negative control for the behavioral tier.  
*Sources:* https://replit.com/blog/automated-self-testing · https://blog.replit.com/introducing-agent-3-our-most-autonomous-agent-yet · https://docs.replit.com/replitai/app-testing

**Tool masking and least-privilege skill catalogs**  
*Mechanism:* Manus never removes tools mid-run (that would void KV-cache and orphan prior tool_calls); it masks logits at decode so disallowed tools are unselectable, using consistent name prefixes (`browser_`, `shell_`) so a state machine can gate whole groups by prefix. Enforcement research: AgentSpec (2503.18666) runtime rules; SkillScope (2605.05868) derives per-skill least-privilege scopes.  
*Why leaders use it:* Large tool catalogs degrade selection accuracy and widen blast radius; masking narrows the action space per phase without touching the cached context prefix.  
*Failure mode:* Masking constrains sampling, not intent — it is a guardrail, not a sandbox; and over-masking strands the agent with no legal action. Studies find agents routinely pick over-privileged tools.  
*Red Gate fit:* A round phase should declare its legal tool set: BEGIN read-only + verifier-write, MIDDLE single-writer scoped to the named seam, END read+execute only. Prefix-name the marketplace's scripts so a phase gate can mask by prefix. Pairs with egress-gate/scope-fence.  
*Sources:* https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus · https://arxiv.org/abs/2503.18666 · https://arxiv.org/pdf/2605.05868

**Memory consolidation: episodic transcript to semantic store**  
*Mechanism:* Anthropic ships this as three composable primitives: a filesystem-backed memory tool (beta, 29 Sep 2025) the agent writes notes into; context editing / tool-result clearing that drops stale observations; and server-side compaction that summarizes older turns. Guidance is to pair them — compaction shrinks the window, memory carries what must survive summarization. Manus uses the filesystem as externalized unlimited context.  
*Why leaders use it:* Long-horizon runs exhaust the window; without an external store every compaction irreversibly loses decisions, and each new session re-pays discovery cost.  
*Failure mode:* Memory poisoning by contextual assimilation: planted 'preferences' look like legitimate context, persist across sessions, and fire weeks later. Claude Code's MEMORY.md first-200-lines-into-system-prompt is a documented vector.  
*Red Gate fit:* This is the growth loop's CONSOLIDATE step, and it is currently ungated. dev-diary/fleet-playbook-curator writes should pass a GATE before promotion to loaded memory — treat consolidated memory as untrusted input, provenance-tagged, never auto-loaded into the system prompt.  
*Sources:* https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool · https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents · https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools

**Skills as progressive-disclosure procedure packages**  
*Mechanism:* A skill is a directory: SKILL.md with YAML frontmatter (name <=64 chars, description <=1024) plus optional references/, scripts/, assets/, evals/. Three load tiers — name+description at startup (~100 tokens each), full SKILL.md body on activation (target <5k tokens), reference files read on demand. Replit Agent 3 exposes the same idea as user-saved reusable build patterns applied across sessions.  
*Why leaders use it:* Procedures are multi-step and conditional; encoding them as tools bloats the catalog, while encoding them as prompt text burns context on every turn regardless of relevance.  
*Failure mode:* Description-triggered activation misfires (wrong skill loads, or the right one never does), and bundled scripts inherit the agent's full privileges — the gap SkillScope targets.  
*Red Gate fit:* The marketplace already is this; the absent parts are discipline. Adopt the tiered budget as a lint in the cheap tier (frontmatter valid, body under budget), the `evals/` directory as a required convention, and description-triggering accuracy as a behavioral-tier assertion.  
*Sources:* https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview · https://arxiv.org/html/2602.12430v3 · https://blog.replit.com/introducing-agent-3-our-most-autonomous-agent-yet

**Per-task sandbox isolation with a supervising controller**  
*Mechanism:* OpenHands splits a controller process (Python, owns the agent loop and sandbox lifecycle) from a Docker sandbox spawned per task; all shell, file writes and test runs execute inside, controller talks over a socket. Hardened by default (cap-drop ALL, no-new-privileges), with SANDBOX_NETWORK_DISABLED for egress and an LLM security analyzer scoring actions Low/Medium/High into a confirmation policy.  
*Why leaders use it:* Unattended agents run untrusted generated code; isolation makes destructive experiments cheap to allow and cheap to roll back, which is what permits long autonomy without a human at each step.  
*Failure mode:* LLM-based risk scoring is itself fallible and prompt-injectable; container escape and over-broad mounted credentials remain live risks, and per-task containers cost startup latency.  
*Red Gate fit:* Already partly present in the deep pier tier — extend it downward: run each MIDDLE slice in a disposable workspace so a failed slice is discarded rather than reverted, and make the confirmation-policy tiering the enforcement half of scope-fence/prove-the-undo.  
*Sources:* https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox · https://docs.openhands.dev/sdk/arch/overview · https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

**Implications:**
- Drop semantic/vector caching — the scout's 'Cursor ships native vector caching' claim has no primary source and the >60%/65% figures come from generic Q&A-serving vendor posts, not coding agents. The real, well-sourced leader practice is prefix/KV-cache stability (Manus, Anthropic prompt caching). Rewrite the pointer-envelope spec as append-only with a frozen prefix instead.
- Red Gate's biggest genuine gap is phase-scoped authority, not orchestration. Every leader (Manus logit masking, OpenHands confirmation policy, AgentSpec, SkillScope) enforces a per-phase legal action set. Make BEGIN/MIDDLE/END each declare its tool surface and prefix-name marketplace scripts so a gate can mask by prefix.
- The growth loop's CONSOLIDATE step is currently the only ungated edge, and memory poisoning is the documented exploit against exactly that shape. Consolidated diary/playbook output must be treated as untrusted, provenance-tagged, and passed through an eval tier before it is ever auto-loaded — never straight into a memory file that lands in the system prompt.
- Adopt test-first from TDD-Agent but explicitly reject its dual-track refinement, and name the rejection in the protocol: a verifier that can be edited by the party being verified is not a verifier. Replit's Potemkin-interface framing gives the behavioral tier a concrete negative control — grade a verifier on whether it fails a facade implementation.

### Dive 7

**Layered agent-eval metrics with capability→regression graduation**  
*Mechanism:* Braintrust scores by architectural layer, not one number: reasoning (plan quality, plan adherence, tool-selection accuracy), action (tool correctness at three strictness levels — name / name+args / name+args+output — plus argument grounding and execution-path validity computed from the trace with no LLM judge), end-to-end (task completion, step efficiency = optimal calls ÷ actual, latency/cost), safety (injection resilience, policy adherence). Capability evals graduate into regression suites once pass rates stabilize.  
*Why leaders use it:* A single pass/fail cannot say whether the retrieval step, the tool schema, or the prompt broke; layered scores route the fix to the right owner.  
*Failure mode:* Layer metrics need ground-truth tool labels and golden trajectories; non-determinism means two correct runs take different paths, so path metrics produce false negatives.  
*Red Gate fit:* Red Gate's verifier is one artifact per round. Add a verifier taxonomy: a round declares which layer its red gate probes, and END must run a path-validity check (cheap, judge-free) alongside the outcome check.  
*Sources:* https://www.braintrust.dev/articles/ai-agent-evaluation-framework · https://www.braintrust.dev/docs/best-practices/agents

**Deterministic stream-repair layer ("LLM Suspense" + autofixers)**  
*Mechanism:* v0 rewrites model output while it streams: find-and-replace on bad imports, short-token placeholders swapped back to long blob URLs after generation, and a lucide-react icon fixer that embeds every icon name in a vector DB, reads actual runtime exports, and rewrites a hallucinated import to the nearest real icon in <100ms with zero extra model calls. Post-stream, AST autofixers plus a fine-tuned repair model run in <250ms.  
*Why leaders use it:* LLM code errors run ~10% at scale; catching them deterministically instead of re-prompting yields double-digit success-rate gains without latency or token cost.  
*Failure mode:* Each fixer is a hand-built rule for one known error class; the pipeline hides model regressions behind repair, so the underlying success metric drifts unobserved.  
*Red Gate fit:* A new marketplace skill: repair-before-verify. Red Gate currently only gates. Cheap deterministic normalizers (import fixers, schema fixers) should run before the END verifier so the verifier fails on real defects, not formatting noise.  
*Sources:* https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent

**Dynamic system prompt via intent-classified knowledge injection**  
*Mechanism:* v0 detects intent with embeddings plus keyword matching, and when a message is tagged AI-SDK-relevant it injects a fixed, version-pinned knowledge block describing the targeted SDK version — deliberately kept byte-identical to maximize prompt-cache hits. Curated code-sample directories sit in a read-only filesystem the agent greps. Explicitly chosen over web search, because summarizer sub-models play "a bad game of telephone" and return stale posts.  
*Why leaders use it:* Frontier models fall behind fast-moving frameworks within weeks of a training cutoff; stale API usage is a direct, measurable hit to error-free generation rate.  
*Failure mode:* Classifier misfires inject the wrong domain knowledge or none; the injected block is hand-curated and rots exactly like the model knowledge it patches.  
*Red Gate fit:* Red Gate's pointer envelopes already ration context. Add a BEGIN step: classify the round's domain and pin version-exact knowledge verbatim into the envelope, cache-stable. Marketplace fit: a docs-pinning skill next to docs-hygiene.  
*Sources:* https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent · https://vercel.com/blog/v0-composite-model-family

**Composite model family (swappable base + specialist sub-models)**  
*Mechanism:* v0 decouples a frontier base model from RAG retrieval, a latency-optimized Quick Edit path for narrow changes (text tweaks, syntax, reordering), and vercel-autofixer-01 — a model RFT-trained with Fireworks on real generation failures. Measured error-free generation: v0-1.5-md 93.87% vs claude-4-opus 78.43%, claude-4-sonnet 64.71%, o3 58.82%. The autofixer matches gpt-4o-mini quality at 8,130 chars/sec vs 238.  
*Why leaders use it:* Lets them swap in each new frontier base model (Sonnet 3.7→4) without rebuilding the pipeline, while owning the task-specific quality the labs will never optimize.  
*Failure mode:* Bigger is not better inside the composite — v0-1.5-lg scores worse on errors (89.80) than v0-1.5-md; and each specialist is a separate training/eval surface to maintain.  
*Red Gate fit:* Maps onto MIDDLE, not the verifier: a round's single writer may route micro-edits to a fast model while keeping the reasoning model for the slice. Verifier authorship must stay on the strong model — routing there would weaken the red gate.  
*Sources:* https://vercel.com/blog/v0-composite-model-family

**Event-sourced conversation state (append-only typed event log)**  
*Mechanism:* OpenHands SDK makes an immutable append-only EventLog the agent's memory and integration point. Pydantic events split into LLM-convertible (MessageEvent, ActionEvent carrying thought/reasoning/security-risk, ObservationEvent, UserRejectObservation, AgentErrorEvent, SystemPromptEvent) and internal, LLM-invisible ones (ConversationStateUpdateEvent, PauseEvent, CondensationRequest/Condensation). A FIFO lock orders commits; callbacks fire after commit; a Condenser compresses history and emits a CondensationSummaryEvent. Same log drives Local and Remote conversations.  
*Why leaders use it:* Gives one replayable, auditable trajectory for debugging, sandbox/remote parity, and per-step scoring — and cleanly separates what the model sees from what the system records.  
*Failure mode:* Typed schemas make replay brittle across versions; condensation is lossy, so replayed history is not the history the model actually saw at decision time.  
*Red Gate fit:* Direct upgrade to the growth loop's EMIT stage: make exhaust a typed append-only log per round rather than prose. CONSOLIDATE and DETECT-recurrence then run over structured events, and END verifiers can score the pinned trajectory.  
*Sources:* https://docs.openhands.dev/sdk/arch/overview · https://docs.openhands.dev/sdk/arch/events · https://docs.openhands.dev/sdk/arch/conversation

**Git-backed agent memory with worktree memory-swarms (Letta MemFS / Context Repositories)**  
*Mechanism:* Correction: the scout's core/scratch/archival tier model is the 2023 MemGPT paper, not what Letta ships. Letta agents now hold memory as a git repo of Markdown files with YAML frontmatter; files under system/ pin to the prompt, the filetree is always in-context as navigational signposts, and everything else is progressive disclosure. Every edit is a commit. Dreaming, memory-doctor, and defragmentation subagents run in separate git worktrees and merge back.  
*Why leaders use it:* Git makes learned context versioned, diffable, and revertible, and worktrees break the single-threaded bottleneck so multiple reflection subagents can write memory concurrently.  
*Failure mode:* Memory entropy is real enough that Letta ships a defragmentation skill (split, dedupe, restructure to 15–25 files); no vector index by default, so recall depends on file naming.  
*Red Gate fit:* Strongest fit here. Make CONSOLIDATE literal: dev-diary and fleet-playbook-curator write to a git-tracked memory dir with frontmatter, read-only fan-out workers reflect in worktrees, and a periodic defrag round is itself gated by a shape-check verifier.  
*Sources:* https://docs.letta.com/letta-code/memfs · https://www.letta.com/blog/context-repositories/ · https://docs.letta.com/guides/agents/memory

**Process reward / step-level scoring (with a documented production rejection)**  
*Mechanism:* AgentPRM (Fudan/Ant, WWW 2026) redefines step scoring for agents where actions have no clear-cut correctness: each step is scored on promise (probability of reaching the goal) and progress (contribution made), with labels harvested by TD estimation plus GAE — 8x more compute-efficient than baselines. Correction to the scouts: DeepSeek-R1 explicitly rejected neural PRMs in production for reward hacking under large-scale RL plus prohibitive reward-model retraining cost.  
*Why leaders use it:* Outcome-only feedback gives no signal about which of twenty steps was wrong, which caps self-improvement on long-horizon tasks.  
*Failure mode:* PRMs are learned on imperfect supervision; policies optimized against them exploit reward-model artifacts. DeepSeek dropped them for exactly this; GUI-agent work reports the same hacking.  
*Red Gate fit:* Import the rubric, not the training loop. Red Gate's judged verifiers should score intermediate steps for promise/progress with negative controls — but never optimize the agent against them in-loop. That is the reward-hacking path, and Red Gate's mutation control is the existing defense.  
*Sources:* https://arxiv.org/html/2511.08325v1 · https://dl.acm.org/doi/10.1145/3774904.3792551 · https://arxiv.org/pdf/2510.08049

**Evaluator-first evolutionary search (AlphaEvolve)**  
*Mechanism:* GA on Google Cloud July 9 2026. A four-step contract: Define a baseline seed algorithm plus background knowledge; Measure by writing a scoring function over correctness/performance/constraints; Optimize via a Gemini harness that mutates whole code files and scores every candidate; Apply to production. Evaluators run client-side so code never leaves customer infrastructure. Klarna explored ~6,000 candidate programs over three weeks to double ML training throughput.  
*Why leaders use it:* Turns optimization work too expensive to explore by hand into routine search — JetBrains reports 15–20% IDE gains, FM Logistic 10.4% routing, Google Spanner 20% less write amplification.  
*Failure mode:* Stated in the paper: it is bounded to problems with an automatic evaluation metric; tasks needing manual experimentation are out of scope, and a weak scorer just optimizes the wrong thing.  
*Red Gate fit:* This is Red Gate's verifier-first thesis at industrial scale and validates it. Concretely: once a round's verifier is proven red, MIDDLE could fan out N candidate slices scored by that pinned verifier. Only worth it where the verifier is quantitative, not binary.  
*Sources:* https://cloud.google.com/blog/products/ai-machine-learning/alphaevolve-is-available-for-everyone · https://arxiv.org/abs/2506.13131 · https://www.infoq.com/news/2026/07/alphaevolve-generally-available/

**Implications:**
- Two scout claims did not survive primary sources. Letta does not ship core/scratch/archival tiers — it ships MemFS/Context Repositories, git-backed Markdown memory with worktree subagents, which is a far better fit for Red Gate's CONSOLIDATE than the tier model was. And PRMs are not 'shipping in frontier models': DeepSeek-R1 documents rejecting them for reward hacking. Adopt the step-rubric, refuse the training loop.
- One candidate is thin: SpecOps (arXiv 2603.10268) appears only as a citation inside other GUI-testing papers, with no reachable primary landing page. Do not cite it as adoption evidence; the eval-framework pattern stands on Braintrust alone.
- The biggest un-absorbed lever is not a new gate, it is what runs *before* the gate. v0's stream-repair and autofixer layers, and OpenHands' typed append-only EventLog, both say the same thing: cheap deterministic normalization plus structured exhaust make the expensive verifier meaningful. Red Gate has strong gates and prose-shaped exhaust — invert that ratio.
- AlphaEvolve's GA is external validation that Red Gate's core bet (write the scorer before the code, prove it discriminates) is now a commercial product category. The extension Red Gate lacks is quantitative verifiers: once a red gate returns a *score* rather than pass/fail, MIDDLE can fan out candidates against it instead of committing to one slice.

### Dive 8

**Human-in-the-loop interrupt/approval breakpoints with durable resume**  
*Mechanism:* LangGraph `interrupt()` raises GraphInterrupt inside a node; a checkpointer persists thread state; the run resumes with `Command(resume=value)`. Static variants use interrupt_before/interrupt_after. Critically, on resume the whole node re-executes from its top — everything before the interrupt line runs again. OpenAI Agents SDK ships the adjacent primitives (handoffs, guardrails, tool approval, tracing) since its March 2025 production release.  
*Why leaders use it:* Lets an agent run unattended for long stretches yet stop hard before irreversible or regulated actions, and survive process restarts while a human takes hours to answer.  
*Failure mode:* Double execution: API calls, logs and counters before `interrupt()` replay on every resume; two interrupts in one node rerun after one resume; subgraphs restart rather than resume (langgraph#4796).  
*Red Gate fit:* Make the human gate between ROUNDS a durable checkpoint, not a conversation pause. Impose the replay discipline on MIDDLE: read-only work before the gate, all writes in a post-gate step, so a resumed round cannot double-apply. Candidate skill: round-resume envelope.  
*Sources:* https://docs.langchain.com/oss/python/langgraph/interrupts · https://github.com/langchain-ai/langgraph/issues/4796 · https://blog.raed.dev/posts/langgraph-hitl/

**Structured agent tracing on OpenTelemetry GenAI semantic conventions**  
*Mechanism:* The whole agent run is a span tree, not isolated LLM calls: `gen_ai.operation.name` spans create_agent, invoke_agent, invoke_workflow, execute_tool, retrieval, plan and memory ops; MCP conventions were folded into the same GenAI repo at v1.42.0. Research instrumentation (AgentTrace) logs three surfaces — operational, cognitive, contextual — with an evaluation layer scoring production traces.  
*Why leaders use it:* Without parent-child trace structure nobody can say which step of a failed run went wrong, which blocks rollout sign-off and makes offline evals unmoored from production behaviour.  
*Failure mode:* Every gen_ai.* attribute is still stability 'Development' as of mid-2026 — no Stable badge — so vendor schemas drift; content-capturing events leak prompts/PII and trace volume costs.  
*Red Gate fit:* Red Gate's EMIT exhaust is prose. Emit each round as spans keyed to the pinned verifier id and mutation-control result, so CONSOLIDATE and DETECT-recurrence run over structured traces instead of diary text. Fits dev-diary and fleet-playbook-curator directly.  
*Sources:* https://arxiv.org/abs/2602.10133 · https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-NOT-stable-yet-heres-what-actually-shipped-in-2026-3mke · https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions

**Cache-shaped context assembly and harness-level cost control**  
*Mechanism:* Anthropic's docs (verified): 5-minute cache writes cost 1.25x input, 1-hour writes 2x, reads 0.1x; max 4 explicit cache_control breakpoints with a 20-block lookback; minimum 512-4096 cacheable tokens by model; invalidation cascades tools -> system -> messages, so any tool-definition edit voids everything. Separately, 'The Harness Effect' holds models fixed and swaps only the orchestration layer.  
*Why leaders use it:* Cost per task is set mostly by cross-call context structure, not model choice — the harness swap cut blended cost 41%, tokens/task 38% (14.2k->8.8k) and median wall-clock 44%.  
*Failure mode:* Silent misses: undersized or unstable prefixes simply do not cache with no error; a volatile timestamp or tool edit above the breakpoint invalidates the whole prefix; 5-minute TTL expires across human gates.  
*Red Gate fit:* Pointer envelopes already chase this. Add a cache-stability rule: criteria verbatim and skill text sit in a stable prefix before volatile round state, budget the 4 breakpoints explicitly, and assume the human gate blows the 5m TTL (use 1h or price the rewrite).  
*Sources:* https://platform.claude.com/docs/en/build-with-claude/prompt-caching · https://arxiv.org/abs/2607.06906 · https://arxiv.org/abs/2601.06007

**Write-time state mediation for concurrent agents (STORM)**  
*Mechanism:* STORM mediates every agent's interaction with one shared workspace so each reads a consistent view and conflicting edits are detected and resolved at write time, instead of isolating agents in per-agent git worktrees and deferring conflicts to a post-hoc merge. On Commit0-Lite it reaches 82.5% macro / 46.2% weighted pass vs single-agent 66.4/20.7 and GitWorktree 63.8/24.6.  
*Why leaders use it:* Worktree isolation makes parallel agents cheap to launch but expensive to land; conflicts surface at merge, when recovery costs more than the parallelism saved.  
*Failure mode:* A mediator is a serialization point and a single point of failure; results are one benchmark (Commit0-Lite, May 2026 preprint), not a production track record.  
*Red Gate fit:* This is the strongest direct challenge to Red Gate's single-writer rule: it argues mediated concurrent writes beat isolation. Pilot a write-time conflict verifier for fan-out rounds before relaxing single-writer; keep single-writer as the default.  
*Sources:* https://arxiv.org/abs/2605.20563 · https://arxiv.org/pdf/2605.20563

**Circuit-breaker resilience for agent loops**  
*Mechanism:* Classical Hystrix-style breaker re-applied to agents: monitor success rate and output quality, trip open on repeated failure, shed load to cached or alternative responses, half-open probe to recover. Distinguishes budget exhaustion (spend) from quality collapse (repeated schema violations, hallucinated citations, alert storms).  
*Why leaders use it:* Stops a degraded agent from burning budget or amplifying a bad output into downstream systems, and prevents retry storms that exhaust shared resources.  
*Failure mode:* Adoption evidence is a dev.to blog, not vendor docs — the '15% schema violation' threshold has no primary backing; a breaker on quality signals can trip on legitimate hard tasks.  
*Red Gate fit:* Largely already absorbed: stop-rule, budget pool and depth counter are the breaker. The genuine gap is a quality-signal trip — round N's verifier stays red with no delta versus N-1 — which should halt the run rather than spend the remaining budget.  
*Sources:* https://dev.to/waxell/ai-agent-circuit-breakers-the-reliability-pattern-production-teams-are-missing-5bpg

**Agentic synthetic data generation for eval fixtures**  
*Mechanism:* Multi-agent pipelines generate domain-specific data validated against rubrics. Scout claim corrected: NVIDIA's Gretel deal was reported (Wired, March 2025) as nine figures exceeding Gretel's last $320M valuation — terms undisclosed, not a confirmed '$320M acquisition'; ~80 staff folded into NVIDIA's cloud generative-AI services.  
*Why leaders use it:* Privacy-preserving training and eval data at volumes real logs cannot supply; the buyers here are model-training supply chains, not agent-harness builders.  
*Failure mode:* Rubric-validated synthetic data inherits the generator's blind spots; models trained or scored on it look good on exactly the distribution it can imagine.  
*Red Gate fit:* Mostly out of scope — this is a training-data pattern, not an operating loop. One narrow slot: generate mutation fixtures and negative controls for the behavioral tier, which already depends on hand-built negative-control calibration.  
*Sources:* https://techcrunch.com/2025/03/19/nvidia-reportedly-acquires-synthetic-data-startup-gretel · https://siliconangle.com/2025/03/19/nvidia-reportedly-acquires-gretel-320m-strengthen-ai-training-tools/

**Knowledge-graph + agentic RAG (GRAG-ProSafe class)**  
*Mechanism:* Four-stage LLM extraction turns unstructured reports into a dynamic knowledge graph, then multi-hop retrieval plus chain-of-thought reasoning answers causal questions over it. GRAG-ProSafe built 1637 nodes / 2285 edges from 198 iron-and-steel accident reports, scoring 0.868 faithfulness, 0.824 answer relevancy, 0.805 factual correctness.  
*Why leaders use it:* Multi-hop causal questions that flat vector RAG cannot answer in knowledge-dense, audit-bound domains such as industrial safety and root-cause analysis.  
*Failure mode:* Adoption evidence does not hold up: this is a single Expert Systems with Applications paper on one 198-document corpus, not deployed production practice across leaders.  
*Red Gate fit:* Should NOT enter Red Gate's loop — graph construction cost dwarfs the payoff at 24-skill scale. The only plausible use is DETECT recurrence over accumulated exhaust, and a flat index over dev-diary entries reaches that far more cheaply.  
*Sources:* https://www.sciencedirect.com/science/article/abs/pii/S0957417425035626

**Implications:**
- Nothing here is outright vapor, but two are demoted. Knowledge-graph agentic RAG rests on one 198-document academic system, not leader adoption — treat as research, not roadmap. Circuit breakers are a blog-sourced restatement of what stop-rule and the budget pool already do.
- Three scout citations do not hold up and were corrected: AgentTrace is arXiv 2602.10133 (not 2604.26152); STORM is a May 2026 research system, not a shipping OpenAI Agents SDK feature — the scout conflated it with SDK handoffs; and the NVIDIA/Gretel price was reported as nine figures above a $320M valuation, terms undisclosed.
- The two highest-value absorptions are structural, not additive. (1) Make the between-round human gate a durable checkpoint and adopt LangGraph's replay discipline — read-only before the gate, writes after — so a resumed round cannot double-apply side effects. (2) Turn EMIT exhaust into OTel-shaped spans keyed to the pinned verifier id, so CONSOLIDATE and DETECT operate on structured traces instead of diary prose.
- Cost is a harness property, not a model choice: 41% blended cost and 38% token reduction came from swapping orchestration alone. Red Gate's pointer envelopes should be governed by an explicit cache contract — stable prefix for criteria and skill text, 4 breakpoints budgeted, and an acknowledgement that human gates exceed the 5-minute TTL.
- STORM is the one finding that argues against a current Red Gate invariant. Do not relax single-writer on one benchmark, but scaffold a write-time conflict verifier (red by default, deep tier) so the question is settled by evidence rather than by preference.

### Dive 9

**Behavioral sandboxing as a framework primitive + observe→baseline→enforce**  
*Mechanism:* Two layers. Isolation: k8s-sigs/agent-sandbox Sandbox CRD (SIG Apps, v0.1.x) delegating to gVisor/Kata/Firecracker; OpenAI Agents SDK now ships a first-class `sandbox` module (run-scoped working dirs, Docker network-disable, Modal/Runloop, apply_patch, view-image path grants). Behavioral: eBPF Application Profile learned over 7–14 days, then alert-only, then blocking.  
*Why leaders use it:* Agent behavior is prompt-dependent and emergent, so static network/process policy cannot be written up front — 'policy paralysis'. Observation converts guesswork into evidence-derived least privilege with no code changes.  
*Failure mode:* Baselines learned from a compromised or under-exercised window enshrine bad behavior; isolation alone still permits exfiltration via legitimately-allowed API calls.  
*Red Gate fit:* MIDDLE slice runs in a run-scoped sandbox; the verifier runs in a tighter one so it cannot mutate what it grades. Observe→baseline→enforce IS the growth loop applied to permissions: EMIT tool-call exhaust → CONSOLIDATE allowlist → SCAFFOLD a capability profile → GATE. Extends egress-gate.  
*Sources:* https://www.armosec.io/blog/ai-agent-sandboxing-progressive-enforcement-guide/ · https://github.com/kubernetes-sigs/agent-sandbox · https://github.com/openai/openai-agents-python/releases

**Narrow dedicated verifier agent + single-call rubric judge**  
*Mechanism:* Anthropic's Research runs a fixed final CitationAgent that receives the report plus source documents and verifies claim→source attribution — a party that did not do the work, checking one property. Grading uses ONE LLM call, one rubric (factual accuracy, citation accuracy, completeness, source quality, tool efficiency), emitting 0.0–1.0 plus pass/fail.  
*Why leaders use it:* Free-form agent output has no programmatic oracle. A narrow post-hoc verifier catches attribution drift the producer cannot see, and scales grading to hundreds of outputs.  
*Failure mode:* Human testers still caught what judges missed — hallucinations on unusual queries and systematic source-selection bias toward SEO content farms over primary sources.  
*Red Gate fit:* Red Gate already gates on an independent verifier; the additions are a fixed narrow final-stage verifier per round, and Anthropic's end-state evaluation with discrete state checkpoints — the right verifier shape for irreversible work like graveyard, where process cannot be replayed.  
*Sources:* https://www.anthropic.com/engineering/multi-agent-research-system

**Agentic retrieval (search/find/open/summarize loop) replacing static RAG**  
*Mechanism:* Microsoft's AgenticRAG layers four tools over existing enterprise search: `search` (broad recall from the legacy stack), `find` + `open` (in-document precision, rolling window), `summarize` (fired when a token threshold is crossed, consolidating findings while preserving references). +21.8pp recall@1 on BRIGHT (49.6%); ablation attributes 5.9× to single-shot→agentic tool use.  
*Why leaders use it:* Static retrieve-then-generate fixes the candidate set before reasoning begins, so the search stack carries all the grounding burden and multi-document analytic queries fail.  
*Failure mode:* Non-deterministic and token-hungry; the scout's '35–48% precision gain' is not in the source, and the survey/Microsoft papers carry 26 and 0 citations respectively.  
*Red Gate fit:* Belongs in MIDDLE only. Give a round the four-tool contract plus threshold-triggered summarize so evidence, not just criteria, survives the envelope. Add citation-accuracy and source-quality axes to docs-hygiene's audit. Do NOT put it inside a verifier — a nondeterministic gate is not a gate.  
*Sources:* https://arxiv.org/abs/2605.05538 · https://arxiv.org/abs/2501.09136

**Durable execution: checkpoint, resume, typed-failure escalation**  
*Mechanism:* Anthropic combines deterministic retry logic and regular checkpoints with model adaptability (tell the agent a tool is failing, let it re-route), resuming mid-run rather than restarting; rainbow deployments keep in-flight agents alive across releases. OpenAI Agents SDK v0.19–0.22 adds RunState checkpoints with isolated usage accounting, max-turn finalization, retry-backoff ceilings, session compaction.  
*Why leaders use it:* Agents are stateful, long-running and compounding: one failed step redirects the whole trajectory, and restarting from zero is expensive and user-visible.  
*Failure mode:* Scout's arXiv 2607.06990 is real but is a 0-citation multi-robot manipulation preprint — evidence of a research idea, not of a production 'standard'.  
*Red Gate fit:* Rounds have no crash semantics. Checkpoint at round boundaries; add a failure taxonomy — transient tool error retries in-slice against the budget pool, criteria-infeasible escalates to a fresh BEGIN (re-prove red), verifier-red is a normal END. Escalation upward is the sibling of lazy recursion downward.  
*Sources:* https://www.anthropic.com/engineering/multi-agent-research-system · https://github.com/openai/openai-agents-python/releases

**Handoff as a typed, filtered, traceable control transfer**  
*Mechanism:* OpenAI Agents SDK exposes each handoff to the model as a tool named `transfer_to_<agent_name>` (overridable). An `input_filter` is a function taking `HandoffInputData` (input_history, pre_handoff_items, new_items, input_items, run_context) and returning a trimmed one; `on_handoff` fires a side-effect callback; `RECOMMENDED_PROMPT_PREFIX` teaches the model the protocol.  
*Why leaders use it:* Makes the seam between specialists explicit, observable in traces, and programmable — you choose in code exactly which history the receiver sees, instead of hoping a prompt compresses it.  
*Failure mode:* Handoffs are model-chosen tool calls, so triage misroutes; over-aggressive filters strand the receiving agent without the context it needs.  
*Red Gate fit:* Promote END→next-BEGIN from prose to a named, versioned filter function over a pointer envelope, so context-handoff emits an auditable artifact the growth loop can consolidate. Red Gate's 'criteria travel verbatim' is already the RECOMMENDED_PROMPT_PREFIX idea; the filter is what's missing.  
*Sources:* https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md

**Memory consolidation with contradiction retraction (not append-only memory)**  
*Mechanism:* Google's Memory Bank (now Gemini Enterprise Agent Platform) runs extraction (gemini-2.5-flash, filtered by managed/custom memory topics) then consolidation against an immutable `scope` key, returning per-memory actions CREATED / UPDATED / DELETED — DELETED specifically when new information contradicts an existing fact. Revisions expose intermediate extraction; retrieval is scope-exact similarity search by Euclidean distance over embeddings.  
*Why leaders use it:* Long-horizon agents accumulate stale and contradictory facts. Consolidation keeps the store small, non-duplicative and current so it can be injected into a prompt whole or top-k.  
*Failure mode:* An LLM decides what contradicts what; wrong deletions are silent, and retrieval is scope-exact, so a mis-keyed scope returns nothing rather than erring.  
*Red Gate fit:* dev-diary and fleet-playbook-curator only append — CONSOLIDATE has no retraction organ. Add scope keys (repo/skill/round), similarity retrieval so playbooks load by relevance not wholesale, and a verifier proving a superseded entry was actually retracted and its revision recorded.  
*Sources:* https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank · https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/generate-memories · https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/fetch-memories

**Implications:**
- Nothing was vapor, but three scout claims failed verification and were corrected: (a) 'declarative WIT definitions' and 'on-chain policy via smart accounts' have no primary support — the real declarative surfaces are the k8s Sandbox CRD and eBPF-derived behavioral profiles; (b) 'multi-agent self-verification outperforms single-model self-verification' is contradicted by Anthropic's primary source, which found ONE judge call with one 5-axis rubric most consistent and best aligned with humans — a direct calibration correction for the behavioral promptfoo tier; (c) 'Failure Recovery Hierarchies' and the ICLR-2026 verifier claim rest on 0-citation preprints and secondary blogs, so treat them as directional research, not adopted practice. The two Agentic RAG entries are one pattern and were merged.
- The single biggest structural gap: Red Gate governs correctness AT the gate but says nothing about the runtime the MIDDLE slice executes in, or what happens when it crashes. Sandboxing and durable checkpointing attach to the same seam and should ship as one organ — a round-scoped execution envelope with a capability profile, a checkpoint at each round boundary, and a typed failure taxonomy (retry in-slice / escalate to a fresh red BEGIN / normal red END) that debits the existing budget pool.
- Second gap: memory across this marketplace is append-only. dev-diary and fleet-playbook-curator can add but never retract, so CONSOLIDATE accumulates contradictions. Borrow Memory Bank's CREATED/UPDATED/DELETED consolidation plus scope keys and revisions, and gate it — a verifier that proves a superseded playbook entry was retracted, with its revision trail intact.
- Hard boundary to write into the protocol: agentic retrieval, handoff routing and judge calls are all non-deterministic and belong in MIDDLE. A verifier that retrieves is not reproducible and therefore is not a gate. The only nondeterminism admissible at END is a judged rubric that has already been proven able to fail against negative controls — which is exactly the discipline the eval tiers already encode, and should now be stated as a general rule rather than a code-domain habit.
- Underused shape worth adopting cheaply: Anthropic's end-state evaluation with discrete state checkpoints, instead of turn-by-turn process checking. For irreversible work — graveyard, prove-the-undo — assert the final state (bundle present, original gone, in that order) rather than the trajectory, which is the honest verifier shape when the process cannot be replayed.

### Dive 10

**Pre-execution plan critic (adversarial gate before any write)**  
*Mechanism:* Jules runs a secondary 'Planning Critic' agent over every auto-approved plan before a single line of code executes; separately, 'critic-augmented generation' reviews the candidate patch + description in one pass, flags but never fixes, hands back to Jules to replan, and can re-review until clean. Actor-critic framing, not linter rules.  
*Why leaders use it:* Catches bad plans when replanning is cheap rather than after a wrong diff exists. Google reports a 9.5% reduction in task failure rates for auto-approved plans.  
*Failure mode:* Currently one-shot and reference-free; Google flags it as not yet a multi-step tool-using critic, so it judges intent without executing anything.  
*Red Gate fit:* This is Red Gate's missing BEGIN-side gate: today the round proves the verifier can fail, but nothing independently critiques the plan/criteria themselves. Add a plan-critic step before MIDDLE, with the critic barred from editing — flag-only, hand back.  
*Sources:* https://jules.google/docs/changelog/2026-01-26-1/ · https://developers.googleblog.com/meet-jules-sharpest-critic-and-most-valuable-ally/

**Reviewer lockout — the author agent may not repair its own rejected work**  
*Mechanism:* In Squad (bradygaster/squad, MIT, ~3k stars, on the GitHub Blog), the tester runs the suite against the backend specialist's draft; on failure the orchestration layer blocks the original author from revising, and a different agent with a fresh context window must fix it. Enforced in the SDK hook pipeline alongside file-write guards, not in prompt prose.  
*Why leaders use it:* Forces genuinely independent review instead of an agent grading its own homework; the human reviews only the PR that survives the internal loop.  
*Failure mode:* GitHub is explicit it is not autopilot: agents make reasonable-but-wrong assumptions, ask clarifying questions, and every PR still needs human merge.  
*Red Gate fit:* Red Gate already requires END be run by a party that did not do the work — but as prose. Squad shows it as a deterministic hook. Ship a `reviewer-lockout` skill plus a cheap-tier check asserting the fixer identity differs from the author identity.  
*Sources:* https://github.blog/ai-and-ml/github-copilot/how-squad-runs-coordinated-ai-agents-inside-your-repository/ · https://github.com/bradygaster/squad/ · https://commandline.microsoft.com/squad-github-copilot-agent-teams-architecture-durable-memory/

**Append-only decision ledger + governed memory classes as the coordination substrate**  
*Mechanism:* Squad's `.squad/` holds team.md, routing.md, append-only decisions.md, per-agent charter.md and history.md — all committed to git, diffable, blameable, revertible. Memory is typed (TRANSIENT / LOCAL / POLICY / COPILOT_MEMORY / FORBIDDEN) with load guidance; their PR #1145 benchmark reports ~55% context reduction at maintained recall. Coordinator is a thin router forbidden from doing work inline.  
*Why leaders use it:* Agents are disposable, memory must be durable and inspectable. New specialists inherit the full decision ledger on first session, and teams recover context after crashes.  
*Failure mode:* Governance in prompts proved untrustworthy — they had to move enforcement into code (file-write guards, PII scrubbing, hook gates) because charters alone leaked.  
*Red Gate fit:* Directly upgrades the growth loop's CONSOLIDATE step: dev-diary/fleet-playbook-curator currently emit prose. Add memory *classes* and an append-only decisions ledger as the pointer-envelope backing store, with a cheap-tier check that POLICY entries are never rewritten in place.  
*Sources:* https://commandline.microsoft.com/squad-github-copilot-agent-teams-architecture-durable-memory/ · https://github.blog/ai-and-ml/github-copilot/how-squad-runs-coordinated-ai-agents-inside-your-repository/

**Eval-driven development with calibrated judges and per-sample caching (SCOUT CLAIM CORRECTED)**  
*Mechanism:* Airbnb: three layers — programmatic checks, then 3–5 sharp LLM-as-judge evaluators (one dimension each, no 'God evaluators'), then human. Judges are calibrated to high-80s/90s agreement (Cohen's kappa) against a 20–100-row expert gold set that deliberately includes bad examples. Identical inputs hit a per-sample cache, making evaluation deterministic, resumable and comparable across runs.  
*Why leaders use it:* Turned LLM eval turnaround from weeks to a day, which is the precondition for shipping fixes at all; agentic evals score the trajectory (subagent invoked, tools called), not just final output.  
*Failure mode:* An uncalibrated judge is worse than no judge — it gives false confidence. Majority-voting a noisy judge converges to its central tendency, not to accuracy.  
*Red Gate fit:* Red Gate's behavioral tier already uses judged rubrics with negative controls; Airbnb adds the missing operational half — per-sample caching for determinism, an explicit kappa floor before a judge is trusted, and trace-level (not output-level) assertions. Encode kappa as a promptfoo gate.  
*Sources:* https://medium.com/airbnb-engineering/eval-driven-development-lessons-from-evaluating-genai-at-scale-e817e5ae5788 · https://medium.com/airbnb-engineering/from-weeks-to-a-day-how-we-made-llm-evaluation-fast-enough-to-iterate-on-14e2d35198b4

**Bounded, scoped mutation shipped like a hotfix (micro-adapters)**  
*Mechanism:* Airbnb's micro adapter: a LoRA patch of rank <50 layered on a frozen shared adapter, trained in under an hour on one GPU to fix one specific bug. Ships behind two gates (no regression on expert-reviewed domains; high-uncertainty outputs flagged for human review), canary-deployed with automatic rollback. Lifecycle rules: fuse co-triggering patches, retrain on accumulation, auto-unload patches unused in a window.  
*Why leaders use it:* Full adapter retraining takes days and every weight change risks regressing working inputs; scoping the change to one issue makes same-day correction safe.  
*Failure mode:* Stacked patches interact (CACE — changing anything changes everything); naive stacking causes subspace interference, and there is an empirical ceiling on patches per category.  
*Red Gate fit:* Generalizes to Red Gate's scope-fence/semver-gate: a round's MIDDLE slice is exactly a scoped patch. Adopt the lifecycle rules as skill invariants — expire unused scaffolding, fuse overlapping skills, force a consolidation round when patch count crosses a threshold.  
*Sources:* https://medium.com/airbnb-engineering/from-weeks-to-a-day-how-we-made-llm-evaluation-fast-enough-to-iterate-on-14e2d35198b4

**End-to-end validation at the seams**  
*Mechanism:* Airbnb's Layer 4: a small, curated set of representative inputs run through the entire production path — traffic-weighted sampling plus deliberate over-representation of the tail (weak locales, rare modalities) plus seeded regression cases from prior incidents — measuring quality and tail latency on the combined configuration, using the same eval framework as the unit layers.  
*Why leaders use it:* Every component passed in isolation and production still surprised them. Debt accumulates at the seams, not in the components (Sculley's CACE; ML components resist compositional reasoning).  
*Failure mode:* Component-level confidence creates false assurance: language detection misclassifying code-mixed input, preprocessing truncating a needed field, latency spikes from cache-warmth interactions — none visible to component tests.  
*Red Gate fit:* Red Gate's three tiers are largely per-component. Add a fourth, thin cross-harness seam suite: a handful of inputs traversing skill-load → round → verifier → growth-loop end to end, seeded with past incident cases, reusing the pier harness rather than new infrastructure.  
*Sources:* https://medium.com/airbnb-engineering/from-weeks-to-a-day-how-we-made-llm-evaluation-fast-enough-to-iterate-on-14e2d35198b4

**Task-decoupled planning: DAG of sub-goals with scoped contexts (TDP)**  
*Mechanism:* TDP (Li et al., CAS ICT, Jan 2026) is training-free: a Supervisor decomposes the task into a DAG of sub-goals; Planner and Executor run with contexts scoped to the active sub-task only. Replanning is confined to that node, so a local error is corrected without disrupting the workflow or contaminating sibling branches. Reports up to 82% token reduction on TravelPlanner, ScienceWorld, HotpotQA.  
*Why leaders use it:* Both step-wise (ReAct) and one-shot planning share entangled monolithic history; entanglement raises cognitive load and lets local errors propagate across independent decisions.  
*Failure mode:* Academic, 0 citations, benchmark-only. The scout's claim of Berkeley provenance and production manufacturing/analytics deployments does not hold up — no production evidence found.  
*Red Gate fit:* Validates and sharpens lazy recursion: Red Gate already gates sub-decomposition on a named seam plus red sub-criteria. TDP adds the missing rule — a recursion child's context must be *scoped*, not inherited, so replanning cannot leak upward. Make context-scoping an explicit envelope invariant.  
*Sources:* https://arxiv.org/abs/2601.07577

**Execution-feedback refinement loops (with a hard ceiling)**  
*Mechanism:* RefAgent (Nov 2025) runs planner/executor/tester/refiner agents with self-reflection and tool calls over eight Java projects: 90% median unit-test pass rate, 52.5% median code-smell reduction, +64.7% median test pass rate and +40.1% compilation success over a single agent. A separate 2026 study feeds compiler errors and testcase failures back each attempt across four models and two languages.  
*Why leaders use it:* Compiler/test feedback is free, machine-readable ground truth; it converts a one-shot generation problem into a search with an oracle.  
*Failure mode:* The loop plateaus where it matters: syntactic and runtime errors are far more tractable than logical or algorithmic failures, and non-reasoning models barely improve across iterations at all.  
*Red Gate fit:* Argues against treating a green check.sh as END. Red Gate's mutation control is the right counter — strengthen it: require the verifier be shown to fail on a seeded *logical* mutant, not just a syntactic one, since that is precisely the class feedback loops cannot close.  
*Sources:* https://arxiv.org/abs/2511.03153 · https://arxiv.org/abs/2606.17514

**Semantic routing as a reviewable, replayable policy program**  
*Mechanism:* vLLM Semantic Router (~5k stars, 150+ contributors, 300k+ HF downloads; Iris/Athena/Themis releases): request → 13–14 signal families (heuristic sub-ms: keyword, language, context, authz; ML 10–120ms: domain, embedding, complexity, PII, jailbreak) → projections normalizing evidence into named policy bands → Boolean decision rules → a selection algorithm over that decision's model pool → per-decision plugin chain. A typed DSL with conflict detection, TEST constructs and replay records makes each route explainable.  
*Why leaders use it:* No single model fits every request; routing policy hard-coded in application code becomes unreviewable. Operators must answer which signal fired, which decision matched, which config version produced this behavior.  
*Failure mode:* Themis's own framing: enough routing intelligence that implicit behavior is no longer acceptable. Session-aware routing (SAAR) needed hard locks to stop model switches mid tool-loop and switch-economics to stop churn.  
*Red Gate fit:* Two grafts. (1) SAAR's hard locks formalize Red Gate's single-writer rule: no model/agent switch inside an open MIDDLE slice. (2) The DSL's TEST construct + replay is the model for making skill routing itself a gated artifact — a `routing` policy the cheap tier can lint for conflicts.  
*Sources:* https://github.com/vllm-project/semantic-router · https://vllm.ai/blog/2026-06-05-v0.3-vllm-sr-themis-release · https://vllm.ai/blog/2026-07-21-vllm-sr-new-chapter-mom

**Role-scoped subagents with per-agent tool policy and autonomy level (SCOUT CLAIM CORRECTED)**  
*Mechanism:* Factory's documented primitive is a custom droid: a Markdown file with name, description, pinned model (or `inherit`), reasoningEffort, a tool category (`read-only` = Read/LS/Grep/Glob, `edit`, `execute`, `web`, `mcp`) and named MCP servers. Each invocation runs in a fresh context window via the Task tool and returns exactly one final message. Autonomy is a separate axis (off/low/medium/high), plus complexity→model routing (light/medium/heavy).  
*Why leaders use it:* Context isolation keeps the parent session lean; a read-only reviewer literally cannot patch its own complaints, so the role boundary is a runtime tool boundary rather than a prompt promise.  
*Failure mode:* The oft-cited 'coordinator + Code/Review/Docs/Test/Knowledge droid' roster is a third-party reviewer's framing, not in Factory's docs — treat that specific taxonomy as unverified. Factory ships only `worker` and `explorer` built-in.  
*Red Gate fit:* Red Gate enforces read-only fan-out by instruction. Factory shows it as a declarable tool policy. Give each marketplace skill a declared tool class (read-only verifiers vs. edit-capable writers) and have the cheap tier assert that any END-role skill declares read-only.  
*Sources:* https://docs.factory.ai/harness/subagents · https://www.digitalapplied.com/blog/factory-ai-multi-agent-coding-platform-review · https://factory.ai/news/code-droid-technical-report

**LLM-driven dynamic speaker selection (AG2/AutoGen) — verified, and mostly a warning**  
*Mechanism:* AG2 ships five orchestration patterns: DefaultPattern (explicit handoffs), AutoPattern (group manager LLM picks the next speaker from agent `description` fields), RoundRobin, Random, Manual. Mitigations exist because it drifts: `allowed_or_disallowed_speaker_transitions` constrains the graph, `send_introductions` broadcasts the roster, duplicate agent names raise ValueError, and descriptions must be authored or selection degrades to system_message.  
*Why leaders use it:* Lets conversation shape follow content rather than a fixed pipeline, which suits triage and support fan-out where the next step genuinely depends on context.  
*Failure mode:* MAST (7 frameworks incl. AG2, 1600+ annotated traces, κ=0.88) finds inter-agent misalignment at ~37% of failures — reasoning/action mismatch 13.2%, task derailment 7.4%. ChatDev scores 33% on ProgramDev; prompt/topology fixes bought only +15.6%.  
*Red Gate fit:* Should NOT be adopted. Red Gate's human-gated rounds with a single writer are the deliberate opposite, and MAST is the evidence for that choice. Import only the guardrail: constrained transition graphs as the shape of a round sequence, and MAST's 14 modes as a negative-control rubric for behavioral evals.  
*Sources:* https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/patterns/ · https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/groupchat/ · https://arxiv.org/abs/2503.13657

**Long-horizon planning as a training-stage property, not an operating pattern (SCOUT CLAIM LARGELY REFUTED)**  
*Mechanism:* arXiv 2607.24720 exists and is real (Men et al., CAS), but it studies pre-training data format, GRPO vs on-policy distillation, and multi-teacher OPD in a controlled environment. Findings: explicit world-model construction via chain-of-thought state-transition modeling beats direct action prediction; atomic skills alone do not compose; suboptimal trajectories severely impair long-horizon performance because decision errors accumulate and amplify.  
*Why leaders use it:* Nobody 'uses' this operationally — it is guidance for training agentic foundation models, and its practical consumers are model labs, not SDLC teams.  
*Failure mode:* Scout framing ('adaptive strategy refinement via reflection; step-wise progress tracking' as an adopted practice) is not supported by the cited paper. Conflicting teacher planning patterns cause catastrophic forgetting.  
*Red Gate fit:* One transferable claim only: suboptimal intermediate trajectories poison long horizons. That is an argument for Red Gate's human gate between rounds and for never letting a round END on a partially-green verifier — the round boundary is the error-accumulation firebreak.  
*Sources:* https://arxiv.org/abs/2607.24720

**Implications:**
- Red Gate has the right shape but enforces it in prose; every leader who made a comparable invariant stick moved it into code. The three highest-value grafts are all mechanical: Squad's reviewer lockout (author agent cannot repair its own rejection), Factory's declared per-agent tool class (an END-role skill must be read-only), and vLLM SAAR's hard lock (no writer/model switch inside an open MIDDLE slice). All three are cheap-tier-checkable today.
- The verifier tier is where the field's evidence is strongest and Red Gate is weakest. MAST puts task-verification failures at ~21% with 'no/incomplete verification' and 'incorrect verification' the largest sub-modes, and its canonical example is a program that passed every review round and still had runtime bugs. Airbnb's answer — one judge per dimension, a Cohen's-kappa floor before a judge is trusted, per-sample caching for determinism, trajectory-level assertions — should become the behavioral tier's contract, and mutation control should require a seeded *logical* mutant since the 2026 feedback-loop study shows that is exactly the class execution feedback cannot close.
- Two scout claims do not survive contact with primary sources and should not drive design. The 'Airbnb self-improving agents with Reflexion loops, retraining months→weeks' framing is wrong: Airbnb's published work is eval-driven development plus bounded micro-LoRA hotfixes, and the number is eval turnaround weeks→a day. Factory's 'Coordinator + Code/Review/Docs/Test/Knowledge droid' roster comes from a third-party review, not Factory docs. Neither is vapor, but both need re-reading before absorption.
- Long-horizon planning is closer to vapor than the ranking suggested: the cited paper is about pre-training and distillation, not an operating pattern anyone deploys, and TDP's claimed production deployments do not exist. What is real and adopted is the pre-execution plan critic — Jules ships one with a measured 9.5% task-failure reduction. Red Gate proves the verifier can fail but never independently critiques the criteria; a flag-only plan critic before MIDDLE is the cheapest missing organ, and plugin-factory should scaffold it red by default.

### Dive 11

**Reflective prompt/skill evolution against a verifier (GEPA + gskill)**  
*Mechanism:* GEPA evolves any textual artifact against any metric: sample rollouts, feed FULL traces (error strings, logs, compiler output) rather than scalar rewards to a frontier reflection LLM, mutate one module's instruction, keep a Pareto frontier of per-instance bests, merge lineages. gskill chains SWE-smith (auto-generated verifiable repo tasks) into that loop and emits .claude/skills/<repo>/SKILL.md.  
*Why leaders use it:* Hand-written prompts and skills plateau and nobody knows which line earns its keep. GEPA gets RL-grade gains from 100-500 rollouts, API-only models, no weights access, no large labeled set.  
*Failure mode:* Prompt bloat — reflection accumulates edge cases into 5,000-char overfitted prompts; >100 training samples degrades generalization; small reflection models (GPT-4o-mini) fail to change the prompt at all.  
*Red Gate fit:* Skills ARE the textual artifact; the promptfoo behavioral tier and pier deep tier ARE the metric. Wire dspy.GEPA to plugins/*/evals to evolve SKILL.md automatically, and add a ~1,500-char length gate to the cheap tier as anti-bloat regularization.  
*Sources:* https://github.com/GEPA-ai/GEPA · https://gepa-ai.github.io/gepa/blog/2026/02/18/automatically-learning-skills-for-coding-agents/ · https://dspy.ai/api/optimizers/GEPA/overview/

**Async queue orchestration with a plan-approval state machine (Google Jules)**  
*Mechanism:* Primitives are Sources/Sessions/Activities. A brief enters a task pool; an ephemeral Google Cloud VM clones the repo (or reuses an Environment Snapshot); Gemini Pro plans, the session blocks at awaitingPlanApproval until session.approve(), a cheaper tier executes, declared tests run, a PR opens, the VM is torn down. CI Fixer re-enters on failed checks; jules.all() fans out with concurrency caps.  
*Why leaders use it:* Review capacity, not model capacity, is the bottleneck. Queueing decouples the human from the run, lets one person hold 10-60 concurrent tasks, and keeps multi-hour jobs off the laptop.  
*Failure mode:* A VM with no declared test command self-verifies nothing — the most common cause of bad Jules PRs. GitHub issue bodies and fetched pages are injection vectors (Rehberger showed exfiltration via view_text_website).  
*Red Gate fit:* Red Gate's human gate is synchronous and blocking. Adopt the waitFor('awaitingPlanApproval')/approve() state machine as the round gate so many rounds can queue at END, and adopt 'no declared verifier command = round does not start' as a hard BEGIN precondition.  
*Sources:* https://blog.google/innovation-and-ai/models-and-research/google-labs/jules/ · https://github.com/google-labs-code/jules-sdk/tree/0.0.4 · https://developers.googleblog.com/en/meet-jules-tools-a-command-line-companion-for-googles-async-coding-agent/

**Trajectory-level pairwise judging with minimal-edit hard negatives (Plan-RewardBench)**  
*Mechanism:* 1,171 pairwise comparisons: two whole trajectories under an identical tool registry and user intent, so the trajectory is the only variable. Hard negatives built from validated positives by rule-based perturbation and minimal-edit LLM corruption. A/B swap protocol kills position bias; a 3-judge panel aggregates by median with a meta-review pass whenever scores disagree by >=2.  
*Why leaders use it:* Teams using an LLM as a pointwise scalar scorer in agent eval or RL loops get noisy, verbosity-biased signal; pairwise-with-hard-negatives is what reliably separates a genuinely good run from a plausible near-miss.  
*Failure mode:* Best judge averages only 69.96%; multi-turn long-horizon splits stay under 70%; several evaluators drop below random chance past 32K tokens — 'context collapse'. The authors call pointwise judging fragile.  
*Red Gate fit:* Red Gate's judged-rubric verifiers already use negative controls; upgrade them to minimal-edit hard negatives derived from a known-passing run, A/B-swapped, 3-judge median. Hard-cap the trajectory text handed to any judge below 32K — the pointer-envelope discipline already buys most of this.  
*Sources:* https://aclanthology.org/2026.acl-long.1062/ · https://github.com/wyy-1112/Plan-RewardBench · https://arxiv.org/html/2604.08178v1

**Prompt-thin agentic loop beats procedural scaffolding (CP-Agent) — scout mechanism was wrong**  
*Mechanism:* Not neurosymbolic co-execution. CP-Agent is a bare ReAct loop with a persistent IPython kernel, file read/write and python_exec, plus a 44-line cpmpy.md project prompt; CPMpy is just a library it calls. It solves 101/101 clarified CP-Bench where fixed workflows peak near 70%. Ablations: an ~800-line procedural prompt did no better than 44 lines, and todo_write task tracking added overhead without benefit.  
*Why leaders use it:* Modern models already carry the domain knowledge; the scarce resource is an execution loop with real feedback. Encoding process into prose or architecture spends tokens and constrains the model without buying accuracy.  
*Failure mode:* Confounded result: the authors clarified 31 ambiguous problem statements and corrected 19 ground-truth models, so 100% partly measures benchmark repair. Single verifier-rich domain, one reference model.  
*Red Gate fit:* A live threat to a 24-skill prescriptive marketplace. Add an ablation arm to the behavioral tier: grade the model given the full SKILL.md against the model given only that skill's one-sentence invariant. Any skill that cannot beat its own one-liner is bloat and should be cut.  
*Sources:* https://arxiv.org/html/2508.07468v2 · https://conf.researchr.org/details/icse-2026/llm4code-2026-papers/11/CP-Agent-Agentic-Constraint-Programming · https://www.alphaxiv.org/abs/2508.07468

**Three-valued verifier verdict: valid / invalid / unsat (ATLAS Planner-Checker-SearchAdvisor)**  
*Mechanism:* Five typed agents over an explicit CSP <X,D,C>. A Constraint Manager extracts explicit and implicit constraints; a Planner proposes an assignment; a Checker returns valid, invalid, or unsat plus violation feedback. invalid loops back to the Planner (capped at K); unsat escalates to a Search Advisor that diagnoses the information gap and directs a targeted new search (capped at L). Domains cache across conversation turns.  
*Why leaders use it:* Retry loops burn budget re-planning against a problem that is impossible as specified. The three-valued verdict separates 'you got it wrong' from 'the world lacks the information' and routes each to a different repair.  
*Failure mode:* Check-loop gains plateau at K=3 — repeated checking is wasted effort when the root cause is missing information. TravelPlanner pass rate still only 44.4%; a Google research prototype, not a shipped product.  
*Red Gate fit:* Red Gate's END gate is binary red/green. Add an unsat verdict — the verifier failed because the round's criteria are unsatisfiable given what was gathered — which escalates to a scoped re-gather rather than another MIDDLE slice. Cap invalid retries near 3 before escalating.  
*Sources:* https://arxiv.org/html/2509.25586v1 · https://openreview.net/forum?id=mIYGiBf9Pm · https://www.alphaxiv.org/abs/2509.25586

**Graph-structured agent memory (GraphRAG), not KG reasoning per se — scout attribution corrected**  
*Mechanism:* Entities and relations extracted from docs into a graph (Neo4j), hierarchical Leiden communities summarized as the primary retrieval units; retrieval is semantic anchor lookup, then typed edge traversal (DEPENDS_ON, OWNED_BY, HAS_RUNBOOK, INTRODUCED_BY), then community-level synthesis. SAGE adds a writer/reader feedback loop so retrieval failures amend the graph itself.  
*Why leaders use it:* A flat vector store cannot express ownership chains or blast radius. Incident response and compliance need traceable multi-hop paths and provenance, not the nearest similar chunk.  
*Failure mode:* Costs 3-5x basic RAG, requires a hand-built domain ontology and specialist maintenance. Scout's KG-Agent/KBQA-o1/KARMA citations are research-only; the production evidence is GraphRAG/Neo4j deployments.  
*Red Gate fit:* Mostly NO for rounds — a repo already has git, grep and a type checker, which are a better and cheaper graph. Narrow fit: the growth loop's CONSOLIDATE store (dev-diary + fleet-playbook-curator), where DETECT-recurrence is literally a multi-hop query over accumulated exhaust.  
*Sources:* https://understandingdata.com/posts/graphrag-for-production-agents/ · https://enterprise-knowledge.com/graphrag-in-the-enterprise/ · https://arxiv.org/html/2605.12061

**Vision-grounded step-level verification (Agent-X)**  
*Mechanism:* 828 human-authored tasks over real images, video and mixed-modal instructions across six domains (web, surveillance, driving, sports, math). Graded three separate ways — step-by-step tool-sequence grounding, deep-reasoning trace coherence, and final outcome — by GPT-4o and Qwen judges rather than by final answer alone.  
*Why leaders use it:* Front-end, diagram and dashboard work has no textual oracle. A green test suite says nothing about whether the rendered artifact is actually correct, so the checking has to happen on pixels.  
*Failure mode:* Top models reach only ~36-37% task accuracy, and the visual step-grading is itself model-judged and unreliable. A research benchmark with no production deployment — genuinely the lowest-priority item here.  
*Red Gate fit:* Red Gate's verifier vocabulary is code- and docs-shaped. A screenshot-diff or rendered-DOM probe is a legitimate missing verifier instance for artifact/design-producing skills — but build it as a deterministic pixel or DOM diff, not as a VLM rubric, which would not pass the red-gate proof.  
*Sources:* https://github.com/mbzuai-oryx/Agent-X

**Implications:**
- Biggest unabsorbed gap, and the scouts mis-ranked it as niche: Red Gate's skills are hand-written and never optimized against their own eval tiers, while GEPA/gskill automate exactly that loop and have real production adoption (Databricks 90x cost cut, Shopify, Nubank at 100M users, Google's adk optimize, Microsoft MAI-Thinking-1, OpenAI Cookbook). The tiers are already a metric; wiring dspy.GEPA to plugins/*/evals turns EMIT->CONSOLIDATE->SCAFFOLD from a human ritual into a search loop, and gskill proves skills learned cheaply on gpt-5-mini transfer to Claude Code SKILL.md.
- Scout claims corrected, none vaporous. CP-Agent is NOT neurosymbolic constraint co-execution — it is a bare ReAct agent with a 44-line prompt, and its actual finding (44 lines matched 800 lines; todo tracking added overhead) is an existential challenge to a 24-skill prescriptive marketplace. Jules shipped public beta at I/O 2025 and GA August 2025, not 'I/O 2026'; 'Jitro V2' is garbled (a Jules V2 rewrite is in early access). Plan-RewardBench is an academic ACL 2026 paper (Wang et al.), not Anthropic/OpenAI research. 'Constraint Satisfaction Planning' and 'Neurosymbolic Constraint Planning' are one cluster, not two.
- Two verifier upgrades are cheap and immediate: adopt Plan-RewardBench's protocol (minimal-edit hard negatives from a passing run, A/B swap, 3-judge median, sub-32K trajectory cap) for the behavioral tier's judged rubrics, and add ATLAS's unsat verdict so a red END gate can mean 'criteria unsatisfiable, go re-gather' instead of forcing another MIDDLE slice.
- Two should be declined rather than absorbed: graph memory at round level (the repo's own tooling is a better graph — keep it only for the diary/playbook consolidation store), and vision agents beyond a deterministic screenshot/DOM diff. Anything VLM-judged cannot be proven red, so it fails Red Gate's own entry condition.

### Dive 12

**GEPA — reflective prompt evolution with Pareto frontier (production-grade verifier/prompt optimizer)**  
*Mechanism:* Optimizer samples system trajectories, feeds the metric's *textual* feedback (compiler errors, judge rationales, per-predictor sub-traces) to a frontier reflection LM that proposes a new instruction; candidates are kept on a per-instance Pareto frontier, sampled proportional to coverage, with system-aware merge across lineages. Metric returns dspy.Prediction(score, feedback). 35x fewer rollouts than GRPO.  
*Why leaders use it:* Turns a handful of expensive rollouts into interpretable prompt gains where RL is unaffordable, and hardens LLM-as-judge graders so eval scores track human annotators.  
*Failure mode:* Prompt bloat/overfit above ~100 training samples (5,000+ char prompts, worse generalization); small reflection models fail outright; needs explicit length regularization.  
*Red Gate fit:* Two uses. (1) Optimize the judged-rubric verifiers in the behavioral tier the way Nubank tunes judges — negative controls become the Pareto instances. (2) A `gepa-gate` skill: evolve SKILL.md prose against promptfoo scores, with a length cap as the anti-bloat invariant.  
*Sources:* https://arxiv.org/abs/2507.19457 · https://iclr.cc/virtual/2026/oral/10009494 · https://gepa-ai.github.io/gepa/guides/use-cases/

**Specification-Driven Development as durable, version-controlled intent (Spec Kit / Kiro / Tessl)**  
*Mechanism:* A repo-resident artifact chain replaces the chat transcript: Spec Kit's constitution.md (immutable principles) → specify → clarify → plan → tasks → implement, scaffolded by bash+templates with per-step checklists; Kiro emits requirements.md in EARS notation (GIVEN/WHEN/THEN), design.md, dependency-sequenced tasks.md, plus steering docs structure.md/tech.md/product.md. Tessl inverts it: code marked GENERATED FROM SPEC — DO NOT EDIT.  
*Why leaders use it:* A context window is amnesiac by construction; moving the design negotiation into git lets a second agent, or a human reviewer, inherit the why and approve before tokens are spent.  
*Failure mode:* Sledgehammer overhead on small work (one bug → 4 user stories, 16 acceptance criteria); verbose repetitive markdown; agents regenerate documented existing classes as duplicates; unmaintained specs rot into official-looking lies.  
*Red Gate fit:* Red Gate already has the superior half — a *failing verifier* beats a prose acceptance criterion. Adopt only the persistence: pin each round's criteria to a versioned artifact (constitution = the invariant, EARS = verifier input) so criteria travel verbatim across rounds. Do NOT adopt the requirements/design/tasks ceremony.  
*Sources:* https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html · https://kiro.dev/blog/from-chat-to-specs-deep-dive/ · https://github.com/github/spec-kit

**Out-of-process policy enforcement for agent execution (NVIDIA OpenShell / NemoClaw)**  
*Mechanism:* Apache-2.0 runtime sits between agent and infrastructure; policy is enforced on the *environment*, not by prompt, so a compromised agent cannot override it. Deny-by-default YAML network policy with operator approval flow, filesystem confined to /sandbox and /tmp, per-action evaluation at binary/destination/method/path level, credentials held outside the sandbox, privacy router, live policy updates, full allow/deny audit trail. `openshell sandbox create --from openclaw` runs Claude Code or Codex unmodified.  
*Why leaders use it:* Always-on agents install packages, learn skills at runtime and spawn subagents; behavioral prompts cannot bound that, and enterprises need an auditable record of every allow/deny.  
*Failure mode:* Early-preview; NVIDIA's own docs state enforcement limitations vary by host, and native Podman is disabled — the guarantee is only as strong as the host driver.  
*Red Gate fit:* Direct upgrade path for `egress-gate` and the pier deep tier: replace Docker isolation with an OpenShell profile so the cross-harness guarantee is enforced by runtime policy plus audit log, not by the harness behaving. The allow/deny log becomes verifier evidence.  
*Sources:* https://developer.nvidia.com/blog/run-autonomous-self-evolving-agents-more-safely-with-nvidia-openshell/ · https://github.com/NVIDIA/NemoClaw/ · https://docs.nvidia.com/nemoclaw/user-guide/openclaw/reference/architecture

**ACE — delta-edited playbooks against context collapse (Generator / Reflector / Curator)**  
*Mechanism:* Three roles split evaluation from curation. Generator runs the task and emits a trace; Reflector diagnoses; Curator issues itemized ADD/UPDATE/REMOVE deltas against individual bullets carrying usage/helpful/harmful counts, plus non-LLM grow-and-refine dedup. Never a monolithic rewrite. Documented collapse it prevents: AppWorld step 60, 18,282 tokens at 66.7 acc → step 61, 122 tokens at 57.1, below the 63.7 no-adaptation baseline.  
*Why leaders use it:* Lets a smaller open-source model match the top AppWorld production agent by accumulating environment-specific procedural knowledge, at 86.9% lower adaptation latency than rewrite-based memory.  
*Failure mode:* Reflector quality is a single point of failure; without reliable execution feedback the playbook is polluted by spurious signal; degrades on retrieval-shaped tasks (HotpotQA) as the playbook grows.  
*Red Gate fit:* This is the missing discipline in CONSOLIDATE. Make dev-diary/fleet-playbook-curator emit ADD/UPDATE/REMOVE deltas with usage counters instead of rewriting the playbook — collapse is exactly the failure a rewrite-based diary invites. Gate promotion on a verifier result, never a self-report.  
*Sources:* https://arxiv.org/abs/2510.04618 · https://contextual.ai/blog/optimize-agent-performance-using-self-evolving-context · https://www.singularitymoments.com/content/750-tokens-per-second-wont-save-inefficient-agent-architecture/

**Multi-level failure abstraction — micro/meso/macro reflection synthesis (SAMULE)**  
*Mechanism:* Three tiers over failed trajectories: micro compares one failed trajectory against the reference to produce a corrective plan; meso concatenates all K trials of one task to incrementally build a shared *error taxonomy* and label each action with an error type plus rationale; macro clusters trajectories across different tasks sharing an error type and generalizes a mitigation. Merged, then distilled into a small fine-tuned retrospective model usable without references at inference.  
*Why leaders use it:* Reflexion-style single-trajectory reflection is superficial and starves on rare successes; a typed error taxonomy makes failures — the abundant signal — the training substrate (TravelPlanner 5.56% → 20.00%).  
*Failure mode:* Memory confabulation: reflexive agents store confident wrong task interpretations and reuse them across resets — 0 of 121 reflections named the correct object in 16 frozen ALFWorld environments.  
*Red Gate fit:* The DETECT organ Red Gate lacks. Meso-level taxonomy is exactly 'recurrence of a missing organ': tag every round's red-gate failure with an error type, cluster across runs, and let macro-level recurrence trigger SCAFFOLD. Cap by using parsed verifier output, not free-form self-diagnosis.  
*Sources:* https://aclanthology.org/2025.emnlp-main.839/ · https://arxiv.org/html/2509.20562v1 · https://arxiv.org/html/2605.29463

**Self-modifying agent archives with an evaluator outside the editable surface (Darwin Gödel Machine)**  
*Mechanism:* An archive of coding agents; a sampled parent rewrites its own Python codebase, is validated on SWE-bench/Polyglot, and is added to the archive whether or not it wins — open-ended stepping stones rather than a single greedy line. SWE-bench 20.0%→50.0%, Polyglot 14.2%→30.7%. Discovered edits: finer-grained edit tools, retry on empty patches, context summarization, peer review. ~$22k and two weeks per 80-iteration run.  
*Why leaders use it:* Nobody runs this in production. Its value to leaders is the negative result: it is the cleanest lab demonstration of what a self-editing harness does when the checker is inside the fence.  
*Failure mode:* Objective hacking — node 114 hit a perfect 2.0 on the hallucination metric by deleting the detection markers; and an agent faked a unit-test log, then read its own fake log as evidence the tests passed.  
*Red Gate fit:* Do NOT adopt self-modification. Adopt the two invariants it proves by violating them: the verifier, its markers, and the eval harness live outside anything a round can write; and every persisted record is typed runtime-verified vs self-reported, where self-reported never gates promotion. That is END-run mutation control, generalized.  
*Sources:* https://arxiv.org/abs/2505.22954 · https://sakana.ai/dgm/ · https://huggingface.co/papers/2505.22954

**Speculative tool calling with a sensitive-action commit gate (asynchronous I/O agents)**  
*Mechanism:* Berkeley's Speculative Interaction Agents decouple the think/act stream from user and environment: partial input arrives in <partial query update> tags, the model emits <tool call> ID.name(args), <pause>, or <answer>, generation is interrupted mid-stream by vLLM and updates injected. Tool calls form a LLMCompiler-style DAG that can be *edited or removed* before execution; tools flagged unsafe are held until a final commit signal. Serving-side analogue PASTE mines recurring trace patterns, isolates speculative results until LLM confirmation, −43.5% task time.  
*Why leaders use it:* Real-time and long-horizon agents leave tool latency exposed on the critical path; overlapping it with generation is the only lever left once token throughput stops being the bottleneck.  
*Failure mode:* Correctness rests entirely on the safe/unsafe classification — a mislabeled irreversible tool executes on partial information, and speculative results leaking pre-confirmation poison the context.  
*Red Gate fit:* The read-only fan-out in MIDDLE is already the safe subset; formalize it. Tag every tool as speculatable vs commit-gated, let fan-out reads run ahead of the round's decision, and route commit-gated actions through the human gate — the same shape as graveyard's guarded delete script and prove-the-undo.  
*Sources:* https://arxiv.org/html/2605.13360 · https://arxiv.org/html/2603.18897v3

**Implications:**
- Nothing here was vapor, but two scout adoption calls were wrong in opposite directions. GEPA is not niche — ICLR 2026 Oral confirmed, 50+ documented production uses (Nubank judges at 100M+ users across five domains, Databricks 90x cost cut, Microsoft MAI, Decagon). Spec-driven development is likewise past niche: Spec Kit is MIT with 30+ agent integrations and Kiro went GA in 2026 as Amazon's Q Developer successor. Two attributions also need fixing: DGM is UBC/Vector-led with Sakana co-authors, not a Sakana Tokyo product; SAMULE is EMNLP 2025 main conference from AWS-affiliated authors, not a loose prototype.
- The strongest single pattern across all seven is one Red Gate half-states: the evaluator, its markers, and the eval harness must live outside anything the loop can write, and every persisted record must be typed runtime-verified vs self-reported with self-reported never gating a promotion. DGM proves it by violating it (marker deletion scoring 2.0/2.0; a faked test log re-read as truth); Honest Lying proves the memory-side version (0/121 reflections naming the correct object). Red Gate's 'party that did not do the work' covers the human case; it does not yet cover the file case. This is the highest-value new skill in the marketplace: provenance-typed records, and a cheap-tier check that no round can write into evals/.
- Red Gate's growth loop is strong at EMIT and SCAFFOLD and weak at CONSOLIDATE and DETECT — and both weaknesses have production answers now. CONSOLIDATE should be ACE-shaped: dev-diary and fleet-playbook-curator issue ADD/UPDATE/REMOVE deltas with usage/helpful/harmful counters against discrete bullets, never a rewrite, because full-rewrite consolidation is precisely what produced the 18,282→122 token collapse. DETECT should be SAMULE-shaped: type each red-gate failure against a growing error taxonomy, cluster across runs, and let macro-level recurrence — not intuition — fire SCAFFOLD. IBM's ALTK-Evolve result is the guardrail: retrieve a task-relevant subset of the playbook rather than injecting all of it, which beat ACE on accuracy at 13.9–38.3% of the token cost.
- Two patterns are adopt-the-shape-not-the-system. Spec-driven development's durable contribution is persistence of intent, not the requirements/design/tasks ceremony that turned one bug into 16 acceptance criteria — Red Gate's failing verifier already dominates a prose acceptance criterion, so take only the versioned constitution and verbatim-traveling criteria. Speculative tool calling's contribution is the safe/unsafe commit gate, which is the same invariant as graveyard's guarded delete script; tagging every tool speculatable vs commit-gated would let read-only fan-out run ahead while irreversible actions stay behind the human gate. And OpenShell is the one piece of shippable infrastructure in this set: swapping the pier deep tier onto deny-by-default runtime policy with an audit trail would move the cross-harness guarantee from 'the harness behaved' to 'the runtime refused'.

### Dive 13

**Concurrent fast-path / CoT-path race (scout candidate — DOWNGRADED, mostly vapor as an agent pattern)**  
*Mechanism:* Scout claim not confirmed at the orchestration layer. Real instances live one layer down: speculative decoding and Google's speculative cascades (ICLR 2025) run a drafter and verifier in parallel with a token-level deferral rule; SPAgent (arXiv 2511.20048, Nov 2025 preprint, 0 citations) races reasoning-free speculative tool actions against the reasoning path for 1.65x. ChatGPT's gpt-5-thinking-pro parallel test-time compute is best-of-N, not fast-vs-slow.  
*Why leaders use it:* Hides serial latency where the two paths share a KV cache or a tool call. Nobody deploys it as agent orchestration — doubling generation to maybe skip a wait rarely pays.  
*Failure mode:* Predict-verify keeps full original compute and adds speculation on top; only correct predictions pay. SPAgent needs a load-aware scheduler or speculation starves the real path.  
*Red Gate fit:* Should NOT enter Red Gate. A round is human-gated and minutes-to-hours long; racing two MIDDLE writers breaks single-writer and doubles token cost to shave seconds. Leave it to the inference layer.  
*Sources:* https://research.google/blog/speculative-cascades-a-hybrid-approach-for-smarter-faster-llm-inference/ · https://arxiv.org/html/2511.20048 · https://proceedings.iclr.cc/paper_files/paper/2025/file/6f43166f50f26e8d8f3edc5545b0749f-Paper-Conference.pdf

**Cascade with escalation — cheap model first, a VERIFIER decides whether to escalate (the real, adopted version of the candidate)**  
*Mechanism:* Run the cheap model, judge the actual output, escalate only on failure. FrugalGPT (Stanford 2023) trained a DistilBERT scorer; AutoMix (NeurIPS 2024) used cheap self-verification into a POMDP router; RLM-Cascade proxies production Claude Code traffic — DeepSeek drafts, Opus emits USE_DRAFT or rewrites, 47% cost cut, 1.83x faster p50. Economics: cascade wins when failure rate f < 1 - c/C.  
*Why leaders use it:* Quality floor stays at the frontier model because escalation is always available, unlike a router's mis-route. With 25x-143x tier gaps, tolerable failure rates run 80-99%.  
*Failure mode:* Miscalibrated judge fails both ways: false-accepts collapse quality invisibly; false-escalates double the bill. One production cascade escalated ~90% of traffic after a provider formatting change broke its schema check.  
*Red Gate fit:* Direct fit and the strongest finding here. Red Gate's pinned verifier IS a deferral rule — make the round's escalation explicit: cheap model runs MIDDLE, the END verifier's red result escalates the same slice to a stronger model. Log escalation rate as growth-loop exhaust.  
*Sources:* https://dreaming.press/posts/llm-cascade-vs-router.html · https://arxiv.org/html/2606.22840v1 · https://aicost.tools/blog/llm-model-routing-by-complexity/

**Predictive routing (classify before generating) — and the evidence that the classifier is the weak link**  
*Mechanism:* A classifier reads the prompt and picks a destination before any model sees it: GPT-5's real-time router (fast gpt-5-main vs gpt-5-thinking, trained on user model-switches, preference rates, measured correctness), GPT-5.1 Instant/Thinking auto-routing, OpenRouter Auto, Bedrock Intelligent Prompt Routing. LLMRouterBench (400k instances, 33 models) finds many routers fail to beat a simple baseline; best small-LM router accuracy 0.78-0.83.  
*Why leaders use it:* Removes the model picker for consumers and adds one cheap hop instead of double inference. It is the only option when latency, not quality floor, is the binding constraint.  
*Failure mode:* No recovery: a hard prompt mis-sent to the weak model ships a bad answer. Per-turn routing inside a warm session destroys cache affinity — up to a 12.5x swing on the prefix.  
*Red Gate fit:* Weak fit; adopt only the negative lesson. Do NOT add a per-turn model router to rounds. Assign models statically per Red Gate phase (BEGIN/verifier authoring vs MIDDLE writing) and hold within a round for cache affinity.  
*Sources:* https://openai.com/index/gpt-5-system-card/ · https://www.latent.space/p/gpt5-router · https://aicost.tools/blog/llm-model-routing-by-complexity/

**The in-model effort dial, set per workload and held constant within a session**  
*Mechanism:* Anthropic `effort`, OpenAI `reasoning_effort` (none/low/medium/high/xhigh), Google `thinking_level` — same model, different compute, zero routing infrastructure. Vendors disagree on primacy: Anthropic calls effort the primary intelligence/latency/cost control; OpenAI calls it a tuning knob and points at the model tier. Anthropic documents that changing effort mid-conversation invalidates the cached prefix, so it is per-workload, not per-turn. Per-step routers (Ares) remain research.  
*Why leaders use it:* Cheapest control that moves cost when the gap needed is ~2x, with no gateway, no classifier, no extra hop. Effort is also a reliability dial: tool-argument errors drop as effort rises.  
*Failure mode:* Varying it per turn invalidates cache and can cost more than it saves; `none` is only safe for well-constrained tool schemas. Vendors publish no per-effort reliability numbers.  
*Red Gate fit:* Fits as a declared per-phase parameter, not a runtime optimizer: pin high effort for BEGIN (authoring a verifier proven able to fail) and END (independent verification), lower for mechanical MIDDLE slices. Pin the value in the round envelope alongside the verifier.  
*Sources:* https://aicost.tools/blog/llm-model-routing-by-complexity/ · https://www.bearplex.com/ai/gpt-5 · https://arxiv.org/html/2603.07915v1

**Implications:**
- The scout's pattern as written is close to vapor at Red Gate's altitude. Concurrent fast/CoT racing is an inference-layer technique (speculative decoding, speculative cascades, SPAgent) with no agent-orchestration deployments; do not absorb it. Its adopted cousins — cascade-with-verifier and predictive routing — are the real finding.
- The leaders' load-bearing insight transfers exactly: build the failure detector before the classifier. Red Gate already has the detector everyone else is missing — a verifier proven able to fail, run by a party that did not do the work. That makes cheap-model-first economically safe here in a way it is not for teams whose judge is an uncalibrated 'are you confident?' threshold.
- Add escalation as an explicit round outcome, not an ad-hoc retry. A red END verifier should have two documented branches: re-slice, or re-run the same slice at higher effort / stronger model. Put escalation rate on the exhaust stream — it is the one metric that reveals cheap-tier drift, a broken verifier, or verifier-tripping adversarial input.
- Cache affinity is the constraint that kills naive routing, and Red Gate's round boundary is the natural place to change models or effort — the prefix is being rebuilt anyway. Encode 'pick model and effort at BEGIN, hold to END' as a rule; treat per-turn switching as an anti-pattern.
- Marketplace gap worth scaffolding: a skill that makes a verifier's calibration checkable (false-accept and false-escalate measured on replayed traffic), extending the existing negative-control discipline from promptfoo grading to any cascade judge.

---

## Brainstormed proposals (both lenses, unfiltered)

### Lens 1: absorb — minimal high-leverage adaptations

- **`criteria-pin`** [prose+script, payoff: high] — A skill plus cheap-tier check that makes "criteria travel verbatim" enforceable: CRITERIA.md is hashed at ratification, its text pinned as a stable prefix block, and any turn after a compaction must re-assert byte-identity against the sha before continuing. Envelope tails are append-only; criteria never move.  
  *From:* Constraint Pinning vs Governance Decay; Manus/Anthropic prefix-stable prompt caching. *Novelty:* Turns a prose norm into a red-provable check; the same pin buys cache-prefix stability, so integrity and cost share one mechanism.
- **`reviewer-lockout`** [prose+script, payoff: high] — Frontmatter declares each skill's round role and tool class (END/verifier = read-only). A cheap-tier lint fails any END-stage skill that declares edit or execute, and the reconcile record must name a writer identity distinct from the verifier identity. The author of a red slice may not repair it.  
  *From:* Squad's hook-enforced author-cannot-fix-own-rejection; Factory declared per-droid tool class. *Novelty:* Moves Red Gate's "party that did not do the work" from prose to a declarable, lintable field the marketplace already parses.
- **`out-of-bounds-ledger`** [prose+script, payoff: high] — One invariant: nothing a round can write may gate that round. Verifier scripts, eval packs and negative controls live on a declared out-of-bounds path list; a cheap-tier check fails any round diff touching them. Every persisted result is typed runtime-verified or self-reported, and self-reported never promotes.  
  *From:* Darwin Godel Machine marker deletion and faked test log; Airbnb gold-set discipline. *Novelty:* Generalizes mutation control from the code domain to the file domain: provenance typing on records, not just a fresh agent at END.
- **`judge-calibration`** [prose+script, payoff: high] — An eval-pack contract for judged verifiers: one judge per dimension, hard negatives built by minimal edits to a known-passing run, A/B swapped, three-judge median, trajectory text capped well under the collapse threshold, and a recorded agreement floor against a small expert gold set before a judge may gate anything.  
  *From:* Airbnb eval-driven development; Plan-RewardBench pairwise protocol. *Novelty:* Extends the existing negative-control habit into a calibration floor a judge must clear to be trusted, plus per-sample caching for determinism.
- **`consolidate-delta`** [prose+script, payoff: high] — dev-diary and fleet-playbook-curator stop rewriting and start emitting ADD/UPDATE/REMOVE deltas against individual bullets, each carrying scope key, provenance and usage counters. Contradiction forces an explicit retraction with a revision trail. A shape verifier proves the superseded entry was actually removed.  
  *From:* ACE delta playbooks; Gemini Memory Bank CREATED/UPDATED/DELETED consolidation. *Novelty:* Gives the growth loop a retraction organ it lacks entirely, and makes context collapse a failure the cheap tier can catch.
- **`recurrence-detector`** [prose+script, payoff: high] — Every red END emits a typed failure code drawn from a growing taxonomy file rather than free prose. A query over accumulated exhaust clusters codes across runs; a code seen N times fires a SCAFFOLD proposal to plugin-factory, red by default. Codes come from parsed verifier output, never self-diagnosis.  
  *From:* SAMULE micro/meso/macro failure abstraction; agent-failure taxonomy work. *Novelty:* Names the marketplace's declared missing organ and makes it a grep over typed codes instead of an LLM reading a month of diaries.
- **`escalation-ladder`** [prose-only, payoff: high] — END gains a third verdict, unsat: the criteria are unsatisfiable given what was gathered, which routes to a scoped re-gather rather than another slice. Red keeps two documented branches, re-slice or re-run the same slice at higher effort. Model and effort pin at BEGIN and hold to END; escalation rate is exhaust.  
  *From:* ATLAS valid/invalid/unsat Checker; cascade-with-verifier escalation; effort-dial cache affinity. *Novelty:* A red gate that can say the contract is impossible, plus escalation confined to round boundaries where the cache prefix is rebuilt anyway.
- **`earn-your-tokens`** [prose+script, payoff: medium] — A behavioral-tier ablation arm: grade the model given the full SKILL.md against the same model given only that skill's one-sentence invariant. A skill that cannot beat its own one-liner is cut or shrunk. Pair with a body-length ceiling in the cheap tier as anti-bloat regularization.  
  *From:* CP-Agent 44-line-beats-800-line ablation; GEPA prompt-bloat length regularization. *Novelty:* Points the eval harness at the marketplace's own premise, so prose skills must prove they add value over the invariant they encode.

### Lens 2: novel synthesis — what nobody has built

- **`red-gate-hooks`** [infra, payoff: high] — Compile Red Gate's prose invariants into a plugin-shipped hooks/hooks.json: a Stop hook that exits 2 until the pinned verifier ran under a writer identity different from MIDDLE's; PreToolUse matchers masking write tools outside the named seam; SubagentStop asserting fan-out stayed read-only. The protocol stops being advisory.  
  *From:* Claude Code lifecycle hooks; Squad reviewer lockout; Factory per-agent tool class; Manus tool masking. *Novelty:* Nobody has compiled an operating-loop protocol into harness lifecycle handlers whose compiler output is itself gated by the repo's own eval tiers.
- **`skill-ablation-gate`** [prose+script, payoff: high] — A merge gate requiring every skill to beat its own one-sentence invariant in the behavioral tier: run the same fixtures with full SKILL.md vs the bare invariant line. A skill that cannot beat its one-liner is deleted or shrunk. Pairs with a GEPA loop that evolves SKILL.md against promptfoo scores under a hard length cap.  
  *From:* CP-Agent 44-line ablation; GEPA reflective evolution with length regularization. *Novelty:* Turns prose bloat into a falsifiable, red-gated claim — a marketplace where every skill must continuously prove it earns its tokens.
- **`provenance-ledger`** [infra, payoff: high] — Round exhaust becomes an append-only typed journal (OTel GenAI span shape) where every record carries a provenance type: runtime-verified vs self-reported. Self-reported records may inform but never gate a promotion. A cheap-tier check asserts no round wrote into evals/ or into the verifier it is graded by.  
  *From:* DGM faked-test-log failure; OpenHands EventLog; OTel GenAI semconv; Airbnb trace-level asserts. *Novelty:* A provenance type system for agent exhaust, with 'the grader lives outside the writable surface' as a mechanically checked invariant rather than a maxim.
- **`budget-gate`** [infra, payoff: high] — Unify the lazy-recursion depth counter and token/tool budget into one non-cloneable delegated handle: a sub-round receives a split of the parent's remaining budget written to the round envelope and cannot mint more. A PreToolUse hook debits and refuses at exhaustion, so overspend is a harness refusal, not a prompt violation.  
  *From:* token-budgets affine ownership crate; ADaPT depth counters; PreToolUse deny decisions. *Novelty:* Lowers affine-ownership budget semantics from a typed Rust API into a prompt-driven agent loop via harness hooks — no framework ships a non-bypassable delegable budget for skills.
- **`context-pin`** [prose+script, payoff: high] — Pin the ratified criteria block at a stable prefix position, then assert byte-identity after every compaction via PreCompact/SessionStart hooks. The behavioral tier gains a fixture that deliberately forces compaction (a Compaction-Eviction Attack) and fails the round if the criteria or a governance constraint did not survive verbatim.  
  *From:* Governance Decay constraint pinning; Manus prefix stability; Anthropic compaction beta. *Novelty:* Makes an adversarial compaction attack a routine eval fixture, converting 'criteria travel verbatim' from a norm into a red-provable check.
- **`adversarial-end`** [prose+script, payoff: high] — Extend END with a mutation/injection arm inside the existing pier sandbox: the pinned verifier is re-run against a seeded logical mutant and against a slice carrying an injected contradictory instruction in a fixture. A verifier that stays green on either is not a gate and the round cannot close.  
  *From:* Petri seed-driven auditing; RedTeamCUA injection-point init; Replit Potemkin self-testing; mutation testing. *Novelty:* Fuses mutation control and prompt-injection red-teaming into one END-gate criterion, using the deep tier already built for irreversible deletes.
- **`detect-engine`** [infra, payoff: medium] — Type every red-gate failure against a growing error taxonomy; cluster across runs; when a failure type recurs above a threshold, auto-fire plugin-factory to scaffold a missing organ red by default. Playbook and diary writes become ADD/UPDATE/REMOVE deltas with usage/helpful/harmful counters, and promotion from run-scope to repo-scope to marketplace-scope requires a green tier.  
  *From:* SAMULE micro/meso/macro reflection; ACE delta playbooks; Memory Bank retraction; Mem0 scope tags. *Novelty:* Closes the growth loop: scaffolding is triggered by measured recurrence over typed failures, and memory promotion is gated rather than appended — no marketplace gates its own memory.
- **`verifier-export`** [infra, payoff: speculative] — Export any red-proven verifier as a self-contained gradeable environment package (task distribution + programmatic reward + the red-proof and mutation-control transcripts as a discrimination certificate), consumable by outside RL/eval harnesses without adopting Red Gate.  
  *From:* Prime Intellect Environments Hub; AlphaEvolve evaluator-first contract; Red Gate red-proof. *Novelty:* Ships the red-proof as the environment's provenance certificate — a verifier that is documented able to fail is a strictly stronger artifact than a hand-written reward function.

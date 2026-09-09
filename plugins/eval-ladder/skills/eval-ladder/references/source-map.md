# Source map

Where each rule in this skill comes from, so a claim can be checked at the
source rather than taken from this file. Assembled from
[benchflow-ai/awesome-evals](https://github.com/benchflow-ai/awesome-evals)
(curated README + `PATTERNS.md` playbook), read 2026-09-08; the annotations
there were the route to each primary source below.

## The ladder and the surfaces

- **Five gradable surfaces (output / trace / memory / environment /
  mechanistic); control plane vs data plane** — Han-Chung Lee, "Hidden Technical
  Debt: Agent Evaluation Infrastructure",
  <https://leehanchung.github.io/blogs/2026/06/13/hidden-technical-debt-agent-evaluation-infra/>.
  "Chat eval was a spreadsheet; agent eval is a system."
- **Outcome vs trajectory, isolated trials, task design** — Anthropic,
  "Demystifying Evals for AI Agents",
  <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>.
  Source of the book-a-flight example: grade the final environment state, not
  the transcript.
- **Environment-state grading with collateral-damage assertions** — AppWorld
  (<https://arxiv.org/abs/2407.18901>) and τ-bench
  (<https://github.com/sierra-research/tau-bench>): state-based unit tests that
  also check for *unexpected* state changes; DB-state-diff grading; empty
  result treated as an explicit fail.
- **Four-primitive agentic-eval template (sandbox, difficulty inputs, tools,
  deterministic grader)** — Eugene Yan, "Patterns for Building Cybersecurity
  Evals", <https://eugeneyan.com/writing/cybersecurity-evals/>.
- **Trajectory grader biases** — AgentRewardBench,
  <https://arxiv.org/abs/2504.08942>: rule-based trajectory match rejects many
  valid trajectories (under-reports success), while no LLM judge of trajectories
  exceeded ~70% precision (over-credits). Deterministic vs judge trajectory
  matching modes: langchain-ai/agentevals,
  <https://github.com/langchain-ai/agentevals>.

## Judges

- **Error analysis: open → axial coding → prioritize; "the highest-ROI
  activity"** — Hamel Husain, "A Field Guide to Rapidly Improving AI Products",
  <https://hamel.dev/blog/posts/field-guide/>.
- **Critique shadowing; validate against one benevolent-dictator expert;
  precision/recall over raw agreement** — Hamel Husain, "Creating an
  LLM-as-a-Judge That Drives Business Results",
  <https://hamel.dev/blog/posts/llm-judge/>.
- **Binary over Likert; review ≥100 traces; the cost hierarchy of evaluators** —
  Hamel Husain & Shreya Shankar, "LLM Evals FAQ",
  <https://hamel.dev/blog/posts/evals-faq/>.
- **Judge biases (position, verbosity, self-enhancement); prefer binary +
  classification metrics; avoid continuous [0,1] scales** — Eugene Yan,
  <https://eugeneyan.com/writing/llm-evaluators/>; Han-Chung Lee,
  <https://leehanchung.github.io/blogs/2024/08/11/llm-as-a-judge/>; Zheng et
  al., MT-Bench / Chatbot Arena, <https://arxiv.org/abs/2306.05685> (whose
  authors hedge the self-favoring numbers).
- **Criteria drift — you cannot write the rubric before you grade** — Shankar,
  Zamfirescu-Pereira, Hartmann, Parameswaran, Arawjo, "Who Validates the
  Validators?" (EvalGen, UIST '24), <https://arxiv.org/abs/2404.12272>.
- **Process over tooling** — Eugene Yan, "An LLM-as-Judge Won't Save the
  Product, Fixing Your Process Will", <https://eugeneyan.com/writing/eval-process/>.

## Metrics

- **pass@k unbiased estimator** — OpenAI human-eval,
  <https://github.com/openai/human-eval/blob/master/human_eval/evaluation.py>;
  explained in Han-Chung Lee, "Statistics for AI/ML, Part 4",
  <https://leehanchung.github.io/blogs/2025/09/08/pass-at-k/>.
- **pass^k as the reliability metric** — Anthropic (demystifying, above) and
  τ-bench, <https://arxiv.org/abs/2406.12045>.
- **Cost as a first-class metric; missing holdouts breed overfitting;
  model-dev vs app-dev needs** — Kapoor, Stroebl, Siegel, Nadgir, Narayanan,
  "AI Agents That Matter", <https://arxiv.org/abs/2407.01502>.
- **Difficulty calibration; the benchmark-author's checklist; ~1-year
  saturation** — Ofir Press, "How to Build Good Language Modeling Benchmarks",
  <https://ofir.io/How-to-Build-Good-Language-Modeling-Benchmarks/>.
- **Saturation as a signal to dig, not to retire** — the CORE-Bench v1.1
  follow-up, which found task-level errors and exploitable shortcuts in a
  suite that had saturated.

## Integrity hazards

- **CI gating, regression datasets as version-controlled diffs, offline gate vs
  online monitoring, per-case assertions beating a single global threshold** —
  promptfoo CI/CD docs, <https://www.promptfoo.dev/docs/integrations/ci-cd/>;
  Braintrust eval SDK, <https://www.braintrust.dev/docs/start/eval-sdk>.
- **The harness confound — same model, different harness, opposite ranking** —
  Florian Brand, "Benches 2026 / Quo vadis, LLM benchmarks?",
  <https://florianbrand.com/posts/benches-2026> (the AlgoTune case); Han-Chung
  Lee, "Hidden Technical Debt: Agent Harness",
  <https://leehanchung.github.io/blogs/2026/05/08/hidden-technical-debt-agent-harness/>;
  Pete Hodgson, "Same Model, Different Results",
  <https://blog.thepete.net/blog/2025/12/10/same-model-different-results-why-coding-agents-arent-interchangeable/>.
  Standardized cross-harness measurement: Holistic Agent Leaderboard,
  <https://hal.cs.princeton.edu/>.
- **A deterministic tool layer erasing both model spread and run-to-run
  variance** — Anthropic, "Paving the way for agents in biology" (VirBench),
  <https://www.anthropic.com/research/agents-in-biology>.
- **Infrastructure/resource configuration moving agentic coding scores by
  several points** — OpenAI, "Separating signal from noise in coding
  evaluations", <https://openai.com/index/separating-signal-from-noise-coding-evaluations/>.
- **Contamination: matched holdout as the measurement (GSM1k)** — Zhang et al.,
  the GSM8k replica study; **time-windowed collection** — LiveCodeBench;
  **automated decontaminated refresh** — SWE-rebench; **three contamination
  types for web-searching agents** (metadata / question-context / explicit
  answer leakage) — the agent-contamination taxonomy indexed in awesome-evals §6.
- **Success by retrieval rather than reasoning** — Cursor's audit of 731
  trajectories, where a majority of "successful" resolutions retrieved known
  fixes; re-run under strict isolation.
- **Broken tests and wrong ground truth in respected benchmarks** — the
  SWE-bench audit finding a majority of audited failures were broken tests;
  MMLU-Redux (~6.5% of questions in error); Northcutt et al. on pervasive label
  errors, <https://arxiv.org/abs/2103.14749>.
- **Reward hacking / specification gaming under metric pressure** — Anthropic,
  "Natural Emergent Misalignment from Reward Hacking in Production RL",
  <https://www.anthropic.com/research/emergent-misalignment-reward-hacking>;
  Krakovna et al. on specification gaming.
- **Models recognizing they are being evaluated** — OpenAI, "Deployment
  Simulation", <https://openai.com/index/deployment-simulation/>; and the
  documented case of a model locating and decrypting its own benchmark's answer
  key, indexed in awesome-evals §6.
- **Evals are not all you need — offline tests + production monitoring + real
  user iteration** — Reganti & Badam,
  <https://www.oreilly.com/radar/evals-are-not-all-you-need/>.

## The framing

- **"If you can eval it, you have built it"; verifiable beats judgeable** —
  Jason Wei, "Asymmetry of Verification and Verifier's Law",
  <https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law>;
  Han-Chung Lee, "A Taxonomy of RL Environments for LLM Agents",
  <https://leehanchung.github.io/blogs/2026/03/21/rl-environments-for-llm-agents/>
  (a benchmark is a frozen RL environment; `E = {T,H,V,S,C}`).
- **Eval = dataset + harness + rubric, written so the scorer is reusable as a
  reward** — PrimeIntellect verifiers,
  <https://github.com/PrimeIntellect-ai/verifiers>.

## Caveat on this map

These citations are transcribed from awesome-evals' annotations, which are
themselves curated summaries. Where a claim here is load-bearing for a decision,
open the primary source and confirm the number before relying on it — several
of the most-quoted figures in this literature (the self-favoring percentages,
for one) are hedged by their own authors.

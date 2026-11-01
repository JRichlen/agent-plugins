# AGENTS.md — delegated execution

Read `skills/delegated-intelligence/SKILL.md` for bounded dispatch, handback,
integration and recovery. Use the operating contract in `core/OPERATING.md`
for shared authority, interaction and state; its generated package copy is
`context/OPERATING.md`. Do not restate or edit those policies here.

The service ends when its assignments are accounted for and returns evidence
and gaps to the calling method. It does not own persistent plans, retry quotas,
a coordinator persona or autonomous learning.

The command is `commands/delegated-intelligence.md`. Installation does not
modify global instructions. Real workers are required for real dispatch;
sequential work must be labeled as such.

Deterministic contract and mutation controls are in `evals/cheap/`. They
check the shipped procedure and references, not measured model effectiveness.

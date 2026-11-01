# Check claims and verify work

Use evidence proportionate to the claim. A routine statement may need a direct
read or test; selected work may need agreed executable acceptance criteria and
an independent reviewer. Neither route introduces a universal workflow.

## Install

```text
/plugin marketplace add JRichlen/agent-plugins
/plugin install verify-before-claim@jrichlen
```

## Choose the procedure

- [Check a claim](skills/verify-before-claim/SKILL.md): inspect the source, run
  the relevant check and state what remains uncertain.
- [Verify work](skills/verify-work/SKILL.md): create and pin an acceptance
  contract, protect it while work proceeds, then obtain independent review.

Core reporting and authority rules remain binding without selecting a procedure.
The method returns to the existing task record; it creates no coordinator,
mandatory planning round, retry policy, model tier or automatic observer.

The shell helpers require Bash and coreutils. Claude Code can additionally use
the contract-write hook. Other hosts need supported equivalent enforcement;
script integrity/freshness checks do not establish that an independent reviewer
actually ran. Preserve that distinction in the handback.

[Migration and legacy data](../../docs/migrations/verification.md) describes
the retired product identity and thin source-path adapters. Earlier
[claim-check measurements](docs/measurement-history.md) are historical findings,
not validation of this integration or proof of benefit across hosts.

PORTABILITY: On another harness without the Claude Code write hook, use a
supported equivalent write guard or check pinned hashes before and after work.
Hash checks detect drift afterward; they do not prevent writes. If prevention
is required and unavailable, report that unmet prerequisite rather than claiming
protected execution. Independent review still requires an actual reviewer.

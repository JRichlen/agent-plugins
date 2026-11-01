# Delegate independent work

Use this service when a bounded part of a task benefits from real workers.
It supplies briefs, output ownership, integration and recovery. Small or tightly
coupled work can stay direct.

## Install and use

```text
/plugin marketplace add JRichlen/agent-plugins
/plugin install delegated-intelligence@jrichlen
```

Choose its installed command from the host's command menu. See the
[method](skills/delegated-intelligence/SKILL.md) for entry, acceptance and exit.

The service reuses the current task record. Shared rules and state come from
[core](context/OPERATING.md); persistent plans belong to Wayfinder, retry
bounds to stop-rule and completion checks to verify-before-claim. It introduces
no mandatory board, model-brand tier ladder, automatic review or scheduler.

## Compatibility and limits

The former Jori product is retired. Its duplicated coordinator identity,
boards, tiers and observer policy were removed. Useful whole-cycle cost and
proportional-record guidance now belongs to this execution method. See the
[migration](../../docs/migrations/coordination.md).

Real dispatch requires real worker tools. A file or worker report alone does
not prove the result correct. The templates and free checks do not establish
behavioral benefit or cross-host runtime parity.

The packaged core is a generated copy of the repository source. Installation
does not activate always-on host instructions; that requires separate reviewed
host adoption.

## License

MIT.

# tracer-bullets

Ship the thinnest possible end-to-end slice through a system (or a question)
first — get it working for real — then widen it in place. Applies to software
delivery (a real skeleton request that hits every layer) and to open-ended
investigation/research (a real shallow pass that touches every branch of an
unfamiliar space before any one branch gets read deeply).

## Where the idea comes from

- **Origin:** Andrew Hunt & David Thomas, *The Pragmatic Programmer* — the
  tracer-round metaphor. A tracer round is a live round on the same trajectory
  as the rest of the belt, made visible so you can see where your fire lands;
  it is not a separate, disposable round fired just to check your aim. That
  distinction — real and kept vs. disposable and discarded — is the whole point
  of this skill.
- **Applied write-up:** Matt Pocock, ["How I Use Tracer Bullets To Ship Fast As
  A Senior Engineer"](https://www.aihero.dev/tracer-bullets) (aihero.dev). The
  software-delivery half of this skill leans on that restatement of the
  technique for AI-assisted engineering.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install tracer-bullets@jrichlen
```

## What it defends

The invariant this plugin protects: a tracer bullet must always be a real,
end-to-end, kept-and-built-upon slice — and it must never be treated like a
prototype or spike, which answers a question and gets thrown away. The two are
easy to conflate in practice (both are "build something small first"), and
conflating them is the specific failure mode this skill exists to prevent. See
`skills/tracer-bullets/SKILL.md` for the full procedure, the two worked use
cases (software delivery and investigation/research — including a self-
referential worked example: this very plugin was shipped using the methodology
to investigate the site the methodology came from), and the explicit
tracer-bullet-vs-prototype contrast table.

## License

MIT

# dev-diary

A developer journal that writes itself — and stays scannable.

At the end of a day, run the loop. It discovers what you actually did from your
local Claude Code sessions, git commits, and prompt history; interviews you about
what mattered and *why*; and records a tight, dated entry you can scan in seconds
and still trust months later.

```
/dev-diary
   discover  →  today's prompts, sessions, and commits (deterministic digest)
   research  →  drill into the commits/sessions that look significant
   interview →  confirm what mattered, capture the reasoning behind it
   write     →  entries/<YYYY>/<date>.md  +  CHANGELOG.md   (in the journal repo)
```

## Commands

- **`/dev-diary [date]`** — write today's entry (or backfill a past `YYYY-MM-DD`).
- **`/dev-diary-review [date]`** — revise an entry that already exists: correct a
  mistake, enrich a thin/backfilled day with the reasoning only you remember, or
  tighten the writing. Clears the `backfilled: true` marker once a day is really
  reviewed.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install dev-diary@jrichlen
```

## The tool/journal split

This plugin is **only the tool**. The **journal is a separate private repo at
`~/projects/dev-diary`** — that's where entries and the changelog live. The plugin
is shareable; the diary is not, so they're kept apart. Both skills reference the
journal by that absolute path.

If your journal lives elsewhere, point the skills at it by editing the journal-root
path in `skills/dev-diary/SKILL.md` and `skills/dev-diary-review/SKILL.md`.

## Layout

```
dev-diary/
├── .claude-plugin/plugin.json
├── commands/
│   ├── dev-diary.md            ← /dev-diary
│   └── dev-diary-review.md     ← /dev-diary-review
└── skills/
    ├── dev-diary/
    │   ├── SKILL.md                    ← the write loop
    │   ├── scripts/discover-today.sh   ← deterministic "what happened" digest
    │   ├── templates/entry.md          ← the entry shape
    │   └── references/format-guide.md  ← the house style
    └── dev-diary-review/
        └── SKILL.md                    ← the edit loop
```

## Principles

- **Significance over completeness** — the entry is the judged version of a day.
- **Capture the why** — decisions without reasoning rot.
- **Never commit a secret** — entries redact pasted tokens/keys by rule.
- **Backfilled ≠ reviewed** — reconstructed days say so until you vet them.

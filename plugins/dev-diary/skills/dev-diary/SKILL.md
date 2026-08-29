---
name: dev-diary
description: >-
  Run a guided end-of-day loop that discovers everything the user did today from
  their local Claude Code sessions, git commits, and prompt history, interviews
  them about what actually mattered, and records a scannable dated entry in the
  dev-diary journal. Use this whenever the user wants to write a dev diary, daily
  log, work journal, standup note, changelog entry, or "what did I do today"
  wrap-up — or says things like "log today", "diary entry", "capture today",
  "end of day", "what did I get done", "dev-diary", or invokes /dev-diary. Also
  use it to backfill a past day (pass the date) or to review recent entries.
argument-hint: "[YYYY-MM-DD]  (defaults to today, local time)"
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Dev Diary

Turn a day of scattered work into one entry that a busy person can scan in
fifteen seconds and a future self can trust. The value is not transcription —
the raw signals already exist. The value is **judgment**: separating the two or
three things that mattered from the noise, and recording *why* they mattered.

This skill ships in the `dev-diary` plugin, but the **journal itself is a
separate private repo at `~/projects/dev-diary`**. Entries are committed there,
organized temporally under `entries/YYYY/`. Keeping the tool (this plugin) and
the journal (that repo) apart is deliberate: the plugin is shareable; the diary
is private.

## The loop

Work through these phases in order. Do not skip the interview — an unreviewed
auto-summary is exactly the low-signal artifact this skill exists to avoid.

### 1. Resolve the day and locate the repo

- Target date = the argument if given, else today in **local** time
  (`date +%F`). The user's clock is what defines "today", not UTC.
- The journal root is `~/projects/dev-diary` (a separate private repo from this
  plugin). Confirm `entries/` exists there.

### 2. Discover — run the deterministic first pass

Run the discovery script and read its digest. It is fast, read-only, and
gathers the three signals that actually show what happened:

```bash
<skill-dir>/scripts/discover-today.sh [YYYY-MM-DD]
```

It emits Markdown with three sections: **Prompts typed** (from
`~/.claude/history.jsonl`), **Sessions active** (titles + turn counts from
session transcripts), and **Commits authored** (across `~/projects/*`). Each
degrades gracefully if a source is missing.

### 3. Research — drill into what looks significant

The digest is a map, not the territory. For anything that reads like a real
event — a shipped feature, a hard decision, a nasty bug, a direction change —
go one level deeper before you form an opinion:

- `git -C ~/projects/<repo> show <hash>` for a commit that looks meaningful.
- `git -C ~/projects/<repo> log --oneline --since=... --until=...` to see a
  cluster of related commits as one thread.
- Read a slice of a session transcript
  (`~/.claude/projects/<slug>/<sessionId>.jsonl`) when a session title hints at
  something the commits don't capture (a decision, a dead end, a lesson).

Aim to walk into the interview already understanding the day. Come with a draft,
not a blank page.

### 4. Interview — confirm what mattered

Synthesize the signals into a short draft of candidate **significant events**,
grouped the way the entry will read (Shipped / Changed / Decided / Learned /
Open threads / Next — see the template). Then interview the user to sharpen it.
Keep it tight and specific; reference concrete items so they can react, not
recall:

- "I see these as today's headline items — [list]. Did I miss anything, or is
  something here just noise?"
- "This looks like a real decision: [X over Y]. What was the reasoning?"
- "Anything you learned or got burned by that isn't in the commits?"
- "What's still open / what's tomorrow's first move?"

Use `AskUserQuestion` when a few crisp choices will move faster than prose (e.g.
picking the day's headline, or which threads are still open). Otherwise just
talk. The point is to capture the *why* behind events and the things that never
touch a commit — judgment, not stenography.

### 5. Write — record the entry

Write to `entries/<YYYY>/<YYYY-MM-DD>.md` using `templates/entry.md` as the
shape. If the file already exists (backfill or a second pass on the same day),
**merge** — read it, fold in the new material, don't clobber prior content.

Follow `references/format-guide.md` for the house style. The non-negotiables:

- **Scannable first.** A one-line TL;DR up top, then short bullets under emoji
  headers. Someone should get the gist without scrolling.
- **Significant over complete.** Two great bullets beat twenty mechanical ones.
  Fold routine churn into a single line or drop it. Empty sections get removed.
- **Every "Decided" says why.** A decision without its rationale is useless in
  three months.
- **Redact secrets.** Prompt history and transcripts routinely contain API
  tokens, keys, and credentials the user pasted. **Never** copy a secret into a
  committed entry — this repo lives on GitHub. If a token is relevant, write
  "rotated the Tailscale API key", never the key itself.
  Before writing an entry off-machine, run `evals/cheap/secret-gate.sh` (in the
  marketplace repo) over the draft — a mechanical WITNESS that redaction held.
- **Link to durable anchors.** Commit hashes, repo names, PR numbers — not
  transcript paths, which are local and disappear.

### 6. Update the rollups and offer to commit

- Prepend a one-line entry for the day to `CHANGELOG.md` (reverse-chronological:
  newest at top), so the changelog is a skimmable spine of the whole journal.
- If `README.md` carries a "Recent entries" index, add the new day there too.
- Show the user the finished entry. Offer to commit (and push, since the repo
  has a remote): `git -C ~/projects/dev-diary add -A && git commit`. Use a
  message like `diary: 2026-07-17`. Only commit when they say so.

## Notes on judgment

- **Timezone.** All windows are local. The discovery script already handles the
  UTC→local conversion for transcripts; trust its output.
- **A quiet day is a valid entry.** If little happened, say so in one line and
  stop. Don't manufacture significance.
- **Backfilling.** `dev-diary 2026-07-15` reconstructs a past day from the same
  signals. Older transcripts may have rotated away; lean on git history, which
  persists.
- **This is the user's voice, first-person and terse.** Write the way they'd
  write a note to themselves, not a press release.

## References

- [`references/consolidate-delta.md`](references/consolidate-delta.md) — emit
  typed `ADD`/`UPDATE`/`REMOVE` deltas and a `SHAPE:` tag alongside the prose
  entry, so recurring failures are countable by `recurrence-detector` instead
  of needing a month of prose re-read.

---
name: dev-diary-review
description: >-
  Open a past dev-diary entry and revise it with the user — correct mistakes,
  enrich a thin or backfilled day with the reasoning only they remember, tighten
  the writing, or re-pull the day's signals to check facts. Use whenever the user
  wants to edit, revise, amend, correct, fix, expand, or clean up an existing
  diary entry, review a backfilled day, or says things like "fix the 07-15
  entry", "that day is wrong", "review my backfilled entries", "edit the diary",
  or invokes /dev-diary-review. This is the editing counterpart to /dev-diary
  (which writes today's entry); reach for it for any change to a day already on
  disk.
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion
metadata:
  argument-hint: "[YYYY-MM-DD]  (the entry to edit; omit to pick from recent)"
  user-invocable: "true"
---

# Dev Diary — Review & Edit

Revise a day that's already written. The entry exists; the job now is to make it
*truer* — fix what's wrong, add the judgment only the user carries in their head,
or sharpen the prose — without losing what's already good. Editing is not
rewriting: preserve every bullet that still holds.

The journal lives in the separate private repo `~/projects/dev-diary`; entries
are at `entries/<YYYY>/<YYYY-MM-DD>.md`.

## The loop

### 1. Pick the entry

- If a date was given, edit `~/projects/dev-diary/entries/<YYYY>/<date>.md`.
  If that file doesn't exist, say so and offer to write it fresh with `/dev-diary <date>`.
- If no date, show a short menu of recent entries so the user can choose. The
  fastest source is the changelog spine:
  ```bash
  sed -n '1,15p' ~/projects/dev-diary/CHANGELOG.md
  ```
  or list files: `ls ~/projects/dev-diary/entries/*/ | tail`. Ask which day.

### 2. Load what's there — and, if useful, re-check the facts

- Read the current entry in full. This is your baseline; you are amending it.
- When the edit is about accuracy (not just wording), re-pull the day's signals
  so you're correcting against evidence, not guessing:
  ```bash
  ~/projects/dev-diary/skills/... # NOT here — the script ships in this plugin:
  <this-plugin>/skills/dev-diary/scripts/discover-today.sh <date>
  ```
  (The discovery script lives beside the sibling `dev-diary` skill:
  `../dev-diary/scripts/discover-today.sh`.) Drill into a commit with
  `git -C ~/projects/<repo> show <hash>` when a claim is in question.

### 3. Interview — find out what actually needs to change

Don't assume the shape of the edit. Ask, then act. Common modes:

- **Correction** — "What's wrong in this entry?" Fix the specific claim; leave
  the rest untouched.
- **Enrichment** — a backfilled or git-only day is often thin on the *why*.
  "This day was reconstructed from commits — what was the actual reasoning behind
  [decision]? Anything you learned that never hit a commit?" Fold their answer
  into 🧭 Decided / 💡 Learned.
- **Tightening** — the entry is bloated or buried. Cut churn, sharpen the TL;DR,
  merge redundant bullets.

Use `AskUserQuestion` when a few concrete choices are faster than prose. Keep the
user reacting to specifics, not recalling from scratch.

### 4. Apply the edits

Edit the file in place. Hold the house style (`../dev-diary/references/format-guide.md`)
— the same rules that govern a fresh entry govern an edited one:

- **Significance over completeness**; every 🧭 Decided bullet states its *why*.
- **Delete sections that end up empty**; add a section if the edit introduces one.
- **Redact secrets** — never introduce a token/key/credential while editing; this
  repo is on GitHub.
- **Durable anchors only** — repo names, commit hashes, PR/issue numbers.
- Preserve the entry's voice: first person, terse, a note to self.

### 5. Clear the "backfilled" marker once a day is genuinely reviewed

Backfilled entries carry `backfilled: true` in front matter and end with an
italic footer like `_Backfilled from git … ; not live-reviewed._`. That marker
means "reconstructed, unconfirmed." **Once the user has actually reviewed and
corrected the day with you, it is no longer unconfirmed** — remove the
`backfilled: true` line and delete the footer, so the marker keeps meaning
something.

- If the pass was only a light copy-edit and the user didn't confirm the
  substance, leave the marker in place and ask which it was.
- Don't remove the marker on a day the user didn't actually vet.

### 6. Keep the rollups in sync, and offer to commit

- If the TL;DR or headline changed, update that day's line in
  `~/projects/dev-diary/CHANGELOG.md` and (if present) the README index — and
  drop the `⤵ backfilled` tag on the changelog line when you clear the marker.
- Show the user the revised entry. Offer to commit from the journal repo:
  `git -C ~/projects/dev-diary add -A && git commit -m "diary: revise <date>"`
  (and push — the repo has a remote). Only commit when they say so.

## Notes

- **One entry at a time by default.** If the user asks to sweep several backfilled
  days, do them one-by-one so each gets real review — that's the whole point of
  the marker. Don't bulk-clear markers without per-day confirmation.
- **Never invent to fill a gap.** If the user doesn't remember the *why* behind a
  reconstructed decision, leave it as-is (still marked) rather than fabricating a
  rationale. An honest thin entry beats a confident wrong one.
- **This skill only edits existing days.** For today (or a brand-new past day),
  use `/dev-diary`.

# 🪦 Graveyard

**Archive old GitHub repositories into a single private "graveyard" repo as
restorable git bundles — then safely delete the originals.**

Got a GitHub account cluttered with dead side-projects, abandoned experiments,
and one-off repos you'll "definitely come back to"? Graveyard walks you through
retiring them: it captures each repo's **complete history** (every branch, tag,
and even pull-request refs) into a single `.bundle` file, stores them all in one
cheap private repo, and only deletes an original **after its backup is verified
present**. Nothing is lost, and your repo list gets a lot shorter.

It ships as a **Claude Code plugin** but works with **any coding agent** — the
core is plain `bash` + `git` + `gh`, driven by a standard `SKILL.md` and an
`AGENTS.md` entry point.

> Part of the [agent-plugins](../../README.md) marketplace.

---

## What it does

1. **Lists** your repos with the details you need to decide (size, last push,
   fork status, visibility).
2. **You choose** which to retire. Empty repos and forks are flagged — no point
   bundling those.
3. **Bundles** each chosen repo: `git clone --mirror` + `git bundle create --all`
   captures the full history, then **verifies** the bundle is valid.
4. **Documents** every archive — a per-repo `README.md` with restore commands
   plus a `metadata.json` snapshot, and a top-level index.
5. **Pushes** the graveyard to a private GitHub repo and **confirms** each
   bundle actually landed.
6. **Generates a guarded delete script** for you to review and run. It
   re-checks each backup exists on GitHub before deleting the original.

## Why git bundles?

A [`git bundle`](https://git-scm.com/docs/git-bundle) is a single file of real
git objects — not a zip of the working tree. You can `git clone` straight from
it, and it preserves the entire history. Mirror-cloning first means the bundle
holds **every** ref, so a restored repo is indistinguishable from the original.
That fidelity is exactly what makes deleting the original safe.

```sh
# Restoring is a one-liner:
git clone my-old-project.bundle my-old-project
```

## Quick start

### As a Claude Code plugin

```sh
# Add the marketplace, then install:
/plugin marketplace add JRichlen/agent-plugins
/plugin install graveyard@jrichlen
```

Then just ask, or run the command:

```
/graveyard
```
> "Help me archive my old GitHub repos into a graveyard and delete them."

### With any other agent (Codex, Cursor, Gemini, Aider, …)

```sh
git clone https://github.com/JRichlen/agent-plugins
cd agent-plugins/plugins/graveyard
```

Point your agent at [`AGENTS.md`](AGENTS.md) (most read it automatically) and
ask it to archive your old repos. See [docs/installation.md](docs/installation.md)
for per-harness setup.

### Or run the scripts directly, no agent

```sh
# Back up one repo:
skills/graveyard/scripts/archive-repo.sh octocat/Hello-World ./graveyard

# Generate a guarded deletion script:
skills/graveyard/scripts/generate-delete-script.sh octocat graveyard \
  --bundled "Hello-World" > delete-originals.sh
```

## Requirements

- [`git`](https://git-scm.com/)
- [GitHub CLI `gh`](https://cli.github.com/), authenticated: `gh auth login`
- Deletion needs the `delete_repo` scope — the generated script adds it for you
  interactively (one-time browser step).

## Safety model

Deleting a GitHub repo is **irreversible**, so Graveyard is built around not
trusting itself:

- The tool **never deletes anything directly.** It generates a script *you*
  review and run.
- That script **re-verifies each bundle exists in the graveyard on GitHub**
  before deleting its original. No backup, no delete.
- Repos deleted *without* a backup (empty repos, forks) are listed **explicitly**
  in the script — nothing is deleted silently.
- The graveyard repo defaults to **private**, because bundles contain full
  history including anything ever committed.

These invariants are enforced by the marketplace's eval suite — see
[`evals/`](../../evals/README.md).

## Documentation

- [Installation](docs/installation.md) — per-harness setup (Claude Code, Codex,
  Cursor, Gemini, Aider, standalone).
- [Usage walkthrough](docs/usage.md) — a full end-to-end example.
- [How it works](docs/how-it-works.md) — bundles, mirror clones, the PR-ref
  detail, and restore mechanics.

## Layout

```
plugins/graveyard/
├── .claude-plugin/plugin.json     # Claude Code plugin manifest
├── AGENTS.md                      # cross-harness entry point
├── commands/graveyard.md          # /graveyard slash command
├── skills/graveyard/
│   ├── SKILL.md                   # the portable workflow (read this)
│   └── scripts/
│       ├── archive-repo.sh        # bundle one repo (verified)
│       └── generate-delete-script.sh  # emit guarded delete script
├── docs/
└── README.md
```

## License

MIT — see [LICENSE](../../LICENSE).

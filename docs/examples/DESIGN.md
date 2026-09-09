# Example gallery — why the page looks the way it does

The gallery is a *verification surface*: real with-skill / without-skill
model runs, published so a reader can judge for themselves whether a skill
earns its slot. The first version stacked fifteen cards, each carrying the
full prompt and two full transcripts, with the judge's verdict at the bottom
and a one-line provenance string under it. It was accurate and unreadable.
This note records the schemes that were surveyed before the redesign, which
one was chosen, and what the page borrows from each — so the next change can
argue against a reason rather than a taste.

## What the content is

Per plugin: one prompt (100–1,400 chars), two transcripts (1–8 KB each), a
judge's paragraph on how they diverge with a one-word grade, and provenance.
Twenty-four plugins, so the page must be *skimmable* (which skills show the
starkest effect?) and *auditable* (where did this text come from?) at once.
Constraints: static HTML from a Python script, no build tooling, no external
assets, light and dark, byte-reproducible, and the original prompts verbatim.

## Schemes surveyed

**Information architecture.**
[Diátaxis](https://diataxis.fr/) separates tutorial, how-to, reference and
explanation and argues against mixing them in one block. Read through that
lens, a card was mixing reference (the transcripts) with explanation (the
verdict) with metadata, in the wrong order. The docs-as-code shells
([MkDocs Material](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/),
[Docusaurus](https://docusaurus.io/docs/sidebar), Stripe's three-column API
reference) all converge on a sticky left navigation plus anchored sections —
achievable in static HTML with `position: sticky` and `#anchors`.
[Storybook's](https://storybook.js.org/docs/get-started/browse-stories) sidebar
= component tree, story = one rendered case, addon panel = metadata, is the
closest mental model: plugin → captured prompt → provenance panel.

**Comparing two long texts.** GitHub's
[split/unified toggle](https://github.blog/news-insights/product-news/introducing-split-diffs/)
degrades to unified on narrow screens; matklad's
[critique](https://matklad.github.io/2023/10/23/unified-vs-split-diff.html)
is that both fail for large changes and readers want the diff *on demand*.
[promptfoo's own viewer](https://www.promptfoo.dev/docs/usage/web-ui/) — the
tool that produces these pairs — truncates cells by default with a per-cell
"details" expansion and filter chips. [Chatbot Arena](https://arena.ai/how-it-works)
shows two anonymous columns for the same prompt; its anonymity is a bias
control, not a reading aid.

**Skimmability.** Nielsen Norman Group on
[progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
(show the few most important things; label the rest so it has information
scent), the [F-pattern](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/)
(front-load the first words of every line; use a layer-cake of subheads),
the [inverted pyramid](https://www.nngroup.com/articles/inverted-pyramid/)
(the conclusion first), and [in-page links](https://www.nngroup.com/articles/in-page-links/)
(more valuable the smaller the screen). The native
[`<details>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details)
element gives script-free collapsibles.

**Disclosure of AI outputs.**
[Model Cards](https://arxiv.org/abs/1810.03993),
[Datasheets for Datasets](https://arxiv.org/abs/1803.09010) and the
[Dataset Nutrition Label](https://arxiv.org/abs/1805.03677) share one idea: a
fixed-shape facts block in the same place every time. Leaderboards go further
on *roles*: [HELM](https://crfm.stanford.edu/2025/03/20/helm-capabilities.html)
frames every score as (instruction, model, evaluator, criterion) and names
its judges per scenario; [Arena-Hard](https://arena.ai/blog/arena-hard/)
publishes the judge model and notes judge self-preference. Subject, grader
and judge are always named separately.

**Proving a file came from a run.**
[GitHub artifact attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds)
bind a file's digest to a signed SLSA provenance predicate for one workflow
run (`id-token: write`, `attestations: write`); a reader verifies with
[`gh attestation verify`](https://cli.github.com/manual/gh_attestation_verify),
ideally with `--signer-workflow`. Gotchas that shaped the design: verification
is by exact digest, so attest the captured JSON, not the HTML derived from it;
GitHub says not to attest documentation files; only the certificate and the
timestamps are unforgeable — the predicate is workflow-controlled, so the
workflow file must be public and short enough to read.

## What was chosen

A docs-as-code shell around Diátaxis *reference* content, with each card in
inverted-pyramid order and a nutrition-label provenance block:

| Element | Borrowed from | Why |
|---|---|---|
| Sticky left list of plugins with divergence dots and filter chips | MkDocs / Docusaurus sidebar; promptfoo filters; NN/g in-page links | The skim question is "which skills diverge starkly?" — answerable without scrolling |
| Verdict block first, grade as a badge, judge named under it | Inverted pyramid; HELM's evaluator-per-score | The judge's paragraph was the most useful text on the old page and sat at the bottom |
| Prompt in a `<details>` with a one-line preview, full text verbatim inside | Progressive disclosure; the "never lose the prompt" constraint | Collapsed by default so the eye lands on the verdict; expanded, it is the exact prompt in `pre-wrap` |
| Transcripts side by side, clamped to a preview with one *Read in full*; stacked below 760 px, and a manual stack toggle | promptfoo's truncated cells; GitHub's split → unified degrade | Long transcripts are the detail layer, not the skim layer; the clamp is JS-applied so a no-script reader sees everything |
| Provenance `<details>` with the same rows on every card: source, subject, grader, judge, captured, run, attestation, SHA-256, links, verify commands | Model cards / nutrition labels; Arena-Hard's judge disclosure; `gh attestation verify` | Same shape every time, and the commands are copy-pasteable |
| Page-level "Models used — by role" table and "How to verify" chain | HELM's role framing; SLSA | The site-wide answer to "who graded whom, and how would I check" |
| Same-family-judge warning badge | Arena-Hard's self-preference note | A seed judged by the subject's own model family is disclosed as such, not dressed up |

## What was rejected

- **One card expanded at a time (Storybook-style routing).** Needs JS
  routing and breaks deep links for no-script readers; anchored sections with
  `:target` highlighting give most of the benefit.
- **Rendering the transcripts as Markdown.** Prettier, but it changes what the
  model produced; the page shows the raw text with only fenced code promoted
  to `<pre>`, as before.
- **A hand-curated "best examples" strip.** Cherry-picking is exactly what a
  verification surface must not do; the sidebar's divergence dots let the
  reader pick.
- **Truncating long prompts.** The preview line is a summary; the full prompt
  is always one click away and never edited.
- **Attesting the HTML.** The page is derived; the cheap tier proves it is a
  pure function of the JSON, and the JSON is what gets signed.

## The landing page

The old hub listed two of twenty-four plugins by hand. It is now generated
(`docs/build-index.sh`) from `marketplace.json`, the snapshots and the packs,
so every plugin appears with its example, its grading status and its deep
dive, and the cheap tier fails a commit that lets it drift. The three entry
cards follow Diátaxis loosely: evidence (the gallery), story (the timeline),
reference (the testing inventory).

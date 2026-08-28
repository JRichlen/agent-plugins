# Tells — full catalogue

Loaded on demand by `ai-writing-mistakes/SKILL.md` for a dedicated cleanup pass.
The SKILL.md carries the twelve most common; this is the rest, grouped by what
the tell is doing to the sentence.

Every entry follows the same shape: the pattern, the commitment it is standing
in for, and a rewrite that supplies that commitment. Read the rewrites as
demonstrations of the repair, not as templates to copy — the point is always to
say the specific thing the draft avoided saying.

---

## 1. Structural tics

### The negation flip

> It's not a cache — it's a coordination layer.
> This isn't just refactoring. It's a rethink of how the module is bounded.

Sets up a comparison nobody asked for so the second half arrives sounding
earned. The first half is always a straw man; deleting it costs nothing.

**Fix:** assert the second half, with the evidence that makes it true.

> The layer holds the lease, so two writers can't claim the same shard.

### The pivot-back

> But here's the thing.
> And that's where it gets interesting.
> The real question is whether...

A paragraph break dressed as a revelation. It promises the next sentence will
be surprising, which puts a debt on it that it rarely pays.

**Fix:** delete the pivot and keep the sentence after it. If that sentence
cannot stand without the drum roll, it was not the point.

### Anaphora and symmetry

> Not just faster. Not just cheaper. Fundamentally different.

Three parallel fragments in a row read as rhetoric because the shape carries
the emphasis instead of the content.

**Fix:** one sentence, one claim, with the number that makes it land.

### The one-line paragraph drumbeat

Alternating a long paragraph with a four-word line, repeatedly, at regular
intervals. Once, this is emphasis. Three times on a page, it is a tic — and it
makes the piece unskimmable, because everything is emphasized.

**Fix:** keep at most one per section, at the point that genuinely matters.

### Perfectly balanced coverage

Two options, an equal number of words each, symmetric pro/con lists, and no
pick. The symmetry is a tell that the writer had no view.

**Fix:** rank them and say why. `human-voice` requires the verdict first; an
even-handed survey with a preference buried in the last line fails that rule
too.

---

## 2. Lexical filler

### Filler verbs

delve · leverage · harness · unlock · navigate · foster · underscore ·
showcase · embark · streamline · elevate · empower · facilitate · utilize

Each has a plain equivalent that is shorter and more specific. "Leverage the
API" is "call the API". "Navigate the tradeoffs" is "choose".

**Caveat:** these are ordinary words in the right register. "Leverage" in a
finance document, "harness" in a hardware one, "delve" in a cited title — leave
them.

### Abstraction nouns

landscape · realm · ecosystem · tapestry · testament · beacon · cornerstone ·
paradigm · journey · at the intersection of · in the world of

They put a category where the subject should be. "The observability landscape"
is "the four tools we evaluated".

**Fix:** name the actual thing, and if you cannot name it, you do not have a
subject yet.

### Unearned quality adjectives

robust · seamless · comprehensive · cutting-edge · state-of-the-art ·
game-changing · powerful · elegant · rich · thoughtful

They assert a verdict on the thing instead of describing a property of it. The
reader cannot check any of them.

**Fix:** the checkable property.

> ~~a robust retry mechanism~~ → retries five times with jitter, then dead-letters

### "It's worth noting that"

> It's worth noting that the migration is irreversible.
> It's important to understand that this only applies to v2.

The frame is longer than the note.

**Fix:** state the note. If it were not worth noting you would not be writing it.

### Analogy inflation

> Think of it like a post office for events.

Useful once, for a genuinely unfamiliar mechanism. Reflexive when the plain
statement is already shorter than the analogy.

**Fix:** try the plain statement first; keep the analogy only if it is shorter
or if the mechanism is genuinely alien to the reader.

---

## 3. Hedging and disclaiming

### Stacked hedges

may potentially · could possibly · generally tends to · in some cases might ·
it seems likely that perhaps

Three hedges do not express more uncertainty than one; they express
unwillingness to be pinned down.

**Fix:** one hedge, or `human-voice`'s `⚠️` / `❓` tag, which says it once and
in a vocabulary the reader already knows.

### The both-sides close

> Ultimately, the right choice depends on your specific needs and priorities.
> There's no one-size-fits-all answer here.

Almost always true and never useful. It returns the decision to the person who
asked precisely because they could not make it.

**Fix:** name the condition that decides it, then decide it for the case in
front of you.

> Under 10k writes/sec, take Postgres. The DynamoDB case starts at the point
> you need multi-region writes, which you said you don't.

### Pre-emptive capability disclaimers

> As an AI, I can't browse the web, but...
> I don't have access to your codebase, however...

Relevant only when it changes the answer. Otherwise it spends the verdict slot
on an apology.

**Fix:** if the limit shapes the answer, state it once, inline, where it bites.
If it does not, cut it.

---

## 4. Shape, rhythm, and punctuation

### Em-dash uniformity

The tell is not the character; it is one per paragraph, every paragraph, always
in the same role — a parenthetical aside dropped mid-sentence. The SKILL.md
rule is at most one per paragraph. Where a second appears, ask what the aside
is doing: usually it is a qualification that belongs in its own sentence, or a
definition that belongs in a comma clause.

### Uniform sentence and paragraph length

Machine prose converges on 15–25 word sentences and three-sentence paragraphs.
The absence of variation reads as absence of emphasis, because emphasis in
prose *is* variation.

**Fix:** after the longest sentence in a section, write a short one. Let one
paragraph be a single line.

### Bulletization

Bullets whose items are full paragraphs, or that must be read in order, or that
are not parallel in grammar.

**Fix:** a list is for parallel, independently readable items. Anything else is
a paragraph that got chopped up. Ordered steps are a numbered list, not
bullets.

### Decorative bold and heading inflation

Bold scattered on phrases that are not the load-bearing ones; a heading over
every two-line section; Title Case On Every Heading.

**Fix:** bold marks what the skimming reader must not miss — a few per page. A
section under about four lines takes a bold lead-in, not a heading.

### Emoji decoration

Emoji as ornament on headings in human-read prose. Distinct from
`machine-voice`, where a small closed set of glyphs are *typed status markers*
and carry meaning, and from `human-voice`'s confidence vocabulary. Ornamental
emoji in prose belong to neither system.

**Fix:** remove them. If a glyph is carrying meaning, it belongs to one of the
two closed vocabularies and should be used as that vocabulary defines it.

---

## 5. Content tells

These are the expensive ones. The sections above cost the reader attention;
these cost them accuracy.

### Invented specificity

> Studies show a 40% improvement in developer productivity.
> Most teams find this approach reduces onboarding time by half.

A number with no source, attached to a claim that sounds better with one.
Fluency makes it more believable than a vague claim would have been, which is
what makes it worse.

**Fix:** cite it, measure it, or state it qualitatively and tag it `❓`.

### The confident summary of unread material

Describing a file, a doc, or a library's behaviour in fluent detail without
having opened it. The prose gives no signal that it is reconstruction.

**Fix:** read it, or say which parts you did not read. `human-voice`'s
confidence vocabulary exists for exactly this.

### Sycophantic openers

> Great question! · Absolutely! · You're right to be concerned about that.
> That's a really interesting problem.

**Fix:** delete. The answer is the respect.

### Question restatement

> You're asking about how to handle retries in the payment worker.

Consumes the verdict slot to prove the question was read.

**Fix:** delete. Answer, and the reader infers you understood.

### The empty closer

> In summary, choosing the right database is a critical decision that depends on
> many factors.

Restates the topic instead of the finding.

**Fix:** delete, or replace with `human-voice`'s scoped depth offer — one line
naming what was left out.

### The audience spanner

> Whether you're just getting started or scaling to millions of users...

There is one reader, and you know something about them.

**Fix:** write to the reader you have.

---

## What this catalogue is not

A blocklist. Every pattern above appears in good prose written by people, used
deliberately, once, where it earns its place. The failure mode this skill
guards against second — after unrepaired filler — is a mechanical find-and-
replace that leaves the meaning untouched and the sentence slightly worse.

The test is always the same:
**does the fix supply a commitment the draft was avoiding?**
If not, it is not a fix.

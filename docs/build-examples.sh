#!/usr/bin/env bash
#
# build-examples.sh — generate the before/after example gallery for GitHub Pages.
#
# Reads every committed snapshot in docs/examples/data/*.json (each a REAL,
# provenanced with-skill / without-skill model run — see capture-example.sh) and
# each plugin's SKILL.md description, and writes a single self-contained,
# theme-aware static page to docs/examples/index.html. No external assets, no
# build step, no network — GitHub Pages serves the file as-is.
#
# Page shape (see docs/examples/DESIGN.md for the research behind it):
#   - a sticky plugin list + filters on the left, one anchored card per plugin
#   - inside a card, inverted-pyramid order: verdict first, then the scenario,
#     the verbatim prompt (collapsible, never truncated), then the two
#     transcripts side by side — clamped to a preview with a single expand,
#     stacking to one column on narrow screens — and last a nutrition-label
#     provenance block naming every model by role plus the exact commands that
#     verify the snapshot against its GitHub Actions run
#   - a page-level disclosure of which models answered, graded and judged, and
#     a "how to verify" section describing the evidence chain end to end
#
# Deterministic: same snapshots in, byte-identical HTML out (no timestamps
# minted here — provenance timestamps come from the snapshots themselves; the
# per-snapshot SHA-256 is of the committed file), so the cheap tier can assert
# the committed index.html is in sync with the data.
#
# Usage:  build-examples.sh            # write docs/examples/index.html
#         build-examples.sh --check    # exit 1 if index.html is stale
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="$HERE/examples/index.html"

render() {
python3 - "$ROOT" <<'PY'
import collections, glob, hashlib, html, json, os, re, string, sys
root = sys.argv[1]
sys.dont_write_bytecode = True   # never litter docs/_shared with __pycache__
sys.path.insert(0, os.path.join(root, "docs", "_shared"))
from sitenav import nav, BASE_CSS, REPO

data_dir = os.path.join(root, "docs", "examples", "data")
snaps = []
for f in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
    try:
        raw = open(f, "rb").read()
        s = json.loads(raw.decode("utf-8"))
        s["_sha256"] = hashlib.sha256(raw).hexdigest()
        s["_file"] = os.path.basename(f)
        snaps.append(s)
    except Exception as e:
        print(f"<!-- skip {f}: {e} -->", file=sys.stderr)

def esc(x):
    return html.escape("" if x is None else str(x))

def desc_of(plugin):
    p = os.path.join(root, "plugins", plugin, "skills", plugin, "SKILL.md")
    if not os.path.isfile(p):
        return ""
    txt = open(p).read()
    m = re.search(r'description:\s*>?-?\s*\n?(.*?)(?:\nlicense:|\ncompatibility:|\n---)', txt, re.S)
    if not m:
        return ""
    return " ".join(m.group(1).split())

def has_deep_dive(plugin):
    return os.path.isfile(os.path.join(root, "docs", plugin, "index.html"))

def render_output(s):
    # Show the model's real response verbatim. Escape HTML, then promote fenced
    # code blocks to <pre> so diffs read cleanly; everything else stays as the
    # model wrote it, line breaks preserved. No markdown embellishment — the
    # point is to show exactly what was produced.
    fence = re.compile(r'```(\w*)\n(.*?)```', re.S)
    parts, last = [], 0
    for m in fence.finditer(s):
        parts.append(("text", s[last:m.start()]))
        parts.append(("code", m.group(2)))
        last = m.end()
    parts.append(("text", s[last:]))
    buf = []
    for kind, seg in parts:
        if kind == "code":
            buf.append('<pre class="code">' + esc(seg.rstrip("\n")) + "</pre>")
        else:
            seg = esc(seg).strip("\n")
            if seg.strip():
                buf.append('<div class="prose">' + seg.replace("\n", "<br>") + "</div>")
    return "".join(buf)

def grade_badge(g):
    p = (g or {}).get("pass")
    if p is True:  return '<span class="badge pass" title="the pack\'s llm-rubric grader passed this output">graded: pass</span>'
    if p is False: return '<span class="badge fail" title="the pack\'s llm-rubric grader failed this output">graded: fail</span>'
    return '<span class="badge ungraded" title="no pass/fail rubric was applied to this seed">ungraded</span>'

DIV_ORDER = ["stark", "strong", "moderate", "subtle"]
def divergence_of(s):
    m = re.search(r"\[divergence: ([a-z]+)\]", s.get("notice") or "")
    return m.group(1) if m else "untagged"
def notice_body(s):
    return re.sub(r"^\s*\[divergence: [a-z]+\]\s*", "", s.get("notice") or "").strip()

def source_kind(s):
    prov = s.get("provenance") or {}
    src = str(prov.get("source") or "")
    attested = str(prov.get("attestation") or "").startswith("github")
    if src.startswith("promptfoo"):
        return ("attested" if attested else "graded")
    return "seed"

SRC_LABEL = {
    "attested": ("CI-graded · attested", "captured by the refresh workflow from a graded promptfoo run and Sigstore-attested to that run"),
    "graded":   ("CI-graded", "captured from a graded promptfoo run in CI; not attested"),
    "seed":     ("seed · ungraded", "produced by a Claude Code session outside CI; no rubric grade, no attestation"),
}

def short(text, n):
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"

# ── cards ───────────────────────────────────────────────────────────────────
cards, side_items = [], []
for s in snaps:
    plugin = s["plugin"]
    prov = s.get("provenance") or {}
    div = divergence_of(s)
    kind = source_kind(s)
    src_label, src_title = SRC_LABEL[kind]
    same_family = prov.get("same_family_judge") is True
    judge_flag = ('<span class="badge warnb" title="the divergence verdict was written by a model of the same family as the one being tested — read it as a description, not an independent grade">same-family judge</span>'
                  if same_family else "")
    deep = f' · <a href="../{esc(plugin)}/">deep dive</a>' if has_deep_dive(plugin) else ""
    run_url = prov.get("run_url") if isinstance(prov.get("run_url"), str) else ""
    commit = str(prov.get("commit") or "")
    commit_html = (f'<a href="{REPO}/commit/{esc(commit)}"><code>{esc(commit[:12])}</code></a>'
                   if re.fullmatch(r"[0-9a-f]{7,40}", commit) else f'<code>{esc(commit)}</code>')
    run_html = f'<a href="{esc(run_url)}">{esc(run_url.split("github.com/")[-1])}</a>' if run_url else "<em>none — not produced by a CI run</em>"
    json_url = f"{REPO}/blob/main/docs/examples/data/{plugin}.json"
    hist_url = f"{REPO}/commits/main/docs/examples/data/{plugin}.json"
    if kind == "attested":
        verify = (f"# 1. fetch the exact bytes this page was built from\n"
                  f"git clone {REPO}.git && cd agent-plugins\n"
                  f"sha256sum docs/examples/data/{plugin}.json      # expect {s['_sha256']}\n"
                  f"# 2. prove GitHub Actions produced those bytes, in the run linked above\n"
                  f"gh attestation verify docs/examples/data/{plugin}.json \\\n"
                  f"  --repo JRichlen/agent-plugins \\\n"
                  f"  --signer-workflow JRichlen/agent-plugins/.github/workflows/refresh-examples.yml\n"
                  f"# 3. compare the pair against the run's promptfoo-results artifact (linked from the run page)")
    elif kind == "graded":
        verify = (f"sha256sum docs/examples/data/{plugin}.json      # expect {s['_sha256']}\n"
                  f"# then open the run linked above: its promptfoo-results artifact holds the results.json this pair was cut from")
    else:
        verify = (f"sha256sum docs/examples/data/{plugin}.json      # expect {s['_sha256']}\n"
                  f"git log --format='%H %an %ad' -- docs/examples/data/{plugin}.json   # who committed it, and when\n"
                  f"# no attestation exists for a seed: the git history above is the whole provenance")
    with_out = (s.get("with_skill") or {}).get("output", "")
    without_out = (s.get("without_skill") or {}).get("output", "")
    prompt = s.get("prompt") or ""
    cards.append(f'''
<article class="card" id="{esc(plugin)}" data-div="{esc(div)}" data-src="{esc(kind)}">
  <header class="card-head">
    <div class="title-row">
      <h2><a href="#{esc(plugin)}">{esc(plugin)}</a></h2>
      <span class="badge div {esc(div)}" title="how far the two transcripts diverge, in the judge's own word">{esc(div) if div != "untagged" else "described, not graded"}</span>
      <span class="badge src {esc(kind)}" title="{esc(src_title)}">{esc(src_label)}</span>
      {judge_flag}
    </div>
    <p class="card-links"><a href="{REPO}/tree/main/plugins/{esc(plugin)}">plugin docs</a>{deep} · <a href="{json_url}">raw JSON</a></p>
  </header>
  <p class="skilldesc">{esc(desc_of(plugin))}</p>
  <div class="verdict">
    <span class="lbl">What to notice</span>
    <p>{esc(notice_body(s))}</p>
    <p class="who">Verdict source: {esc(prov.get("judge_model") if kind == "seed" else "the pass/fail grades below, from " + str(prov.get("grader_model")))}</p>
  </div>
  <p class="scenario"><span class="lbl">Scenario</span>{esc(s.get("scenario", ""))}</p>
  <details class="prompt">
    <summary><span class="lbl">Prompt</span><span class="preview">{esc(short(prompt, 150))}</span><span class="meta">{len(prompt)} chars · verbatim</span></summary>
    <div class="promptbody">{esc(prompt)}</div>
  </details>
  <div class="compare clamped">
    <div class="col without">
      <div class="col-head"><span>Without the skill</span>{grade_badge((s.get("without_skill") or {}).get("graded"))}</div>
      <div class="body">{render_output(without_out)}</div>
    </div>
    <div class="col with">
      <div class="col-head"><span>With the skill</span>{grade_badge((s.get("with_skill") or {}).get("graded"))}</div>
      <div class="body">{render_output(with_out)}</div>
    </div>
    <div class="compare-tools js-only">
      <button type="button" class="expand" aria-expanded="false">Read both transcripts in full</button>
      <button type="button" class="stack" aria-pressed="false">Stack vertically</button>
      <span class="sizes">{len(without_out):,} / {len(with_out):,} chars</span>
    </div>
  </div>
  <details class="prov">
    <summary><span class="lbl">Provenance</span>who answered, who graded, who judged — and how to verify this pair</summary>
    <dl>
      <dt>Source</dt><dd>{esc(prov.get("source"))}{(" · workflow: " + esc(prov.get("workflow"))) if prov.get("workflow") else ""}</dd>
      <dt>Subject model</dt><dd>{esc(prov.get("subject_model"))}</dd>
      <dt>Grader model</dt><dd>{esc(prov.get("grader_model"))}</dd>
      <dt>Divergence judge</dt><dd>{esc(prov.get("judge_model"))}</dd>
      <dt>Captured</dt><dd>{esc(prov.get("captured_at"))} at commit {commit_html}</dd>
      <dt>Actions run</dt><dd>{run_html}</dd>
      <dt>Attestation</dt><dd>{esc(prov.get("attestation"))}</dd>
      <dt>Snapshot SHA-256</dt><dd><code class="sha">{esc(s["_sha256"])}</code></dd>
      <dt>On GitHub</dt><dd><a href="{json_url}">this file at main</a> · <a href="{hist_url}">its commit history</a></dd>
    </dl>
    <pre class="verify">{esc(verify)}</pre>
  </details>
</article>''')
    side_items.append(f'<li data-div="{esc(div)}" data-src="{esc(kind)}"><a href="#{esc(plugin)}"><span class="dot {esc(div)}" aria-hidden="true"></span>{esc(plugin)}<span class="mini">{esc(div if div != "untagged" else "—")}</span></a></li>')

# ── page-level numbers, all computed from the data ──────────────────────────
count = len(snaps)
kinds = collections.Counter(source_kind(s) for s in snaps)
tags = collections.Counter(divergence_of(s) for s in snaps)
spread_parts = [f"{tags[k]} {k}" for k in DIV_ORDER if tags[k]]
if tags["untagged"]: spread_parts.append(f"{tags['untagged']} described without a grade")
spread = ", ".join(spread_parts) if spread_parts else "none yet"

# models disclosure — one row per distinct (source kind, subject, grader, judge)
roles = collections.OrderedDict()
for s in snaps:
    p = s.get("provenance") or {}
    key = (source_kind(s), p.get("subject_model"), p.get("grader_model"), p.get("judge_model"), p.get("same_family_judge") is True)
    roles.setdefault(key, []).append(s["plugin"])
model_rows = []
for (kind, subj, grader, judge, same), plugins in roles.items():
    label, _ = SRC_LABEL[kind]
    flag = ' <span class="badge warnb">same family</span>' if same else ""
    model_rows.append(f"<tr><td><span class=\"badge src {esc(kind)}\">{esc(label)}</span><br><small>{len(plugins)} example{'s' if len(plugins)!=1 else ''}: {esc(', '.join(plugins))}</small></td>"
                      f"<td>{esc(subj)}</td><td>{esc(grader)}</td><td>{esc(judge)}{flag}</td></tr>")

# the pack policy, read from the packs themselves so the page cannot overstate it
pack_subjects, pack_graders = set(), set()
for cfg in sorted(glob.glob(os.path.join(root, "plugins", "*", "evals", "promptfoo", "promptfooconfig.yaml"))):
    txt = open(cfg).read()
    m = re.search(r"^providers:\s*\n\s*-\s*id:\s*(\S+)", txt, re.M)
    g = re.search(r"id:\s*(anthropic:messages:\S+)", txt)
    if m: pack_subjects.add(m.group(1))
    if g: pack_graders.add(g.group(1))
packs_n = len(glob.glob(os.path.join(root, "plugins", "*", "evals", "promptfoo", "promptfooconfig.yaml")))

filters_html = "".join(f'<button type="button" class="chip" data-filter="div" data-value="{k}"><span class="dot {k}"></span>{k}</button>' for k in DIV_ORDER)

CSS = BASE_CSS + """
  .layout { display:grid; grid-template-columns:250px minmax(0,1fr); gap:2rem; max-width:1240px; margin:0 auto; padding:1.6rem 1.2rem 5rem; }
  aside.side { position:sticky; top:3.2rem; align-self:start; max-height:calc(100vh - 3.6rem); overflow:auto; font-size:.88rem; }
  @media (max-width:960px) { .layout { grid-template-columns:1fr; } aside.side { position:static; max-height:none; } }
  aside.side h3 { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:1.1rem 0 .4rem; }
  aside.side ol { list-style:none; padding:0; margin:0; }
  aside.side li a { display:flex; align-items:center; gap:.5rem; color:var(--fg); text-decoration:none; padding:.22rem .45rem; border-radius:6px; }
  aside.side li a:hover { background:var(--code-bg); }
  aside.side li.hide { display:none; }
  aside.side .mini { margin-left:auto; color:var(--muted); font-size:.72rem; }
  .dot { width:.6rem; height:.6rem; border-radius:50%; display:inline-block; background:var(--line-strong); flex:none; }
  .dot.stark { background:var(--stark); } .dot.strong { background:var(--strong); } .dot.moderate { background:var(--moderate); } .dot.subtle { background:var(--subtle); }
  .chips { display:flex; flex-wrap:wrap; gap:.35rem; }
  .chip { font:inherit; font-size:.78rem; border:1px solid var(--line-strong); background:var(--card); color:var(--fg);
    border-radius:999px; padding:.15rem .6rem; cursor:pointer; display:inline-flex; align-items:center; gap:.35rem; }
  .chip.on { background:var(--fg); color:var(--bg); border-color:var(--fg); }
  .chip.on .dot { outline:2px solid var(--bg); }
  .search { width:100%; font:inherit; font-size:.85rem; padding:.35rem .55rem; border:1px solid var(--line-strong); border-radius:6px;
    background:var(--card); color:var(--fg); margin:.3rem 0 .2rem; }
  .side-note { color:var(--muted); font-size:.8rem; margin:.3rem 0 0; }
  .js-only { display:none; } html.js .js-only { display:initial; } html.js .chips.js-only, html.js .compare-tools.js-only { display:flex; }
  main { min-width:0; }
  header.top h1 { font-size:1.9rem; margin:0 0 .3rem; letter-spacing:-.02em; }
  header.top .sub { color:var(--muted); margin:0 0 1rem; max-width:72ch; }
  .stats { display:flex; flex-wrap:wrap; gap:.5rem 1.4rem; font-size:.88rem; color:var(--muted); margin:0 0 1.4rem; }
  .stats b { color:var(--fg); font-size:1.15rem; margin-right:.25rem; }
  .howto { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem 1.2rem; margin:0 0 1.2rem; }
  .howto h2 { font-size:1rem; margin:0 0 .5rem; }
  .howto ol { margin:0; padding-left:1.2rem; }
  .howto li { margin:.25rem 0; }
  .howto .legend { display:flex; flex-wrap:wrap; gap:.4rem .8rem; margin:.7rem 0 0; font-size:.85rem; color:var(--muted); align-items:center; }
  .disclose { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem 1.2rem; margin:0 0 1.6rem; }
  .disclose h2 { font-size:1.05rem; margin:0 0 .4rem; }
  .disclose p { margin:.3rem 0 .6rem; color:var(--muted); font-size:.92rem; max-width:80ch; }
  .disclose table { width:100%; border-collapse:collapse; font-size:.85rem; }
  .disclose th, .disclose td { text-align:left; vertical-align:top; padding:.45rem .5rem; border-top:1px solid var(--line); }
  .disclose th { font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); border-top:none; }
  .disclose .tablewrap { overflow-x:auto; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1.2rem 1.4rem 1rem; margin:0 0 1.4rem; scroll-margin-top:3.6rem; }
  .card.hide { display:none; }
  .card:target { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); }
  .title-row { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
  .card h2 { margin:0; font-size:1.3rem; } .card h2 a { color:var(--fg); text-decoration:none; }
  .card h2 a:hover { text-decoration:underline; }
  .card-links { margin:.25rem 0 0; font-size:.85rem; color:var(--muted); }
  .skilldesc { color:var(--muted); margin:.6rem 0 .9rem; font-size:.9rem; max-width:90ch; }
  .badge.div { border-color:currentColor; background:transparent; }
  .badge.div.stark { color:var(--stark); } .badge.div.strong { color:var(--strong); } .badge.div.moderate { color:var(--moderate); }
  .badge.div.subtle { color:var(--subtle); } .badge.div.untagged { color:var(--muted); text-transform:none; letter-spacing:0; }
  .badge.src { background:var(--code-bg); color:var(--muted); }
  .badge.src.attested { background:var(--with-bg); color:var(--with); } .badge.src.graded { background:var(--with-bg); color:var(--with); }
  .badge.warnb { background:var(--warn-bg); color:var(--warn); }
  .badge.pass { background:var(--pass); color:#fff; } .badge.fail { background:var(--fail); color:#fff; }
  .badge.ungraded { background:var(--line); color:var(--muted); }
  .verdict { border-left:4px solid var(--accent); background:var(--accent-soft); border-radius:0 10px 10px 0; padding:.7rem 1rem .5rem; margin:0 0 .9rem; }
  .verdict p { margin:.2rem 0 .4rem; }
  .verdict .who { font-size:.8rem; color:var(--muted); margin:0; }
  .scenario { margin:0 0 .7rem; }
  details.prompt, details.prov { border:1px solid var(--line); border-radius:10px; margin:0 0 .9rem; background:var(--bg); }
  details summary { cursor:pointer; padding:.55rem .9rem; list-style:none; display:flex; align-items:baseline; gap:.5rem; flex-wrap:wrap; }
  details summary::-webkit-details-marker { display:none; }
  details summary::before { content:"▸"; color:var(--muted); font-size:.8rem; margin-right:.1rem; }
  details[open] summary::before { content:"▾"; }
  details.prompt .preview { color:var(--fg); flex:1 1 30ch; min-width:0; }
  details.prompt .meta { color:var(--muted); font-size:.78rem; margin-left:auto; }
  details.prompt[open] .preview { display:none; }
  .promptbody { white-space:pre-wrap; word-wrap:break-word; padding:.2rem 1rem .9rem 2rem;
    font:13.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  .compare { display:grid; grid-template-columns:1fr 1fr; gap:.9rem; position:relative; margin:0 0 .9rem; }
  .compare.stacked { grid-template-columns:1fr; }
  @media (max-width:760px) { .compare { grid-template-columns:1fr; } }
  .col { border:1px solid var(--line); border-radius:10px; padding:0 1rem .8rem; min-width:0; }
  .col.with { border-color:var(--with); background:var(--with-bg); } .col.without { border-color:var(--without); background:var(--without-bg); }
  .col-head { position:sticky; top:2.8rem; z-index:1; font-weight:700; font-size:.88rem; padding:.7rem 0 .5rem; margin:0 0 .3rem;
    display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; background:inherit; border-bottom:1px solid transparent; }
  .col.with .col-head { color:var(--with); background:var(--with-bg); } .col.without .col-head { color:var(--without); background:var(--without-bg); }
  html.js .compare.clamped .body { max-height:24em; overflow:hidden;
    -webkit-mask-image:linear-gradient(#000 78%, transparent); mask-image:linear-gradient(#000 78%, transparent); }
  .compare-tools { grid-column:1 / -1; align-items:center; gap:.6rem; font-size:.82rem; color:var(--muted); }
  .compare-tools button { font:inherit; font-size:.82rem; border:1px solid var(--line-strong); background:var(--card); color:var(--fg);
    border-radius:6px; padding:.3rem .7rem; cursor:pointer; }
  .compare-tools button:hover { border-color:var(--fg); }
  .compare-tools .sizes { margin-left:auto; font-family:ui-monospace,Menlo,monospace; }
  .prose { word-wrap:break-word; font-size:.93rem; }
  .code { background:var(--code-bg); border-radius:7px; padding:.6rem .7rem; overflow-x:auto; margin:.5rem 0;
    font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; }
  details.prov dl { display:grid; grid-template-columns:max-content 1fr; gap:.3rem 1rem; padding:.2rem 1rem .6rem; margin:0; font-size:.86rem; }
  details.prov dt { color:var(--muted); font-weight:600; } details.prov dd { margin:0; word-break:break-word; }
  details.prov .sha { word-break:break-all; font-size:.78rem; }
  details.prov .verify { margin:.4rem .9rem .9rem; white-space:pre; }
  @media (max-width:640px) { details.prov dl { grid-template-columns:1fr; } }
  .chain { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.8rem; margin:.8rem 0; counter-reset:step; }
  .chain .step { background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:.7rem .9rem; font-size:.88rem; }
  .chain .step::before { counter-increment:step; content:counter(step); display:inline-block; width:1.5rem; height:1.5rem; border-radius:50%;
    background:var(--accent); color:#fff; font-weight:700; text-align:center; line-height:1.5rem; margin-bottom:.4rem; font-size:.8rem; }
  .chain .step b { display:block; margin-bottom:.2rem; }
  .chain .step.weak { border-style:dashed; }
  .empty { color:var(--muted); }
  .verify-section h2 { font-size:1.2rem; margin:1.6rem 0 .3rem; }
  .verify-section h3 { font-size:1rem; margin:1.1rem 0 .3rem; }
  .verify-section p { max-width:80ch; }
"""

JS = r"""
document.documentElement.classList.add('js');
(function(){
  var state = {div:null, src:null, q:''};
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var items = Array.prototype.slice.call(document.querySelectorAll('aside.side li[data-div]'));
  var counter = document.getElementById('shown-count');
  function apply(){
    var shown = 0;
    cards.forEach(function(c){
      var ok = (!state.div || c.dataset.div === state.div) && (!state.src || c.dataset.src === state.src)
            && (!state.q || (c.id + ' ' + c.textContent).toLowerCase().indexOf(state.q) !== -1);
      c.classList.toggle('hide', !ok); if (ok) shown++;
      items.forEach(function(li){ if (li.querySelector('a').getAttribute('href') === '#' + c.id) li.classList.toggle('hide', !ok); });
    });
    if (counter) counter.textContent = shown === cards.length ? 'all ' + cards.length : shown + ' of ' + cards.length;
  }
  document.querySelectorAll('.chip').forEach(function(ch){
    ch.addEventListener('click', function(){
      var f = ch.dataset.filter, v = ch.dataset.value;
      state[f] = (state[f] === v) ? null : v;
      document.querySelectorAll('.chip[data-filter="'+f+'"]').forEach(function(o){ o.classList.toggle('on', state[f] === o.dataset.value); });
      apply();
    });
  });
  var search = document.getElementById('search');
  if (search) search.addEventListener('input', function(){ state.q = search.value.trim().toLowerCase(); apply(); });
  document.querySelectorAll('.compare').forEach(function(cmp){
    var ex = cmp.querySelector('.expand'), st = cmp.querySelector('.stack');
    ex.addEventListener('click', function(){
      var open = cmp.classList.toggle('clamped') === false;
      ex.textContent = open ? 'Collapse to preview' : 'Read both transcripts in full';
      ex.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open) cmp.scrollIntoView({block:'nearest'});
    });
    st.addEventListener('click', function(){
      var on = cmp.classList.toggle('stacked');
      st.textContent = on ? 'Side by side' : 'Stack vertically';
      st.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  });
  // a deep link to a card should show it expanded, whatever the filters
  function reveal(){
    var id = location.hash.slice(1); if (!id) return;
    var c = document.getElementById(id); if (!c || !c.classList.contains('card')) return;
    c.classList.remove('hide');
  }
  window.addEventListener('hashchange', reveal); reveal();
})();
"""

TEMPLATE = string.Template('''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill examples — before &amp; after · agent-plugins</title>
<meta name="description" content="Real, provenanced with-skill / without-skill model runs for every skill in the agent-plugins marketplace, with the models disclosed by role and a verification path back to the CI run.">
<style>$css</style>
</head>
<body>
$nav
<div class="layout">
<aside class="side">
  <h3>Filter <span id="shown-count" class="js-only"></span></h3>
  <input id="search" class="search js-only" type="search" placeholder="Search plugin or scenario" aria-label="Search examples">
  <div class="chips js-only">$filters</div>
  <div class="chips js-only" style="margin-top:.35rem">
    <button type="button" class="chip" data-filter="src" data-value="attested">attested</button>
    <button type="button" class="chip" data-filter="src" data-value="graded">CI-graded</button>
    <button type="button" class="chip" data-filter="src" data-value="seed">seed</button>
  </div>
  <p class="side-note">Dots grade divergence in the judge's own word: <span class="dot stark"></span> stark, <span class="dot strong"></span> strong, <span class="dot moderate"></span> moderate, <span class="dot subtle"></span> subtle.</p>
  <h3>Plugins ($count)</h3>
  <ol>$side_items</ol>
  <h3>On this page</h3>
  <ol>
    <li><a href="#how-to-read">How to read a card</a></li>
    <li><a href="#models">Models used</a></li>
    <li><a href="#verify">How to verify these are real</a></li>
  </ol>
</aside>
<main>
<header class="top">
  <h1>Skill examples — before &amp; after</h1>
  <p class="sub">One real prompt per skill, answered twice by the same model: once with the skill injected, once with a generic stub.
  The judge's verdict comes first; the full transcripts and the original prompt are one click away; every card ends with who answered,
  who graded, who judged, and the commands that check it.</p>
  <div class="stats">
    <span><b>$count</b>example$plural</span>
    <span><b>$n_attested</b>CI-graded &amp; attested</span>
    <span><b>$n_graded</b>CI-graded, unattested</span>
    <span><b>$n_seed</b>seeds (ungraded)</span>
    <span>divergence: $spread</span>
  </div>
</header>

<section class="howto" id="how-to-read">
  <h2>How to read a card</h2>
  <ol>
    <li><strong>Verdict first.</strong> The red block is the judge's own paragraph on how the two transcripts differ, and its one-word grade is the coloured badge. Where the judge shares the subject's model family the card says so; read those as descriptions, not independent grades.</li>
    <li><strong>Then the evidence.</strong> The scenario is the pack designer's one-line intent. The prompt is verbatim and never truncated (expand it). The two transcripts are shown as a preview; <em>Read both transcripts in full</em> opens them, and on narrow screens they stack.</li>
    <li><strong>Then the receipts.</strong> The provenance block names every model by role, links the commit and the GitHub Actions run, and gives the exact commands that verify this snapshot's bytes came from that run.</li>
  </ol>
  <div class="legend">
    <span class="badge pass">graded: pass</span><span class="badge fail">graded: fail</span><span class="badge ungraded">ungraded</span>
    <span>= the pack's rubric grader's call on that side;</span>
    <span class="badge src attested">CI-graded · attested</span><span class="badge src seed">seed · ungraded</span>
    <span>= how the pair was produced;</span>
    <span class="badge warnb">same-family judge</span><span>= the verdict is not independent of the subject.</span>
  </div>
</section>

<section class="disclose" id="models">
  <h2>Models used — by role</h2>
  <p>Three roles, disclosed separately on every card: the <strong>subject</strong> answered the prompt (both sides), the <strong>grader</strong> applied the pack's pass/fail rubric, the <strong>judge</strong> wrote the divergence verdict.
  The rule this repository enforces: <em>a model never grades its own family</em>. Every behavioral pack tests one model and grades with another
  ($packs_n packs: subject $pack_subjects, grader $pack_graders); the cheap eval tier refuses a pack or a graded snapshot where the two share a family, and the capture script refuses to write one.
  Seeds predate that rule, and the table says so instead of hiding it — they are replaced by CI-graded, attested pairs as the refresh workflow reaches each pack.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Produced by</th><th>Subject (answered)</th><th>Grader (pass/fail)</th><th>Judge (divergence verdict)</th></tr></thead>
    <tbody>$model_rows</tbody>
  </table></div>
</section>

$body

<section class="verify-section disclose" id="verify">
  <h2>How to verify these are real model outputs</h2>
  <p>Nothing on this page is typed by hand, and you do not have to take that on trust. The evidence chain for a CI-graded, attested pair:</p>
  <div class="chain">
    <div class="step"><b>The run.</b> A scheduled GitHub Actions workflow (<a href="$repo/blob/main/.github/workflows/refresh-examples.yml"><code>refresh-examples.yml</code></a>) runs each plugin's promptfoo pack against the subject model and grades it with a different model family. The run's log and its <code>promptfoo-results</code> artifact are linked from the card.</div>
    <div class="step"><b>The cut.</b> <a href="$repo/blob/main/evals/paid/capture-example.sh"><code>capture-example.sh</code></a> copies one passing real-skill row and its stub-skill calibration row out of <code>results.json</code>, verbatim, into the snapshot — reading the grader from the pack config and refusing a same-family pair.</div>
    <div class="step"><b>The signature.</b> <a href="https://github.com/actions/attest-build-provenance"><code>actions/attest-build-provenance</code></a> signs the snapshot's SHA-256 with GitHub's Sigstore identity for that exact run. A hand-edited or hand-written file has no valid attestation.</div>
    <div class="step"><b>The review.</b> The run opens a pull request; a maintainer reads the transcripts; merging publishes. The cheap eval tier re-checks, offline, that this page is byte-for-byte what the committed snapshots render to and that every snapshot discloses its models.</div>
  </div>
  <h3>Verify one yourself</h3>
  <pre><code>gh attestation verify docs/examples/data/&lt;plugin&gt;.json \\
  --repo JRichlen/agent-plugins \\
  --signer-workflow JRichlen/agent-plugins/.github/workflows/refresh-examples.yml</code></pre>
  <p>That command proves GitHub-hosted infrastructure produced those exact bytes in a run of that workflow; the run page shows the model calls it made. What it cannot prove is that a model <em>wrote</em> the text rather than the workflow file — so the workflow file is public, pinned by commit in the run, and short enough to read.</p>
  <h3>What a seed can and cannot prove</h3>
  <div class="chain">
    <div class="step weak"><b>No signature.</b> A seed was produced by a Claude Code session outside CI, before this chain existed. Its only provenance is the git commit that introduced it (linked from the card), the SHA-256 of the file, and the disclosure that the judge shares the subject's model family.</div>
    <div class="step weak"><b>Replaced, not dressed up.</b> Seeds are labelled as seeds everywhere they appear. The twelve plugins with a behavioral pack get an attested pair on the next refresh; the rest keep their seed until they have a pack — a plugin with neither has no card at all.</div>
  </div>
</section>

<footer class="site">
  Generated by <code>docs/build-examples.sh</code> from committed snapshots in <code>docs/examples/data/</code> — no timestamps minted here, so the page is reproducible byte for byte.
  Source of truth: the behavioral eval tier. <a href="$repo/blob/main/docs/examples/DESIGN.md">Why the page looks like this</a> · <a href="$repo/blob/main/docs/examples/PLAN.md">Roadmap</a>
</footer>
</main>
</div>
<script>$js</script>
</body>
</html>
''')

body = "\n".join(cards) if cards else '<p class="empty">No example snapshots yet. CI captures them from behavioral eval runs.</p>'
print(TEMPLATE.substitute(
    css=CSS, js=JS, nav=nav("examples", "../"), repo=REPO,
    filters=filters_html, count=count, plural="s" if count != 1 else "",
    side_items="\n".join(side_items),
    n_attested=kinds["attested"], n_graded=kinds["graded"], n_seed=kinds["seed"], spread=esc(spread),
    packs_n=packs_n,
    pack_subjects=esc(", ".join(sorted(pack_subjects)) or "none"),
    pack_graders=esc(", ".join(sorted(pack_graders)) or "none"),
    model_rows="\n".join(model_rows), body=body,
), end="")
PY
}

# Render to a temp file first so a failed render (bad JSON, schema drift) can
# never truncate the committed page, and its failure propagates as exit 1
# instead of being masked by the redirect.
TMP="$(mktemp "${TMPDIR:-/tmp}/examples-page.XXXXXX")" || { echo "examples: mktemp FAILED — cannot render" >&2; exit 1; }
trap 'rm -f "$TMP"' EXIT
if ! render > "$TMP"; then
  echo "examples: render FAILED — $OUT left untouched" >&2
  exit 1
fi
if [ "${1:-}" = "--check" ]; then
  if [ ! -f "$OUT" ]; then echo "examples: index.html missing — run docs/build-examples.sh" >&2; exit 1; fi
  if ! diff -q "$TMP" "$OUT" >/dev/null; then
    echo "examples: index.html is STALE — regenerate: docs/build-examples.sh" >&2
    exit 1
  fi
  echo "examples: index.html in sync"
  exit 0
fi
chmod 644 "$TMP"   # mktemp creates 0600; the published page is 0644
mv "$TMP" "$OUT"
trap - EXIT
echo "wrote $OUT"

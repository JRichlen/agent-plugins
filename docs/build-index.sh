#!/usr/bin/env bash
#
# build-index.sh — generate the GitHub Pages landing page (docs/index.html).
#
# The landing page is the site's hub: what the marketplace is, how to install
# from it, the three ways into the site (evidence, story, deep dives), and a
# catalog of EVERY plugin read from .claude-plugin/marketplace.json — with, per
# plugin, whether it has a before/after example (and how starkly the judge saw
# it diverge), a behavioral eval pack, and a deep-dive page. Reading those from
# the repo instead of hand-writing them is what keeps the hub from going stale
# the way the previous hand-written page did (it listed two of twenty-four).
#
# Deterministic: same inputs in, byte-identical HTML out, so the cheap tier can
# assert the committed index.html is in sync (docs/build-index.sh --check).
#
# Usage:  build-index.sh            # write docs/index.html
#         build-index.sh --check    # exit 1 if index.html is stale
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="$HERE/index.html"

render() {
python3 - "$ROOT" <<'PY'
import glob, html, json, os, re, string, sys
root = sys.argv[1]
sys.dont_write_bytecode = True   # never litter docs/_shared with __pycache__
sys.path.insert(0, os.path.join(root, "docs", "_shared"))
from sitenav import nav, BASE_CSS, REPO

def esc(x):
    return html.escape("" if x is None else str(x))

mp = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
plugins = sorted(mp.get("plugins") or [], key=lambda p: p["name"])

snaps = {}
for f in glob.glob(os.path.join(root, "docs", "examples", "data", "*.json")):
    try:
        s = json.load(open(f))
        m = re.search(r"\[divergence: ([a-z]+)\]", s.get("notice") or "")
        src = str((s.get("provenance") or {}).get("source") or "")
        snaps[s["plugin"]] = {"div": m.group(1) if m else "untagged",
                              "kind": "graded" if src.startswith("promptfoo") else "seed"}
    except Exception:
        pass

def has_pack(name):
    return os.path.isfile(os.path.join(root, "plugins", name, "evals", "promptfoo", "promptfooconfig.yaml"))
def has_deep(name):
    return os.path.isfile(os.path.join(root, "docs", name, "index.html"))

DEEP_BLURB = {
    "redgate": "The Red Gate protocol: rounds of ARM → TRACE → JUDGE with graduated autonomy, a verifier proven able to fail before any work starts, and PATCH / MINOR / MAJOR gates so irreversible decisions always block on a human.",
    "agent-compiler": "Compile deterministic, content-hashed agents from small behavior modules: fuzzy intent becomes a typed AgentQuery, a stdlib-only kernel resolves modules and fails closed on conflicts, and out comes an immutable AgentImage with per-line provenance.",
}

rows = []
for p in plugins:
    name = p["name"]
    ex = snaps.get(name)
    if ex:
        label = ex["div"] if ex["div"] != "untagged" else "example"
        ex_html = f'<a class="tag ex {esc(ex["div"])}" href="examples/#{esc(name)}" title="before/after example — judged divergence: {esc(ex["div"])}; {esc(ex["kind"])}"><span class="dot {esc(ex["div"])}"></span>{esc(label)}</a>'
    else:
        ex_html = '<span class="tag none" title="no before/after example yet — the gallery never fabricates one">no example yet</span>'
    pack_html = ('<span class="tag pack" title="has a behavioral (promptfoo) eval pack: a model is graded on this skill in CI">graded in CI</span>'
                 if has_pack(name) else '<span class="tag none" title="no behavioral pack yet — cheap (offline) tier only">cheap tier only</span>')
    deep_html = f' · <a href="{esc(name)}/">deep dive</a>' if has_deep(name) else ""
    kw = " ".join(p.get("keywords") or [])
    rows.append(f'''
  <li class="plugin" data-q="{esc((name + ' ' + p.get('description','') + ' ' + kw).lower())}">
    <div class="p-head">
      <h3><a href="{REPO}/tree/main/plugins/{esc(name)}">{esc(name)}</a> <span class="ver">v{esc(p.get("version","?"))}</span></h3>
      <div class="tags">{ex_html}{pack_html}</div>
    </div>
    <p>{esc(p.get("description",""))}</p>
    <p class="p-links"><code>/plugin install {esc(name)}@jrichlen</code>{deep_html}</p>
  </li>''')

n_ex = sum(1 for p in plugins if p["name"] in snaps)
n_pack = sum(1 for p in plugins if has_pack(p["name"]))
n_deep = sum(1 for p in plugins if has_deep(p["name"]))
deep_cards = "".join(f'''
  <a class="card deep" href="{esc(n)}/"><span class="lbl">Deep dive</span><h3>{esc(n)}</h3><p>{esc(DEEP_BLURB.get(n, ""))}</p></a>'''
    for n in [p["name"] for p in plugins if has_deep(p["name"])])

CSS = BASE_CSS + """
  .wrap { max-width:1000px; margin:0 auto; padding:2.2rem 1.2rem 5rem; }
  header.hero h1 { font-size:2.2rem; margin:0 0 .4rem; letter-spacing:-.02em; }
  header.hero .sub { color:var(--muted); margin:0 0 1.2rem; max-width:72ch; font-size:1.05rem; }
  .install { display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin:0 0 2rem; }
  @media (max-width:700px) { .install { grid-template-columns:1fr; } }
  .install div { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:.8rem 1rem; }
  .install .lbl { display:block; margin-bottom:.3rem; }
  .install pre { margin:0; }
  h2 { font-size:1.3rem; margin:2rem 0 .7rem; letter-spacing:-.01em; }
  h2 small { font-weight:400; color:var(--muted); font-size:.85rem; margin-left:.5rem; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:1rem; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1.1rem 1.3rem; color:var(--fg); text-decoration:none; display:block; }
  .card:hover { border-color:var(--line-strong); }
  .card h3 { margin:.2rem 0 .4rem; font-size:1.15rem; }
  .card p { margin:0; color:var(--muted); font-size:.92rem; }
  .card .lbl { color:var(--accent); }
  .card.deep .lbl { color:var(--link); }
  .search { width:100%; font:inherit; padding:.5rem .7rem; border:1px solid var(--line-strong); border-radius:8px;
    background:var(--card); color:var(--fg); margin:.2rem 0 1rem; }
  .js-only { display:none; } html.js .js-only { display:block; }
  ol.catalog { list-style:none; padding:0; margin:0; display:grid; gap:.8rem; }
  .plugin { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:.9rem 1.1rem; }
  .plugin.hide { display:none; }
  .p-head { display:flex; align-items:baseline; gap:.8rem; flex-wrap:wrap; }
  .plugin h3 { margin:0; font-size:1.05rem; } .plugin h3 a { color:var(--fg); text-decoration:none; } .plugin h3 a:hover { text-decoration:underline; }
  .ver { color:var(--muted); font-size:.78rem; font-weight:400; margin-left:.3rem; }
  .tags { display:flex; gap:.35rem; flex-wrap:wrap; margin-left:auto; }
  .tag { font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.04em; border-radius:999px; padding:.12rem .55rem;
    text-decoration:none; display:inline-flex; align-items:center; gap:.3rem; border:1px solid transparent; }
  .tag.ex { border-color:currentColor; color:var(--muted); }
  .tag.ex.stark { color:var(--stark); } .tag.ex.strong { color:var(--strong); } .tag.ex.moderate { color:var(--moderate); } .tag.ex.subtle { color:var(--subtle); }
  .tag.pack { background:var(--with-bg); color:var(--with); }
  .tag.none { background:var(--code-bg); color:var(--muted); font-weight:600; text-transform:none; letter-spacing:0; }
  .dot { width:.55rem; height:.55rem; border-radius:50%; display:inline-block; background:var(--line-strong); }
  .dot.stark { background:var(--stark); } .dot.strong { background:var(--strong); } .dot.moderate { background:var(--moderate); } .dot.subtle { background:var(--subtle); }
  .plugin p { margin:.45rem 0 0; color:var(--muted); font-size:.92rem; max-width:90ch; }
  .plugin .p-links { font-size:.85rem; margin-top:.5rem; }
  .checked { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem 1.2rem; margin-top:2rem; color:var(--muted); font-size:.92rem; }
  .checked strong { color:var(--fg); }
  .checked ul { margin:.4rem 0 0; padding-left:1.2rem; }
"""

JS = r"""
document.documentElement.classList.add('js');
(function(){
  var q = document.getElementById('q'), items = Array.prototype.slice.call(document.querySelectorAll('.plugin')), n = document.getElementById('n');
  if (!q) return;
  q.addEventListener('input', function(){
    var v = q.value.trim().toLowerCase(), shown = 0;
    items.forEach(function(li){ var ok = !v || li.dataset.q.indexOf(v) !== -1; li.classList.toggle('hide', !ok); if (ok) shown++; });
    if (n) n.textContent = shown === items.length ? '' : '(' + shown + ' shown)';
  });
})();
"""

TEMPLATE = string.Template('''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-plugins — a cross-harness agent plugin marketplace</title>
<meta name="description" content="$n_plugins plugins for Claude Code and any coding agent that reads SKILL.md and AGENTS.md, each with evals, real before/after examples, and a design record.">
<style>$css</style>
</head>
<body>
$nav
<div class="wrap">

<header class="hero">
  <h1>agent-plugins</h1>
  <p class="sub">A marketplace of $n_plugins plugins for <a href="https://docs.claude.com/en/docs/claude-code">Claude Code</a> that also work with any coding agent
  (Codex, Cursor, Gemini, …) through standard <code>SKILL.md</code> + <code>AGENTS.md</code> entry points. Every plugin is gated by evals;
  $n_ex of them have a published before/after example with the models disclosed; $n_pack are graded by a model in CI on every change.</p>
</header>

<div class="install">
  <div><span class="lbl">Claude Code</span><pre>/plugin marketplace add JRichlen/agent-plugins
/plugin install &lt;name&gt;@jrichlen</pre></div>
  <div><span class="lbl">Any harness, via APM (pin the SHA)</span><pre>apm install JRichlen/agent-plugins/plugins/&lt;name&gt;#&lt;sha&gt;</pre></div>
</div>

<h2>Three ways in</h2>
<div class="cards">
  <a class="card" href="examples/"><span class="lbl">Evidence</span><h3>Before &amp; after examples</h3><p>One real prompt per skill, answered with and without it. Verdict first, transcripts on demand, every model named by role, and a verification path back to the CI run that produced the pair.</p></a>
  <a class="card" href="timeline/"><span class="lbl">Story</span><h3>Design trajectory</h3><p>How this marketplace became what it is, told as the decisions that shaped it: what forced each one, what was rejected, and a receipt you can check. Start here for the why behind everything else.</p></a>
  <a class="card" href="$repo/blob/main/docs/testing.md"><span class="lbl">Reference</span><h3>How every change is checked</h3><p>The full inventory of eval tiers, what each proves and what it structurally cannot, when it fires and what it costs — the doc the cheap tier itself keeps in sync with the workflows.</p></a>
</div>

<h2>Deep dives <small>$n_deep plugins with a long-form page</small></h2>
<div class="cards">$deep_cards
</div>

<h2>All plugins <small><span id="n"></span></small></h2>
<input id="q" class="search js-only" type="search" placeholder="Filter by name, description or keyword" aria-label="Filter plugins">
<ol class="catalog">$rows
</ol>

<div class="checked">
  <strong>This site is generated, and checked.</strong> The landing page, the example gallery and the timeline are each rendered from committed data by a
  script in <code>docs/</code>; the offline eval tier fails any commit whose page drifts from its data, and the Pages workflow re-checks before it deploys.
  <ul>
    <li><a href="$repo/blob/main/docs/build-index.sh">build-index.sh</a> — this page, from <code>marketplace.json</code>, the snapshots and the packs</li>
    <li><a href="$repo/blob/main/docs/build-examples.sh">build-examples.sh</a> — the gallery, from <code>docs/examples/data/</code> (<a href="$repo/blob/main/docs/examples/DESIGN.md">why it looks the way it does</a>)</li>
    <li><a href="$repo/blob/main/docs/timeline/build-timeline.sh">build-timeline.sh</a> — the timeline, from <code>docs/timeline/data/decisions.json</code></li>
  </ul>
</div>

<footer class="site">
  Served from <code>docs/</code> by GitHub Pages · <a href="$repo">source</a> · <a href="$repo/blob/main/AGENTS.md">eval discipline</a> · <a href="$repo/blob/main/docs/red-gate-protocol.md">Red Gate protocol</a> · <a href="$repo/blob/main/docs/red-gate-glossary.md">glossary</a>
</footer>
</div>
<script>$js</script>
</body>
</html>
''')

print(TEMPLATE.substitute(css=CSS, js=JS, nav=nav("home", ""), repo=REPO,
                          n_plugins=len(plugins), n_ex=n_ex, n_pack=n_pack, n_deep=n_deep,
                          deep_cards=deep_cards, rows="".join(rows)), end="")
PY
}

TMP="$(mktemp "${TMPDIR:-/tmp}/index-page.XXXXXX")" || { echo "index: mktemp FAILED — cannot render" >&2; exit 1; }
trap 'rm -f "$TMP"' EXIT
if ! render > "$TMP"; then
  echo "index: render FAILED — $OUT left untouched" >&2
  exit 1
fi
if [ "${1:-}" = "--check" ]; then
  if [ ! -f "$OUT" ]; then echo "index: index.html missing — run docs/build-index.sh" >&2; exit 1; fi
  if ! diff -q "$TMP" "$OUT" >/dev/null; then
    echo "index: docs/index.html is STALE — regenerate: docs/build-index.sh" >&2
    exit 1
  fi
  echo "index: docs/index.html in sync"
  exit 0
fi
chmod 644 "$TMP"
mv "$TMP" "$OUT"
trap - EXIT
echo "wrote $OUT"

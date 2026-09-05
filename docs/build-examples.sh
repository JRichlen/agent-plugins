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
# Deterministic: same snapshots in, byte-identical HTML out (no timestamps
# minted here — provenance timestamps come from the snapshots themselves), so
# the cheap tier can assert the committed index.html is in sync with the data.
#
# Usage:  build-examples.sh            # write docs/examples/index.html
#         build-examples.sh --check    # exit 1 if index.html is stale
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="$HERE/examples/index.html"

render() {
python3 - "$ROOT" <<'PY'
import glob, html, json, os, re, sys
root = sys.argv[1]
data_dir = os.path.join(root, "docs", "examples", "data")
snaps = []
for f in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
    try:
        snaps.append(json.load(open(f)))
    except Exception as e:
        print(f"<!-- skip {f}: {e} -->", file=sys.stderr)

def desc_of(plugin):
    p = os.path.join(root, "plugins", plugin, "skills", plugin, "SKILL.md")
    if not os.path.isfile(p):
        return ""
    txt = open(p).read()
    m = re.search(r'description:\s*>?-?\s*\n?(.*?)(?:\nlicense:|\ncompatibility:|\n---)', txt, re.S)
    if not m:
        return ""
    return " ".join(m.group(1).split())

def render_output(s):
    # Show the model's real response verbatim. Escape HTML, then promote fenced
    # code blocks to <pre><code> so diffs read cleanly; everything else stays as
    # the model wrote it, line breaks preserved. No markdown embellishment — the
    # point is to show exactly what was produced.
    out, i, parts = s, 0, []
    fence = re.compile(r'```(\w*)\n(.*?)```', re.S)
    last = 0
    for m in fence.finditer(out):
        parts.append(("text", out[last:m.start()]))
        parts.append(("code", m.group(2)))
        last = m.end()
    parts.append(("text", out[last:]))
    buf = []
    for kind, seg in parts:
        if kind == "code":
            buf.append('<pre class="code">' + html.escape(seg.rstrip("\n")) + "</pre>")
        else:
            seg = html.escape(seg).strip("\n")
            if seg.strip():
                buf.append('<div class="prose">' + seg.replace("\n", "<br>") + "</div>")
    return "".join(buf)

def grade_badge(g):
    p = g.get("pass")
    if p is True:  return '<span class="badge pass">graded: pass</span>'
    if p is False: return '<span class="badge fail">graded: fail</span>'
    return '<span class="badge ungraded">ungraded seed</span>'

cards = []
for s in snaps:
    plugin = s["plugin"]
    prov = s.get("provenance", {})
    prov_line = " · ".join(filter(None, [
        f'source: {html.escape(str(prov.get("source","?")))}',
        f'model: {html.escape(str(prov.get("model","?")))}',
        f'grader: {html.escape(str(prov.get("grader","?")))}',
        f'commit: {html.escape(str(prov.get("commit","?")))}',
        f'captured: {html.escape(str(prov.get("captured_at","?")))}',
    ]))
    notice = html.escape(s.get("notice","")) if s.get("notice") else ""
    cards.append(f'''
  <section class="card" id="{html.escape(plugin)}">
    <div class="card-head">
      <h2>{html.escape(plugin)}</h2>
      <a class="docs-link" href="https://github.com/JRichlen/agent-plugins/tree/main/plugins/{html.escape(plugin)}">plugin docs →</a>
    </div>
    <p class="skilldesc">{html.escape(desc_of(plugin))}</p>
    <div class="scenario"><span class="lbl">Scenario</span> {html.escape(s.get("scenario",""))}</div>
    <div class="prompt"><span class="lbl">Prompt</span><div class="prose">{html.escape(s.get("prompt","")).replace(chr(10),"<br>")}</div></div>
    <div class="cols">
      <div class="col without">
        <div class="col-head">Without the skill {grade_badge(s.get("without_skill",{}).get("graded",{}))}</div>
        {render_output(s.get("without_skill",{}).get("output",""))}
      </div>
      <div class="col with">
        <div class="col-head">With the skill {grade_badge(s.get("with_skill",{}).get("graded",{}))}</div>
        {render_output(s.get("with_skill",{}).get("output",""))}
      </div>
    </div>
    {f'<p class="notice"><strong>What to notice.</strong> {notice}</p>' if notice else ''}
    <p class="prov">{prov_line}</p>
  </section>''')

count = len(cards)
# judged-divergence spread, computed from the data so it can never drift from the cards
import re as _re, collections as _c
_tags = _c.Counter()
_untagged = 0
for s in snaps:
    m = _re.search(r"\[divergence: ([a-z]+)\]", s.get("notice") or "")
    if m: _tags[m.group(1)] += 1
    else: _untagged += 1
_order = ["stark", "strong", "moderate", "subtle"]
_parts = [f"{_tags[k]} {k}" for k in _order if _tags[k]] + [f"{_tags[k]} {k}" for k in sorted(_tags) if k not in _order]
if _untagged: _parts.append(f"{_untagged} described without a grade")
spread = ", ".join(_parts) if _parts else "none yet"
toc = " · ".join(f'<a href="#{html.escape(s["plugin"])}">{html.escape(s["plugin"])}</a>' for s in snaps) or "—"
body = "\n".join(cards) if cards else '<p class="empty">No example snapshots yet. CI captures them from behavioral eval runs.</p>'

print(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill examples — before &amp; after</title>
<style>
  :root {{
    --bg:#f7f6f3; --fg:#1a1a1a; --muted:#5a5a5a; --card:#ffffff; --line:#e3e1dc;
    --with:#0a7d3f; --with-bg:#eaf6ee; --without:#8a5a00; --without-bg:#f6f0e6;
    --code-bg:#f2f1ee; --link:#0b5cad;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#141414; --fg:#ececec; --muted:#a2a2a2; --card:#1d1d1d; --line:#2f2f2f;
      --with:#4bd07f; --with-bg:#12251a; --without:#e0aa4a; --without-bg:#241d10;
      --code-bg:#0f0f0f; --link:#6db3f2;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
    font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:1060px; margin:0 auto; padding:2.4rem 1.2rem 5rem; }}
  header h1 {{ font-size:1.9rem; margin:0 0 .3rem; letter-spacing:-.02em; }}
  header .sub {{ color:var(--muted); margin:0 0 1.2rem; max-width:70ch; }}
  .intro {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:1rem 1.2rem; margin:1.2rem 0 1.8rem; color:var(--muted); }}
  .intro strong {{ color:var(--fg); }}
  .toc {{ font-size:.9rem; color:var(--muted); margin:.4rem 0 2rem; }}
  .toc a {{ color:var(--link); text-decoration:none; }}
  a {{ color:var(--link); }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:1.3rem 1.4rem 1.1rem; margin:0 0 1.8rem; }}
  .card-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:1rem; }}
  .card h2 {{ margin:0; font-size:1.35rem; }}
  .docs-link {{ font-size:.85rem; text-decoration:none; white-space:nowrap; }}
  .skilldesc {{ color:var(--muted); margin:.4rem 0 1rem; font-size:.92rem; }}
  .lbl {{ display:inline-block; font-size:.7rem; text-transform:uppercase; letter-spacing:.08em;
    color:var(--muted); font-weight:600; margin-right:.5rem; }}
  .scenario {{ margin:.2rem 0 .8rem; }}
  .prompt {{ background:var(--code-bg); border-radius:8px; padding:.7rem .9rem; margin:0 0 1.2rem; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; }}
  @media (max-width:760px) {{ .cols {{ grid-template-columns:1fr; }} }}
  .col {{ border:1px solid var(--line); border-radius:10px; padding:.9rem 1rem; min-width:0; }}
  .col.with {{ border-color:var(--with); background:var(--with-bg); }}
  .col.without {{ border-color:var(--without); background:var(--without-bg); }}
  .col-head {{ font-weight:700; font-size:.9rem; margin-bottom:.6rem;
    display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }}
  .col.with .col-head {{ color:var(--with); }}
  .col.without .col-head {{ color:var(--without); }}
  .badge {{ font-size:.68rem; font-weight:700; padding:.1rem .45rem; border-radius:999px;
    text-transform:uppercase; letter-spacing:.04em; }}
  .badge.pass {{ background:var(--with); color:#fff; }}
  .badge.fail {{ background:#c0392b; color:#fff; }}
  .badge.ungraded {{ background:var(--line); color:var(--muted); }}
  .prose {{ white-space:normal; word-wrap:break-word; }}
  .code {{ background:var(--code-bg); border-radius:7px; padding:.6rem .7rem; overflow-x:auto;
    font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; margin:.5rem 0; }}
  .notice {{ font-size:.9rem; color:var(--muted); border-left:3px solid var(--line);
    padding:.2rem 0 .2rem .8rem; margin:1rem 0 .4rem; }}
  .prov {{ font:11.5px/1.5 ui-monospace,monospace; color:var(--muted);
    border-top:1px dashed var(--line); padding-top:.6rem; margin:.9rem 0 0; word-break:break-word; }}
  .empty {{ color:var(--muted); }}
  footer {{ color:var(--muted); font-size:.85rem; margin-top:2.5rem;
    border-top:1px solid var(--line); padding-top:1rem; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Skill examples — before &amp; after</h1>
  <p class="sub">Real prompt/response pairs showing what each skill changes, run with the
  skill and without it (against a generic stub). {count} example{"s" if count!=1 else ""} —
  judged divergence, in the reader's own word: {spread}.</p>
</header>
<div class="intro">
  <strong>Every pair here is a real, provenanced model run</strong> — captured from the
  behavioral eval tier, never hand-written. The <em>without-skill</em> side is the
  eval's negative control (the same request given a generic assistant stub); the
  <em>with-skill</em> side injects the actual skill. Where a run was graded, the badge
  says pass or fail; ungraded seeds are labelled as such. Judge the divergence yourself.
</div>
<nav class="toc">Jump to: {toc}</nav>
{body}
<footer>
  Generated by <code>docs/build-examples.sh</code> from committed snapshots in
  <code>docs/examples/data/</code>. Source of truth: the behavioral eval tier.
</footer>
</div>
</body>
</html>''')
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

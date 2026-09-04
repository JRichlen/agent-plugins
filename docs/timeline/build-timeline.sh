#!/usr/bin/env bash
#
# build-timeline.sh — generate the design-trajectory decision timeline page.
#
# Reads the curated decision inventory in docs/timeline/data/decisions.json —
# every entry a decision with the problem that forced it, the alternative it
# rejected, and receipts (PR/commit URLs or repo paths) a reader can check —
# and writes a single self-contained, theme-aware static page to
# docs/timeline/index.html. No external assets, no network; GitHub Pages
# serves the file as-is.
#
# Curation is a data edit: flip an entry's "curated" flag (recording a
# cut_reason) and rebuild. Cut entries stay in the data file as inventory.
#
# Deterministic: same data in, byte-identical HTML out, so the cheap tier can
# assert the committed index.html is in sync with the data.
#
# Usage:  build-timeline.sh            # write docs/timeline/index.html
#         build-timeline.sh --check    # exit 1 if index.html is stale
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/index.html"

render() {
python3 - "$ROOT" <<'PY'
import html, json, os, sys
root = sys.argv[1]
data = json.load(open(os.path.join(root, "docs", "timeline", "data", "decisions.json")))

REPO = "https://github.com/JRichlen/agent-plugins"

def esc(s):
    return html.escape(s or "")

def receipt_link(r):
    # Select url only when it is a non-empty string — the same semantics the
    # cheap-tier validator applies — so a null/empty url beside a valid path
    # renders the path link instead of href="".
    url = r.get("url") if isinstance(r.get("url"), str) else ""
    if url.strip():
        href = url.strip()
    else:
        p = r["path"]
        kind = "tree" if os.path.isdir(os.path.join(root, p)) else "blob"
        href = f"{REPO}/{kind}/main/{p}"
    return f'<a href="{esc(href)}">{esc(r["label"])}</a>'

eras = data["eras"]
by_era = {e["id"]: [] for e in eras}
shown = 0
total = len(data["decisions"])
for d in data["decisions"]:
    if d.get("curated"):
        by_era[d["era"]].append(d)
        shown += 1

# Spelled out so the heading reads as prose; falls back to the digit if the
# era count ever outgrows the list.
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve"]
era_count = WORDS[len(eras)] if len(eras) < len(WORDS) else str(len(eras))

skim = "\n".join(
    f'  <li><a href="#{esc(e["id"])}"><strong>{esc(e["title"])}</strong></a>'
    f' <span class="win">({esc(e["window"])})</span> — {esc(e["lesson"])}</li>'
    for e in eras)

sections = []
for e in eras:
    cards = []
    for d in by_era[e["id"]]:
        rej = (f'<div class="block"><span class="lbl rej">Rejected</span>'
               f'<p>{esc(d["rejected"])}</p></div>') if d.get("rejected") else ""
        receipts = " · ".join(receipt_link(r) for r in d["receipts"])
        cards.append(f'''
    <article class="entry" id="{esc(d["id"])}">
      <div class="dot" aria-hidden="true"></div>
      <div class="card">
        <div class="meta"><span class="date">{esc(d["date"])}</span></div>
        <h3>{esc(d["title"])}</h3>
        <div class="block"><span class="lbl forced">Forced by</span><p>{esc(d["forced_by"])}</p></div>
        <div class="block"><span class="lbl dec">Decided</span><p>{esc(d["decided"])}</p></div>
        {rej}
        <p class="receipts"><span class="lbl rcpt">Receipts</span> {receipts}</p>
      </div>
    </article>''')
    sections.append(f'''
  <section class="era" id="{esc(e["id"])}">
    <header class="era-head">
      <h2>{esc(e["title"])}</h2>
      <p class="window">{esc(e["window"])}</p>
      <p class="lesson">{esc(e["lesson"])}</p>
    </header>
    <div class="rail">{"".join(cards)}</div>
  </section>''')

print(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design trajectory — a decision timeline</title>
<style>
  :root {{
    --bg:#f7f6f3; --fg:#1a1a1a; --muted:#5a5a5a; --card:#ffffff; --line:#e3e1dc;
    --accent:#6d3f9e; --accent-soft:#f0e9f7; --link:#0b5cad;
    --forced:#8a5a00; --dec:#0a7d3f; --rej:#a03030;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#141414; --fg:#ececec; --muted:#a2a2a2; --card:#1d1d1d; --line:#2f2f2f;
      --accent:#b493dd; --accent-soft:#241b30; --link:#6db3f2;
      --forced:#e0aa4a; --dec:#4bd07f; --rej:#e07a7a;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
    font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:880px; margin:0 auto; padding:2.4rem 1.2rem 5rem; }}
  a {{ color:var(--link); }}
  .crumb {{ font-size:.85rem; margin:0 0 1.4rem; }}
  .crumb a {{ text-decoration:none; }}
  header.top h1 {{ font-size:1.9rem; margin:0 0 .3rem; letter-spacing:-.02em; }}
  header.top .sub {{ color:var(--muted); margin:0 0 1.2rem; max-width:72ch; }}
  .thesis {{ background:var(--accent-soft); border:1px solid var(--accent);
    border-radius:12px; padding:1rem 1.2rem; margin:1.2rem 0 1.6rem; }}
  .thesis strong {{ color:var(--accent); }}
  .skim {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:1rem 1.2rem .6rem; margin:0 0 2.2rem; }}
  .skim h2 {{ font-size:1rem; margin:0 0 .5rem; text-transform:uppercase;
    letter-spacing:.06em; color:var(--muted); }}
  .skim ul {{ margin:0; padding:0 0 .4rem 1.1rem; }}
  .skim li {{ margin:0 0 .55rem; }}
  .skim .win {{ color:var(--muted); font-size:.88rem; }}
  .skim a {{ text-decoration:none; }}
  .era {{ margin:0 0 2.6rem; }}
  .era-head h2 {{ font-size:1.45rem; margin:0; color:var(--accent); }}
  .era-head .window {{ color:var(--muted); font-size:.88rem; margin:.1rem 0 .4rem; }}
  .era-head .lesson {{ margin:0 0 1.1rem; max-width:74ch; }}
  .rail {{ border-left:2px solid var(--line); margin-left:.4rem; padding-left:1.4rem; }}
  .entry {{ position:relative; margin:0 0 1.4rem; }}
  .dot {{ position:absolute; left:calc(-1.4rem - 7px); top:1.35rem; width:12px; height:12px;
    border-radius:50%; background:var(--accent); border:2px solid var(--bg); }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:1rem 1.2rem .9rem; }}
  .meta {{ font:12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--muted); }}
  .card h3 {{ margin:.35rem 0 .7rem; font-size:1.12rem; }}
  .block {{ margin:0 0 .7rem; }}
  .block p {{ margin:.15rem 0 0; }}
  .lbl {{ display:inline-block; font-size:.68rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.08em; padding:.05rem .45rem; border-radius:999px; }}
  .lbl.forced {{ color:var(--forced); border:1px solid var(--forced); }}
  .lbl.dec {{ color:var(--dec); border:1px solid var(--dec); }}
  .lbl.rej {{ color:var(--rej); border:1px solid var(--rej); }}
  .lbl.rcpt {{ color:var(--muted); border:1px solid var(--line); }}
  .receipts {{ font-size:.85rem; color:var(--muted); border-top:1px dashed var(--line);
    padding-top:.6rem; margin:.8rem 0 .1rem; }}
  .receipts a {{ text-decoration:none; }}
  footer {{ color:var(--muted); font-size:.85rem; margin-top:2.5rem;
    border-top:1px solid var(--line); padding-top:1rem; }}
</style>
</head>
<body>
<div class="wrap">
<p class="crumb"><a href="../">← agent-plugins docs</a></p>
<header class="top">
  <h1>Design trajectory — a decision timeline</h1>
  <p class="sub">How this marketplace became what it is, told as the decisions that shaped it:
  what forced each one, what was rejected, and a receipt you can check. {shown} decisions shown
  of {total} recorded — the rest stay in the
  <a href="{REPO}/blob/main/docs/timeline/data/decisions.json">data file</a> with their cut reasons.</p>
</header>
<div class="thesis">
  <strong>The through-line.</strong> {esc(data["thesis"])}
</div>
<nav class="skim">
  <h2>The story in {era_count} lines</h2>
  <ul>
{skim}
  </ul>
</nav>
{"".join(sections)}
<footer>
  Generated by <code>docs/timeline/build-timeline.sh</code> from
  <code>docs/timeline/data/decisions.json</code> — curated by hand, never from git logs.
  Every claim above links to its primary source; if a receipt doesn't support its entry,
  that's a bug — <a href="{REPO}/issues">file it</a>.
</footer>
</div>
</body>
</html>''')
PY
}

# Render to a temp file first so a failed render (bad JSON, schema drift) can
# never truncate the committed page, and its failure propagates as exit 1
# instead of being masked by the redirect.
TMP="$(mktemp "${TMPDIR:-/tmp}/timeline-page.XXXXXX")" || { echo "timeline: mktemp FAILED — cannot render" >&2; exit 1; }
trap 'rm -f "$TMP"' EXIT
if ! render > "$TMP"; then
  echo "timeline: render FAILED — $OUT left untouched" >&2
  exit 1
fi
if [ "${1:-}" = "--check" ]; then
  if [ ! -f "$OUT" ]; then echo "timeline: index.html missing — run docs/timeline/build-timeline.sh" >&2; exit 1; fi
  if ! diff -q "$TMP" "$OUT" >/dev/null; then
    echo "timeline: index.html is STALE — regenerate: docs/timeline/build-timeline.sh" >&2
    exit 1
  fi
  echo "timeline: index.html in sync"
  exit 0
fi
chmod 644 "$TMP"   # mktemp creates 0600; the published page is 0644
mv "$TMP" "$OUT"
trap - EXIT
echo "wrote $OUT"

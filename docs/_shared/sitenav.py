"""Shared site chrome for the GitHub Pages site under docs/.

Every generated page (docs/build-examples.sh, docs/build-index.sh,
docs/timeline/build-timeline.sh) imports this so the top navigation, the
colour tokens and the base typography are identical across the site; the two
hand-written deep-dive pages (docs/redgate/, docs/agent-compiler/) paste the
same markup in by hand. No timestamps, no randomness: the output is a pure
function of its inputs so every page stays byte-reproducible.
"""
import html

REPO = "https://github.com/JRichlen/agent-plugins"

# (id, label, path relative to docs/)
PAGES = [
    ("home",     "Home",           ""),
    ("examples", "Examples",       "examples/"),
    ("timeline", "Timeline",       "timeline/"),
    ("redgate",  "redgate",        "redgate/"),
    ("compiler", "agent-compiler", "agent-compiler/"),
]


def nav(current, prefix):
    """The site-wide top bar. `current` is a PAGES id; `prefix` is the relative
    path from the page back to docs/ ('' at the root, '../' one level down)."""
    items = []
    for pid, label, path in PAGES:
        cls = ' class="cur" aria-current="page"' if pid == current else ""
        items.append(f'<a href="{html.escape(prefix + path)}"{cls}>{html.escape(label)}</a>')
    items.append(f'<a href="{REPO}" class="ext" rel="noopener">GitHub ↗</a>')
    return ('<nav class="site" aria-label="Site">'
            f'<a class="brand" href="{html.escape(prefix)}">agent-plugins</a>'
            '<div class="site-links">' + "".join(items) + '</div></nav>')


# Colour tokens + base typography, shared by every page. Light palette on
# :root; dark palette under prefers-color-scheme so the site follows the
# reader's OS setting the way the existing pages already do.
BASE_CSS = """
  :root {
    --bg:#f7f6f3; --fg:#1a1a1a; --muted:#5f5e5a; --card:#ffffff; --line:#e3e1dc; --line-strong:#cfccc4;
    --code-bg:#f1efea; --link:#0b5cad; --accent:#b02a43; --accent-soft:#f6e3e7;
    --with:#0a7d3f; --with-bg:#ecf7f0; --without:#8a5a00; --without-bg:#f8f1e4;
    --pass:#0a7d3f; --fail:#c0392b; --warn:#9a6700; --warn-bg:#fff4d6;
    --stark:#0a7d3f; --strong:#1f7a5c; --moderate:#a86b00; --subtle:#6b6b6b;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:#141414; --fg:#ececec; --muted:#a3a29e; --card:#1d1d1d; --line:#2f2f2f; --line-strong:#454545;
      --code-bg:#0f0f0f; --link:#6db3f2; --accent:#e4677e; --accent-soft:#3a1a22;
      --with:#4bd07f; --with-bg:#12251a; --without:#e0aa4a; --without-bg:#241d10;
      --pass:#4bd07f; --fail:#ff7b6b; --warn:#e8c66b; --warn-bg:#2d2610;
      --stark:#4bd07f; --strong:#5fcfa6; --moderate:#e0aa4a; --subtle:#9a9a9a;
    }
  }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { margin:0; background:var(--bg); color:var(--fg);
    font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  a { color:var(--link); }
  code, kbd { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.9em;
    background:var(--code-bg); border-radius:4px; padding:.1em .35em; }
  pre { background:var(--code-bg); border-radius:8px; padding:.7rem .9rem; overflow-x:auto;
    font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  pre code { background:none; padding:0; font-size:inherit; }
  nav.site { position:sticky; top:0; z-index:20; background:var(--card); border-bottom:1px solid var(--line);
    display:flex; align-items:center; gap:1rem; padding:.55rem 1.2rem; font-size:.9rem; }
  nav.site .brand { font-weight:800; letter-spacing:-.01em; color:var(--fg); text-decoration:none; }
  nav.site .site-links { display:flex; gap:.15rem; flex-wrap:wrap; margin-left:auto; }
  nav.site .site-links a { color:var(--muted); text-decoration:none; padding:.25rem .6rem; border-radius:6px; }
  nav.site .site-links a:hover { background:var(--code-bg); color:var(--fg); }
  nav.site .site-links a.cur { color:var(--fg); font-weight:700; background:var(--code-bg); }
  nav.site .site-links a.ext { color:var(--link); }
  .lbl { display:inline-block; font-size:.7rem; text-transform:uppercase; letter-spacing:.08em;
    color:var(--muted); font-weight:700; margin-right:.5rem; }
  .badge { display:inline-block; font-size:.68rem; font-weight:700; padding:.12rem .5rem; border-radius:999px;
    text-transform:uppercase; letter-spacing:.04em; border:1px solid transparent; white-space:nowrap; }
  footer.site { color:var(--muted); font-size:.85rem; margin-top:3rem; border-top:1px solid var(--line); padding-top:1rem; }
"""

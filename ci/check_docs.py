#!/usr/bin/env python3
"""Check the guided documentation path's local links and generated site links."""
from html.parser import HTMLParser
import html
import unicodedata
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ["README.md", "CONTRIBUTING.md", "docs/README.md", "docs/getting-started.md",
          "ci/README.md", "release/README.md", "evals/README.md", "evals/paid/README.md",
          "docs/examples/README.md"]


def prose(text):
    """Remove fenced code; support backtick and tilde fences independently."""
    result, fence = [], None
    for line in text.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            result.append(line)
    return "\n".join(result)


def markdown_links(text):
    """Links used by these guides, including titled/angle and reference links.

    This is a bounded source check, not a claim of complete CommonMark parity.
    """
    text = prose(text)
    definitions = {}
    for match in re.finditer(r'^ {0,3}\[([^]\n]+)\]:\s*<?([^\s>]+)>?', text, re.M):
        definitions[' '.join(match[1].lower().split())] = match[2]
    body = re.sub(r'^ {0,3}\[[^]\n]+\]:.*$', '', text, flags=re.M)
    targets = re.findall(r'!?\[[^]\n]*\]\(\s*<?([^\s>]+?)>?(?:\s+["\'][^\n]*?["\'])?\s*\)', body)
    for match in re.finditer(r'(?<!!)\[([^]\n]+)\](?:\[([^]\n]*)\])?(?!\()', body):
        key = ' '.join((match[2] or match[1]).lower().split())
        if key in definitions:
            targets.append(definitions[key])
    parser = Links()
    parser.feed(body)
    return targets + parser.links


def anchors(path):
    text = prose(path.read_text(encoding="utf-8"))
    parser = Links()
    parser.feed(text)
    found = set(parser.ids)
    if path.suffix == '.html':
        return found
    counts = {}
    for title in re.findall(r"^ {0,3}#{1,6}\s+(.+?)\s*$", text, re.M):
        title = re.sub(r'\s+#+\s*$', '', title)
        title = re.sub(r'!?\[([^]]+)\]\([^)]*\)', r'\1', title)
        title = re.sub(r'<[^>]+>', '', title)
        title = html.unescape(title).lower()
        title = ''.join(c for c in title if c in '-_ ' or unicodedata.category(c)[0] in 'LN')
        base = title.replace(' ', '-')
        count = counts.get(base, 0)
        candidate = base if count == 0 else base + '-' + str(count)
        while candidate in found:
            count += 1
            candidate = base + '-' + str(count)
        counts[base] = count + 1
        found.add(candidate)
    return found


def check_link(root, source, target):
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or target.startswith("mailto:"):
        return None
    destination = (source.parent / unquote(parts.path)).resolve() if parts.path else source
    if not destination.is_relative_to(root.resolve()):
        return "link escapes repository: " + target
    if not destination.exists():
        return "missing target: " + target
    if destination.is_dir():
        destination = destination / "index.html" if (destination / "index.html").exists() else destination / "README.md"
    if parts.fragment and destination.is_file() and destination.suffix in (".md", ".html"):
        if unquote(parts.fragment) not in anchors(destination):
            return "missing anchor: " + target
    return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for key, value in attrs if (key == "id" or (tag == "a" and key == "name")) and value)
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)


def check(root=ROOT):
    sources = [root / p for p in GUIDES] + sorted((root / "docs/guides").glob("*.md"))
    sources += [root / p for p in ("docs/index.html", "docs/examples/index.html", "docs/agent-compiler/index.html")]
    failures = []
    for source in sources:
        text = source.read_text(encoding="utf-8")
        if source.suffix == ".html":
            parser = Links()
            parser.feed(text)
            targets = parser.links
        else:
            targets = markdown_links(text)
        for target in targets:
            error = check_link(root, source, target)
            if error:
                failures.append(source.relative_to(root).as_posix() + ": " + error)
        if source.suffix == ".html" and ("â€”" in text or "Â·" in text):
            failures.append(source.relative_to(root).as_posix() + ": mojibake")
    return failures


if __name__ == "__main__":
    failures = check()
    print("\n".join(failures) if failures else "Guided documentation links and anchors: PASS")
    sys.exit(bool(failures))

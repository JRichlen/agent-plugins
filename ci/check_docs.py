#!/usr/bin/env python3
"""Check the guided documentation path's local links and generated site links."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ["README.md", "CONTRIBUTING.md", "docs/README.md", "docs/getting-started.md",
          "ci/README.md", "release/README.md", "evals/README.md", "evals/paid/README.md",
          "docs/examples/README.md"]


def anchors(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        return set(re.findall(r'\bid=["\']([^"\']+)', text))
    found = set()
    for title in re.findall(r"^#{1,6} (.+)$", re.sub(r"```.*?```", "", text, flags=re.S), re.M):
        title = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        found.add(title)
    found.update(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', text))
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

    def handle_starttag(self, tag, attrs):
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
            text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
            targets = re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text)
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

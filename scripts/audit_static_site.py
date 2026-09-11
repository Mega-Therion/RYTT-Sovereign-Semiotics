#!/usr/bin/env python3
"""Small dependency-free audit for public static routes."""
from __future__ import annotations

from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
ROUTES = [ROOT / "index.html", ROOT / "web" / "playground.html", ROOT / "web" / "codex.html"]

class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = False
        self.title = False
        self.main = False
        self.skip = False
        self.unnamed_buttons = 0
        self._title_depth = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html" and attrs.get("lang"): self.lang = True
        if tag == "title": self._title_depth = 1
        if self._title_depth and tag != "title": self._title_depth += 1
        if tag == "main": self.main = True
        if tag == "a" and attrs.get("class", "").find("skip") >= 0: self.skip = True
        if tag == "button" and not (attrs.get("id") or attrs.get("aria-label") or attrs.get("title")): self.unnamed_buttons += 1
    def handle_endtag(self, tag):
        if tag == "title" and self._title_depth: self.title = True; self._title_depth = 0

def audit(path: Path):
    parser = Audit(); parser.feed(path.read_text(encoding="utf-8"))
    errors=[]
    for name, ok in [("lang", parser.lang), ("title", parser.title), ("main", parser.main), ("skip-link", parser.skip)]:
        if not ok: errors.append(name)
    if parser.unnamed_buttons: errors.append(f"unnamed-buttons={parser.unnamed_buttons}")
    return errors

failures = {str(path.relative_to(ROOT)): audit(path) for path in ROUTES if audit(path)}
if failures:
    for path, errors in failures.items(): print(path + ": " + ", ".join(errors))
    raise SystemExit(1)
print(f"static accessibility audit OK for {len(ROUTES)} routes")

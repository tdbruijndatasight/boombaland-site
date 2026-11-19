#!/usr/bin/env python3
"""Writes sitemap.xml: every committed HTML page that may be indexed (no `noindex`), with its canonical URL and a
truthful lastmod (the date of the page's last commit; today for a page changed in the working tree).

Usage: python3 -I tools/sitemap.py          (run after tools/build.py and tools/build_wiki.py; tools/qa.sh checks it)
"""
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.boombaland.com"


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True).stdout


def pages():
    """(url, file) for every indexable page: tracked or new *.html files, minus noindex pages."""
    files = set(git("ls-files", "*.html").split()) | set(git("ls-files", "--others", "--exclude-standard", "*.html").split())
    out = []
    for f in sorted(files):
        if f.startswith(("assets/", "local/", "footage/")):
            continue
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', src):
            continue
        m = re.search(r'<link rel="canonical" href="([^"]+)"', src)
        url = m.group(1) if m else SITE + "/" + (f[:-len("index.html")] if f.endswith("index.html") else f)
        out.append((url, f))
    return sorted(out, key=lambda p: (p[0] != SITE + "/", p[0]))


def lastmod(f):
    if git("status", "--porcelain", "--", f).strip():
        return datetime.date.today().isoformat()
    d = git("log", "-1", "--format=%cs", "--", f).strip()
    return d or datetime.date.today().isoformat()


def build():
    rows = "\n".join(f"  <url><loc>{u}</loc><lastmod>{lastmod(f)}</lastmod></url>" for u, f in pages())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{rows}\n</urlset>\n")


if __name__ == "__main__":
    xml = build()
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(f"sitemap.xml: {xml.count('<url>')} URLs", file=sys.stderr)

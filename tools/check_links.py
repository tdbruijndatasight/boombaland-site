#!/usr/bin/env python3
"""Tiny link checker for the local server. Usage: python3 -I tools/check_links.py [http://127.0.0.1:8766]
Crawls every page reachable from / (plus the known roots), fetches every local href/src/srcset/url() target and reports
anything that is not 200. External links are listed, not fetched. Also checks that a few HTML basics hold on each page
(one <h1>, lang, title, meta description, alt on every <img>, unique ids, no duplicate attributes)."""
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766").rstrip("/")
ROOTS = ["/", "/press/", "/support/", "/privacy/", "/terms/", "/404.html", "/app-ads.txt", "/robots.txt",
         "/sitemap.xml", "/CNAME", "/favicon.ico", "/apple-touch-icon.png", "/assets/site.css", "/assets/site.js"]


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.problems, self.h1, self.title, self.desc, self.lang = [], [], [], 0, False, False, False

    def handle_starttag(self, tag, attrs):
        names = [k for k, _ in attrs]
        if len(names) != len(set(names)):
            self.problems.append(f"duplicate attribute on <{tag}>: {names}")
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = True
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.desc = True
        if tag == "img" and "alt" not in a:
            self.problems.append(f"<img> without alt: {a.get('src')}")
        if "id" in a:
            self.ids.append(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.refs.append(a[k])
        if a.get("srcset"):
            self.refs += [part.strip().split(" ")[0] for part in a["srcset"].split(",") if part.strip()]


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""


def main():
    seen, bad, external, queue, pages = set(), [], set(), list(ROOTS), 0
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        status, ctype, body = get(BASE + path)
        if status != 200:
            bad.append(f"{status} {path}")
            continue
        if "text/css" in ctype:
            for u in re.findall(r'url\("?([^")]+)"?\)', body.decode()):
                queue.append(urllib.parse.urljoin(path, u))
        if "text/html" not in ctype:
            continue
        pages += 1
        p = P()
        p.feed(body.decode("utf-8"))
        checks = [(p.lang, "no lang"), (p.title, "no title"), (p.desc, "no meta description"), (p.h1 == 1, f"{p.h1} h1")]
        for ok, msg in checks:
            if not ok:
                bad.append(f"{path}: {msg}")
        dup = {i for i in p.ids if p.ids.count(i) > 1}
        if dup:
            bad.append(f"{path}: duplicate ids {dup}")
        bad += [f"{path}: {x}" for x in p.problems]
        for ref in p.refs:
            if ref.startswith(("mailto:", "data:", "tel:")) or ref == "#":
                continue
            u = urllib.parse.urlparse(urllib.parse.urljoin(path, ref))
            if u.scheme in ("http", "https") and u.netloc and not (BASE.endswith(u.netloc)):
                external.add(ref)
                continue
            if u.fragment and not u.path.strip():
                continue
            if u.fragment:
                # same-page or cross-page anchor: the target page must hold that id
                s, _, b = get(BASE + u.path)
                if f'id="{u.fragment}"' not in b.decode("utf-8", "ignore"):
                    bad.append(f"{path}: missing anchor {ref}")
            queue.append(u.path)
    print(f"checked {len(seen)} local URLs ({pages} HTML pages)")
    print(f"{len(external)} external links (not fetched):")
    for e in sorted(external):
        print("  ", e)
    if bad:
        print(f"{len(bad)} PROBLEMS:")
        for b in bad:
            print("  ", b)
        sys.exit(1)
    print("no problems")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Site QA checks that run locally and in CI without any account (AUDIT.md section 9.3). Report-only: it changes nothing.

Usage:  python3 -I tools/qa.py [check ...] [--online]
Checks (all by default): sitemap meta noindex jsonld availability names
  --online   also fetch the store pages when STORE_LINKS are filled (HTTP 200 + right ids; Apple lookup API)
Env:     BOMBWORLD=/path/to/BombWorld  REF=<git ref>  (names: compare with the game; without the repo, only the
         retired names and the snapshot in tools/game_names.json are checked)
Exit status 1 when any check fails.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sitemap  # noqa: E402

ROOT = sitemap.ROOT
SITE = sitemap.SITE
APPLE_ID = "6821619320"
PLAY_ID = "com.datasight.boomworld"
IOS_URL = re.compile(r"^https://apps\.apple\.com/(?:[a-z]{2}/)?app/(?:[^/]+/)?id" + APPLE_ID + r"(?:\?.*)?$")
PLAY_URL = re.compile(r"^https://play\.google\.com/store/apps/details\?id=" + re.escape(PLAY_ID) + r"(?:&.*)?$")
# Words that claim the game can be played or downloaded now. Not allowed while STORE_LINKS are empty.
LIVE_CLAIMS = re.compile(r"\b(out now|play (?:it )?(?:for )?free now|download (?:it )?now|available now|free download|"
                         r"get it on google play|download on the app store|play now)\b", re.I)
# The old trailer poster has "Play free now" baked into the image: allowed only once the stores are live.
LIVE_ONLY_IMAGES = ["/assets/img/trailer-640.", "/assets/img/trailer-1280."]
FORBIDDEN_LD = {"aggregateRating", "review", "reviews", "ratingValue", "reviewCount", "ratingCount", "interactionStatistic",
                "userInteractionCount", "award", "awards", "downloadCount"}

FAILS, WARNS = [], []


def fail(check, msg):
    FAILS.append(f"[{check}] {msg}")


def warn(check, msg):
    WARNS.append(f"[{check}] {msg}")


def read(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


def all_html():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "*.html"], capture_output=True, text=True).stdout.split()
    return [f for f in out if not f.startswith(("assets/", "local/", "footage/"))]


class Text(HTMLParser):
    """The text a visitor (or a crawler) reads: body text, alt/title/aria-label, meta descriptions and JSON-LD values.
    Not ids, classes, file names or URLs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.ld, self._skip, self._ld = [], [], 0, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self._ld = a.get("type") == "application/ld+json"
            self._skip += 0 if self._ld else 1
        elif tag == "style":
            self._skip += 1
        for k in ("alt", "title", "aria-label"):
            if a.get(k):
                self.parts.append(a[k])
        if tag == "meta" and (a.get("name") in ("description", "twitter:title", "twitter:description")
                              or a.get("property") in ("og:title", "og:description", "og:image:alt")):
            self.parts.append(a.get("content") or "")

    def handle_endtag(self, tag):
        if tag == "script":
            if self._ld:
                self._ld = False
            else:
                self._skip -= 1
        elif tag == "style":
            self._skip -= 1

    def handle_data(self, data):
        if self._ld:
            self.ld.append(data)
        elif not self._skip:
            self.parts.append(data)


def parse(rel):
    p = Text()
    p.feed(read(rel))
    return p


def ld_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from ld_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from ld_strings(v)
    elif isinstance(obj, str) and not obj.startswith("http"):
        yield obj


def site_texts():
    """{file: visible text} for every HTML page, plus llms.txt and the wiki search index."""
    out = {}
    for f in all_html():
        p = parse(f)
        ld = []
        for block in p.ld:
            try:
                ld += list(ld_strings(json.loads(block)))
            except ValueError:
                pass
        out[f] = re.sub(r"\s+", " ", " ".join(p.parts + ld))
    for extra in ("llms.txt", "wiki/search.json"):
        if os.path.exists(os.path.join(ROOT, extra)):
            out[extra] = read(extra)
    return out


def store_links():
    js = read("assets/site.js")
    m = re.search(r"var STORE_LINKS = \{(.*?)\};", js, re.S)
    if not m:
        fail("availability", "STORE_LINKS not found in assets/site.js")
        return {"ios": "", "android": ""}
    return {k: (re.search(k + r':\s*"([^"]*)"', m.group(1)) or [None, ""])[1] for k in ("ios", "android")}


# ---------------------------------------------------------------------------------------------------------- checks
def check_sitemap():
    try:
        tree = ET.parse(os.path.join(ROOT, "sitemap.xml"))
    except ET.ParseError as e:
        return fail("sitemap", f"sitemap.xml is not valid XML: {e}")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = {}
    for u in tree.getroot().findall("s:url", ns):
        loc = (u.findtext("s:loc", "", ns) or "").strip()
        lm = (u.findtext("s:lastmod", "", ns) or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm):
            fail("sitemap", f"{loc}: lastmod {lm!r} is not a date")
        if loc in locs:
            fail("sitemap", f"listed twice: {loc}")
        locs[loc] = lm
    want = {u: f for u, f in sitemap.pages()}
    for u in sorted(set(want) - set(locs)):
        fail("sitemap", f"indexable page missing from sitemap.xml: {u} (run tools/sitemap.py)")
    for u in sorted(set(locs) - set(want)):
        fail("sitemap", f"listed but not an indexable page: {u}")
    robots = read("robots.txt")
    if f"Sitemap: {SITE}/sitemap.xml" not in robots:
        fail("sitemap", "robots.txt does not point to the sitemap")
    if re.search(r"(?im)^\s*Disallow:\s*/\s*$", robots):
        warn("sitemap", "robots.txt has a 'Disallow: /' line: check it only hits the intended bots")
    print(f"sitemap: {len(locs)} URLs listed, {len(want)} indexable pages")


def check_meta():
    n = 0
    for url, f in sitemap.pages():
        s = read(f)
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        d = re.search(r'<meta name="description" content="([^"]*)"', s)
        c = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        og = re.search(r'<meta property="og:image" content="([^"]+)"', s)
        import html as h
        tl = len(h.unescape(t.group(1))) if t else 0
        dl = len(h.unescape(d.group(1))) if d else 0
        if not 10 <= tl <= 70:
            fail("meta", f"{f}: title length {tl} (want 10-70)")
        if not 50 <= dl <= 160:
            fail("meta", f"{f}: description length {dl} (want 50-160)")
        if not c or c.group(1) != url:
            fail("meta", f"{f}: canonical {c.group(1) if c else None} != {url}")
        if not og:
            fail("meta", f"{f}: no og:image")
        elif og.group(1).startswith(SITE + "/") and not os.path.exists(os.path.join(ROOT, og.group(1)[len(SITE) + 1:])):
            fail("meta", f"{f}: og:image file missing: {og.group(1)}")
        n += 1
    print(f"meta: {n} pages")


def check_noindex():
    for f in all_html():
        if re.search(r'<meta name="robots" content="[^"]*noindex', read(f)) and f != "404.html":
            fail("noindex", f"unexpected noindex on {f}")
    if not re.search(r'noindex', read("404.html")):
        fail("noindex", "404.html should be noindex")
    print("noindex: checked")


def check_jsonld():
    live = all(store_links().values())
    blocks, game = 0, None
    for f in all_html():
        for b in parse(f).ld:
            blocks += 1
            try:
                data = json.loads(b)
            except ValueError as e:
                fail("jsonld", f"{f}: JSON-LD does not parse: {e}")
                continue
            stack = [data]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    bad = FORBIDDEN_LD & set(o)
                    if bad:
                        fail("jsonld", f"{f}: forbidden field(s) {sorted(bad)} (no ratings, reviews, downloads or awards)")
                    if o.get("@type") == "VideoGame":
                        game = (f, o)
                    stack += list(o.values())
                elif isinstance(o, list):
                    stack += o
    if not game:
        fail("jsonld", "no VideoGame block (expected on the home page)")
    else:
        f, g = game
        if g.get("name") != "Boombaland":
            fail("jsonld", f"{f}: VideoGame.name is {g.get('name')!r}")
        if "bomberman" in json.dumps(g).lower():
            fail("jsonld", f"{f}: the trademark 'Bomberman' must not be used")
        if "offers" in g and not live:
            fail("jsonld", f"{f}: VideoGame has offers while STORE_LINKS are empty")
        if live and "offers" not in g:
            fail("jsonld", f"{f}: stores are live but VideoGame has no offers")
        for o in g.get("offers", []):
            if str(o.get("price")) != "0":
                fail("jsonld", f"{f}: offer price {o.get('price')!r}, expected 0")
    print(f"jsonld: {blocks} blocks")


def check_availability(online=False):
    links = store_links()
    live = all(links.values())
    if any(links.values()) and not live:
        warn("availability", "only one store link is filled; the site stays in 'coming soon' mode until both are")
    texts = site_texts()
    if not live:
        for f, t in texts.items():
            for m in LIVE_CLAIMS.finditer(t):
                fail("availability", f"{f}: says {m.group(0)!r} while STORE_LINKS are empty")
        for f in all_html():
            s = read(f)
            for img in LIVE_ONLY_IMAGES:
                if img in s:
                    fail("availability", f"{f}: uses the 'Play free now' poster {img}* while the stores are not live")
            if re.search(r'<a[^>]*data-store[^>]*href="https?://', s):
                fail("availability", f"{f}: a store button links somewhere while STORE_LINKS are empty")
    else:
        if not IOS_URL.match(links["ios"]):
            fail("availability", f"ios link {links['ios']!r} is not the App Store page of id{APPLE_ID}")
        if not PLAY_URL.match(links["android"]):
            fail("availability", f"android link {links['android']!r} is not the Play page of {PLAY_ID}")
        if "Coming soon" in texts.get("index.html", ""):
            fail("availability", "index.html still says 'Coming soon' while the stores are live (rebuild)")
        if online:
            for k, u in links.items():
                try:
                    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (site QA)"})
                    with urllib.request.urlopen(req, timeout=20) as r:
                        if r.status != 200:
                            fail("availability", f"{k}: {u} -> HTTP {r.status}")
                except urllib.error.HTTPError as e:
                    fail("availability", f"{k}: {u} -> HTTP {e.code}")
                except OSError as e:
                    fail("availability", f"{k}: {u} -> {e}")
            try:
                with urllib.request.urlopen(f"https://itunes.apple.com/lookup?id={APPLE_ID}", timeout=20) as r:
                    if json.load(r).get("resultCount", 0) < 1:
                        fail("availability", f"Apple lookup id={APPLE_ID}: resultCount 0 (not public yet)")
            except OSError as e:
                fail("availability", f"Apple lookup failed: {e}")
    print(f"availability: stores {'LIVE' if live else 'not live (coming soon)'}")


def game_values(cfg):
    """The current values of the configured keys at REF in the game repo, or None when the repo is not available."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    bw = os.environ.get("BOMBWORLD", "/Users/tomdebruijn/Dev/BombWorld")
    ref = os.environ.get("REF", cfg["snapshot"]["ref"])
    r = subprocess.run(["git", "-C", bw, "show", f"{ref}:{cfg['game_strings']}"], capture_output=True)
    if r.returncode != 0:
        return None, ref
    src = r.stdout.decode("utf-8")
    out = {}
    for k in set(cfg["required"]) | set(cfg["retired"]):
        m = re.search(r'\["' + re.escape(k) + r'"\]\s*=\s*"((?:[^"\\]|\\.)*)"', src)
        out[k] = m.group(1).replace('\\"', '"') if m else None
    return out, ref


def check_names():
    cfg = json.load(open(os.path.join(ROOT, "tools", "game_names.json"), encoding="utf-8"))
    snap = cfg["snapshot"]["values"]
    game, ref = game_values(cfg)
    if game is None:
        warn("names", f"game repo / {ref} not available: checking the snapshot in tools/game_names.json only")
        current = dict(snap)
    else:
        current = game
        for k, v in game.items():
            if v is None:
                fail("names", f"{k} not found in the game at {ref} (key renamed? update tools/game_names.json)")
            elif snap.get(k) != v:
                fail("names", f"the game renamed {k}: {snap.get(k)!r} -> {v!r} at {ref}. Rebuild the site, add "
                              f"{snap.get(k)!r} to retired, update the snapshot in tools/game_names.json")
    texts = site_texts()
    joined = "\n".join(texts.values())
    for k in cfg["required"]:
        v = current.get(k)
        if v and not re.search(r"\b" + re.escape(v) + r"\b", joined):
            fail("names", f"current name {v!r} ({k}) appears nowhere on the site")
    for k, olds in cfg["retired"].items():
        for old in olds:
            if current.get(k) and old.lower() == current[k].lower():
                continue
            pat = re.compile(r"\b" + re.escape(old) + r"s?\b", re.I)
            for f, t in texts.items():
                for m in pat.finditer(t):
                    ctx = t[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                    fail("names", f"{f}: retired name {m.group(0)!r} (now {current.get(k)!r}): ...{ctx}...")
    if re.search(r"\bbomberman\b", joined, re.I):
        fail("names", "the trademark 'Bomberman' appears in the site text")
    print(f"names: {len(cfg['required'])} current names, {sum(len(v) for v in cfg['retired'].values())} retired, "
          f"source {'game ' + ref if game is not None else 'snapshot'}")


CHECKS = {"sitemap": check_sitemap, "meta": check_meta, "noindex": check_noindex, "jsonld": check_jsonld,
          "availability": None, "names": check_names}


def main(argv):
    online = "--online" in argv
    want = [a for a in argv if not a.startswith("--")] or list(CHECKS)
    for c in want:
        if c == "availability":
            check_availability(online)
        elif c in CHECKS:
            CHECKS[c]()
        else:
            raise SystemExit(f"unknown check {c}; choose from {', '.join(CHECKS)}")
    for w in WARNS:
        print("WARN", w)
    for f in FAILS:
        print("FAIL", f)
    print(f"qa: {len(FAILS)} failure(s), {len(WARNS)} warning(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

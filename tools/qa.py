#!/usr/bin/env python3
"""Site QA checks that run locally and in CI without any account (AUDIT.md section 9.3). Report-only: it changes nothing.

Usage:  python3 -I tools/qa.py [check ...] [--online]
Checks (all by default): sitemap meta noindex jsonld availability names getlink
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
# Claims that one particular store has the game. Not allowed while that store's link is empty (partial launch).
_CLAIM = r"(?:out(?: now)?|available(?: now)?|free download|download(?: it)?(?: now)?|get it|play(?: it)? (?:for )?free(?: now)?)"
STORE_CLAIMS = {
    "ios": re.compile(r"\b(" + _CLAIM + r" (?:on|in|from) the App Store|download on the app store)\b", re.I),
    "android": re.compile(r"\b(" + _CLAIM + r" (?:on|in|from) (?:the App Store and )?Google Play|get it on google play)\b", re.I),
}
# The old trailer poster has "Play free now" baked into the image: allowed only once the stores are live.
LIVE_ONLY_IMAGES = ["/assets/img/trailer-640.", "/assets/img/trailer-1280."]
FORBIDDEN_LD = {"aggregateRating", "review", "reviews", "ratingValue", "reviewCount", "ratingCount", "interactionStatistic",
                "userInteractionCount", "award", "awards", "downloadCount"}

FAILS, WARNS = [], []


def urlopen(req, timeout=20):
    """urllib with a CA bundle that also works on a python.org macOS Python (no certs installed): the system bundle."""
    import ssl
    ctx = ssl.create_default_context()
    for ca in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(ca):
            ctx.load_verify_locations(ca)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


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


NOINDEX_OK = {"404.html", "get/index.html"}  # /get/ is the social-bio redirect page: reachable, never indexed


def check_noindex():
    for f in all_html():
        if re.search(r'<meta name="robots" content="[^"]*noindex', read(f)) and f not in NOINDEX_OK:
            fail("noindex", f"unexpected noindex on {f}")
    if not re.search(r'noindex', read("404.html")):
        fail("noindex", "404.html should be noindex")
    print("noindex: checked")


def check_jsonld():
    links = store_links()
    live_urls = [u for u in (links["ios"], links["android"]) if u]
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
        if "offers" in g and not live_urls:
            fail("jsonld", f"{f}: VideoGame has offers while STORE_LINKS are empty")
        if live_urls and "offers" not in g:
            fail("jsonld", f"{f}: a store is live but VideoGame has no offers")
        if live_urls and sorted(o.get("url", "") for o in g.get("offers", [])) != sorted(live_urls):
            fail("jsonld", f"{f}: VideoGame offers do not list exactly the live store(s) {live_urls}")
        if sorted(g.get("sameAs", [])) != sorted(live_urls):
            fail("jsonld", f"{f}: VideoGame sameAs {g.get('sameAs', [])} != the live store(s) {live_urls}")
        for o in g.get("offers", []):
            if str(o.get("price")) != "0":
                fail("jsonld", f"{f}: offer price {o.get('price')!r}, expected 0")
    print(f"jsonld: {blocks} blocks")


def check_availability(online=False):
    links = store_links()
    live = all(links.values())
    partial = any(links.values()) and not live
    texts = site_texts()
    if partial:
        # One store live (e.g. Google Play first): live claims are fine for that store only, and only its button links.
        for k in ("ios", "android"):
            if links[k]:
                continue
            for f, t in texts.items():
                for m in STORE_CLAIMS[k].finditer(t):
                    fail("availability", f"{f}: says {m.group(0)!r} while the {k} link is empty")
            for f in all_html():
                if re.search(r'<a[^>]*data-store="' + k + r'"[^>]*href="https?://', read(f)):
                    fail("availability", f"{f}: the {k} store button links somewhere while its link is empty")
        for f in all_html():
            for img in LIVE_ONLY_IMAGES:
                if img in read(f):
                    fail("availability", f"{f}: uses the 'Play free now' poster {img}* before both stores are live")
    if not any(links.values()):
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
    if any(links.values()):
        if links["ios"] and not IOS_URL.match(links["ios"]):
            fail("availability", f"ios link {links['ios']!r} is not the App Store page of id{APPLE_ID}")
        if links["android"] and not PLAY_URL.match(links["android"]):
            fail("availability", f"android link {links['android']!r} is not the Play page of {PLAY_ID}")
        if live and "Coming soon" in texts.get("index.html", ""):
            fail("availability", "index.html still says 'Coming soon' while the stores are live (rebuild)")
        if online:
            for k, u in links.items():
                if not u:
                    continue
                try:
                    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (site QA)"})
                    with urlopen(req) as r:
                        if r.status != 200:
                            fail("availability", f"{k}: {u} -> HTTP {r.status}")
                except urllib.error.HTTPError as e:
                    fail("availability", f"{k}: {u} -> HTTP {e.code}")
                except OSError as e:
                    fail("availability", f"{k}: {u} -> {e}")
            if links["ios"]:
                try:
                    with urlopen(f"https://itunes.apple.com/lookup?id={APPLE_ID}") as r:
                        if json.load(r).get("resultCount", 0) < 1:
                            fail("availability", f"Apple lookup id={APPLE_ID}: resultCount 0 (not public yet)")
                except OSError as e:
                    fail("availability", f"Apple lookup failed: {e}")
    state = ("LIVE" if live else "PARTIAL (" + ", ".join(f"{k} {'live' if u else 'coming soon'}" for k, u in links.items()) + ")"
             if partial else "not live (coming soon)")
    print(f"availability: stores {state}")


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


# ---------------------------------------------------------------------------------------------------------- /get/
GET_FILE = "get/index.html"
GET_URL = SITE + "/get/"
SOURCE_RE = re.compile(r"[a-z0-9_-]{1,24}")  # the ?s= whitelist; tools/get_redirect.js must use the same one


def get_source(search):
    """Python mirror of source() in tools/get_redirect.js: the first s= value if it passes the whitelist, else ''."""
    m = re.search(r"[?&]s=([^&#]*)", search or "")
    return m.group(1) if m and SOURCE_RE.fullmatch(m.group(1)) else ""


def get_store_url(store, s, ios, play, pt=""):
    """Python mirror of storeUrl() in tools/get_redirect.js."""
    import urllib.parse
    if store == "ios":
        return ios + (f"?ct={s}" + (f"&pt={pt}&mt=8" if pt else "") if s else "")
    return play + ("&referrer=" + urllib.parse.quote(f"utm_source={s}&utm_medium=social&utm_campaign=bio", safe="") if s else "")


GET_UAS = {  # (userAgent, navigator.platform, maxTouchPoints) -> where the page must send it
    "iphone": (("Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.1 Mobile/15E148 Safari/604.1"), "iPhone", 5, "ios"),
    "iphone-instagram": (("Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Mobile/22B83 Instagram 356.0.0.0 (iPhone15,2; iOS 18_1; en_US)"), "iPhone", 5, "ios"),
    "ipad": ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148", "iPad", 5, "ios"),
    "ipados-desktop": (("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                        "Version/18.1 Safari/605.1.15"), "MacIntel", 5, "ios"),
    "android": (("Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
                 "Mobile Safari/537.36"), "Linux armv8l", 5, "android"),
    "android-tiktok": (("Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Version/4.0 Chrome/130.0 Mobile Safari/537.36 trill_370 musical_ly_2023"), "Linux aarch64", 5, "android"),
    "mac": (("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/18.1 Safari/605.1.15"), "MacIntel", 0, ""),
    "windows": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36", "Win32", 0, ""),
    "linux": ("Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0", "Linux x86_64", 0, ""),
    "empty": ("", "", 0, ""),
}
# (search, expected source): the sanitiser's unit test. Anything outside a-z 0-9 - _ (max 24) is dropped, not cleaned.
GET_SOURCES = [("", ""), ("?s=tiktok", "tiktok"), ("?s=ig_bio-2", "ig_bio-2"), ("?s=" + "a" * 24, "a" * 24),
               ("?s=" + "a" * 25, ""), ("?s=TikTok", ""), ("?s=", ""), ("?s=a%20b", ""), ("?s=a+b", ""), ("?s=a b", ""),
               ("?s=%3Cscript%3E", ""), ("?s=<script>", ""), ("?s=javascript:alert(1)", ""), ("?s=x.y", ""),
               ("?s=https://evil.example", ""), ("?s=yt&s=fb", "yt"), ("?a=1&s=yt", "yt"), ("?s=yt#top", "yt"),
               ("?xs=yt", ""), ("?s=%2F", ""), (r"?s=\u0061", ""), ("?s=tik\ntok", ""), ("?s=café", "")]
_NODE_HARNESS = r"""
const vm = require("vm"); let inp = "";
process.stdin.on("data", d => inp += d).on("end", () => {
  const {code, cases} = JSON.parse(inp); const out = [];
  for (const c of cases) {
    const nav = [], hrefs = {ios: null, android: null};
    const links = ["ios", "android"].map(k => ({getAttribute: a => a === "data-get" ? k : null,
                                                 set href(v) { hrefs[k] = v; }, get href() { return hrefs[k]; }}));
    const loc = {search: c.search, replace: u => nav.push(u), assign: u => nav.push("ASSIGN " + u)};
    Object.defineProperty(loc, "href", {set: u => nav.push("HREF " + u), get: () => ""});
    const win = {location: loc, navigator: {userAgent: c.ua, platform: c.platform, maxTouchPoints: c.touch},
                 document: {querySelectorAll: () => links, cookie: ""}};
    win.open = u => nav.push("OPEN " + u);
    vm.runInNewContext(code, {window: win, location: loc, navigator: win.navigator, document: win.document});
    out.push({nav, hrefs, cookie: win.document.cookie});
  }
  process.stdout.write(JSON.stringify(out));
});
"""


class _Res(HTMLParser):
    """Every resource a page would fetch by itself (not <a> links), plus its inline scripts and meta tags."""
    LOAD = {"img": ("src", "srcset"), "script": ("src",), "source": ("src", "srcset"), "iframe": ("src",), "video": ("src", "poster"),
            "audio": ("src",), "embed": ("src",), "object": ("data",), "track": ("src",), "image": ("href",), "use": ("href",),
            "input": ("src",), "frame": ("src",)}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls, self.scripts, self.meta, self.links, self._in = [], [], {}, [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in self.LOAD.get(tag, ()):
            if a.get(k):
                self.urls += [u.strip().split(" ")[0] for u in a[k].split(",")] if k == "srcset" else [a[k]]
        if tag == "link":
            self.links.append(a)
            if a.get("rel") != "canonical":
                self.urls.append(a.get("href", ""))
        if a.get("style") and "url(" in a["style"]:
            self.urls.append(a["style"])
        if tag == "meta":
            self.meta[a.get("name") or a.get("property")] = a.get("content", "")
        self._in = tag == "script" and not a.get("src") and a.get("type") in (None, "text/javascript")
        if self._in:
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._in = False

    def handle_data(self, data):
        if self._in:
            self.scripts[-1] += data


def check_getlink():
    if not os.path.exists(os.path.join(ROOT, GET_FILE)):
        return fail("getlink", f"{GET_FILE} is missing (python3 -I tools/build.py)")
    src = read(GET_FILE)
    links = store_links()
    ios, play = links["ios"], links["android"]
    if not (IOS_URL.match(ios) and PLAY_URL.match(play)):
        return fail("getlink", f"STORE_LINKS are not both live store URLs: {links}")
    for u in (ios, play):
        if f'href="{u}"' not in src:
            fail("getlink", f"{GET_FILE}: no badge links to {u}")
    p = _Res()
    p.feed(src)
    for u in p.urls:
        if re.match(r"\s*(https?:)?//", u) or re.search(r"url\(\s*['\"]?(https?:)?//", u):
            fail("getlink", f"{GET_FILE}: loads an external resource {u!r} (no third-party request before a click)")
    if "/assets/site.js" in src:
        fail("getlink", f"{GET_FILE}: must not load site.js (it would rewrite the tagged badge links)")
    if not re.search(r'<meta name="robots" content="[^"]*noindex', src):
        fail("getlink", f"{GET_FILE}: not noindex")
    canon = [l.get("href") for l in p.links if l.get("rel") == "canonical"]
    if canon != [GET_URL]:
        fail("getlink", f"{GET_FILE}: canonical {canon} != [{GET_URL}]")
    for k in ("og:title", "og:description", "og:image", "og:url", "twitter:card"):
        if not p.meta.get(k):
            fail("getlink", f"{GET_FILE}: no {k}")
    if GET_URL in read("sitemap.xml") or "/get/" in read("sitemap.xml"):
        fail("getlink", "sitemap.xml lists /get/ (it is noindex)")
    if '<svg class="qr"' not in src:
        fail("getlink", f"{GET_FILE}: no inline QR code")
    code = "\n".join(s for s in p.scripts if "boombalandGet" in s)
    if not code:
        return fail("getlink", f"{GET_FILE}: the redirect script is missing")
    for u in set(re.findall(r"https?://[^\"'\s)]+", code)):
        if u not in (ios, play):
            fail("getlink", f"redirect script names a URL other than the two stores: {u}")
    if "/^[a-z0-9_-]{1,24}$/" not in code:
        fail("getlink", "redirect script does not use the s whitelist /^[a-z0-9_-]{1,24}$/")
    for bad in ("document.cookie", "localStorage", "sessionStorage", "indexedDB", "fetch(", "XMLHttpRequest", "sendBeacon",
                "import(", ".assign(", "location.href", "location =", "window.open", "eval(", "innerHTML", "document.write"):
        if bad in code:
            fail("getlink", f"redirect script uses {bad!r}")
    pt = (re.search(r'var PT = "([^"]*)"', code) or [None, None])[1]
    if pt is None:
        return fail("getlink", "redirect script: no PT line")
    # the sanitiser's unit test (python mirror; node then checks the shipped script against the mirror)
    for search, want in GET_SOURCES:
        if get_source(search) != want:
            fail("getlink", f"sanitiser mirror: {search!r} -> {get_source(search)!r}, expected {want!r}")
    want_tt = {"ios": ios + "?ct=tiktok" + (f"&pt={pt}&mt=8" if pt else ""),
               "android": play + "&referrer=utm_source%3Dtiktok%26utm_medium%3Dsocial%26utm_campaign%3Dbio"}
    for k, w in want_tt.items():
        if get_store_url(k, "tiktok", ios, play, pt) != w:
            fail("getlink", f"URL builder mirror: {k} tiktok -> {get_store_url(k, 'tiktok', ios, play, pt)}, expected {w}")
    import random
    import shutil
    rnd = random.Random(1127)
    alphabet = "abcxyz019-_ABZ%&#=?+./:<>\"' é\n"
    searches = [s for s, _ in GET_SOURCES] + ["?s=" + "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 30)))
                                              for _ in range(150)]
    cases = [{"search": se, "ua": ua, "platform": pl, "touch": t, "want": w, "name": n}
             for n, (ua, pl, t, w) in GET_UAS.items() for se in searches]
    node = shutil.which("node")
    if not node:
        warn("getlink", "node not found: the shipped redirect script was not run; only the python mirror was tested")
        return print(f"getlink: {GET_FILE} static checks + {len(GET_SOURCES)} sanitiser cases (mirror only)")
    r = subprocess.run([node, "-e", _NODE_HARNESS], input=json.dumps({"code": code, "cases": cases}),
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return fail("getlink", f"node harness failed: {r.stderr.strip()[:300]}")
    bad = 0
    for c, o in zip(cases, json.loads(r.stdout)):
        s = get_source(c["search"])
        want_nav = [get_store_url(c["want"], s, ios, play, pt)] if c["want"] else []
        want_hrefs = {k: get_store_url(k, s, ios, play, pt) for k in ("ios", "android")}
        problems = []
        if o["nav"] != want_nav:
            problems.append(f"navigated {o['nav']} expected {want_nav}")
        if o["hrefs"] != want_hrefs:
            problems.append(f"badges {o['hrefs']} expected {want_hrefs}")
        for u in o["nav"] + list(o["hrefs"].values()):
            if not isinstance(u, str):
                problems.append(f"no URL set: {u!r}")
                continue
            if not ((u == ios or u.startswith(ios + "?ct=")) and IOS_URL.match(u)
                    or (u == play or u.startswith(play + "&referrer=")) and PLAY_URL.match(u)):
                problems.append(f"not a store URL: {u!r}")
        if o["cookie"]:
            problems.append("set a cookie")
        if problems:
            bad += 1
            if bad <= 5:
                fail("getlink", f"{c['name']} {c['search']!r}: " + "; ".join(problems))
    if bad > 5:
        fail("getlink", f"... {bad} redirect cases failed in all")
    print(f"getlink: {GET_FILE} static checks, {len(GET_SOURCES)} sanitiser cases, {len(cases)} redirect cases in node "
          f"({len(GET_UAS)} user agents), provider token {'set' if pt else 'not set (ct only)'}")


CHECKS = {"sitemap": check_sitemap, "meta": check_meta, "noindex": check_noindex, "jsonld": check_jsonld,
          "availability": None, "names": check_names, "getlink": check_getlink}


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

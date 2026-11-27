#!/usr/bin/env python3
"""Writes the site's HTML pages. The site itself has no build step: the pages are committed as plain HTML and served as-is.
This script only exists so the shared header, footer and <head> stay identical on every page. Edit the templates here,
run `python3 -I tools/build.py`, commit the result.

The legal pages (privacy, terms, support) are ported from the old site (repo tdbruijndatasight/boomworld-legal, HEAD 1802774
plus the approved D-33.449 patch). Pass the path of that patched copy as LEGAL_SRC. Their wording is kept verbatim except:
  - the contact address info.tomdebruijn@gmail.com -> support@boombaland.com (the new official mailbox), everywhere;
  - links: ../ relative paths -> site-root paths, and the old github.io URLs -> https://www.boombaland.com/... .
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BW = os.environ.get("BOMBWORLD", "/Users/tomdebruijn/Dev/BombWorld")
# The game branch the site's facts and names are read from. Point it at the branch that is (or will be) in the stores.
REF = os.environ.get("REF", "origin/coordinator/candidate-j-1126")
_STRINGS = None


def game_strings():
    """Every player-facing English string of the game, read from MenuStringsEn.cs at REF (cached)."""
    global _STRINGS
    if _STRINGS is None:
        import subprocess
        src = subprocess.run(["git", "-C", BW, "show", f"{REF}:Assets/_Project/Code/Menu/Services/MenuStringsEn.cs"],
                             capture_output=True, check=True).stdout.decode("utf-8")
        lit = r'"(?:[^"\\]|\\.)*"'
        out = {}
        for m in re.finditer(r'\["([^"]+)"\]\s*=\s*((?:' + lit + r'\s*\+?\s*)+)[,\n]', src):
            v = "".join(p[1:-1] for p in re.findall(lit, m.group(2)))
            v = re.sub(r"\\u([0-9a-fA-F]{4})", lambda u: chr(int(u.group(1), 16)), v)
            out[m.group(1)] = v.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        _STRINGS = out
    return _STRINGS


def text(key):
    s = game_strings()
    if key not in s:
        raise SystemExit(f"build.py: string {key} not found in MenuStringsEn.cs at {REF}")
    return s[key]


def name(key):
    """A player-visible name from the game's Codex (menu.codex.<key>), e.g. name("thorn_guard") -> "Grimdorn"."""
    return text("menu.codex." + key)


def skill_bullets():
    """The home page's six skill bullets, in the game's own words: each skill's name (menu.heroes.skill_<hero>) and the
    Heroes screen's description (menu.heroes.skill_<hero>_text), read from MenuStringsEn.cs on the game's branch."""
    out = []
    for h in ["blom", "gusto", "frosta", "zappy", "ember", "banshee"]:
        out.append(f"<li><strong>{html.escape(text('menu.heroes.skill_' + h))}</strong>: "
                   f"{html.escape(text('menu.heroes.skill_' + h + '_text'))}</li>")
    return "\n".join(out)


SITE = "https://www.boombaland.com"
OLD_MAIL = "info.tomdebruijn@gmail.com"
MAIL = "support@boombaland.com"
OLD_BASE = "https://tdbruijndatasight.github.io/boomworld-legal/"
LEGAL_SRC = os.environ.get("LEGAL_SRC", "")

NAV = [("/", "Home"), ("/wiki/", "Wiki"), ("/development/", "Development"), ("/press/", "Press"), ("/redeem/", "Redeem"), ("/support/", "Support"),
       ("/privacy/", "Privacy"), ("/terms/", "Terms")]


def nav(current, cls="nav"):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return f'<ul class="{cls}">' + "".join(items) + "</ul>"


def ld_script(items):
    """JSON-LD blocks. Facts only: never aggregateRating, review, download counts or awards (tools/qa checks this)."""
    if not items:
        return ""
    out = []
    for it in items:
        j = json.dumps(it, ensure_ascii=False, indent=1).replace("</", "<\\/")
        out.append(f'\n<script type="application/ld+json">\n{j}\n</script>')
    return "".join(out)


def head(title, description, path, og_image="/assets/img/og-image-1200x630.jpg", noindex=False, jsonld=None):
    url = SITE + path
    t = html.escape(title)
    d = html.escape(description)
    robots = '\n<meta name="robots" content="noindex">' if noindex else ""
    canonical = "" if noindex else f'\n<link rel="canonical" href="{url}">'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">{robots}{canonical}
<meta name="theme-color" content="#4a2c16">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/assets/img/icon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/assets/img/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/LilitaOne-Regular.ttf" as="font" type="font/ttf" crossorigin>
<link rel="preload" href="/assets/fonts/Fredoka-SemiBold.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
<script>document.documentElement.classList.add("js")</script>
<meta property="og:type" content="website">
<meta property="og:site_name" content="Boombaland">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Boombaland logo over a castle on a floating island">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{SITE}{og_image}">{ld_script(jsonld)}
</head>
"""


def topbar(current):
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
<div class="wrap">
<a class="brand" href="/"><img src="/assets/img/icon-48.png" srcset="/assets/img/icon-48.png 1x, /assets/img/icon-192.png 4x" width="40" height="40" alt=""><span>Boombaland</span></a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav"><img src="/assets/img/menu-96.png" width="48" height="48" alt=""><span class="sr-only">Menu</span></button>
<nav class="site-nav" id="site-nav" aria-label="Main">{nav(current)}</nav>
</div>
</header>
"""


FOOTER = f"""<footer class="footer">
<div class="wrap">
<nav aria-label="Footer">{nav(None)}</nav>
<p>Boombaland is free to play. It offers optional in-app purchases. Ads only play when you choose to watch one for a reward.</p>
<p><a href="/development/">How Boombaland is made</a>: by a one-person studio working with AI tools, with every change reviewed and approved.</p>
<p>Follow Boombaland on <a href="https://www.youtube.com/@BoombalandGame" rel="noopener">YouTube</a>, <a href="https://www.instagram.com/boombaland.game/" rel="noopener">Instagram</a> and <a href="https://www.tiktok.com/@boombaland" rel="noopener">TikTok</a>.</p>
<p class="legal-id">Boombaland is made by DataSight (Tom de Bruijn), Tulameenpad 10, 1461 HN Zuidoostbeemster, the Netherlands.
KvK 93353413. Contact: <a href="mailto:{MAIL}">{MAIL}</a></p>
</div>
</footer>
"""


def page(path, body, title, description, current=None, script=False, noindex=False, extra_script=None, jsonld=None):
    s = '<script src="/assets/nav.js" defer></script>\n'
    s += '<script src="/assets/site.js" defer></script>\n' if script else ""
    if extra_script:
        s += f'<script src="{extra_script}" defer></script>\n'
    out = head(title, description, path, noindex=noindex, jsonld=jsonld) + topbar(current) + body + FOOTER + s + "</body>\n</html>\n"
    dest = os.path.join(ROOT, path.strip("/"), "index.html") if path.endswith("/") else os.path.join(ROOT, path.strip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", os.path.relpath(dest, ROOT))


def pic(name, widths, sizes, alt, fallback_w, w, h, ext="jpg", cls="", lazy=True):
    """<picture>: AVIF at every width, then a JPEG/PNG fallback at one width."""
    av = ", ".join(f"/assets/img/{name}-{x}.avif {x}w" for x in widths)
    fb = ", ".join(f"/assets/img/{name}-{x}.{ext} {x}w" for x in widths if ext == "jpg" or x <= 480)
    loading = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    c = f' class="{cls}"' if cls else ""
    return (f'<picture><source type="image/avif" srcset="{av}" sizes="{sizes}">'
            f'<img{c} src="/assets/img/{name}-{fallback_w}.{ext}" srcset="{fb}" sizes="{sizes}" width="{w}" height="{h}" alt="{html.escape(alt)}"{loading}></picture>')


# Gameplay clips (tools/make_clips.sh writes assets/clips/<name>.mp4/.webm/-poster.jpg). A clip whose files are missing is
# simply left out. They play muted and looped, only while on screen, and never under prefers-reduced-motion (site.js).
CLIP_CAPTIONS = {
    "boss": f"{name('thorn_guard')} arrives",
    "bosses": "A boss fight",
    "heroes": "A hero's skill in action",
    "powerups": "Blasts, chains and power-ups",
    "levels": "A level in play",
    "castle": "A castle push-block puzzle",
    "basics": "Drop a bomb, run, BOOM",
}


# The story goal, in the PO's words (round 3). Spoiler-free: no throne hall, no epilogue. Used on home, development, wiki.
GOAL = f"Your goal: defeat {name('thorn_guard')} and free Boombaland from his thorns."

# The home page's clips, in order (FOOTAGE_NEEDS.md shots 1-4). Missing ones are skipped.
HOME_CLIPS = ["basics", "heroes", "castle", "bosses"]


def tracked(path):
    """True when the file is committed (or staged) in the site repo: local, unpublished renders are left out."""
    import subprocess
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "--error-unmatch", os.path.relpath(path, ROOT)], capture_output=True)
    return r.returncode == 0


def clip_html(name, caption=None):
    base = os.path.join(ROOT, "assets", "clips", name)
    if not all(os.path.exists(base + ext) and tracked(base + ext) for ext in (".mp4", ".webm", "-poster.jpg")):
        return ""
    cap = html.escape(caption or CLIP_CAPTIONS.get(name, ""))
    u = f"/assets/clips/{name}"
    return (f'<figure class="clip"><video class="clip-video" muted loop playsinline preload="none" width="1280" height="720" '
            f'poster="{u}-poster.jpg" aria-label="Gameplay clip: {cap}" data-clip>'
            f'<source src="{u}.webm" type="video/webm"><source src="{u}.mp4" type="video/mp4"></video>'
            f'<figcaption>{cap}</figcaption></figure>')


APPLE_ID = "6821619320"
PLAY_ID = "com.datasight.boomworld"


def store_links():
    """The store URLs, read from the one config spot: STORE_LINKS in assets/site.js (filled by tools/go_live.py)."""
    js = open(os.path.join(ROOT, "assets", "site.js"), encoding="utf-8").read()
    m = re.search(r"var STORE_LINKS = \{(.*?)\};", js, re.S)
    out = {}
    for k in ("ios", "android"):
        mm = re.search(k + r':\s*"([^"]*)"', m.group(1))
        out[k] = mm.group(1) if mm else ""
    return out


STORES = ("ios", "android")
STORE_NAMES = {"ios": "the App Store", "android": "Google Play"}
STORE_PLATFORMS = {"ios": "iPhone and iPad", "android": "Android"}


def live_stores():
    """The stores whose link is filled in STORE_LINKS, in a fixed order (ios, android)."""
    links = store_links()
    return [k for k in STORES if links[k]]


def stores_live():
    """Both stores live (the full launch)."""
    return len(live_stores()) == len(STORES)


def partial_live():
    """One store live, the other still coming (e.g. Google Play first). Returns (live_key, coming_key) or None."""
    live = live_stores()
    if len(live) != 1:
        return None
    return live[0], next(k for k in STORES if k not in live)


def partial_status(sep=" and "):
    """'out now on Google Play and coming soon to the App Store' for a partial launch (lower case, no full stop)."""
    on, soon = partial_live()
    return f"out now on {STORE_NAMES[on]}{sep}coming soon to {STORE_NAMES[soon]}"


def cap(s):
    return s[:1].upper() + s[1:]


BADGES = {  # official artwork, downloaded unchanged from Apple / Google on launch day (IMAGE_NEEDS.md #10)
    "ios": ("/assets/badges/app-store-badge.svg", "Download on the App Store", 120, 40),
    "android": ("/assets/badges/google-play-badge.png", "Get it on Google Play", 135, 40),
}


def store_buttons():
    """Not live: a status plank per store that is NOT a link (nothing to tap). Live: the official badge (or, if the badge
    file is missing, the green kit button) linking to the verified store page."""
    links = store_links()
    out = []
    for key, label in (("ios", "App Store"), ("android", "Google Play")):
        url = links[key]
        if not url:
            out.append(f'<span class="btn btn--soon" data-store="{key}"><span class="stack">'
                       f'<span>{label}</span><small data-store-note>Coming soon</small></span></span>')
            continue
        src, alt, w, h = BADGES[key]
        if os.path.exists(os.path.join(ROOT, src.lstrip("/"))):
            out.append(f'<a class="store-badge" data-store="{key}" href="{html.escape(url)}" rel="noopener">'
                       f'<img src="{src}" alt="{alt}" width="{w * 4}" height="{h * 4}"></a>')
        else:
            out.append(f'<a class="btn" data-store="{key}" href="{html.escape(url)}" rel="noopener"><span class="stack">'
                       f'<span>{label}</span><small data-store-note>Free download</small></span></a>')
    return '<div class="stores">\n' + "\n".join(out) + "\n</div>"


SHOTS = [  # the store images v8 (PO approved 20 Nov 2026): captions are the frames' own banners, alt says what is on screen.
    # No painted Grimdorn (PO 20 Nov 2026): he appears only as he is in the game (frames 3 and 8).
    ("shot1", "The six heroes", "Blom, Gusto, Frosta, Zappy, Ember and Banshee together under the Boombaland logo"),
    ("shot2", "Drop. Run. BOOM! Outsmart every enemy", "Blom holds up a lit bomb; on the board he has run clear while his blast hits an enemy and breaks crates"),
    ("shot3", f"Fight epic bosses: beat {name('thorn_guard')} and his tricks", f"{name('thorn_guard')} up close on his arena, as he looks in the game"),
    ("shot4", "Unlock unique heroes, each with their own power", "Zappy next to a board where her storm cloud strikes an enemy on a conveyor belt"),
    ("shot5", "Use powerful skills: Frosta casts her Frost Ring", "Frosta next to a board where she casts her Frost Ring, ice shards all around her"),
    ("shot6", "Explore evolving levels: conveyor belts carry you, your bombs and crates", "Gusto next to a level full of conveyor belts and crates, a chain blast beside him"),
    ("shot7", "Solve complex puzzles: push the block into the gap to cross", "Banshee next to a castle puzzle with push blocks and a gap"),
    ("shot8", f"Claim the throne: fight your way to {name('thorn_guard')}'s throne", "Ember next to a castle board, her burning trail behind her and the throne gate at the top"),
]
# The home gallery shows six of the eight (its layout); the press kit shows all eight. v8 frames 3 and 8 carry the game's
# current boss name, so they may be unhidden at any time.
SHOTS_HIDDEN = {"shot3", "shot8"}

# The trailer's poster: ONE hook, the heroes-only v8 frame shot1 (16:9). The old poster (YouTube thumbnail with a painted
# Thorn Guard and "Play free now") is gone (PO 20 Nov 2026: no painted Grimdorn anywhere). To drop in a new poster: put
# trailer-<name>-640/1280.{avif,jpg} in assets/img (tools/make_images.sh) and set the name here. On launch day
# tools/go_live.py can switch to the LIVE variant (TRAILER_POSTER_LIVE) when it exists.
TRAILER_POSTER = ("shot1", "The six heroes: play the Boombaland trailer")
TRAILER_POSTER_LIVE = None  # e.g. ("trailer-live", "...") once the "Play free now" poster may be shown

TRAILER_ID = "rlRE_Cv3Jm4"
CHANNEL = "https://www.youtube.com/@BoombalandGame"
INSTAGRAM = "https://www.instagram.com/boombaland.game/"
TIKTOK = "https://www.tiktok.com/@boombaland"


def trailer_poster():
    return TRAILER_POSTER_LIVE if (TRAILER_POSTER_LIVE and stores_live()) else TRAILER_POSTER


def trailer():
    """The trailer, click-to-play: only the poster loads with the page; YouTube (privacy-enhanced mode) loads on the click."""
    return f"""<section class="section" aria-labelledby="trailer-title">
<div class="wrap">
<h2 class="section-title" id="trailer-title">Watch the trailer</h2>
<div class="trailer" data-trailer="{TRAILER_ID}">
<a class="trailer-play" href="https://youtu.be/{TRAILER_ID}" aria-label="Play the Boombaland trailer">{pic(trailer_poster()[0], [640, 1280], "(min-width: 900px) 860px, 92vw", trailer_poster()[1], 1280, 1280, 720)}<span class="trailer-btn" aria-hidden="true"></span></a>
</div>
<p class="trailer-note">The trailer plays from YouTube, which loads only when you press play.</p>
<div class="stores">
<a class="btn" href="{CHANNEL}" rel="noopener"><span class="stack"><span>YouTube</span><small>@BoombalandGame</small></span></a>
<a class="btn" href="{INSTAGRAM}" rel="noopener"><span class="stack"><span>Instagram</span><small>@boombaland.game</small></span></a>
<a class="btn" href="{TIKTOK}" rel="noopener"><span class="stack"><span>TikTok</span><small>@boombaland</small></span></a>
</div>
</div>
</section>
"""


HEROES = ["blom", "gusto", "frosta", "zappy", "ember", "banshee"]
# One genre wording everywhere (store drafts: "Bomber Game", "Bomb puzzle adventure", keyword "arcade"). Never the
# trademark "Bomberman" (Konami) in copy, titles, meta or JSON-LD.
GENRE_LINE = "a classic bomb-maze arcade game"
GENRES = ["Arcade", "Action", "Puzzle"]
ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "DataSight", "url": SITE + "/",
       "email": MAIL, "logo": SITE + "/assets/img/icon-192.png",
       "address": {"@type": "PostalAddress", "addressCountry": "NL"},
       "sameAs": [CHANNEL, INSTAGRAM, TIKTOK]}


def hero_names():
    return [text("menu.heroes.name_" + h) for h in HEROES]


def about():
    """Plain, quotable facts (answer engines quote these). No AI here: that story lives on /development/."""
    heroes = hero_names()
    if stores_live():
        status = "<p>Yes. Boombaland is out now on the App Store and Google Play.</p>"
    elif partial_live():
        status = f"<p>Yes, on {STORE_PLATFORMS[partial_live()[0]]}. Boombaland is {partial_status()}.</p>"
    else:
        status = "<p>Not yet. Boombaland is coming soon to the App Store and Google Play.</p>"
    return f"""<section class="section" aria-labelledby="about-title">
<div class="wrap prose about">
<h2 class="section-title" id="about-title">What is Boombaland?</h2>
<p>Boombaland is {GENRE_LINE} for iPhone, iPad and Android phones and tablets. You drop bombs, run from the blasts, break
crates, grab power-ups and outsmart enemies on grid boards, with bosses and push-block puzzles along the way.</p>
<p>It has 25 levels in {text('menu.worlds.green_lands')} and on Castle Road, six heroes ({", ".join(heroes[:-1])} and
{heroes[-1]}), each with their own skill, and four difficulties from Easy to Impossible. Besides the
{text('menu.main.play')} there is the {text('menu.main.quickmatch')}: quick battles against CPU opponents. You play on
your own, against computer-controlled enemies.</p>
<p>Boombaland is free to play. It offers optional in-app purchases. Ads only play when you choose to watch one for a
reward. There are no loot boxes.</p>
<h3>Is Boombaland out yet?</h3>
{status}
<h3>Who makes Boombaland?</h3>
<p>DataSight, the one-person studio of Tom de Bruijn in the Netherlands.</p>
</div>
</section>
"""


def home_jsonld():
    """Organization + WebSite + VideoGame. offers + sameAs list only the live store(s) (tools/go_live.py)."""
    links = store_links()
    game = {"@type": "VideoGame", "@id": SITE + "/#game", "name": "Boombaland", "url": SITE + "/",
            "description": f"Boombaland is {GENRE_LINE} for iPhone, iPad and Android: drop bombs, dodge the blasts, beat "
                           f"bosses and solve push-block puzzles across 25 levels with six heroes.",
            "genre": GENRES, "gamePlatform": ["iOS", "Android"], "operatingSystem": "iOS, Android",
            "applicationCategory": "GameApplication", "playMode": "SinglePlayer", "numberOfPlayers": 1,
            "image": SITE + "/assets/img/key-art-2048.jpg", "author": {"@id": ORG["@id"]}, "publisher": {"@id": ORG["@id"]},
            "trailer": {"@type": "VideoObject", "name": "Boombaland – Official Trailer",
                        "embedUrl": f"https://www.youtube-nocookie.com/embed/{TRAILER_ID}",
                        "url": f"https://youtu.be/{TRAILER_ID}",
                        "thumbnailUrl": f"{SITE}/assets/img/{trailer_poster()[0]}-1280.jpg"}}
    live = live_stores()
    if live:
        game["offers"] = [{"@type": "Offer", "price": "0", "priceCurrency": "EUR", "availability": "https://schema.org/InStock",
                           "url": links[k]} for k in live]
        game["sameAs"] = [links[k] for k in live]
    site = {"@type": "WebSite", "@id": SITE + "/#website", "name": "Boombaland", "url": SITE + "/",
            "publisher": {"@id": ORG["@id"]}}
    return [{"@context": "https://schema.org", "@graph": [ORG, site, game]}]


def home():
    gallery = "\n".join(
        f'<li><figure><a href="/assets/img/{n}-1280.jpg" data-lightbox data-caption="{html.escape(c)}">'
        + pic(n, [640, 1280], "(min-width: 1000px) 25vw, (min-width: 600px) 50vw, 100vw", alt, 640, 640, 360)
        + f"</a><figcaption>{html.escape(c)}</figcaption></figure></li>"
        for n, c, alt in SHOTS if n not in SHOTS_HIDDEN)
    clips = "\n".join(c for c in (clip_html(n) for n in HOME_CLIPS) if c)
    clips_section = (f"""<section class="section" aria-labelledby="clips-title">
<div class="wrap">
<h2 class="section-title" id="clips-title">See it in action</h2>
<div class="clips">
{clips}
</div>
</div>
</section>
""" if clips else "")
    body = f"""<main id="main">
<section class="hero" aria-labelledby="hero-title">
{pic("hero-castle", [800, 1280, 1920], "100vw", "", 1280, 1280, 720, cls="", lazy=False).replace('<picture>', '<picture class="bg">')}
<div class="wrap">
<div class="hero-copy">
<h1 id="hero-title" class="hero-h1">{pic("logo", [480, 960], "(min-width: 600px) 520px, 90vw", "Boombaland", 480, 480, 110, ext="png", cls="hero-logo", lazy=False)}</h1>
<p class="hero-tag">Ready, Set, BOOM!</p>
<p class="hero-pitch">Drop a bomb, run, and watch the board explode. Battle brutal bosses and unlock epic heroes in bright 3D adventures.</p>
<p class="hero-classic">Classic bomb battles with a fresh new twist.</p>
{"" if stores_live() else f'<p class="date-plank">Out now on {STORE_NAMES[partial_live()[0]]}</p>' if partial_live() else '<p class="date-plank">Coming soon</p>'}
{store_buttons()}
<p class="hero-note">For iPhone, iPad and Android phones and tablets. Free to play.</p>
</div>
{pic("blom", [360, 720], "360px", "Blom, a cheerful sprout hero, holds up a lit bomb", 360, 360, 540, ext="png", cls="hero-blom", lazy=False)}
</div>
</section>

{trailer()}
{about()}
<section class="section" aria-labelledby="features-title">
<div class="wrap">
<h2 class="section-title" id="features-title">Drop. Run. Boom!</h2>
<p class="lede">Simple touch controls: move, drop a bomb, use your skill. Kick bombs, grab power-ups and plan every blast.</p>
<div class="features">

<article class="panel feature" aria-labelledby="f-heroes">
<h3 class="panel-header" id="f-heroes">Unlock epic heroes</h3>
{pic("heroes", [480, 800, 1440], "(min-width: 720px) 36rem, 92vw", "The six heroes side by side: Blom, Gusto, Frosta, Zappy, Ember and Banshee", 480, 800, 367, ext="png", cls="art")}
<ul>
{skill_bullets()}
</ul>
<p>Star up every hero and make each skill stronger.</p>
</article>

<article class="panel feature" aria-labelledby="f-bosses">
<h3 class="panel-header" id="f-bosses">Battle big bosses</h3>
{pic("boss", [360, 570], "220px", f"{name('thorn_guard')} as he is in the game: a wooden forest giant raising his spiked fists on his arena", 360, 360, 480, cls="art art--tall art--shot")}
<ul>
<li>{name('thorn_guard')} hides behind a thorn shield, rains bomb barrages and gets faster when he is enraged</li>
<li>{name('archer')}, the tower, shoots arrow-bombs across the board</li>
<li>{name('airship')}, {name('thorn_guard')}'s flying warship, fires cannonballs that explode the moment they land</li>
<li>On Castle Road, {name('shellback')} blocks every blast with its shell until it walks</li>
<li>{GOAL[:-1]}</li>
</ul>
</article>

<article class="panel feature" aria-labelledby="f-castle">
<h3 class="panel-header" id="f-castle">Castle puzzles</h3>
{pic("shot7", [640, 1280], "(min-width: 720px) 34rem, 90vw", "Banshee pushes a block into the gap in a castle puzzle", 640, 640, 360, cls="art art--shot")}
<p>25 levels across {text('menu.worlds.green_lands')} and Castle Road, each with its own twist: bridges, switches, towers, timed gates and push-block puzzles. Story comics between chapters, and 4 difficulties, from Easy to Impossible, each with its own three stars on every level.</p>
</article>

<article class="panel feature" aria-labelledby="f-chests">
<h3 class="panel-header" id="f-chests">No loot boxes</h3>
{pic("chest-badge", [256], "140px", "A treasure chest with a green gem", 256, 256, 256, ext="png", cls="art art--badge")}
<p>Every chest shows the item it guarantees, and the chance of everything else, before you open it. No mystery, no surprises.</p>
<p>Earn new heroes, gear, power-ups and Codex entries as you play. Equip boots, gloves and helmets, level them up and merge them at the Blacksmith.</p>
</article>

</div>
</div>
</section>

{clips_section}<section class="section section--wood" aria-labelledby="gallery-title">
<div class="wrap">
<h2 class="section-title" id="gallery-title">Screenshots</h2>
<ul class="gallery">
{gallery}
</ul>
</div>
</section>

<section class="section cta" aria-labelledby="cta-title">
<div class="wrap">
<h2 class="section-title" id="cta-title">{"Play Boombaland" if live_stores() else "Coming soon"}</h2>
{pic("key-art", [1024, 2048], "(min-width: 700px) 640px, 92vw", "The six heroes together under the Boombaland logo", 1024, 1024, 500, cls="art")}
{store_buttons()}
</div>
</section>
</main>

<dialog class="lightbox" id="lightbox" aria-label="Screenshot">
<button type="button" aria-label="Close">&times;</button>
<img src="data:," alt="">
<p></p>
</dialog>
"""
    page("/", body, "Boombaland: drop a bomb, run, BOOM!",
         "Boombaland is a classic bomb-maze arcade game for iPhone, iPad and Android. Battle bosses, unlock six heroes "
         "and solve castle puzzles. " + ("Free to play." if stores_live() else
                                         f"Out now on {STORE_NAMES[partial_live()[0]]}." if partial_live() else "Coming soon."),
         current="/", script=True, jsonld=home_jsonld())


LANG_NAMES = {"en": "English", "de": "German", "nl": "Dutch", "fr": "French", "es": "Spanish", "pt-BR": "Portuguese (Brazil)",
              "ru": "Russian", "ja": "Japanese", "ko": "Korean", "zh-Hans": "Chinese (Simplified)", "zh-Hant": "Chinese (Traditional)"}


def game_languages():
    """The game's languages, in the in-game picker's order: Languages.Codes in Languages.cs at REF."""
    import subprocess
    src = subprocess.run(["git", "-C", BW, "show", f"{REF}:Assets/_Project/Code/Menu/Services/Languages.cs"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    codes = re.findall(r'"([^"]+)"', re.search(r"Codes \{ get; \} = new\[\]\s*\{(.*?)\}", src, re.S).group(1))
    missing = [c for c in codes if c not in LANG_NAMES]
    if missing:
        raise SystemExit(f"build.py: add an English name for language code(s) {missing} to LANG_NAMES")
    return [LANG_NAMES[c] for c in codes]


PRESS_FILES = [  # (file in assets/press, label, size, thumbnail)
    ("boombaland-app-icon-1024.png", "App icon", "1024 × 1024 PNG", "/assets/img/icon-192.png"),
    ("boombaland-logo.png", "Logo", "PNG, transparent", "/assets/img/logo-480.png"),
    ("boombaland-key-art-heroes-2048x1000.jpg", "Key art: the six heroes", "2048 × 1000 JPEG", "/assets/img/key-art-1024.jpg"),
    ("boombaland-castle-heroes-3840x1646.jpg", "The heroes at the castle", "3840 × 1646 JPEG", "/assets/img/press-castle-640.jpg"),
    ("boombaland-castle-logo-1920x1080.jpg", "Castle island with logo", "1920 × 1080 JPEG", "/assets/img/og-image-1200x630.jpg"),
    ("boombaland-blom-1024x1536.png", "Blom, the first hero", "1024 × 1536 PNG, transparent", "/assets/img/blom-360.png"),
]
PRESS_ZIP = "boombaland-press-kit.zip"


def press_status():
    """Release status in one line, from STORE_LINKS: 'Out now on Google Play; coming soon to the App Store'."""
    return ("Out now on the App Store and Google Play" if stores_live() else cap(partial_status("; ")) if partial_live()
            else "Coming soon to the App Store and Google Play")


def press_blurb():
    """The PO-approved fact sheet text (marketing/community_kit_2026-11-21.md, approved 22 Nov 2026), kept true: the friends
    room is still in testing, so its sentence is left out, and the status follows STORE_LINKS."""
    return ("Boombaland is a bomb-arena game for iPhone and Android. Place bombs, break crates, trap the enemies and get out "
            "before the blast. Play through a campaign with castles and bosses. Free to play; ads can be removed. "
            f"{press_status()}.")


def press():
    links = store_links()
    items = "\n".join(
        f'<li><a href="/assets/press/{f}" download><img src="{thumb}" alt="" loading="lazy" decoding="async" width="320" height="200">'
        f'<span>{html.escape(label)}</span></a><br><small>{html.escape(size)}</small></li>'
        for f, label, size, thumb in PRESS_FILES)
    gallery = "\n".join(
        f'<li><figure><a href="/assets/img/{n}-1280.jpg" data-lightbox data-caption="{html.escape(c)}">'
        + pic(n, [640, 1280], "(min-width: 600px) 24rem, 92vw", alt, 640, 640, 360)
        + f'</a><figcaption>{html.escape(c)}<br><a href="/assets/press/boombaland-screenshot-{i}.jpg" download>Full size</a>'
          f' <small>(2560 × 1440 JPEG)</small></figcaption></figure></li>'
        for i, (n, c, alt) in enumerate(SHOTS, 1))
    store_rows = "".join(
        f'<dt>{"App Store" if k == "ios" else "Google Play"}</dt><dd>'
        + (f'<a href="{html.escape(links[k])}" rel="noopener">{"App Store" if k == "ios" else "Google Play"} page</a>' if links[k] else "Coming soon")
        + "</dd>\n" for k in STORES)
    body = f"""<main id="main" class="page">
<div class="wrap prose">
<h1>Press kit</h1>
<p>Boombaland is {GENRE_LINE} for iPhone, iPad and Android phones and tablets. Place bombs, break crates, trap the enemies
and get out before the blast. Play through a campaign with castles and bosses, unlock heroes with their own skills, and
solve push-block puzzles along the way. {press_status()}.</p>
{store_buttons()}
<section class="panel" aria-labelledby="facts-title">
<h2 class="panel-header" id="facts-title">Fact sheet</h2>
<dl class="facts">
<dt>Game</dt><dd>Boombaland</dd>
<dt>Developer</dt><dd>DataSight (Tom de Bruijn), the Netherlands</dd>
<dt>Status</dt><dd>{press_status()}</dd>
{store_rows}<dt>Platforms</dt><dd>iPhone, iPad and Android phones and tablets</dd>
<dt>Price</dt><dd>Free to play, with optional in-app purchases. Ads only play when you choose to watch one for a reward; the No Ads purchase gives those rewards without an ad.</dd>
<dt>Genre</dt><dd>Arcade bomber: {GENRE_LINE} with bosses and puzzles</dd>
<dt>Modes</dt><dd>The {text('menu.main.play')} through {text('menu.worlds.green_lands')} and Castle Road, and the {text('menu.main.quickmatch')}: quick battles against CPU opponents. Single player.</dd>
<dt>Heroes</dt><dd>{", ".join(hero_names())}, each with their own skill</dd>
<dt>Languages</dt><dd>{", ".join(game_languages())}</dd>
<dt>Chests</dt><dd>No loot boxes: every chest shows the item it guarantees and the chance of everything else</dd>
<dt>Website</dt><dd><a href="https://www.boombaland.com/">www.boombaland.com</a></dd>
<dt>Trailer</dt><dd><a href="https://youtu.be/{TRAILER_ID}" rel="noopener">youtu.be/{TRAILER_ID}</a></dd>
<dt>Press contact</dt><dd><a href="mailto:{MAIL}">{MAIL}</a></dd>
</dl>
</section>

<h2 id="copy">Short description to copy</h2>
<p>Free to use as it is in an article, a listing or a profile.</p>
<blockquote class="copy-text" id="blurb">{html.escape(press_blurb())}</blockquote>
<p><button class="btn" type="button" data-copy="blurb">Copy the text</button> <span class="copy-done" role="status" aria-live="polite"></span></p>

<h2 id="trailer-title">Trailer</h2>
<div class="trailer" data-trailer="{TRAILER_ID}">
<a class="trailer-play" href="https://youtu.be/{TRAILER_ID}" aria-label="Play the Boombaland trailer">{pic(trailer_poster()[0], [640, 1280], "(min-width: 900px) 47rem, 92vw", trailer_poster()[1], 1280, 1280, 720)}<span class="trailer-btn" aria-hidden="true"></span></a>
</div>
<p class="trailer-note">The trailer plays from YouTube, which loads only when you press play.</p>

<h2 id="screenshots">Screenshots</h2>
<ul class="gallery">
{gallery}
</ul>

<h2 id="downloads">Logo, icon and art</h2>
<p>You may use these images when you write about or show Boombaland. Please do not change the logo or the characters.</p>
<p><a class="btn" href="/assets/press/{PRESS_ZIP}" download><span class="stack"><span>Download everything</span><small>ZIP, {os.path.getsize(os.path.join(ROOT, "assets", "press", PRESS_ZIP)) / 1e6:.0f} MB</small></span></a></p>
<ul class="downloads">
{items}
</ul>
</div>
</main>

<dialog class="lightbox" id="lightbox" aria-label="Screenshot">
<button type="button" aria-label="Close">&times;</button>
<img src="data:," alt="">
<p></p>
</dialog>
"""
    page("/press/", body, "Boombaland press kit",
         "Boombaland press kit: fact sheet, trailer, screenshots, logo, icon and key art of the bomb-maze arcade game for iPhone, iPad and Android.",
         current="/press/", script=True)


# How a change reaches players (PO, 2 Nov: "add a flow chart"). Real text in every box; site.css lays it out as a vertical
# stack on phones and as a two-row loop on wide screens.
FLOW = [
    ("An idea", "A player's idea, or feedback from a test build."),
    ("Design", "The idea is designed and written up as a task card."),
    ("Build", "AI agents build it, together with automated tests."),
    ("Review", "The work is reviewed, then merged into the game."),
    ("Test run", "A full automated run checks thousands of tests."),
    ("Test build", "A test build goes out on TestFlight and internal testing."),
    ("Play-test", "Testers play it and send their feedback."),
]


def flow_chart():
    steps = "\n".join(
        f'<li class="flow-step"><span class="flow-n" aria-hidden="true">{i}</span><strong class="flow-t">{html.escape(t)}</strong>'
        f'<span class="flow-d">{html.escape(d)}</span></li>'
        for i, (t, d) in enumerate(FLOW, 1))
    loop = ('<li class="flow-step flow-loop"><svg class="flow-icon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" '
            'focusable="false"><path d="M19 12a7 7 0 1 1-2.05-4.95" fill="none" stroke="currentColor" stroke-width="3" '
            'stroke-linecap="round"/><path d="M20 3v5h-5" fill="none" stroke="currentColor" stroke-width="3" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg><strong class="flow-t">Back to the start</strong>'
            '<span class="flow-d">The feedback brings new ideas, and the loop goes round again.</span></li>')
    return f"""<figure class="flow-fig">
<ol class="flow" role="list">
{steps}
{loop}
</ol>
<figcaption>How a change reaches players: an idea, design, build, review, a full test run, a test build and
play-testing. Then the loop starts again.</figcaption>
</figure>"""


def development():
    body = f"""<main id="main" class="page">
<div class="wrap prose">
<h1>How Boombaland is made</h1>
<p>Boombaland is made in the Netherlands by DataSight, the one-person studio of Tom de Bruijn, working with a team of AI
tools. The studio designs and directs the game, plays every build and decides what goes in. The AI tools do much of the
making. Every piece of their work is reviewed and approved before it reaches the game.</p>

<h2 id="pipeline">The pipeline</h2>
<ul>
<li><strong>Concept art and 2D art.</strong> Heroes, worlds, items and screens start as concepts made with OpenAI's
ChatGPT image generation and Codex. The best ones are picked and approved, often after several rounds.</li>
<li><strong>3D models and animation</strong> are built in Blender, by script, from the approved concepts.</li>
<li><strong>Code, tools and documentation</strong> are written with AI coding assistants: Anthropic's Claude, via
Claude Code, and OpenAI Codex. They work as a crew of specialist agents. Their work is directed and reviewed by the
studio.</li>
<li><strong>Sound effects</strong> are synthesised by the project's own script from noise and tones.</li>
<li><strong>Music:</strong> the round, boss, win, lose and finale tracks were generated for Boombaland with
ACE-Step 1.5. The main menu plays "Retro Game" by The_Mountain (Pixabay).</li>
</ul>
<p>The game runs on Unity. The first line of code went in on 30 July 2026. By the end of October, the project had passed
13,000 commits.</p>

<h2 id="flow">How a change reaches players</h2>
<p>Every change, big or small, goes round the same loop. It starts with an idea and ends with feedback, and that feedback
starts the next round.</p>
{flow_chart()}

<h2 id="journey">From one bomb to 25 levels</h2>
<p>Boombaland was built in steps, and every step had to be <em>fun</em> before the next one started. First came the bare
loop: one bomb, one opponent, one small arena. Then power-ups, score and menus. Then the full game: a living board with
bridges, belts and gates, bosses, six heroes, gear and chests.</p>
<p>Version 1.0 has 25 levels in two parts of the same world: <strong>Green Lands</strong>, a floating forest of
bridges, belts and towers, and <strong>Castle Road</strong>, where push-block puzzles lead to {name('thorn_guard')}'s castle. A
nine-chapter comic tells the story between the levels. {GOAL}</p>

<h2 id="next">What's next</h2>
<p>{"Boombaland is out now on the App Store and Google Play." if stores_live() else f"Boombaland is {partial_status()}." if partial_live() else "Boombaland is coming soon to the App Store and Google Play."} From there, Boombaland keeps growing: more to discover, and your ideas can shape what
comes next.</p>

<section class="panel" id="ideas" aria-labelledby="ideas-title">
<h2 class="panel-header" id="ideas-title">Help develop Boombaland</h2>
<p>Got an idea for a hero, a level, a boss or a power-up? Tell us! If we like the idea, we'll get in touch to talk about
the details.</p>
{idea_form()}
</section>
</div>
</main>
"""
    page("/development/", body, "How Boombaland is made",
         "How Boombaland is made by a one-person studio with AI tools, how a change reaches players, what comes next, and how to send us your idea for the game.",
         current="/development/", script=True, jsonld=[{
             "@context": "https://schema.org", "@type": "AboutPage", "@id": SITE + "/development/#page",
             "name": "How Boombaland is made", "url": SITE + "/development/", "inLanguage": "en",
             "about": {"@id": SITE + "/#game"}, "publisher": {"@id": SITE + "/#org"},
             "isPartOf": {"@id": SITE + "/#website"}}])


def idea_form():
    # Ideas arrive by email (PO, 2 Nov): no form service, so nothing passes through a third party.
    subject = "Idea%20for%20Boombaland"
    body = ("Title%20of%20my%20idea%3A%20%0A%0AMy%20idea%3A%20%0A%0A"
            "(Optional)%20My%20name%2C%20if%20I%20am%2016%20or%20older%3A%20%0A")
    return f"""<p><a class="btn" href="mailto:{MAIL}?subject={subject}&amp;body={body}">Email us your idea</a></p>
<p>This opens your mail app with a message to <strong>{MAIL}</strong>. No mail app? Copy the address
and send your idea from any email. Tell us the title of your idea and what it does.</p>
<p>Under 16? Ask a parent to send it for you. We use what you send only to look at your idea and to
reply. See the <a href="/privacy/">Privacy Policy</a>.</p>"""


def not_found():
    body = """<main id="main" class="page">
<div class="wrap prose center">
<h1>Page not found</h1>
<p>This page went BOOM. It may have moved when the site moved to www.boombaland.com.</p>
<p><a class="btn" href="/">Back to Boombaland</a></p>
<p><a href="/support/">Support</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/terms/">Terms of Service</a></p>
</div>
</main>
"""
    page("/404.html", body, "Page not found · Boombaland", "This page could not be found.", noindex=True)


LEGAL = {
    "support": ("/support/", "Boombaland support: help with purchases, refunds, privacy choices, bugs, and deleting your data."),
    "privacy": ("/privacy/", "Boombaland Privacy Policy: what information the game uses, why, who else sees it, and what you can do about it."),
    "terms": ("/terms/", "Boombaland Terms of Service (End User Licence Agreement)."),
}


def port_legal():
    if not LEGAL_SRC:
        print("LEGAL_SRC not set: legal pages left as they are")
        return
    for name, (path, desc) in LEGAL.items():
        src = open(os.path.join(LEGAL_SRC, name, "index.html"), encoding="utf-8").read()
        title = re.search(r"<title>(.*?)</title>", src, re.S).group(1)
        inner = re.search(r"<main>\n<nav>.*?</nav>\n(.*?)<footer>", src, re.S).group(1)
        inner = inner.replace(OLD_MAIL, MAIL)
        for p in ("privacy", "terms", "support"):
            inner = inner.replace(OLD_BASE + p + "/", SITE + "/" + p + "/")
            inner = inner.replace(f'href="../{p}/"', f'href="/{p}/"')
        inner = inner.replace('href="../"', 'href="/"')
        assert OLD_MAIL not in inner and "../" not in inner and "github.io" not in inner, name
        body = f'<main id="main" class="page">\n<article class="wrap prose">\n{inner}</article>\n</main>\n'
        page(path, body, title, desc, current=path)


def llms_txt():
    """/llms.txt (optional, experimental): the same plain facts as the home page, generated so names and status follow the game."""
    h = hero_names()
    status = ("Out now on the App Store and Google Play." if stores_live() else cap(partial_status("; ")) + "." if partial_live()
              else "Coming soon to the App Store and Google Play.")
    bosses = [name(k) for k in ("thorn_guard", "archer", "airship", "shellback", "cobblewatch")]
    out = f"""# Boombaland

> Boombaland is {GENRE_LINE} for iPhone, iPad and Android phones and tablets, made by DataSight,
> the one-person studio of Tom de Bruijn in the Netherlands. Status: {status}

- You drop bombs, run from the blasts, break crates, grab power-ups and outsmart enemies on grid boards, with bosses
  and push-block puzzles.
- 25 levels in {text('menu.worlds.green_lands')} and on Castle Road; six heroes ({", ".join(h[:-1])} and {h[-1]}), each with
  their own skill; four difficulties from Easy to Impossible. Single player, against computer-controlled enemies.
- Bosses and special enemies: {", ".join(bosses[:-1])} and {bosses[-1]}.
- Free to play, with optional in-app purchases. Ads only play when you choose to watch one for a reward. No loot boxes:
  every chest shows the item it guarantees and the chance of everything else.
"""
    links = store_links()
    for k in live_stores():
        out += f"- {'App Store' if k == 'ios' else 'Google Play'}: {links[k]}\n"
    out += f"""
## Pages

- [Home]({SITE}/): what the game is, trailer, screenshots
- [Wiki]({SITE}/wiki/): heroes, enemies, power-ups, levels, gear, chests, read from the game's data
- [Press kit]({SITE}/press/): fact sheet and images
- [How Boombaland is made]({SITE}/development/): the studio, its tools and its process
- [Support]({SITE}/support/): help, purchases, deleting your data ({MAIL})
- [Privacy Policy]({SITE}/privacy/) and [Terms]({SITE}/terms/)
"""
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote llms.txt")


def sync_footer():
    """Pages this script does not write every time (the ported legal pages, the redeem page) get the current shared footer.
    Only the <footer> block is replaced; the legal wording above it is never touched."""
    for rel in ("privacy/index.html", "terms/index.html", "support/index.html", "redeem/index.html"):
        f = os.path.join(ROOT, rel)
        src = open(f, encoding="utf-8").read()
        new = re.sub(r'<footer class="footer">.*?</footer>\n', lambda _m: FOOTER, src, count=1, flags=re.S)
        if new != src:
            open(f, "w", encoding="utf-8").write(new)
            print("footer", rel)


if __name__ == "__main__":
    home()
    press()
    development()
    not_found()
    port_legal()
    sync_footer()
    llms_txt()

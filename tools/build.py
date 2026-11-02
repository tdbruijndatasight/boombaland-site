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
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def skill_bullets():
    """The home page's six skill bullets, in the game's own words: each skill's name (menu.heroes.skill_<hero>) and the
    Heroes screen's description (menu.heroes.skill_<hero>_text), read from MenuStringsEn.cs on the game's branch."""
    import subprocess
    bw = os.environ.get("BOMBWORLD", "/Users/tomdebruijn/Dev/BombWorld")
    ref = os.environ.get("REF", "origin/coordinator/integrate-1028")
    src = subprocess.run(["git", "-C", bw, "show", f"{ref}:Assets/_Project/Code/Menu/Services/MenuStringsEn.cs"],
                         capture_output=True, check=True).stdout.decode("utf-8")

    def text(key):
        m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*"((?:[^"\\]|\\.)*)"', src)
        if not m:
            raise SystemExit(f"build.py: string {key} not found in MenuStringsEn.cs")
        return m.group(1).replace('\\"', '"')

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

NAV = [("/", "Home"), ("/wiki/", "Wiki"), ("/development/", "Development"), ("/press/", "Press"), ("/support/", "Support"),
       ("/privacy/", "Privacy"), ("/terms/", "Terms")]


def nav(current, cls="nav"):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return f'<ul class="{cls}">' + "".join(items) + "</ul>"


def head(title, description, path, og_image="/assets/img/og-image-1200x630.jpg", noindex=False):
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
<meta name="twitter:image" content="{SITE}{og_image}">
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
<p>Boombaland is free to play. It offers optional in-app purchases and may show ads.</p>
<p class="legal-id">Boombaland is made by DataSight (Tom de Bruijn), Tulameenpad 10, 1461 HN Zuidoostbeemster, the Netherlands.
KvK 93353413. Contact: <a href="mailto:{MAIL}">{MAIL}</a></p>
</div>
</footer>
"""


def page(path, body, title, description, current=None, script=False, noindex=False, extra_script=None):
    s = '<script src="/assets/nav.js" defer></script>\n'
    s += '<script src="/assets/site.js" defer></script>\n' if script else ""
    if extra_script:
        s += f'<script src="{extra_script}" defer></script>\n'
    out = head(title, description, path, noindex=noindex) + topbar(current) + body + FOOTER + s + "</body>\n</html>\n"
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
    "boss": "Thorn Guard arrives",
    "bosses": "A boss fight",
    "heroes": "A hero's skill in action",
    "powerups": "Blasts, chains and power-ups",
    "levels": "A level in play",
    "castle": "A castle push-block puzzle",
    "basics": "Drop a bomb, run, BOOM",
}


# The story goal, in the PO's words (round 3). Spoiler-free: no throne hall, no epilogue. Used on home, development, wiki.
GOAL = "Your goal: defeat Thorn Guard and free Boombaland from his thorns."

# The home page's clips, in order (FOOTAGE_NEEDS.md shots 1-4). Missing ones are skipped.
HOME_CLIPS = ["basics", "heroes", "castle", "bosses"]


def clip_html(name, caption=None):
    base = os.path.join(ROOT, "assets", "clips", name)
    if not all(os.path.exists(base + ext) for ext in (".mp4", ".webm", "-poster.jpg")):
        return ""
    cap = html.escape(caption or CLIP_CAPTIONS.get(name, ""))
    u = f"/assets/clips/{name}"
    return (f'<figure class="clip"><video class="clip-video" muted loop playsinline preload="none" width="1280" height="720" '
            f'poster="{u}-poster.jpg" aria-label="Gameplay clip: {cap}" data-clip>'
            f'<source src="{u}.webm" type="video/webm"><source src="{u}.mp4" type="video/mp4"></video>'
            f'<figcaption>{cap}</figcaption></figure>')


def store_buttons():
    return """<div class="stores">
<a class="btn" data-store="ios" href="#" aria-disabled="true"><span class="stack"><span>App Store</span><small data-store-note>Coming end of November</small></span></a>
<a class="btn" data-store="android" href="#" aria-disabled="true"><span class="stack"><span>Google Play</span><small data-store-note>Coming end of November</small></span></a>
</div>"""


SHOTS = [
    ("shot1", "Level 10: a chain of blasts races towards the Thorn Guard", "A bomb chain lights up the board in the Thorn Guard's forest arena"),
    ("shot2", "Level 25: the Thorn Guard is enraged", "The Thorn Guard stands enraged in a castle courtyard while the floor cracks"),
    ("shot3", "Frosta's Frost Ring sets off a chain", "Frosta's skill sets off a chain of blasts across a crate-filled board"),
    ("shot4", "Every boss tells you how to beat it", "The Thorn Guard's intro card: walk over the 3 switch tiles to break its shield"),
    ("shot5", "Level 20: blast past the Rage Towers", "A blast runs between rows of crates next to the Rage Towers"),
    ("shot6", "Castle push-block puzzles", "A walled castle puzzle board with locks, guards and push blocks"),
    ("shot7", "Six heroes, six superpowers", "The heroes screen with Ember, Blom, Gusto, Frosta, Zappy and Banshee"),
    ("shot8", "Every chest shows what it guarantees", "The shop's chests, each showing its guaranteed item and its odds"),
]


def home():
    gallery = "\n".join(
        f'<li><figure><a href="/assets/img/{n}-1280.jpg" data-lightbox data-caption="{html.escape(c)}">'
        + pic(n, [640, 1280], "(min-width: 1000px) 25vw, (min-width: 600px) 50vw, 100vw", alt, 640, 640, 360)
        + f"</a><figcaption>{html.escape(c)}</figcaption></figure></li>"
        for n, c, alt in SHOTS)
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
<p class="date-plank">Coming end of November</p>
{store_buttons()}
<p class="hero-note">For iPhone, iPad and Android. Free to play.</p>
</div>
{pic("blom", [360, 720], "360px", "Blom, a cheerful sprout hero, holds up a lit bomb", 360, 360, 540, ext="png", cls="hero-blom", lazy=False)}
</div>
</section>

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
<h3 class="panel-header" id="f-bosses">Battle brutal bosses</h3>
{pic("thorn-guard", [360, 720], "220px", "The Thorn Guard, a giant wooden forest warrior wrapped in thorny vines", 360, 360, 480, ext="png", cls="art art--tall")}
<ul>
<li>The Thorn Guard hides behind a thorn shield, rains bomb barrages and gets faster when he is enraged</li>
<li>The Rage Tower wakes up and fires arrow-bombs across the board</li>
<li>An enemy airship drops in with its crew and cannons</li>
<li>{GOAL[:-1]}</li>
</ul>
</article>

<article class="panel feature" aria-labelledby="f-castle">
<h3 class="panel-header" id="f-castle">Castle puzzles</h3>
{pic("shot6", [640, 1280], "(min-width: 720px) 34rem, 90vw", "A walled castle puzzle board with locks, guards and push blocks", 640, 640, 360, cls="art art--shot")}
<p>25 levels across the floating forest and Castle Road, each with its own twist: bridges, switches, towers, timed gates and push-block puzzles. Story comics between chapters, and 4 difficulties, from Easy to Impossible, each with its own three stars on every level.</p>
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
<h2 class="section-title" id="cta-title">Coming end of November</h2>
{pic("key-art", [1024, 2048], "(min-width: 700px) 640px, 92vw", "Blom and the Thorn Guard face off over a burning board, with the Boombaland logo between them", 1024, 1024, 500, cls="art")}
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
         "Boombaland is a bomb-blasting arcade game for iPhone, iPad and Android. Battle brutal bosses, unlock six heroes and solve castle puzzles. Coming end of November.",
         current="/", script=True)


PRESS_FILES = [
    ("boombaland-app-icon-1024.png", "App icon", "1024 × 1024 PNG", "/assets/img/icon-192.png"),
    ("boombaland-logo.png", "Logo", "PNG, transparent", "/assets/img/logo-480.png"),
    ("boombaland-key-art-2048x1000.jpg", "Key art", "2048 × 1000 JPEG", "/assets/img/key-art-1024.jpg"),
    ("boombaland-castle-logo-1920x1080.jpg", "Castle island with logo", "1920 × 1080 JPEG", "/assets/img/og-image-1200x630.jpg"),
    ("boombaland-blom-1024x1536.png", "Blom, the first hero", "1024 × 1536 PNG, transparent", "/assets/img/blom-360.png"),
] + [(f"boombaland-screenshot-{i}.jpg", c, "full-size JPEG", f"/assets/img/{n}-640.jpg") for i, (n, c, _a) in enumerate(SHOTS, 1)]


def press():
    items = "\n".join(
        f'<li><a href="/assets/press/{f}" download><img src="{thumb}" alt="" loading="lazy" decoding="async" width="320" height="200">'
        f'<span>{html.escape(label)}</span></a><br><small>{html.escape(size)}</small></li>'
        for f, label, size, thumb in PRESS_FILES)
    body = f"""<main id="main" class="page">
<div class="wrap prose">
<h1>Press kit</h1>
<p>Boombaland is a bomb-blasting arcade game for iPhone, iPad and Android. Drop a bomb, run, and watch the board explode: battle brutal bosses, unlock six heroes with their own superpowers, and solve castle puzzles across 25 levels.</p>
<section class="panel" aria-labelledby="facts-title">
<h2 class="panel-header" id="facts-title">Fact sheet</h2>
<dl class="facts">
<dt>Game</dt><dd>Boombaland</dd>
<dt>Developer</dt><dd>DataSight (Tom de Bruijn), the Netherlands</dd>
<dt>Release date</dt><dd>End of November 2026</dd>
<dt>Platforms</dt><dd>iPhone, iPad and Android</dd>
<dt>Price</dt><dd>Free to play, with optional in-app purchases and optional rewarded video ads</dd>
<dt>Genre</dt><dd>Bomb-blasting arcade game with bosses and puzzles</dd>
<dt>Content</dt><dd>25 levels across the floating forest and Castle Road, 6 heroes, bosses including the Thorn Guard, the Rage Tower and an enemy airship, story comics between chapters, 4 difficulties</dd>
<dt>Chests</dt><dd>No loot boxes: every chest shows the item it guarantees and the chance of everything else</dd>
<dt>Website</dt><dd><a href="https://www.boombaland.com/">www.boombaland.com</a></dd>
<dt>Press contact</dt><dd><a href="mailto:{MAIL}">{MAIL}</a></dd>
</dl>
</section>
<h2>Downloads</h2>
<p>You may use these images when you write about or show Boombaland. Please do not change the logo or the characters.</p>
<ul class="downloads">
{items}
</ul>
</div>
</main>
"""
    page("/press/", body, "Boombaland press kit",
         "Fact sheet, app icon, logo, key art and screenshots of Boombaland, a bomb-blasting arcade game for iPhone, iPad and Android.",
         current="/press/")


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
bridges, belts and towers, and <strong>Castle Road</strong>, where push-block puzzles lead to Thorn Guard's castle. A
nine-chapter comic tells the story between the levels. {GOAL}</p>

<h2 id="next">What's next</h2>
<p>Launch is planned for the end of November 2026. After that, Boombaland keeps growing: more to discover, and your ideas can shape what
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
         current="/development/", script=True)


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


if __name__ == "__main__":
    home()
    press()
    development()
    not_found()
    port_legal()

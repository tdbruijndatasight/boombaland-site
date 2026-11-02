#!/usr/bin/env python3
"""Generates the Boombaland wiki (/wiki/) from the game's own data. No number on these pages is typed by hand.

Sources (all read with `git show <REF>:<path>` from the BombWorld repo; nothing there is changed):
  Assets/_Project/Code/Menu/Services/MenuStringsEn.cs            every player-facing English string
  Assets/_Project/ScriptableObjects/Balance/SO_Balance_Default.asset  skill, power-up, enemy and boss numbers
  Assets/_Project/Code/Menu/Data/Economy/SO_ProgressionCatalog.asset  heroes (unlock, stars), gear, chests, keys, Lucky Chest
  Assets/_Project/Code/Menu/Data/Economy/SO_EconomyCatalog.asset      energy, coins, gems, daily login ladder
  Assets/_Project/Resources/SO_Achievements_Default.asset             achievements
  Assets/_Project/ScriptableObjects/Campaign/SO_Campaign_Default.asset level order (by GUID -> .meta -> level asset)
  Assets/_Project/ScriptableObjects/Levels|CastleRoad/SO_Level_*.asset per-level goals, enemies, bosses, pickups, mechanics
  Assets/_Project/Code/Game/LevelStarTracker.cs                       the star-goal wording (hard-coded in C#)
  Assets/_Project/Code/Sim/PowerUps/PowerUpType.cs, ProgressionCatalog.cs (enums)
  Icons: Assets/_Project/Art/UI/{Portraits,Hud/Skills,Enemies,BossSkills,PowerUps,Gear,Chests,Achievements,Menu}/ (Git LFS)

Usage:  python3 -I tools/build_wiki.py            (BOMBWORLD=/path/to/BombWorld REF=<git ref> to override)
Writes: wiki/**/index.html, wiki/search.json, assets/wiki/*.png, and prints what it could not source.
Excluded on purpose: the epilogue / "teaser" story chapter, the credits roll and the final banner (no spoilers).
"""
import html
import json
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402  (the site's shared head / top bar / footer)

ROOT = build.ROOT
BW = os.environ.get("BOMBWORLD", "/Users/tomdebruijn/Dev/BombWorld")
REF = os.environ.get("REF", "origin/coordinator/integrate-1028")
UNSOURCED = []
TPS = 60  # simulation ticks per second (Fixed.TicksPerSecond)


# ---------------------------------------------------------------- reading the game repo
def show(path, binary=False):
    out = subprocess.run(["git", "-C", BW, "show", f"{REF}:{path}"], capture_output=True, check=True).stdout
    return out if binary else out.decode("utf-8")


def lfs_bytes(path):
    data = show(path, binary=True)
    if data.startswith(b"version https://git-lfs"):
        data = subprocess.run(["git", "-C", BW, "lfs", "smudge"], input=data, capture_output=True, check=True).stdout
    return data


def ls(prefix):
    out = subprocess.run(["git", "-C", BW, "ls-tree", "-r", "--name-only", REF, prefix], capture_output=True, check=True)
    return out.stdout.decode().split()


def strings():
    src = show("Assets/_Project/Code/Menu/Services/MenuStringsEn.cs")
    out = {}
    lit = r'"(?:[^"\\]|\\.)*"'
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*((?:' + lit + r'\s*\+?\s*)+)[,\n]', src):
        parts = re.findall(lit, m.group(2))
        s = "".join(p[1:-1] for p in parts)
        s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda u: chr(int(u.group(1), 16)), s)
        s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        out[m.group(1)] = s
    return out


def field(text, name, default=None):
    m = re.search(r"^\s*" + re.escape(name) + r":[ \t]*(.*)$", text, re.M)
    if not m:
        if default is None:
            UNSOURCED.append(f"field {name} not found")
        return default
    v = m.group(1).strip()
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def raw(text, name):
    m = re.search(r"^\s*" + re.escape(name) + r":[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def packed(hexstr):
    """Unity packs an int array as little-endian int32 hex."""
    b = bytes.fromhex(hexstr)
    return [struct.unpack("<i", b[i:i + 4])[0] for i in range(0, len(b), 4)]


def blocks(text, listname, firstkey):
    """The items of a YAML list `listname:` whose items start with `- firstkey:` (one level, scalar fields)."""
    m = re.search(r"^(\s*)" + re.escape(listname) + r":\s*\n", text, re.M)
    if not m:
        UNSOURCED.append(f"list {listname} not found")
        return []
    indent = m.group(1)
    body = text[m.end():]
    items, cur = [], None
    for line in body.splitlines():
        if not line.startswith(indent) or (line[len(indent):len(indent) + 1] not in ("-", " ") and line.strip()):
            break
        s = line[len(indent):]
        if s.startswith("- " + firstkey + ":"):
            cur = {}
            items.append(cur)
            s = "  " + s[2:]
        elif s.startswith("- "):
            break
        mm = re.match(r"\s+(\w+):\s*(.*)$", s)
        if mm and cur is not None and s.startswith("  ") and not s.startswith("   "):
            v = mm.group(2).strip()
            cur[mm.group(1)] = int(v) if re.fullmatch(r"-?\d+", v) else v
    return items


def enum(path, name):
    src = show(path)
    m = re.search(r"enum\s+" + name + r"\b[^{]*\{(.*?)\}", src, re.S)
    body = re.sub(r"//.*", "", m.group(1))
    out, nxt = {}, 0
    for item in [x.strip() for x in body.split(",") if x.strip()]:
        mm = re.fullmatch(r"(\w+)(?:\s*=\s*(\d+))?", item)
        if not mm:
            continue
        nxt = int(mm.group(2)) if mm.group(2) else nxt
        out[mm.group(1)] = nxt
        nxt += 1
    return out


# ---------------------------------------------------------------- formatting helpers
def esc(s):
    return html.escape(str(s))


def secs(ticks, places=1):
    v = ticks / TPS
    s = f"{v:.{places}f}".rstrip("0").rstrip(".")
    return s


def fill(s, *args):
    for i, a in enumerate(args):
        s = s.replace("{" + str(i) + "}", str(a))
    return s


def an(word):
    return ("an " if word[:1].lower() in "aeiou" else "a ") + word


def table(head, rows, cls=""):
    th = "".join(f"<th scope=\"col\">{h}</th>" for h in head)
    # A "stack" table is too wide for a phone: each cell carries its column name, and site.css lays every row out as a
    # card below 700px (instead of squeezing eight columns into 358px or hiding them behind a sideways scroll).
    lab = (lambda i: f' data-label="{head[i]}"' if head[i] else "") if "stack" in cls.split() else (lambda i: "")
    trs = "".join("<tr>" + "".join(f"<td{lab(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="t"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


ICON_DIR = os.path.join(ROOT, "assets", "wiki")


def icon(src_path, name, size=96, alt="", cls="wiki-icon"):
    """Copies one in-game PNG (LFS) into assets/wiki at `size` px (longest side) and returns an <img>."""
    os.makedirs(ICON_DIR, exist_ok=True)
    dest = os.path.join(ICON_DIR, f"{name}.png")
    if not os.path.exists(dest):
        tmp = dest + ".src.png"
        with open(tmp, "wb") as f:
            f.write(lfs_bytes(src_path))
        subprocess.run(["sips", "-Z", str(size), "-s", "format", "png", tmp, "--out", dest], capture_output=True, check=True)
        os.remove(tmp)
    w = h = size
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", dest], capture_output=True).stdout.decode()
        w = int(re.search(r"pixelWidth: (\d+)", out).group(1))
        h = int(re.search(r"pixelHeight: (\d+)", out).group(1))
    except Exception:
        pass
    return f'<img class="{cls}" src="/assets/wiki/{name}.png" width="{w}" height="{h}" alt="{esc(alt)}" loading="lazy" decoding="async">'


# ---------------------------------------------------------------- load everything
S = strings()


def T(key, *args):
    if key not in S:
        UNSOURCED.append(f"string {key} missing")
        return f"[{key}]"
    return fill(S[key], *args)


BAL = show("Assets/_Project/ScriptableObjects/Balance/SO_Balance_Default.asset")
PROG = show("Assets/_Project/Code/Menu/Data/Economy/SO_ProgressionCatalog.asset")
ECO = show("Assets/_Project/Code/Menu/Data/Economy/SO_EconomyCatalog.asset")
ACH = show("Assets/_Project/Resources/SO_Achievements_Default.asset")
POWER = enum("Assets/_Project/Code/Sim/PowerUps/PowerUpType.cs", "PowerUpType")
SPECIAL = {v: k for k, v in enum("Assets/_Project/Code/Menu/Services/ProgressionCatalog.cs", "GearSpecial").items()}
HEROES = ["blom", "gusto", "frosta", "zappy", "ember", "banshee"]  # HeroId 1..6 (ProgressionCatalog.cs)
HERO_ID = {v: k.lower() for k, v in enum("Assets/_Project/Code/Menu/Services/ProgressionCatalog.cs", "HeroId").items()}
RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]  # GearRarity 1..5, KeyKind 1..5

# levels, in campaign order
camp = show("Assets/_Project/ScriptableObjects/Campaign/SO_Campaign_Default.asset")
guids = re.findall(r"guid: ([0-9a-f]{32}), type: 2", camp)
level_paths = {}
for p in ls("Assets/_Project/ScriptableObjects/Levels") + ls("Assets/_Project/ScriptableObjects/CastleRoad"):
    if p.endswith(".asset.meta"):
        g = re.search(r"guid: ([0-9a-f]{32})", show(p)).group(1)
        level_paths[g] = p[:-5]
LEVELS = []
for i, g in enumerate(guids, 1):
    if g not in level_paths:
        UNSOURCED.append(f"level {i}: GUID {g} has no level asset")
        continue
    LEVELS.append((i, level_paths[g], show(level_paths[g])))

STAR_TEXT = {}
src_star = show("Assets/_Project/Code/Game/LevelStarTracker.cs")
GOAL_ENUM = enum("Assets/_Project/Code/Data/LevelStarGoal.cs", "LevelStarGoal")


def star_goal_text(goal, n):
    name = {v: k for k, v in GOAL_ENUM.items()}.get(goal)
    fn = src_star[src_star.index("class LevelStarGoalText"):]
    m = re.search(r"case LevelStarGoal\." + str(name) + r":\s*return ([^;]+);", fn)
    if not m:
        UNSOURCED.append(f"star goal text for {name}")
        return str(name)
    expr = m.group(1)
    expr = re.sub(r"\.ToString\([^)]*\)", "", expr)
    parts = re.findall(r'"([^"]*)"|\b(n|amount)\b', expr)
    out = ""
    for lit, var in parts:
        out += lit if lit else (f"{n:,}" if name == "ReachScore" else str(n))
    return out


# ---------------------------------------------------------------- pages
PAGES = []  # (slug, title, nav label)
SEARCH = []


def wiki_page(slug, title, intro, body, desc, clip=None):
    PAGES.append((slug, title))
    text = re.sub(r"<[^>]+>", " ", body)
    heads = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", body)
    SEARCH.append({"t": title, "u": f"/wiki/{slug}/" if slug else "/wiki/",
                   "h": [re.sub(r"<[^>]+>", "", h) for h in heads],
                   "x": re.sub(r"\s+", " ", html.unescape(intro + " " + text))[:6000]})
    return (slug, title, intro, body, desc, clip)


def render_all(pages):
    nav_items = "".join(
        f'<li><a href="/wiki/{s + "/" if s else ""}"{{cur_{i}}}>{esc(t)}</a></li>' for i, (s, t, *_r) in enumerate(pages))
    for i, (slug, title, intro, body, desc, clip) in enumerate(pages):
        nav = nav_items
        for j in range(len(pages)):
            nav = nav.replace("{cur_" + str(j) + "}", ' aria-current="page"' if j == i else "")
        clip_html = build.clip_html(clip) if clip else ""
        content = f"""<main id="main" class="page wiki">
<div class="wiki-wrap">
<aside class="wiki-side">
<form class="wiki-search" role="search" action="/wiki/" onsubmit="return false">
<label for="wiki-q" class="sr-only">Search the wiki</label>
<input id="wiki-q" type="search" placeholder="Search the wiki" autocomplete="off">
<ul id="wiki-results" class="wiki-results" aria-live="polite"></ul>
</form>
<details class="wiki-nav" id="wiki-nav">
<summary>Wiki pages</summary>
<nav aria-label="Wiki"><ul>{nav}</ul></nav>
</details>
</aside>
<article class="prose wiki-body">
<p class="crumbs"><a href="/wiki/">Wiki</a>{(' › ' + esc(title)) if slug else ''}</p>
<h1>{esc(title)}</h1>
<p class="lede-left">{intro}</p>
{clip_html}
{body}
<p class="wiki-source">Every number on this page comes from the game's own data for version 1.0. Something wrong? Mail <a href="mailto:{build.MAIL}">{build.MAIL}</a>.</p>
</article>
</div>
</main>
"""
        path = f"/wiki/{slug}/" if slug else "/wiki/"
        build.page(path, content, f"{title} · Boombaland Wiki" if slug else "Boombaland Wiki", desc,
                   current="/wiki/", script=True, extra_script="/assets/wiki.js")


def hero_section():
    star_shards = packed(raw(PROG, "_heroLevelShards"))
    bosses = blocks(PROG, "_bosses", "_hero")
    by_hero = {HERO_ID[b["_hero"]]: b for b in bosses}
    trial, unlock, maxlvl = field(PROG, "_trialGames"), field(PROG, "_unlockShards"), field(PROG, "_maxHeroLevel")
    b = lambda n: field(BAL, n)  # noqa: E731
    cd = lambda p: f"{secs(b(p + 'CooldownTicksAtLevelOne'))} s → {secs(b(p + 'CooldownTicksAtTopLevel'))} s"  # noqa: E731
    stats = {
        "blom": [("Dash", f"{b('dashTilesAtLevelOne')} tiles; {b('dashTilesAtLevelOne') + 1} tiles from ★{b('dashPlusOneFromLevel')}"),
                 ("Cooldown ★1 → ★8", cd("dash"))],
        "gusto": [("Reach", f"{b('gustReachTiles')} tiles"),
                  ("Push", f"{b('gustPushTilesAtLevelOne')} tiles; {b('gustPushTilesAtLevelOne') + 1} from ★{b('gustPushPlusOneFromLevel')}; "
                           f"{b('gustPushTilesAtLevelOne') + 2} from ★{b('gustPushPlusTwoFromLevel')}"),
                  ("Shape", f"straight line; a {b('gustConeWidthTiles')}-tile-wide cone from ★{b('gustConeFromLevel')}"),
                  ("Cooldown ★1 → ★8", cd("gust"))],
        "frosta": [("Ring", f"{b('frostRadiusTilesAtLevelOne')} tiles; {b('frostRadiusTilesAtLevelOne') + 1} from ★{b('frostRadiusPlusOneFromLevel')}"),
                   ("Freeze ★1 → ★8", f"{secs(b('frostFreezeTicksAtLevelOne'), 2)} s → {secs(b('frostFreezeTicksAtTopLevel'), 2)} s "
                                      f"(bosses: {b('frostBossFreezePercent')}% of that)"),
                   ("Cooldown ★1 → ★8", cd("frost"))],
        "zappy": [("Range", f"{b('stormRangeTiles')} tiles"),
                  ("Strikes", f"{b('stormStrikesAtLevelOne')}; {b('stormStrikesAtLevelOne') + 1} from ★{b('stormStrikesPlusOneFromLevel')}; "
                              f"{b('stormStrikesAtLevelOne') + 2} from ★{b('stormStrikesPlusTwoFromLevel')}"),
                  ("Damage", f"{b('stormDamage')} per strike"),
                  ("Stun ★1 → ★8", f"{secs(b('stormStunTicksAtLevelOne'))} s → {secs(b('stormStunTicksAtTopLevel'))} s"),
                  ("Cooldown ★1 → ★8", cd("storm"))],
        "ember": [("Trail ★1 → ★8", f"{secs(b('emberTrailTicksAtLevelOne'))} s → {secs(b('emberTrailTicksAtTopLevel'))} s"),
                  ("Burn ★1 → ★8", f"{secs(b('emberBurnTicksAtLevelOne'))} s → {secs(b('emberBurnTicksAtTopLevel'))} s"),
                  ("Damage", f"{b('emberDamage')}"),
                  ("Cooldown ★1 → ★8", cd("ember"))],
        "banshee": [("Phantom Form ★1 → ★8", f"{secs(b('phantomFormTicksAtLevelOne'))} s → {secs(b('phantomFormTicksAtTopLevel'))} s"),
                    ("Cooldown ★1 → ★8", cd("phantom"))],
    }
    skill_icon = {"blom": "bomb_dash", "gusto": "gust", "frosta": "frost_ring", "zappy": "storm_call", "ember": "ember_trail",
                  "banshee": "phantom_form"}
    out = []
    for h in HEROES:
        name = T(f"menu.heroes.name_{h}")
        if h == "blom":
            how = "Blom is your first hero: you play as Blom from the start."
        elif h == "banshee":
            how = (f"Banshee is sold in the Shop: for {field(PROG, '_bansheeGems')} gems, or as an in-app purchase.")
        else:
            bb = by_hero[h]
            how = (f"Win Level {bb['_levelIndex'] + 1} to meet {name}. That first win gives {bb['_firstShards']} {name} portraits "
                   f"and starts a trial of {trial} games as {name}. Collect {unlock} portraits to unlock {name} for good.")
        rows = "".join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in stats[h])
        out.append(f"""<section class="wiki-card" id="{h}">
<div class="wiki-card-head">{icon(f'Assets/_Project/Art/UI/Portraits/ui_icon_portrait_{h}.png', f'portrait-{h}', 160, name)}
<div><h2>{esc(name)}</h2>
<p class="skill">{icon(f'Assets/_Project/Art/UI/Hud/Skills/skill_{skill_icon[h]}_ready.png', f'skill-{h}', 64, '', 'wiki-icon wiki-icon--sm')}
<strong>{esc(T(f'menu.heroes.skill_{h}'))}</strong>: {esc(T(f'menu.heroes.skill_{h}_text'))}</p></div></div>
<p><strong>How to get {esc(name)}:</strong> {esc(how)}</p>
<div class="t"><table class="kv"><tbody>{rows}</tbody></table></div>
</section>""")
    stars = table(["Star", "Portraits needed"], [[f"★{i + 2}", n] for i, n in enumerate(star_shards)])
    body = "\n".join(out) + f"""
<h2 id="stars">Stars: making a hero stronger</h2>
<p>Every hero goes from ★1 to ★{maxlvl}. A star costs portraits of that hero plus coins. Universal portraits stand in for
any hero's portraits. Each new star makes the skill stronger (the numbers above show ★1 and ★{maxlvl}).</p>
{stars}
<p>A boss level you have won before gives {by_hero['gusto']['_replayShards']} portraits each time you win it again.</p>"""
    return wiki_page("heroes", "Heroes", "Six heroes, six superpowers. Every hero drops bombs like Blom, plus one skill of their own.",
                     body, "Boombaland's six heroes: skills, numbers per star, and how to unlock each one.", clip="heroes")


def enemies_section():
    E = "Assets/_Project/Art/UI/Enemies/"
    roster_first = {}
    for n, path, a in LEVELS:
        m = re.search(r"cpuRoster:\n((?:\s+- tier: \d+\n(?:\s{4}\w+: .*\n)*)*)", a)
        if m:
            for t in re.findall(r"tier: (\d+)", m.group(1)):
                roster_first.setdefault(int(t), n)
    b = lambda n: field(BAL, n)  # noqa: E731
    rows = []
    for tier, key, img in [(1, "twig_scout", "enemy_01_twig_scout_portrait_02"), (2, "burr_bomber", "enemy_02_burr_bomber_portrait_02"),
                           (3, "tier_3", "enemy_03_bramble_lobber_portrait_02")]:
        skills = [S[k] for k in (f"menu.codex.{key}_skill_1", f"menu.codex.{key}_skill_2") if k in S]
        rows.append(f"""<section class="wiki-card" id="{key}"><div class="wiki-card-head">{icon(E + img + '.png', 'enemy-' + key, 128, T('menu.codex.' + key))}
<div><h3>{esc(T('menu.codex.' + key))}</h3><p>{esc(', '.join(skills))}.</p>
<p class="muted">{esc(T('menu.codex.first_level', roster_first.get(tier, '?')))}</p></div></div></section>""")
    boss_levels = [n for n, p, a in LEVELS if re.search(r"bossEntrance:\n\s+- ", a)]
    tg = T("menu.codex.thorn_guard")
    boss = f"""<section class="wiki-card" id="thorn-guard"><div class="wiki-card-head">{icon(E + 'enemy_04_thorn_guard_card_portrait_01.png', 'boss-thorn-guard', 160, tg)}
<div><h3>{esc(tg)}</h3><p>{esc(T('menu.codex.thorn_guard_body_any'))}</p>
<p>Fights you on Levels {', '.join(str(x) for x in boss_levels)}.</p></div></div>
<ul class="skills">
<li>{icon('Assets/_Project/Art/UI/BossSkills/boss_skill_04_thorn_guard_barrage_icon_01.png', 'boss-barrage', 64, '', 'wiki-icon wiki-icon--sm')} {esc(T('menu.codex.thorn_guard_skill_barrage'))}</li>
<li>{icon('Assets/_Project/Art/UI/BossSkills/boss_skill_04_thorn_guard_aimed_throw_icon_01.png', 'boss-throw', 64, '', 'wiki-icon wiki-icon--sm')} {esc(T('menu.codex.thorn_guard_skill_throw'))}</li>
<li>{icon('Assets/_Project/Art/UI/BossSkills/boss_skill_04_thorn_guard_ring_break_icon_01.png', 'boss-ring', 64, '', 'wiki-icon wiki-icon--sm')} {esc(T('menu.codex.thorn_guard_skill_ring'))}</li>
</ul>
{table(['', 'Level ' + str(boss_levels[0]), 'Levels ' + ', '.join(str(x) for x in boss_levels[1:])], [['Hits to win', b('endBossHealthHitsL4'), f"{b('endBossHealthHitsL8')}, then {b('endBossFuriousHealthHitsL8')} more when he gets furious"],
                                              ['Bombs in a barrage', b('bombBarrageBombsL4'), b('bombBarrageBombsL8')]])}
</section>"""
    others = []
    for key, img, body_key, stat in [
        ("archer", "enemy_05_archer_portrait_02", "archer_body_any", f"Takes {b('towerHitPoints')} hits. Range {b('archerRangeTiles')} tiles. An arrow takes {b('arrowDamage')} of your {b('maxHealth')} health."),
        ("airship", None, "airship_body", ""),
        ("shellback", "enemy_06_shellback_portrait_01", "shellback_body", f"Takes {b('shellbackHitPoints')} hits."),
        ("cobblewatch", "enemy_07_cobblewatch_portrait_01", "cobblewatch_body", f"A spear hit takes {b('cobblewatchHitDamage')} of your {b('maxHealth')} health.")]:
        im = icon(E + img + ".png", "enemy-" + key, 128, T("menu.codex." + key)) if img else ""
        others.append(f"""<section class="wiki-card" id="{key}"><div class="wiki-card-head">{im}<div><h3>{esc(T('menu.codex.' + key))}</h3>
<p>{esc(T('menu.codex.' + body_key, '', '', b('towerHitPoints')))}</p><p>{esc(stat)}</p></div></div></section>""")
    dmg = table(["Distance from the bomb", "0 tiles", "1", "2", "3", "4"], [["Damage"] + [b(f"damageAtDistance{i}") for i in range(5)]])
    body = f"""<h2 id="bombers">Bombers</h2>
<p>Thorn Guard's bombers play by the same rules as you: they drop bombs, grab power-ups and can be blown up.</p>
{''.join(rows)}
<h2 id="bosses">The boss</h2>
{boss}
<h2 id="hazards">Towers, the airship and the castle guards</h2>
{''.join(others)}
<h2 id="damage">How much a blast hurts</h2>
<p>Everyone has {b('maxHealth')} health. The closer you stand to the bomb, the more it hurts:</p>
{dmg}"""
    return wiki_page("enemies", "Enemies and bosses", "Who you are up against in Green Lands and on Castle Road.", body,
                     "Boombaland enemies and bosses: the bombers, Thorn Guard, Rage Towers, the airship, Shellback and Cobblewatch.",
                     clip="bosses")


POWER_KEYS = {  # PowerUpType name -> (codex string key, icon file stem)
    "ExtraBomb": ("extra_bomb", "power_up_01_extra_bomb_icon_01"), "FireUp": ("fire_up", "power_up_02_firepower_up_icon_01"),
    "Speed": ("speed", "power_up_03_speed_up_icon_01"), "Armor": ("armor", "power_up_04_armor_icon_01"),
    "Kick": ("kick", "power_up_05_kick_icon_01"), "Heart": ("heart", "power_up_06_heart_icon_01"),
    "ThunderBomb": ("thunder_bomb", "power_up_07_thunder_icon_02"), "IceBomb": ("ice_bomb", "power_up_08_ice_bomb_icon_01"),
    "FireBomb": ("fire_bomb", "power_up_09_fire_bomb_icon_01"), "HealthRegen": ("health_regen", "power_up_10_health_regen_icon_01"),
    "BombDown": ("bomb_down", "power_up_11_bomb_down_icon_01"), "FireDown": ("fire_down", "power_up_12_firepower_down_icon_01"),
    "SpeedDown": ("speed_down", "power_up_13_speed_down_icon_01"), "BrokenShield": ("broken_shield", "power_up_14_broken_shield_icon_01"),
    "RegenDown": ("regen_down", "power_up_15_regen_down_icon_01"), "SurpriseBox": ("surprise_box", "power_up_16_surprise_icon_01"),
}


def power_name(ptype):
    return T("menu.codex." + POWER_KEYS[ptype][0])


def powerups_section():
    b = lambda n: field(BAL, n)  # noqa: E731
    first = {}
    inv = {v: k for k, v in POWER.items()}
    for n, p, a in LEVELS:
        pool = raw(a, "pickupPool")
        if pool and pool != "[]":
            for code in bytes.fromhex(pool):
                first.setdefault(inv.get(code), n)
    extra = {
        "ExtraBomb": f"Start with {b('bombCapacityBase')}, up to {b('bombCapacityMax')}.",
        "FireUp": f"Blasts start at {b('blastRadiusBaseTiles')} tiles, up to {b('blastRadiusMaxTiles')}.",
        "Speed": f"+{b('speedPerPickupTilesPerSecond')} tiles a second each, from {b('baseMoveSpeedTilesPerSecond')} up to {b('maxMoveSpeedTilesPerSecond')}.",
        "Armor": f"Lasts {secs(b('armorDurationTicks'))} s.",
        "Heart": f"Heals {b('heartHealAmount')} health.",
        "HealthRegen": f"Heals {b('healthRegenHealPerPulse')} health every {secs(b('healthRegenPulseIntervalTicks'))} s for {secs(b('healthRegenDurationTicks'))} s.",
        "RegenDown": f"Blocks healing for {secs(b('regenDownHealBlockTicks'))} s.",
        "IceBomb": f"Ice lasts {secs(b('iceTileDurationTicks'))} s.",
    }
    good, bad = [], []
    for ptype, (key, img) in POWER_KEYS.items():
        eff = S.get(f"menu.codex.{key}_effect", "")
        row = [icon(f"Assets/_Project/Art/UI/PowerUps/{img}.png", "pu-" + key, 64, ""),
               f"<strong>{esc(power_name(ptype))}</strong>", esc(" ".join(x for x in [eff, extra.get(ptype, "")] if x)),
               str(first.get(ptype, "–"))]
        if not eff and ptype not in extra:
            UNSOURCED.append(f"power-up {ptype}: no effect text")
        (bad if "Avoid it" in eff or ptype == "RegenDown" else good).append(row)
    head = ["", "Power-up", "What it does", "First level"]
    body = f"""<p>A crate you blow up has a {b('powerUpDropChancePercent')}% chance to drop a power-up. It vanishes after
{secs(b('powerUpDespawnTicks'))} s if nobody takes it. Each level has its own list of power-ups that can drop there.</p>
<h2 id="good">Good power-ups</h2>
{table(head, good, 'icons')}
<h2 id="bad">Power-downs: avoid these</h2>
{table(head, bad, 'icons')}
<h2 id="bombs">Bombs</h2>
<p>A bomb goes off {secs(b('fuseDurationTicks'))} seconds after you drop it. A bomb caught in a blast goes off too, so
one bomb can start a chain.</p>
<p class="muted">"–" in the First level column: this one is not on any campaign level's drop list in version 1.0.</p>"""
    return wiki_page("power-ups", "Power-ups", "What drops out of crates, what it does, and where you first find it.", body,
                     "Every Boombaland power-up and power-down with its effect and the level it first drops on.", clip="powerups")


def gear_section():
    caps = packed(raw(PROG, "_gearLevelCaps"))
    specials = blocks(PROG, "_gearSpecials", "_slot")
    slots = {1: "boots", 2: "gloves", 3: "helmet"}
    rows = []
    for sp in specials:
        name = SPECIAL[sp["_special"]]
        key = re.sub(r"(?<!^)([A-Z])", r"_\1", name).lower()
        vals = packed(str(sp["_values"]))

        def fmt(v):
            if name == "QuickEscape":
                return fill(T("menu.gear.special_value_seconds"), f"{v / TPS:.2f}")
            if name == "Forager":
                return fill(T("menu.gear.special_value_points"), v)
            if name == "SecondWind":
                return fill(T("menu.gear.special_value_health"), v)
            return fill(T("menu.gear.special_value_percent"), v)
        extra = (field(PROG, "_piercingBlastSoftBlocks") if name == "CrateCrusher"
                 else secs(field(PROG, "_earlyBirdCpuWaitTicks")) if name == "EarlyBird" else "")
        text = T(f"menu.gear.special_{key}", "X", "", extra).replace(" X", "").replace("X ", "").strip()
        look = sp["_look"]
        ic = icon(f"Assets/_Project/Art/UI/Gear/ui_gear_{look}_legendary.png", "gear-" + look, 64, "")
        rows.append([ic, f"<strong>{esc(T('menu.gear.look_' + look))}</strong><br>{esc(T('menu.gear.slot_' + slots[sp['_slot']]))}",
                     esc(text.rstrip(':').strip())] + [esc(fmt(v)) for v in vals])
    rar = [esc(T("menu.gear.rarity_" + r)) for r in RARITIES]
    body = f"""<p>{esc(T('menu.main.hint_gear', field(PROG, '_mergeInputs')))}</p>
<h2 id="rarities">Rarities and level caps</h2>
<p>Gear levels belong to the slot, not to the piece: level up your Boots once and every pair you wear counts at that
level, up to the cap of the piece's rarity.</p>
{table(rar, [caps])}
<h2 id="specials">Specials</h2>
<p>Every look has one special. A rarer piece has a stronger special.</p>
{table(['', 'Piece', 'Special'] + rar, rows, 'icons stack')}
<h2 id="blacksmith">The Blacksmith: merging</h2>
<p>Merge {field(PROG, '_mergeInputs')} pieces into one piece of the next rarity. {', '.join(T('menu.gear.rarity_' + r) for r in RARITIES[:field(PROG, '_anyLookMergeMaxRarity')])}
pieces: any {field(PROG, '_mergeInputs')} pieces of the same slot and rarity will do (the first one you pick sets the look). From
{T('menu.gear.rarity_' + RARITIES[field(PROG, '_anyLookMergeMaxRarity')])} up, the {field(PROG, '_mergeInputs')} pieces must be
identical (same slot, look and rarity). {T('menu.gear.rarity_legendary')}
is the top rarity and does not merge.</p>"""
    return wiki_page("gear", "Gear", "Boots, Gloves and a Helmet: three slots, nine looks, five rarities.", body,
                     "Boombaland gear: rarities, level caps, every look's special, and merging at the Blacksmith.")


MECH = [  # (level asset test, codex tile key) ; the lesson system's MechanicsOn (LessonPanel.cs)
    (lambda a: re.search(r"\n    scroll:\n      enabled: 1", a), "scrolling_ground"),
    (lambda a: re.search(r"\n    ring:\n      enabled: 1", a), "shrinking_ring"),
    (lambda a: re.search(r"\n    conveyor:\n      enabled: 1", a), "conveyor_rows"),
]
SWITCH_TILE = {0: "caged_enemies", 1: "bridge_switch", 2: "timed_gates", 3: "switch_order", 4: "reverse_switch"}


def level_facts(n, a):
    facts = []
    for test, key in MECH:
        if test(a):
            facts.append(key)
    m = re.search(r"\n    levelSwitches:\n((?:\s{4}- tileX.*\n(?:\s{6}\w+: .*\n)*)*)", a)
    if m:
        for k in re.findall(r"\n\s{6}kind: (\d+)", "\n" + m.group(1)):
            key = SWITCH_TILE.get(int(k))
            if key and key not in facts:
                facts.append(key)
    return facts


def levels_section():
    inv = {v: k for k, v in POWER.items()}
    seen_tiles, seen_pu, seen_tier = set(), set(), set()
    tier_name = {1: T("menu.codex.twig_scout"), 2: T("menu.codex.burr_bomber"), 3: T("menu.codex.tier_3")}
    rows, cards = [], []
    for n, path, a in LEVELS:
        name = T(f"menu.worlds.level_1_{n}")
        goal = field(a, "starGoal", 0)
        amount = field(a, "starGoalAmount", 0)
        star3 = star_goal_text(goal, amount) if goal else "–"
        new = []
        for key in level_facts(n, a):
            if key not in seen_tiles:
                seen_tiles.add(key)
                new.append(f"<a href=\"/wiki/board/#{key}\">{esc(T('menu.codex.tile_' + key))}</a>")
        pool = raw(a, "pickupPool")
        if pool and pool != "[]":
            for code in bytes.fromhex(pool):
                p = inv.get(code)
                if p in POWER_KEYS and p not in seen_pu:
                    seen_pu.add(p)
                    new.append(esc(power_name(p)))
        m = re.search(r"cpuRoster:\n((?:\s+- tier: \d+\n(?:\s{4}\w+: .*\n)*)*)", a)
        foes = []
        if m:
            for t, c in re.findall(r"tier: (\d+)\n\s+count: (\d+)", m.group(1)):
                t = int(t)
                foes.append(f"{c}× {tier_name.get(t, t)}")
                if t not in seen_tier:
                    seen_tier.add(t)
                    new.append(esc(tier_name.get(t, t)))
        special = []
        if re.search(r"bossEntrance:\n\s+- ", a):
            special.append(T("menu.codex.thorn_guard"))
        if re.search(r"\n  towers:\n\s+- ", a):
            special.append(T("menu.codex.archer"))
        if re.search(r"\n  airship:\n    enabled: 1", a):
            special.append(T("menu.codex.airship"))
        stages = len(re.findall(r"\n    - width: ", a)) if re.search(r"castlePuzzle:\n    enabled: 1", a) else 0
        castle = stages > 0
        world = "Castle Road" if "CastleRoad" in path else T("menu.worlds.green_lands")
        goals = []
        for k in range(1, 4):
            key = f"menu.common.castle_l{n}_s{k}_goal"
            if key in S:
                goals.append(f"Stage {k}: {esc(S[key])}")
        rows.append([str(n), f"<a href=\"#level-{n}\">{esc(name)}</a>", esc(world), esc(star3),
                     ", ".join(esc(s) for s in special) or "–"])
        cards.append(f"""<section class="wiki-level" id="level-{n}"><h3>Level {n}: {esc(name)}</h3>
<ul>
<li><strong>Stars:</strong> ★ Win · ★ Win without taking a hit · ★ {esc(star3)}</li>
{f'<li><strong>Enemies:</strong> {esc(", ".join(foes))}</li>' if foes else ''}
{f'<li><strong>Also here:</strong> {esc(", ".join(special))}</li>' if special else ''}
{f'<li><strong>New here:</strong> {", ".join(new)}</li>' if new else ''}
{f'<li><strong>Castle puzzle:</strong> {stages} stages. ' + ' · '.join(goals) + '</li>' if castle else ''}
</ul></section>""")
    tiers = f"""<p>Every level has four difficulties: Easy, Normal, Hard and Impossible. {esc(T('menu.main.tour_tier'))}
{esc(T('menu.main.tour_stars'))}</p>"""
    body = f"""{tiers}
{table(['#', 'Level', 'Where', 'Third star', 'Boss and specials'], rows)}
<h2 id="every-level">Level by level</h2>
<p>"New here" lists what a level shows you for the first time: board tiles, power-ups and enemies.</p>
{''.join(cards)}"""
    return wiki_page("levels", "Worlds and levels", f"{len(LEVELS)} levels: {T('menu.worlds.green_lands')} and Castle Road. {GOAL}",
                     body, "All 25 Boombaland levels with their star goals, enemies, bosses and what is new on each.", clip="levels")


def board_section():
    keys = ["holes", "tiles_fall", "ground_joins", "rows_shift", "random_collapse", "switches", "bridge_switch", "conveyor_rows",
            "reverse_switch", "shrinking_ring", "caged_enemies", "timed_gates", "switch_order", "scrolling_ground"]
    out = []
    for k in keys:
        if f"menu.codex.tile_{k}" in S:
            out.append(f'<section class="wiki-level" id="{k}"><h3>{esc(T("menu.codex.tile_" + k))}</h3><p>{esc(T("menu.codex.tile_" + k + "_body"))}</p></section>')
    castle_keys = [k for k in S if re.fullmatch(r"menu\.common\.lesson_castle_l21_s1_\d", k)]
    castle = "".join(f"<li>{esc(S[k])}</li>" for k in sorted(castle_keys))
    clock = "".join(f"<li>{esc(S[k])}</li>" for k in sorted(k for k in S if re.fullmatch(r"menu\.common\.lesson_castle_clock_\d", k)))
    runes = "".join(f"<li>{esc(S[k])}</li>" for k in sorted(k for k in S if re.fullmatch(r"menu\.common\.lesson_bell_runes_\d", k)))
    body = f"""<h2 id="tiles">Board tiles</h2>
{''.join(out)}
<h2 id="castle">Castle puzzles</h2>
<p>Levels 21 to 25 on Castle Road are puzzle levels in stages. The game explains them like this:</p>
<ul>{castle}</ul>
<h3 id="castle-clock">The stage clock</h3><ul>{clock}</ul>
<h3 id="bell-runes">The bell and the runes</h3><ul>{runes}</ul>
<p>A castle level gives you {field(PROG, '_castleAttemptRetries', 5) if '_castleAttemptRetries' in PROG else 'some'} retries.</p>"""
    return wiki_page("board", "Board tiles and castle puzzles", "Bridges, belts, cages, gates and push blocks: what the tiles on the board do.",
                     body, "Boombaland board tiles and castle puzzle rules: switches, bridges, belts, gates, push blocks and the stage clock.",
                     clip="castle")


def chests_section():
    chests = blocks(PROG, "_chests", "_kind")
    mats = [field(PROG, f"_{r}ChestMaterials") for r in RARITIES]
    univ = [0, 0] + [field(PROG, f"_{r}ChestUniversalPortraits") for r in RARITIES[2:]]
    keyp = {"common": field(PROG, "_keyPickupCommonPercent"), "uncommon": field(PROG, "_keyPickupUncommonPercent"),
            "rare": field(PROG, "_keyPickupRarePercent")}
    cards = []
    for c in chests:
        r = RARITIES[c["_kind"] - 1]
        rname = T("menu.gear.rarity_" + r)
        others = c["_gearPieces"] - 1
        odds = [f"{T('menu.gear.rarity_' + rr)}: {c['_' + rr + 'Percent']}%" for rr in RARITIES if c["_" + rr + "Percent"]]
        lines = [f"<li><strong>{esc(T('menu.shop.chest_odds_guaranteed', rname))}</strong> gear piece</li>"]
        if others:
            lead = T("menu.shop.chest_odds_more", others) if others > 1 else T("menu.shop.chest_odds_more_one")
            lines.append(f"<li>{esc(lead)} {esc(', '.join(odds))}</li>")
        lines.append(f"<li>{esc(T('menu.shop.chest_odds_coins', c['_coins']))}</li>")
        lines.append(f"<li>{esc(T('menu.shop.chest_odds_materials', mats[c['_kind'] - 1]))}</li>")
        port = T("menu.shop.chest_odds_shards", c["_shards"])
        if c.get("_shardsPercent", 100) < 100:
            port += f" ({c['_shardsPercent']}% chance)"
        lines.append(f"<li>{esc(port)}</li>")
        if univ[c["_kind"] - 1]:
            lines.append(f"<li>{esc(T('menu.shop.chest_odds_universal', univ[c['_kind'] - 1]))}</li>")
        if c["_gems"]:
            lines.append(f"<li>{esc(T('menu.shop.chest_odds_gems', c['_gems']))}</li>")
        price = f"or {c['_gemPrice']} gems in the Shop" if c["_gemPrice"] else "keys only"
        # The Shop's whole closed-chest icon (the game's Shop shows these). Not Chests/chest_0N_*_open_01.png: those are
        # frames of the opening animation, drawn as a narrow front slice, so on a page they read as half a chest.
        img = icon(f"Assets/_Project/Art/UI/Shop/shop_{c['_kind'] + 9}_chest_{r}_icon_01.png", f"chest-{r}", 128, "")
        cards.append(f"""<section class="wiki-card" id="{r}-chest"><div class="wiki-card-head">{img}<div>
<h3>{esc(T('menu.shop.chest_name', rname) if 'menu.shop.chest_name' in S else rname + ' Chest')}</h3>
<p>Opens with {an(rname)} key ({price}). {esc(T('menu.shop.key_info_' + r))}</p></div></div>
<ul>{''.join(lines)}</ul></section>""")
    lucky = {k: field(PROG, k) for k in ("_guaranteedRarity", "_bonusRarity", "_bonusPercent", "_bonusPity", "_freePerWeek", "_drawGems", "_tenDrawGems")}
    gr = T("menu.gear.rarity_" + RARITIES[lucky["_guaranteedRarity"] - 1])
    br = T("menu.gear.rarity_" + RARITIES[lucky["_bonusRarity"] - 1])
    body = f"""<p><strong>Every chest shows what it guarantees before you open it.</strong> Each chest always holds one gear
piece of its own rarity; only the extra pieces are rolled, and the game shows their odds on the chest. A
{T('menu.gear.rarity_common')} key turns up in {keyp['common']}% of games, an {T('menu.gear.rarity_uncommon')} key in
{keyp['uncommon']}% and a {T('menu.gear.rarity_rare')} key in {keyp['rare']}%.</p>
{''.join(cards)}
<h2 id="lucky-chest">{esc(T('menu.shop.lucky_title'))}</h2>
<ul>
<li><strong>{esc(T('menu.shop.lucky_guaranteed', 1, gr))}</strong> gear piece, every draw, shown before you draw.</li>
<li>{esc(T('menu.shop.lucky_bonus', lucky['_bonusPercent'], br))}. {esc(T('menu.shop.lucky_bonus_random'))}</li>
<li>{esc(T('menu.shop.lucky_pity', br, lucky['_bonusPity']))}.</li>
<li>{lucky['_freePerWeek']} free draw a week; then {lucky['_drawGems']} gems a draw, or {lucky['_tenDrawGems']} gems for 10.</li>
</ul>
<p>{esc(T('menu.shop.chests_not_sold'))}</p>"""
    return wiki_page("chests", "Chests and keys", "What is in every chest, with the guaranteed item and the odds the game shows.",
                     body, "Boombaland chests and the Lucky Chest: guaranteed item, odds, coins and portraits, and where keys come from.")


def currencies_section():
    e = lambda n: field(ECO, n)  # noqa: E731
    ladder = blocks(ECO, "_dailyLadder", "_coins")
    rows = []
    for i, d in enumerate(ladder, 1):
        parts = []
        for k, label in [("_coins", "coins"), ("_gems", "gems"), ("_energy", "energy"), ("_leaves", "Leaflets"),
                         ("_portraits", "portraits"), ("_universalPortraits", "universal portraits")]:
            if d.get(k):
                lab = label[:-1] if d[k] == 1 and label.endswith("s") else label
                parts.append(f"{d[k]} {lab}")
        if d.get("_key"):
            parts.append(f"{an(T('menu.gear.rarity_' + RARITIES[d['_key'] - 1]))} key")
        rows.append([f"Day {i}", ", ".join(parts) or "–"])
    ic = lambda f, n: icon(f"Assets/_Project/Art/UI/Menu/{f}.png", n, 64, "", "wiki-icon wiki-icon--sm")  # noqa: E731
    body = f"""<section class="wiki-card" id="energy"><h2>{ic('ui_top_icon_energy_full', 'energy')} Energy</h2>
<p>{esc(T('menu.main.tour_energy', e('_energyPerGame'), 'minute' if e('_secondsPerEnergyPoint') == 60 else str(e('_secondsPerEnergyPoint')) + ' s', e('_energyCap')))}
You start with {e('_startingEnergy')}. Watching an ad gives {e('_adEnergyReward')} energy (up to {e('_adEnergyRewardsPerDay')} times a day).</p></section>
<section class="wiki-card" id="coins"><h2>{ic('ui_top_icon_coin', 'coin')} Coins</h2>
<p>{esc(T('menu.main.tour_coins'))} A first win of a level gives {e('_campaignFirstClearCoins')} coins, a replay {e('_campaignReplayCoins')},
plus {e('_coinsPerStar')} for every star. Coins also pay for gear levels and hero stars.</p></section>
<section class="wiki-card" id="gems"><h2>{ic('ui_top_icon_gem', 'gem')} Gems</h2>
<p>{esc(T('menu.main.tour_gems'))} Achievements pay gems, and so does the daily login on some days.</p></section>
<h2 id="daily">{esc(T('menu.daily.login_title'))}</h2>
<p>{esc(T('menu.main.tour_daily'))}</p>
{table(['Day', 'Reward'], rows)}"""
    return wiki_page("currencies", "Energy, coins and gems", "The three things you collect and spend, and the 28-day login.",
                     body, "Boombaland energy, coins and gems: how you earn them, what they cost, and the 28-day login rewards.")


def achievements_section():
    entries = blocks(ACH, "entries", "id")
    cats = {}
    for en in entries:
        cats.setdefault(en.get("category", "other"), []).append(en)
    out = []
    for cat, items in cats.items():
        rows = []
        for en in items:
            aid = en["id"]
            stem = aid.replace("boomworld.", "").replace(".", "_")
            ipath = f"Assets/_Project/Art/UI/Achievements/ui_achievement_{stem}.png"
            try:
                im = icon(ipath, "ach-" + stem, 64, "")
            except subprocess.CalledProcessError:
                im = ""
                UNSOURCED.append(f"achievement icon {ipath}")
            rows.append([im, f"<strong>{esc(T('achievement.' + aid + '.title'))}</strong>", esc(T("achievement." + aid + ".before")),
                         f"{en.get('gems', 0)} gem{'s' if en.get('gems', 0) != 1 else ''}"])
        out.append(f"<h2 id=\"{esc(cat)}\">{esc(cat.capitalize())}</h2>" + table(["", "Achievement", "How", "Reward"], rows, "icons"))
    return wiki_page("achievements", "Achievements", f"All {len(entries)} achievements, also in Game Center and Google Play Games.",
                     "".join(out), "Every Boombaland achievement and how to earn it.")


def start_section():
    training = [k for k in S if k.startswith("menu.codex.training_")]
    tour = ["menu.main.tour_levels", "menu.main.tour_stars", "menu.main.tour_tier", "menu.main.tour_energy", "menu.main.tour_shop_back"]
    e = lambda n: field(ECO, n)  # noqa: E731
    body = f"""<h2 id="goal">The story</h2>
<p>{esc(S['menu.settings.mail_welcome_body'].split(chr(10))[0])} {esc(GOAL)}</p>
<h2 id="controls">Controls</h2>
<ul>
<li><strong>Touch:</strong> move with the joystick, tap the bomb button to drop a bomb, tap the skill button to use your hero's skill.
Joystick and button settings are under Settings › Controls.</li>
<li><strong>Keyboard:</strong> arrow keys or WASD to move, Space to drop a bomb, X for the skill, E to turn the camera.</li>
</ul>
<h2 id="first-steps">Your first steps</h2>
<ul>{''.join(f'<li>{esc(T(k, e("_energyPerGame"), "minute", e("_energyCap")))}</li>' for k in tour)}</ul>
<h2 id="tips">Tips from the game</h2>
<ul>
<li>{esc(T('menu.codex.kick_effect'))}</li>
<li>{esc(T('menu.codex.training_harmless')) if 'menu.codex.training_harmless' in S else ''}</li>
<li>{esc(T('menu.codex.open_edge_hint'))}</li>
<li>{esc(T('menu.codex.random_collapse_hint'))}</li>
<li>{esc(T('menu.main.hint_chests'))}</li>
<li>{esc(T('menu.main.hint_tasks'))}</li>
</ul>"""
    return wiki_page("getting-started", "Getting started", "Controls, your first levels, and tips straight from the game.", body,
                     "How to play Boombaland: touch and keyboard controls, first steps and beginner tips.", clip="basics")


def faq_section():
    body = f"""<h2 id="save">Is my progress saved?</h2>
<p>Yes. Your progress is saved on your device, and a copy is kept in your iCloud (iPhone and iPad) or Google Play Games
account (Android) when you are signed in. Settings › Account › Cloud save across devices keeps the same save on your other
devices of the same kind. The <a href="/privacy/#2-8-cloud-saves">Privacy Policy, section 2.8</a> has the details.</p>
<h2 id="restore">I bought something on a new device. How do I get it back?</h2>
<p>Sign in to the same Apple ID or Google account and tap Settings › Account › Restore Purchases. Permanent purchases such
as No Ads come back. See <a href="/support/#how-do-i-get-my-no-ads-or-unlimited-energy-back-on-a-new-device">Support</a>.</p>
<h2 id="refund">How do I get a refund?</h2>
<p>Refunds are handled by Apple or Google: see <a href="/support/#how-do-i-get-a-refund">Support</a>.</p>
<h2 id="delete">How do I delete my data?</h2>
<p>Settings › Account › Delete my data. See <a href="/support/#delete-your-account-and-data">Support</a> for what it deletes.</p>
<h2 id="chests-random">Are chests random?</h2>
<p>Every chest names its guaranteed gear piece before you open it, and shows the odds of everything else. See
<a href="/wiki/chests/">Chests and keys</a>.</p>
<h2 id="energy-out">I ran out of energy.</h2>
<p>{esc(T('menu.main.tour_energy', field(ECO, '_energyPerGame'), 'minute', field(ECO, '_energyCap')))}</p>
<h2 id="contact">Something else?</h2>
<p>Mail <a href="mailto:{build.MAIL}">{build.MAIL}</a>.</p>"""
    return wiki_page("faq", "FAQ", "Saves, purchases, refunds and your data.", body, "Boombaland frequently asked questions.")


def whatsnew_section():
    body = """<h2 id="v1-0">Version 1.0: end of November 2026</h2>
<p>Boombaland launches on the App Store and Google Play.</p>
<ul>
<li>25 levels across Green Lands and Castle Road, each in Easy, Normal, Hard and Impossible.</li>
<li>Six heroes: Blom, Gusto, Frosta, Zappy, Ember and Banshee.</li>
<li>Bosses, Rage Towers, an airship and the castle's guards.</li>
<li>Gear, the Blacksmith, chests that show what they guarantee, and the Lucky Chest.</li>
<li>Daily login, daily and weekly tasks, and achievements in Game Center and Google Play Games.</li>
</ul>"""
    return wiki_page("whats-new", "What's new", "Patch notes, newest first.", body, "Boombaland patch notes and version history.")


GOAL = build.GOAL


def index_section(pages):
    cards = "".join(f'<li><a href="/wiki/{s}/">{esc(t)}</a></li>' for s, t, *_ in pages)
    body = f"""<p>{esc(GOAL)}</p>
<ul class="wiki-index">{cards}</ul>"""
    return wiki_page("", "Boombaland Wiki", "Everything about Boombaland, straight from the game's own data.", body,
                     "The Boombaland wiki: heroes, enemies, bosses, power-ups, gear, levels, chests, achievements and tips.")


def main():
    sections = [start_section(), heroes_section_wrapper(), enemies_section(), powerups_section(), levels_section(), board_section(),
                gear_section(), chests_section(), currencies_section(), achievements_section(), faq_section(), whatsnew_section()]
    index = index_section(sections)
    PAGES.insert(0, PAGES.pop())  # index first in the nav
    all_pages = [index] + sections
    render_all(all_pages)
    with open(os.path.join(ROOT, "wiki", "search.json"), "w", encoding="utf-8") as f:
        json.dump(SEARCH, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wiki: {len(all_pages)} pages, {len(os.listdir(ICON_DIR))} icons")
    if UNSOURCED:
        print("UNSOURCED / not found:")
        for u in sorted(set(UNSOURCED)):
            print("  ", u)


def heroes_section_wrapper():
    return hero_section()


if __name__ == "__main__":
    main()

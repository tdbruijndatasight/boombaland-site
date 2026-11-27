# www.boombaland.com

Plain static HTML, committed and served as-is by GitHub Pages (branch `master` of `tdbruijndatasight/boombaland-site`)
behind Cloudflare. No trackers, no cookies, no third-party requests before a click: the audience is kids (9+).
**Publishing is the PO's decision:** a push to `master` is a deploy.

## Build

```
python3 -I tools/build.py        # home, press, development, 404, get/, llms.txt; syncs the footer onto legal + redeem pages
python3 -I tools/build_wiki.py   # wiki/** + wiki/search.json + assets/wiki/*, all from the game's own data
python3 -I tools/sitemap.py      # sitemap.xml: every indexable page, lastmod = last commit of the page
tools/qa.sh                      # the checks below; must say QA PASSED before the PO publishes
python3 -m http.server 8080      # preview at http://127.0.0.1:8080/
```

Both build scripts read the game repo (`BOMBWORLD`, default `~/Dev/BombWorld`) at one git ref, `REF` in
`tools/build.py` (now `origin/coordinator/release-107-1119`). Every player-visible name and number comes from there:
hero, boss and enemy names from `MenuStringsEn.cs`, numbers from the balance and level assets.

## How a game change reaches the site (PO rule: game changes flow to the website)

1. **When a release branch is cut** (or a name, level or number changes in the game), set `REF` in `tools/build.py` to
   that branch and run `tools/qa.sh --rebuild`.
2. `--rebuild` regenerates the site from the game. If anything changed, it **fails** and lists the files: review
   `git diff`, run `tools/qa.sh` again, commit on a branch, and ask the PO to merge.
3. The **name-drift check** (`tools/qa.py names`, part of `qa.sh`) compares the game's current names with
   `tools/game_names.json`. When the game renames something (as Thorn Guard became Grimdorn), it fails with the old and
   the new name. Then: rebuild, move the old name to `retired`, update `snapshot`. A retired name anywhere in the
   site's visible text (pages, alt text, meta, JSON-LD, llms.txt, wiki search) fails the check.
4. Images can't be rebuilt from the game: `tools/make_images.sh` (and `tools/make_press_images.sh`) re-encode the approved
   store art. `SHOTS_HIDDEN` (`tools/build.py`) keeps frames off the home gallery; the trailer poster is the one setting
   `TRAILER_POSTER`. No painted Grimdorn anywhere (PO 20 Nov 2026): he appears only as he is in the game.

CI (`.github/workflows/qa.yml`) runs `tools/qa.sh` on every push and pull request. It is report-only (no deploy) and has
no access to the private game repo, so there the name check uses the snapshot only.

## QA (`tools/qa.sh`, `tools/qa.py`)

| Check | Fails when |
|---|---|
| links | any local link, image or anchor is not 200; missing alt/lang/title/description; not exactly one h1 (`check_links.py`) |
| sitemap | invalid XML or date; an indexable page missing; a listed URL that is not an indexable page |
| meta | title not 10–70 chars, description not 50–160, canonical not the page's own URL, og:image missing |
| noindex | `noindex` anywhere but `404.html` |
| jsonld | a block doesn't parse; `aggregateRating`/`review`/download counts/awards; `offers` before launch; "Bomberman" |
| availability | while `STORE_LINKS` are empty: "out now", "download now", "play free now", "free download", store-badge wording, the old "Play free now" poster, or a store button that links. After launch: wrong store ids, "Coming soon" left on the home page (`--online` also fetches both store pages) |
| names | a retired name in the site text; a current game name missing; the game renamed something since the snapshot |
| getlink | `/get/` missing, a store URL missing, any external script/img/font/stylesheet, not `noindex`, canonical not `/get/`, listed in the sitemap, or the redirect script navigating anywhere but the two store URLs (the shipped script runs in node against 10 user agents × 173 `?s=` values, compared with a python mirror; the `s` whitelist has its own unit cases) |

## Launch day

`tools/go_live.py` (dry run by default) checks both store URLs live, fills `STORE_LINKS` in `assets/site.js`, rebuilds
(badges, JSON-LD `offers`, status lines) and runs QA. Steps and checklist: `GO_LIVE.md`, "Launch day".

## The bio link: `/get/`

`https://www.boombaland.com/get/` is the one link for social bios (a profile allows one). `tools/build.py` writes it from
`STORE_LINKS`; its script (`tools/get_redirect.js`, inlined) sends iPhone/iPad (also iPadOS in desktop mode) to the App
Store and Android to Google Play with `location.replace`. Everyone else, a browser without JavaScript, and an in-app
browser that blocks the redirect see the page itself: both official badges (`assets/badges/`, unchanged artwork) and a
QR code of `/get/` drawn at build time by `tools/qr.py` (no QR service). No cookie, no analytics, no third-party request
before the store. `noindex`, not in the sitemap.

`?s=<source>` (a-z 0-9 - _, max 24; anything else is dropped) tags the store links: Google Play gets
`&referrer=utm_source%3D<s>%26utm_medium%3Dsocial%26utm_campaign%3Dbio` (Play Console's acquisition reports list
UTM-tagged installs), the App Store `?ct=<s>`. Apple counts `ct` only together with the provider token `pt`: set
`APPLE_PROVIDER_TOKEN` in `tools/build.py` (App Store Connect › Apps › App Analytics › Acquisition › Campaigns ›
"Generate a campaign link": the `pt=` number) and rebuild; the redirect then adds `&pt=…&mt=8`.

Bio links: TikTok `https://www.boombaland.com/get/?s=tiktok`, Instagram `…/get/?s=instagram`, YouTube
`…/get/?s=youtube`, Facebook `…/get/?s=facebook`, X `…/get/?s=x`, Reddit `…/get/?s=reddit`.

## Search engines and AI crawlers

- `robots.txt` allows the search and answer bots (Googlebot, Bingbot, Applebot, DuckDuckBot, OAI-SearchBot,
  ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User) and **blocks the AI training crawlers**
  (GPTBot, Google-Extended, Applebot-Extended, ClaudeBot, anthropic-ai, CCBot, Meta-ExternalAgent, Bytespider,
  cohere-training-data-crawler): PO decision 2026-11-20. Everyone else is allowed.
- `llms.txt` is optional and experimental; `build.py` generates it from the same facts as the home page.
- IndexNow: the key file `<32 hex>.txt` is at the root. After a publish, `python3 -I tools/indexnow.py --submit`
  (dry run without `--submit`). Or switch on Cloudflare Crawler Hints instead.
- Never use the trademark "Bomberman" in copy, titles, meta or JSON-LD. The genre wording is "a classic bomb-maze
  arcade game" (`GENRE_LINE` in `tools/build.py`).

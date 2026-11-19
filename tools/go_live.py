#!/usr/bin/env python3
"""Launch day: switch the site from "Coming soon" to the live store pages. DRY RUN unless --apply.

  python3 -I tools/go_live.py                     check both store pages are live; show what would change
  python3 -I tools/go_live.py --apply             ... then fill STORE_LINKS, rebuild everything, run QA (--online)
  python3 -I tools/go_live.py --only android     partial launch: verify and fill only that store (or --only ios); the other
                                                  STORE_LINKS key is left as it is, so its button and copy stay "coming soon"
  options: --ios URL --android URL                (defaults: the canonical URLs for id6821619320 / com.datasight.boomworld)
           --live-poster NAME --live-poster-alt TEXT   use assets/img/NAME-640/1280 as the trailer poster once live

What --apply changes (nothing is committed or pushed; the PO publishes):
  assets/site.js     STORE_LINKS = the verified URL(s) (the one config spot)
  tools/build.py     TRAILER_POSTER_LIVE, only with --live-poster
  rebuilt pages      store buttons -> official badges (assets/badges/, else the green button), JSON-LD VideoGame
                     gets offers (price 0) + sameAs for the live store(s), "Coming soon" lines -> live wording (per store
                     with --only: "out now on Google Play and coming soon to the App Store"), llms.txt, wiki What's new,
                     sitemap.xml
Stops without changing anything when a store page is not live or not the right app.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa  # noqa: E402  (store ids and URL patterns, one definition)

ROOT = qa.ROOT
IOS_DEFAULT = f"https://apps.apple.com/app/id{qa.APPLE_ID}"
PLAY_DEFAULT = f"https://play.google.com/store/apps/details?id={qa.PLAY_ID}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) boombaland-site go_live check"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with qa.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except OSError as e:
        return 0, url, str(e)


def verify(ios, android, only=None):
    ok = True
    if only != "android":
        ok = verify_ios(ios) and ok
    if only != "ios":
        ok = verify_android(android) and ok
    return ok


def verify_ios(ios):
    ok = True
    if not qa.IOS_URL.match(ios):
        print(f"FAIL ios URL {ios!r} is not an App Store URL for id{qa.APPLE_ID}")
        ok = False
    # Apple: the public lookup API is the reliable signal (the page itself rate-limits non-iPhone clients).
    st, _, body = fetch(f"https://itunes.apple.com/lookup?id={qa.APPLE_ID}")
    try:
        res = json.loads(body).get("results", [])
    except ValueError:
        res = []
    if st != 200 or not res or str(res[0].get("trackId")) != qa.APPLE_ID:
        print(f"FAIL App Store: lookup id={qa.APPLE_ID} -> HTTP {st}, {len(res)} result(s): not public yet"
              + (f" ({body[:120]})" if st == 0 else ""))
        ok = False
    else:
        print(f"ok   App Store: {res[0].get('trackName')!r} {res[0].get('version')} ({res[0].get('trackViewUrl', '')[:80]})")
    st, final, _ = fetch(ios)
    print(f"{'ok  ' if st == 200 else 'note'} App Store page {ios} -> HTTP {st}"
          + (" (Apple rate-limits desktop clients; the lookup above decides)" if st == 429 else ""))
    return ok


def verify_android(android):
    ok = True
    if not qa.PLAY_URL.match(android):
        print(f"FAIL android URL {android!r} is not the Play URL for {qa.PLAY_ID}")
        ok = False
    st, final, body = fetch(android + ("&" if "?" in android else "?") + "hl=en")
    if st != 200 or qa.PLAY_ID not in body:
        print(f"FAIL Google Play: {android} -> HTTP {st}: not public yet (or not this app)" + (f" ({body[:120]})" if st == 0 else ""))
        ok = False
    else:
        print(f"ok   Google Play: {android} -> HTTP 200")
    return ok


def set_store_links(ios, android, only=None):
    """Fill STORE_LINKS; with only="ios"/"android" just that key (the other is left exactly as it is)."""
    p = os.path.join(ROOT, "assets", "site.js")
    s = open(p, encoding="utf-8").read()
    new = s
    if only != "android":
        new = re.sub(r'(ios:\s*)"[^"]*"', lambda m: f'{m.group(1)}"{ios}"', new, count=1)
    if only != "ios":
        new = re.sub(r'(android:\s*)"[^"]*"', lambda m: f'{m.group(1)}"{android}"', new, count=1)
    return p, s, new


def set_live_poster(name, alt):
    p = os.path.join(ROOT, "tools", "build.py")
    s = open(p, encoding="utf-8").read()
    new = re.sub(r"^TRAILER_POSTER_LIVE = .*$", f"TRAILER_POSTER_LIVE = ({name!r}, {alt!r})", s, count=1, flags=re.M)
    return p, s, new


def run(*cmd):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ios", default=IOS_DEFAULT)
    ap.add_argument("--android", default=PLAY_DEFAULT)
    ap.add_argument("--live-poster")
    ap.add_argument("--live-poster-alt", default="Play the Boombaland trailer")
    ap.add_argument("--only", choices=["ios", "android"],
                    help="partial launch: verify and fill only this store's link (default: both, and both must be live)")
    ap.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    a = ap.parse_args()

    print("== 1. verify the store page" + (f"s ({a.only} only)" if a.only else "s"))
    if not verify(a.ios, a.android, a.only):
        print("STOP: not switching. Nothing was changed.")
        return 1

    edits = [set_store_links(a.ios, a.android, a.only)]
    if a.live_poster:
        for size in (640, 1280):
            for ext in ("avif", "jpg"):
                f = os.path.join(ROOT, "assets", "img", f"{a.live_poster}-{size}.{ext}")
                if not os.path.exists(f):
                    print(f"STOP: live poster file missing: {os.path.relpath(f, ROOT)}")
                    return 1
        edits.append(set_live_poster(a.live_poster, a.live_poster_alt))
    for k, f in (("ios", "assets/badges/app-store-badge.svg"), ("android", "assets/badges/google-play-badge.png")):
        if a.only in (None, k) and not os.path.exists(os.path.join(ROOT, f)):
            print(f"note {f} missing: that store gets the green text button. Official artwork: Apple Marketing Tools /"
                  " Google Play badges page, unchanged (IMAGE_NEEDS.md #10).")

    print("== 2. changes")
    for p, old, new in edits:
        if old == new:
            print(f"   {os.path.relpath(p, ROOT)}: already set")
            continue
        for o, n in zip(old.splitlines(), new.splitlines()):
            if o != n:
                print(f"   {os.path.relpath(p, ROOT)}:\n     - {o.strip()}\n     + {n.strip()}")
    if not a.apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        return 0

    for p, old, new in edits:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(new)
    print("== 3. rebuild + QA")
    rc = (run(sys.executable, "-I", "tools/build.py") or run(sys.executable, "-I", "tools/build_wiki.py")
          or run(sys.executable, "-I", "tools/sitemap.py"))
    if rc:
        print("FAIL: a build step failed; see above. Revert with: git checkout -- .")
        return rc
    rc = run("tools/qa.sh", "--online")
    print("""== next (by hand)
  git diff; commit on a branch; the PO merges to master (= publish).
  After it is live: python3 -I tools/indexnow.py --submit ; Search Console > URL inspection > Request indexing on /.""")
    return rc


if __name__ == "__main__":
    sys.exit(main())

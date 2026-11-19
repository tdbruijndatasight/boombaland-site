#!/usr/bin/env python3
"""Tells IndexNow engines (Bing, Yandex, Naver, Seznam, Yep; not Google) which pages changed. NOT run automatically.

The key is the 32-hex-character file at the site root (<key>.txt, containing only the key). It must be live at
https://www.boombaland.com/<key>.txt before a submit counts, so run this only AFTER the PO has published.

Usage:
  python3 -I tools/indexnow.py                     dry run: prints what would be sent (every URL in sitemap.xml)
  python3 -I tools/indexnow.py /wiki/ /press/      dry run for these paths only
  python3 -I tools/indexnow.py --submit [paths]    actually POST to https://api.indexnow.org/IndexNow

Docs: https://www.indexnow.org/documentation , https://www.bing.com/indexnow/getstarted
Alternative with nothing to run: Cloudflare dashboard > Caching > Configuration > Crawler Hints = On.
"""
import glob
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "www.boombaland.com"
SITE = "https://" + HOST
ENDPOINT = "https://api.indexnow.org/IndexNow"


def key():
    for f in glob.glob(os.path.join(ROOT, "*.txt")):
        k = os.path.basename(f)[:-4]
        if re.fullmatch(r"[0-9a-f]{32}", k) and open(f).read().strip() == k:
            return k
    raise SystemExit("indexnow: no <key>.txt key file at the site root")


def sitemap_urls():
    return re.findall(r"<loc>([^<]+)</loc>", open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read())


def main(argv):
    submit = "--submit" in argv
    paths = [a for a in argv if not a.startswith("--")]
    urls = [SITE + (p if p.startswith("/") else "/" + p) for p in paths] if paths else sitemap_urls()
    k = key()
    body = {"host": HOST, "key": k, "keyLocation": f"{SITE}/{k}.txt", "urlList": urls}
    print(json.dumps(body, indent=1))
    if not submit:
        print("dry run: nothing sent (add --submit after the site is published)", file=sys.stderr)
        return 0
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow:", r.status, file=sys.stderr)  # 200 or 202 = accepted
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

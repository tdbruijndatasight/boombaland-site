#!/usr/bin/env bash
# Site QA, local and in CI, no accounts needed. Report-only: it never commits, pushes or deploys.
#
#   tools/qa.sh              links (check_links.py on a local server) + tools/qa.py (sitemap, meta, noindex, JSON-LD,
#                            availability messaging, name drift against the game)
#   tools/qa.sh --rebuild    first rebuild every generated file from the game (REF, see tools/build.py) and FAIL if
#                            anything changed: the committed site is stale against the game. Needs the game repo.
#   tools/qa.sh --online     also fetch the store pages once STORE_LINKS are filled
#
# Env: BOMBWORLD=/path/to/BombWorld  REF=<git ref>  PORT=8799
set -uo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8799}"
rc=0
REBUILD=0; QA_ARGS=()
for a in "$@"; do
  case "$a" in
    --rebuild) REBUILD=1 ;;
    *) QA_ARGS+=("$a") ;;
  esac
done

if [ "$REBUILD" = 1 ]; then
  echo "== rebuild from the game (${REF:-default REF})"
  before="$(git status --porcelain -- . ':!assets/clips')"
  python3 -I tools/build.py >/dev/null && python3 -I tools/build_wiki.py >/dev/null && python3 -I tools/sitemap.py 2>/dev/null || { echo "FAIL build"; rc=1; }
  after="$(git status --porcelain -- . ':!assets/clips')"
  if [ "$before" != "$after" ]; then
    echo "FAIL [rebuild] the generated site differs from what was there: the game changed. Review 'git diff', commit."
    git status --short -- . ':!assets/clips' | head -40
    rc=1
  else
    echo "rebuild: no change"
  fi
fi

echo "== links (tools/check_links.py on http://127.0.0.1:$PORT)"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
srv=$!
trap 'kill $srv 2>/dev/null' EXIT
for _ in $(seq 1 50); do
  python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$PORT/robots.txt')" 2>/dev/null && break
  python3 -c "import time; time.sleep(0.1)"
done
python3 -I tools/check_links.py "http://127.0.0.1:$PORT" | grep -v '^   https\?://' || rc=1
kill $srv 2>/dev/null; wait $srv 2>/dev/null

echo "== tools/qa.py"
python3 -I tools/qa.py ${QA_ARGS[@]+"${QA_ARGS[@]}"} || rc=1

[ "$rc" = 0 ] && echo "QA PASSED" || echo "QA FAILED"
exit "$rc"

#!/bin/bash
# Re-creates assets/img/ and assets/press/ from the approved sources (macOS sips + ffmpeg; no other tools).
# Every image here is a resize/re-encode of approved art; nothing is drawn. Sources are listed in IMAGE_SOURCES.md.
set -euo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)"; I="$S/assets/img"; P="$S/assets/press"; mkdir -p "$I" "$P"
B=/Users/tomdebruijn/Dev/bombworld-status; RA=$B/review_assets; SH=$B/store_listing/play/shots_1026; PH=$B/store_listing/play
ICON=$RA/app_icon_2026-11-01/BlomBomb_1024.png   # = Assets/_Project/Art/AppIcon/T_AppIcon_BlomBomb_1024.png (PO 1 Nov: previous icon back)
# opaque: AVIF + JPEG fallback
op(){ sips --resampleWidth "$3" -s format avif -s formatOptions 55 "$1" --out "$I/$2-$3.avif" >/dev/null
      sips --resampleWidth "$3" -s format jpeg -s formatOptions 62 "$1" --out "$I/$2-$3.jpg" >/dev/null; }
# transparent: AVIF + PNG fallback
tr(){ sips --resampleWidth "$3" -s format avif -s formatOptions 60 "$1" --out "$I/$2-$3.avif" >/dev/null
      # PNG fallback (browsers without AVIF) only at the smallest width, to keep the repo and page weight small
      if [ "$3" -le 480 ]; then sips --resampleWidth "$3" -s format png "$1" --out "$I/$2-$3.png" >/dev/null; fi; }
for x in 800 1280 1920; do op $RA/endcard_redo_2026-10-29/C7_R8_background_1920x1080.png hero-castle $x; done
# The wordmark's master lives IN this repo, so a redrawn wordmark drops in by replacing this one file (IMAGE_NEEDS.md #7b).
WORDMARK="$S/assets/src/boombaland_wordmark.png"   # g164 boombaland_bomb_inside_o_v2.png (PO approved 2 Nov, "this is perfect"), review_assets/logo_fix_2026-11-02/
for x in 480 960; do tr "$WORDMARK" logo $x; done
for x in 360 720; do tr $B/store_kit/masters/blom_standing_2048x3072_C2_R3.png blom $x; done
for x in 360 720; do tr $B/store_kit/shared/thorn_guard_fullbody_1200x1600_C4_R3.png thorn-guard $x; done
for x in 480 800 1440; do tr $B/store_kit/shared/six_hero_lineup_2400x1100_C3_R3.png heroes $x; done  # 1600 with alpha decodes blank in Chrome (sips AVIF)
tr $RA/approved_2026-10-30/C8_R1_green.png chest-badge 256
for x in 1024 2048; do op $B/store_kit/masters/feature_graphic_2048x1000_C1_R2.png key-art $x; done
i=0
V7=$RA/store_screens_play_v7   # the store images v7 (PO 4 Nov: "update the images used on the website as well")
for f in $V7/play_en_01.png $V7/play_en_02.png $V7/play_en_03.png $V7/play_en_04.png \
         $V7/play_en_05.png $V7/play_en_06.png $V7/play_en_07.png $V7/play_en_08.png; do
  i=$((i+1)); for x in 640 1280; do op "$f" shot$i $x; done
  sips -s format jpeg -s formatOptions 85 "$f" --out "$P/boombaland-screenshot-$i.jpg" >/dev/null
done
# the trailer's click-to-play poster: the YouTube thumbnail (Blom VS Thorn Guard end card)
for x in 640 1280; do op $RA/youtube_2026-11-04/youtube_thumbnail_1280x720.jpg trailer $x; done
# icons and favicons (opaque square icon)
sips -s format png "$ICON" --out "$P/boombaland-app-icon-1024.png" >/dev/null
for x in 192 180 48 32 16; do sips -z $x $x -s format png "$ICON" --out "$I/icon-$x.png" >/dev/null; done
cp "$I/icon-180.png" "$S/apple-touch-icon.png"
ffmpeg -loglevel error -y -i "$I/icon-48.png" -i "$I/icon-32.png" -i "$I/icon-16.png" -map 0 -map 1 -map 2 -c png "$S/favicon.ico" 2>/dev/null \
  || ffmpeg -loglevel error -y -i "$I/icon-32.png" "$S/favicon.ico"
# Open Graph stand-in: the approved C7 R8 end card (castle island + R1 logo), 1920x1080 -> 1200x675 -> centre crop 1200x630
ffmpeg -loglevel error -y -i $RA/endcard_redo_2026-10-29/C7_R8.png -vf "scale=1200:675,crop=1200:630" -q:v 3 "$I/og-image-1200x630.jpg"
# press downloads
sips -s format jpeg -s formatOptions 88 $B/store_kit/masters/feature_graphic_2048x1000_C1_R2.png --out "$P/boombaland-key-art-2048x1000.jpg" >/dev/null
sips -s format jpeg -s formatOptions 88 $RA/endcard_redo_2026-10-29/C7_R8.png --out "$P/boombaland-castle-logo-1920x1080.jpg" >/dev/null
sips --resampleWidth 1024 -s format png $B/store_kit/masters/blom_standing_2048x3072_C2_R3.png --out "$P/boombaland-blom-1024x1536.png" >/dev/null
cp "$WORDMARK" "$P/boombaland-logo.png"

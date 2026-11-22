#!/bin/bash
# The press kit's images (/press/), from the approved store art (macOS sips + zip; no other tools). Nothing is drawn.
#   screenshots: store images v8 (PO approved 20 Nov 2026), store_kit/v8_2026-11-20/screens/play_en_0{1..8}.png
#   key art:     v8 heroes-only feature graphic master (PO approved with v8; live on Google Play)
#   castle art:  App Store header R1 (PO approved 21 Nov 2026, store_kit/v9_2026-11-21/appstore/PO_APPROVAL.json)
#   Blom:        v8 Blom cut-out with the current plain green scarf (store_kit/v8_2026-11-20/masters)
# No painted Grimdorn anywhere (PO 20 Nov 2026): the old key art (C1 R2) is no longer offered.
set -euo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)"; I="$S/assets/img"; P="$S/assets/press"; mkdir -p "$I" "$P"
K=/Users/tomdebruijn/Dev/bombworld-status/store_kit
op(){ sips --resampleWidth "$3" -s format avif -s formatOptions 55 "$1" --out "$I/$2-$3.avif" >/dev/null
      sips --resampleWidth "$3" -s format jpeg -s formatOptions 62 "$1" --out "$I/$2-$3.jpg" >/dev/null; }
for i in 1 2 3 4 5 6 7 8; do
  f=$K/v8_2026-11-20/screens/play_en_0$i.png
  for x in 640 1280; do op "$f" press-shot$i $x; done
  sips -s format jpeg -s formatOptions 85 "$f" --out "$P/boombaland-screenshot-$i.jpg" >/dev/null
done
FG=$K/v8_2026-11-20/masters/feature_graphic_2048x1000_v8_heroes.png
HD=$K/v9_2026-11-21/appstore/header_R1_approved.png
BL=$K/v8_2026-11-20/masters/blom_standing_2048x3072_C2_R3_v1scarf.png
op "$FG" press-key-art 640
op "$HD" press-castle 640
sips -s format jpeg -s formatOptions 88 "$FG" --out "$P/boombaland-key-art-heroes-2048x1000.jpg" >/dev/null
sips -s format jpeg -s formatOptions 88 "$HD" --out "$P/boombaland-castle-heroes-3840x1646.jpg" >/dev/null
sips --resampleWidth 1024 -s format png "$BL" --out "$P/boombaland-blom-1024x1536.png" >/dev/null
sips --resampleWidth 360 -s format png "$BL" --out "$I/press-blom-360.png" >/dev/null
rm -f "$P/boombaland-key-art-2048x1000.jpg"   # painted Grimdorn (PO 20 Nov 2026)
# everything in one zip (stored, the images are compressed already)
rm -f "$P/boombaland-press-kit.zip"
( cd "$P" && zip -q -0 -X boombaland-press-kit.zip boombaland-app-icon-1024.png boombaland-logo.png \
    boombaland-key-art-heroes-2048x1000.jpg boombaland-castle-heroes-3840x1646.jpg boombaland-castle-logo-1920x1080.jpg \
    boombaland-blom-1024x1536.png boombaland-screenshot-{1,2,3,4,5,6,7,8}.jpg )

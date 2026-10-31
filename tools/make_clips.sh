#!/usr/bin/env bash
# Cut one short gameplay loop for the website from a REAL gameplay recording.
#
#   tools/make_clips.sh SOURCE.mp4 START DURATION NAME [CRF]
#
#   SOURCE    original landscape phone recording (see FOOTAGE_NEEDS.md), e.g. footage/RPReplay_Final1234.MOV; never a
#             storyboard/animatic. iPhone screen recordings (HEVC, variable frame rate, 2556x1179 and similar) work as-is.
#   START     start time in the source, e.g. 12.5 or 00:00:12.5
#   DURATION  4 to 8 seconds
#   NAME      basics | heroes | bosses | powerups | levels | castle  (tools/build.py CLIP_CAPTIONS)
#   CRF       optional starting quality (default 28); the script raises it until both files are under the cap
#
# Writes assets/clips/NAME.mp4 (H.264, faststart), NAME.webm (VP9) and NAME-poster.jpg, all 1280x720, no audio.
# Framing: the source is centre-cropped to 16:9 (an iPhone's 19.5:9 loses ~9% at each side). If that cuts off HUD
# buttons at the edges, set FIT=pad to letterbox instead, or CROP_X=0..1 to slide the crop (0 = left, 1 = right).
# Then rebuild: python3 tools/build.py (with LEGAL_SRC) and python3 -I tools/build_wiki.py.
# A clip shows up on the site only when all three files exist.
set -euo pipefail

if [ $# -lt 4 ]; then sed -n '2,15p' "$0"; exit 2; fi
SRC=$1; START=$2; DUR=$3; NAME=$4; CRF=${5:-28}
CAP_BYTES=$((1500 * 1024))            # ~1.5 MB per file
FFMPEG=${FFMPEG:-ffmpeg}

case "$NAME" in basics|heroes|bosses|powerups|levels|castle) ;; *) echo "unknown clip name: $NAME" >&2; exit 2;; esac
awk -v d="$DUR" 'BEGIN{exit !(d>=4 && d<=8)}' || { echo "DURATION must be 4-8 s (got $DUR)" >&2; exit 2; }
[ -f "$SRC" ] || { echo "no such file: $SRC" >&2; exit 2; }

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/assets/clips"; mkdir -p "$OUT"
# Probe: refuse portrait sources (a landscape recording is needed; ffprobe reports the size before rotation).
read -r W H ROT < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height:stream_side_data=rotation \
  -of default=nw=1:nk=1 "$SRC" | tr '\n' ' '; echo)
case "${ROT:-0}" in 90|-90|270|-270) t=$W; W=$H; H=$t;; esac
[ "${W:-0}" -ge "${H:-1}" ] || { echo "source is portrait (${W}x${H}); record in landscape" >&2; exit 2; }
# ffmpeg applies the rotation itself. Then: 16:9 crop (or pad), 1280x720, constant 30 fps (iPhone recordings are
# variable frame rate), SDR 8-bit 4:2:0 so every browser, Safari included, plays it.
CROP_X=${CROP_X:-0.5}
if [ "${FIT:-crop}" = pad ]; then
  FRAME="scale=1280:720:force_original_aspect_ratio=decrease:flags=lanczos,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x4a2c16"
else
  FRAME="crop='min(iw,ih*16/9)':'min(ih,iw*9/16)':'(iw-ow)*${CROP_X}':'(ih-oh)/2',scale=1280:720:flags=lanczos"
fi
VF="${FRAME},setsar=1,fps=30,format=yuv420p"

size() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1"; }

crf=$CRF
while :; do
  "$FFMPEG" -loglevel error -y -ss "$START" -t "$DUR" -i "$SRC" -an -vf "$VF" \
    -c:v libx264 -profile:v high -preset slow -crf "$crf" -movflags +faststart "$OUT/$NAME.mp4"
  [ "$(size "$OUT/$NAME.mp4")" -le $CAP_BYTES ] && break
  crf=$((crf + 2)); [ $crf -le 40 ] || { echo "cannot get $NAME.mp4 under 1.5 MB; use a shorter DURATION" >&2; exit 1; }
done

wcrf=$((crf + 6))
while :; do
  "$FFMPEG" -loglevel error -y -ss "$START" -t "$DUR" -i "$SRC" -an -vf "$VF" \
    -c:v libvpx-vp9 -b:v 0 -crf "$wcrf" -row-mt 1 -deadline good -cpu-used 2 "$OUT/$NAME.webm"
  [ "$(size "$OUT/$NAME.webm")" -le $CAP_BYTES ] && break
  wcrf=$((wcrf + 3)); [ $wcrf -le 55 ] || { echo "cannot get $NAME.webm under 1.5 MB" >&2; exit 1; }
done

# Poster = the first frame, so the reduced-motion still matches where the loop starts.
"$FFMPEG" -loglevel error -y -ss "$START" -i "$SRC" -frames:v 1 -vf "$VF" -q:v 4 "$OUT/$NAME-poster.jpg"

printf '%s: mp4 %s B (crf %s), webm %s B (crf %s), poster %s B\n' "$NAME" \
  "$(size "$OUT/$NAME.mp4")" "$crf" "$(size "$OUT/$NAME.webm")" "$wcrf" "$(size "$OUT/$NAME-poster.jpg")"

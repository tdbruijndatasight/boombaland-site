# Footage needs: gameplay clips for the website

**Status (31 Oct 2026): no clips on the site yet, because no real gameplay recording exists.** The site is wired for
them. Each clip slot stays hidden until its files are in `assets/clips/`.

## What was checked

| Source | What it is | Usable? |
|---|---|---|
| `bombworld-status/review_assets/store_production_2026-10-29/segment_*.mp4`, `video_0*.mp4` (54 files, EN + NL) | Animatics built from still frames, with the persistent banner "TIMING DRAFT / STILL FRAMES / NOT FINAL GAMEPLAY" (checked on a frame of `segment_wide_04.mp4`). `CLAUDE_HANDOVER.md` says they are "not ... final recorded gameplay", and `approved_2026-10-30` says "Existing MP4s remain draft animatics". | **No.** Storyboard, not gameplay. |
| `review_assets/ember_r3c_build_2026-10-26/*.mp4` (15), `hero_upgrade_2026-10-25/ember/*.mp4` (20) | Ember model motion reviews: one character on a plain background, under 1 s each. | **No.** Model reviews, not gameplay. |
| Anything else under `~/Dev` (depth 3) | No other `.mp4` or `.mov` files. | — |

No clip was recorded from Unity. The brief forbids it.

## Shots needed

Record them on the iPhone (screen recording), in **landscape**, with the **final TestFlight build** and a **store-ready profile** (no player
name "Tom", no "Unlimited" energy badge, Do Not Disturb on). The full-screen original is fine; the site drops the
audio. These follow `store_production_2026-10-29/RECORDING_SHOTLIST.csv` and `CAPTURE_CHECKLIST.md`, so **one recording
session serves both the store preview and the website**.

Record each moment for 10–20 s, with a second of calm before and after. The website loop is the best **4–8 s** of it.
A loop reads best when the start and end frames are similar, for example a hero standing still before the bomb and
after the blast clears.

| # | Clip name | Where on the site | Level | Moment | Loop length |
|---|---|---|---|---|---|
| 1 | `basics` | Home, "See it in action" (1st); wiki Getting started | L1–L3 (any early level) | Hero drops a bomb, runs around a corner, the blast clears crates, and a pickup drops | 5–6 s |
| 2 | `heroes` | Home (2nd); wiki Heroes | Any unlocked level, with Frosta or Zappy (or Blom) | The hero casts a skill in real play, and the skill's effect hits enemies; HUD skill button visible | 5–7 s |
| 3 | `castle` | Home (3rd); wiki Board & castle puzzles | L21 | Hero pushes a block ON a pressure plate, and the gate opens | 6–8 s |
| 4 | `bosses` | Home (4th); wiki Enemies & bosses | L5 (Thorn Guard, first boss) or L25 | Boss arrives or rages; hero dodges and lands a hit. Use L5 if L25 would spoil the castle ending | 6–8 s |
| 5 | `powerups` | Wiki Power-ups | L6–L12 | Hero picks up a power-up, and the next blast is visibly bigger or chains through two bombs | 4–6 s |
| 6 | `levels` | Wiki Worlds & levels | L15 (airship) or L20 (Rage Tower + airship) | The airship passes over a busy board, or a Rage Tower fires | 5–7 s |

Shots 1–4 are the minimum (home page). Shots 5–6 are nice to have. **No epilogue, teaser or finale footage.** The wiki
keeps those out on purpose.

## How a clip goes on the site

**Drop location:** put the iPhone screen recordings in `footage/` in this repo (gitignored, so the originals never
enter git; only the cut clips in `assets/clips/` are committed). The iPhone's `RPReplay_*.MOV` files (HEVC, variable
frame rate, about 2556 × 1179) work as they are. The script centre-crops them to 16:9, which takes about 9% off each side.
If that cuts a HUD button, run it with `FIT=pad` (letterbox) or `CROP_X=0.3` (slide the crop left).

```
tools/make_clips.sh footage/RPReplay_Final1234.MOV 00:00:12.5 6 basics
LEGAL_SRC=... python3 tools/build.py        # home page
python3 -I tools/build_wiki.py               # wiki pages
```

The script writes `assets/clips/<name>.mp4` (H.264), `.webm` (VP9) and `-poster.jpg`, all at 1280 × 720 with no audio.
It raises the compression until each file is under ~1.5 MB. The page plays a clip muted and looped, only while it is on
screen. With "reduce motion" on, only the poster shows. Captions are in `CLIP_CAPTIONS` in `tools/build.py`.

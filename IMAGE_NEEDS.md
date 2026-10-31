# Image needs for www.boombaland.com

The site uses only approved art today (list at the end). Where approved art does not fit a slot, the site uses the best
approved asset as a stand-in. These are the images that would make the site better. None of them is drawn yet. Every ask
follows the game's rules: **no leaves, flowers, vines or moss on any UI frame**, **no oval or pill shape behind any word**,
and **no new characters**. Characters must stay on model with the approved art named in each row.

When an image is delivered and picked, drop it into `assets/` and re-run `tools/make_images.sh` (add a line for it there).

| # | Purpose (where on the site) | Exact size | Transparency | Base it on (approved art) | Stand-in used now |
|---|---|---|---|---|---|
| 1 | **Home hero, wide**: the full-bleed banner behind the logo, the pitch and the store buttons. It needs the castle island with heroes, but no baked-in text or logo, because the logo and copy are live HTML on top. Keep the centre 60% calm (low detail) for the text, and put the characters in the right third. | 2560 × 1200 (desktop) **and** a phone crop of 1080 × 1350 with the same scene | Opaque | C7 R8 clean background `review_assets/endcard_redo_2026-10-29/C7_R8_background_1920x1080.png`, with Blom C2 R3 (`store_kit/masters/blom_standing_2048x3072_C2_R3.png`) and the C3 R3 six-hero lineup | C7 R8 clean background (1920 × 1080) with the C2 R3 Blom cut-out placed over it in HTML. On a phone, Blom is hidden and the scene has no character. |
| 2 | **Open Graph / Twitter share image**: the picture shown when the link is shared in WhatsApp, iMessage, Slack, X or Facebook. | 1200 × 630 | Opaque (JPEG or 24-bit PNG) | C1 R2 feature graphic (`store_kit/masters/feature_graphic_2048x1000_C1_R2.png`) re-composed to 1.91:1, with the R1 wordmark inside the centre 1000 × 500 safe area (some apps crop the edges) | A centre crop of C7 R8 (`endcard_redo_2026-10-29/C7_R8.png`, castle island + R1 logo) at 1200 × 630. The logo sits close to the crop edges. |
| 3 | **Press banner**: the header image of `/press/` and a download for journalists. | 2400 × 800 | Opaque | C1 R2 feature graphic (Blom and the Thorn Guard face-off) widened to 3:1, with the R1 wordmark | None. The press page has no banner, and key art C1 R2 (2048 × 1000) is offered as the download. |
| 4 | **Hero cut-outs, one per hero**: feature panels, the press kit, and later a hero page. | 1024 × 1536 each (2:3, like Blom C2 R3), with the character's feet on the bottom edge and 6% padding elsewhere | Transparent (RGBA PNG) | Each hero as in the C3 R3 six-hero lineup (`store_kit/shared/six_hero_lineup_2400x1100_C3_R3.png`): **Gusto, Frosta, Zappy, Ember and Banshee** (Blom exists already as C2 R3) | The whole C3 R3 lineup in the "Unlock epic heroes" panel. Blom is the only single-hero cut-out. |
| 5 | **Boss cut-outs**: the "Battle brutal bosses" panel and the press kit. | 1200 × 1600 each (like Thorn Guard C4 R3) | Transparent | The in-game Rage Tower and the enemy airship, as they look in the game and on the store screenshots | The Thorn Guard C4 R3 cut-out only (`store_kit/shared/thorn_guard_fullbody_1200x1600_C4_R3.png`). |
| 6 | **Small favicon**: the browser tab icon. The full app icon turns into a green blur at 16 and 32 px. | 32 × 32 and 16 × 16 PNG, plus a 512 × 512 master | Transparent outside the shape is fine | C6 R1 app icon (`review_assets/store_completion_2026-10-29/C6_R1.png`, which is `Assets/_Project/Art/AppIcon/T_AppIcon_C6R1_iOS_1024.png`), simplified to the bomb and Blom's face | C6 R1 scaled down to 16, 32 and 48 px (`favicon.ico`, `assets/img/icon-*.png`). |
| 7 | **Logo on dark wood**: the top bar and footer of every page. | 1200 × 340 | Transparent | R1 wordmark (`review_assets/store_production_2026-10-29/boombaland_wordmark_R1.png`, from `delivery_2026-10-28/logo_R1.png`) with a thicker dark outline, so it reads on `#4a2c16` wood at 150 px wide | The R1 wordmark as-is, at 150 px wide in the top bar. |
| 8 | **Castle-puzzle panel art**: the "Castle puzzles" feature panel. | 1280 × 720 | Opaque | A fresh in-game capture of a castle push-block level, taken with a store-ready profile (no developer name "Tom", no "Unlimited" energy badge) | `store_listing/play/phone_2.jpg` (26 Oct capture). |
| 9 | **Store-ready UI captures**: gallery slots 7 (heroes) and 8 (shop). | 2622 × 1475 or 2560 × 1440 | Opaque | Fresh captures of the Heroes and Shop screens with a store-ready profile | `store_listing/play/phone_5.jpg` and `phone_7.jpg`. Both show the player name "Tom" and the "Unlimited" energy badge. |
| 10 | **Official store badges**: the App Store and Google Play buttons. This is **not a Codex job**. The artwork must be downloaded unchanged from Apple's and Google's marketing pages once the store listings are live, and used under their guidelines. | Apple: from the App Store marketing tools. Google: from the Google Play badge page. | As supplied | Apple "Download on the App Store" and Google "Get it on Google Play" badges | Text buttons drawn with the game's green kit button (`assets/kit/btn-green.png`). |

## Approved art the site uses now

- **Hero background**: C7 R8 clean background, 1920 × 1080 (`review_assets/endcard_redo_2026-10-29/`, approved in `approved_2026-10-30/PO_PICKS.json`).
- **Logo**: R1 wordmark (`review_assets/store_production_2026-10-29/boombaland_wordmark_R1.png`). The PO picked R1 in `art_feedback_2026-10-28/PO_PICKS.json` ("lofo of r1 looks good!").
- **Blom cut-out**: C2 R3 (`store_kit/masters/blom_standing_2048x3072_C2_R3.png`).
- **Six-hero lineup**: C3 R3 (`store_kit/shared/six_hero_lineup_2400x1100_C3_R3.png`).
- **Thorn Guard cut-out**: C4 R3 (`store_kit/shared/thorn_guard_fullbody_1200x1600_C4_R3.png`).
- **Key art**: C1 R2 feature graphic (`store_kit/masters/feature_graphic_2048x1000_C1_R2.png`).
- **Chest badge**: C8 R1 with the green gem (`review_assets/approved_2026-10-30/C8_R1_green.png`).
- **App icon and favicons**: C6 R1 (`store_completion_2026-10-29/C6_R1.png`, byte-identical to the iOS build's `T_AppIcon_C6R1_iOS_1024.png`).
- **Open Graph stand-in**: C7 R8 (`endcard_redo_2026-10-29/C7_R8.png`), cropped.
- **Screenshots**: `store_listing/play/shots_1026/` shot1, shot2 (Rage Towers), shot3 (enraged banner), shot5 (Frosta skill chain) and shot6 (intro card); `store_listing/play/phone_2.jpg`, `phone_5.jpg` and `phone_7.jpg`.
- **UI frames**: the game's leafless R3 kit (panel, header, card) and the soft-gloss green button, from `Assets/_Project/Art/UI/Menu/` on the game's integration branch. They were downscaled by 50% and are used as CSS 9-slices.
- **Fonts**: Lilita One, and Fredoka SemiBold and Bold, copied unmodified from `Assets/_Project/Art/Fonts/` (SIL OFL 1.1, as listed in `legal/CREDITS.md`). Their OFL texts are in `assets/fonts/`.

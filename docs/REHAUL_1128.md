# Site rehaul, 28 Nov 2026: what we took from other game sites, and why

Looked at (public home pages, fetched 28 Nov 2026): Brawl Stars (Supercell), Squad Busters (now a closure FAQ),
Alto's Odyssey, Stumble Guys, Among Us (Innersloth), Sky: Children of the Light, Crossy Road, the Balatro App Store
page; Monument Valley's site rendered only a loading screen without JavaScript. Text-level reading: colour and motion
were judged from our own screenshots, not measured on theirs.

## Patterns we adopted

| Pattern (seen on) | What Boombaland does now | Why |
|---|---|---|
| Logo, one line and both store buttons in the first viewport (Brawl Stars, Alto, Among Us, Stumble Guys) | Hero: key art, the wordmark as the h1, "Drop a bomb, run, BOOM!", one line of what it is, App Store and Google Play buttons, "Free to play · iPhone, iPad and Android". Fits the first screen at 360 × 740. | The page's one job is the install; a phone visitor should not have to scroll to find it. |
| Big key art, not an autoplaying video (all of them) | The approved heroes-at-the-castle art: a square crop around the six heroes on phones, the full scene on wide screens with the copy on a cream card over the castle wall. A muted gameplay loop can sit on top once a clip is committed (it never plays under reduced motion or Data Saver). | Key art is light (64–150 KB AVIF) and reads instantly; none of the studied sites autoplays video in the hero. |
| Trailer behind a click (Alto, Stumble, Among Us, Sky) | Unchanged mechanism: poster first, YouTube (nocookie) only after the click, in its own dark band right after the hero. | Kids' audience: no third-party request before a click. |
| Feature blocks with real screenshots (Brawl Stars, Crossy Road) | "What is Boombaland?": four numbers (25 levels, 6 heroes, 4 difficulties, 0 loot boxes) and four alternating blocks with in-game pictures. | Numbers are the honest social proof we have (no ratings, awards or download counts: JSON-LD rules and kid audience). |
| Character roster (Brawl Stars, Among Us) | Six hero cards with the game's own portraits, names and skill texts from MenuStringsEn.cs. | Characters sell a cute game; the text stays generated from the game. |
| Story hook / villain (Sky, Brawl Stars events) | "Stop Grimdorn" band with the in-game boss crop (no painted Grimdorn). | Gives the campaign a goal in one line. |
| Screenshot row that opens full size (Alto, Among Us) | A swipeable scroll-snap strip on phones, a 3 × 2 grid on desktop, lightbox on tap. | Thumb-friendly; no carousel script. |
| Store buttons repeated near the end (Among Us, Stumble, Crossy) | A closing call to action with Blom and both buttons; "Get the game" in the sticky top bar. | Second chance after the scroll. |
| Footer with legal, press kit and social (all) | Two columns (Game, Help) with every page incl. Privacy and Terms, socials as plain links, the company line. | Legal and support always one tap away; no tracking social widgets. |
| Hamburger menu on phones (Brawl Stars, Crossy Road) | Kept the game's own menu button; the panel now also has "Get the game". | Familiar on phones; uses the game's art. |

## Anti-patterns we avoided

- Splash/loader screens that show nothing until a framework boots (Monument Valley, Sky): every page is plain HTML.
- Heavy bundles, GIFs and many CDNs (Crossy Road, Stumble Guys): no framework, no external request before a click.
- Stale dates and visible config errors (Crossy Road): facts and status lines are generated from the game and STORE_LINKS.
- Store buttons only in the footer (Squad Busters after shutdown).

## Design system (assets/site.css)

- Colour: the game's menu tokens (wood, wood-dark, parchment, cream, leaf greens, gold) plus sky blue from the key art;
  every text pair checked to WCAG AA (Lighthouse accessibility 100 on the tested pages).
- Type: Lilita One for display, Fredoka for UI, the system font for long prose (legal, wiki); one fluid scale
  (`--t-xs` … `--t-3xl`). Spacing scale `--s-1` … `--s-8`; radii 8/14/22 px, rounded rectangles only, never pills.
- Components: dark two-line store buttons, the game's green kit button, cards with a 3 px "ledge" shadow like the game's
  UI, the R3 panel for the press fact sheet, paper sheets on a sky band for every inner page.
- Motion: fade-up reveals, hover lifts and press states; all off under `prefers-reduced-motion`.

## Where we are still weaker than the best of them

- No gameplay video anywhere on the page (Brawl Stars and Sky lead with motion); the clips in FOOTAGE_NEEDS.md are
  still not recorded/committed.
- Official App Store / Google Play badge artwork is not in the repo (IMAGE_NEEDS.md #10), so the buttons are our own.
- No news/updates feed on the home page (the wiki has "What's new"); no press quotes or awards yet.
- Single language (English), like before.

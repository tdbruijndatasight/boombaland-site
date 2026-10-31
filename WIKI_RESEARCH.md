# What game wikis contain (research note for /wiki/)

Researched 31 Oct 2026. Fandom answered every direct fetch with HTTP 402, and the Hollow Knight wiki answered 403. So
the Fandom observations below come from search-result snippets, not from pages I read.

| Wiki | Looked at | What it has |
|---|---|---|
| Minecraft Wiki (official community wiki, read) | https://minecraft.wiki/w/Minecraft_Wiki | topic grid (mobs, blocks, items, brewing…), version tracker and per-version pages, beginner's guide, tutorials, calculators, search box on top, left sidebar |
| Brawl Stars (Fandom, snippets) | https://brawlstars.fandom.com/wiki/Jessie, https://brawlstars.fandom.com/wiki/Sapphire_Plains, https://brawlstars.fandom.com/wiki/Gem_Grab | one page per brawler, map and mode, each with "Tips" and "History" sections. Liquipedia (https://liquipedia.net/brawlstars/Brawl_Stars) adds gadgets, gears, currencies and update history |
| Angry Birds (Fandom, snippets) | https://angrybirds.fandom.com/wiki/Power-Ups, https://angrybirds.fandom.com/wiki/Minion_Pigs/Small_Pig | enemy pages, a power-ups page, per-level pages, galleries |
| Bomberman (Fandom + StrategyWiki) | https://bomberman.fandom.com/wiki/Bomberman_Portable, https://strategywiki.org/wiki/Super_Bomberman/World_1, https://strategywiki.org/wiki/Super_Bomberman_2/Power-ups | per-world and per-stage pages listing enemies and power-ups, plus a power-ups page |
| Clash Royale (Fandom) | not loaded | (unverified) cards, arenas, chests, currencies |

**What these have in common:**
- entity pages with an image, key stats and tips;
- tables for items and levels;
- version history;
- a beginner guide;
- a sidebar and a search box.

**What our wiki ships, ranked by value for a 25-level game at launch:**
1. Heroes
2. Levels
3. Power-ups
4. Enemies and bosses
5. Getting started (controls and tips) and the FAQ
6. Gear
7. Chests
8. Currencies
9. Achievements
10. Board tiles and castle puzzles
11. What's new

Lore is left out on purpose: no spoilers, and the story comics are in the game.

All numbers come from the game's data files through `tools/build_wiki.py`. That script's docstring lists every source
file.

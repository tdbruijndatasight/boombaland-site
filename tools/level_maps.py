#!/usr/bin/env python3
"""Top-down level maps for the wiki, drawn from the game's own level assets (stdlib only; writes SVG).

Read by tools/build_wiki.py, which hands in each level asset's text (git show from the BombWorld repo). Nothing is typed by
hand and nothing is guessed: every cell comes from the asset through the same rules the game uses to lay the board.

Green Lands / Castle Road levels 1-20 (LevelGenerator.GenerateLattice + LevelSimConfig.WriteStackedCells, ported):
  1. every cell is floor, then a hard block on every cell with odd x and odd z (PlaceLattice);
  2. cells outside `boardShape` (row-major over maxWidth x maxHeight, 01 = floor) become void (CarveShape);
  3. `blockShapes` (Bar2, Bar3, Square2, Ell3, four rotations) are written as walls, and a lattice block beside one is
     cleared to floor (BlockShapes.Apply);
  4. spawns: spawn i on corner (0,0), (W-1,H-1), (0,H-1), (W-1,0), moved inward along x by 2 while off the shape
     (AssignSpawnsToCorners); each keeps an L of `spawnClearanceRadiusTiles` free of crates (ReserveClearances);
  5. `stackedCells` are written over the board (authored floor, crates and walls).
  Crates are NOT authored on these levels: each round scatters them over the free floor at `crateDensityPercent`, from
  the round's own random seed. The map therefore marks the cells where a crate can appear, not one particular layout.
  Cells kept free of crates: spawn clearances, boss switches, level switches, vault cells and the border of each
  crate-free ring (LevelSimConfig.BuildLevelGenerator).

Castle Road levels 21-25: each stage's own authored grid (LevelCastlePuzzle: floorCells, wallCells, blockCells, ...);
a cell named in no list is void.

Coordinates: x runs east (left to right), z runs north (bottom to top), as on the game board.
"""
import html

import unity_yaml

CELL = 24  # SVG units per tile

# Colours close to the game's tiles, inside the site's palette (assets/site.css).
C = {
    "floor": "#8cc63f", "floor2": "#80bb36", "wall": "#9aa1ab", "wall_top": "#b9c0c8", "wall_edge": "#5c636d",
    "crate": "#c98b45", "crate_edge": "#7c4e22", "void": "#bfe3f7", "grid": "#5f8f2a", "outline": "#2a1a0c",
    "spot": "#a8743a", "hero": "#2f9be0", "enemy": "#d8402c", "boss": "#7a1d14", "ally": "#ffffff", "switch": "#f2c230",
    "plate": "#e8b230", "block": "#d9a35a", "rune": "#8a5bd0", "gate": "#6b4a2a", "exit": "#3a8022", "power": "#ffd447",
    "tower": "#6d6f75", "vault": "#ffe9a0", "cage": "#4a2c16", "egg": "#fff7e4", "belt": "#7a6a55", "later": "#ffffff",
}


def _int(v, d=0):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return d


def _cells(s):
    """'x,z;x,z' -> [(x, z)]"""
    out = []
    for part in str(s or "").split(";"):
        part = part.strip()
        if part and "," in part:
            a, b = part.split(",")[:2]
            out.append((int(a), int(b)))
    return out


# ---------------------------------------------------------------- block shapes (Sim/Board/BlockShape.cs)
_BASE = {1: [(0, 0), (1, 0)], 2: [(0, 0), (1, 0), (2, 0)], 3: [(0, 0), (1, 0), (0, 1), (1, 1)], 4: [(0, 0), (1, 0), (0, 1)]}


def _turn(x, z, q):
    for _ in range(q):
        x, z = z, -x
    return x, z


def shape_cells(kind, rot, ax, az):
    base = _BASE.get(kind)
    if not base or not 0 <= rot < 4:
        return []
    turned = [_turn(x, z, rot) for x, z in base]
    mx, mz = min(t[0] for t in turned), min(t[1] for t in turned)
    return [(ax + x - mx, az + z - mz) for x, z in turned]


# ---------------------------------------------------------------- a Green Lands level
def standard_board(a, notes):
    W, H = _int(a["gridWidth"]), _int(a["gridHeight"])
    MW, MH = _int(a.get("maxWidth"), W), _int(a.get("maxHeight"), H)
    shape_hex = a.get("boardShape") or ""
    shape = bytes.fromhex(shape_hex) if isinstance(shape_hex, str) and shape_hex else b""

    def in_shape(x, z):
        if not shape:
            return 0 <= x < W and 0 <= z < H
        if not (0 <= x < MW and 0 <= z < MH) or len(shape) != MW * MH:
            return False
        return shape[z * MW + x] != 0

    if _int(a.get("hardBlockPattern")) != 0:
        notes.append("hardBlockPattern is not Lattice: the walls are not drawn from it")
    if _int(a.get("levelCount"), 1) != 1:
        notes.append("a raised second level is not drawn")
    t = {}
    for z in range(H):
        for x in range(W):
            t[x, z] = "H" if (x % 2 == 1 and z % 2 == 1) else "F"
    if shape:
        for z in range(H):
            for x in range(W):
                if not in_shape(x, z):
                    t[x, z] = "V"
    pieces = []
    for p in a.get("blockShapes") or []:
        pieces.append(shape_cells(_int(p.get("kind")), _int(p.get("rotation")), _int(p.get("x")), _int(p.get("z"))))
    piece_cells = {c for cells in pieces for c in cells}
    for c in piece_cells:
        if c in t and t[c] != "V":
            t[c] = "H"
    for (x, z) in piece_cells:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in t and n[0] % 2 == 1 and n[1] % 2 == 1 and t[n] == "H" and n not in piece_cells:
                t[n] = "F"
    # spawns and their clearances
    spawns, reserved = [], set()
    for i in range(_int(a.get("spawnCount"))):
        hx, hz = i in (1, 3), i in (1, 2)
        sx, sz = (W - 1 if hx else 0), (H - 1 if hz else 0)
        if shape:
            step, probe = (-1 if hx else 1), sx
            while 0 <= probe < W and 0 <= probe + step < W and not in_shape(probe, sz) and not in_shape(probe + step, sz):
                probe += 2 * step
            sx = probe if 0 <= probe < W else sx
        spawns.append((sx, sz))
        stepx, stepz = (-1 if hx else 1), (-1 if hz else 1)
        reserved.add((sx, sz))
        for d in range(1, _int(a.get("spawnClearanceRadiusTiles"), 1) + 1):
            reserved.add((sx + stepx * d, sz))
            reserved.add((sx, sz + stepz * d))
    # cells kept free of crates (LevelSimConfig.BuildLevelGenerator)
    bv = a.get("boardVariety") or {}
    crate_free = set()
    for s in a.get("bossSwitches") or []:
        crate_free.add((_int(s["tileX"]), _int(s["tileZ"])))
    for s in bv.get("levelSwitches") or []:
        crate_free.add((_int(s["tileX"]), _int(s["tileZ"])))
    for c in (bv.get("vault") or {}).get("cells") or []:
        crate_free.add((_int(c["tileX"]), _int(c["tileZ"])))
    for r in bv.get("crateFreeRings") or []:
        x0, z0, x1, z1 = (_int(r[k]) for k in ("minX", "minZ", "maxX", "maxZ"))
        for z in range(max(0, z0), min(H - 1, z1) + 1):
            for x in range(max(0, x0), min(W - 1, x1) + 1):
                if x in (x0, x1) or z in (z0, z1):
                    crate_free.add((x, z))
    # stacked cells written over the generated board (level 0 only on every campaign level)
    authored = set()
    for c in a.get("stackedCells") or []:
        if _int(c.get("level")) != 0:
            notes.append("a stacked cell above the ground is not drawn")
            continue
        x, z, tile = _int(c.get("x")), _int(c.get("z")), _int(c.get("tile"))
        t[x, z] = {0: "F", 1: "C", 2: "H", 3: "V"}.get(tile, "F")
        authored.add((x, z))
    # where a random crate can appear: floor, not reserved, not kept free, not an authored cell
    spots = {c for c, v in t.items() if v == "F" and c not in reserved and c not in crate_free and c not in authored}
    marks = []
    roster = a.get("cpuRoster") or []
    cpus = sum(_int(r.get("count")) for r in roster)
    pockets = [(_int(p["tileX"]), _int(p["tileZ"])) for p in a.get("pocketGuards") or []]
    lines = bv.get("rosterLines") or []
    held = sum(1 for ln in lines if _int(ln.get("heldInCage")) == 1)
    late = sum(1 for ln in lines if _int(ln.get("enterOnScrollStep")) > 0)
    if spawns:
        marks.append(("hero", spawns[0]))
    used = set()
    for e in range(1, cpus + 1):  # LevelRoster.SpawnSlotOf
        slot = e if not pockets else (0 if e <= len(pockets) else e - len(pockets))
        if pockets and e <= len(pockets):
            continue
        used.add(slot)
    for i in sorted(used):
        if 0 < i < len(spawns):
            marks.append(("enemy", spawns[i]))
    for p in pockets:
        marks.append(("enemy", p))
    if held or late:
        notes.append("some enemies enter later (from a cage or as the ground scrolls) rather than from a start point")
    for b in a.get("bossEntrance") or []:
        marks.append(("boss", (_int(b["spawnTileX"]), _int(b["spawnTileZ"]))))
    for s in a.get("bossSwitches") or []:
        marks.append(("bswitch", (_int(s["tileX"]), _int(s["tileZ"]))))
    ally = a.get("ally") or {}
    if _int(ally.get("enabled")):
        marks.append(("ally", (_int(ally["spawnTileX"]), _int(ally["spawnTileZ"]))))
    kinds = {0: "cage", 1: "bridge", 2: "gate", 3: "seq", 4: "reverse"}
    for s in bv.get("levelSwitches") or []:
        k = kinds.get(_int(s.get("kind")), "switch")
        marks.append(("sw_" + k, (_int(s["tileX"]), _int(s["tileZ"])), _int(s.get("sequencePosition"))))
    for c in (bv.get("vault") or {}).get("cells") or []:
        marks.append(("vault", (_int(c["tileX"]), _int(c["tileZ"]))))
    objs = []
    for o in a.get("boardObjects") or []:
        k = {0: "egg", 1: "tower", 2: "cage", 10: "shellback"}.get(_int(o.get("kind")), "obj")
        objs.append((k, _int(o["tileX"]), _int(o["tileZ"]), max(1, _int(o.get("sizeTiles"), 1))))
    for tw in a.get("towers") or []:
        objs.append(("tower", _int(tw["tileX"]), _int(tw["tileZ"]), max(1, _int(tw.get("sizeTiles"), 1))))
    later_add, later_remove, shifts = set(), set(), 0
    for step in a.get("mapTimeline") or []:
        cells = {(_int(c["x"]), _int(c["z"])) for c in step.get("tiles") or [] if isinstance(c, dict)}
        k = _int(step.get("kind"))
        if k == 1:
            later_add |= cells
        elif k == 0:
            later_remove |= cells
        else:
            shifts += 1
    if shifts:
        notes.append("rows that shift during the round are not drawn")
    belts = []
    conv = bv.get("conveyor") or {}
    if _int(conv.get("enabled")):
        for ln in conv.get("lanes") or []:
            belts.append((_int(ln["z"]), "E" if _int(ln.get("direction")) == 0 else "W"))
    if _int((bv.get("ring") or {}).get("enabled")):
        notes.append("the ring of ground that falls away from the edge during the round is not drawn")
    if _int((bv.get("scroll") or {}).get("enabled")):
        notes.append("the ground scrolls during the round: this is the starting board")
    mp = a.get("mutationProfile") or {}
    if _int(mp.get("randomCollapseEnabled")):
        notes.append("random tiles fall during the round (never the same ones), so they are not drawn")
    air = a.get("airship") or {}
    airship = _int(air.get("anchorSide")) if _int(air.get("enabled")) else None
    return {"W": W, "H": H, "t": t, "spots": spots, "marks": marks, "objs": objs, "later_add": later_add,
            "later_remove": later_remove, "belts": belts, "airship": airship, "density": _int(a.get("crateDensityPercent")),
            "ring": None}


# ---------------------------------------------------------------- a Castle Road stage
def castle_stage(s, notes, boss=None):
    W, H = _int(s["width"]), _int(s["height"])
    t = {(x, z): "V" for x in range(W) for z in range(H)}
    for c in _cells(s.get("floorCells")):
        t[c] = "F"
    for c in _cells(s.get("wallCells")):
        t[c] = "H"
    marks, objs = [], []
    later_add, later_remove = set(), set()
    for c in _cells(s.get("sealCells")):
        t[c] = "C"  # a blast seal: the round starts it as a crate
    for c in _cells(s.get("socketCells")):
        marks.append(("socket", c))
    for c in _cells(s.get("plateCells")):
        marks.append(("plate", c))
    for c in _cells(s.get("blockCells")):
        marks.append(("block", c))
    for c in _cells(s.get("runeCells")):
        marks.append(("rune", c))
    for c in _cells(s.get("gateCells")):
        marks.append(("cgate", c))
    for c in _cells(s.get("switchCells")):
        marks.append(("sw_switch", c, 0))
    for c in _cells(s.get("towerCells")):
        objs.append(("tower", c[0], c[1], 1))
    if _int(s.get("hasBell")):
        marks.append(("bell", (_int(s["bellX"]), _int(s["bellZ"]))))
    if _int(s.get("hasExit")):
        marks.append(("exit", (_int(s["exitX"]), _int(s["exitZ"]))))
    for item in str(s.get("powerUps") or "").split(";"):
        item = item.strip()
        if item and " " in item:
            _name, xz = item.split(" ", 1)
            x, z = xz.split(",")
            marks.append(("power", (int(x), int(z))))
    for c in _cells(s.get("guardCells")):
        marks.append(("enemy", c))
    for c in _cells(s.get("shellbackCells")):
        marks.append(("shellback", c))
    ring = []
    for c in _cells(s.get("cobblewatchCells")):
        ring.append(c)
        marks.append(("cobble", c))
    for c in _cells(s.get("fightRiseCells")):
        later_add.add(c)
    fin = s.get("finale") or {}
    if _int(fin.get("enabled")):
        for c in _cells(fin.get("openingGuardCells")):
            marks.append(("enemy", c))
        for c in _cells(fin.get("escortGuardCells")) + _cells(fin.get("rageGuardCells")):
            marks.append(("enemy_late", c))
        for c in _cells(fin.get("breakCalmCells")) + _cells(fin.get("breakRageCells")):
            later_remove.add(c)
        for c in _cells(fin.get("partitionCells")):
            later_add.add(c)
        if boss is not None:
            marks.append(("boss", boss))
        if str(fin.get("refugeCells") or "").strip() or str(fin.get("solvedBlockCells") or "").strip():
            notes.append("the final battle's refuge cells and where the blocks rest after the puzzle are not drawn")
    marks.insert(0, ("hero", (_int(s.get("startX")), _int(s.get("startZ")))))
    sockets = set(_cells(s.get("socketCells")))
    ring_walls = []
    if _int(s.get("edgeWall")):  # CastlePuzzle.WallTheVoidRoundTheFloor: void beside floor (8 ways) is a wall, save a socket
        floor = {c for c, v in t.items() if v == "F"} | set(_cells(s.get("sealCells")))
        for z in range(-1, H + 1):
            for x in range(-1, W + 1):
                if (x, z) in sockets or ((x, z) in t and t[x, z] != "V"):
                    continue
                if any((x + dx, z + dz) in floor for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz):
                    if (x, z) in t:
                        t[x, z] = "H"
                    else:
                        ring_walls.append((x, z))
    if _int(s.get("fightCrumbleIntervalTicks")) > 0 or _int(s.get("sectionCrumble")):
        notes.append("during the fight the ground crumbles away from the start towards the exit")
    if _int(s.get("crateLobPeriodTicks")) > 0:
        notes.append("crates are thrown onto the board during the fight")
    pad = bool(ring_walls) or any(c[0] < 0 or c[0] >= W or c[1] < 0 or c[1] >= H for c in ring)
    return {"W": W, "H": H, "t": t, "spots": set(), "marks": marks, "objs": objs, "later_add": later_add,
            "later_remove": later_remove, "belts": [], "airship": None, "density": 0, "ring": pad,
            "ring_walls": ring_walls}


# ---------------------------------------------------------------- drawing
LEGEND = {
    "F": "Floor", "H": "Wall (cannot be blasted)", "C": "Crate (placed by the level)", "V": "Gap (no ground)",
    "spot": "Crate spot: each round, crates fill about {d}% of these at random", "hero": "You start here",
    "enemy": "Enemy", "enemy_late": "Enemy that joins later", "boss": "Boss", "ally": "Helper hero", "bswitch": "Boss switch",
    "sw_cage": "Cage switch", "sw_bridge": "Bridge switch", "sw_gate": "Gate switch", "sw_seq": "Switch in order (1, 2, 3)",
    "sw_reverse": "Reverse switch (turns the belts)", "sw_switch": "Switch", "vault": "Vault (power-ups inside)",
    "egg": "Boss egg", "cage": "Cage", "tower": "Tower", "shellback": "Shellback", "cobble": "Cobblewatch (on the wall)",
    "later_add": "Ground that appears later", "later_remove": "Ground that falls away later", "belt": "Conveyor belt (pushes this way)",
    "socket": "Catch socket (push a block in to make a bridge)", "plate": "Weight plate", "block": "Push block",
    "rune": "Rune", "cgate": "Timed gate", "bell": "Bell", "exit": "Exit", "power": "Power-up", "airship": "Airship side",
}


def _rect(x, y, w, h, fill, stroke=None, sw=0, rx=0, extra=""):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    r = f' rx="{rx}"' if rx else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}"{s}{r}{extra}/>'


def _glyph(kind, cx, cy, n=0):
    """One marker centred on (cx, cy); a tile is CELL wide."""
    r = CELL * 0.34
    o = C["outline"]
    if kind == "hero":
        return f'<circle cx="{cx}" cy="{cy}" r="{r:g}" fill="{C["hero"]}" stroke="#fff" stroke-width="2.4"/>'
    if kind in ("enemy", "enemy_late"):
        dash = ' stroke-dasharray="3 2"' if kind == "enemy_late" else ""
        fill = "none" if kind == "enemy_late" else C["enemy"]
        return f'<circle cx="{cx}" cy="{cy}" r="{r:g}" fill="{fill}" stroke="{C["enemy"] if fill == "none" else o}" stroke-width="2"{dash}/>'
    if kind == "boss":
        d = CELL * 0.44
        return (f'<path d="M{cx} {cy - d} L{cx + d} {cy} L{cx} {cy + d} L{cx - d} {cy} Z" fill="{C["boss"]}" stroke="#fff" '
                f'stroke-width="2"/>')
    if kind == "ally":
        return f'<circle cx="{cx}" cy="{cy}" r="{r:g}" fill="{C["ally"]}" stroke="{C["hero"]}" stroke-width="3"/>'
    if kind == "shellback":
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="{r:g}" ry="{r * 0.75:g}" fill="#3f8f7a" stroke="{o}" stroke-width="1.6"/>'
                f'<path d="M{cx - r * 0.6:g} {cy} H{cx + r * 0.6:g}" stroke="{o}" stroke-width="1.2"/>')
    if kind == "cobble":
        return f'<rect x="{cx - r:g}" y="{cy - r:g}" width="{2 * r:g}" height="{2 * r:g}" fill="{C["enemy"]}" stroke="{o}" stroke-width="1.6" rx="2"/>'
    if kind.startswith("sw_") or kind == "bswitch":
        label = {"sw_cage": "C", "sw_bridge": "B", "sw_gate": "G", "sw_reverse": "R", "bswitch": "!"}.get(kind, "")
        if kind == "sw_seq":
            label = str(n) if n else ""
        txt = (f'<text x="{cx}" y="{cy + 4:g}" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" '
               f'font-size="11" fill="{o}">{label}</text>') if label else ""
        return f'<circle cx="{cx}" cy="{cy}" r="{r:g}" fill="{C["switch"]}" stroke="{o}" stroke-width="1.6"/>{txt}'
    if kind == "plate":
        q = CELL * 0.36
        return f'<rect x="{cx - q:g}" y="{cy - q:g}" width="{2 * q:g}" height="{2 * q:g}" fill="none" stroke="{C["plate"]}" stroke-width="3" rx="2"/>'
    if kind == "block":
        q = CELL * 0.4
        return (f'<rect x="{cx - q:g}" y="{cy - q:g}" width="{2 * q:g}" height="{2 * q:g}" fill="{C["block"]}" stroke="{o}" '
                f'stroke-width="1.6" rx="2"/><path d="M{cx - q * 0.5:g} {cy} H{cx + q * 0.5:g} M{cx} {cy - q * 0.5:g} V{cy + q * 0.5:g}" '
                f'stroke="{o}" stroke-width="1.4"/>')
    if kind == "socket":
        q = CELL * 0.38
        return f'<rect x="{cx - q:g}" y="{cy - q:g}" width="{2 * q:g}" height="{2 * q:g}" fill="none" stroke="{C["block"]}" stroke-width="2.4" stroke-dasharray="3 2"/>'
    if kind == "rune":
        return (f'<circle cx="{cx}" cy="{cy}" r="{r:g}" fill="{C["rune"]}" stroke="{o}" stroke-width="1.4"/>'
                f'<circle cx="{cx}" cy="{cy}" r="{r * 0.4:g}" fill="#e6d6ff"/>')
    if kind == "cgate":
        q = CELL * 0.42
        bars = "".join(f'<path d="M{cx + dx:g} {cy - q:g} V{cy + q:g}" stroke="{C["gate"]}" stroke-width="2.4"/>' for dx in (-q * 0.6, 0, q * 0.6))
        return f'<path d="M{cx - q:g} {cy - q:g} H{cx + q:g}" stroke="{C["gate"]}" stroke-width="2.4"/>{bars}'
    if kind == "bell":
        return (f'<path d="M{cx - r:g} {cy + r * 0.6:g} Q{cx - r:g} {cy - r:g} {cx} {cy - r:g} Q{cx + r:g} {cy - r:g} {cx + r:g} {cy + r * 0.6:g} Z" '
                f'fill="{C["plate"]}" stroke="{o}" stroke-width="1.4"/>')
    if kind == "exit":
        q = CELL * 0.4
        return (f'<path d="M{cx - q:g} {cy - q:g} L{cx + q:g} {cy} L{cx - q:g} {cy + q:g} Z" fill="{C["exit"]}" stroke="#fff" '
                f'stroke-width="1.6"/>')
    if kind == "power":
        return (f'<circle cx="{cx}" cy="{cy}" r="{r * 0.8:g}" fill="{C["power"]}" stroke="{o}" stroke-width="1.4"/>'
                f'<path d="M{cx - r * 0.45:g} {cy} H{cx + r * 0.45:g} M{cx} {cy - r * 0.45:g} V{cy + r * 0.45:g}" stroke="{o}" stroke-width="1.6"/>')
    if kind == "vault":
        q = CELL * 0.5
        return f'<rect x="{cx - q:g}" y="{cy - q:g}" width="{CELL}" height="{CELL}" fill="{C["vault"]}" opacity=".75"/>'
    return ""


def _tile(v, x, y, alt):
    if v == "V":
        return _rect(x, y, CELL, CELL, C["void"])
    if v == "H":
        return (_rect(x, y, CELL, CELL, C["wall_edge"]) + _rect(x + 1.5, y + 1.5, CELL - 3, CELL - 5, C["wall"]) +
                _rect(x + 4, y + 3.5, CELL - 8, CELL - 11, C["wall_top"], rx=1.5))
    base = _rect(x, y, CELL, CELL, C["floor2"] if alt else C["floor"])
    if v == "C":
        base += (_rect(x + 2, y + 2, CELL - 4, CELL - 4, C["crate"], C["crate_edge"], 1.6, 2) +
                 f'<path d="M{x + 4} {y + 4} L{x + CELL - 4} {y + CELL - 4} M{x + CELL - 4} {y + 4} L{x + 4} {y + CELL - 4}" '
                 f'stroke="{C["crate_edge"]}" stroke-width="1.3"/>')
    return base


def svg(b, title):
    """The board `b` (standard_board / castle_stage) as one SVG document."""
    W, H, t = b["W"], b["H"], b["t"]
    pad = CELL if (b.get("ring") or b.get("airship") is not None) else 0
    PW, PH = W * CELL + 2 * pad, H * CELL + 2 * pad
    out = []
    used = set()

    def X(x):
        return pad + x * CELL

    def Y(z):
        return pad + (H - 1 - z) * CELL  # z runs north: row H-1 at the top

    for z in range(H):
        for x in range(W):
            v = t[x, z]
            used.add(v if v != "F" else "F")
            out.append(_tile(v, X(x), Y(z), (x + z) % 2))
    for (x, z) in b.get("ring_walls") or []:
        out.append(_tile("H", X(x), Y(z), 0))
        used.add("H")
    for (x, z) in sorted(b["spots"]):
        out.append(_rect(X(x) + 6, Y(z) + 6, CELL - 12, CELL - 12, "none", C["spot"], 1.6, 2,
                         ' stroke-dasharray="2.5 2" opacity=".9"'))
        used.add("spot")
    for z, d in b["belts"]:
        used.add("belt")
        for x in range(W):
            if t.get((x, z)) != "F":
                continue
            cx, cy = X(x) + CELL / 2, Y(z) + CELL / 2
            s = 1 if d == "E" else -1
            out.append(f'<path d="M{cx - 6 * s:g} {cy - 5:g} L{cx + 4 * s:g} {cy:g} L{cx - 6 * s:g} {cy + 5:g}" fill="none" '
                       f'stroke="{C["belt"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
    for (x, z) in sorted(b["later_remove"]):
        if (x, z) in t:
            used.add("later_remove")
            out.append(_rect(X(x) + 1, Y(z) + 1, CELL - 2, CELL - 2, "none", C["enemy"], 1.6, 0, ' stroke-dasharray="3 2"') +
                       f'<path d="M{X(x) + 5} {Y(z) + 6} l5 5 l-2 4 l6 5" fill="none" stroke="{C["outline"]}" stroke-width="1.2" opacity=".7"/>')
    for (x, z) in sorted(b["later_add"]):
        if (x, z) in t:
            used.add("later_add")
            out.append(_rect(X(x) + 2, Y(z) + 2, CELL - 4, CELL - 4, "none", C["later"], 2, 2, ' stroke-dasharray="3 2"'))
    for k, x, z, size in b["objs"]:
        used.add(k)
        x0, y0, w = X(x), Y(z + size - 1), size * CELL
        if k == "tower":
            out.append(_rect(x0 + 2, y0 + 2, w - 4, w - 4, C["tower"], C["outline"], 1.8, 3) +
                       _rect(x0 + w * 0.3, y0 + w * 0.3, w * 0.4, w * 0.4, "#45474c", rx=2))
        elif k == "cage":
            bars = "".join(f'<path d="M{x0 + 3 + i * (w - 6) / 4:g} {y0 + 3} V{y0 + w - 3}" stroke="{C["cage"]}" stroke-width="2"/>' for i in range(5))
            out.append(_rect(x0 + 3, y0 + 3, w - 6, w - 6, "none", C["cage"], 2.4, 2) + bars)
        elif k == "egg":
            out.append(f'<ellipse cx="{x0 + w / 2:g}" cy="{y0 + w / 2:g}" rx="{w * 0.32:g}" ry="{w * 0.42:g}" fill="{C["egg"]}" '
                       f'stroke="{C["outline"]}" stroke-width="2"/>')
        else:
            out.append(_glyph("shellback", x0 + w / 2, y0 + w / 2))
    for m in b["marks"]:
        k, (x, z) = m[0], m[1]
        n = m[2] if len(m) > 2 else 0
        if k != "cobble" and (x, z) not in t:
            continue
        used.add(k)
        out.append(_glyph(k, X(x) + CELL / 2, Y(z) + CELL / 2, n))
    if b.get("airship") is not None:
        used.add("airship")
        side = b["airship"]  # North, East, South, West
        cx, cy = {0: (PW / 2, pad / 2), 1: (PW - pad / 2, PH / 2), 2: (PW / 2, PH - pad / 2), 3: (pad / 2, PH / 2)}[side]
        out.append(f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{CELL * 0.45 if side in (1, 3) else CELL * 1.2:g}" '
                   f'ry="{CELL * 1.2 if side in (1, 3) else CELL * 0.45:g}" fill="#8a5a2b" stroke="{C["outline"]}" stroke-width="1.8"/>')
    grid = (f'<rect x="{pad}" y="{pad}" width="{W * CELL}" height="{H * CELL}" fill="none" stroke="{C["outline"]}" '
            f'stroke-width="2"/>')
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PW:g} {PH:g}" width="{PW:g}" height="{PH:g}" role="img">'
           f'<title>{html.escape(title)}</title><rect width="{PW:g}" height="{PH:g}" fill="{C["void"]}"/>{"".join(out)}{grid}</svg>')
    return doc, used


def legend_items(used, density):
    """[(key, label)] in a fixed order, only the ones the map uses."""
    order = ["F", "H", "C", "V", "spot", "hero", "enemy", "enemy_late", "boss", "ally", "shellback", "cobble", "egg", "cage",
             "tower", "bswitch", "sw_cage", "sw_bridge", "sw_gate", "sw_seq", "sw_reverse", "sw_switch", "vault", "block",
             "socket", "plate", "rune", "cgate", "bell", "exit", "power", "belt", "later_add", "later_remove", "airship"]
    return [(k, LEGEND[k].replace("{d}", str(density))) for k in order if k in used]


def legend_swatch(key):
    """A 24x24 SVG of one legend key (inline in the page)."""
    if key in ("F", "H", "C", "V"):
        inner = _tile(key, 0, 0, 0)
    elif key == "spot":
        inner = _tile("F", 0, 0, 0) + _rect(6, 6, CELL - 12, CELL - 12, "none", C["spot"], 1.6, 2, ' stroke-dasharray="2.5 2"')
    elif key == "belt":
        inner = _tile("F", 0, 0, 0) + (f'<path d="M6 7 L16 12 L6 17" fill="none" stroke="{C["belt"]}" stroke-width="2.4" '
                                       f'stroke-linecap="round" stroke-linejoin="round"/>')
    elif key == "later_add":
        inner = _rect(0, 0, CELL, CELL, C["void"]) + _rect(2, 2, CELL - 4, CELL - 4, "none", "#ffffff", 2, 2, ' stroke-dasharray="3 2"')
    elif key == "later_remove":
        inner = (_tile("F", 0, 0, 0) + _rect(1, 1, CELL - 2, CELL - 2, "none", C["enemy"], 1.6, 0, ' stroke-dasharray="3 2"') +
                 f'<path d="M5 6 l5 5 l-2 4 l6 5" fill="none" stroke="{C["outline"]}" stroke-width="1.2" opacity=".7"/>')
    elif key in ("tower", "cage", "egg"):
        b = {"W": 1, "H": 1, "t": {(0, 0): "F"}, "spots": set(), "marks": [], "objs": [(key, 0, 0, 1)], "later_add": set(),
             "later_remove": set(), "belts": [], "airship": None}
        return svg(b, "")[0].replace("<title></title>", "").replace('role="img"', 'aria-hidden="true"')
    elif key == "airship":
        inner = f'<ellipse cx="12" cy="12" rx="11" ry="6" fill="#8a5a2b" stroke="{C["outline"]}" stroke-width="1.8"/>'
    elif key == "vault":
        inner = _tile("F", 0, 0, 0) + _rect(0, 0, CELL, CELL, C["vault"], extra=' opacity=".75"')
    else:
        base = _tile("V", 0, 0, 0) if key == "socket" else _tile("F", 0, 0, 0)
        inner = base + _glyph(key, CELL / 2, CELL / 2, 1 if key == "sw_seq" else 0)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELL} {CELL}" width="{CELL}" height="{CELL}" '
            f'aria-hidden="true">{inner}</svg>')


def maps_for(asset_text):
    """[(caption, board, notes)] for one level asset: one board, or one per castle stage."""
    a = unity_yaml.load(asset_text)
    cp = a.get("castlePuzzle") or {}
    out = []
    if _int(cp.get("enabled")):
        stages = cp.get("stages") or []
        W, H = _int(a["gridWidth"]), _int(a["gridHeight"])
        boss = None
        for be in a.get("bossEntrance") or []:
            boss = (_int(be["spawnTileX"]), _int(be["spawnTileZ"]))
        for i, s in enumerate(stages, 1):
            notes = []
            same_grid = _int(s["width"]) == W and _int(s["height"]) == H
            out.append((f"Stage {i}", castle_stage(s, notes, boss if same_grid else None), notes))
        return out
    notes = []
    out.append(("", standard_board(a, notes), notes))
    return out

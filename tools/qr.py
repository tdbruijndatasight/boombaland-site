#!/usr/bin/env python3
"""A small QR code generator (ISO/IEC 18004), pure Python, no dependencies: byte mode, error correction level M,
versions 1-6 (up to 106 bytes). tools/build.py uses it to draw the /get/ page's QR code as an inline SVG at build time,
so the page asks no QR web service for it.

    python3 -I tools/qr.py "https://www.boombaland.com/get/"     # prints the SVG

Checked module-for-module against the `segno` library for every mask (see the commit that added it).
"""
import sys

# Level M, versions 1-6: (error-correction codewords per block, [data codewords of each block])
_EC_M = {1: (10, [16]), 2: (16, [28]), 3: (26, [44]), 4: (18, [32, 32]), 5: (24, [43, 43]), 6: (16, [27, 27, 27, 27])}
_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34]}
_EC_LEVEL_M = 0b00

# GF(256) with the QR polynomial x^8 + x^4 + x^3 + x^2 + 1
_EXP, _LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i], _LOG[_x] = _x, _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _rs_ec(data, n):
    """The n Reed-Solomon error-correction codewords of one block."""
    gen = [1]
    for i in range(n):
        nxt = [0] * (len(gen) + 1)
        for j, g in enumerate(gen):
            nxt[j] ^= g
            if g:
                nxt[j + 1] ^= _EXP[_LOG[g] + i]
        gen = nxt
    rem = list(data) + [0] * n
    for i in range(len(data)):
        c = rem[i]
        if c:
            for j in range(1, len(gen)):
                if gen[j]:
                    rem[i + j] ^= _EXP[_LOG[gen[j]] + _LOG[c]]
    return rem[len(data):]


def _codewords(data, version):
    ec_n, blocks = _EC_M[version]
    cap = sum(blocks)
    bits = [int(b) for b in "0100" + format(len(data), "08b") + "".join(format(c, "08b") for c in data)]
    bits += [0] * min(4, cap * 8 - len(bits))
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    while len(words) < cap:
        words.append(pad[(len(words) - len(bits) // 8) % 2])
    split, i = [], 0
    for b in blocks:
        split.append(words[i:i + b])
        i += b
    ecs = [_rs_ec(b, ec_n) for b in split]
    out = [b[k] for k in range(max(blocks)) for b in split if k < len(b)]
    return out + [e[k] for k in range(ec_n) for e in ecs]


def _format_bits(mask):
    v = (_EC_LEVEL_M << 3) | mask
    r = v << 10
    for i in range(14, 9, -1):
        if r & (1 << i):
            r ^= 0x537 << (i - 10)
    return ((v << 10) | r) ^ 0x5412


_MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def _base(version):
    """The function patterns: (modules, reserved) as size x size grids."""
    n = 17 + 4 * version
    m = [[0] * n for _ in range(n)]
    res = [[False] * n for _ in range(n)]

    def put(r, c, v):
        m[r][c], res[r][c] = v, True

    for (r0, c0) in ((0, 0), (0, n - 7), (n - 7, 0)):
        for r in range(-1, 8):
            for c in range(-1, 8):
                rr, cc = r0 + r, c0 + c
                if 0 <= rr < n and 0 <= cc < n:
                    on = 0 <= r <= 6 and 0 <= c <= 6 and (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                    put(rr, cc, int(on))
    for i in range(8, n - 8):
        put(6, i, int(i % 2 == 0))
        put(i, 6, int(i % 2 == 0))
    for r in _ALIGN[version]:
        for c in _ALIGN[version]:
            if res[r][c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    put(r + dr, c + dc, int(max(abs(dr), abs(dc)) != 1))
    for i in range(9):  # format areas (filled per mask)
        for (r, c) in ((8, i), (i, 8)):
            if not res[r][c]:
                put(r, c, 0)
    for i in range(8):
        put(8, n - 1 - i, 0)
        put(n - 1 - i, 8, 0)
    put(n - 8, 8, 1)  # the dark module
    return m, res


def _place(m, res, words):
    n = len(m)
    bits = [(w >> (7 - i)) & 1 for w in words for i in range(8)]
    k, c, up = 0, n - 1, True
    while c > 0:
        if c == 6:
            c -= 1
        for r in (range(n - 1, -1, -1) if up else range(n)):
            for cc in (c, c - 1):
                if not res[r][cc]:
                    m[r][cc] = bits[k] if k < len(bits) else 0
                    k += 1
        up = not up
        c -= 2


def _apply(m, res, mask):
    n = len(m)
    out = [row[:] for row in m]
    for r in range(n):
        for c in range(n):
            if not res[r][c] and _MASKS[mask](r, c):
                out[r][c] ^= 1
    f = _format_bits(mask)
    fb = [(f >> i) & 1 for i in range(15)]  # bit 0 = least significant
    for i in range(15):
        b = fb[i]
        # around the top-left finder
        if i < 6:
            out[i][8] = b
        elif i < 8:
            out[i + 1][8] = b
        else:
            out[8][14 - i if i > 8 else 7] = b
        # split between the other two finders
        if i < 8:
            out[8][n - 1 - i] = b
        else:
            out[n - 15 + i][8] = b
    out[n - 8][8] = 1
    return out


def _penalty(m):
    n = len(m)
    p = 0
    for grid in (m, [list(col) for col in zip(*m)]):
        for row in grid:
            run, prev = 0, None
            for v in row:
                if v == prev:
                    run += 1
                else:
                    if run >= 5:
                        p += run - 2
                    run, prev = 1, v
            if run >= 5:
                p += run - 2
            s = "".join(map(str, row))
            for pat in ("10111010000", "00001011101"):
                i = s.find(pat)
                while i != -1:
                    p += 40
                    i = s.find(pat, i + 1)
    for r in range(n - 1):
        for c in range(n - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                p += 3
    dark = sum(map(sum, m)) * 100 // (n * n)
    return p + abs(dark - 50) // 5 * 10


def matrix(text, version=None, mask=None):
    """The QR code of `text` (UTF-8, byte mode, level M) as rows of 0/1, without the quiet zone."""
    data = text.encode("utf-8")
    if version is None:
        version = next((v for v in _EC_M if sum(_EC_M[v][1]) * 8 >= 12 + 8 * len(data)), None)
        if version is None:
            raise ValueError(f"too long for versions 1-6 at level M: {len(data)} bytes")
    base, res = _base(version)
    _place(base, res, _codewords(data, version))
    if mask is not None:
        return _apply(base, res, mask)
    return min((_apply(base, res, k) for k in range(8)), key=_penalty)


def svg(text, quiet=4, title=None):
    """An inline SVG of the QR code: one path, dark modules on a white square, scaled by CSS (viewBox in modules)."""
    m = matrix(text)
    n = len(m) + 2 * quiet
    d = []
    for r, row in enumerate(m):
        c = 0
        while c < len(row):
            if row[c]:
                s = c
                while c < len(row) and row[c]:
                    c += 1
                d.append(f"M{s + quiet} {r + quiet}h{c - s}v1h-{c - s}z")
            else:
                c += 1
    t = f"<title>{title}</title>" if title else ""
    return (f'<svg class="qr" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n * 6}" height="{n * 6}" '
            f'role="img" shape-rendering="crispEdges"{" aria-label=" + chr(34) + title + chr(34) if title else ""}>{t}'
            f'<rect width="{n}" height="{n}" fill="#fff"/><path fill="#000" d="{"".join(d)}"/></svg>')


if __name__ == "__main__":
    print(svg(sys.argv[1] if len(sys.argv) > 1 else "https://www.boombaland.com/get/"))

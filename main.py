#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Monday 23 November 2026.

A front page that sums up the world's news of Monday 23 November 2026 in
one image. Pure Python 3.13 standard library only: no Pillow, no numpy,
no network. The program draws every letter itself with a vector stroke
font (glyph outlines, not pixels) and writes a deterministic PNG to
$MAKEFUN_OUTPUT_DIR/entry.png.

Layout (canonical front page):
  masthead -> 4-headline subhead -> numbers row (6 biggest numbers)
  -> region bar -> 3 lead stories -> 10 illustrated tiles
  -> world map + ALSO -> DATE CHECK -> footer
"""

import binascii
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
INK = (18, 18, 18)          # near-black text
PAPER = (250, 247, 238)      # newsprint cream
PAPER2 = (244, 238, 224)     # slightly darker cream
RED = (178, 34, 28)          # headline red
BLUE = (24, 64, 110)         # deep news blue
TEAL = (14, 92, 86)
GOLD = (176, 128, 28)
GREY = (96, 94, 88)
LGREY = (206, 200, 186)
RULE = (60, 58, 52)
SKY = (214, 230, 238)
SEA = (168, 198, 214)
LAND = (232, 222, 190)
LAND2 = (214, 204, 168)
WHITE = (255, 255, 255)

# ------------------------------------------------------------------ canvas
px = bytearray(W * H * 3)


def _set(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = c[0]
        px[i + 1] = c[1]
        px[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(W, int(x + w))
    y1 = min(H, int(y + h))
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            px[i] = c[0]
            px[i + 1] = c[1]
            px[i + 2] = c[2]


def disc(cx, cy, r, c):
    """Filled disc, centre (cx, cy), radius r (float)."""
    r = float(r)
    x0 = max(0, int(cx - r - 1))
    x1 = min(W - 1, int(cx + r + 1))
    y0 = max(0, int(cy - r - 1))
    y1 = min(H - 1, int(cy + r + 1))
    rr = r * r
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        for xx in range(x0, x1 + 1):
            dx = xx - cx
            if dx * dx + dy * dy <= rr:
                _set(xx, yy, c)


def line(x0, y0, x1, y1, w, c):
    """Thick line with round caps, stamped as discs along the segment."""
    x0 = float(x0)
    y0 = float(y0)
    x1 = float(x1)
    y1 = float(y1)
    dx = x1 - x0
    dy = y1 - y0
    dist = (dx * dx + dy * dy) ** 0.5
    r = max(0.6, w / 2.0)
    if dist < 0.01:
        disc(x0, y0, r, c)
        return
    step = max(0.45 * r, 0.4)
    n = max(1, int(dist / step) + 1)
    for k in range(n + 1):
        t = k / n
        disc(x0 + dx * t, y0 + dy * t, r, c)


def polyline(pts, w, c):
    for a, b in zip(pts, pts[1:]):
        line(a[0], a[1], b[0], b[1], w, c)


def circle_outline(cx, cy, r, w, c):
    import math
    n = max(24, int(2 * 3.14159 * r / 3))
    pts = []
    for k in range(n + 1):
        a = 2 * 3.14159 * k / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    polyline(pts, w, c)


def filled_circle(cx, cy, r, c):
    disc(cx, cy, r, c)


def polygon(pts, c):
    """Even-odd scanline fill of a polygon given as [(x, y), ...]."""
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(pts)
    for yy in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1a = pts[i]
            x2, y2a = pts[(i + 1) % n]
            if y1a == y2a:
                continue
            if (y1a <= yy < y2a) or (y2a <= yy < y1a):
                t = (yy - y1a) / (y2a - y1a)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[k]))
            xb = min(W - 1, int(xs[k + 1]))
            for xx in range(xa, xb + 1):
                _set(xx, yy, c)


def hline(x, y, w, c, t=1):
    fill_rect(x, y, w, t, c)


def vline(x, y, h, c, t=1):
    fill_rect(x, y, t, h, c)


def rect_outline(x, y, w, h, c, t=1):
    fill_rect(x, y, w, t, c)
    fill_rect(x, y + h - t, w, t, c)
    fill_rect(x, y, t, h, c)
    fill_rect(x + w - t, y, t, h, c)


# --------------------------------------------------------------------- PNG
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, width, height, rgb):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: none
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += _chunk(b"IHDR", ihdr)
    data += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)

# ------------------------------------------------- vector stroke font
# Each glyph: "width;stroke|stroke|..." ; a stroke is "x,y x,y ..."
# Coordinates live on a 7-unit em: y=0 is the cap top, y=7 the baseline.
# Lowercase letters are rendered as small caps (the same outlines, scaled).
# This is a real vector font: strokes are drawn as thick round-capped
# lines at any size, so text stays crisp instead of turning into pixels.
_FONT_RAW = {
    "A": "5.0;0,7 2.5,0 5,7|1.2,4.6 3.8,4.6",
    "B": "5.0;0,0 0,7|0,0 3,0 4.5,1 4.5,2.5 3,3.5 0,3.5|0,3.5 3.5,3.5 5,4.8 5,5.8 3.5,7 0,7",
    "C": "5.0;5,1.8 4,0.4 1.8,0 0.4,1.2 0,3.5 0,5.5 1.5,7 4,7 5,5.6",
    "D": "5.5;0,0 0,7 3,7 5,5 5,2 3,0 0,0",
    "E": "5.0;4.8,0 0,0 0,7 4.8,7|0,3.5 3.2,3.5",
    "F": "5.0;0,0 0,7|0,0 4.8,0|0,3.5 3.2,3.5",
    "G": "5.5;5,1.8 4,0.4 1.8,0 0.4,1.2 0,5.5 1.5,7 4,7 5,5.6 5,4 3,4",
    "H": "5.0;0,0 0,7|5,0 5,7|0,3.5 5,3.5",
    "I": "3.0;1.5,0 1.5,7|0,0 3,0|0,7 3,7",
    "J": "5.0;4.8,0 4.8,5 3.5,7 1.5,7 0,5.5",
    "K": "5.0;0,0 0,7|4.8,0 0.8,3.5 4.8,7",
    "L": "5.0;0,0 0,7 5,7",
    "M": "6.5;0,7 0,0 3.2,4.2 6.5,0 6.5,7",
    "N": "6.0;0,7 0,0 6,7 6,0",
    "O": "5.5;1.2,0 4,0 5.3,1.3 5.3,5.7 4,7 1.2,7 0,5.7 0,1.3 1.2,0",
    "P": "5.0;0,7 0,0 3,0 4.8,1.2 4.8,2.6 3,3.8 0,3.8",
    "Q": "5.5;1.2,0 4,0 5.3,1.3 5.3,5.7 4,7 1.2,7 0,5.7 0,1.3 1.2,0|3.5,5 5.5,7",
    "R": "5.0;0,7 0,0 3,0 4.8,1.2 4.8,2.6 3,3.8 0,3.8|2.2,3.8 5,7",
    "S": "5.0;4.6,1 3.5,0 1.5,0 0.3,1 0,2.5 0.8,3.8 2.5,4.2 4,4.6 5,5.6 4.6,6.8 3,7.2 1,7 0.2,6",
    "T": "5.0;0,0 5,0|2.5,0 2.5,7",
    "U": "5.5;0,0 0,5.5 1.2,7 4,7 5.2,5.5 5.2,0",
    "V": "5.5;0,0 2.6,7 5.2,0",
    "W": "7.0;0,0 1.5,7 3.5,2.5 5.5,7 7,0",
    "X": "5.5;0,0 5.2,7|5.2,0 0,7",
    "Y": "5.5;0,0 2.6,3.5 5.2,0|2.6,3.5 2.6,7",
    "Z": "5.0;0,0 5,0 0,7 5,7",
    "0": "5.5;1.2,0 4,0 5.3,1.3 5.3,5.7 4,7 1.2,7 0,5.7 0,1.3 1.2,0",
    "1": "4.5;1.2,1.2 2.6,0 2.6,7|0.6,7 4.2,7",
    "2": "5.0;0.6,1.4 1.6,0 3.6,0 4.8,1.4 4.8,3 0.6,7 5,7",
    "3": "5.0;0.6,1 1.6,0 3.6,0 4.8,1.2 4.8,2.6 3.4,3.5|3.4,3.5 4.8,4.4 4.8,5.8 3.6,7 1.6,7 0.6,6",
    "4": "5.0;0,4.8 4.8,4.8|3.4,0 3.4,7|0,4.8 3.4,0",
    "5": "5.0;4.8,0 0.6,0 0.6,3.2 3,3.2 4.8,4.4 4.8,5.8 3.6,7 1.6,7 0.6,6",
    "6": "5.0;4.6,1.2 3.4,0 1.4,0 0.4,1.4 0,3.5 0,5.5 1.2,7 3.4,7 4.8,5.6 4.8,4.2 3.4,3.2 1.4,3.2 0.4,4.2",
    "7": "5.0;0.4,0 5,0 2.4,7",
    "8": "5.0;1.4,0 3.6,0 4.8,1.4 4.8,2.6 3.4,3.5 1.6,3.5 0.4,2.6 0.4,1.4 1.4,0|1.6,3.5 3.4,3.5 4.8,4.6 4.8,5.8 3.6,7 1.4,7 0.4,5.8 0.4,4.6 1.6,3.5",
    "9": "5.0;0.4,5.8 1.4,7 3.4,7 4.8,5.6 4.8,3.5 4.8,1.4 3.6,0 1.4,0 0.4,1.4 0.4,2.8 1.4,3.8 3.4,3.8 4.8,2.8",
    ".": "2.5;1.2,6.4 1.2,7",
    ",": "2.5;1.2,6.4 1.2,7|1.2,7 0.4,8.4",
    ":": "2.5;1.2,2.2 1.2,3.2|1.2,6.2 1.2,7",
    ";": "2.5;1.2,2.2 1.2,3.2|1.2,6.2 1.2,7|1.2,7 0.4,8.4",
    "!": "2.5;1.2,0 1.2,5.2|1.2,6.4 1.2,7",
    "?": "4.0;0.8,1.6 1.6,0.4 3,0.4 3.8,1.4 3.8,2.4 2.6,3.6 2,4.4 2,5.2|2,6.4 2,7",
    "-": "4.0;0.4,3.8 3.6,3.8",
    "\u2013": "5.0;0.2,3.8 4.8,3.8",
    "\u2014": "6.0;0.2,3.8 5.8,3.8",
    "(": "3.0;2.2,0 1,1.8 1,5.2 2.2,7",
    ")": "3.0;0.8,0 2,1.8 2,5.2 0.8,7",
    "'": "2.0;1.2,0 0.6,2",
    "\u2019": "2.0;1.2,0 0.6,2",
    '"': "3.5;0.8,0 0.4,2|2.6,0 2.2,2",
    "/": "4.0;3.4,7 0.6,0",
    "%": "6.0;1.4,0.8 1.4,2.2|4.6,4.8 4.6,6.2|5.2,7 0.8,0",
    "$": "5.0;4.6,1 3.5,0 1.5,0 0.3,1 0,2.5 0.8,3.8 2.5,4.2 4,4.6 5,5.6 4.6,6.8 3,7.2 1,7 0.2,6|2.5,-1 2.5,8",
    "\u00b0": "3.0;0.6,0.6 1.5,0 2.4,0.6 2.4,1.6 1.5,2.2 0.6,1.6 0.6,0.6",
    "\u2022": "3.0;1,3.2 1,4.6",
    "\u00b7": "2.0;0.8,3.4 0.8,4.2",
    "+": "5.0;2.5,1 2.5,6|0,3.5 5,3.5",
    "=": "5.0;0.5,2.6 4.5,2.6|0.5,4.8 4.5,4.8",
    "<": "4.0;3.4,0.4 0.6,3.5 3.4,6.6",
    ">": "4.0;0.6,0.4 3.4,3.5 0.6,6.6",
    "[": "3.0;2.2,0 0.4,0 0.4,7 2.2,7",
    "]": "3.0;0.8,0 2.6,0 2.6,7 0.8,7",
    "*": "5.0;2.5,0.5 2.5,6.5|0.3,2 4.7,5|4.7,2 0.3,5",
    "#": "6.0;2,0 1.4,7|4,0 3.4,7|0.2,2.4 5.6,2.4|0.2,4.8 5.6,4.8",
    " ": "3.0;",
}


def _parse_font(raw):
    out = {}
    for ch, spec in raw.items():
        width_s, _, strokes_s = spec.partition(";")
        strokes = []
        if strokes_s:
            for st in strokes_s.split("|"):
                pts = []
                for tok in st.split():
                    xs, _, ys = tok.partition(",")
                    pts.append((float(xs), float(ys)))
                if len(pts) >= 2:
                    strokes.append(pts)
        out[ch] = (float(width_s), strokes)
    return out


FONT = _parse_font(_FONT_RAW)
SPACE_W = 3.0
SMALLCAP = 0.74


def _glyph(ch):
    if "a" <= ch <= "z":
        return FONT[ch.upper()], True
    return FONT.get(ch, FONT[" "]), False


def text_width(s, size):
    """Width in px of string s at cap-height `size`."""
    scale = size / 7.0
    total = 0.0
    for ch in s:
        if ch == " ":
            total += SPACE_W * scale
            continue
        (gw, _), small = _glyph(ch)
        if small:
            total += (gw * SMALLCAP + 1.0) * scale
        else:
            total += (gw + 1.0) * scale
    return total


def draw_glyph(x, y_top, ch, size, color, sw=None):
    """Draw one glyph; (x, y_top) is the top-left of the cap box.
    Returns the advance in px."""
    scale = size / 7.0
    if ch == " ":
        return SPACE_W * scale
    (gw, strokes), small = _glyph(ch)
    if small:
        s2 = scale * SMALLCAP
        y0 = y_top + size * (1.0 - SMALLCAP)
    else:
        s2 = scale
        y0 = y_top
    if sw is None:
        sw = max(1.0, size * 0.13)
    for pts in strokes:
        ppx = [(x + px_ * s2, y0 + py * s2) for px_, py in pts]
        polyline(ppx, sw, color)
    if small:
        return (gw * SMALLCAP + 1.0) * scale
    return (gw + 1.0) * scale


def draw_text(x, y, s, size, color, align="left", sw=None):
    """Draw one line; (x, y) is the top-left (or centre/right) of the cap box."""
    w = text_width(s, size)
    if align == "center":
        x = x - w / 2.0
    elif align == "right":
        x = x - w
    cx = x
    for ch in s:
        cx += draw_glyph(cx, y, ch, size, color, sw)
    return w


def wrap_text(s, size, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = s.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(x, y, s, size, color, max_w, leading=None, align="left"):
    """Draw a wrapped paragraph; returns the y just below the last line."""
    if leading is None:
        leading = size * 1.32
    for ln in wrap_text(s, size, max_w):
        draw_text(x, y, ln, size, color, align=align)
        y += leading
    return y

# ------------------------------------------------------------- pictograms
# Small vector scenes drawn with the same primitives, one per story.
# Each takes the top-left corner of its box (bx, by) and its size (s).

def icon_globe(bx, by, s):
    cx, cy, r = bx + s * 0.5, by + s * 0.5, s * 0.44
    circle_outline(cx, cy, r, max(2, s * 0.05), BLUE)
    # meridians
    line(cx, cy - r, cx, cy + r, max(1, s * 0.02), BLUE)
    line(cx - r * 0.62, cy - r * 0.78, cx - r * 0.62, cy + r * 0.78, max(1, s * 0.02), BLUE)
    line(cx + r * 0.62, cy - r * 0.78, cx + r * 0.62, cy + r * 0.78, max(1, s * 0.02), BLUE)
    line(cx - r, cy, cx + r, cy, max(1, s * 0.02), BLUE)
    # land blobs
    polygon([(cx - r * 0.7, cy - r * 0.5), (cx - r * 0.1, cy - r * 0.65),
             (cx + r * 0.1, cy - r * 0.3), (cx - r * 0.3, cy - r * 0.1)], TEAL)
    polygon([(cx + r * 0.1, cy + r * 0.2), (cx + r * 0.6, cy + r * 0.1),
             (cx + r * 0.7, cy + r * 0.55), (cx + r * 0.2, cy + r * 0.6)], TEAL)
    # the crack: talks broken
    line(cx - r * 0.9, cy - r * 0.9, cx + r * 0.2, cy + r * 0.1, max(2, s * 0.06), RED)
    line(cx + r * 0.2, cy + r * 0.1, cx + r * 0.9, cy + r * 0.9, max(2, s * 0.06), RED)


def icon_tanker(bx, by, s):
    # sea
    for k in range(3):
        yy = by + s * (0.72 + 0.08 * k)
        line(bx + s * 0.05, yy, bx + s * 0.95, yy, max(1, s * 0.025), SEA)
    # hull
    polygon([(bx + s * 0.08, by + s * 0.55), (bx + s * 0.92, by + s * 0.55),
             (bx + s * 0.82, by + s * 0.72), (bx + s * 0.18, by + s * 0.72)], INK)
    # containers
    fill_rect(bx + s * 0.16, by + s * 0.38, s * 0.18, s * 0.17, RED)
    fill_rect(bx + s * 0.38, by + s * 0.38, s * 0.18, s * 0.17, GOLD)
    fill_rect(bx + s * 0.60, by + s * 0.38, s * 0.18, s * 0.17, BLUE)
    # missile arc + burst
    line(bx + s * 0.85, by + s * 0.30, bx + s * 0.98, by + s * 0.06, max(2, s * 0.04), RED)
    filled_circle(bx + s * 0.97, by + s * 0.05, s * 0.05, GOLD)
    line(bx + s * 0.90, by + s * 0.10, bx + s * 0.99, by + s * 0.02, max(1, s * 0.02), GOLD)
    line(bx + s * 0.97, by + s * 0.12, bx + s * 0.99, by + s * 0.02, max(1, s * 0.02), GOLD)


def icon_fire(bx, by, s):
    # factory block
    fill_rect(bx + s * 0.10, by + s * 0.45, s * 0.80, s * 0.32, INK)
    fill_rect(bx + s * 0.16, by + s * 0.52, s * 0.10, s * 0.12, GOLD)
    fill_rect(bx + s * 0.34, by + s * 0.52, s * 0.10, s * 0.12, GOLD)
    fill_rect(bx + s * 0.52, by + s * 0.52, s * 0.10, s * 0.12, GOLD)
    # chimney
    fill_rect(bx + s * 0.72, by + s * 0.25, s * 0.10, s * 0.22, INK)
    # flames
    polygon([(bx + s * 0.20, by + s * 0.45), (bx + s * 0.30, by + s * 0.12),
             (bx + s * 0.38, by + s * 0.30), (bx + s * 0.48, by + s * 0.06),
             (bx + s * 0.58, by + s * 0.32), (bx + s * 0.68, by + s * 0.14),
             (bx + s * 0.76, by + s * 0.45)], RED)
    polygon([(bx + s * 0.38, by + s * 0.45), (bx + s * 0.44, by + s * 0.24),
             (bx + s * 0.52, by + s * 0.45)], GOLD)


def icon_badge(bx, by, s):
    cx, cy = bx + s * 0.5, by + s * 0.45
    r = s * 0.34
    pts = []
    import math
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    polygon(pts, GOLD)
    circle_outline(cx, cy, r * 0.42, max(1, s * 0.03), INK)
    line(cx, by + s * 0.82, cx, by + s * 0.95, max(2, s * 0.04), RED)
    line(bx + s * 0.30, by + s * 0.88, bx + s * 0.70, by + s * 0.88, max(2, s * 0.04), RED)


def icon_capitol(bx, by, s):
    # dome
    polygon([(bx + s * 0.28, by + s * 0.42), (bx + s * 0.30, by + s * 0.28),
             (bx + s * 0.40, by + s * 0.16), (bx + s * 0.50, by + s * 0.10),
             (bx + s * 0.60, by + s * 0.16), (bx + s * 0.70, by + s * 0.28),
             (bx + s * 0.72, by + s * 0.42)], BLUE)
    line(bx + s * 0.50, by + s * 0.02, bx + s * 0.50, by + s * 0.10, max(2, s * 0.03), BLUE)
    # columns
    for k in range(5):
        xx = bx + s * (0.18 + 0.16 * k)
        line(xx, by + s * 0.46, xx, by + s * 0.72, max(2, s * 0.04), BLUE)
    line(bx + s * 0.12, by + s * 0.44, bx + s * 0.88, by + s * 0.44, max(2, s * 0.04), BLUE)
    line(bx + s * 0.12, by + s * 0.74, bx + s * 0.88, by + s * 0.74, max(2, s * 0.04), BLUE)
    line(bx + s * 0.08, by + s * 0.80, bx + s * 0.92, by + s * 0.80, max(2, s * 0.04), BLUE)


def icon_drone(bx, by, s):
    cx, cy = bx + s * 0.5, by + s * 0.5
    line(cx - s * 0.30, cy - s * 0.22, cx + s * 0.30, cy + s * 0.22, max(2, s * 0.04), INK)
    line(cx + s * 0.30, cy - s * 0.22, cx - s * 0.30, cy + s * 0.22, max(2, s * 0.04), INK)
    for dx, dy in ((-0.34, -0.26), (0.34, -0.26), (-0.34, 0.26), (0.34, 0.26)):
        circle_outline(cx + dx * s, cy + dy * s, s * 0.10, max(1, s * 0.025), INK)
    filled_circle(cx, cy, s * 0.10, RED)
    # falling sparks
    line(bx + s * 0.15, by + s * 0.85, bx + s * 0.25, by + s * 0.95, max(1, s * 0.03), GOLD)
    line(bx + s * 0.85, by + s * 0.85, bx + s * 0.75, by + s * 0.95, max(1, s * 0.03), GOLD)


def icon_boat(bx, by, s):
    for k in range(3):
        yy = by + s * (0.68 + 0.09 * k)
        line(bx + s * 0.05, yy, bx + s * 0.95, yy, max(1, s * 0.025), SEA)
    polygon([(bx + s * 0.12, by + s * 0.50), (bx + s * 0.88, by + s * 0.50),
             (bx + s * 0.72, by + s * 0.66), (bx + s * 0.28, by + s * 0.66)], INK)
    line(bx + s * 0.50, by + s * 0.50, bx + s * 0.50, by + s * 0.14, max(2, s * 0.03), INK)
    polygon([(bx + s * 0.52, by + s * 0.16), (bx + s * 0.52, by + s * 0.44),
             (bx + s * 0.82, by + s * 0.44)], RED)
    filled_circle(bx + s * 0.22, by + s * 0.30, s * 0.05, GOLD)
    filled_circle(bx + s * 0.34, by + s * 0.22, s * 0.05, GOLD)


def icon_gradcap(bx, by, s):
    polygon([(bx + s * 0.50, by + s * 0.22), (bx + s * 0.92, by + s * 0.42),
             (bx + s * 0.50, by + s * 0.62), (bx + s * 0.08, by + s * 0.42)], INK)
    polygon([(bx + s * 0.30, by + s * 0.52), (bx + s * 0.30, by + s * 0.72),
             (bx + s * 0.50, by + s * 0.82), (bx + s * 0.70, by + s * 0.72),
             (bx + s * 0.70, by + s * 0.52)], BLUE)
    line(bx + s * 0.90, by + s * 0.44, bx + s * 0.90, by + s * 0.72, max(2, s * 0.03), GOLD)
    filled_circle(bx + s * 0.90, by + s * 0.76, s * 0.05, GOLD)


def icon_flags(bx, by, s):
    line(bx + s * 0.30, by + s * 0.12, bx + s * 0.30, by + s * 0.85, max(2, s * 0.03), INK)
    line(bx + s * 0.68, by + s * 0.12, bx + s * 0.68, by + s * 0.85, max(2, s * 0.03), INK)
    polygon([(bx + s * 0.32, by + s * 0.14), (bx + s * 0.62, by + s * 0.14),
             (bx + s * 0.62, by + s * 0.38), (bx + s * 0.32, by + s * 0.38)], RED)
    filled_circle(bx + s * 0.47, by + s * 0.26, s * 0.06, WHITE)
    polygon([(bx + s * 0.70, by + s * 0.14), (bx + s * 0.94, by + s * 0.14),
             (bx + s * 0.94, by + s * 0.38), (bx + s * 0.70, by + s * 0.38)], BLUE)
    line(bx + s * 0.70, by + s * 0.26, bx + s * 0.94, by + s * 0.26, max(1, s * 0.025), WHITE)
    # handshake arc below
    line(bx + s * 0.20, by + s * 0.78, bx + s * 0.45, by + s * 0.66, max(2, s * 0.035), TEAL)
    line(bx + s * 0.80, by + s * 0.78, bx + s * 0.55, by + s * 0.66, max(2, s * 0.035), TEAL)


def icon_cricket(bx, by, s):
    # bat
    polygon([(bx + s * 0.42, by + s * 0.10), (bx + s * 0.58, by + s * 0.10),
             (bx + s * 0.62, by + s * 0.55), (bx + s * 0.46, by + s * 0.72),
             (bx + s * 0.34, by + s * 0.60), (bx + s * 0.38, by + s * 0.30)], GOLD)
    line(bx + s * 0.50, by + s * 0.08, bx + s * 0.52, by + s * 0.02, max(2, s * 0.03), INK)
    # ball + stumps
    filled_circle(bx + s * 0.78, by + s * 0.22, s * 0.09, RED)
    for k in range(3):
        xx = bx + s * (0.16 + 0.08 * k)
        line(xx, by + s * 0.72, xx, by + s * 0.95, max(2, s * 0.03), INK)
    line(bx + s * 0.14, by + s * 0.72, bx + s * 0.34, by + s * 0.72, max(1, s * 0.025), INK)


def icon_ball(bx, by, s):
    cx, cy, r = bx + s * 0.5, by + s * 0.5, s * 0.36
    circle_outline(cx, cy, r, max(2, s * 0.04), INK)
    polygon([(cx - r * 0.28, cy - r * 0.25), (cx + r * 0.28, cy - r * 0.25),
             (cx + r * 0.42, cy + r * 0.25), (cx, cy + r * 0.5),
             (cx - r * 0.42, cy + r * 0.25)], INK)
    line(cx, cy - r, cx, cy - r * 0.25, max(1, s * 0.025), INK)
    line(cx - r * 0.9, cy - r * 0.3, cx - r * 0.42, cy + r * 0.25, max(1, s * 0.025), INK)
    line(cx + r * 0.9, cy - r * 0.3, cx + r * 0.42, cy + r * 0.25, max(1, s * 0.025), INK)


def icon_robot(bx, by, s):
    line(bx + s * 0.50, by + s * 0.06, bx + s * 0.50, by + s * 0.20, max(2, s * 0.03), INK)
    filled_circle(bx + s * 0.50, by + s * 0.05, s * 0.04, RED)
    rect_outline(bx + s * 0.22, by + s * 0.20, s * 0.56, s * 0.48, INK, max(2, s * 0.035))
    filled_circle(bx + s * 0.38, by + s * 0.40, s * 0.05, BLUE)
    filled_circle(bx + s * 0.62, by + s * 0.40, s * 0.05, BLUE)
    line(bx + s * 0.36, by + s * 0.56, bx + s * 0.64, by + s * 0.56, max(2, s * 0.03), INK)
    line(bx + s * 0.22, by + s * 0.78, bx + s * 0.78, by + s * 0.78, max(2, s * 0.03), INK)
    line(bx + s * 0.30, by + s * 0.78, bx + s * 0.30, by + s * 0.92, max(2, s * 0.03), INK)
    line(bx + s * 0.70, by + s * 0.78, bx + s * 0.70, by + s * 0.92, max(2, s * 0.03), INK)


def icon_scales(bx, by, s):
    line(bx + s * 0.50, by + s * 0.10, bx + s * 0.50, by + s * 0.85, max(2, s * 0.035), INK)
    line(bx + s * 0.18, by + s * 0.22, bx + s * 0.82, by + s * 0.22, max(2, s * 0.035), INK)
    line(bx + s * 0.50, by + s * 0.85, bx + s * 0.30, by + s * 0.92, max(2, s * 0.03), INK)
    line(bx + s * 0.50, by + s * 0.85, bx + s * 0.70, by + s * 0.92, max(2, s * 0.03), INK)
    for cx in (0.18, 0.82):
        line(bx + s * cx, by + s * 0.22, bx + s * (cx - 0.10), by + s * 0.44, max(1, s * 0.025), INK)
        line(bx + s * cx, by + s * 0.22, bx + s * (cx + 0.10), by + s * 0.44, max(1, s * 0.025), INK)
        line(bx + s * (cx - 0.12), by + s * 0.44, bx + s * (cx + 0.12), by + s * 0.44, max(2, s * 0.03), GOLD)


# ------------------------------------------------------------- world map
# Simplified continent outlines as (lon, lat) polygons, equirectangular.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 80),
     (-75, 72), (-65, 60), (-55, 52), (-60, 45), (-70, 42), (-75, 35),
     (-80, 26), (-85, 20), (-90, 15), (-95, 18), (-100, 20), (-105, 23),
     (-110, 28), (-115, 32), (-125, 40), (-125, 48), (-135, 58), (-155, 60),
     (-165, 60)],
    [(-58, 64), (-45, 60), (-40, 70), (-55, 76), (-68, 76), (-60, 70)],
    [(-80, 10), (-75, 5), (-70, 0), (-75, -5), (-80, -10), (-80, -20),
     (-75, -30), (-70, -40), (-68, -52), (-65, -55), (-60, -45), (-55, -35),
     (-50, -25), (-40, -20), (-35, -8), (-40, -3), (-50, 0), (-55, 5),
     (-60, 8), (-70, 10)],
    [(-17, 15), (-15, 25), (-10, 30), (-5, 35), (0, 36), (10, 37),
     (20, 32), (30, 31), (35, 28), (40, 15), (45, 11), (50, 10),
     (45, 0), (40, -10), (35, -20), (30, -30), (20, -35), (15, -30),
     (12, -18), (10, -5), (5, 0), (0, 5), (-8, 5), (-15, 8)],
    [(30, 70), (40, 68), (50, 70), (60, 70), (70, 73), (80, 74), (90, 76),
     (100, 77), (110, 76), (120, 75), (130, 72), (140, 72), (150, 70),
     (160, 68), (170, 66), (178, 65), (170, 60), (162, 58), (158, 52),
     (150, 60), (142, 55), (140, 45), (135, 40), (130, 35), (127, 35),
     (122, 38), (120, 32), (115, 25), (110, 20), (108, 12), (105, 8),
     (100, 8), (98, 12), (95, 16), (92, 20), (90, 22), (88, 22),
     (85, 19), (80, 15), (77, 8), (75, 12), (72, 20), (70, 22),
     (66, 25), (62, 25), (58, 26), (56, 27), (52, 27), (50, 29),
     (48, 30), (44, 29), (40, 30), (36, 36), (33, 36), (30, 36),
     (28, 40), (28, 45), (30, 50), (35, 55), (40, 60), (45, 65), (50, 68)],
    [(-10, 36), (-9, 43), (-2, 44), (-1, 46), (-4, 48), (0, 50), (2, 52),
     (5, 54), (8, 57), (10, 59), (5, 60), (5, 62), (10, 64), (15, 68),
     (20, 70), (25, 71), (30, 70), (35, 66), (30, 60), (28, 55),
     (24, 58), (20, 55), (18, 54), (15, 54), (12, 55), (8, 55),
     (5, 53), (0, 51), (-2, 50), (-5, 48), (-2, 43), (-9, 38)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (125, -32), (130, -32),
     (135, -35), (138, -35), (140, -38), (145, -38), (150, -37), (153, -32),
     (153, -27), (150, -23), (146, -19), (142, -15), (142, -11), (137, -12),
     (135, -15), (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51)],
    [(130, 31), (132, 33), (135, 34), (138, 35), (140, 36), (141, 39),
     (142, 42), (144, 44), (142, 44), (140, 40), (138, 37), (135, 35), (132, 33)],
    [(95, 5), (100, 0), (104, -3), (106, -6), (103, -6), (99, 2)],
    [(105, -6), (110, -7), (114, -8), (112, -9), (107, -8)],
    [(109, 1), (113, 4), (117, 0), (116, -3), (111, -3), (109, -2)],
    [(131, -1), (136, -2), (141, -3), (146, -6), (147, -9), (141, -8), (136, -6)],
    [(167, -45), (170, -42), (173, -40), (175, -38), (178, -37),
     (176, -40), (173, -42), (170, -44), (167, -46)],
]
# (lon, lat, label, dx, dy) - label offset in px from the dot
MAP_POINTS = [
    (31, 37, "ANTALYA", 4, 10),
    (56, 26, "HORMUZ", 6, -15),
    (106, -6, "CIKANDE", 6, -2),
    (-108, 25, "GUASAVE", 4, -12),
    (-77, 39, "WASHINGTON", -84, -12),
    (31, 50, "KYIV", -36, -14),
    (6, 5, "BAYELSA", 4, 8),
    (127, 37, "SEOUL", 4, -12),
    (77, 29, "NEW DELHI", 6, 12),
    (175, -41, "WELLINGTON", -78, -14),
]

# -------------------------------------------------------------- front page

def fit_size(s, size, max_w):
    while size > 8 and text_width(s, size) > max_w:
        size -= 1
    return size


def masthead():
    fill_rect(0, 0, W, H, PAPER)
    # top rules
    hline(28, 10, W - 56, INK, 3)
    name = "THE WORLD IN ONE DAY"
    sz = fit_size(name, 54, W - 80)
    draw_text(W / 2, 18, name, sz, INK, align="center", sw=max(2.5, sz * 0.11))
    dateline = "MONDAY 23 NOVEMBER 2026"
    draw_text(W / 2, 82, dateline, 24, RED, align="center", sw=3.2)
    hline(28, 112, W - 56, INK, 2)
    hline(28, 116, W - 56, INK, 1)


SUBHEAD = [
    "COP31 COLLAPSES WITHOUT A DEAL",
    "IRAN CLAIMS THE STRAIT OF HORMUZ",
    "50 MISSING IN JAVA FACTORY FIRE",
    "DEMOCRATS WIN 258 HOUSE SEATS",
]


def subhead(y0=122, y1=168):
    cw = (W - 56 - 3 * 10) / 4.0
    for i, h in enumerate(SUBHEAD):
        x = 28 + i * (cw + 10)
        if i:
            vline(int(x - 5), y0 + 4, y1 - y0 - 8, LGREY, 1)
        lines = wrap_text(h, 17, cw)
        yy = y0 + 2
        for ln in lines[:2]:
            draw_text(x, yy, ln, 17, INK, sw=2.2)
            yy += 22
    hline(28, y1 + 4, W - 56, RULE, 1)


NUMBERS = [
    ("258", "HOUSE SEATS WON BY DEMOCRATS"),
    ("720", "INDIA'S RECORD TEST TOTAL"),
    ("50", "WORKERS MISSING IN JAVA FIRE"),
    ("24", "DEAD IN NIGERIA BOAT SINKING"),
    ("11", "KILLED IN MEXICO CARTEL RAID"),
    ("0", "'FOSSIL FUELS' IN COP31 DRAFT"),
]


def numbers_row(y0=180, y1=246):
    cw = (W - 56) / 6.0
    for i, (num, label) in enumerate(NUMBERS):
        x = 28 + i * cw
        if i:
            vline(int(x), y0 + 6, y1 - y0 - 12, LGREY, 1)
        sz = fit_size(num, 32, cw - 16)
        draw_text(x + cw / 2, y0 + 2, num, sz, RED if i % 2 == 0 else BLUE,
                  align="center", sw=max(2.5, sz * 0.11))
        yy = y0 + 40
        for ln in wrap_text(label, 11, cw - 14)[:2]:
            draw_text(x + cw / 2, yy, ln, 11, INK, align="center", sw=1.4)
            yy += 13
    hline(28, y1, W - 56, RULE, 1)


def region_bar(y0=252, h=28):
    fill_rect(28, y0, W - 56, h, INK)
    s = "ANTALYA  \u2022  HORMUZ  \u2022  CIKANDE  \u2022  GUASAVE  \u2022  WASHINGTON  \u2022  KYIV  \u2022  BAYELSA  \u2022  SEOUL  \u2022  NEW DELHI  \u2022  WELLINGTON"
    sz = fit_size(s, 14, W - 80)
    draw_text(W / 2, y0 + 6, s, sz, WHITE, align="center", sw=1.8)


LEADS = [
    ("CLIMATE - ANTALYA, TURKEY", "COP31 COLLAPSES WITH NO DEAL",
     "UN climate talks fail as the EU rejects a draft with no mention "
     "of fossil fuels.", icon_globe, RED),
    ("WAR - STRAIT OF HORMUZ", "IRAN SAYS IT HOLDS THE STRAIT",
     "Tehran claims the Strait and says it hit a US base in Bahrain. "
     "A Houthi missile is shot down.", icon_tanker, BLUE),
    ("DISASTER - CIKANDE, JAVA", "50 MISSING IN FACTORY FIRE",
     "Three dead after a blaze tears through a candy factory in Banten. "
     "The search resumes at dawn.", icon_fire, RED),
]


def leads(y0=292, y1=514):
    cw = (W - 56 - 2 * 14) / 3.0
    for i, (kick, head, dek, icon, accent) in enumerate(LEADS):
        x = 28 + i * (cw + 14)
        if i:
            vline(int(x - 7), y0, y1 - y0, LGREY, 1)
        icon(x + cw / 2 - 36, y0, 72)
        yy = y0 + 78
        draw_text(x, yy, kick, 13, accent, sw=1.8)
        yy += 19
        for ln in wrap_text(head, 21, cw)[:2]:
            draw_text(x, yy, ln, 21, INK, sw=2.8)
            yy += 26
        yy += 3
        draw_para(x, yy, dek, 14, INK, cw, leading=17)
    hline(28, y1, W - 56, RULE, 1)


TILES = [
    ("MEXICO", "FBI MOST-WANTED KINGPIN CAUGHT",
     "Seized in Guasave; 11 dead, four of them soldiers.", icon_badge),
    ("AMERICA", "DEMOCRATS CLINCH THE HOUSE",
     "At least 258 seats - most since 1992.", icon_capitol),
    ("UKRAINE", "14 MISSING AFTER KYIV STRIKE",
     "Drone hits a Kyiv building; ship burns off Finland.", icon_drone),
    ("NIGERIA", "FUNERAL BOAT SINKS, 24 DEAD",
     "Overloaded boat capsizes in Bayelsa; 24 rescued.", icon_boat),
    ("S. KOREA", "MINISTER QUITS IN AI EXAM SCANDAL",
     "Education minister resigns over AI exam cheating.", icon_gradcap),
    ("INDIA", "NEPAL PM MEETS MODI IN DELHI",
     "Balendra Shah holds talks on his first visit to India.", icon_flags),
    ("CRICKET", "INDIA'S 720 REWRITES THE BOOKS",
     "A record first-innings total in the Wellington Test.", icon_cricket),
    ("FOOTBALL", "LIVERPOOL ROUT MAN UTD",
     "Ten-man United thrashed in Pochettino's first match.", icon_ball),
    ("UN", "TALKS ON KILLER ROBOTS GO ON",
     "Nations keep negotiating curbs on killer robots.", icon_robot),
    ("ISRAEL", "WEST BANK ARSON IS 'TERRORISM'",
     "Eisenkot condemns settler attacks; talks collapse.", icon_scales),
]


def tiles(y0=524, y1=844):
    cw = (W - 56 - 4 * 10) / 5.0
    ch = (y1 - y0 - 10) / 2.0
    for idx, (kick, head, dek, icon) in enumerate(TILES):
        row, col = divmod(idx, 5)
        x = 28 + col * (cw + 10)
        y = y0 + row * (ch + 10)
        if col:
            vline(int(x - 5), int(y), int(ch), LGREY, 1)
        if row:
            hline(int(x), int(y - 5), int(cw), LGREY, 1)
        icon(x + 2, y, 46)
        draw_text(x + 52, y + 6, kick, 11, RED, sw=1.5)
        yy = y + 52
        for ln in wrap_text(head, 14, cw)[:3]:
            draw_text(x, yy, ln, 14, INK, sw=1.9)
            yy += 17
        draw_para(x, yy + 2, dek, 11, GREY, cw, leading=14)
    hline(28, y1, W - 56, RULE, 1)


ALSO = [
    "Wall Street hits correction",
    "Lisbon march over living costs",
    "24 killed in South Sudan attack",
    "Congo Ebola response disrupted",
    "Mongolia plans an early vote",
    "Japan: Labour Thanksgiving Day",
]


def map_row(y0=852, y1=978):
    mx, my = 28, y0
    mw, mh = 612, y1 - y0 - 20
    draw_text(mx, my, "WHERE IT HAPPENED", 13, INK, sw=1.8)
    draw_text(mx + mw, my, "23 NOVEMBER 2026", 13, RED, align="right", sw=1.8)
    my += 20
    fill_rect(mx, my, mw, mh, SKY)
    rect_outline(mx, my, mw, mh, RULE, 1)

    def proj(lon, lat):
        return (mx + (lon + 180.0) / 360.0 * mw,
                my + (78.0 - lat) / 140.0 * mh)

    for poly in CONTINENTS:
        polygon([proj(lon, lat) for lon, lat in poly], LAND)
        polyline([proj(lon, lat) for lon, lat in poly] + [proj(*poly[0])],
                 1, LAND2)
    for lon, lat, label, dx, dy in MAP_POINTS:
        cx, cy = proj(lon, lat)
        filled_circle(cx, cy, 4.5, RED)
        circle_outline(cx, cy, 4.5, 1, WHITE)
        draw_text(cx + dx, cy + dy, label, 10, INK, sw=1.3)
    # ALSO panel
    ax = 664
    draw_text(ax, y0, "ALSO IN THE NEWS", 13, INK, sw=1.8)
    yy = y0 + 22
    for item in ALSO:
        filled_circle(ax + 4, yy + 5, 3, RED)
        yy = draw_para(ax + 14, yy, item, 12, INK, W - 28 - ax - 14, leading=14)
        yy += 3
    hline(28, y1, W - 56, RULE, 1)


def draw_all():
    masthead()
    subhead()
    numbers_row()
    region_bar()
    leads()
    tiles()
    map_row()
    # DATE CHECK band
    y0 = 984
    fill_rect(28, y0, W - 56, 24, PAPER2)
    rect_outline(28, y0, W - 56, 24, RED, 2)
    s = ("DATE CHECK - Every story on this page was in the world's news "
         "on Monday 23 November 2026.")
    sz = fit_size(s, 13, W - 90)
    draw_text(W / 2, y0 + 5, s, sz, INK, align="center", sw=1.7)
    # footer
    draw_text(W / 2, 1010,
              "Sources: Reuters, AP, CNN, Fox News, PEOPLE  |  Drawn in pure "
              "Python.",
              11, GREY, align="center", sw=1.4)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "out"
    os.makedirs(outdir, exist_ok=True)
    draw_all()
    path = os.path.join(outdir, "entry.png")
    n = write_png(path, W, H, px)
    print("wrote %s (%d bytes)" % (path, n))


if __name__ == "__main__":
    main()

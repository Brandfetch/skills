#!/usr/bin/env python3
"""
Wall geometry: grid shape, optical sizing, optical centring.

A logo wall reads as designed when every mark carries the same VISUAL weight,
not the same box. Three effects fight that, and each has a correction:

1. Padding. Brands' files carry anything from 0% to 40% empty margin
   (Stripe's is tight, many symbols float in a big square). Every mark is
   trimmed to its ink before any of this runs — see ink.trim.

2. Shape. Equal heights make a 6:1 wordmark look huge next to a symbol;
   equal widths make it a sliver. Equal AREA is the perceptual middle:
       w = sqrt(A * r),  h = sqrt(A / r)          (r = aspect ratio)
   with heights guarded to 0.6x-1.6x the median so extreme ratios stay sane.

3. Weight. A solid, heavy mark reads bigger than a thin wordmark of the same
   area. Linear size is scaled by (median density / density) ** 0.25,
   clamped to 0.88-1.12 — enough to calm a bold symbol, not enough to inflate
   a hairline one (at 0.35 / 1.2, Figma's thin, tall wordmark dominated).

Then each mark is centred on its ink centroid rather than its box, limited
to 7% of its size — the fix for marks with an empty quadrant (Figma), capped
so a wordmark with a big left-hand symbol does not slide out of its cell.
"""
import math

SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN_X, BOTTOM = 0.9, 0.8
TOP_WITH_TITLE, TOP_BARE = 1.85, 0.9
AREA_FIT_QUANTILE = 0.2      # ≤20% of marks may hit their box and shrink to fit
WEIGHT_EXP, WEIGHT_MIN, WEIGHT_MAX = 0.25, 0.88, 1.12
HEIGHT_GUARD = (0.6, 1.6)
CENTROID_PULL = 0.07
MIN_CELL_ASPECT = {"logo": 1.55, "symbol": 1.15}
OPTICAL_CENTRE = 0.46       # a block sits slightly above centre to look centred


def choose_grid(n, median_aspect, area_w, area_h, cols=None):
    """
    Columns that fill rows evenly and give cells the shape the marks need.
    Wordmarks want wide cells, symbols near-square ones; empty cells in the
    last row cost more than a slightly-off cell shape.
    """
    if cols:
        return cols, math.ceil(n / cols)
    target = min(3.2, max(1.3, median_aspect * 1.6))
    best = None
    for c in range(2, min(8, n) + 1):
        r = math.ceil(n / c)
        if r > c:
            continue
        empty = c * r - n
        cell_aspect = (area_w / c) / (area_h / r)
        score = 3.0 * empty / c + abs(math.log(cell_aspect / target))
        if best is None or score < best[0]:
            best = (score, c, r)
    if best is None:
        return n, 1
    return best[1], best[2]


def layout(marks, title=False, cols=None, kind="logo"):
    """
    marks: [{"aspect", "density", "centroid"}] -> same dicts with
    x, y, w, h (inches, slide space) and cell-relative fractions for HTML.
    """
    n = len(marks)
    top = TOP_WITH_TITLE if title else TOP_BARE
    area_w, area_h = SLIDE_W - 2 * MARGIN_X, SLIDE_H - top - BOTTOM
    aspects = sorted(m["aspect"] for m in marks)
    med_aspect = aspects[n // 2]
    c, r = choose_grid(n, med_aspect, area_w, area_h, cols)
    cell_w = area_w / c
    # A wall is one block. Two rows stretched over the whole slide float
    # apart, so cells never get taller than the marks need; the block is
    # then centred in the space under the title.
    cell_h = min(area_h / r, cell_w / (MIN_CELL_ASPECT[kind]))
    top += (area_h - cell_h * r) * OPTICAL_CENTRE
    # the safe box is the gutter: the rest of the cell is breathing room
    box_w = cell_w * 0.78
    box_h = cell_h * (0.46 if kind == "logo" else 0.62)

    dens = sorted(m["density"] for m in marks)
    med_d = dens[n // 2] or 1
    for m in marks:
        m["g"] = min(WEIGHT_MAX, max(WEIGHT_MIN, (med_d / max(m["density"], 1e-3)) ** WEIGHT_EXP))

    # largest common area that fits most marks uncapped
    fits = sorted(min((box_w / m["g"]) ** 2 / m["aspect"], (box_h / m["g"]) ** 2 * m["aspect"])
                  for m in marks)
    A = fits[min(n - 1, int(AREA_FIT_QUANTILE * n))]

    for m in marks:
        m["w"] = math.sqrt(A * m["aspect"]) * m["g"]
        m["h"] = math.sqrt(A / m["aspect"]) * m["g"]
    heights = sorted(m["h"] for m in marks)
    med_h = heights[n // 2]
    for m in marks:
        lo, hi = HEIGHT_GUARD[0] * med_h, HEIGHT_GUARD[1] * med_h
        if m["h"] < lo:
            m["h"], m["w"] = lo, lo * m["aspect"]
        elif m["h"] > hi:
            m["h"], m["w"] = hi, hi * m["aspect"]
        s = min(1.0, box_w / m["w"], box_h / m["h"])      # never leave the box
        m["w"], m["h"] = m["w"] * s, m["h"] * s
        m["capped"] = s < 0.999

    for i, m in enumerate(marks):
        row, col = divmod(i, c)
        in_row = c if row < r - 1 else n - (r - 1) * c
        offset = (c - in_row) * cell_w / 2                 # centre a short last row
        cx0 = MARGIN_X + offset + col * cell_w
        cy0 = top + row * cell_h
        gx, gy = m["centroid"]
        dx = max(-CENTROID_PULL, min(CENTROID_PULL, 0.5 - gx)) * m["w"]
        dy = max(-CENTROID_PULL, min(CENTROID_PULL, 0.5 - gy)) * m["h"]
        m["x"] = cx0 + (cell_w - m["w"]) / 2 + dx
        m["y"] = cy0 + (cell_h - m["h"]) / 2 + dy
        m["cell"] = {"left": (m["x"] - cx0) / cell_w, "top": (m["y"] - cy0) / cell_h,
                     "w": m["w"] / cell_w, "h": m["h"] / cell_h}

    return {"cols": c, "rows": r, "cell": (cell_w, cell_h), "top": top, "area": A}

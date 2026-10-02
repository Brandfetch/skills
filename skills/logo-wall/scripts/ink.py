#!/usr/bin/env python3
"""
Logo pixels: loading, ink extraction, monochrome, measurement.

Everything a wall needs to know about ONE mark, measured from its pixels —
never from the `theme` label, which names a colour family, not a guarantee.

The monochrome treatment is the luminance-threshold filter from
references/monochrome.md (the #full-white / #full-dark SVG filters), ported
so PPTX, PDF, PNG and HTML get identical pixels:

    L    = .2126 R + .7152 G + .0722 B          (sRGB, 0..1)
    t    = clamp(16 L - 14.4)                   (0 below ~90% white, 1 above)
    ink  = alpha * (1 - t)                      (paper → transparent)

That keeps knocked-out detail — Notion's white cube face, a counter inside a
letter — as holes instead of flattening the mark into a solid blob, which is
what brightness(0) / a plain alpha fill does.
"""
import io
import os
import shutil
import subprocess
import tempfile

from PIL import Image

SAT_THRESH = 0.15      # per-pixel saturation above this counts as coloured
MONO_FRAC = 0.02       # >2% coloured ink = not a monochrome asset
VISIBLE, CONTRAST = 0.5, 1.5   # same bar as the deck builder


# ── loading ──────────────────────────────────────────────────────────────────

def load(path, width=1600):
    """RGBA image from PNG/JPEG/WebP/SVG. SVG is rasterised, never skipped."""
    with open(path, "rb") as f:
        head = f.read(512)
    if b"<svg" in head or head.lstrip().startswith(b"<?xml"):
        return _rasterise_svg(path, width)
    im = Image.open(path)
    im.load()
    return im.convert("RGBA")


def _rasterise_svg(path, width):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.png")
        try:
            import cairosvg
            cairosvg.svg2png(url=path, write_to=out, output_width=width)
        except ImportError:
            for cmd in (["rsvg-convert", "-w", str(width), "-o", out, path],
                        ["magick", "-background", "none", "-density", "300", path,
                         "-resize", f"{width}x", out]):
                if shutil.which(cmd[0]):
                    subprocess.run(cmd, check=True, capture_output=True)
                    break
            else:
                raise RuntimeError("SVG-only asset: pip install cairosvg (or install librsvg)")
        im = Image.open(out)
        im.load()
        return im.convert("RGBA")


# ── measurement ──────────────────────────────────────────────────────────────

def _lum(r, g, b):
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def _rel_lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def profile(im):
    """
    What the mark is made of: polarity (light/dark ink), coloured share,
    whether its colours span distinct hues, whether it has real transparency.
    """
    sm = im.copy()
    sm.thumbnail((200, 200))
    px = list(sm.getdata())
    total = len(px)
    opaque = [(r, g, b) for r, g, b, a in px if a > 128]
    transparent = sum(1 for *_, a in px if a < 20) / max(1, total)
    if not opaque:
        return {"polarity": "dark", "coloured": 0.0, "multi_hue": False,
                "transparent": transparent, "mean_lum": 0.0}
    mean_lum = sum(_lum(*p) for p in opaque) / len(opaque)
    coloured, hues = 0, [0] * 12
    for r, g, b in opaque:
        mx, mn = max(r, g, b), min(r, g, b)
        if mx > 30 and (mx - mn) / mx > SAT_THRESH:
            coloured += 1
            if (mx - mn) / mx > 0.25:
                hues[_hue(r, g, b) * 12 // 360] += 1
    sat = sum(hues)
    strong = [i for i, n in enumerate(hues) if sat and n / sat >= 0.08]
    spread = max((min(abs(a - b), 12 - abs(a - b)) for a in strong for b in strong), default=0)
    return {
        "polarity": "light" if mean_lum > 0.5 else "dark",
        "coloured": coloured / len(opaque),
        # Distinct hues ≥90° apart (Slack, Google) are the case where colour
        # is the only thing separating the parts — flattening merges them.
        "multi_hue": spread >= 3,
        "transparent": transparent,
        "mean_lum": mean_lum,
    }


def _sat(p):
    mx, mn = max(p[:3]), min(p[:3])
    return (mx - mn) / mx if mx > 30 else 0.0


def _hue(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0
    d = mx - mn
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return int(h * 60) % 360


def structure_loss(im, prof=None):
    """
    How much of the mark's drawing flattening would erase.

    Counts colour edges BETWEEN ink pixels (Mastercard's overlap, Figma's
    touching lobes, Slack's arms) against the ink's outer outline (which a
    flat version keeps). Hue alone misses this: Mastercard's red / orange /
    yellow are neighbours on the wheel, yet its overlap exists only in colour.
    Knockouts are not lost — near-white inside a dark mark becomes a hole.
    """
    sm = im.copy()
    sm.thumbnail((240, 240))
    mask = ink_mask(sm, prof).load()
    px = sm.load()
    w, h = sm.size
    inner = outline = 0
    for y in range(h - 1):
        for x in range(w - 1):
            a = mask[x, y] > 128
            for nx, ny in ((x + 1, y), (x, y + 1)):
                b = mask[nx, ny] > 128
                if a != b:
                    outline += 1
                elif a:
                    p, q = px[x, y], px[nx, ny]
                    # a colour change, not shading: grey-on-black is shading
                    # (Notion's cube side) and may go; red-on-orange is identity
                    if (_sat(p) > 0.25 or _sat(q) > 0.25) and \
                            abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) > 90:
                        inner += 1
    return inner / max(1, outline)


def silhouette_iou(a, b, size=48):
    """How much two marks share a silhouette (1 = same drawing)."""
    def sil(im):
        m = ink_mask(im).resize((size, size))
        return [v > 96 for v in m.getdata()]
    x, y = sil(a), sil(b)
    union = sum(p or q for p, q in zip(x, y)) or 1
    return sum(p and q for p, q in zip(x, y)) / union


def secondary_line(im):
    """
    True when the mark is a two-line lockup whose second line is much smaller
    — a tagline or endorsement ("slack / from Salesforce"). At wall size that
    line shrinks to unreadable, so it is worth a human look.
    """
    m = ink_mask(im)
    w, h = m.size
    rows = [sum(1 for v in m.crop((0, y, w, y + 1)).getdata() if v > 96) for y in range(h)]
    bands, start = [], None
    for y, n in enumerate(rows + [0]):
        if n and start is None:
            start = y
        elif not n and start is not None:
            bands.append(y - start)
            start = None
    return len(bands) >= 2 and min(bands) < 0.45 * max(bands)


def is_mono(prof):
    return prof["coloured"] < MONO_FRAC


def visibility(im, ground_hex):
    """Share of the mark's opaque pixels that stand out on ground (≥1.5:1)."""
    sm = im.copy()
    sm.thumbnail((160, 160))
    g = _rel_lum(hex_rgb(ground_hex))
    n = ok = 0
    for r, gg, b, a in sm.getdata():
        if a < 128:
            continue
        n += 1
        l = _rel_lum((r, gg, b))
        if (max(l, g) + 0.05) / (min(l, g) + 0.05) >= CONTRAST:
            ok += 1
    return ok / n if n else 0.0


# ── ink ──────────────────────────────────────────────────────────────────────

def ink_mask(im, prof=None):
    """
    8-bit mask of what is INK in this mark, paper removed.

    Dark-ink sources (the usual case): near-white is paper — the engineer's
    threshold, t = clamp(16L − 14.4), ink = α(1 − t). This is also what erases
    the opaque white background of a JPEG.

    Light-ink sources (a white mark for dark slides): the same rule would
    erase the mark itself, so the polarity flips — near-black is paper:
    s = clamp(16(0.16 − L)), ink = α(1 − s).
    """
    prof = prof or profile(im)
    light = prof["polarity"] == "light" and prof["transparent"] > 0.05
    out = Image.new("L", im.size)
    data = []
    for r, g, b, a in im.getdata():
        L = _lum(r, g, b)
        if light:
            paper = min(1.0, max(0.0, 16 * (0.16 - L)))
        else:
            paper = min(1.0, max(0.0, 16 * L - 14.4))
        data.append(int(a * (1 - paper)))
    out.putdata(data)
    return out


def monochrome(im, ink_hex, prof=None):
    """The mark in one flat colour, knockouts kept as transparency."""
    mask = ink_mask(im, prof)
    out = Image.new("RGBA", im.size, hex_rgb(ink_hex) + (0,))
    out.putalpha(mask)
    return out


def trim(im, threshold=8):
    """Crop to the ink: padding differs wildly between brands' files."""
    alpha = im.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    bbox = alpha.getbbox()
    return im.crop(bbox) if bbox else im


def metrics(im):
    """
    Geometry of a trimmed mark: aspect, ink density, optical centre.

    density — share of the box that is ink (a bold solid symbol ≈ .7, a light
    wordmark ≈ .25). Heavier marks read bigger at the same size.
    centroid — alpha-weighted centre, 0..1 in the box. A mark with an empty
    quadrant (Figma) looks off-centre when its BOX is centred.
    """
    w, h = im.size
    sm = im.copy()
    sm.thumbnail((200, 200))
    sw, sh = sm.size
    a = list(sm.getchannel("A").getdata())
    total = sum(a) or 1
    cx = sum((i % sw + 0.5) * v for i, v in enumerate(a)) / total / sw
    cy = sum((i // sw + 0.5) * v for i, v in enumerate(a)) / total / sh
    return {"aspect": w / h, "density": total / (255 * sw * sh),
            "centroid": (cx, cy), "px": (w, h)}


def png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()

#!/usr/bin/env python3
"""
Turn a deck you already sent to a client into an instrumented template.

Nobody types a token. The user uploads a real deck, this script proposes
everything that should change per deck, the proposal is agreed in
conversation, and the script writes the template.

    # 1. propose (JSON on stdout)
    python3 instrument_template.py --detect deck.pptx \
        [--brand=brand.json] [--extract=previews/] > proposal.json

    # 2. edit proposal.json with the user, then write the template
    python3 instrument_template.py --apply deck.pptx proposal.json template.pptx

--brand is the get_brand_data response for the client the deck was made for. With
it, detection is matching rather than guessing: the brand's exact name
string, description, firmographics and logo files are compared against the
deck. Without it, detection falls back to heuristics (repeated proper nouns,
logo-shaped pictures) and pre-selects nothing it is not sure of.

--extract writes every picture as a PNG on its own background, so the
candidates can be looked at rather than inferred.

The proposal IS the mapping. Every entry carries a "token": keep it, change
it, or set it to null to leave that value alone. Add entries for anything
detection missed:

    {"find": "<exact text on the slide>", "token": "{your_token}"}     text
    {"slide": 3, "id": 7, "token": "{bf:lightOrDarkLogo}"}             picture

A text entry may carry "slides": [2, 4] to limit it to those slides.

Editing follows the builder's rules (references/rules.md): runs are merged
before substituting, every edit is scoped to one shape, nothing is
global-replaced across slide XML.
"""
import hashlib
import html
import io
import json
import os
import posixpath
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from PIL import Image

import bf_fields as BF
from build_deck import EMU, SAFE_W, SAFE_H, fetch, geom, merge_split_runs, prst_geom, to_raster
from scan_template import luminance

SLIDE = re.compile(r"ppt/slides/slide(\d+)\.xml")
NOTES = re.compile(r"ppt/notesSlides/notesSlide\d+\.xml")
# Shape-level units. None of these nest inside themselves; groups are
# handled separately (group_spans) because they do.
UNIT = re.compile(r"<p:(sp|pic|graphicFrame)(?:\s[^>]*)?>.*?</p:\1>", re.S)
PARA = re.compile(r"<a:p>(.*?)</a:p>", re.S)
RUN = re.compile(r"<a:r>(.*?)</a:r>", re.S)
T = re.compile(r"<a:t>(.*?)</a:t>", re.S)
TOKEN_SPAN = re.compile(r"\{[^{}\n]{1,40}\}")

MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|"
         r"July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
         r"Dec(?:ember)?)")
DATE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}\.?,?\s+\d{{4}}"
    rf"|{MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|{MONTH}\s+\d{{4}}"
    rf"|{MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+'?\d{{2}}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/.]\d{1,2}[/.](?:\d{4}|\d{2})"
    r"|Q[1-4]\s?\d{4})\b"
)
CODES = r"(?:USD|EUR|GBP|CHF|CAD|AUD|NZD|JPY|CNY|SEK|NOK|DKK|INR|SGD|HKD|BRL|MXN|ZAR|AED)"
MAGNITUDE = r"(?:\s?(?:k|K|m|M|bn|BN|million|thousand|billion)\b)?"
AMOUNT = re.compile(
    rf"(?:[$€£¥₹]\s?\d[\d,.]*{MAGNITUDE}"
    rf"|\b{CODES}\s?\d[\d,.]*{MAGNITUDE}"
    rf"|\b\d[\d,.]*{MAGNITUDE}\s?(?:{CODES}\b|€))"
)
PROPER = re.compile(
    r"(?<![\w{:@./])[A-Z][\w&'’.-]*[\w](?:[ \t]+[A-Z][\w&'’.-]*[\w]){0,2}"
)
# Capitalised words that are grammar or slide furniture, never a client.
STOP = set("""
A An The Our Your Their We You They It Its This That These Those Here There
And Or But For With Without In On At To Of By From Into Over Under About
How What Why When Where Who Which Next Why Key Our Us I Me My
Mr Ms Mrs Dr Inc Ltd LLC GmbH SA AG Co Corp
Monday Tuesday Wednesday Thursday Friday Saturday Sunday
January February March April May June July August September October November December
Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec Q1 Q2 Q3 Q4
Page Slide Agenda Appendix Contents Summary Overview Introduction Thank Thanks Confidential
""".split())

SCHEME = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
RASTER = ["png", "jpeg", "jpg", "webp", "svg"]   # SVG last: it must be rasterised first
# "Volume: 100,000 requests/mo" — a deal field written as one line
FIELD = re.compile(r"^\s*([A-Z][^:\n]{1,40}?)\s*:\s+(\S.{0,60}?)\s*$")


# ── package plumbing ─────────────────────────────────────────────────────────

def load(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def slide_parts(files):
    return sorted((n for n in files if SLIDE.fullmatch(n)),
                  key=lambda n: int(SLIDE.fullmatch(n).group(1)))


def slide_no(part):
    return int(SLIDE.fullmatch(part).group(1))


def rels_path(part):
    d, _, b = part.rpartition("/")
    return f"{d}/_rels/{b}.rels" if d else f"_rels/{b}.rels"


def relationships(files, part):
    """{rId: (type, resolved target part)} for one part."""
    raw = files.get(rels_path(part), b"").decode("utf-8", "replace")
    base = part.rpartition("/")[0]
    out = {}
    for m in re.finditer(r"<Relationship\b[^>]*/?>", raw):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("TargetMode") == "External":
            continue
        out[a.get("Id")] = (a.get("Type", ""),
                            posixpath.normpath(posixpath.join(base, a.get("Target", ""))))
    return out


def related(files, part, kind):
    for typ, target in relationships(files, part).values():
        if typ.endswith("/" + kind):
            return target
    return None


def attr(fragment, tag, name):
    m = re.search(rf"<{tag}\b[^>]*\b{name}=\"([^\"]*)\"", fragment)
    return html.unescape(m.group(1)) if m else None


def shape_label(unit):
    return attr(unit, "p:cNvPr", "name") or ""


def shape_id(unit):
    v = attr(unit, "p:cNvPr", "id")
    return int(v) if v and v.isdigit() else None


# ── colour ───────────────────────────────────────────────────────────────────

def theme_colors(files):
    raw = next((files[n] for n in sorted(files) if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)), b"")
    raw = raw.decode("utf-8", "replace")
    out = {}
    for name in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
                 "accent4", "accent5", "accent6"):
        m = re.search(rf"<a:{name}>(.*?)</a:{name}>", raw, re.S)
        if m:
            c = re.search(r'(?:srgbClr val|lastClr)="([0-9A-Fa-f]{6})"', m.group(1))
            if c:
                out[name] = c.group(1).upper()
    return out


def color_in(fragment, theme):
    """First concrete colour element in fragment, resolved through the theme."""
    m = re.search(r"<a:(srgbClr|schemeClr|sysClr)\b([^>]*)>?", fragment)
    if not m:
        return None
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
    if m.group(1) == "srgbClr":
        return a.get("val", "").upper() or None
    if m.group(1) == "sysClr":
        return a.get("lastClr", "").upper() or None
    v = a.get("val", "")
    return theme.get(SCHEME.get(v, v))


def shape_fill(unit, theme):
    """The shape's own fill colour, or None (no fill, picture, gradient...)."""
    sppr = re.search(r"<p:spPr\b[^>]*>(.*?)</p:spPr>", unit, re.S)
    body = sppr.group(1) if sppr else ""
    body = re.sub(r"<a:ln\b[^>]*/>|<a:ln\b.*?</a:ln>", "", body, flags=re.S)
    if "<a:noFill" in body or "<a:gradFill" in body or "<a:blipFill" in body:
        return None
    m = re.search(r"<a:solidFill>(.*?)</a:solidFill>", body, re.S)
    if m:
        return color_in(m.group(1), theme)
    # No explicit fill: shapes drawn in PowerPoint inherit one from <p:style>.
    ref = re.search(r'<a:fillRef idx="(\d+)"[^>]*>(.*?)</a:fillRef>', unit, re.S)
    if ref and ref.group(1) != "0":
        return color_in(ref.group(2), theme)
    return None


def background(files, part, theme):
    """Slide background, falling back through its layout and master."""
    chain = [part]
    layout = related(files, part, "slideLayout")
    if layout:
        chain.append(layout)
        master = related(files, layout, "slideMaster")
        if master:
            chain.append(master)
    for p in chain:
        raw = files.get(p, b"").decode("utf-8", "replace")
        m = re.search(r"<p:bg>(.*?)</p:bg>", raw, re.S)
        if m:
            c = color_in(m.group(1), theme)
            if c:
                return c
    return None


def tone(hexval):
    return None if not hexval else ("dark" if luminance(hexval) < 128 else "light")


# ── geometry ─────────────────────────────────────────────────────────────────

def group_spans(xml):
    """(start, end, group_xml) for every <p:grpSp>, nested ones included."""
    spans, stack = [], []
    for m in re.finditer(r"<p:grpSp>|</p:grpSp>", xml):
        if m.group(0) == "<p:grpSp>":
            stack.append(m.start())
        elif stack:
            s = stack.pop()
            spans.append((s, m.end(), xml[s:m.end()]))
    return spans


def group_transform(gxml):
    m = re.search(r"<p:grpSpPr(?:\s[^>]*)?(?:/>|>(.*?)</p:grpSpPr>)", gxml, re.S)
    body = (m.group(1) or "") if m else ""
    n = re.search(
        r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>\s*'
        r'<a:chOff x="(-?\d+)" y="(-?\d+)"/>\s*<a:chExt cx="(\d+)" cy="(\d+)"/>',
        body)
    return tuple(int(v) for v in n.groups()) if n else None


def enclosing_groups(groups, pos):
    """Groups containing pos, innermost first."""
    return sorted((g for g in groups if g[0] < pos < g[1]), key=lambda g: -g[0])


def to_slide_space(frame, groups):
    x, y, cx, cy = frame
    for _, _, gxml in groups:
        t = group_transform(gxml)
        if not t:
            continue
        ox, oy, ecx, ecy, chx, chy, chcx, chcy = t
        sx = ecx / chcx if chcx else 1
        sy = ecy / chcy if chcy else 1
        x, y, cx, cy = ox + (x - chx) * sx, oy + (y - chy) * sy, cx * sx, cy * sy
    return int(x), int(y), int(cx), int(cy)


def is_identity(groups):
    for _, _, gxml in groups:
        t = group_transform(gxml)
        if t and (t[0], t[1], t[2], t[3]) != (t[4], t[5], t[6], t[7]):
            return False
    return True


def slide_size(files):
    raw = files.get("ppt/presentation.xml", b"").decode("utf-8", "replace")
    m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', raw)
    return (int(m.group(1)), int(m.group(2))) if m else (12192000, 6858000)


def inches(frame):
    return [round(v / EMU, 2) for v in frame]


# ── slide model ──────────────────────────────────────────────────────────────

def plain(run_xml):
    t = T.search(run_xml)
    return html.unescape(t.group(1)) if t else ""


def run_texts(inner):
    """
    (runs, texts) for one paragraph. A run that follows a soft line break or
    a field starts with "\n", so words either side of a break never fuse
    ("team" + "Spotify" is not "teamSpotify").
    """
    runs = list(RUN.finditer(inner))
    texts, last = [], 0
    for r in runs:
        gap = inner[last:r.start()]
        texts.append(("\n" if last and ("<a:br" in gap or "<a:fld" in gap) else "")
                     + plain(r.group(1)))
        last = r.end()
    return runs, texts


def para_text(inner):
    return "".join(run_texts(inner)[1])


def paragraphs(unit):
    """Visible text per paragraph. Tables yield (text, row label) per cell."""
    out = []
    if unit.startswith("<p:graphicFrame"):
        rows = re.findall(r"<a:tr\b[^>]*>(.*?)</a:tr>", unit, re.S)
        header = []
        for r_i, row in enumerate(rows):
            cells = [" ".join(para_text(p) for p in PARA.findall(c)).strip()
                     for c in re.findall(r"<a:tc\b[^>]*>(.*?)</a:tc>", row, re.S)]
            if r_i == 0:
                header = cells
            for c_i, text in enumerate(cells):
                col = header[c_i] if r_i and c_i < len(header) else ""
                row = cells[0] if c_i and cells[0] else ""
                if col:
                    label = f"{col} {row}".strip()
                else:
                    label = next((c for c in reversed(cells[:c_i])
                                  if c and not re.fullmatch(r"[\d.,%$€£ ]+", c)), None)
                if text:
                    out.append((text, label))
        return out
    for p in PARA.findall(unit):
        text = para_text(p)
        if text.strip():
            out.append((text, None))
    return out


def slide_model(files, part, theme, xml=None):
    """Shapes in z-order with slide-space frames. Pass xml to model an edit in progress."""
    if xml is None:
        xml = merge_split_runs(files[part].decode("utf-8", "replace"))
    groups = group_spans(xml)
    units = []
    for m in UNIT.finditer(xml):
        u = m.group(0)
        g = geom(u)
        enc = enclosing_groups(groups, m.start())
        units.append({
            "kind": m.group(1), "xml": u, "start": m.start(), "end": m.end(),
            "id": shape_id(u), "name": shape_label(u),
            "frame": to_slide_space(g, enc) if g else None,
            "groups": enc, "fill": shape_fill(u, theme) if m.group(1) == "sp" else None,
        })
    return xml, units, background(files, part, theme)


# ── labels: what a value is next to ──────────────────────────────────────────

def label_for(unit, units, text, match_start):
    """
    The short text a value sits beside: an in-line prefix ("Fee: USD 9,000"),
    a shape to its left on the same row, or a shape directly above it.
    """
    prefix = text[:match_start].rstrip()
    if prefix.endswith((":", "–", "—", "-")):
        # "Prepared for Acme · Kick-off: 12 May": the label is the last
        # segment, not the whole line
        words = re.split(r"[·•|;,]", prefix.rstrip(":–—- "))[-1].split()
        if 0 < len(words) <= 4:
            return " ".join(words)
    return neighbour_label(unit, units)[0]


def text_style(unit):
    """(size, bold, colour) of a shape's first run — how a label differs from its value."""
    m = re.search(r"<a:r><a:rPr\b([^>]*?)/?>(.*?)</a:r>", unit, re.S)
    if not m:
        return None
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    c = re.search(r'<a:srgbClr val="(\w+)"', m.group(2).split("<a:t>")[0])
    return a.get("sz"), a.get("b") == "1", c.group(1).upper() if c else None


def neighbour_label(unit, units):
    """(text, unit) of the nearest short text shape left on the row, else above."""
    if not unit["frame"]:
        return None, None
    x, y, cx, cy = unit["frame"]
    best, best_u, best_d = None, None, None
    for o in units:
        if o is unit or o["kind"] != "sp" or not o["frame"]:
            continue
        otext = " ".join(t for t, _ in paragraphs(o["xml"])).strip()
        if not otext or len(otext) > 40 or TOKEN_SPAN.search(otext) \
                or DATE.search(otext) or AMOUNT.search(otext):
            continue
        ox, oy, ocx, ocy = o["frame"]
        same_row = abs((oy + ocy / 2) - (y + cy / 2)) < max(0.2 * EMU, cy / 3)
        left_gap = x - (ox + ocx)
        overlap = min(x + cx, ox + ocx) - max(x, ox)
        above_gap = y - (oy + ocy)
        d = None
        if same_row and -0.05 * EMU <= left_gap:
            d = left_gap
        elif overlap > 0.5 * min(cx, ocx) and -0.05 * EMU <= above_gap <= 0.6 * EMU:
            d = above_gap + 0.5 * EMU     # prefer a row label over one above
        if d is not None and (best_d is None or d < best_d):
            best, best_u, best_d = otext, o, d
    return best, best_u


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return "_".join(s.split("_")[:4])


# ── images ───────────────────────────────────────────────────────────────────

def open_image(data):
    """Pillow image from bytes; SVG is rasterised first (Pitch exports many)."""
    try:
        if data.lstrip()[:5] in (b"<?xml", b"<svg ", b"<svg>") or b"<svg" in data[:512]:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "in.svg")
                open(src, "wb").write(data)
                im = Image.open(to_raster(src, width=800))
                im.load()
                return im
        im = Image.open(io.BytesIO(data))
        im.load()
        return im
    except Exception:
        return None


def crop_src_rect(im, pic):
    m = re.search(r"<a:srcRect\b([^>]*)/>", pic)
    if not m:
        return im
    a = {k: int(v) / 100000 for k, v in re.findall(r'(\w)="(-?\d+)"', m.group(1))}
    w, h = im.size
    box = (int(w * a.get("l", 0)), int(h * a.get("t", 0)),
           int(w * (1 - a.get("r", 0))), int(h * (1 - a.get("b", 0))))
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return im
    return im.crop(box)


def signature(im):
    """(aspect, 24x24 grey thumbnail) of the visible mark, borders trimmed."""
    im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    # Mid-grey ground keeps both white and black marks visible.
    ground = Image.new("RGBA", im.size, (128, 128, 128, 255))
    ground.alpha_composite(im)
    thumb = ground.convert("L").resize((24, 24), Image.BILINEAR)
    return w / max(h, 1), list(thumb.getdata())


def distance(a, b):
    ar = abs(a[0] - b[0]) / max(a[0], b[0])
    px = sum(abs(p - q) for p, q in zip(a[1], b[1])) / (255 * len(a[1]))
    return ar, px


def brand_assets(brand):
    """Download one raster file per logo/image entry. Returns (assets, notes)."""
    wanted = []
    for e in brand.get("logos") or []:
        wanted.append((e.get("type"), e.get("theme"), e.get("formats")))
    for e in brand.get("images") or []:
        if e.get("type") == "banner":
            wanted.append(("banner", e.get("theme"), e.get("formats")))
    tmp = tempfile.mkdtemp(prefix="bf_assets_")
    assets, notes = [], []
    for i, (typ, theme, formats) in enumerate(wanted):
        by_fmt = {f.get("format"): f for f in formats or []}
        fmt = next((by_fmt[f] for f in RASTER if f in by_fmt), None)
        if not fmt:
            continue
        path = os.path.join(tmp, f"{i}_{typ}_{theme}.{fmt['format']}")
        try:
            fetch(fmt["src"], path)
        except Exception as e:
            notes.append(f"could not download the {theme} {typ} ({e}); "
                         f"logo matching falls back to heuristics")
            continue
        data = open(path, "rb").read()
        im = open_image(data)
        if im:
            assets.append({"type": typ, "theme": theme, "sha1": hashlib.sha1(data).hexdigest(),
                           "image": im})
    return assets, notes


def logo_token(kind, ground_tone, asset_theme, aspect, shape):
    """
    The slot token for a picture. Logos and symbols get the auto tokens: the
    builder picks the light or dark variant per slot by measuring which one is
    visible on that slot's ground, so the template never hard-codes a theme.
    """
    if kind == "icon" or (kind is None and shape == "ellipse"):
        return "{bf:icon}"
    if kind == "banner":
        return "{bf:banner}"
    if kind not in ("logo", "symbol"):
        kind = "logo" if aspect >= 1.6 else "symbol"
    return "{bf:logo}" if kind == "logo" else "{bf:symbol}"


def ground_under(unit, units, slide_bg):
    """Colour directly beneath a shape: the topmost filled shape below it, else the slide."""
    if not unit["frame"]:
        return slide_bg
    x, y, cx, cy = unit["frame"]
    px, py = x + cx / 2, y + cy / 2
    hit = None
    for o in units:
        if o["start"] >= unit["start"]:
            break
        if o["fill"] and o["frame"]:
            ox, oy, ocx, ocy = o["frame"]
            if ox <= px <= ox + ocx and oy <= py <= oy + ocy:
                hit = o["fill"]
    return hit or slide_bg


# ── detect ───────────────────────────────────────────────────────────────────

def detect(deck, brand=None, extract=None):
    files = load(deck)
    theme = theme_colors(files)
    sw, sh = slide_size(files)
    parts = slide_parts(files)
    notes = []

    brand_text = []   # (literal, token, kind, why)
    if brand:
        text_vals, _, _ = BF.resolve(brand)
        name = text_vals.get("{bf:name}")
        for tok, val in text_vals.items():
            if val:
                brand_text.append((val, tok, "client_name" if tok == "{bf:name}" else "brand_field",
                                   f"exact {tok} value from get_brand_data"))
        if name and name.upper() != name:
            brand_text.append((name.upper(), "{bf:name}", "client_name",
                               "{bf:name} in capitals — the builder fills the API's casing"))
        dom = (brand.get("domain") or "").strip()
        if dom:
            brand_text.append((dom, "{client_domain}", "client_domain",
                               "the client's domain — no {bf:*} field carries it, supply it per deck"))
        brand_text.sort(key=lambda b: -len(b[0]))

    text_items = {}       # literal -> item
    proper = {}           # candidate -> stats
    existing = set()

    def item(literal, token, kind, confidence, why):
        if literal not in text_items:
            text_items[literal] = {"find": literal, "token": token, "kind": kind,
                                   "confidence": confidence, "why": why, "occurrences": []}
        return text_items[literal]

    models = {}
    for part in parts:
        n = slide_no(part)
        xml, units, bg = slide_model(files, part, theme)
        models[part] = (xml, units, bg)
        for u in units:
            if u["kind"] == "pic":
                continue
            for text, row_label in paragraphs(u["xml"]):
                taken = [(m.start(), m.end()) for m in TOKEN_SPAN.finditer(text)]
                existing.update(m.group(0) for m in TOKEN_SPAN.finditer(text))

                def free(s, e):
                    return all(e <= a or s >= b for a, b in taken)

                occ = {"slide": n, "shape": u["name"], "id": u["id"], "text": text[:140]}

                for literal, tok, kind, why in brand_text:
                    for m in find_pattern(literal).finditer(text):
                        if free(m.start(), m.end()):
                            taken.append((m.start(), m.end()))
                            item(literal, tok, kind, "high", why)["occurrences"].append(occ)

                for rx, kind in ((DATE, "date"), (AMOUNT, "amount")):
                    for m in rx.finditer(text):
                        s, e = m.start(), m.end()
                        lit = m.group(0).rstrip(" .,")
                        e = s + len(lit)
                        if not free(s, e):
                            continue
                        taken.append((s, e))
                        label = row_label or label_for(u, units, text, s)
                        it = item(lit, None, kind, "medium",
                                  f"{kind} — does it change per deck?"
                                  + (f" (label: {label})" if label else ""))
                        it.setdefault("_label", label)
                        it["occurrences"].append(occ)

                f = FIELD.match(text)
                if f and f.group(2) and len(f.group(1).split()) <= 4 \
                        and len(f.group(2).split()) <= 6 and free(f.start(2), f.end(2)):
                    val = f.group(2).rstrip(" .")
                    taken.append((f.start(2), f.start(2) + len(val)))
                    base = slug(f.group(1)) or "value"
                    it = item(val, None, "field", "medium",
                              f"'{f.group(1)}: …' line — a deal term that changes per deck?")
                    it.setdefault("suggestion", "{" + base + "}")
                    it["occurrences"].append(occ)

                for m in PROPER.finditer(text):
                    if not free(m.start(), m.end()):
                        continue
                    # Capitalised because it starts a line or sentence proves
                    # nothing; only a capital mid-sentence marks a name.
                    initial = re.fullmatch(r"[\W\d]*", text[:m.start()]) is not None \
                        or text[:m.start()].rstrip().endswith((".", "!", "?", ":", "—", "–", "-"))
                    words = re.sub(r"['’]s$", "", m.group(0)).split()
                    while words and words[0] in STOP:
                        words.pop(0)
                    if not words or all(w in STOP for w in words):
                        continue
                    cand = " ".join(words)
                    if re.fullmatch(r"[A-Z0-9]{1,4}", cand):
                        continue            # acronyms: CDN, API, SOC2
                    st = proper.setdefault(cand, {"count": 0, "slides": set(), "occ": [],
                                                  "mid": 0})
                    st["mid"] += not initial
                    st["count"] += 1
                    st["slides"].add(n)
                    st["occ"].append(occ)

    # user-value tokens named after their labels, unique per literal
    used = set(existing) | {i["token"] for i in text_items.values() if i["token"]}
    for it in text_items.values():
        if it["kind"] not in ("date", "amount"):
            continue
        label = it.pop("_label", None)
        base = slug(label) if label else ""
        if it["kind"] == "date":
            base = (base + ("" if "date" in base.split("_") else "_date")).strip("_") or "date"
        else:
            base = base or "amount"
        tok, i = "{" + base + "}", 2
        while tok in used:
            tok, i = "{" + f"{base}_{i}" + "}", i + 1
        used.add(tok)
        it["token"] = tok

    for it in text_items.values():
        if it["kind"] == "field":
            base, i = it["suggestion"].strip("{}"), 2
            tok = it["suggestion"]
            while tok in used:
                tok, i = "{" + f"{base}_{i}" + "}", i + 1
            used.add(tok)
            it["suggestion"] = tok

    covered = {i["find"] for i in text_items.values()}
    brand_name = (brand or {}).get("name")
    ranked = sorted(proper.items(), key=lambda kv: (-len(kv[1]["slides"]), -kv[1]["count"]))
    ranked = [(c, st) for c, st in ranked
              if st["count"] >= 2 and st["mid"] and c not in covered and c != brand_name
              and not (brand_name and brand_name in c)]
    for cand, st in ranked[:8]:
        text_items[cand] = {
            "find": cand, "token": None, "kind": "repeated_name", "confidence": "low",
            "suggestion": "{bf:name}",
            "why": f"proper noun, {st['count']}x on {len(st['slides'])} slide(s) — the previous "
                   f"client? your own company? a product? ask",
            "occurrences": st["occ"],
        }

    labelled = labelled_values(models, text_items, used)

    # pictures
    assets, fetch_notes = brand_assets(brand) if brand else ([], [])
    notes += fetch_notes
    media_slides = {}
    pics = []
    for part in parts:
        xml, units, bg = models[part]
        rel = relationships(files, part)
        for u in units:
            if u["kind"] != "pic":
                continue
            # Pitch exports SVG-only pictures: the reference lives on the
            # svgBlip extension and the <a:blip> itself is empty.
            rid = attr(u["xml"], "a:blip", "r:embed") or attr(u["xml"], "asvg:svgBlip", "r:embed")
            target = rel.get(rid, (None, None))[1] if rid else None
            data = files.get(target) if target else None
            sha = hashlib.sha1(data).hexdigest() if data else None
            if sha:
                media_slides.setdefault(sha, set()).add(slide_no(part))
            pics.append((part, u, bg, target, data, sha))

    images = []
    for part, u, bg, target, data, sha in pics:
        n = slide_no(part)
        frame = u["frame"] or (0, 0, 1, 1)
        shape = prst_geom(u["xml"])
        ground = ground_under(u, models[part][1], bg)
        gt = tone(ground)
        area = frame[2] * frame[3] / (sw * sh)
        aspect = frame[2] / max(frame[3], 1)
        im = open_image(data) if data else None
        entry = {
            "slide": n, "id": u["id"], "name": u["name"],
            "alt_text": attr(u["xml"], "p:cNvPr", "descr"),
            "media": target, "frame_in": inches(frame), "shape": shape,
            "ground": f"{ground} ({gt})" if ground else "unknown",
            "on_slides": sorted(media_slides.get(sha, {n})),
            "in_group": bool(u["groups"]),
        }
        if im is None:
            entry.update(token=None, kind="unreadable", confidence="low",
                         why="image format not readable here (EMF/WMF/SVG-only?) — look at the slide")
            images.append(entry)
            continue

        best = None
        if assets:
            sig = signature(crop_src_rect(im, u["xml"]))
            for a in assets:
                if sha == a["sha1"]:
                    best = (a, 0.0, "identical file")
                    break
                ar, px = distance(sig, signature(crop_src_rect(a["image"], u["xml"])))
                if ar < 0.10 and px < 0.07 and (best is None or px < best[1]):
                    best = (a, px, f"visual match, {px:.3f} difference")
        if best:
            a = best[0]
            tok = logo_token(a["type"], gt, a["theme"], aspect, shape)
            what = a["type"] if a["type"] == "banner" else f"{a['theme']} {a['type']}"
            entry.update(token=tok, kind="client_logo", confidence="high",
                         why=f"matches {brand.get('name')}'s {what} "
                             f"({best[2]}) on a {gt or 'unknown'} ground — the builder picks the "
                             f"visible variant per slot")
        elif area > 0.5:
            entry.update(token=None, kind="background", confidence="low",
                         why="covers most of the slide — background art, usually static")
        elif len(entry["on_slides"]) >= max(2, (len(parts) + 1) // 2):
            entry.update(token=None, kind="recurring", confidence="low",
                         suggestion=logo_token(None, gt, None, aspect, shape),
                         why=f"same image on slides {entry['on_slides']} — usually your own branding")
        else:
            alpha = (im.mode in ("RGBA", "LA") or "transparency" in im.info) and \
                im.convert("RGBA").getchannel("A").getextrema()[0] < 255
            looks = alpha or aspect >= 2.2 or area < 0.05 or shape == "ellipse"
            strip = frame[2] >= 0.6 * sw and aspect >= 2.5
            suggestion = "{bf:banner}" if strip else logo_token(None, gt, None, aspect, shape)
            if assets:
                why = (f"matches none of {brand.get('name')}'s logos — probably your own "
                       f"branding, a partner, or an older client logo")
            elif strip:
                why = "full-width strip — the previous client's banner?"
            elif looks:
                why = "logo-shaped (transparent or small) — the previous client's?"
            else:
                why = "photo or illustration — static unless the user says so"
            entry.update(token=None, kind="possible_logo" if looks else "picture",
                         confidence="low", suggestion=suggestion,
                         why=why + "; look at the preview")
        if extract:
            entry["preview"] = write_preview(im, u["xml"], ground, extract, n, u["id"])
        images.append(entry)

    if brand and brand.get("name") and not any(
            i["kind"] == "client_name" for i in text_items.values()):
        notes.append(f"the deck never mentions {brand['name']!r} — is this the right client domain?")
    if brand and assets and not any(i["kind"] == "client_logo" for i in images):
        notes.append(f"no picture matched {brand.get('name')}'s logos — the deck may use an older "
                     f"or recoloured logo; check the previews")
    grouped = [f"slide {i['slide']} #{i['id']}" for i in images if i["in_group"]]
    if grouped:
        notes.append(f"pictures inside groups: {grouped} — apply lifts a mapped one out of its "
                     f"group so the builder places it correctly")

    order = {"client_name": 0, "brand_field": 1, "client_domain": 2, "amount": 3, "date": 4,
             "labelled_value": 5, "repeated_name": 6}
    text_list = sorted(list(text_items.values()) + labelled,
                       key=lambda i: (order.get(i["kind"], 9),
                                      min((o["slide"] for o in i["occurrences"]), default=0)))
    return {
        "deck": os.path.basename(deck),
        "slides": len(parts),
        "brand": (brand or {}).get("name"),
        "text": text_list,
        "images": images,
        "existing_tokens": sorted(existing),
        "elsewhere": residue(files, [i for i in text_list if i["kind"] in ("client_name", "client_domain")],
                             skip_slides=True),
        "notes": notes,
    }


def labelled_values(models, text_items, used):
    """
    Short values that sit under or beside a short label — "Sector" / "Retail",
    "Duration" / "12 weeks". Classic per-deck fields no pattern can recognise.
    """
    covered = set(text_items)
    out, seen = [], {}
    for part, (xml, units, bg) in models.items():
        for u in units:
            if u["kind"] != "sp":
                continue
            paras = paragraphs(u["xml"])
            if len(paras) != 1:
                continue
            text = paras[0][0].strip()
            words = text.split()
            if not words or len(words) > 4 or text.endswith((".", "?", "!", ":")) \
                    or TOKEN_SPAN.search(text) or re.fullmatch(r"[\d.,]+\s?%", text) \
                    or any(c in text for c in covered) or DATE.search(text) or AMOUNT.search(text):
                continue
            label, lu = neighbour_label(u, units)
            if not label or len(label.split()) > 3 or label == text:
                continue
            # A label is styled apart from its value (smaller, greyer, bolder).
            # Same styling means two labels, or two list items, side by side.
            if text_style(lu["xml"]) == text_style(u["xml"]):
                continue
            occ = {"slide": slide_no(part), "shape": u["name"], "id": u["id"], "text": text}
            if text in seen:
                seen[text]["occurrences"].append(occ)
                continue
            base, tok, i = slug(label) or "value", None, 2
            tok = "{" + base + "}"
            while tok in used:
                tok, i = "{" + f"{base}_{i}" + "}", i + 1
            used.add(tok)
            seen[text] = {"find": text, "token": None, "kind": "labelled_value",
                          "confidence": "low", "suggestion": tok,
                          "why": f"short value under/next to the label {label!r} — per-deck field?",
                          "occurrences": [occ]}
            out.append(seen[text])
    # A slide full of label/value pairs is a data slide (coverage stats, a
    # spec sheet), not a set of deal fields. Leave it to the user to name.
    per_slide = {}
    for it in out:
        per_slide.setdefault(it["occurrences"][0]["slide"], []).append(it)
    return [it for items in per_slide.values() if len(items) <= 6 for it in items]


def write_preview(im, pic, ground, folder, slide, pid):
    os.makedirs(folder, exist_ok=True)
    im = crop_src_rect(im, pic).convert("RGBA")
    im.thumbnail((480, 480))
    rgb = tuple(int((ground or "FFFFFF")[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    out = Image.new("RGBA", im.size, rgb)
    out.alpha_composite(im)
    path = os.path.join(folder, f"slide{slide}-pic{pid}.png")
    out.convert("RGB").save(path)
    return path


# ── apply ────────────────────────────────────────────────────────────────────

def find_pattern(literal):
    p = re.escape(literal)
    if re.match(r"\w", literal):
        p = r"(?<!\w)" + p
    if re.search(r"\w$", literal):
        p += r"(?!\w)"
    return re.compile(p)


def replace_in_paragraph(inner, pattern, token):
    """
    Replace every match in one paragraph's visible text, across run
    boundaries if need be. The token takes the formatting of the run the
    match starts in; text before and after keeps its own. Existing tokens
    are never matched into.
    """
    runs, texts = run_texts(inner)
    breaks = [t.startswith("\n") for t in texts]
    count, pos = 0, 0
    while True:
        full = "".join(texts)
        guard = [(m.start(), m.end()) for m in TOKEN_SPAN.finditer(full)]
        m = pattern.search(full, pos)
        while m and any(m.start() < b and m.end() > a for a, b in guard):
            m = pattern.search(full, m.end())
        if not m:
            break
        s, e = m.start(), m.end()
        off, first = 0, None
        for i, t in enumerate(texts):
            a, b = off, off + len(t)
            off = b
            if b <= s or a >= e:
                continue
            if first is None:
                first = i
                texts[i] = t[: s - a] + token + (t[e - a:] if e <= b else "")
            else:
                texts[i] = t[e - a:] if e < b else ""
        count += 1
        pos = s + len(token)
    if not count:
        return inner, 0
    out, last = [], 0
    for r, t, br in zip(runs, texts, breaks):
        t = t[1:] if br and t.startswith("\n") else t
        body = r.group(1)
        new = T.sub(lambda _: f"<a:t>{escape(t)}</a:t>", body, count=1) if T.search(body) else body
        out.append(inner[last:r.start()] + f"<a:r>{new}</a:r>")
        last = r.end()
    out.append(inner[last:])
    return "".join(out), count


def replace_in_unit(unit, pattern, token):
    total = 0

    def one(m):
        nonlocal total
        new, c = replace_in_paragraph(m.group(1), pattern, token)
        total += c
        return f"<a:p>{new}</a:p>"

    return PARA.sub(one, unit), total


def slot_xml(sid, token, frame, shape, ground):
    x, y, cx, cy = frame
    ink = "6E6E6A" if tone(ground) != "light" else "9A9A94"
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(token)} slot"/>'
        f"<p:cNvSpPr/><p:nvPr/></p:nvSpPr>"
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="{shape}"><a:avLst/></a:prstGeom><a:noFill/>'
        f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{ink}"/></a:solidFill>'
        f'<a:prstDash val="dash"/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" '
        f'rtlCol="0" anchor="ctr"/><a:lstStyle/>'
        f'<a:p><a:pPr algn="ctr"><a:buNone/></a:pPr><a:r><a:rPr lang="en-US" sz="900" dirty="0">'
        f'<a:solidFill><a:srgbClr val="{ink}"/></a:solidFill></a:rPr>'
        f"<a:t>{escape(token)}</a:t></a:r></a:p></p:txBody></p:sp>"
    )


def slot_frame(frame, token, shape):
    """
    The slot a picture becomes, sized so the builder puts the next client's
    mark exactly where this one was.

    Cover slots (banner, icon, ellipses) and large squares (tight contain)
    fill their frame, so the picture's own frame is the slot. Every other
    slot is contain-fit inside a safe box of SAFE_W x SAFE_H — so the slot is
    the picture's frame grown by the inverse of that inset, around the same
    centre. The dashed box is bigger than the logo; the logo is not smaller.
    """
    x, y, cx, cy = frame
    if token in ("{bf:banner}", "{bf:icon}") or shape == "ellipse":
        return frame
    if abs(cx - cy) < int(0.05 * EMU) and cx > int(0.5 * EMU):
        return frame
    ncx, ncy = int(cx / SAFE_W), int(cy / SAFE_H)
    if abs(ncx - ncy) < int(0.05 * EMU) and ncx > int(0.5 * EMU):
        ncy += int(0.1 * EMU)      # stay out of tight-contain territory
    return x - (ncx - cx) // 2, y - (ncy - cy) // 2, ncx, ncy


def apply(deck, mapping_path, out):
    files = load(deck)
    theme = theme_colors(files)
    mapping = json.load(open(mapping_path))
    text_items = [i for i in mapping.get("text", []) if i.get("token") and i.get("find")]
    image_items = [i for i in mapping.get("images", []) if i.get("token")]
    text_items.sort(key=lambda i: -len(i["find"]))      # longest first: descriptions before names
    log, warnings = [], []
    hits = {i["find"]: 0 for i in text_items}
    changed = set()

    targets = slide_parts(files) + sorted(n for n in files if NOTES.fullmatch(n))
    for part in targets:
        is_slide = bool(SLIDE.fullmatch(part))
        n = slide_no(part) if is_slide else None
        xml = merge_split_runs(files[part].decode("utf-8", "replace"))
        original = xml

        # ── pictures → slots ────────────────────────────────────────────────
        for it in (image_items if is_slide else []):
            if it.get("slide") != n:
                continue
            _, units, bg = slide_model(files, part, theme, xml)
            u = next((u for u in units if u["kind"] == "pic" and u["id"] == it.get("id")), None)
            if not u or not u["frame"]:
                warnings.append(f"slide {n}: no picture with id {it.get('id')} — skipped {it['token']}")
                continue
            tok, shape = it["token"], prst_geom(u["xml"])
            ground = ground_under(u, units, bg)
            frame = slot_frame(u["frame"], tok, shape)
            groups = enclosing_groups(group_spans(xml), u["start"])
            slot = slot_xml(u["id"], tok, frame, shape, ground)
            if not groups or is_identity(groups):
                xml = xml[:u["start"]] + slot + xml[u["end"]:]
                where = ""
            else:
                # Lift out of the group: the builder reads slot geometry in
                # slide space, and a group's child space is not.
                g_start, g_end, _ = groups[-1]
                inner = xml[g_start:u["start"]] + xml[u["end"]:g_end]
                if not re.search(r"<p:(?:sp|pic|graphicFrame|grpSp|cxnSp)[\s>]",
                                 inner[len("<p:grpSp>"):]):
                    xml = xml[:g_start] + slot + xml[g_end:]
                else:
                    xml = xml[:g_start] + inner + slot + xml[g_end:]
                where = " (lifted out of its group)"
            dropped = [d for d in ("<a:ln", "<a:effectLst>") if d in u["xml"].split("<p:spPr", 1)[-1]]
            log.append((part, tok, f"picture #{u['id']} -> slot {inches(frame)} in{where}"
                        + (f"; its {', '.join(d.strip('<>') for d in dropped)} was dropped"
                           if dropped else "")))

        # ── text → tokens, one shape at a time ──────────────────────────────
        for it in text_items:
            if is_slide and it.get("slides") and n not in it["slides"]:
                continue
            pat = find_pattern(it["find"])
            out_parts, pos, count = [], 0, 0
            for m in UNIT.finditer(xml):
                if m.group(1) == "pic":
                    continue
                new, c = replace_in_unit(m.group(0), pat, it["token"])
                if c:
                    out_parts += [xml[pos:m.start()], new]
                    pos = m.end()
                    count += c
            if count:
                xml = "".join(out_parts) + xml[pos:]
                hits[it["find"]] += count if is_slide else 0
                log.append((part, it["token"], f"{count}x {it['find']!r}"))

        if xml != original:
            files[part] = xml.encode("utf-8")
            changed.add(part)

    for f, c in hits.items():
        if not c:
            warnings.append(f"{f!r} was not found on any slide — nothing replaced")

    removed = prune_media(files, changed)
    for part in changed | {rels_path(p) for p in changed if rels_path(p) in files}:
        try:
            ET.fromstring(files[part])
        except ET.ParseError as e:
            sys.exit(f"refusing to write: {part} is no longer well-formed XML ({e})")

    # the sent deck's own title and properties usually name the previous client
    from build_deck import clear_doc_props
    clear_doc_props(files, os.path.splitext(os.path.basename(out))[0])

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)

    for part, tok, note in log:
        print(f"  {part.rsplit('/', 1)[-1]:18s} {tok:26s} {note}")
    for m in removed:
        print(f"  removed unused media {m} (the previous client's file does not ship in the template)")
    left = residue(files, [i for i in text_items
                           if i.get("kind") in ("client_name", "client_domain")
                           or i["token"].startswith("{bf:")])
    if left:
        print("\n  STILL MENTIONS THE PREVIOUS CLIENT (not a slide text box):")
        for r in left:
            print(f"    {r}")
    if warnings:
        print(f"\n  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    ! {w}")
    print(f"\nwritten: {out}")
    return 1 if warnings else 0


def prune_media(files, changed):
    """Drop relationships nothing references any more, then media nothing targets."""
    ct = files["[Content_Types].xml"].decode("utf-8")
    for part in changed:
        rp = rels_path(part)
        if rp not in files:
            continue
        xml = files[part].decode("utf-8", "replace")
        rels = files[rp].decode("utf-8")

        def keep(m):
            rid = re.search(r'Id="([^"]+)"', m.group(0)).group(1)
            is_image = "/relationships/image" in m.group(0)
            return m.group(0) if not is_image or f'"{rid}"' in xml else ""

        files[rp] = re.sub(r"<Relationship\b[^>]*/>", keep, rels).encode("utf-8")
    targeted = set()
    for p in list(files):
        if p.endswith(".rels"):
            src = p.replace("_rels/", "").rsplit(".rels", 1)[0]
            if not src:
                continue            # package root: docProps, not media
            targeted |= {t for _, t in relationships(files, src).values()}
    removed = []
    for p in [p for p in files if p.startswith("ppt/media/") and p not in targeted]:
        del files[p]
        ct = re.sub(rf'<Override PartName="/{re.escape(p)}"[^>]*/>', "", ct)
        removed.append(p)
    files["[Content_Types].xml"] = ct.encode("utf-8")
    return removed


def residue(files, items, skip_slides=False):
    """Where the previous client's name still appears outside slide text boxes."""
    out = []
    lits = {i["find"] for i in items}
    for part in sorted(files):
        if not part.endswith(".xml"):
            continue
        raw = html.unescape(files[part].decode("utf-8", "replace"))
        if skip_slides and SLIDE.fullmatch(part):
            # slide text is proposed elsewhere; alt text on shapes is not
            raw = " ".join(re.findall(r'<p:cNvPr\b[^>]*?\b(?:descr|title)="([^"]*)"', raw))
        for lit in lits:
            if find_pattern(lit).search(raw):
                where = "speaker notes" if NOTES.fullmatch(part) else \
                        "document properties" if part.startswith("docProps/") else \
                        "alt text / hidden XML" if SLIDE.fullmatch(part) else part
                out.append(f"{lit!r} in {part} ({where})")
    return out


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts = dict(a.split("=", 1) if "=" in a else (a, True) for a in argv if a.startswith("--"))
    pos = [a for a in argv if not a.startswith("--")]
    if "--detect" in opts and len(pos) == 1:
        brand = json.load(open(opts["--brand"])) if "--brand" in opts else None
        print(json.dumps(detect(pos[0], brand, opts.get("--extract")), indent=2, ensure_ascii=False))
    elif "--apply" in opts and len(pos) == 3:
        sys.exit(apply(*pos))
    else:
        sys.exit("usage: instrument_template.py --detect deck.pptx [--brand=brand.json] "
                 "[--extract=DIR]\n       instrument_template.py --apply deck.pptx "
                 "mapping.json out.pptx")

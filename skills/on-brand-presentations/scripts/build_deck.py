#!/usr/bin/env python3
"""
Fill an instrumented PPTX template with brand data and user-supplied values.

Two token namespaces, one rule:
  {bf:*}            resolved automatically from a Brandfetch get_brand response
  {anything_else}   yours — supplied via --values, never guessed

Slots are found by TEXT CONTENT, not shape name (slide editors export generic
names like "Text 13"). Geometry comes from each slot shape's own xfrm, so
nothing about any particular template is hardcoded — move, resize or reorder
slots freely and rebuild.

    python3 build_deck.py template.pptx brand.json out.pptx \
        [--values=values.json] [--slides=1,3]

An unfilled token stays visible as {token} in the output, so a gap reads as an
obvious blank to fill rather than a silent omission.
"""
import io
import json
import re
import sys
import shutil
import zipfile
import subprocess

from PIL import Image

import bf_fields as BF

EMU = 914400
SAFE_W, SAFE_H = 0.76, 0.62      # inset for contain-fit inside a slot frame

# Tolerant matcher: accepts {bf:x}, {{bf:x}, {{bf:x}} — the template has
# malformed doubled braces on two slots and exact matching would silently
# skip them, leaving those cards empty.
TOKEN = re.compile(r"\{{1,2}(bf:[A-Za-z]+)\}{1,2}")

# Text widths are MEASURED in a real font, not estimated — a guessed advance
# width is how text slots end up overflowing. The bundled template uses Arial;
# Liberation Sans is metrics-compatible and present on most Linux systems. If
# your template uses another font, put its .ttf paths first in these lists.
FONT_CANDIDATES = {
    False: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    True: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def measure(text, pt, bold=False):
    """(width_pt, line_height_pt) for text rendered at pt."""
    from PIL import ImageFont

    for path in FONT_CANDIDATES[bold]:
        try:
            # rasterise at 4x for sub-point precision, then scale back
            f = ImageFont.truetype(path, int(pt * 4))
            return f.getlength(text) / 4, pt * 1.25
        except Exception:
            continue
    return len(text) * pt * 0.5, pt * 1.25   # crude fallback: no font found


def native_size(path):
    with Image.open(path) as im:
        return im.size


def contain(frame, native, safe_w=SAFE_W, safe_h=SAFE_H):
    fw, fh = frame
    nw, nh = native
    sw, sh = int(fw * safe_w), int(fh * safe_h)
    scale = min(sw / nw, sh / nh)
    cx, cy = round(nw * scale), round(nh * scale)
    return (fw - cx) // 2, (fh - cy) // 2, cx, cy


def cover(frame, native):
    fw, fh = frame
    nw, nh = native
    scale = max(fw / nw, fh / nh)
    rw, rh = nw * scale, nh * scale
    src = {}
    if rh > fh + 1:
        f = ((rh - fh) / rh) / 2
        src = {"t": round(f * 100000), "b": round(f * 100000)}
    elif rw > fw + 1:
        f = ((rw - fw) / rw) / 2
        src = {"l": round(f * 100000), "r": round(f * 100000)}
    return 0, 0, fw, fh, src


def src_rect(src):
    if not src:
        return ""
    return "<a:srcRect " + " ".join(f'{k}="{v}"' for k, v in sorted(src.items())) + "/>"


def geom(fragment):
    m = re.search(
        r'<a:off x="(-?\d+)" y="(-?\d+)"\s*/>\s*<a:ext cx="(\d+)" cy="(\d+)"\s*/>',
        fragment,
    )
    return tuple(int(v) for v in m.groups()) if m else None


def prst_geom(fragment):
    """Preserve the placeholder's shape (ellipse for the icon circle, etc.)."""
    m = re.search(r'<a:prstGeom prst="(\w+)"', fragment)
    return m.group(1) if m else "rect"


def ln_width(fragment):
    """
    Width (EMU) of the shape's own <a:ln> stroke, if any, else 0.

    OOXML centers a stroke on its shape's boundary by default (half draws
    inside, half bleeds outside the nominal xfrm). A same-size picture
    overlay only ever covers the inside half, leaving the outward bleed
    visible as a thin ring around the image — most visible on the {bf:icon}
    avatar circle, whose ring is drawn in the same white as its fill.
    """
    m = re.search(r'<a:ln w="(\d+)"', fragment)
    return int(m.group(1)) if m else 0


def fetch(url, dest):
    """
    Download with curl, exactly as given. The `src` URLs in a get_brand
    response carry per-request credentials in `?c=` — edit or rebuild the URL
    and the CDN 302s to a hotlink-policy page, which surfaces as a 403.
    """
    import os
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    subprocess.run(
        ["curl", "-sS", "--fail", "-o", dest, url], check=True, capture_output=True
    )
    return dest


def to_raster(path, width=1600):
    """
    PNG path for an asset PowerPoint and Pillow can both use.

    Many brands publish some variants as SVG only (often the main logo and
    symbol), and older PowerPoint will not render WebP. Rasterise SVG with
    cairosvg, else librsvg's rsvg-convert, else ImageMagick; convert WebP
    with Pillow. Anything else is returned unchanged.
    """
    base, _, ext = path.rpartition(".")
    png = base + ".png"
    if ext == "webp":
        Image.open(path).save(png)
        return png
    if ext != "svg":
        return path
    try:
        import cairosvg
        cairosvg.svg2png(url=path, write_to=png, output_width=width)
        return png
    except ImportError:
        pass
    for cmd in (["rsvg-convert", "-w", str(width), "-o", png, path],
                ["magick", "-background", "none", "-density", "300", path,
                 "-resize", f"{width}x", png]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, check=True, capture_output=True)
            return png
    raise RuntimeError(f"{path} is SVG-only: pip install cairosvg (or install librsvg)")


# A mark counts as visible when at least this share of its opaque pixels
# reaches CONTRAST against the ground. The failures this exists for sit near
# 1:1 — white on off-white is ~1.15, black on near-black ~1.1 — while a
# brand-green symbol on off-white (~1.6) reads fine. A 2:1 bar rejected
# exactly that green, so the bar is set between the two.
VISIBLE, CONTRAST = 0.5, 1.5
_visibility_cache = {}


def _rel_lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def visibility(path, ground):
    """
    Share of the mark's opaque pixels that stand out against ground (hex).

    Measured on the actual file, never inferred from the theme label: "dark"
    variants are often coloured, and a coloured mark can be perfectly visible
    on a dark-grey slide where a black one would vanish.
    """
    key = (path, ground)
    if key not in _visibility_cache:
        im = Image.open(path).convert("RGBA")
        im.thumbnail((160, 160))
        g = _rel_lum(tuple(int(ground[i:i + 2], 16) for i in (0, 2, 4)))
        n = ok = 0
        for r, gg, b, a in im.getdata():
            if a < 128:
                continue
            n += 1
            l = _rel_lum((r, gg, b))
            if (max(l, g) + 0.05) / (min(l, g) + 0.05) >= CONTRAST:
                ok += 1
        _visibility_cache[key] = ok / n if n else 0.0
    return _visibility_cache[key]


def pick_variant(slot, variants, ground):
    """
    (theme, score, note) for a themed slot, or (None, None, note) to leave it
    empty. Try the token's preferred theme first — or, for {bf:logo} and
    {bf:symbol}, the theme the ground calls for (light mark on a dark ground)
    — and take the first variant that is actually visible there.
    """
    pref = BF.THEMED[slot][1]
    if pref is None:
        dark_ground = ground is not None and _rel_lum(
            tuple(int(ground[i:i + 2], 16) for i in (0, 2, 4))) < 0.18
        pref = "light" if dark_ground else "dark"
    order = [t for t in (pref, "dark" if pref == "light" else "light") if t in variants]
    if ground is None:
        return (order[0], None, "ground unknown — token preference used") if order else \
               (None, None, "no variant")
    scores = {t: visibility(variants[t]["path"], ground) for t in order}
    for t in order:
        if scores[t] >= VISIBLE:
            return t, scores[t], f"{scores[t]:.0%} visible on #{ground}"
    tried = ", ".join(f"{t} {v:.0%}" for t, v in scores.items())
    return None, None, f"LEFT EMPTY: no variant visible on #{ground} ({tried})"


def merge_split_runs(xml):
    """
    Slide editors (PowerPoint included) split text mid-string across <a:r>
    runs whenever a token is typed in stages or spell-checked — '{start_' in
    one run, 'date}' in the next — so the token never appears whole in any
    single <a:t> and exact-match substitution silently misses it.

    Merge adjacent runs in a paragraph whose formatting is effectively
    identical. Volatile editor attributes (dirty, smtClean, err, noProof) are
    stripped before comparing: they mark spell-check state, not appearance,
    and editors apply them inconsistently across runs that look the same.

    Only runs that are truly adjacent merge. A soft line break (<a:br/>) or a
    field between runs ends the block: merging the whole paragraph into its
    first block once duplicated every line after a shift-enter break.
    """
    volatile = re.compile(r'\s+(?:dirty|smtClean|err|noProof)="[^"]*"')

    def merge_block(block):
        runs = re.findall(r"<a:r>(.*?)</a:r>", block.group(0), re.S)
        if len(runs) < 2:
            return block.group(0)
        merged = []
        for run in runs:
            rpr = re.search(r"<a:rPr[^>]*/>", run) or re.search(
                r"<a:rPr[^>]*>.*?</a:rPr>", run, re.S
            )
            t = re.search(r"<a:t>(.*?)</a:t>", run, re.S)
            rpr_raw = rpr.group(0) if rpr else ""
            key = volatile.sub("", rpr_raw)
            text = t.group(1) if t else ""
            if merged and merged[-1][0] == key:
                merged[-1][2] += text
            else:
                merged.append([key, rpr_raw, text])
        return "".join(
            f"<a:r>{raw}<a:t>{text}</a:t></a:r>" for _, raw, text in merged
        )

    def merge_para(inner):
        # each contiguous run block separately, leaving pPr/br/endParaRPr intact
        return re.sub(r"(?:<a:r>.*?</a:r>)+", merge_block, inner, flags=re.S)

    return re.sub(
        r"(<a:p>)(.*?)(</a:p>)",
        lambda m: m.group(1) + merge_para(m.group(2)) + m.group(3),
        xml,
        flags=re.S,
    )


def fit_text_slots(xml, text_vals, log, slide):
    """Grow text slot frames that are sized for the placeholder token, not the content."""
    slots = []
    for m in re.finditer(r"<p:sp>(?:(?!</p:sp>).)*?</p:sp>", xml, re.S):
        sp = m.group(0)
        body = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S))
        tok = TOKEN.search(body)
        g = geom(sp)
        if tok and g:
            slots.append({"tok": "{" + tok.group(1) + "}", "geom": g,
                          "span": (m.start(), m.end()), "sp": sp})
    if not slots:
        return xml

    right_edge = max(s["geom"][0] + s["geom"][2] for s in slots)
    edits = []
    for s in slots:
        slot = s["tok"]
        val = text_vals.get(slot)
        if not val:
            continue
        x, y, cx, cy = s["geom"]
        same_row = [o["geom"][0] for o in slots
                    if o is not s and abs(o["geom"][1] - y) < int(0.15 * EMU)
                    and o["geom"][0] > x]
        limit = min(same_row) if same_row else right_edge
        available = max(cx, limit - x - int(0.04 * EMU))
        sz = re.search(r'sz="(\d+)"', s["sp"])
        pt = int(sz.group(1)) / 100 if sz else 10
        bold = 'b="1"' in s["sp"]
        w_pt, line_h = measure(val, pt, bold)
        need = int(w_pt / 72 * EMU)
        if need <= cx:
            continue
        new_cx = min(need, available)
        lines = max(1, -(-need // max(1, new_cx)))
        new_cy = max(cy, int(lines * line_h / 72 * EMU * 1.15))
        fixed = s["sp"].replace(
            f'<a:ext cx="{cx}" cy="{cy}"/>', f'<a:ext cx="{new_cx}" cy="{new_cy}"/>', 1
        )
        edits.append((s["span"], fixed))
        log.append((slide, slot,
                    f"resized {cx/EMU:.2f}x{cy/EMU:.2f} -> "
                    f"{new_cx/EMU:.2f}x{new_cy/EMU:.2f}in ({lines} line/s @ {pt}pt)"))
    for (a, b), fixed in sorted(edits, key=lambda e: -e[0][0]):
        xml = xml[:a] + fixed + xml[b:]
    return xml


def strip_placeholder_outlines(xml, filled):
    """
    Remove the dashed outline from any slot shape whose token is about to be
    filled.

    A dashed border is a placeholder marker, not design: it tells whoever is
    instrumenting the template where a slot is. Once the slot holds real
    content the marker has done its job, and leaving it in ships a client deck
    with dashed boxes around the customer's logo.

    Scoped deliberately:

    - Only the <a:ln> goes. The shape's fill is often load-bearing design
      (Rule 3 — the logo tiles carry their own solidFill on the very shape
      that holds the token), so fills are never touched.
    - Only DASHED lines go. A solid stroke is design — the {bf:icon} avatar
      ring is a solid white <a:ln> that the cover-fit bleed exists to meet.
    - Only shapes whose token will actually be FILLED. An unfilled token keeps
      its dashed box, so a gap stays visibly marked rather than becoming an
      invisible empty rectangle.

    Runs before the image-slot pass, so ln_width() reports 0 for a stripped
    shape and no pointless bleed is applied to what was only a placeholder.
    """
    out, pos = [], 0
    for m in re.finditer(r"<p:sp>(?:(?!</p:sp>).)*?</p:sp>", xml, re.S):
        sp = m.group(0)
        body = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S))
        toks = set(re.findall(r"\{{1,2}[^{}]{1,40}\}{1,2}", body))
        toks = {"{" + t.strip("{}") + "}" for t in toks}
        if not toks & filled:
            continue
        cleaned = re.sub(
            r"<a:ln\b[^>]*>(?:(?!</a:ln>).)*?"
            r'<a:prstDash val="(?:dash|sysDash|lgDash|dashDot|lgDashDot'
            r'|lgDashDotDot|sysDashDot|sysDashDotDot|sysDot|dot)"/>'
            r"(?:(?!</a:ln>).)*?</a:ln>",
            "<a:ln><a:noFill/></a:ln>",
            sp,
            flags=re.S,
        )
        if cleaned != sp:
            out.append(xml[pos:m.start()])
            out.append(cleaned)
            pos = m.end()
    out.append(xml[pos:])
    return "".join(out)


def build(template, brand, out, only_slides=None, values=None):
    text_vals, images, missing = BF.resolve(brand)
    name = text_vals["{bf:name}"]

    # download every needed asset once — both themes for logo/symbol slots,
    # since which one is visible is only known per slot, from its ground
    downloaded = {}

    def download(key, fmt):
        if key not in downloaded:
            ext = "jpg" if fmt["format"] in ("jpeg", "jpg") else fmt["format"]
            path = to_raster(fetch(fmt["src"], f"assets/{key}.{ext}"))
            downloaded[key] = {"path": path, "ext": path.rpartition(".")[2],
                               "native": native_size(path), "key": key}
        return downloaded[key]

    assets = {}
    for slot, info in images.items():
        if slot in BF.THEMED:
            typ = BF.THEMED[slot][0]
            variants = {t: download(f"{typ}-{t}", f) for t, f in info["variants"].items()}
        else:
            variants = {None: download(slot.strip("{}").replace("bf:", ""), info)}
        assets[slot] = {"fit": info["fit"], "variants": variants}

    with zipfile.ZipFile(template) as z:
        files = {n: z.read(n) for n in z.namelist()}

    slides = sorted(
        (n for n in files if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
        key=lambda s: int(re.search(r"\d+", s.rsplit("/", 1)[-1]).group()),
    )
    if only_slides:
        slides = [s for s in slides
                  if int(re.search(r"\d+", s.rsplit("/", 1)[-1]).group()) in only_slides]

    log = []

    # media + content types are registered only for variants actually placed
    ct_box = [files["[Content_Types].xml"].decode("utf-8")]
    # what this build has stored: a bf_ file already in the template is a
    # leftover from the deck it was made from, so it is overwritten, never reused
    placed = set()

    def register(a):
        media = f"ppt/media/bf_{a['key']}.{a['ext']}"
        a["media"] = media
        if media in placed:
            return media
        placed.add(media)
        ct = ct_box[0]
        files[media] = open(a["path"], "rb").read()
        mime = "image/jpeg" if a["ext"] in ("jpg", "jpeg") else f"image/{a['ext']}"
        if f'Extension="{a["ext"]}"' not in ct:
            ct = ct.replace(
                "<Types",
                "<Types", 1
            )
            # Default declarations must precede Overrides in practice; appending
            # inside <Types> is valid and PowerPoint accepts it.
            ct = ct.replace(
                "</Types>",
                f'<Default Extension="{a["ext"]}" ContentType="{mime}"/></Types>',
            )
        if f'PartName="/{media}"' not in ct:
            ct = ct.replace("</Types>",
                            f'<Override PartName="/{media}" ContentType="{mime}"/></Types>')
        ct_box[0] = ct
        return media

    # the ground under each slot is read with the instrumenter's slide model
    from instrument_template import ground_under, slide_model, theme_colors
    theme = theme_colors(files)

    for slide in slides:
        xml = files[slide].decode("utf-8", "replace")
        rels_path = f"ppt/slides/_rels/{slide.rsplit('/',1)[-1]}.rels"
        rels = files[rels_path].decode("utf-8")
        next_rid = max(int(n) for n in re.findall(r'Id="rId(\d+)"', rels)) + 1
        new_rels = []
        rid_for = {}

        # Placeholder markers come off before anything is filled, so a filled
        # slot never ships with its dashed instrumentation border.
        # Themed slots are stripped one by one below, once a visible variant
        # is known: a slot left empty keeps its dashed marker.
        filled = {s for s, v in text_vals.items() if v}
        filled |= {s for s in assets if s not in BF.THEMED}
        filled |= {t for t, v in (values or {}).items() if v}
        xml = strip_placeholder_outlines(xml, filled)
        _, units, slide_bg = slide_model(files, slide, theme, xml)
        unit_at = {u["start"]: u for u in units}

        # ── image slots ──────────────────────────────────────────────────────
        # The slot shape often CARRIES the design: the three logo tiles have
        # their own solidFill (242426 / 222222 / 242424) on the same <p:sp>
        # that holds the token. Replacing the shape destroys the tile. So we
        # keep the shape, blank its placeholder text, and append a fitted
        # <p:pic> after it in z-order.
        overlays = []
        out_parts, pos = [], 0
        for m in re.finditer(r"<p:sp>(?:(?!</p:sp>).)*?</p:sp>", xml, re.S):
            sp = m.group(0)
            body = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S))
            tok = TOKEN.search(body)
            if not tok:
                continue
            slot = "{" + tok.group(1) + "}"
            if slot not in assets:
                continue
            frame = geom(sp)
            if not frame:
                log.append((slide, slot, "SKIP no xfrm"))
                continue
            variants = assets[slot]["variants"]
            pick_note = ""
            if slot in BF.THEMED:
                u = unit_at.get(m.start())
                ground = (u["fill"] or ground_under(u, units, slide_bg)) if u else slide_bg
                theme_pick, _, pick_note = pick_variant(slot, variants, ground)
                if theme_pick is None:
                    log.append((slide, slot, pick_note))
                    continue
                a = variants[theme_pick]
                pick_note = f" · {theme_pick} {BF.THEMED[slot][0]}, {pick_note}"
                sp = strip_placeholder_outlines(sp, {slot})
            else:
                a = variants[None]
            media = register(a)
            fx, fy, fw, fh = frame
            shape = prst_geom(sp)

            is_square = abs(fw - fh) < int(0.05 * EMU)
            is_large = fw > int(0.5 * EMU)
            fit = (
                "cover"
                if slot == "{bf:banner}" or slot == "{bf:icon}" or shape == "ellipse"
                else "contain"
            )
            # Large square frames (avatar slots) use tight contain — no safe-box
            # inset — so the symbol fills as much of the square as possible
            # without cropping. Regular logo tiles keep the safe-box.
            tight = is_square and is_large

            # A cover-fit picture only ever fills the shape's nominal xfrm.
            # If that shape also carries its own <a:ln> stroke (the {bf:icon}
            # avatar ring), half the stroke bleeds outward past that xfrm by
            # OOXML's default centered alignment, and a same-size picture
            # never reaches it — leaving a thin ring of the shape's own fill
            # visible around the image. Inflate the frame by the stroke width
            # (centered) so the picture bleeds out to meet it.
            bleed = ln_width(sp) if fit == "cover" else 0
            if bleed:
                half = bleed // 2
                fx, fy = fx - half, fy - half
                fw, fh = fw + bleed, fh + bleed

            if fit == "cover":
                ox, oy, cx, cy, sr = cover((fw, fh), a["native"])
                srx = src_rect(sr)
            else:
                # tight=True: no safe-box inset for large avatar squares
                sw = 1.0 if tight else SAFE_W
                sh = 1.0 if tight else SAFE_H
                ox, oy, cx, cy = contain((fw, fh), a["native"], sw, sh)
                srx = ""

            if media not in rid_for:
                rid_for[media] = f"rId{next_rid}"
                new_rels.append(
                    f'<Relationship Id="rId{next_rid}" Type="http://schemas.'
                    f'openxmlformats.org/officeDocument/2006/relationships/image" '
                    f'Target="../{media[4:]}"/>'
                )
                next_rid += 1
            rid = rid_for[media]

            # blank the placeholder text but keep the shape and its fill
            stripped = re.sub(r"<a:t>.*?</a:t>", "<a:t></a:t>", sp, flags=re.S)

            overlays.append(
                f"<p:pic><p:nvPicPr>"
                f'<p:cNvPr id="{9000+len(overlays)}" name="{slot}"/>'
                f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
                f"<p:nvPr/></p:nvPicPr>"
                f'<p:blipFill><a:blip r:embed="{rid}"/>{srx}'
                f"<a:stretch><a:fillRect/></a:stretch></p:blipFill>"
                f"<p:spPr><a:xfrm>"
                f'<a:off x="{fx+ox}" y="{fy+oy}"/><a:ext cx="{cx}" cy="{cy}"/>'
                f"</a:xfrm>"
                f'<a:prstGeom prst="{"ellipse" if shape=="ellipse" else "rect"}">'
                f"<a:avLst/></a:prstGeom>"
                f"</p:spPr></p:pic>"
            )
            out_parts.append(xml[pos:m.start()])
            out_parts.append(stripped)
            pos = m.end()
            bleed_note = f" +{bleed}emu bleed" if bleed else ""
            log.append((slide, slot,
                        f"{fit:7s} {cx}x{cy} in {shape} tile{bleed_note}{pick_note}"))
        out_parts.append(xml[pos:])
        xml = "".join(out_parts)

        # append overlays at the end of the shape tree so they sit on top
        if overlays:
            xml = xml.replace("</p:spTree>", "".join(overlays) + "</p:spTree>")

        # ── text slots ───────────────────────────────────────────────────────
        # Merge runs split mid-token by Pitch's exporter, then resize and substitute.
        xml = merge_split_runs(xml)
        xml = fit_text_slots(xml, text_vals, log, slide)

        # Token-by-token substitution. No composite/literal patterns: those
        # would bind the builder to one template's exact wording, and the
        # individual replacements below cover the same ground.
        for slot, val in text_vals.items():
            if not val:
                continue
            xml = xml.replace(slot, val)
        # User tokens come from the CONVERSATION, never from the API. Only
        # substitute values the user actually supplied — an absent token stays
        # visible as {token} so the gap is obvious rather than silently blank.
        for token, val in (values or {}).items():
            if val:
                xml = xml.replace(token, str(val))

        files[slide] = xml.encode("utf-8")
        if new_rels:
            files[rels_path] = rels.replace(
                "</Relationships>", "".join(new_rels) + "</Relationships>"
            ).encode("utf-8")

    files["[Content_Types].xml"] = ct_box[0].encode("utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in files.items():
            z.writestr(n, d)

    # leftovers, visible text only
    leftover = []
    for slide in slides:
        vis = "".join(re.findall(r"<a:t>(.*?)</a:t>",
                                 files[slide].decode("utf-8", "replace"), re.S))
        leftover += [(slide, t) for t in re.findall(r"\{[^}]{1,30}\}", vis)]

    return {"text": text_vals, "missing": missing, "log": log, "leftover": leftover}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3:
        sys.exit("usage: build_deck.py template.pptx brand.json out.pptx "
                 "[--values=values.json] [--slides=1,3]")
    tpl, bj, out = args

    only, values = None, None
    for a in sys.argv[1:]:
        if a.startswith("--slides="):
            only = {int(v) for v in a.split("=", 1)[1].split(",")}
        elif a.startswith("--values="):
            values = json.load(open(a.split("=", 1)[1]))

    r = build(tpl, json.load(open(bj)), out, only, values)

    for k, v in r["text"].items():
        print(f"  {k:26s} {v!r}")
    print()
    for slide, slot, note in r["log"]:
        print(f"  {slide.rsplit('/',1)[-1]:12s} {slot:26s} {note}")
    if r["missing"]:
        print(f"\n  missing (left empty): {r['missing']}")
    if r["leftover"]:
        print(f"\n  UNFILLED TOKENS: {r['leftover']}")
    print(f"\nwritten: {out}")

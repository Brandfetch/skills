#!/usr/bin/env python3
"""
One layout, four outputs: PNG (preview), PPTX, PDF, HTML.

No third-party writers: the PPTX and PDF packages are written directly, so
the skill runs wherever Pillow does. Every logo stays a separate object —
a movable picture in PowerPoint, an image XObject in the PDF, an <img> in
the HTML — never one flattened screenshot of the wall.
"""
import base64
import html
import io
import os
import zipfile
import zlib

from PIL import Image, ImageDraw, ImageFont

from layout import SLIDE_W, SLIDE_H, MARGIN_X

EMU = 914400
TITLE_PT = 28
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(px):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def export_px(m, dpi=300):
    """The mark at print resolution, never upscaled past its source."""
    w = max(1, min(m["image"].width, round(m["w"] * dpi)))
    h = max(1, round(w / m["aspect"]))
    return m["image"].resize((w, h), Image.LANCZOS)


# ── PNG ──────────────────────────────────────────────────────────────────────

def png(path, marks, spec, dpi=150):
    W, H = round(SLIDE_W * dpi), round(SLIDE_H * dpi)
    canvas = Image.new("RGBA", (W, H), _rgb(spec["background"]) + (255,))
    if spec.get("title"):
        d = ImageDraw.Draw(canvas)
        d.text((MARGIN_X * dpi, 0.75 * dpi), spec["title"], fill=_rgb(spec["text"]),
               font=_font(round(TITLE_PT / 72 * dpi)), anchor="ls")
    for m in marks:
        im = m["image"].resize((max(1, round(m["w"] * dpi)), max(1, round(m["h"] * dpi))),
                               Image.LANCZOS)
        canvas.alpha_composite(im, (round(m["x"] * dpi), round(m["y"] * dpi)))
    canvas.convert("RGB").save(path)
    return path


# ── PPTX ─────────────────────────────────────────────────────────────────────

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "application/vnd.openxmlformats-officedocument.presentationml"
GRP = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
       '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
       '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
X = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _rels(items):
    body = "".join(f'<Relationship Id="{i}" Type="{t}" Target="{g}"/>' for i, t, g in items)
    return (X + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            f'relationships">{body}</Relationships>')


def pptx(path, marks, spec):
    e = lambda inches: round(inches * EMU)
    parts, pics, media_rels = {}, [], []
    for i, m in enumerate(marks, start=1):
        buf = io.BytesIO()
        export_px(m).save(buf, "PNG", optimize=True)
        parts[f"ppt/media/logo{i}.png"] = buf.getvalue()
        rid = f"rId{i + 1}"
        media_rels.append((rid, f"{REL}/image", f"../media/logo{i}.png"))
        pics.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{i + 10}" name="{html.escape(m["name"])}" '
            f'descr="{html.escape(m["name"])} logo"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/>'
            f'</p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/>'
            f'<a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm>'
            f'<a:off x="{e(m["x"])}" y="{e(m["y"])}"/><a:ext cx="{e(m["w"])}" cy="{e(m["h"])}"/>'
            f'</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')

    title = ""
    if spec.get("title"):
        title = (
            f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/>'
            f'</p:nvSpPr><p:spPr><a:xfrm><a:off x="{e(MARGIN_X)}" y="{e(0.45)}"/>'
            f'<a:ext cx="{e(SLIDE_W - 2 * MARGIN_X)}" cy="{e(0.6)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="b"/>'
            f'<a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="{TITLE_PT * 100}" b="1" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{spec["text"]}"/></a:solidFill>'
            f'<a:latin typeface="Arial"/><a:cs typeface="Arial"/></a:rPr>'
            f'<a:t>{html.escape(spec["title"])}</a:t></a:r></a:p></p:txBody></p:sp>')

    slide = (X + f'<p:sld {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr '
             f'val="{spec["background"]}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
             f'<p:spTree>{GRP}{title}{"".join(pics)}</p:spTree></p:cSld>'
             f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')

    parts.update({
        "[Content_Types].xml": X + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            f'<Override PartName="/ppt/presentation.xml" ContentType="{CT}.presentation.main+xml"/>'
            f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{CT}.slideMaster+xml"/>'
            f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{CT}.slideLayout+xml"/>'
            f'<Override PartName="/ppt/slides/slide1.xml" ContentType="{CT}.slide+xml"/>'
            f'<Override PartName="/ppt/presProps.xml" ContentType="{CT}.presProps+xml"/>'
            f'<Override PartName="/ppt/viewProps.xml" ContentType="{CT}.viewProps+xml"/>'
            f'<Override PartName="/ppt/tableStyles.xml" ContentType="{CT}.tableStyles+xml"/>'
            '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'),
        "_rels/.rels": _rels([
            ("rId1", f"{REL}/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", f"{REL}/extended-properties", "docProps/app.xml")]),
        "docProps/core.xml": X + (
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{html.escape(spec.get("title") or "Logo wall")}</dc:title></cp:coreProperties>'),
        "docProps/app.xml": X + (
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>Brandfetch logo wall</Application><Slides>1</Slides></Properties>'),
        "ppt/presentation.xml": X + (
            f'<p:presentation {NS} saveSubsetFonts="1">'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
            f'<p:sldSz cx="{e(SLIDE_W)}" cy="{e(SLIDE_H)}"/><p:notesSz cx="6858000" cy="9144000"/>'
            '</p:presentation>'),
        "ppt/_rels/presentation.xml.rels": _rels([
            ("rId1", f"{REL}/slideMaster", "slideMasters/slideMaster1.xml"),
            ("rId2", f"{REL}/slide", "slides/slide1.xml"),
            ("rId3", f"{REL}/theme", "theme/theme1.xml"),
            ("rId4", f"{REL}/presProps", "presProps.xml"),
            ("rId5", f"{REL}/viewProps", "viewProps.xml"),
            ("rId6", f"{REL}/tableStyles", "tableStyles.xml")]),
        "ppt/presProps.xml": X + f'<p:presentationPr {NS}/>',
        "ppt/viewProps.xml": X + (f'<p:viewPr {NS}><p:normalViewPr><p:restoredLeft sz="15620"/>'
                                  '<p:restoredTop sz="94660"/></p:normalViewPr>'
                                  '<p:gridSpacing cx="76200" cy="76200"/></p:viewPr>'),
        "ppt/tableStyles.xml": X + ('<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/'
                                    'drawingml/2006/main" def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>'),
        "ppt/slideMasters/slideMaster1.xml": X + (
            f'<p:sldMaster {NS}><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/>'
            f'</p:bgRef></p:bg><p:spTree>{GRP}</p:spTree></p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
            'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
            'folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/>'
            '</p:sldLayoutIdLst><p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400"/></a:lvl1pPr>'
            '</p:titleStyle><p:bodyStyle><a:lvl1pPr><a:defRPr sz="2000"/></a:lvl1pPr></p:bodyStyle>'
            '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle></p:txStyles>'
            '</p:sldMaster>'),
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": _rels([
            ("rId1", f"{REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", f"{REL}/theme", "../theme/theme1.xml")]),
        "ppt/slideLayouts/slideLayout1.xml": X + (
            f'<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{GRP}'
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'),
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": _rels([
            ("rId1", f"{REL}/slideMaster", "../slideMasters/slideMaster1.xml")]),
        "ppt/slides/slide1.xml": slide,
        "ppt/slides/_rels/slide1.xml.rels": _rels(
            [("rId1", f"{REL}/slideLayout", "../slideLayouts/slideLayout1.xml")] + media_rels),
        "ppt/theme/theme1.xml": X + THEME,
    })
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
        for name, data in parts.items():
            z.writestr(name, data)
    return path


def _clr(name, val):
    return f'<a:{name}><a:srgbClr val="{val}"/></a:{name}>'


THEME = (
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Logo wall">'
    '<a:themeElements><a:clrScheme name="Logo wall">'
    + _clr("dk1", "000000") + _clr("lt1", "FFFFFF") + _clr("dk2", "1F1F1F") + _clr("lt2", "EEEEEE")
    + _clr("accent1", "4472C4") + _clr("accent2", "ED7D31") + _clr("accent3", "A5A5A5")
    + _clr("accent4", "FFC000") + _clr("accent5", "5B9BD5") + _clr("accent6", "70AD47")
    + _clr("hlink", "0563C1") + _clr("folHlink", "954F72") +
    '</a:clrScheme><a:fontScheme name="Logo wall">'
    '<a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
    '</a:fontScheme><a:fmtScheme name="Logo wall"><a:fillStyleLst>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst>'
    '<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
    '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/>'
    '</a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
    '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>'
    '</a:themeElements></a:theme>')


# ── PDF ──────────────────────────────────────────────────────────────────────

def pdf(path, marks, spec):
    """Vector page, background and title as drawing ops, each logo its own image."""
    PW, PH = SLIDE_W * 72, SLIDE_H * 72
    objs = {}

    def obj(n, body):
        objs[n] = body if isinstance(body, bytes) else body.encode("latin-1")

    def stream(n, dict_, data):
        obj(n, f"<< {dict_} /Length {len(data)} >>\nstream\n".encode("latin-1") + data + b"\nendstream")

    ops = [f"{_pdf_rgb(spec['background'])} rg 0 0 {PW:.2f} {PH:.2f} re f"]
    if spec.get("title"):
        text = spec["title"].encode("latin-1", "replace").decode("latin-1")
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"BT /F1 {TITLE_PT} Tf {_pdf_rgb(spec['text'])} rg "
                   f"{MARGIN_X * 72:.2f} {PH - 0.75 * 72:.2f} Td ({text}) Tj ET")
    xobjects, n = [], 6
    for i, m in enumerate(marks, start=1):
        im = export_px(m)
        rgb, alpha = im.convert("RGB"), im.getchannel("A")
        img_n, mask_n = n, n + 1
        n += 2
        stream(mask_n, f"/Type /XObject /Subtype /Image /Width {im.width} /Height {im.height} "
                       f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode",
               zlib.compress(alpha.tobytes(), 9))
        stream(img_n, f"/Type /XObject /Subtype /Image /Width {im.width} /Height {im.height} "
                      f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
                      f"/SMask {mask_n} 0 R", zlib.compress(rgb.tobytes(), 9))
        xobjects.append(f"/Im{i} {img_n} 0 R")
        x, w, h = m["x"] * 72, m["w"] * 72, m["h"] * 72
        y = PH - m["y"] * 72 - h
        ops.append(f"q {w:.3f} 0 0 {h:.3f} {x:.3f} {y:.3f} cm /Im{i} Do Q")

    obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
    obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj(3, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW:.2f} {PH:.2f}] /Contents 4 0 R "
           f"/Resources << /Font << /F1 5 0 R >> /XObject << {' '.join(xobjects)} >> >> >>")
    stream(4, "", "\n".join(ops).encode("latin-1"))
    obj(5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    out, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), {}
    for k in sorted(objs):
        offsets[k] = len(out)
        out += f"{k} 0 obj\n".encode() + objs[k] + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for k in sorted(objs):
        out += f"{offsets[k]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)
    return path


def _pdf_rgb(hexval):
    return " ".join(f"{int(hexval[i:i + 2], 16) / 255:.4f}" for i in (0, 2, 4))


# ── HTML ─────────────────────────────────────────────────────────────────────

def html_page(path, marks, spec, grid):
    """
    Self-contained, responsive. Cells keep the slide's cell shape, and each
    logo is positioned in percent of its cell, so the optical sizing holds at
    any width. Below 640px the wall drops to two columns.
    """
    cw, ch = grid["cell"]
    cells = []
    for m in marks:
        data = base64.b64encode(_png_bytes(export_px(m, dpi=200))).decode()
        c = m["cell"]
        cells.append(
            f'<div class="cell"><img alt="{html.escape(m["name"])}" '
            f'src="data:image/png;base64,{data}" style="left:{c["left"] * 100:.3f}%;'
            f'top:{c["top"] * 100:.3f}%;width:{c["w"] * 100:.3f}%;height:{c["h"] * 100:.3f}%"></div>')
    title = f'<h2>{html.escape(spec["title"])}</h2>' if spec.get("title") else ""
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(spec.get("title") or "Logo wall")}</title>
<style>
  :root {{ --bg: #{spec["background"]}; --fg: #{spec["text"]}; --cols: {grid["cols"]}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg);
    font: 700 16px/1.25 Inter, system-ui, -apple-system, "Segoe UI", Arial, sans-serif; }}
  .wall {{ max-width: 1280px; margin: 0 auto; padding: clamp(24px, 5vw, 72px) clamp(16px, 5vw, 72px); }}
  h2 {{ font-size: clamp(20px, 2.4vw, 32px); letter-spacing: -0.01em; margin: 0 0 clamp(16px, 3vw, 36px); }}
  .grid {{ display: flex; flex-wrap: wrap; justify-content: center; }}
  .cell {{ position: relative; flex: 0 0 calc(100% / var(--cols)); aspect-ratio: {cw:.4f} / {ch:.4f}; }}
  .cell img {{ position: absolute; display: block; }}
  @media (max-width: 640px) {{ :root {{ --cols: 2; }} }}
</style>
</head>
<body>
<section class="wall" aria-label="{html.escape(spec.get("title") or "Logo wall")}">
{title}
<div class="grid">
{chr(10).join(cells)}
</div>
</section>
</body>
</html>
"""
    with open(path, "w") as f:
        f.write(page)
    return path


def _png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _rgb(hexval):
    return tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4))

#!/usr/bin/env python3
"""
Scan an instrumented PPTX template and report every token slot it will fill.

Run this after instrumenting your own template, and after every re-export.
It answers "did I do this right?" in one command:

    python3 scan_template.py template.pptx

Reports, per slide:
  - every token found, classified: {bf:*} (known / UNKNOWN) or user-defined
  - each image slot's frame size and the fit the builder will apply
  - the theme the slot prefers, checked against the slide's own background

Warnings (non-zero exit) for:
  - malformed tokens: {bf:} with no name, {unclosed, stray doubled braces
  - {bf:*} names the field mapper does not know (they would stay unfilled)
  - tokens that only appear split across text runs (typed in stages — the
    builder merges runs before substituting, but a split token is a sign the
    text box was edited and is worth a look)
  - a logo token whose preferred theme matches the slide background it sits
    on (light mark on light ground renders invisible; same for dark on dark)
"""
import re
import sys
import zipfile

import bf_fields as BF
from build_deck import merge_split_runs, geom, prst_geom, EMU

GENERIC = re.compile(r"\{[^{}\n]{1,40}\}")
KNOWN = set(BF.TEXT_SLOTS) | set(BF.IMAGE_SLOTS)

# theme preference encoded in the token name: first word wins the chain
THEME_PREF = {
    "{bf:lightOrDarkLogo}": "light",
    "{bf:lightOrDarkSymbol}": "light",
    "{bf:darkOrLightSymbol}": "dark",
}


def luminance(hexval):
    r, g, b = (int(hexval[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def slide_background(xml):
    """Slide's own solid background colour, else None (layout/master decides)."""
    m = re.search(r"<p:bg>.*?<a:srgbClr val=\"([0-9A-Fa-f]{6})\".*?</p:bg>", xml, re.S)
    return m.group(1).upper() if m else None


def infer_fit(slot, sp, frame):
    """Mirror build_deck's fit decision so the report matches the build."""
    shape = prst_geom(sp)
    fw, fh = frame[2], frame[3]
    if slot in ("{bf:banner}", "{bf:icon}") or shape == "ellipse":
        return "cover", shape
    tight = abs(fw - fh) < int(0.05 * EMU) and fw > int(0.5 * EMU)
    return ("tight contain" if tight else "contain"), shape


def scan(path):
    z = zipfile.ZipFile(path)
    slides = sorted(
        (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
        key=lambda s: int(re.search(r"\d+", s.rsplit("/", 1)[-1]).group()),
    )
    warnings = []

    for slide in slides:
        raw = z.read(slide).decode("utf-8", "replace")
        merged = merge_split_runs(raw)
        name = slide.rsplit("/", 1)[-1]
        bg = slide_background(raw)
        bg_note = ""
        if bg:
            bg_note = f"  (background {bg}, {'dark' if luminance(bg) < 128 else 'light'})"
        print(f"\n{name}{bg_note}")

        raw_tokens = set(GENERIC.findall("".join(re.findall(r"<a:t>(.*?)</a:t>", raw, re.S))))

        seen = set()
        for m in re.finditer(r"<p:sp>(?:(?!</p:sp>).)*?</p:sp>", merged, re.S):
            sp = m.group(0)
            body = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S))
            for tok in GENERIC.findall(body):
                seen.add(tok)
                frame = geom(sp)
                if tok in BF.IMAGE_SLOTS and frame:
                    fit, shape = infer_fit(tok, sp, frame)
                    fw, fh = frame[2] / EMU, frame[3] / EMU
                    print(f"  {tok:28s} image  {fw:.2f} x {fh:.2f} in  {fit} ({shape})")
                    pref = THEME_PREF.get(tok)
                    if pref and bg:
                        ground = "dark" if luminance(bg) < 128 else "light"
                        # a LIGHT (white) mark belongs on a DARK ground
                        if pref == ground:
                            warnings.append(
                                f"{name}: {tok} prefers a {pref} mark but sits on a "
                                f"{ground} background — it may render invisible. "
                                f"Use the opposite-theme token or change the ground."
                            )
                elif tok in BF.TEXT_SLOTS:
                    print(f"  {tok:28s} text   (from get_brand)")
                elif tok.startswith("{bf:") or tok.startswith("{{bf:"):
                    print(f"  {tok:28s} UNKNOWN bf token — will stay unfilled")
                    warnings.append(
                        f"{name}: {tok} is not a known {{bf:*}} field. "
                        f"Known: {', '.join(sorted(KNOWN))}"
                    )
                else:
                    print(f"  {tok:28s} user   (you supply this via values.json)")

        for tok in seen - raw_tokens:
            warnings.append(
                f"{name}: {tok} only appears split across text runs — the builder "
                f"handles this, but retyping the token in one go is safer."
            )

        # malformed: empty name, or brace debris that GENERIC cannot match
        vis = "".join(re.findall(r"<a:t>(.*?)</a:t>", merged, re.S))
        for bad in re.findall(r"\{\s*\}|\{bf:\}", vis):
            warnings.append(f"{name}: malformed token {bad!r}")
        if vis.count("{") != vis.count("}"):
            warnings.append(f"{name}: unbalanced braces — an unclosed token somewhere")

    print()
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ! {w}")
        return 1
    print("No warnings. Every slot is recognisable to the builder.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: scan_template.py template.pptx")
    sys.exit(scan(sys.argv[1]))

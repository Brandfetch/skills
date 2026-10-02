#!/usr/bin/env python3
"""
Build a logo wall — PPTX, PDF, HTML and/or PNG — from saved get_brand_data responses.

    python3 build_wall.py wall.json --check     # pick, verify, preview; build nothing
    python3 build_wall.py wall.json             # build every format in "formats"

wall.json:
{
  "title": "Trusted by teams everywhere",      // optional
  "background": "dark",                        // "dark" | "light" | "#RRGGBB"
  "style": "mono",                             // "mono" | "color"
  "type": "logo",                              // "logo" (wordmark) | "symbol"
  "formats": ["pptx"],                         // any of pptx, pdf, html, png
  "out": "logo-wall",                          // output basename
  "cols": null,                                // null = derived
  "ink": null,                                 // mono colour override, "#RRGGBB"
  "brands": [
    "brands/stripe.json",                      // a get_brand_data response saved verbatim
    {"brand": "brands/slack.json", "accept": true},   // decision on a flag
    {"brand": "brands/figma.json", "drop": true},
    {"brand": "brands/shopify.json", "name": "Shopify"}
  ]
}

Which variant each brand gets is decided here, from pixels, never from the
`theme` label alone (references/rules.md):

  mono   1. an official monochrome variant in the colour the ground needs
         2. an official monochrome variant in the other colour, recoloured
            (lossless: a one-colour mark stays the same drawing)
         3. a colour variant flattened with the luminance threshold, knockouts
            kept — FLAGGED for review when colour carries part of the drawing
  color  the variant that is actually visible on the ground (≥50% of the
         mark at ≥1.5:1), light marks first on dark grounds; none visible →
         FLAGGED

Every mono mark is re-rendered in one exact ink colour, so no wall mixes
#FFFFFF with #F4F4F4. A flagged brand is not built until the wall.json entry
says "accept": true or "drop": true — flags are human decisions.
"""
import json
import math
import os
import re
import subprocess
import sys

import ink
import layout as L
import writers as W

DARK, LIGHT = "101012", "FAFAF8"
RASTER_ORDER = ["png", "jpeg", "jpg", "webp", "svg"]
REVIEW_LOSS = 0.08     # flattened marks whose colour carries ≥8% of their drawing


def ground_hex(bg):
    return DARK if bg == "dark" else LIGHT if bg == "light" else bg.lstrip("#").upper()


def is_dark(hexval):
    return ink._rel_lum(ink.hex_rgb(hexval)) < 0.18


def fetch(url, dest):
    """curl the src URL verbatim; the error text is kept for the report."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    r = subprocess.run(["curl", "-sS", "--fail", "-o", dest, url], capture_output=True, text=True)
    if r.returncode:
        msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f"curl exit {r.returncode}"
        if "403" in msg:
            msg += " (see setup.md: allowlist, or an edited ?c= credential)"
        raise RuntimeError(msg)
    return dest


def candidates(brand, kind, workdir, slug):
    """
    Every logo entry that could be this brand's `kind` mark, downloaded and
    profiled. Unlabelled `type: "other"` entries are included when their shape
    matches — the true all-white variant often lives there.
    """
    out, errors = [], []
    for i, e in enumerate(brand.get("logos") or []):
        if e.get("type") not in (kind, "other"):
            continue
        by = {f.get("format"): f for f in e.get("formats") or []}
        fmt = next((by[f] for f in RASTER_ORDER if f in by), None)
        if not fmt:
            continue
        path = os.path.join(workdir, f"{slug}-{i}.{fmt['format']}")
        try:
            if not os.path.exists(path):
                fetch(fmt["src"], path)
            im = ink.trim(ink.load(path))
        except Exception as ex:
            errors.append(f"{e.get('type')}/{e.get('theme')}: {ex}")
            continue
        prof = ink.profile(im)
        out.append({"type": e.get("type"), "theme": e.get("theme"), "image": im,
                    "prof": prof, "aspect": im.width / im.height})
    primary = [c for c in out if c["type"] == kind]
    if primary:
        ref = primary[0]["aspect"]
        out = [c for c in out if c["type"] == kind or abs(math.log(c["aspect"] / ref)) < 0.4]
    else:
        # no labelled mark of this kind: judge "other" entries by shape
        out = [c for c in out if (c["aspect"] >= 1.6) == (kind == "logo")]
    out.sort(key=lambda c: c["type"] != kind)          # labelled first
    return out, errors


def pick_mono(cands, ground, kind):
    target = "light" if is_dark(ground) else "dark"
    tiers = [
        ("official mono", lambda c: ink.is_mono(c["prof"]) and c["prof"]["polarity"] == target),
        ("official mono, recoloured", lambda c: ink.is_mono(c["prof"])),
        ("flattened from colour", lambda c: True),
    ]
    pick = None
    for label, ok in tiers:
        pick = next(((c, label) for c in cands if ok(c)), None)
        if pick:
            break
    c, label = pick
    # An unlabelled "other" variant is sometimes a different lockup — Slack's
    # only mono wordmark is "slack from Salesforce". When it does not share
    # the primary mark's silhouette and the primary flattens cleanly, the
    # primary wins: the wall should show the logo people know.
    primary = next((p for p in cands if p["type"] == kind), None)
    if primary and c["type"] == "other" and ink.silhouette_iou(c["image"], primary["image"]) < 0.8:
        if ink.structure_loss(primary["image"], primary["prof"]) < REVIEW_LOSS:
            return primary, "flattened from colour (the only mono variant is a different lockup)"
        return c, label + " — a different lockup from the primary logo, check it"
    return c, label


def pick_color(cands, ground):
    prefer = "light" if is_dark(ground) else "dark"
    order = sorted(cands, key=lambda c: (c["type"] == "other", c["theme"] != prefer))
    scored = [(c, ink.visibility(c["image"], ground)) for c in order]
    for c, v in scored:
        if v >= ink.VISIBLE:
            return c, f"{c['theme']} variant, {v:.0%} visible", None
    best = max(scored, key=lambda s: s[1], default=(None, 0))
    return best[0], "best available", (
        f"not visible in colour on #{ground} (best {best[1]:.0%}) — switch the wall "
        f"to mono, accept, or drop")


def resolve(cfg, workdir):
    ground = ground_hex(cfg.get("background", "dark"))
    kind = cfg.get("type", "logo")
    style = cfg.get("style", "mono")
    if style not in ("mono", "color"):
        sys.exit(f'"style" must be "mono" or "color" (original brand colours), not {style!r}')
    if kind not in ("logo", "symbol"):
        sys.exit(f'"type" must be "logo" or "symbol", not {kind!r}')
    inkc = (cfg.get("ink") or ("FFFFFF" if is_dark(ground) else "111111")).lstrip("#").upper()
    rows = []
    for entry in cfg["brands"]:
        entry = {"brand": entry} if isinstance(entry, str) else dict(entry)
        brand = json.load(open(entry["brand"]))
        api_name = (brand.get("name") or brand.get("domain") or entry["brand"]).strip()
        name = entry.get("name") or api_name
        slug = re.sub(r"[^a-z0-9]+", "-", (brand.get("domain") or name).lower()).strip("-")
        row = {"name": name, "entry": entry, "flags": [], "notes": []}
        asked = os.path.basename(entry["brand"]).removesuffix(".json").lower()
        got = (brand.get("domain") or "").lower()
        if got and "." in asked and asked != got:
            row["notes"].append(f"{asked} resolved to {got}: check it is the same company")
        if not entry.get("name") and "." in api_name:
            row["notes"].append(f"Brandfetch calls it {api_name!r} — set \"name\" if that is "
                                f"not how it should read (alt text)")
        cands, errors = candidates(brand, kind, workdir, slug)
        row["notes"] += [f"download failed: {e}" for e in errors]
        if not cands:
            row["flags"].append(f"no usable {kind} asset" + (" (downloads failed)" if errors else ""))
            rows.append(row)
            continue
        if style == "mono":
            c, how = pick_mono(cands, ground, kind)
            loss = ink.structure_loss(c["image"], c["prof"]) if how.startswith("flattened") else 0
            if loss >= REVIEW_LOSS:
                row["flags"].append(
                    f"flattened from colour, and colour carries {loss:.0%} of its drawing "
                    f"(parts merge, like Mastercard's overlap) — look at the preview: accept, "
                    f"or drop")
            img = ink.monochrome(c["image"], inkc, c["prof"])
            img = ink.trim(img)
        else:
            c, how, flag = pick_color(cands, ground)
            if flag:
                row["flags"].append(flag)
            img = c["image"]
        if ink.secondary_line(img):
            row["notes"].append("two-line lockup: the smaller line (tagline / endorsement) "
                                "will read tiny on a wall — fine if that is the brand's "
                                "current logo, otherwise drop the brand or use \"type\": \"symbol\"")
        row.update(image=img, how=f"{c['type']} · {how}", **ink.metrics(img))
        rows.append(row)
    return rows, ground, inkc


def report(rows, grid, cfg):
    kept = [r for r in rows if "image" in r and not r["entry"].get("drop")]
    print(f"{len(kept)}/{len(rows)} brands · grid {grid['cols']} x {grid['rows']} · "
          f"{cfg.get('style', 'mono')} {cfg.get('type', 'logo')} on "
          f"{cfg.get('background', 'dark')}\n")
    for r in rows:
        e = r["entry"]
        state = "drop" if e.get("drop") else "FLAG" if r["flags"] and not e.get("accept") else "ok"
        mark = {"ok": "  ", "FLAG": "! ", "drop": "- "}[state]
        extra = " (capped to its box)" if r.get("capped") else ""
        print(f"{mark}{r['name']:18s} {r.get('how', '—')}{extra}")
        for f in r["flags"]:
            print(f"      ! {f}" + ("   [accepted]" if e.get("accept") else ""))
        for n in r["notes"]:
            print(f"      i {n}")
    return [r for r in rows if r["flags"] and not (r["entry"].get("accept") or r["entry"].get("drop"))]


def main(path, check):
    cfg = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    os.chdir(base)
    rows, ground, inkc = resolve(cfg, "wall_assets")
    marks = [r for r in rows if "image" in r and not r["entry"].get("drop")
             and not (r["flags"] and not r["entry"].get("accept") and not check)]
    if not marks:
        report(rows, {"cols": 0, "rows": 0}, cfg)
        sys.exit("nothing to place")
    grid = L.layout(marks, title=bool(cfg.get("title")), cols=cfg.get("cols"),
                    kind=cfg.get("type", "logo"))
    open_flags = report(rows, grid, cfg)
    spec = {"title": cfg.get("title"), "background": ground,
            "text": "FFFFFF" if is_dark(ground) else "111111"}
    out = cfg.get("out", "logo-wall")

    if check:
        W.png(f"{out}.preview.png", marks, spec)
        print(f"\npreview: {os.path.join(base, out + '.preview.png')}  (flagged brands included)")
        if open_flags:
            print(f"{len(open_flags)} brand(s) need a decision: add \"accept\": true or "
                  f"\"drop\": true to their entry in {os.path.basename(path)}.")
        return 1 if open_flags else 0

    if open_flags:
        print(f"\nnot built: {len(open_flags)} unresolved flag(s) — decide in "
              f"{os.path.basename(path)} (\"accept\" / \"drop\"), then rerun.")
        return 2
    written = []
    for fmt in cfg.get("formats", ["pptx"]):
        target = f"{out}.{fmt}"
        if fmt == "pptx":
            W.pptx(target, marks, spec)
        elif fmt == "pdf":
            W.pdf(target, marks, spec)
        elif fmt == "html":
            W.html_page(target, marks, spec, grid)
        elif fmt == "png":
            W.png(target, marks, spec, dpi=300)
        else:
            print(f"  ? unknown format {fmt!r} skipped")
            continue
        written.append(os.path.join(base, target))
    W.png(f"{out}.preview.png", marks, spec)
    print("\nwritten:\n  " + "\n  ".join(written))
    print(f"preview: {os.path.join(base, out + '.preview.png')}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit("usage: build_wall.py wall.json [--check]")
    sys.exit(main(args[0], "--check" in sys.argv))

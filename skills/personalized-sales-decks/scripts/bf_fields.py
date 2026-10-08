#!/usr/bin/env python3
"""
Field mapping and asset selection for {bf:*} slots.

Template-independent: depends only on the get_brand_data response shape, never on
slot geometry. Safe to reuse across any instrumented deck.
"""

# ── text fields ──────────────────────────────────────────────────────────────

EMPLOYEE_BANDS = {
    1: "1",
    2: "2-10",
    11: "11-50",
    51: "51-200",
    201: "201-500",
    501: "501-1,000",
    1001: "1,001-5,000",
    5001: "5,001-10,000",
    10001: "10,001+",
}


def bf_name(brand):
    """{bf:name} — top-level `name`."""
    return (brand.get("name") or "").strip()


def bf_description(brand):
    """
    {bf:description} — top-level `description`, cut at the first period.

    NOT company.description (does not exist) and NOT longDescription
    (multi-paragraph). The period is kept.
    """
    d = (brand.get("description") or "").strip()
    if not d:
        return ""
    i = d.find(".")
    return d[: i + 1] if i != -1 else d


def bf_company_type(brand):
    """
    {bf:companyType} — company.kind, underscores to spaces, Title Case.

    PUBLIC_COMPANY -> Public Company
    PRIVATELY_HELD -> Privately Held
    """
    kind = (brand.get("company") or {}).get("kind")
    if not kind:
        return ""
    return kind.replace("_", " ").title()


def bf_company_employee(brand):
    """
    {bf:companyEmployee} — company.employees (plural) mapped to a band label.

    The integer is a band sentinel, not a headcount. No "employees" suffix:
    the template already carries a headcount icon.
    """
    n = (brand.get("company") or {}).get("employees")
    if n is None:
        return ""
    if n in EMPLOYEE_BANDS:
        return EMPLOYEE_BANDS[n]
    lower = [k for k in EMPLOYEE_BANDS if k <= n]
    return EMPLOYEE_BANDS[max(lower)] if lower else ""


# ── asset selection ──────────────────────────────────────────────────────────

# Raster preferred over SVG for PowerPoint; PNG preferred over WebP always
# (older PowerPoint will not render WebP).
FORMAT_PREFERENCE = ["png", "jpeg", "jpg", "svg", "webp"]


def _pick_format(formats):
    """Highest-preference format available, else None."""
    by_fmt = {f.get("format"): f for f in formats or []}
    for fmt in FORMAT_PREFERENCE:
        if fmt in by_fmt:
            return by_fmt[fmt]
    return None


def _find_logo(brand, logo_type, theme):
    """First logos[] entry matching type + theme, with a usable format."""
    for entry in brand.get("logos") or []:
        if entry.get("type") == logo_type and entry.get("theme") == theme:
            fmt = _pick_format(entry.get("formats"))
            if fmt:
                return fmt
    return None


def _chain(brand, logo_type, themes):
    """
    Walk a theme fallback chain. Returns None if nothing matches — the slot is
    then left empty and the omission reported. Never falls back across types.
    """
    for theme in themes:
        hit = _find_logo(brand, logo_type, theme)
        if hit:
            return hit
    return None


def bf_logo(brand):
    """
    {bf:logo} — the logo, theme chosen at BUILD time from the ground the slot
    sits on (see THEMED). Resolves here to whichever variant exists, so a
    brand with no logo at all is still reported missing.
    """
    return _chain(brand, "logo", ["light", "dark"])


def bf_symbol(brand):
    """{bf:symbol} — the symbol, theme chosen at build time like {bf:logo}."""
    return _chain(brand, "symbol", ["light", "dark"])


def bf_light_or_dark_logo(brand):
    """{bf:lightOrDarkLogo} — logo, light preferred, dark as fallback."""
    return _chain(brand, "logo", ["light", "dark"])


def bf_dark_or_light_logo(brand):
    """{bf:darkOrLightLogo} — logo, dark preferred, light as fallback."""
    return _chain(brand, "logo", ["dark", "light"])


def bf_dark_or_light_symbol(brand):
    """{bf:darkOrLightSymbol} — symbol, dark preferred, light as fallback."""
    return _chain(brand, "symbol", ["dark", "light"])


def bf_light_or_dark_symbol(brand):
    """{bf:lightOrDarkSymbol} — symbol, light preferred, dark as fallback."""
    return _chain(brand, "symbol", ["light", "dark"])


def bf_icon(brand):
    """
    {bf:icon} — type "icon". Single variant in practice; theme is whatever the
    record carries, so no chain. May appear in more than one slot per slide.
    """
    for entry in brand.get("logos") or []:
        if entry.get("type") == "icon":
            fmt = _pick_format(entry.get("formats"))
            if fmt:
                return fmt
    return None


def bf_banner(brand):
    """{bf:banner} — images[] entry of type "banner"."""
    for entry in brand.get("images") or []:
        if entry.get("type") == "banner":
            fmt = _pick_format(entry.get("formats"))
            if fmt:
                return fmt
    return None


# ── resolution ───────────────────────────────────────────────────────────────

TEXT_SLOTS = {
    "{bf:name}": bf_name,
    "{bf:description}": bf_description,
    "{bf:companyType}": bf_company_type,
    "{bf:companyEmployees}": bf_company_employee,
}

# fit mode per image slot:
#   contain — fit wholly inside, letterbox. Wordmarks must never be cropped.
#   cover   — fill the frame, centre-crop overflow, inherit placeholder geometry.
IMAGE_SLOTS = {
    "{bf:banner}": (bf_banner, "cover"),
    "{bf:icon}": (bf_icon, "cover"),
    "{bf:logo}": (bf_logo, "contain"),
    "{bf:symbol}": (bf_symbol, "contain"),
    "{bf:lightOrDarkLogo}": (bf_light_or_dark_logo, "contain"),
    "{bf:darkOrLightLogo}": (bf_dark_or_light_logo, "contain"),
    "{bf:darkOrLightSymbol}": (bf_dark_or_light_symbol, "contain"),
    "{bf:lightOrDarkSymbol}": (bf_light_or_dark_symbol, "contain"),
}


# Slots whose light/dark variant the builder picks per slot, by measuring
# which one is actually visible on the colour underneath it.
#   (logo type, preferred theme) — None means "whichever the ground calls for".
# The chain tokens only set the order tried; a variant that would vanish on
# its ground is never placed, whatever the token asked for.
THEMED = {
    "{bf:logo}": ("logo", None),
    "{bf:symbol}": ("symbol", None),
    "{bf:lightOrDarkLogo}": ("logo", "light"),
    "{bf:darkOrLightLogo}": ("logo", "dark"),
    "{bf:lightOrDarkSymbol}": ("symbol", "light"),
    "{bf:darkOrLightSymbol}": ("symbol", "dark"),
}


def theme_variants(brand, logo_type):
    """{theme: format entry} for every theme this logo type exists in."""
    out = {}
    for theme in ("light", "dark"):
        hit = _find_logo(brand, logo_type, theme)
        if hit:
            out[theme] = hit
    return out


LOGO_TYPES = ("logo", "symbol", "icon")


def parse_use(arg):
    """'symbol:icon,logo:symbol' -> {'symbol': 'icon', 'logo': 'symbol'}"""
    out = {}
    for pair in filter(None, (arg or "").split(",")):
        want, _, alt = pair.partition(":")
        if want not in LOGO_TYPES or alt not in LOGO_TYPES or want == alt:
            raise SystemExit(f"--use takes type:type pairs of {LOGO_TYPES}, got {pair!r}")
        out[want] = alt
    return out


def missing_hint(brand, missing):
    """The question to ask the user about each logo type this brand lacks."""
    lacking = sorted({slot_type(s) for s in missing if slot_type(s)})
    have = available_types(brand)
    name = brand.get("name") or brand.get("domain") or "This brand"
    lines = []
    for t in lacking:
        others = [o for o in have if o != t]
        if others:
            lines.append(f"  ASK THE USER: {name} has no {t}. Use its {' or its '.join(others)} "
                         f"there? Then rebuild with --use={t}:{others[0]} (or :{others[-1]}).")
        else:
            lines.append(f"  {name} has no {t} and no other logo type: the slot stays empty.")
    return "\n".join(lines)


def slot_type(slot):
    """The logo type a slot asks for: logo, symbol, icon — or None (banner)."""
    if slot in THEMED:
        return THEMED[slot][0]
    return "icon" if slot == "{bf:icon}" else None


def available_types(brand):
    """Logo types this brand has at least one usable asset for."""
    return [t for t in LOGO_TYPES if theme_variants(brand, t)]


def resolve(brand, use=None):
    """
    Resolve every slot. Returns (text, images, missing).

    `missing` lists slots with no source asset — those are left empty and
    reported. They are never substituted on the builder's own initiative:
    `use` ({"symbol": "icon"}) is the user's answer to "this brand has no
    symbol — use its icon or its logo there?", and only then does a slot take
    another type.
    """
    use = use or {}
    text = {slot: fn(brand) for slot, fn in TEXT_SLOTS.items()}
    images, missing = {}, []

    for slot, (fn, fit) in IMAGE_SLOTS.items():
        hit = fn(brand)
        typ = slot_type(slot)
        if hit:
            images[slot] = {"src": hit["src"], "format": hit["format"], "fit": fit}
            if slot in THEMED:
                images[slot]["variants"] = theme_variants(brand, typ)
            continue
        alt = use.get(typ)
        variants = theme_variants(brand, alt) if alt in LOGO_TYPES else {}
        if variants:
            first = next(iter(variants.values()))
            # a wordmark or symbol in an icon's cover-fit slot would be cropped
            images[slot] = {"src": first["src"], "format": first["format"],
                            "fit": "contain" if alt != "icon" else fit,
                            "type": alt, "instead_of": typ}
            if slot in THEMED:
                images[slot]["variants"] = variants
        else:
            missing.append(slot)

    missing += [s for s, v in text.items() if not v]
    return text, images, missing


if __name__ == "__main__":
    import json, sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use = parse_use(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--use=")), ""))
    brand = json.load(open(args[0] if args else "brand.json"))
    text, images, missing = resolve(brand, use)
    for k, v in text.items():
        print(f"{k:26s} {v!r}")
    for k, v in images.items():
        sub = f"  ({v['type']} instead of {v['instead_of']})" if "instead_of" in v else ""
        print(f"{k:26s} [{v['fit']:7s}] {v['format']:4s} {v['src'][:72]}{sub}")
    print(f"\nmissing: {missing or 'none'}")
    print(missing_hint(brand, missing))

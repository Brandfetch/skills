#!/usr/bin/env python3
"""
Field mapping and asset selection for {bf:*} slots.

Template-independent: depends only on the get_brand response shape, never on
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


def bf_light_or_dark_logo(brand):
    """{bf:lightOrDarkLogo} — logo, light preferred, dark as fallback."""
    return _chain(brand, "logo", ["light", "dark"])


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
    "{bf:lightOrDarkLogo}": (bf_light_or_dark_logo, "contain"),
    "{bf:darkOrLightSymbol}": (bf_dark_or_light_symbol, "contain"),
    "{bf:lightOrDarkSymbol}": (bf_light_or_dark_symbol, "contain"),
}


def resolve(brand):
    """
    Resolve every slot. Returns (text, images, missing).

    `missing` lists slots with no source asset — those are left empty and
    reported, never substituted.
    """
    text = {slot: fn(brand) for slot, fn in TEXT_SLOTS.items()}
    images, missing = {}, []

    for slot, (fn, fit) in IMAGE_SLOTS.items():
        hit = fn(brand)
        if hit:
            images[slot] = {"src": hit["src"], "format": hit["format"], "fit": fit}
        else:
            missing.append(slot)

    missing += [s for s, v in text.items() if not v]
    return text, images, missing


if __name__ == "__main__":
    import json, sys

    brand = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "brand.json"))
    text, images, missing = resolve(brand)
    for k, v in text.items():
        print(f"{k:26s} {v!r}")
    for k, v in images.items():
        print(f"{k:26s} [{v['fit']:7s}] {v['format']:4s} {v['src'][:72]}")
    print(f"\nmissing: {missing or 'none'}")

---
name: logo-wall
description: Generate a customer or partner logo-wall slide (editable PPTX) from a list of brands, pulling verified logos from the Brandfetch MCP. Use this whenever the user asks for a logo wall, logo grid, customer wall, "trusted by" slide, social-proof slide, or a slide showing many company logos — "make a logo wall of our 12 customers", "a trusted-by slide with these brands". For a full personalized deck for ONE client, use the pitch-deck-generator skill instead.
license: MIT
---

# Logo wall

Builds one slide: a grid of brand logos, sized and verified to read as a
designed set. Output is a real editable `.pptx` — every logo is a separate
picture the user can move or swap.

**Requirements:** the Brandfetch MCP connected, and `cdn.brandfetch.io` on
the network allowlist (see `references/setup.md`).

## Ask these four things first

Do not fetch anything before the answers are clear. Read the conversation
first — some may already be answered.

1. **Which brands?** Domains preferred (`stripe.com`); names are fine, resolve
   ambiguous ones via `brand_search` and confirm the match.
2. **Dark or light slide background?** (Default: dark.) This decides which
   theme variant to fetch — the user should never need to know that
   `theme=light` means a white mark.
3. **Which asset type?** Explain briefly:
   - **logo** — full wordmark, most recognisable. Default.
   - **symbol** — mark only, most visually uniform grid.
   - **icon** — app-tile style; usually JPEG with a baked-in background that
     shows as a tile on the slide. Discourage unless asked for.
4. **Monochrome or original brand colours?** (Default: monochrome on dark.)

The **grid is derived, not asked**: 12 brands → 4×3. Propose it in the
confirm step and accept an override; never make the user do layout math.

## The rule this skill exists for

**The `theme` label does not guarantee monochrome — only pixels do.**

Official light-theme variants frequently keep a coloured symbol (that IS the
brand's approved light-background version), and the true all-white variant,
when it exists, is often filed under `type: "other"` with no semantic label.
So when the user wants monochrome:

1. Collect candidates per brand from `get_brand`: the theme-matched primary
   first, then every same-theme variant under `type: "other"`.
2. The builder downloads candidates in order and keeps the first that passes
   a pixel saturation check.
3. No candidate passes → the brand is **flagged**, never silently shipped and
   **never force-tinted** — recolouring a brand's mark violates its
   guidelines. The user chooses: accept the least-coloured candidate, switch
   that brand to its symbol, or drop it.

## Workflow

### 1. Resolve every brand

`get_brand` per domain. From each response collect, in order, the candidate
`src` URLs for the chosen type and theme — primary first, then `type:"other"`
same-theme variants. Also note the brand **name the API returns**: wrong or
surprising matches (a subsidiary, a post-acquisition lockup like an acquired
company shown under its parent's brand) are confirm-step items, not errors.

### 2. Write `wall.json`

```json
{
  "title": "Trusted by teams everywhere",
  "background": "dark",
  "mono": true,
  "brands": [
    { "name": "Slack", "candidates": ["<primary src URL>", "<other-type URL>"] }
  ]
}
```

Use `src` URLs **verbatim** — the `?c=` parameter is a per-response
credential (see `references/setup.md`).

### 3. Check, then confirm

```bash
python3 scripts/build_wall.py wall.json --check
```

Downloads and pixel-verifies everything, prints the resolved count, the
derived grid, and every flag — builds nothing. Show this to the user and get
their decision on each flag. This step is not optional: flags are human
decisions.

### 4. Build and verify

```bash
python3 scripts/build_wall.py wall.json wall.pptx
```

Then validate and render, and actually look at it:

```bash
python3 <pptx-skill>/scripts/office/validate.py wall.pptx
```

Check for: a wrong-brand logo the confirm step missed, one mark visually
dominating (the clamp bounds this but taste beats math), and lettermark
placeholders where a brand had no real asset.

## How sizing works (so you can explain it)

Each logo is contained into an equal cell at its natural size, then heights
are **clamped to a band around the median** (0.72×–1.25×). Natural sizing is
what makes a wall look organic rather than templated; the clamp is what stops
one square symbol or skyscraper glyph from wrecking it. Logos are never
stretched, cropped, or recoloured. A partial last row is centred.

## Files

- `scripts/build_wall.py` — verify + clamp + grid + PPTX. `--check` for the
  confirm report.
- `references/rules.md` — the verification and layout rules, with the cases
  that produced them.
- `references/setup.md` — MCP, allowlist, dependencies.

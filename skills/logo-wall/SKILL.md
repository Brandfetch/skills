---
name: logo-wall
description: Generate a customer or partner logo wall — as PPTX, PDF, HTML or PNG — from a list of brands, with verified logos from the Brandfetch MCP, optically balanced so no logo looks bigger or smaller than the rest. Use this whenever the user asks for a logo wall, logo grid, logo strip, customer wall, "trusted by" or "as seen in" section, social-proof slide, or any slide or web section showing many company logos — "make a logo wall of our 12 customers", "a trusted-by slide with these brands", "put these logos on a dark background". For a full personalized deck for ONE client, use the pitch-deck-generator skill instead.
license: MIT
---

# Logo wall

One wall of brand logos that reads as a designed set: same visual weight,
same colour treatment, even rhythm. Every logo stays a separate object — a
movable picture in PowerPoint, its own image in the PDF, an `<img>` in the
HTML.

**Requirements:** the Brandfetch MCP connected, `cdn.brandfetch.io` on the
network allowlist, and Pillow (see `references/setup.md`). No other Python
packages: PPTX and PDF are written directly.

## 1. Ask before fetching anything

Read the conversation first; ask only what is still open, in one message,
with the defaults stated so the user can just say "yes":

| Question | Options | Default |
|---|---|---|
| **Format** | PPTX (slide) · PDF · HTML (web section) · PNG — several is fine | PPTX |
| **Which brands, how many** | a list of domains or names; if they say "our top 12 customers", ask for the list | — |
| **Background** | dark · light · a hex colour (their slide or site colour) | dark |
| **Style** | monochrome (one colour, the classic wall) · original brand colours | monochrome |
| **Logo type** | wordmark (most recognisable) · symbol (most uniform, for brands everyone knows) | wordmark |
| **Title** | e.g. "Trusted by teams everywhere", or none | none |

Never ask for a grid: it is derived (10 → 5×2, 7 → 4+3 centred). Propose it
in the check step; accept an override (`"cols"`).

Past ~20 logos a single wall stops being scannable — suggest the strongest
12–16, or two walls.

## 2. Resolve every brand and save it

Call `get_brand` per domain (resolve names with `brand_search` first and
confirm ambiguous matches). Save each response **verbatim** to
`brands/<domain>.json` — the script reads the logo variants from disk and
picks between them itself. Never copy URLs into a config by hand: the `?c=`
parameter is a per-response credential, and hand-picked variants skip the
pixel checks below.

Note the name the API returns. A surprising one (a parent brand, a
co-branded lockup, "Shopify.com") is a check-step item, not an error.

## 3. Write `wall.json` and check

```json
{
  "title": "Trusted by teams everywhere",
  "background": "dark",
  "style": "mono",
  "type": "logo",
  "formats": ["pptx"],
  "out": "logo-wall",
  "brands": ["brands/stripe.com.json", "brands/slack.com.json"]
}
```

```bash
python3 scripts/build_wall.py wall.json --check
```

This downloads every candidate variant, chooses one per brand from its
pixels, lays out the wall and writes `logo-wall.preview.png` — without
building the deliverable. **Look at the preview, then show it to the user**
with the report. Every `!` line is a decision for the user:

- **flattened from colour, colour carries N% of its drawing** — no official
  one-colour version exists and flattening merges parts of the mark
  (Mastercard's overlap, Figma's lobes). Options: accept, drop the brand, or
  switch this wall to original colours.
- **no usable asset** — the brand has no logo of that type (many have no
  symbol). Drop it, or use wordmarks for the whole wall.
- **not visible in colour** — neither variant shows on this background.

Record the answer on the brand's entry — `{"brand": "…", "accept": true}` or
`{"brand": "…", "drop": true}`. The build refuses to run while a flag is
undecided. `i` lines are information worth one sentence to the user (a
two-line lockup like "slack / from Salesforce", an odd API name — fix with
`"name": "Shopify"`).

## 4. Build and look

```bash
python3 scripts/build_wall.py wall.json
```

Writes every format in `formats`, plus a fresh preview. Look at the preview
again before handing anything over: a wrong-brand logo or an off mark is
obvious to the eye and invisible to the report.

## What the script decides, so you can explain it

**Which variant.** Monochrome: an official one-colour version in the right
colour first; then an official one-colour version recoloured (lossless);
only then a colour logo flattened. Original colours: the variant that is
actually visible on the background, measured, not assumed from its label.
An unlabelled `type: "other"` variant often holds the real all-white logo,
so those are considered too.

**How flattening works.** A luminance threshold (`references/monochrome.md`):
ink becomes the wall's colour, near-white becomes transparent. Knocked-out
detail — Notion's cube face, the counters of letters — stays a hole instead
of filling in, which is what a plain "make it white" does. Every mono mark,
official or flattened, is re-rendered in one exact colour. Nothing is ever
tinted a colour the brand did not choose.

**How sizing works.** Each logo is trimmed to its ink (files carry anything
from no padding — Stripe — to huge margins), then sized to equal visual
area, nudged for stroke weight (a heavy mark reads bigger), guarded so
extreme shapes stay sane, and centred on its optical centre rather than its
box. Details and the reasoning: `references/rules.md`.

## Files

- `scripts/build_wall.py` — choose variants, report, build. `--check` first.
- `scripts/ink.py` — loading (SVG included), monochrome, measurements.
- `scripts/layout.py` — grid, optical sizing and centring.
- `scripts/writers.py` — PPTX, PDF, HTML, PNG from one layout.
- `references/rules.md` — every rule, with the wall that produced it.
- `references/monochrome.md` — the flattening filter, and its CSS form.
- `references/setup.md` — MCP, allowlist, dependencies.

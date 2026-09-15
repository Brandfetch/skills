# Rules

Each rule comes from a real wall that looked wrong without it.

## 1. Verify pixels, never trust the theme label

`theme` names the asset's own colour family, not its purity. On a 12-brand
test wall, two "light" logos failed a saturation scan: one carried its
coloured symbol (38% coloured pixels — that IS the brand's approved
light-background variant), one a multicolour mark (33%). One brand's true
all-white version existed only under `type: "other"`, unlabelled; the other
brand's best variant still carried a co-brand element in colour (4.4%) —
no fully monochrome version exists on its record at all.

The check: downscale to ~200px, count visible pixels (alpha > 40) whose
saturation `(max-min)/max > 0.15` at brightness > 30. Over 2% coloured =
not monochrome. Cheap, and it settles what metadata cannot.

## 2. Never force-tint

Recolouring a brand's mark to make the wall uniform violates that brand's
guidelines — the same class of error as stretching it. A brand with no
passing variant is a flag with three honest options: accept the
least-coloured candidate, switch that one brand to its symbol, or drop it.
The tool refuses to pick for you.

## 3. Flags are for humans

Two kinds surface at wall scale that single-logo work never shows:

- **No-mono brands** (rule 1).
- **Surprising matches**: an acquired brand returned under its parent's
  lockup, or a co-branded wordmark ("X from Y"). These are often *correct*
  current branding — which is exactly why a human must decide, not the tool.

`--check` exists so the report lands before anything is built.

## 4. Vary within bounds

Equal-box contain makes a wall of mixed aspect ratios look broken: a
near-square glyph fills its cell while a 6:1 wordmark is height-limited to a
sliver — same box, one reads 2–3× bigger. Full normalisation to equal height
over-corrects: it reads sterile, like a spec sheet.

What works: natural contained size, heights clamped to a band around the
median (0.72×–1.25×). The set breathes, and no single mark can dominate.
On a wordmark set with a 2.5× aspect spread, exactly one logo hit the clamp —
the band is a guard rail, not a straitjacket.

## 5. One asset type per wall

Wordmarks next to bare symbols never cohere, whatever the sizing math does.
Pick logo OR symbol for the whole set, up front. Wordmarks are the safer
default (more recognisable, naturally similar heights); symbols make the most
uniform grid when the audience knows the brands. Icons are last resort —
usually JPEG with baked backgrounds that render as tiles.

## 6. Geometry basics inherited from the deck skill

Never stretch (aspect always preserved), never crop a mark, measure the ink
bounding box rather than the canvas (padding varies wildly between brands),
centre a partial last row.

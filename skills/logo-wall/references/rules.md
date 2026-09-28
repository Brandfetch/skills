# Rules

Each rule comes from a real wall that looked wrong without it.

## 1. Verify pixels, never trust the theme label

`theme` names the asset's colour family, not its purity or its visibility.
On a 12-brand test wall, two "light" logos failed a saturation scan: one
carried its coloured symbol (38% coloured pixels — that IS the brand's
approved light-background variant), one a multicolour mark (33%). One
brand's true all-white version existed only under `type: "other"`,
unlabelled — Slack's is still filed that way.

The checks: saturation (`(max−min)/max > 0.15` on >2% of ink = not
monochrome) and, in colour mode, visibility against the actual background
(≥50% of the mark at ≥1.5:1 contrast). An earlier version checked only
saturation — and passed Notion's and Spotify's *black* logos for a *dark*
wall, where they would have been invisible.

## 2. Official mono first, flatten last, never tint

Order for a monochrome wall: an official one-colour variant in the colour the
background needs → an official one-colour variant recoloured (a one-colour
mark stays the same drawing) → a colour logo flattened with the luminance
threshold (`monochrome.md`). Flattening keeps knockouts as holes, so
Notion's cube and a letter's counters survive.

Never tint a mark a colour the brand did not choose, and never mix inks:
every mono mark is re-rendered in the same exact colour.

## 3. Flag what flattening breaks

When colour is the only thing separating parts of a mark, flattening merges
them. The script measures colour edges between ink pixels against the
outline and flags a flattened logo at ≥8%.

> A hue-spread test missed Mastercard — red, orange and yellow are
> neighbours on the wheel — yet its overlap exists only in colour. A plain
> edge count flagged Notion instead, whose flattening is fine: its internal
> edges are grey shading. Only chromatic edges count.

## 4. Flags are for humans

Three kinds surface at wall scale:

- **Flattened with structure loss** (rule 3), **no asset of that type**, and
  **not visible in colour** block the build until the user accepts or drops
  the brand.
- **Surprising matches** — a parent brand's lockup, a co-branded wordmark
  ("slack / from Salesforce"), an API name like "Shopify.com". These are
  often *correct current branding*, which is exactly why a human decides.
  The script notes two-line lockups (a second line <45% the height of the
  first will read tiny) and domain-like names.

When an unlabelled `other` variant is a different drawing from the primary
logo (silhouette overlap < 0.8) and the primary flattens cleanly, the
primary wins: the wall should show the logo people know.

## 5. Trim to ink, then size by visual area

Padding differs wildly between brands' files; every mark is cropped to its
ink first. Sizing a box ignores what is in it.

- **Equal height** makes a 7.8:1 wordmark (Mastercard) enormous next to a
  2:1 one. **Equal width** makes it a sliver.
- **Equal area** (`w = √(A·r)`, `h = √(A/r)`) is the perceptual middle, with
  heights guarded to 0.6–1.6× the median.
- **Weight**: a heavy mark reads bigger than a light one of the same area;
  linear size × `(median density / density) ** 0.25`, clamped 0.88–1.12.
  At 0.35 / 1.2, Figma's thin, tall wordmark dominated its row.
- The common area is the largest that fits 80% of marks in their safe box;
  the rest shrink to fit (reported as "capped").

## 6. Centre on the ink, not the box

Marks with an empty quadrant (Figma's F) look off-centre when their box is
centred. Each mark is shifted toward its alpha-weighted centroid, capped at
7% of its size so a wordmark with a big left-hand symbol does not drift.

## 7. The wall is one block

Rows spread over the whole slide float apart. Cells never get taller than
the marks need (width:height ≥ 1.55 for wordmarks, 1.15 for symbols); the
block sits at 46% of the free height — optically centred, slightly above
the geometric centre. A short last row is centred.

## 8. One asset type per wall

Wordmarks next to bare symbols never cohere, whatever the sizing does. Pick
wordmark OR symbol for the whole set. Wordmarks are the safer default;
symbols make the most uniform grid when everyone knows the brands. Many
brands have no symbol at all — the check flags them.

## 9. Every format from one layout

PPTX, PDF, HTML and PNG are written from the same computed positions, so the
preview Claude looks at is the deliverable. The HTML positions each logo in
percent of its cell and keeps the cell's shape, so the balance holds at any
width; it ships processed images, not live CSS filters (`monochrome.md`).

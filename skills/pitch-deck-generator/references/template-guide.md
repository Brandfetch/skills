# Instrumenting your own template

The bundled `assets/template.pptx` is a reference, not the product. This is
how to make the skill fill **your** deck.

## The contract

A slot is any shape whose **visible text** is a token. That's the whole
contract: type `{bf:name}` into a text box, or `{bf:lightOrDarkLogo}` into a
rectangle, and the builder finds it. Shape names are ignored (editors export
generic ones like "Text 13"), and geometry is read from each shape's own
frame at build time — move, resize, restyle, reorder slides freely and
rebuild. No code changes.

Two namespaces:

- `{bf:*}` — filled from the Brandfetch API. The full list is in
  `scripts/bf_fields.py`; run `scan_template.py` and it will flag any name it
  does not recognise.
- `{anything_else}` — yours. Name tokens after what your business sells:
  `{fee}`, `{sla}`, `{seats}`, `{go_live_date}`. They are collected at build
  time and never guessed.

## Conventions the reference template uses

Worth copying — the tooling understands them:

**Dashed outline = placeholder.** Give slot shapes a dashed border while
designing; it shows where slots are. The builder strips dashed outlines from
every slot it fills and leaves them on unfilled ones, so gaps stay visible.
Solid borders are treated as design and never touched.

**Your own logo is not a token.** It never varies per deck, so it is a static
image you place once. Same for your company name in a column header.

**Instructions live in speaker notes,** never on the slide surface. Anything
printed on the artwork ships in every client deck.

## Image slots

An image slot is a shape containing an image token. The builder keeps the
shape (its fill and solid border may be design), blanks the token, and
overlays a fitted picture. Fit is inferred from the slot itself:

| Slot | Fit |
|---|---|
| `{bf:banner}`, `{bf:icon}` | cover — fills the frame, centre-crops overflow |
| any ellipse | cover (avatar treatment; a solid stroke on the ellipse is met by a bleed) |
| large square frame (≥0.5", within 5%) | tight contain — fills the square, no inset |
| everything else | contain with a safe-box inset — wordmarks are never cropped |

**Pick the theme token to match the ground.** `theme` names the **asset's own
colour**, not the background: `light` is a white mark for dark grounds,
`dark` a near-black mark for light grounds.

| Ground | Logo token | Symbol token |
|---|---|---|
| dark slide | `{bf:lightOrDarkLogo}` | `{bf:lightOrDarkSymbol}` |
| light slide | — (use dark chain) | `{bf:darkOrLightSymbol}` |

Get this wrong and a monochrome brand renders invisible — a *coloured* brand
will hide the mistake, which is exactly why it survives review. The scanner
checks each logo slot against its slide's background and warns.

**Two logos on one slide will not weight-match.** Contain-fit equalises
frames, not marks: a near-square symbol fills a shared square while a 1.6:1
mark is height-limited to ~60% of it. The reference template's answer is a
small (0.55") symbol + name-as-text lockup, which keeps marks minor enough
that aspect variance stops mattering. If you need large marks side by side,
expect to tune — set-level optical normalisation is not implemented.

## Text slots

Slots are usually authored at the width of the token, not the content —
`{bf:description}` holds a 90-character sentence. The builder measures the
real rendered width and grows the frame toward the next slot on the row or
the card edge, so author slots at whatever size looks right and let it grow.

Keep composite lines simple: `Prepared for {bf:name} · {date}` works, since
each token substitutes independently.

## Fonts

Use fonts that ship with Office (Arial, Calibri, Cambria...) or accept two
costs: recipients without the font get a substituted layout, and your own
preview becomes untrustworthy for overflow (see `setup.md`). The reference
template is Arial with ~15% frame slack for exactly this reason.

## Checklist for a new template

1. Type tokens as visible text into the shapes that should hold them.
2. Dash the borders of slot shapes; keep design borders solid.
3. Match each logo token's theme to its slide's ground (table above).
4. Put per-slide instructions in speaker notes, not on the slide.
5. `python3 scripts/scan_template.py your-template.pptx` — fix every warning.
6. Build once against a real brand and *look at the render* before trusting it.

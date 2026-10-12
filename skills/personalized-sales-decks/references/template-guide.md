# Your own template

How to make the skill fill **your** deck. (No deck yet? Ask for a new
design in the brand — the `on-brand-presentations` skill — and onboard that.)

## The easy way: onboard a deck you already sent

Attach a deck you have already sent to a real client and say *"set up my
template"*. Claude:

1. looks up that client on Brandfetch and finds everything in the deck that
   came from them — their name, description, firmographics, and every
   picture that matches one of their logos, by file or by image;
2. proposes the per-deal values too — dates, amounts, labelled fields like
   `Sector: Retail` — named after their labels (`Kick-off` →
   `{kick_off_date}`), and asks about anything it is unsure of;
3. writes the template once you agree, test-fills it with a different brand,
   and shows you both;
4. hands you both: **your template skill** (a small skill named after your
   company that holds just your template: a `.skill` file you save to your
   skills in claude.ai, installed straight into `~/.claude/skills/` in
   Claude Code) and the **template file** to attach whenever you prefer.
   Either way the
   Brandfetch skill does the building and is never changed, so you keep its
   updates and they never touch your template.

Under the hood that is `scripts/instrument_template.py` (`--detect`, then
`--apply`). It follows every rule below, so the result is exactly what you
would have built by hand: tokens as visible text, dashed slot shapes where the
client's logos were, the previous client's image files removed from the
package.

What it cannot know on its own: free text written for that one client (a
scope line, a project name). Tell it what else changes per deck and it
becomes a token too.

The rest of this guide is the contract those templates follow — read it to
fine-tune an onboarded template, or to instrument one by hand.

## Instrumenting by hand (advanced)

Everything onboarding does, you can do in your slide editor. It is the
right path for a template designed from scratch, with no sent deck to learn
from.

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

## Conventions worth copying

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

**Use `{bf:logo}` and `{bf:symbol}`; the builder picks light or dark.** For
every logo slot it reads the colour the mark will sit on — the slot's own
tile fill, a filled shape underneath, else the slide / layout / master
background — downloads both variants, and measures how much of each is
actually visible there (pixel contrast, not the theme label). It places the
first visible one: the white mark on a dark ground, the dark mark on a light
one, and a *coloured* "dark" mark on a mid-dark ground when that is what the
brand has. If neither variant would show, the slot is left empty with its
dashed box, and the build output says why:

```
slide2.xml  {bf:symbol}  LEFT EMPTY: no variant visible on #F1EFE8 (light 0%)
```

The older tokens still work and only set which variant is tried first:

| Token | Tries first |
|---|---|
| `{bf:logo}` / `{bf:symbol}` | whatever the ground calls for (recommended) |
| `{bf:lightOrDarkLogo}` / `{bf:lightOrDarkSymbol}` | the white mark |
| `{bf:darkOrLightLogo}` / `{bf:darkOrLightSymbol}` | the dark mark |

Neither kind will place a mark that would vanish. `theme` names the **mark's
own colour**, not the background: `light` is a white mark, `dark` a dark one.

**Two logos on one slide will not weight-match.** Contain-fit equalises
frames, not marks: a near-square symbol fills a shared square while a 1.6:1
mark is height-limited to ~60% of it. A good answer is a
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
preview becomes untrustworthy for overflow (see `setup.md`). Arial with ~15%
frame slack is the safe default.

## Checklist for a hand-built template

1. Type tokens as visible text into the shapes that should hold them.
2. Dash the borders of slot shapes; keep design borders solid.
3. Match each logo token's theme to its slide's ground (table above).
4. Put per-slide instructions in speaker notes, not on the slide.
5. `python3 <skill-dir>/scripts/scan_template.py your-template.pptx` — fix every warning.
6. Build once against a real brand and *look at the render* before trusting it.

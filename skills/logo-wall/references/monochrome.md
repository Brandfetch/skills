# Monochrome without losing the mark

How the wall turns a logo into one colour, and why it is done this way.

## The problem

The obvious treatments break real logos:

| Treatment | What goes wrong |
|---|---|
| `brightness(0)` / fill every pixel | Knockouts fill in: Notion's cube becomes a solid black block, letter counters close. |
| `grayscale(1)` | Not monochrome — a grey Slack is still four tones. |
| Recolour to a flat colour, keeping alpha | Same as the first row for any opaque JPEG: the white paper becomes part of the mark. |

## The filter

A soft luminance threshold at ~90% white: everything darker is **ink**,
anything near white is **paper**, and paper becomes transparent.

```
L    = .2126 R + .7152 G + .0722 B        (sRGB, 0..1)
t    = clamp(16 L − 14.4)                 (0 below ~0.9, 1 above)
ink  = alpha × (1 − t)
out  = one flat colour, with ink as its alpha
```

`scripts/ink.py` implements this in Pillow so PPTX, PDF, PNG and HTML get
identical pixels. For a **light** source (a white logo made for dark
backgrounds) the polarity flips — near-black is paper — otherwise the rule
would erase the mark itself.

The same maths as SVG filters, for anyone applying it live in a browser
(`filter: url(#full-white)` on dark, `url(#full-dark)` on light):

```html
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <filter id="full-white" color-interpolation-filters="sRGB">
    <feColorMatrix type="matrix" values=".2126 .7152 .0722 0 0  .2126 .7152 .0722 0 0
                                         .2126 .7152 .0722 0 0  0 0 0 1 0"/>
    <feComponentTransfer result="lum">
      <feFuncR type="linear" slope="16" intercept="-14.4"/>
      <feFuncG type="linear" slope="16" intercept="-14.4"/>
      <feFuncB type="linear" slope="16" intercept="-14.4"/>
    </feComponentTransfer>
    <!-- alpha = alpha − luminance: ink stays, white goes transparent -->
    <feColorMatrix in="lum" type="matrix" result="mask"
                   values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1 0 0 1 0"/>
    <feFlood flood-color="#FFFFFF" result="ink"/>
    <feComposite in="ink" in2="mask" operator="in"/>
  </filter>
</svg>
```

The HTML output does **not** use the live filter: it ships the processed
images, because email clients, CMS embeds and some browsers strip or ignore
SVG filters, and the wall must look the same everywhere it is pasted.

## Where no filter helps

When colour is the only thing separating parts of a mark, every threshold
merges them: Mastercard's two circles become one blob, Figma's five lobes
one silhouette. The script measures this — colour edges between ink pixels
against the mark's outline — and flags any flattened logo where colour
carries ≥8% of the drawing. Shading (Notion's grey cube side) is not
counted; only a change of colour is. For those brands, ship an official
one-colour variant or keep the wall in original colours.

Credit: the filter and the Notion / Figma / Slack analysis come from the
Brandfetch engineering team's `logo-monochrome-filters` study.

# Troubleshooting

Symptom → most likely cause, in the order actually seen in practice.

## Fetching

**`curl` returns 403.** Three distinct causes that look identical:
1. Host not on your network allowlist — the response *body* says so
   explicitly; read it. Remember allowlist changes need a **new
   conversation** to take effect.
2. The `?c=` credential is stale or was edited. `src` URLs are per-response;
   get a fresh `get_brand` and use its URL verbatim.
3. You fetched a `build_logo_urls` URL. Those are display-only by design —
   they 302 to a hotlink page, whose host is not allowlisted, hence 403.

**`curl` exit status 23.** Write failure — the destination directory did not
exist. The bundled builder creates it; a hand-rolled fetch must `mkdir -p`.

**The variant I need has no PNG.** Real for smaller brands: light-theme
variants often exist only as SVG or WebP. SVG → rasterise with `cairosvg`
(setup.md §4). WebP → convert with Pillow. Never embed WebP directly (older
PowerPoint) and avoid embedding SVG (python-pptx and older Office handle it
poorly).

## Building

**A token stayed unfilled.** In order of likelihood:
1. Not a known `{bf:*}` name — run `scan_template.py`, it names the unknowns
   and lists the valid set.
2. A user token you never put in `values.json` — this is by design; supply it
   or accept the visible `{token}`.
3. Malformed: `{bf:}` empty, unbalanced braces — scanner flags these.
4. Split across runs *and* mangled — the builder merges split runs, but a
   token interleaved with different formatting (half bold) will not merge.
   Retype it in one go in the editor.

**A logo is invisible.** Theme/ground mismatch: a white (`theme=light`) mark
on a light slide or vice versa. The scanner warns about this per slot. A
coloured brand hides the mistake; test with a monochrome one (e.g. a brand
whose mark is pure black/white).

**A logo looks stretched or cropped wrong.** Check the slot frame: cover-fit
is only for banners, icons and ellipses. A wordmark in a non-square rect gets
contain — if it was cropped, the token is probably in the wrong kind of shape.
The builder asserts aspect preservation, so a genuine distortion means the
frame geometry was read from a different shape than you think — check for
nested/grouped shapes.

**Dashed boxes visible in the output.** Around a *filled* slot: you are on an
old builder — current ones strip dash-family outlines on fill. Around an
*unfilled* token: intentional; the gap is being kept visible.

## Rendering / QA

**Text overflows in the preview but the frame looks generous.** Fonts not
installed; the previewer substituted wider ones. `fc-list | grep -i <font>`.
Do not resize type to fix a preview artifact (rules.md #8).

**Validation fails on `presentation.xml` in a template-derived build.** Pass
`--original template.pptx` — templates often carry their own pre-existing
schema quirks, and baselining suppresses errors you did not cause.

**The render looks fine but the numbers are wrong.** That is not a rendering
problem. Re-read rules.md #1 and check every value against its source.

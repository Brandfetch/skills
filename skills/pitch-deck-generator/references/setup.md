# Setup

Two of these steps fail in non-obvious ways when skipped. Do them in order.

## 1. Connect the Brandfetch MCP

The skill's brand data comes from the Brandfetch MCP (`get_brand`). Connect
it from the connector directory, or add it manually:
`https://mcp.brandfetch.io/mcp`.

Without it there is no data source — the skill will not invent brand facts.

## 2. Allowlist the Brandfetch CDN

Logo files are downloaded by `curl` from **`cdn.brandfetch.io`**. If your
Claude environment restricts network egress, add that host to the allowlist
(Settings → your organisation's network egress settings).

Two traps, both learned the slow way:

- **The allowlist is read at conversation start.** A change does not apply to
  the conversation you made it from — open a new chat and test again there.
- **A 403 is not always the network.** An expired or edited `?c=` credential
  on the URL also surfaces as a 403 (see `troubleshooting.md`). Test with a
  fresh URL from a fresh `get_brand` call before concluding the allowlist is
  wrong.

Quick test once configured:

```bash
curl -sS -o /tmp/t.png "<any src URL from a fresh get_brand response>" \
  && python3 -c "from PIL import Image; print(Image.open('/tmp/t.png').size)"
```

## 3. Fonts (optional, but read this)

The bundled template uses **Arial** with generous frame slack, so it renders
acceptably with no fonts installed at all — that is deliberate.

If your own template uses other fonts, install them in the render environment
before trusting any preview: LibreOffice substitutes missing fonts with
different widths, and text then *appears* to overflow when it does not
(rules.md #8). Check with:

```bash
fc-list | grep -ci "<your font>"   # 0 = previews are approximate
```

Also point `FONT_CANDIDATES` in `scripts/build_deck.py` at your font's .ttf
files so text-frame growth is measured in the right metrics.

## 4. Python dependencies

`Pillow` (image sizing) is required. `cairosvg` is needed only when a brand's
required variant exists as **SVG only** — it happens (small brands, light-
theme variants) and PowerPoint embedding wants a raster:

```bash
pip install cairosvg
python3 -c "import cairosvg; cairosvg.svg2png(url='mark.svg', write_to='mark.png', output_width=800)"
```

WebP-only variants: convert with Pillow (`Image.open('x.webp').save('x.png')`)
— older PowerPoint does not render WebP.

## 5. Verify the loop once

```bash
python3 scripts/scan_template.py assets/template.pptx     # should report no warnings
# get_brand for any well-known domain → save verbatim as brand.json
python3 scripts/bf_fields.py brand.json                   # preview resolution
python3 scripts/build_deck.py assets/template.pptx brand.json out.pptx
```

If all three run clean, the environment is ready.

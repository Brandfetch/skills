# Setup

Two of these steps fail in non-obvious ways when skipped.

## 1. Connect the Brandfetch MCP

Brand data and logo candidates come from the Brandfetch MCP (`get_brand`,
`brand_search`). Connect it from the connector directory, or add it manually:
`https://mcp.brandfetch.io/mcp`.

## 2. Allowlist the Brandfetch CDN

Logos are downloaded by `curl` from **`cdn.brandfetch.io`**. If your Claude
environment restricts network egress, add that host to the allowlist.

Two traps, both learned the slow way:

- **The allowlist is read at conversation start.** A change does not apply to
  the conversation you made it from — open a new chat and test there.
- **A 403 is not always the network.** The `?c=` parameter on every `src` URL
  is a per-response credential; an edited or stale one also surfaces as a 403
  (the CDN 302s to a hotlink page whose host is not allowlisted). Use `src`
  URLs verbatim from a fresh `get_brand` before blaming the allowlist. URLs
  from `build_logo_urls` are display-only and cannot be fetched at all.

Quick test:

```bash
curl -sS -o /tmp/t.png "<any src URL from a fresh get_brand>" \
  && python3 -c "from PIL import Image; print(Image.open('/tmp/t.png').size)"
```

## 3. Python dependencies

`Pillow` (pixel verification, sizing) and `python-pptx` (slide assembly).
Both are commonly preinstalled; otherwise `pip install Pillow python-pptx`.

If a brand's needed variant exists only as SVG, rasterise it first:
`pip install cairosvg`, then
`cairosvg.svg2png(url='mark.svg', write_to='mark.png', output_width=800)`.
WebP-only variants: convert with Pillow — older PowerPoint does not render
WebP.

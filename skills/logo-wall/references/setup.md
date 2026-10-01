# Setup

Two of these steps fail in non-obvious ways when skipped.

## 1. Connect the Brandfetch MCP

Brand data and logo candidates come from the Brandfetch MCP (`get_brand_data`,
`brand_search`). Connect it from the connector directory, or add it manually:
`https://mcp.brandfetch.io/mcp`.

## 2. Allowlist the Brandfetch CDN

Logos are downloaded by `curl` from **`cdn.brandfetch.io`**. If your Claude
environment restricts network egress, add that host to the allowlist.

Two traps, both learned the slow way:

- **The allowlist is read at conversation start.** A change does not apply to
  the conversation you made it from — open a new chat and test there.
- **A 403 is not always the network.** The `?c=` parameter on every `src` URL
  is a credential; an edited or rebuilt URL also surfaces as a 403 (the CDN
  302s to a hotlink page whose host is not allowlisted). Use `src` URLs
  verbatim from a `get_brand_data` response before blaming the allowlist. URLs
  from `build_logo_urls` are display-only and cannot be fetched at all.

Quick test:

```bash
curl -sS -o /tmp/t.png "<any src URL from a get_brand_data response>" \
  && python3 -c "from PIL import Image; print(Image.open('/tmp/t.png').size)"
```

## 3. Python dependencies

Only **Pillow**. PPTX and PDF files are written directly, so `python-pptx` and
`reportlab` are not needed.

SVG-only variants (common: some brands publish their main logo only as SVG)
are rasterised automatically with the first of `cairosvg`, `rsvg-convert`
(librsvg) or ImageMagick that is available. If none is, the variant is
reported as a failed candidate — `pip install cairosvg` fixes it. WebP is
read by Pillow directly.

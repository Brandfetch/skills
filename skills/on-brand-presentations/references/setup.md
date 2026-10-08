# Setup

Two of these steps fail in non-obvious ways when skipped.

## 1. Connect the Brandfetch MCP

Brand data comes from the Brandfetch MCP (`get_brand_data`,
`get_brand_context`, `brand_search`). Connect it from the connector
directory, or add it manually: `https://mcp.brandfetch.io/mcp`.

Without it there is no data source — the skill will not invent brand facts.

## 2. Allowlist the Brandfetch CDN

Logo files are downloaded by `curl` from **`cdn.brandfetch.io`**. If your
Claude environment restricts network egress, add that host to the allowlist.

Two traps, both learned the slow way:

- **The allowlist is read at conversation start.** A change does not apply to
  the conversation you made it from — open a new chat and test there.
- **A 403 is not always the network.** The `?c=` parameter on every `src` URL
  is a credential; an edited or rebuilt URL also surfaces as a 403. Use `src`
  URLs verbatim from a `get_brand_data` response before blaming the
  allowlist. URLs from `build_logo_urls` are display-only and cannot be
  fetched at all.

Quick test:

```bash
curl -sS -o /tmp/t.png "<any src URL from a get_brand_data response>" \
  && python3 -c "from PIL import Image; print(Image.open('/tmp/t.png').size)"
```

## 3. Presentation tooling

This skill decides the branding; the environment's pptx tooling (a pptx
skill, `python-pptx` or `pptxgenjs`) builds the file. `cairosvg` is needed
only when a brand's logo exists as SVG only. Convert WebP-only variants to
PNG with Pillow: older PowerPoint does not render WebP.

---
name: ticker-logos
description: Resolve stock tickers, ETF tickers, ISINs, and crypto symbols to company logos and brand records for watchlists, portfolio UIs, and financial apps, via Brandfetch. Use when the user has financial instrument identifiers and wants logos or brand data for them, or asks "logo for ticker <X>", "logos for my watchlist", or "brand data by ISIN".
license: MIT
---

# Ticker logos

Resolve financial identifiers to logos or full brand records.

## Requirements

- Display-only: a Brandfetch client ID for CDN URLs (free to 500,000 requests/month, soft-capped).
- Full records: `BRANDFETCH_API_KEY` or the Brandfetch MCP; one credit per identifier.

## Two paths, pick per need

**Display (no credits).** Build CDN URLs with the identifier in place of the domain:
`https://cdn.brandfetch.io/{identifier}/w/{px}/theme/{light|dark}/fallback/lettermark?c={clientId}`
Works for tickers, ISINs, and crypto symbols. With the MCP, `build_logo_urls` accepts a list of identifiers and an explicit `identifier_type` in one call. Hotlink these URLs; do not fetch them programmatically.

**Full record (1 credit each).** MCP `get_brand`, or explicit HTTP routes:
- `GET https://api.brandfetch.io/v2/brands/ticker/{ticker}`
- `GET /v2/brands/isin/{isin}`
- `GET /v2/brands/crypto/{symbol}`
Auto-detection also works via `/v2/brands/{identifier}` (resolved domain → ticker → ISIN → crypto). Prefer explicit routes for batch jobs; auto-detection can misroute an ambiguous string.

## Procedure

1. **Load identifiers** from the CSV, sheet, or code. Classify each: ticker, ISIN (12 chars, 2-letter prefix + checksum), crypto symbol. Ask when a string is ambiguous between ticker and crypto (e.g. `ETH`).
2. **Choose the path.** UI display → CDN URLs. Colors, names, or industry needed → full records; check quota first via `GET /v2/viewer` (free) and confirm if the list exceeds remaining credits.
3. **Resolve and deduplicate.** One lookup per unique identifier.
4. **Output.** New CSV/sheet columns (`logo_url`, and for full records `name`, `domain`, `primary_color` from the `accent` hex), or apply edits to the rendering code with theme matched to the UI background.
5. **Report misses.** Unresolved identifiers get the fallback URL and a flag. Coverage is top 10,000 tickers/ETFs, ISINs, top 2,000 crypto symbols; misses outside that range are expected, never hidden.

## Rules

- Never map an identifier to a company by your own knowledge; the API's resolution is the answer.
- On HTTP 429 (Brand API), stop and report progress. CDN URLs keep working.
- Match logo `theme` to the background: dark UIs take `light` assets.

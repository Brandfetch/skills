---
name: ticker-logos
description: Resolve stock tickers, ETF tickers, ISINs, and crypto symbols to company logos and brand records for watchlists, portfolio UIs, and financial apps, via Brandfetch. Use when the user has financial instrument identifiers and wants logos or brand data for them, or asks "logo for ticker <X>", "logos for my watchlist", or "brand data by ISIN".
license: MIT
---

# Ticker logos

Resolve financial identifiers to logos or full brand records.

## Requirements

- Display-only: a Brandfetch client ID for CDN URLs (free to 500,000 requests/month, soft-capped). With the MCP, `build_logo_urls` adds it for you.
- Full records: `BRANDFETCH_API_KEY` or the Brandfetch MCP; one credit per identifier.

## Two paths, pick per need

**Display (no credits).** Build CDN URLs with the identifier type and the identifier in place of the domain:
`https://cdn.brandfetch.io/{ticker|isin|crypto}/{identifier}/w/{px}/theme/{light|dark}/fallback/lettermark?c={clientId}`
Always include the type segment: without it the CDN guesses, and `ETH` resolves to the Ethan Allen stock before Ether. With the MCP, `build_logo_urls` takes a list of identifiers and an explicit `identifier_type`, one call per type (every identifier in a call must share it). Hotlink these URLs; do not fetch them programmatically.

**Full record (1 credit each).** MCP `get_brand_data`, or explicit HTTP routes:
- `GET https://api.brandfetch.io/v2/brands/ticker/{ticker}`
- `GET /v2/brands/isin/{isin}`
- `GET /v2/brands/crypto/{symbol}`
Auto-detection also works via `/v2/brands/{identifier}` (resolved domain → ticker → ISIN → crypto). Prefer explicit routes for batch jobs; auto-detection can misroute an ambiguous string. MCP `get_brand_data` always auto-detects: for a symbol that is both a ticker and a crypto (ETH, SOL…), use the HTTP `/v2/brands/crypto/{symbol}` route, or check `company.financialIdentifiers` in the response before trusting it.

## Procedure

1. **Load identifiers** from the CSV, sheet, or code. Classify each: ticker, ISIN (12 chars, 2-letter prefix + checksum), crypto symbol. Ask when a string is ambiguous between ticker and crypto (e.g. `ETH`).
2. **Choose the path.** UI display → CDN URLs. Colors, names, or industry needed → full records; check quota first via `GET /v2/viewer` (free) and confirm if the list exceeds remaining credits.
3. **Resolve and deduplicate.** One lookup per unique identifier. A ticker and an ISIN for the same company cost a credit each: if both are in the list, look up one.
4. **Output.** New CSV/sheet columns (`logo_url`: the CDN URL on the display path, the icon's `src` URL from the record on the full-record path; and for full records `name`, `domain`, `primary_color` from the `accent` hex, uppercased), or apply edits to the rendering code with theme matched to the UI background.
5. **Report misses.** Unresolved identifiers get the fallback URL and a flag. Coverage is top 10,000 tickers/ETFs, ISINs, top 2,000 crypto symbols; misses outside that range are expected, never hidden.

## Rules

- Never map an identifier to a company by your own knowledge; the API's resolution is the answer.
- On HTTP 429 (Brand API), stop and report progress. CDN URLs keep working.
- Match logo `theme` to the background: dark UIs take `light` assets.

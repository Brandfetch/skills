---
name: real-logos-migration
description: Replace favicons, Google favicon URLs, Clearbit Logo API endpoints, or hardcoded logo images with Brandfetch Logo API CDN URLs across a codebase or domain list. Use when the user wants better company logos in their UI, mentions favicons looking bad, needs a Clearbit Logo API migration or alternative, or has a list of domains needing displayable logo URLs.
license: MIT
---

# Migrate to real logos

Map every logo source to a Logo API CDN URL. This skill edits references, not images.

## Requirements

- A Brandfetch client ID (`{clientId}`) from the developer dashboard, for the `?c=` parameter. Ask the user for it; do not ship URLs without it.
- Codebase access for repo scans, or the domain list as CSV.
- No API credits consumed: Logo API is free to 500,000 requests/month, soft-capped.

## URL grammar

Base: `https://cdn.brandfetch.io/{domain}?c={clientId}`

- Size: `/w/{px}` and/or `/h/{px}` path segments; aspect ratio is preserved.
- Theme: `/theme/light` or `/theme/dark` (pick against the rendering background: dark UI takes `light` assets). For `/type/logo` and `/type/symbol` it is a hard filter: a brand without that variant returns the fallback, not its other theme. Use `/fallback/404` with an `onerror` handler that retries without `/theme/`, or accept a blank slot. Icons fall back across themes on their own.
- Type: `/type/icon` (default; avatars, lists), `/type/logo` (headers, wide slots), `/type/symbol` (mark only), as the last path segment.
- Fallback: `/fallback/lettermark` (icons only), `/fallback/transparent`, `/fallback/brandfetch`, or `/fallback/404`.
- Tickers, ISINs, and crypto symbols also work as the identifier.
- The CDN never upscales: a small source asset comes back smaller than `/w/` or `/h/`. Set the rendered size in CSS or attributes. `/type/symbol` coverage is sparser than icons, so always set a fallback.

Example: `https://cdn.brandfetch.io/acme.com/w/64/theme/dark/fallback/lettermark?c={clientId}`
Wide logo: `https://cdn.brandfetch.io/acme.com/h/32/theme/dark/fallback/transparent/type/logo?c={clientId}`

## Procedure

1. **Find sources.** Grep for: `favicon.ico`, `google.com/s2/favicons`, `gstatic.com/faviconV2`, `logo.clearbit.com`, `logo.dev`, hardcoded `/logos/` image paths keyed by company. List every hit with file and line.
2. **Determine slot per hit:** avatar/list (icon, 32 to 64px), header (logo), mark (symbol). Read the surrounding code for the rendered size and background theme.
3. **Build replacements** with the grammar above. Clearbit is a direct swap: `logo.clearbit.com/{domain}` → `cdn.brandfetch.io/{domain}?c={clientId}`, then add size and fallback. A filename is not a domain: for hardcoded image paths (`/logos/acme.png`), take the domain from adjacent data (a `domain` field), or resolve it through Brand Search and confirm. Otherwise put the hit on the flagged list.
4. **Apply.** In a repo, make the edits and show the diff. For a CSV, output a new column of URLs.
5. **Report** a before/after table and a flagged list: dynamic URLs it could not resolve statically, identifiers that are not domains, hits needing a human decision.

## Rules

- Hotlink the CDN. Do not download logos into the repo, cache asset bytes, or proxy them; that breaks the Logo API terms.
- These URLs are for browser rendering. Programmatic fetching of CDN assets with only a client ID is blocked; anything needing bytes goes through the Brand API instead. Headless browsers and HEAD requests are rejected too (`302 automated_traffic`, `404`), so screenshot tests in CI show missing logos: verify in a real browser.
- Logos identify their brands. Do not place them where they imply endorsement of the user's product.
- Never invent a domain from a company name; unresolved names go through Brand Search or get flagged.

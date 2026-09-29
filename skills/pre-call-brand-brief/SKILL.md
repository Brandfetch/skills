---
name: pre-call-brand-brief
description: Build a one-page brand brief on any company from its domain - positioning, audience, products, voice, visual identity, and logos. Use when the user wants to prep for a sales call, research a prospect or account, summarize what a company does, or asks "brief me on <company>" or "what should I know about <domain> before my meeting".
license: MIT
---

# Pre-call brand brief

Produce a one-page brief on a company from its domain, grounded in Brandfetch data rather than model memory.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for direct HTTP with `Authorization: Bearer <key>`.
- Cost: 2 credits per brief (one Brand API call, one Brand Context API call).

## Procedure

1. **Resolve the domain.** If given a name instead of a domain, use MCP `brand_search` or `GET https://api.brandfetch.io/v2/search/{name}`. Confirm ambiguous matches with the user before spending credits.
2. **Fetch both records in parallel.**
   - MCP `get_brand` or `GET /v2/brands/{domain}`: logos, colors, fonts, links, industry, employees, founded year, location.
   - MCP `get_brand_context` or `GET /v2/context/{domain}` (accepts `Accept: text/markdown`): identity, positioning, voice, style.
3. **Compose the brief** in this order, one page maximum:
   - Header: canonical name, domain, one-line description, industry, employees, founded, HQ. `company.employees` is the floor of a size band: show `10001` as "10,001+", never as an exact headcount.
   - Their words: tagline and mission, quoted verbatim, never paraphrased.
   - Positioning: value proposition, then audience segments. If the user said what they are selling, mark the segment that matches their buyer.
   - Products and services: names with one-line descriptions.
   - Voice: attributes, plus what the brand avoids. Useful for mirroring their language.
   - Assets: logo and icon URLs (light and dark), `accent` color hex (the brand's primary color).
   - Links: LinkedIn, X, and other socials from the record.
4. **Flag mismatches.** If the context's `meta.canonical_name` differs from what the user said, surface it.
5. **Optional filing.** If a CRM is connected and the user asks, save the brief as a note on the matching record.

## Rules

- Quote `tagline` and `mission` verbatim. Paraphrase only the neutral `description`.
- Do not blend audience segments into one generic audience. Pick or list them as returned.
- If context resolution fails (domain not found, not crawlable), say so and deliver the Brand API half alone. Never fill gaps from memory.
- On HTTP 429, stop and report remaining quota via `GET /v2/viewer` (free).

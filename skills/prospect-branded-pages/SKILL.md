---
name: prospect-branded-pages
description: Generate landing pages, one-pagers, or demo screens themed in a prospect's brand - their logo, colors, and fonts injected into the user's template - for ABM and sales personalization. Use when the user wants to personalize a page or deck per prospect or account, "make this page look like <company>", or batch-generate branded collateral from a prospect list. For a slide deck, use on-brand-presentations instead.
license: MIT
---

# Branded page per prospect

Theme the user's template with each prospect's verified brand assets.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for `GET https://api.brandfetch.io/v2/brands/{domain}` with `Authorization: Bearer <key>`.
- A template: an HTML file, a component, or a described layout. If none exists, draft a clean single-page template first and confirm it.
- Cost: one brand fetch per unique domain.

## Procedure

1. **Collect inputs.** Template plus one domain or a CSV/list of domains. Deduplicate domains.
2. **Fetch each brand** via MCP `get_brand` or the HTTP endpoint. Cache by domain for the run.
3. **Select assets per prospect.**
   - Logo: `type: "logo"` for the header slot, `type: "icon"` for favicons or small marks. Match `theme` to the template background: dark backgrounds take the `light` variant and light backgrounds the `dark` variant. Use returned `src` URLs exactly, unmodified.
   - Colors: `accent` (the brand's primary color) for the accent slot, a `brand` color as secondary. Compute contrast against the template background; if below WCAG AA for text, use the color only on non-text elements and say so.
   - Fonts: apply the `title` font to headings when it is a common or Google font; otherwise keep the template font and note the brand font's name.
4. **Generate one file per prospect**, named `{domain}.html` (or the template's format). Company name and description from the record can fill designated placeholders.
5. **Deliver** the files plus an index table: domain, assets used, contrast notes, anything skipped.

## Rules

- Never alter, recolor, or distort a logo. Placement and sizing only.
- These pages identify the prospect to the prospect. Do not present them publicly as customer endorsements, and add no claims of affiliation.
- A domain with no usable logo gets the template default plus a note. Never a favicon, never a generated substitute.
- On HTTP 429, stop and report which prospects completed.

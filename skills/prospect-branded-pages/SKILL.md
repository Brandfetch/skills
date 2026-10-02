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
- Cost: one brand fetch per unique domain. Logo API URLs cost no credits (free to 500,000 requests/month); the MCP's `build_logo_urls` adds the client ID, and over HTTP you need one from the developer dashboard.

## Procedure

1. **Collect inputs.** Template plus one domain or a CSV/list of domains. Deduplicate domains. Ask how the pages will be used if it isn't clear: **hosted** (a website, a demo environment) or **sent as files** (email attachments, offline, PDF exports). It decides how logos are embedded in step 3.
2. **Fetch each brand** via MCP `get_brand_data` or the HTTP endpoint. Cache by domain for the run.
3. **Select assets per prospect.**
   - Logo: `type: "logo"` for the header slot, `type: "icon"` for favicons or small marks. Match `theme` to the template background: dark backgrounds take the `light` variant and light backgrounds the `dark` variant. Pick from the types and themes the record actually has.
     - **Hosted pages:** link the Logo API. Build the URL with MCP `build_logo_urls` (`type`, `theme`, `height` for the slot), or by hand: `https://cdn.brandfetch.io/{domain}/h/{px}/theme/{light|dark}/fallback/404/type/logo?c={clientId}`. For `logo` and `symbol`, a missing theme returns the fallback rather than the other theme, so add an `onerror` handler that retries the URL without `/theme/…`. Logo API URLs render in browsers only: headless screenshots and `curl` are blocked, so check the pages in a real browser.
     - **Pages sent as files:** download each logo from its `src` URL (exactly as returned) and ship the file beside the page, or inline it as a data URI, so the page works offline.
   - Colors: `accent` (the brand's primary color) for the accent slot, a `brand` color as secondary (none on record: the template default, and say so). Compute contrast against the template background; if below WCAG AA for text, use the color only on non-text elements and say so.
   - Fonts: apply the `title` font to headings when it is a common or Google font; otherwise keep the template font and note the brand font's name.
4. **Generate one file per prospect**, named after the input domain, `{domain}.html` (or the template's format); note in the index when the record's `domain` differs (`notion.so` → `notion.com`). Company name and description from the record can fill designated placeholders. `description` is the brand's own copy, often first-person marketing: check it reads right in your template's voice before using it.
5. **Deliver** the files plus an index table: domain, assets used (Logo API URL or file), contrast notes, anything skipped.

## Rules

- Never alter, recolor, or distort a logo. Placement and sizing only.
- Hotlink Logo API URLs as they are: never download, cache or proxy their bytes (that breaks the Logo API terms). Bytes for file-based pages come from `src` URLs.
- These pages identify the prospect to the prospect. Do not present them publicly as customer endorsements, and add no claims of affiliation.
- A domain with no usable logo gets the template default plus a note. Never a favicon, never a generated substitute.
- On HTTP 429, stop and report which prospects completed.

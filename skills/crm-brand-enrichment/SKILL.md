---
name: crm-brand-enrichment
description: Enrich CRM company records, CSVs, or spreadsheets with Brandfetch brand data - logos, colors, industry, employee count, founded year, location, and social links - or run a coverage report on a sample. Use when the user wants to enrich accounts or companies, fill missing logos, clean up company records, add firmographics in HubSpot, Attio, Salesforce, a CSV, or a Google Sheet, or evaluate and benchmark Brandfetch coverage on their own data.
license: MIT
---

# Enrich CRM records with brand data

Resolve each company's domain through the Brandfetch Brand API and write brand fields back to the record.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` set for direct HTTP calls with `Authorization: Bearer <key>`.
- Read/write access to the target: CRM MCP, CSV file, or spreadsheet.

## Procedure

1. **Check quota first (HTTP only).** Call `GET https://api.brandfetch.io/v2/viewer` (free, never consumes credits). Read `x-api-key-quota` and `x-api-key-approximate-usage` headers on responses. If remaining quota is smaller than the record count, tell the user and ask whether to enrich a subset. With the MCP, skip this: it reports an exhausted quota itself.
2. **Load records.** Identify the domain column or property. Normalize: lowercase, strip scheme, path, and `www.`.
3. **Resolve each domain.** Use the MCP `get_brand_data` tool, or `GET https://api.brandfetch.io/v2/brands/{domain}`. Cache results by domain within the run so duplicate domains cost one call.
4. **No domain? Search first.** Use MCP `brand_search` or `GET /v2/search/{name}`. Accept the top result only if its name closely matches the record. Otherwise list candidates and ask the user. Never guess silently.
5. **Map fields.**
   - Logo: prefer `type: "icon"` for avatar-sized slots, `type: "logo"` for wide slots. Use the `src` URLs exactly as returned, never edited.
   - Colors: the `accent` hex (the brand's primary color).
   - Company: `company.industries[0].name`, `company.employees`, `company.foundedYear`, `company.location.city` + `company.location.country`, `company.kind`. `company.employees` is the floor of a size band: show `10001` as "10,001+", never as an exact headcount.
   - Links: LinkedIn and Twitter/X URLs from `links`.
6. **Write back.** Update the CRM properties or CSV columns. Create missing custom properties when the CRM allows it, after confirming names with the user.
7. **Report.** Output a summary table: records processed, enriched, skipped (no domain, no match, quota), and fetches consumed.

## Coverage report mode

When the user wants to evaluate rather than enrich ("test Brandfetch on our list", "what's your coverage on our accounts"), run steps 1 to 3 on the sample, skip write-back, and report statistics only: share of domains resolved, share with a logo, with colors, with a description, and the misses listed. Compare against the published benchmarks (95% logo coverage on core brands, 86% on the long tail, at docs.brandfetch.com/accuracy/coverage-and-quality) and state the sample's segment honestly; a long-tail-heavy list should be compared to the long-tail number.

## Rules

- Never invent brand data. A failed lookup is reported as not found.
- On HTTP 429, stop and report. Do not retry in a loop.
- Do not download logo bytes into the CRM unless the CRM requires a file; store the returned URL.
- Logos identify the company on its own record. That is standard referential use. Do not use them to imply endorsement.

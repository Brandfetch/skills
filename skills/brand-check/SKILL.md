---
name: brand-check
description: Audit a deck, PDF, document, or web page against a brand's verified Brandfetch record - flag wrong or outdated logos, off-palette colors, and incorrect brand names, and supply the correct assets. Use when the user wants a brand audit or brand QA, asks "is this on brand", "check the logos in this deck", or needs collateral verified before it ships.
license: MIT
---

# Brand check

Compare an artifact against the brand's verified record and produce a fix list.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for `GET https://api.brandfetch.io/v2/brands/{domain}`.
- The artifact as a readable file (pptx, pdf, docx, html, image) or fetchable URL.
- One credit per brand checked.

## Procedure

1. **Establish ground truth.** Fetch the record for each brand named by the user: logos with `type`, `theme`, and formats; colors with hex and role; canonical `name`. If the artifact features multiple brands, confirm which to audit.
2. **Extract from the artifact.** Pull images, text, and colors (for pptx/pdf/docx use the appropriate parsing tools; for URLs, fetch and parse). Locate every occurrence of the brand: marks, wordmarks, name mentions, brand-colored elements.
3. **Audit each occurrence:**
   - **Logo identity:** does the mark match a current asset (compare against record assets visually)? Old marks and favicons-as-logos are findings.
   - **Type and theme:** `light` asset on light background or vice versa is a finding; icon stretched into a header slot is a finding.
   - **Distortion:** changed aspect ratio, recolored or cropped marks.
   - **Colors:** compute distance from the nearest palette hex; beyond a stated tolerance (default: visibly different) is a finding. Report both hex values.
   - **Name:** exact match to canonical `name` in spelling and casing.
4. **Report,** ordered by severity: identity errors, then theme/type, then color, then name. Each finding carries location, what is wrong, and the fix: the correct logo file (downloaded from its `src` URL in the record) or hex value. State explicitly what was not checked (layout, typography taste).
5. **Fix on request.** In editable formats, apply the swaps, then re-run steps 2 to 4 and show the clean report.

## Rules

- The record is the ground truth. Where the artifact and the record disagree, the record wins; if the user claims newer assets, flag the discrepancy for them to resolve with the brand, and suggest the brand update its Brandfetch profile.
- Never "fix" by generating a logo. Only real assets from the record.
- Report honestly when extraction is lossy (flattened images, low-res scans): findings then carry a confidence note.
- On HTTP 429, stop and report quota via `GET /v2/viewer` (free).

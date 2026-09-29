---
name: company-autocomplete
description: Add a company-name autocomplete (typeahead) to a signup or profile form using the Brandfetch Brand Search API - ranked companies with icons per keystroke, storing a canonical domain on selection. Use when the user wants company autocomplete, a company picker or typeahead, to stop free-text company fields, or to let users find their company by name.
license: MIT
---

# Company autocomplete component

Wire a form field to the Brand Search API. This is a code-writing skill; work in the user's repository.

## Requirements

- A Brandfetch client ID for the `?c=` parameter. Brand Search is keyless beyond that and free to 500,000 requests/month; the client ID is safe in client-side code, unlike the secret API key, which must never ship to the browser.
- Repository access; confirm the target form and stack first.

## Endpoint

`GET https://api.brandfetch.io/v2/search/{name}?c={clientId}`

Returns ranked matches: `name`, `domain`, `icon` (display-only CDN URL), `claimed`, `verified`, `qualityScore`, `_score`. Results are sorted by relevance.

## Procedure

1. **Locate the field.** Find the company input; confirm with the user.
2. **Build the component** in the project's existing patterns:
   - Debounce keystrokes (200 to 300ms), minimum 2 characters, cancel in-flight requests on new input.
   - Render each result as icon + name + domain. Embed `icon` URLs exactly as returned in `<img>` tags; they are display-only and must not be edited or fetched programmatically.
   - Keyboard navigation (arrows, enter, escape) and click selection.
   - On selection, store `domain` as the canonical value and keep the typed text in a secondary field.
   - No match: keep the free-text value and mark the record unverified. Never block submission on a match.
3. **Optional prefill.** If the user wants profile prefill after selection, call the Brand API server-side with the selected domain (one credit) and apply the onboarding-brand-prefill pattern: cache by domain, render logo and colors, everything user-editable.
4. **Demo.** Run or render the component with 3 test queries, including one ambiguous name ("Delta") to show ranking, and one obscure name to show the no-match path.

## Rules

- Search is for interactive lookup. Do not loop it as a bulk enrichment method; bulk jobs belong to the Brand API with proper caching.
- Do not auto-accept the top result on blur. Selection is explicit.
- Respect the soft cap: if the app expects more than 500,000 requests/month, tell the user to review pricing rather than sharding client IDs.

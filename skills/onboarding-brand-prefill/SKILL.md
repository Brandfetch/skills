---
name: onboarding-brand-prefill
description: Add brand personalization to a product's signup or onboarding flow - capture the domain from the user's work email, fetch their brand via the Brandfetch Brand API, cache it, and render their logo and colors on first load. Can also enrich the new signup's record (industry, size, location) in the CRM or database from the same call. Use when the user wants onboarding personalization, "show the user's logo at signup", brand prefill, to enrich signups or new users, or to reduce setup friction in a PLG product.
license: MIT
---

# Brand prefill for onboarding

Implement the pattern: work email in, branded first screen out. This is a code-writing skill; work in the user's repository.

## Requirements

- `BRANDFETCH_API_KEY` available server-side. Never expose the secret key in client code.
- Repository access. Identify the signup flow before writing anything.

## Procedure

1. **Locate the flow.** Find where the email is captured and where the post-signup screen renders. Confirm both files with the user.
2. **Extract the domain.** Take the part after `@`, lowercase it. Maintain a denylist of free providers (gmail.com, outlook.com, yahoo.com, icloud.com, and similar); denylisted domains skip personalization entirely.
3. **Fetch server-side.** `GET https://api.brandfetch.io/v2/brands/{domain}` with `Authorization: Bearer <key>`. Timeout at 2 seconds; on timeout or error, render the default flow. Personalization must never block signup.
4. **Cache.** Store the response by domain (your DB or cache layer, 24h+ TTL). Repeat signups from one company must not spend credits.
5. **Render.**
   - Logo: pick `type: "icon"` for avatars, `type: "logo"` for headers, matching the screen's theme (`light`/`dark` variants are in the record).
   - Colors: `primary` or `accent` hex into the accent slots. Check contrast against your background before applying.
   - Name and description: prefill the company profile fields, editable by the user.
6. **Fallback.** For avatar slots with no asset, use the Logo CDN with `fallback/lettermark`: `https://cdn.brandfetch.io/{domain}?c={clientId}` (client ID from the developer dashboard). Otherwise render the default theme.
7. **Enrich the signup record (optional).** If the user also wants new accounts enriched for routing, scoring, or reporting: from the same cached response, write `industries[0].name`, `employees`, `foundedYear`, and `location` to the CRM or database record at signup. Same call, no extra credits.
8. **Demo it.** Run the flow with 2 or 3 user-chosen test domains and show the rendered screens or component output.

## Rules

- One API call per new domain, cached after. This is the production pattern.
- The user can always override prefilled data. Prefill, never lock.
- Do not store logo bytes; store URLs from the response and hotlink CDN assets.
- If the domain returns no brand, say so in the demo output. Never fake a brand.

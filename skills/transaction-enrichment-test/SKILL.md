---
name: transaction-enrichment-test
description: Enrich raw bank or card transaction descriptors with merchant identity - name, domain, industry, logo - via the Brandfetch Transaction API, and produce a match-rate report. Use when the user has statement lines, payment descriptors, or transaction strings to identify, wants to test or benchmark transaction enrichment, or asks "what merchant is <descriptor>".
license: MIT
---

# Merchant enrichment test

Resolve raw payment descriptors to merchants and report the match rate honestly.

## Requirements

- Brandfetch MCP connected (its `enrich_transaction` tool), or `BRANDFETCH_API_KEY` with Transaction API access for `POST https://api.brandfetch.io/v2/brands/transaction`.
- Input: descriptors with an ISO 3166-1 alpha-2 country code per row. Default to `US` only when the user confirms the data is US-only.

## Procedure

1. **Load and normalize.** Read the CSV/Excel. Trim whitespace. Deduplicate by normalized descriptor text and country; enrich each unique pair once.
2. **Resolve each unique descriptor.** MCP `enrich_transaction` with `transaction_label` and `country_code`, or the HTTP endpoint. Cache results by normalized descriptor within the run.
3. **Write the enriched file** with added columns: merchant name, domain, industry, icon URL, resolution status.
   - Resolved: fill all columns from the response.
   - Unresolved: keep the raw descriptor, mark status `unresolved`, leave merchant columns empty. Never substitute a guess.
4. **Report.**
   - Match rate: resolved / total unique descriptors, and the same weighted by row count.
   - Logo rate: share of resolved merchants with an icon or logo asset.
   - The 10 hardest lines: unresolved descriptors, for human review.
5. **Sample check.** Show the user 5 random resolved rows for spot verification before declaring the run done.

## Rules

- Never infer a merchant from the descriptor text yourself. The API's answer or `unresolved` are the only two outcomes.
- On HTTP 429, stop immediately and report how many rows completed. Do not retry in a loop.
- A 400 `Failed to enrich transaction` means no confident match: mark the row `unresolved` and continue. It is an expected outcome, not a bug: never report it with `send_feedback`.
- Recommended production handling, and say this in the report: cache resolutions by normalized descriptor text, and show raw text when a descriptor cannot be resolved.
- Transaction API is an enterprise product. If the key lacks access, report the exact error and point to Talk to sales; do not fall back to guessing merchants via search.

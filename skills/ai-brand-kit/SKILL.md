---
name: ai-brand-kit
description: Build a verified brand kit for AI generation from any domain - logo files, hex colors, fonts, voice attributes, and visual style - formatted for image, video, or copy models. Use when the user wants on-brand AI output, a brand kit or brand context block, "generate something in <company>'s brand", or to ground an LLM, image model, or ad generator in a real brand identity.
license: MIT
---

# Brand kit for AI generation

Assemble a paste-ready brand kit from Brandfetch data. The kit replaces model memory as the source of brand truth.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for direct HTTP with `Authorization: Bearer <key>`.
- Cost: 2 credits per kit (`GET /v2/brands/{domain}` + `GET /v2/context/{domain}`).

## Procedure

1. **Resolve the domain.** Unknown or ambiguous names go through `brand_search` / `GET /v2/search/{name}` first; confirm with the user before spending credits.
2. **Fetch in parallel:** MCP `get_brand_data` and `get_brand_context` (or the HTTP endpoints above).
3. **Assemble the kit** with these sections:
   - **Identity:** canonical name, domain, one-line description, tagline verbatim.
   - **Logos:** for each of `logo`, `symbol`, `icon`: download the file from its `src` URL (exactly as returned) and ship it with the kit, listing theme and format. `theme: light` is a light logo for dark backgrounds, `theme: dark` one for light backgrounds. Note which slot each type is for. Ignore `type: "other"` variants unless the record has no `logo`. Never substitute Logo API (`build_logo_urls`) links for the files.
   - **Colors:** hex values with roles (`accent` is the primary color, then `brand`, `dark`, `light`). No `accent`: write "accent: none on record" and tell the model not to add a brand-coloured highlight.
   - **Typography:** `title` and `body` font names and origins.
   - **Voice:** attributes list, then the avoid-list. Include 1 or 2 verbatim phrases (tagline, mission) as tone anchors.
   - **Visual style:** style attributes from context.
   - **Constraints:** do not generate or redraw the logo; use the files above. Do not invent colors outside the palette.
4. **Format for the target** the user names:
   - Copy/LLM: a system-prompt block, voice-first.
   - Image/video: a prompt preamble, colors and style first, logo placement as an instruction to composite the real file, not to draw it.
   - Pipeline: JSON with the sections as keys.
5. **If generation is requested next,** pass the kit and the constraints into the generation step, and composite real logo files rather than describing them to the model.

## Rules

- Never let a model draw, restyle, or approximate a logo. Real files only.
- Colors come from the record. If a needed role is missing, say so; do not invent a hex.
- If context fails to resolve, ship the asset half and mark voice/style as unavailable.
- Generated output represents the brand; when the brand is not the user's own, remind them to get the brand owner's sign-off before publishing.

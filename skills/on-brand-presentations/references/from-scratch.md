# Build a deck from scratch

The path for users with no template: Claude designs the deck in a brand's
verified identity. Build it from the brand's record, never from model memory.

## Requirements

- Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for HTTP with `Authorization: Bearer <key>`.
- A way to produce the deck: the environment's pptx tooling or skill. Follow that tooling's own guidance for construction; this skill governs the branding inputs. If there is none, say so rather than hand-writing OOXML.
- Cost: 2 credits per brand (`GET /v2/brands/{domain}` + `GET /v2/context/{domain}`).

## Procedure

1. **Resolve the brand.** Domain from the user, or `brand_search` / `GET /v2/search/{name}` for a name; confirm ambiguous matches. Note whether the deck is in the user's own brand or another company's.
2. **Fetch the kit.** MCP `get_brand` and `get_brand_context` in parallel.
3. **Get real asset bytes.** Download the asset `src` URLs from the `get_brand` response verbatim — their `?c=` parameter is a per-response credential, so never edit or reuse one from an old response. If the CDN cannot be reached, read the MCP's `bf://asset/{domain}/{type}` resources instead. URLs from `build_logo_urls` are display-only and cannot be downloaded. Prefer SVG, fall back to the largest PNG. Pick `theme` variants to match slide backgrounds: a dark slide takes the `light` logo.
4. **Apply the brand.**
   - Logos: title slide (type `logo`), small footer or corner mark on content slides (type `icon` or `symbol`). Composite the files; never redraw, recolor, stretch, or crop.
   - Colors: `accent` (the brand's primary color), then `brand` colors, for accents, headings, and charts. Backgrounds stay neutral (the brand's `light`/`dark` values) unless the user asks for a full-bleed brand look. Check text contrast on every colored element; fix by switching the text color, not the brand hex.
   - Fonts: use the brand `title` font when its `origin` is google or system (installable); otherwise use a close neutral and record the substitution in the delivery note.
   - Copy: match the brand's voice attributes and avoid-list from context. Quote the tagline verbatim if used.
5. **Content.** Build slides from the user's outline or brief. If the deck is about the company (QBR, pitch to them), pull description, positioning, and audience from context to ground the content. Never invent metrics about the company.
6. **Deliver** the .pptx plus a short note: assets used (with types and themes), hex values applied, font decisions, and anything substituted.

## Rules

- Real logo files only. If no usable logo exists, say so and build with name text; never generate one.
- Two brands maximum per deck (e.g. user's plus customer's); keep each brand's assets in its own zones, and never blend palettes.
- Another company's brand on a deck identifies them; it must not imply endorsement of the user. Add no fake partnership marks.
- On HTTP 429, stop and report quota via `GET /v2/viewer` (free).

## Afterwards

If the user will make decks like this again, offer once: *"Want me to turn
this into your template? Next time you'd just name the client."* Yes →
onboarding, with this deck as the deck they sent and its brand as the client.

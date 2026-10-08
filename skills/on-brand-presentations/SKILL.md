---
name: on-brand-presentations
description: Design a new presentation in a company's verified brand from the Brandfetch MCP — real logos, exact colors, fonts and brand voice. Use this for any deck that is not a sales deck to a client — internal decks (all-hands, strategy, roadmap, training), investor and board decks, conference talks, partner or co-branded decks, or a deck about the user's own company — "make a deck for the all-hands", "a deck for our board", "an on-brand deck about our Q3 roadmap", "a presentation in Acme's brand". Also used when personalized-sales-decks hands over a client deck to design new because the user has no template. For a sales, pitch, proposal or QBR deck for a client or prospect, use personalized-sales-decks; for a slide of many customer logos, use logo-wall.
license: MIT
---

# On-brand presentations

Designs a new deck in a brand's verified identity: its real logos, colors,
fonts and voice. Brand data comes from the **Brandfetch MCP**; content comes
from the conversation. Never from model memory.

**Which skill.** A deck **for a client or prospect** (sales, pitch, proposal,
QBR) belongs to `personalized-sales-decks`, which fills the user's own
template. Hand it over unless that skill sent the deck here because the user
has no template and wants one designed. Everything else is this skill.

## Requirements

- The Brandfetch MCP connected (preferred), or `BRANDFETCH_API_KEY` for HTTP
  with `Authorization: Bearer <key>`; and `cdn.brandfetch.io` on the network
  allowlist. `references/setup.md` has the traps.
- A way to produce the deck: the environment's pptx tooling or skill. Follow
  that tooling's own guidance for construction; this skill governs the
  branding inputs. If there is none, don't hand-write OOXML; tell the user:
  *"I can't produce a .pptx here: no presentation tooling (python-pptx,
  pptxgenjs or a pptx skill) is available. Enable one and ask again."*
- Cost: 2 credits per brand (`GET /v2/brands/{domain}` +
  `GET /v2/context/{domain}`).

## The one rule that matters most

**Never invent a fact about a company.** Every number, claim and name about
a brand comes from the `get_brand_data` or `get_brand_context` response, or
from something the user said in this conversation. If it is in neither, ask,
or leave it out and say so. A plausible figure recalled from training data is
the failure this rule exists for: it is wrong, and nobody proofreading
catches it.

## Procedure

1. **Resolve the brand.** Domain from the user, or `brand_search` /
   `GET /v2/search/{name}` for a name; confirm ambiguous matches. Note whose brand the deck is in: the user's own
   company (most internal and investor decks) or another company's. A client
   deck handed over by `personalized-sales-decks` is in the user's own brand,
   with the client's logo on the cover; ask for the user's company if it is
   unknown.
2. **Fetch the kit.** `get_brand_data` and `get_brand_context` in parallel.
3. **Get real asset bytes.** Download the asset `src` URLs from the
   `get_brand_data` response verbatim. Their `?c=` parameter is a
   credential, so never edit or rebuild one. If the CDN cannot be reached,
   read the MCP's `bf://asset/{domain}/{type}` resources instead. URLs from
   `build_logo_urls` are display-only and cannot be downloaded. Prefer the
   largest PNG; use SVG only if your tooling rasterises it (`cairosvg`),
   since older Office handles embedded SVG poorly. Pick `theme` variants to
   match slide backgrounds: a dark slide takes the `light` logo.
4. **Apply the brand.**
   - Logos: title slide (type `logo`), small footer or corner mark on
     content slides (type `icon` or `symbol`). If the brand lacks a type the
     design needs, ask which of the types it has to use instead ("Stripe has
     no symbol. Should I use its icon or its logo there?"). Composite the
     files; never redraw, recolor, stretch, or crop.
   - Colors: `accent` (the brand's primary color), then `brand` colors, for
     accents, headings, and charts. Backgrounds stay neutral (the brand's
     `light`/`dark` values) unless the user asks for a full-bleed brand
     look. Check text contrast on every colored element; fix by switching
     the text color, not the brand hex.
   - Fonts: use the brand `title` font when its `origin` is google or system
     (installable); otherwise use a close neutral and record the
     substitution in the delivery note.
   - Copy: match the brand's voice attributes and avoid-list from context.
     Quote the tagline verbatim if used.
5. **Content.** Build slides from the user's outline or brief. When the deck
   is about a company, ground it in the description, positioning and
   audience from context. Never invent metrics.
6. **Render and look.** Render the deck to images (LibreOffice → PDF →
   images) and check every slide: contrast, logo legibility, overflow. A
   valid file is not the same as a good-looking one.
7. **Deliver** the .pptx plus a short note: assets used (with types and
   themes), hex values applied, font decisions, and anything substituted.

## Rules

- Real logo files only. If no usable logo exists, say so and build with name
  text; never generate one.
- Two brands maximum per deck (e.g. user's plus partner's); keep each
  brand's assets in its own zones, and never blend palettes.
- Another company's brand on a deck identifies them; it must not imply
  endorsement of the user. Add no fake partnership marks.
- On HTTP 429, stop and report quota via `GET /v2/viewer` (free).

## Afterwards

A client deck handed over by `personalized-sales-decks`: if the user will
make decks like this again, offer once: *"Want me to turn this into your
template? Next time you'd just name the client."* Yes → onboarding in
`personalized-sales-decks`, with this deck as the deck they sent and its
client as the client.

## Files

- `references/setup.md` — MCP, network allowlist, and the 403 trap.

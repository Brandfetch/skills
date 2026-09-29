# Changelog

All notable changes to the Brandfetch plugin for Claude. Versions follow
[Semantic Versioning](https://semver.org). The `version` in
`.claude-plugin/plugin.json`, the marketplace entry and the git tag must all
match for a release.

## Unreleased

- `logo-wall` rebuilt: PPTX, PDF, HTML and PNG output from one layout, with
  no dependency beyond Pillow. Reads saved `get_brand` responses and picks
  variants itself; monochrome prefers official one-colour variants and
  otherwise flattens with a luminance threshold that keeps knockouts (and
  flags marks whose colour carries their drawing, like Mastercard's
  overlap). Sizing trims each logo to its ink, equalises visual area and
  weight, and centres on the ink centroid. Fixed: black logos passing the
  mono check on dark walls, SVG-only logos silently dropped, 100%-coloured
  logos reported as download failures.
- `logo-wall` always asks for the output format (PPTX, PDF, HTML, PNG), even
  when the request implies one.

- `pitch-deck-generator`: onboarding. Attach a deck you already sent a client
  and say *set up my template* — `scripts/instrument_template.py` proposes
  every per-deck value (`--detect`, matched against the client's Brandfetch
  data) and writes the template (`--apply`). The skill's template is only
  replaced after an explicit yes.
- New `{bf:logo}` and `{bf:symbol}` tokens: the builder picks the light or
  dark variant per slot by measuring which is visible on the colour under it,
  and leaves the slot visibly empty when neither is. The theme-chain tokens
  (`{bf:lightOrDarkLogo}` …) still work but can no longer place an invisible
  mark. Onboarding proposes the new tokens.
- New `{bf:darkOrLightLogo}` token: a dark wordmark for light slides.
- SVG-only and WebP-only brand assets are rasterised automatically (cairosvg,
  rsvg-convert or ImageMagick); SVG-only pictures in Pitch exports are read.
- Fixed: a paragraph with a soft line break had every line after the break
  duplicated by the run merger.
- `scan_template.py` now reports tokens inside tables.
- `pitch-deck-generator` asks before the first deck whether to use the
  sample template or onboard the user's own, and also triggers on "make a
  sales deck". An attached template is filled directly; an attached client
  deck is onboarded first.
- Onboarding no longer overwrites the skill's template, so plugin updates
  can't lose it. It ends with a choice: **your own skill** —
  `scripts/package_skill.py` packages a renamed copy with the template built
  in (a zip for claude.ai, or `~/.claude/skills/` in Claude Code) — or a
  **template file** to attach per deck.

## 1.0.0 - 2026-09-15

First release.

- Bundles the hosted Brandfetch MCP server (`https://mcp.brandfetch.io/mcp`,
  OAuth or `bf1.` token) as `.mcp.json`.
- `pitch-deck-generator` skill: fill your own PPTX template with a client's
  brand assets and your deal values.
- `logo-wall` skill: a "trusted by" slide from a list of brands, logos
  pixel-verified monochrome.

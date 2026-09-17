# Changelog

All notable changes to the Brandfetch plugin for Claude. Versions follow
[Semantic Versioning](https://semver.org). The `version` in
`.claude-plugin/plugin.json`, the marketplace entry and the git tag must all
match for a release.

## 1.0.0 - 2026-09-15

First release.

- Bundles the hosted Brandfetch MCP server (`https://mcp.brandfetch.io/mcp`,
  OAuth or `bf1.` token) as `.mcp.json`.
- `pitch-deck-generator` skill: fill your own PPTX template with a client's
  brand assets and your deal values.
- `logo-wall` skill: a "trusted by" slide from a list of brands, logos
  pixel-verified monochrome.

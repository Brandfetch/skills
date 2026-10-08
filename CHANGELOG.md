# Changelog

All notable changes to the Brandfetch plugin for Claude. Versions follow
[Semantic Versioning](https://semver.org). The `version` in
`.claude-plugin/plugin.json`, the marketplace entry and the git tag must all
match for a release.

## 1.0.0 - Unreleased

First release.

- Bundles the hosted Brandfetch MCP server (`https://mcp.brandfetch.io/mcp`,
  OAuth or `bf1.` token) as `.mcp.json`.
- Skills: `on-brand-presentations`, `logo-wall`.
- `on-brand-presentations` onboarding packages the user's template as a
  template-only skill (`package_template.py`, template format 1) that the
  plugin fills, instead of a copy of the whole skill, so template users keep
  receiving plugin updates.

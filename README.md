# Brandfetch skills

The official [Brandfetch](https://brandfetch.com) plugin for Claude Code and
claude.ai. It bundles the **Brandfetch MCP server** (search 50M+ brands and
get their logos, colors, fonts, company data and brand context) with
**skills** that turn that data into finished work.

## Skills

**Deliverables**

- [`on-brand-presentations`](skills/on-brand-presentations/): a deck for a company, from your own template or designed from scratch in their brand.
- [`logo-wall`](skills/logo-wall/): a "trusted by" logo wall as PPTX, PDF, HTML or PNG.
- [`prospect-branded-pages`](skills/prospect-branded-pages/): landing pages and one-pagers themed in a prospect's brand.
- [`ai-brand-kit`](skills/ai-brand-kit/): a verified brand kit for image, video or copy models.
- [`pre-call-brand-brief`](skills/pre-call-brand-brief/): a one-page brief on a company before a meeting.
- [`brand-check`](skills/brand-check/): an audit of a deck, PDF or page against a brand's verified assets.

**Data enrichment**

- [`crm-brand-enrichment`](skills/crm-brand-enrichment/): logos and firmographics for CRM records, CSVs and sheets.
- [`transaction-enrichment-test`](skills/transaction-enrichment-test/): merchants behind card and bank descriptors, with a match-rate report.
- [`ticker-logos`](skills/ticker-logos/): logos and brand data from tickers, ISINs and crypto symbols.

**Code for your product**

- [`company-autocomplete`](skills/company-autocomplete/): a company-name typeahead for signup forms.
- [`onboarding-brand-prefill`](skills/onboarding-brand-prefill/): a branded first screen from a new user's work email.
- [`real-logos-migration`](skills/real-logos-migration/): replace favicons and Clearbit logo URLs with the Logo API.

Skills load automatically when a request calls for them, or by name as
`/brandfetch:<skill>`. Each skill's folder documents how it works.

## Install

### Claude Code

```
/plugin marketplace add Brandfetch/skills
/plugin install brandfetch@brandfetch
```

The first time a Brandfetch tool is used, Claude Code opens the Brandfetch
sign-in in your browser. You can instead connect with a `bf1.` MCP token from
**Keys and MCP** in the [Brandfetch dashboard](https://developers.brandfetch.com);
see the [MCP docs](https://docs.brandfetch.com/mcp/overview).

### claude.ai

**As a plugin (recommended).** It installs the MCP server and every skill at
once. Go to **Connectors → Plugins → Add marketplace** and paste
`https://github.com/Brandfetch/skills`. Once Brandfetch is listed in the
plugin marketplace, you can also find it there. Team and Enterprise admins can
distribute the plugin to the whole organization from
**Organization settings → Plugins**.

**Skill by skill.** Add **Brandfetch** from the connector directory
(**Settings → Connectors**), then upload the skills you want as zips of their
folders in **Settings → Capabilities → Skills**.

### Claude API

Upload a skill folder with the [Skills API](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
(`/v1/skills`). Skills need the code execution tool.

## Requirements

- A Brandfetch account. The free plan works.
- **`cdn.brandfetch.io`** on your environment's network allowlist, for
  skills that download logo files. Allowlist changes apply to new
  conversations only.
- Some code and enrichment skills call the Brandfetch API directly. They ask
  for an API key or client ID from the [developer dashboard](https://developers.brandfetch.com).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- MCP server source: https://github.com/Brandfetch/brandfetch-mcp-server
- MCP documentation: https://docs.brandfetch.com/mcp/overview
- Brandfetch API: https://developers.brandfetch.com

## License

MIT. See [LICENSE](LICENSE).

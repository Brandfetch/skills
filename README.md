# Brandfetch skills

The official [Brandfetch](https://brandfetch.com) plugin for Claude Code and
claude.ai. It bundles the **Brandfetch MCP server** (search 50M+ brands and
get their logos, colors, fonts, company data and brand context) with
**skills** that turn that data into finished work.

## Skills

- [`personalized-sales-decks`](skills/personalized-sales-decks/): a sales deck, proposal or QBR for a client, filled from your own template with their logos and company data.
- [`on-brand-presentations`](skills/on-brand-presentations/): a new presentation designed in a brand, for internal, investor or event decks.
- [`logo-wall`](skills/logo-wall/): a "trusted by" logo wall as PPTX, PDF, HTML or PNG.

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

**As a plugin (recommended).** It installs the MCP server and all the skills at
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
- **`cdn.brandfetch.io`** on your environment's network allowlist: every
  skill downloads logo files from it. Allowlist changes apply to new
  conversations only.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- MCP server source: https://github.com/Brandfetch/brandfetch-mcp-server
- MCP documentation: https://docs.brandfetch.com/mcp/overview
- Brandfetch API: https://developers.brandfetch.com

## License

MIT. See [LICENSE](LICENSE).

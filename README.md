# Brandfetch Claude Skills

Agent skills that turn the [Brandfetch MCP](https://mcp.brandfetch.io/mcp) into
finished, on-brand deliverables. Give Claude a company, get back real editable
PowerPoint — with the client's actual logos, verified pixel by pixel.

| Skill | One line | Try |
|---|---|---|
| [`pitch-deck-generator`](pitch-deck-generator/) | Fill **your own** PPTX template with a client's brand data and your deal values | *"Make a proposal deck for stripe.com"* |
| [`logo-wall`](logo-wall/) | A "trusted by" slide from a list of brands — grid derived, logos verified monochrome | *"Logo wall of our 12 customers, white on dark"* |

![Deck cover example](docs/deck-example.jpg)
![Logo wall example](docs/wall-example.jpg)

## How it works

Both skills follow the same contract:

- **Two token namespaces.** `{bf:*}` tokens resolve automatically from the
  Brandfetch API (`{bf:name}`, `{bf:lightOrDarkLogo}`, …). Every other
  `{token}` is yours — named after whatever your business sells, supplied at
  build time, **never guessed**.
- **Never invent a fact.** Every value on a slide comes from the API or from
  the conversation. Missing data stays visibly missing.
- **Verify pixels, not metadata.** Logo theme labels don't guarantee a
  monochrome mark; the skills check the actual pixels and hunt alternate
  variants when they fail.
- **The output is real PowerPoint.** Every logo is a separate, movable
  picture. No rasterised slides.

## Requirements

1. **Brandfetch MCP** connected — `https://mcp.brandfetch.io/mcp`
   ([get an API key](https://developers.brandfetch.com)).
2. **`cdn.brandfetch.io`** on your environment's network allowlist (logo
   downloads). Note: allowlist changes apply to **new** conversations only.
3. Python with `Pillow`; `python-pptx` for the logo wall.

Each skill's `references/setup.md` covers the setup traps in detail —
including the three different failures that all look like a 403.

## Install

Each skill is a self-contained folder. Copy the one(s) you want:

**Claude Code** — into your project (`.claude/skills/pitch-deck-generator/`)
or globally (`~/.claude/skills/pitch-deck-generator/`). Docs:
https://code.claude.com/docs/en/skills

```bash
git clone https://github.com/brandfetch/claude-skills.git
cp -r claude-skills/pitch-deck-generator ~/.claude/skills/
```

**claude.ai** — zip the skill folder and add it as a custom skill in your
settings (Capabilities → Skills).

**Claude API** — upload via the [Skills API](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
(`/v1/skills`); requires the code execution tool.

## Make it yours

The deck skill is built to be forked. The bundled `assets/template.pptx` is a
reference showing where tokens go — replace it with **your** deck:

1. Type tokens as visible text in your own template
   (`{bf:name}`, `{bf:lightOrDarkLogo}`, `{your_own_fields}`).
2. `python3 scripts/scan_template.py your-template.pptx` — fix every warning.
3. Build. Nothing about your template's layout is hardcoded.

Full guide: [`pitch-deck-generator/references/template-guide.md`](pitch-deck-generator/references/template-guide.md).

## Repository layout

```
pitch-deck-generator/   SKILL.md · assets/template.pptx · scripts/ · references/
logo-wall/              SKILL.md · scripts/ · references/
docs/                   example renders
```

Every rule in `references/rules.md` is recorded with the real regression that
produced it — these skills were built by shipping wrong slides first so you
don't have to.

## License

MIT. Built by [Brandfetch](https://brandfetch.com) — the brand data API these
skills are powered by.

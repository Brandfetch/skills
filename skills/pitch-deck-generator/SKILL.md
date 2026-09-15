---
name: pitch-deck-generator
description: Generate a client-personalized pitch or proposal deck from a PowerPoint template, pulling the client's logos, colors, description, and firmographics from the Brandfetch MCP. Use this whenever the user wants to build, generate, personalize, or fill a deck, proposal, or pitch for a named company — "make a deck for Stripe", "personalize my template for this prospect", "generate the Acme proposal" — or wants to instrument or check a PPTX template with {bf:*} or {custom} tokens.
license: MIT
---

# Pitch deck generator

Fills an instrumented PowerPoint template with a client's real brand assets
and your own deal-specific values. Brand data comes from the **Brandfetch
MCP**; everything else comes from the conversation. Never from anywhere else.

Ships with a working 4-slide reference template (`assets/template.pptx`).
Replace it with your own — `references/template-guide.md` shows how, and
`scripts/scan_template.py` verifies you did it right.

**Requirements:** the Brandfetch MCP connected, and `cdn.brandfetch.io` on
your network allowlist. First run? Read `references/setup.md` — two of its
steps fail in non-obvious ways if skipped.

## Two namespaces, one rule

| Token | Resolved by | Example |
|---|---|---|
| `{bf:*}` | This skill, from the Brandfetch API | `{bf:name}`, `{bf:lightOrDarkLogo}` |
| everything else | You, at build time | `{fee}`, `{start_date}`, `{anything}` |

The skill has no vocabulary of its own: name your tokens after whatever your
business sells. Unfilled tokens stay visible as `{token}` in the output — a
gap reads as an obvious blank, never a silent omission.

## The one rule that matters most

**Never invent a customer fact or a deal value.**

Every value on a slide comes from a field in the `get_brand` response or from
something the user actually said in this conversation. There is no third
source. This rule exists because it was broken: an early build shipped
"33,000+ employees" recalled from training data when the API said `10001`.
Plausible, wrong, and invisible to a proofreader — plausibility is what makes
this failure dangerous. A fabricated fee or scope is worse: it is a commercial
commitment nobody made.

If a value is not in the conversation, **ask**. If a brand field is missing
from the API, leave the slot empty and say so. An obvious gap is recoverable;
a confident wrong number is not.

## Workflow

### 1. Get the brand data

Call the Brandfetch MCP `get_brand` with the client's domain and save the full
response **verbatim** to `brand.json` — the scripts read it from disk, so
nothing is transcribed by hand.

Preview what will resolve, and show it to the user:

```bash
python3 scripts/bf_fields.py brand.json
```

### 2. Collect the user-token values

Scan the template to see which non-`bf:` tokens it expects:

```bash
python3 scripts/scan_template.py template.pptx
```

Read the conversation first — in a real deal thread most values have already
been mentioned, and asking for something the user just told you is worse than
useless. Extract what is there, then ask only for the gaps. Write them to
`values.json`, keyed by token:

```json
{
  "{engagement_type}": "Operating model review",
  "{fee}": "CHF 180,000"
}
```

Omitting a value is fine and often correct — an early-stage deck may
genuinely not have a fee yet. The token stays visible in the output.

### 3. Confirm before generating

Show the resolved brand fields and the user values together, and wait. This
is the cheapest place to catch a wrong employee band or a misheard fee.

### 4. Build

**Prefer an uploaded template.** The bundled one is a reference; if the user
has uploaded a `.pptx` in this conversation, that one is authoritative. Say
which you used.

```bash
python3 scripts/build_deck.py template.pptx brand.json out.pptx --values=values.json
```

Options: `--slides=1,3` fills only those slides (useful when iterating).

The builder prints every slot it filled, every frame it resized, and any
tokens left unfilled. Read that output — it is the build's own audit trail.
Dashed placeholder outlines are stripped from every slot it fills; unfilled
slots keep theirs, so gaps stay visibly marked.

### 5. Verify

```bash
python3 <pptx-skill>/scripts/office/validate.py out.pptx --original template.pptx
```

Then render it and actually look at it (LibreOffice → PDF → images). Schema
passing does not mean the slides look right. If the template's fonts are not
installed, the preview's text fit is approximate — see
`references/setup.md` before "fixing" an overflow that does not exist.

## When the template changes

Re-run the scanner after any edit or re-export — token names drift, and a
retyped token can end up split across text runs. The builder merges split
runs before substituting, but the scanner will tell you what it found and
what it will do, before you build.

## Files

- `assets/template.pptx` — 4-slide reference template. Every `{bf:*}` token,
  both fit modes, both background themes, and the user-token namespace. Its
  speaker notes document each slide. Replace it with yours.
- `scripts/build_deck.py` — the builder.
- `scripts/bf_fields.py` — `{bf:*}` field mapping and asset selection. Run
  standalone to preview resolved values.
- `scripts/scan_template.py` — template linter. Run after instrumenting.
- `references/template-guide.md` — how to instrument your own template.
- `references/rules.md` — the geometry and data rules, each with the
  regression that produced it.
- `references/setup.md` — MCP, network allowlist, fonts, dependencies.
- `references/troubleshooting.md` — symptom → cause table.

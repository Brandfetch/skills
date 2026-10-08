---
name: on-brand-presentations
description: Make a sales, pitch, proposal or QBR deck for a company in verified brand data from the Brandfetch MCP — real logos, exact colors, fonts, description and firmographics. Two ways — fill the user's own PowerPoint template (or a deck they already sent a client, turned into one), or design a new deck from scratch in the brand. Use this whenever the user wants to build, generate, personalize or fill a deck, presentation or proposal — "make a sales deck", "make a deck for Stripe", "an on-brand presentation for Acme", "personalize my template for this prospect", "set up my template", "turn this deck into a template" — or to instrument or check a PPTX template with {bf:*} or {custom} tokens. For a slide of many customer logos, use logo-wall instead.
license: MIT
---

# On-brand presentations

Makes a deck for a company from its real brand assets: either by filling
the user's PowerPoint template with the client's brand and the deal's
values, or by designing a new deck in the brand. Brand data comes from the **Brandfetch
MCP**; everything else comes from the conversation. Never from anywhere else.

Building a deck **never** writes to this skill or its template: the output
is always a new file. Work in the user's own folder or a scratch folder,
**never inside this skill's folder** — the user's decks, `brand.json` and
previews must not end up next to the skill's files. Commands below are
written `<skill-dir>/scripts/…`: substitute this skill's folder path and run
them from the working folder.

## Which path

Decide before anything else:

1. **A `.pptx` is attached.** Scan it (`<skill-dir>/scripts/scan_template.py`):
   - **Tokens, no warnings** — the user's template. Go to *Every deck* with it.
   - **"No tokens found"** — a deck they sent a client. Go to *Onboarding*;
     if they already named the new client ("make the same for Stripe"), use
     that client for the test-fill (onboarding step 4), so onboarding ends
     with their deck.
   - **"PARTLY FILLED DECK"** — a deck built for a client from a template.
     Never fill it: that client's logo would stay in every deck. Ask for the
     original template, or onboard this deck.
   - Keynote, PDF or Google Slides: ask for a `.pptx` export.
2. **Nothing attached, and a template skill is installed.** Onboarding
   packages the user's template as a small skill of its own — no logic, just
   `assets/template.pptx` — whose description reads *"…deck template for the
   Brandfetch on-brand-presentations skill"*. If one is in your skill list,
   load it, and use its template for *Every deck*; ask for the company if
   they have not named it. Several → ask which. Its SKILL.md states a
   `brandfetch-template-format`; this skill reads format **1**. A higher
   number means the plugin is out of date — tell the user to update it.
3. **Nothing attached, no template skill.** Ask once, in one message, both
   what you still need: *"Who is the deck for (company or domain)? And do
   you have a deck to start from — your template, or one you've already
   sent a client? Attach it, or I'll design a new deck."* Skip the first
   question if they named the company. Attached → step 1. New design →
   `references/from-scratch.md`.

**Requirements:** the Brandfetch MCP connected, and `cdn.brandfetch.io` on
the network allowlist. `references/setup.md` has the traps.

## Two namespaces, one rule

| Token | Resolved by | Example |
|---|---|---|
| `{bf:*}` | This skill, from the Brandfetch API | `{bf:name}`, `{bf:logo}` |
| everything else | You, at build time | `{fee}`, `{start_date}`, `{anything}` |

The skill has no vocabulary of its own: name your tokens after whatever your
business sells. Unfilled tokens stay visible as `{token}` in the output — a
gap reads as an obvious blank, never a silent omission.

## The one rule that matters most

**Never invent a customer fact or a deal value.**

Every value on a slide comes from a field in the `get_brand_data` response or from
something the user actually said in this conversation. There is no third
source. This rule exists because it was broken: an early build shipped
"33,000+ employees" recalled from training data when the API said `10001`.
Plausible, wrong, and invisible to a proofreader — plausibility is what makes
this failure dangerous. A fabricated fee or scope is worse: it is a commercial
commitment nobody made.

If a value is not in the conversation, **ask**. If a brand field is missing
from the API, leave the slot empty and say so. An obvious gap is recoverable;
a confident wrong number is not.

## Onboarding: set up your template

When the user wants to set up or change their template ("set up my
template", "use my deck as the template"), or attached a deck they sent a
client, read `references/onboarding.md` and follow it. It turns that deck
into a template and packages it as the user's template skill.

## Every deck: build for a client

### 1. Get the brand data

Call the Brandfetch MCP `get_brand_data` with the client's domain and save the full
response **verbatim** to `brand.json` — the scripts read it from disk, so
nothing is transcribed by hand.

Preview what will resolve, and show it to the user:

```bash
python3 <skill-dir>/scripts/bf_fields.py brand.json
```

### 2. Collect the user-token values

Scan the template to see which non-`bf:` tokens it expects:

```bash
python3 <skill-dir>/scripts/scan_template.py template.pptx
```

Read the conversation first — in a real deal thread most values have already
been mentioned, and asking for something the user just told you is worse than
useless. Extract what is there, then ask only for the gaps. Write them to
`values.json`, keyed by token:

```json
{
  "{engagement_type}": "Operating model review",
  "{fee}": "USD 180,000"
}
```

Omitting a value is fine and often correct — an early-stage deck may
genuinely not have a fee yet. The token stays visible in the output.

### 3. Confirm before generating

Show the resolved brand fields and the user values together, and wait. This
is the cheapest place to catch a wrong employee band or a misheard fee.

**A missing logo type is a question, not a gap.** When `bf_fields.py` (or the
build) prints `ASK THE USER`, the brand lacks a logo type the template uses.
Ask in the same message, offering only the types it has:

> Stripe has no symbol. Should I use its icon or its logo there?

Then build with their answer, `--use=symbol:icon` or `--use=symbol:logo`.
Never pick one yourself, and never leave the slot empty without asking.

### 4. Build

**Use the template chosen in *Which path*.** Say which you used. A
template skill's file is read-only: build from its path, never edit it.

```bash
python3 <skill-dir>/scripts/build_deck.py template.pptx brand.json out.pptx --values=values.json
```

Options: `--slides=1,3` fills only those slides (useful when iterating);
`--strip-notes` empties the speaker notes; `--use=symbol:icon` fills a
missing type with another, as the user chose in step 3.

**Speaker notes ship to the client.** The builder fills tokens in them like
on the slides, and resets the file's title and properties. Unfilled tokens
in notes are listed under `UNFILLED TOKENS` (`ppt/notesSlides/…`): those
notes are template instructions, not speaker notes. Rebuild with
`--strip-notes`, or ask the user what the notes should say.

For `{bf:logo}` and `{bf:symbol}` slots the builder picks the light or dark
variant per slot by measuring which is visible on the colour underneath, and
leaves the slot empty (dashed box kept) when neither is — relay any
`LEFT EMPTY` line to the user. Never override it by hand-placing a variant.

The builder prints every slot it filled, every frame it resized, and any
tokens left unfilled. Read that output — it is the build's own audit trail.
Dashed placeholder outlines are stripped from every slot it fills; unfilled
slots keep theirs, so gaps stay visibly marked.

The output is a new file. The template and the skill are never written to.

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

- `references/onboarding.md` — turn a deck the user sent a client into
  their template, and package it as their template skill.
- `references/from-scratch.md` — the new-design path: brand kit in, deck
  out, through the environment's pptx tooling.
- `scripts/instrument_template.py` — onboarding: `--detect` proposes,
  `--apply` writes the template.
- `scripts/package_template.py` — onboarding: the user's template skill,
  their template and nothing else; this skill does the building.
- `scripts/build_deck.py` — the builder.
- `scripts/bf_fields.py` — `{bf:*}` field mapping and asset selection. Run
  standalone to preview resolved values.
- `scripts/scan_template.py` — template linter. Run after instrumenting.
- `references/template-guide.md` — how templates work: onboarding first,
  hand-instrumenting as the advanced path.
- `references/rules.md` — the geometry and data rules, each with the
  regression that produced it.
- `references/setup.md` — MCP, network allowlist, fonts, dependencies.
- `references/troubleshooting.md` — symptom → cause table.

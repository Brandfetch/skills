---
name: pitch-deck-generator
description: Generate a client-personalized pitch or proposal deck from a PowerPoint template, pulling the client's logos, colors, description, and firmographics from the Brandfetch MCP. Use this whenever the user wants to build, generate, personalize, or fill a deck, proposal, or pitch for a named company — "make a deck for Stripe", "personalize my template for this prospect", "generate the Acme proposal". Also use it to onboard a template from a real deck — "set up my template", "use my deck as the template", "turn this deck into a template", or an uploaded .pptx they already sent a client — and to instrument or check a PPTX template with {bf:*} or {custom} tokens.
license: MIT
---

# Pitch deck generator

Fills an instrumented PowerPoint template with a client's real brand assets
and your own deal-specific values. Brand data comes from the **Brandfetch
MCP**; everything else comes from the conversation. Never from anywhere else.

Two modes, and they never mix:

- **Onboarding** — once. The user uploads a deck they already sent to a
  real client; you turn it into their template through conversation. Nobody
  types a token. This is the only mode that may change the skill.
- **Every deck** — from then on. Fill the template for a new client.
  Building a deck **never** modifies the skill or its template.

Ships with a 4-slide reference template (`assets/template.pptx`) so the
every-deck flow works on day one. If the user has not onboarded their own
deck yet, offer it once: *"Attach a deck you've sent a client and say 'set
up my template'."*

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

## Onboarding: set up your template

Triggered by "set up my template", "use my deck as the template", or an
uploaded `.pptx` the user sent a client. The deck stays in this conversation
and never goes to Brandfetch — only the client's domain does.

### 1. Check the plumbing quietly

Onboarding needs both halves of the pipeline, and step 3 exercises them
anyway: the `get_brand` call for the deck's client tests the MCP, and
`--brand` downloads its logos from the CDN. Say nothing about setup unless
one of them fails — then follow `references/setup.md` (a 403 has three
different causes; read the response body before blaming the allowlist).

### 2. Get a real deck

Ask the user to upload a deck **they have already sent to a real client** —
not a blank master. A sent deck contains exactly what varies per client, in
exactly the places it varies; that is what makes this work.

Ask who it was for, if they have not said. That one answer is worth more
than every heuristic in the script.

### 3. Detect, then propose

Call `get_brand` for **that** client's domain and save the response verbatim
to `brand.json`. Then:

```bash
python3 scripts/instrument_template.py --detect deck.pptx \
    --brand=brand.json --extract=previews/ > proposal.json
```

With `--brand`, detection is matching, not guessing: the client's exact name,
description and firmographics are found as strings, and their logos are
matched against the deck's pictures by file and by image. Without it
(the user does not know or will not say), it falls back to repeated proper
nouns and logo-shaped pictures, and pre-selects nothing it is unsure of.

**Look at the previews** (`previews/slideN-picID.png`) before proposing any
picture — a thumbnail settles "their logo or ours?" instantly.

Present the proposal as one list the user can scan: each value, where it
appears, and what it becomes. Group it:

- **From Brandfetch** — `{bf:*}` entries (name, logos, description…).
  High-confidence matches are pre-selected.
- **Per deal** — dates, amounts, labelled values (`Sector: Retail`).
  Dates and amounts are pre-selected with names taken from their labels
  (`Kick-off` → `{kick_off_date}`); offer better names if the user has them.
- **Unsure** — `token: null` entries: repeated names (the previous client?
  the user's own company?), unmatched pictures. Ask; never guess.

Also say what detection **cannot** know: free text that was written for that
client ("Operating model review", a scope paragraph). Ask the user what else
changes per deck. Their answer becomes an entry:
`{"find": "<exact slide text>", "token": "{engagement_type}"}`.

Report `elsewhere` too: the old client's name in speaker notes or the file
title ships inside every future deck unless it is cleaned.

### 4. Apply, check, test-fill, show

Write the agreed mapping — the proposal with `token` set, changed or nulled
per entry — and apply it:

```bash
python3 scripts/instrument_template.py --apply deck.pptx mapping.json template.pptx
python3 scripts/scan_template.py template.pptx
```

`--apply` turns text spans into tokens and client pictures into dashed slot
shapes where the logo was (padded so the builder's inset lands the next
client's logo at the same size), lifts grouped pictures out of their group,
and deletes the old client's image files from the package. Read its output:
anything under **STILL MENTIONS THE PREVIOUS CLIENT** needs a decision.

Then test-fill with a **different** real brand — ideally one with a
monochrome mark, which exposes theme mistakes a coloured logo hides — run
the every-deck build, render it, and **show the user both**: the template
with its dashed slots, and the test deck.

### 5. Iterate

Go back to step 3 or 4 until the user says the template is final. Rerun
`--apply` from the **original** deck with an updated mapping rather than
instrumenting an instrumented file.

### 6. Ask before touching the skill

Ask, word for word:

> Do you want me to update your pitch-deck skill with this template?

Wait for a clear yes. Anything else — silence, "looks good", a new request —
is not a yes. Then:

- **Claude Code:** copy `template.pptx` over `assets/template.pptx` in this
  skill's folder. If that folder is inside `~/.claude/plugins/`, a plugin
  update will restore the bundled template — say so, and keep a copy
  alongside the user's work.
- **claude.ai:** the skill folder is read-only. Copy the whole skill folder
  somewhere writable, replace `assets/template.pptx`, zip the folder
  (`pitch-deck-generator/` at the root, no `__pycache__`), and return the
  zip. Tell the user to upload it in **Customize → Skills**, and that it
  **replaces** the current version.

Never update the skill without that yes, and never as a side effect of
building a deck.

## Every deck: build for a client

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
  "{fee}": "USD 180,000"
}
```

Omitting a value is fine and often correct — an early-stage deck may
genuinely not have a fee yet. The token stays visible in the output.

### 3. Confirm before generating

Show the resolved brand fields and the user values together, and wait. This
is the cheapest place to catch a wrong employee band or a misheard fee.

### 4. Build

**Prefer an uploaded template.** The skill's `assets/template.pptx` is the
default; if the user has uploaded an instrumented `.pptx` in this
conversation, that one is authoritative. Say which you used.

```bash
python3 scripts/build_deck.py template.pptx brand.json out.pptx --values=values.json
```

Options: `--slides=1,3` fills only those slides (useful when iterating).

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

- `assets/template.pptx` — the template every build uses. Ships as a 4-slide
  reference (every `{bf:*}` token, both fit modes, both background themes,
  the user-token namespace; its speaker notes document each slide) until
  onboarding replaces it.
- `scripts/instrument_template.py` — onboarding: `--detect` proposes,
  `--apply` writes the template.
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

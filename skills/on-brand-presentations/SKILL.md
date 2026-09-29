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
is always a new file.

<!-- brandfetch:choose-template -->
## Which path

Decide before anything else:

1. **A `.pptx` is attached.** Scan it (`scripts/scan_template.py`).
   - **It has tokens** — the user's template. Go to *Every deck* with it.
   - **No tokens** — a deck they sent a client. Go to *Onboarding*; if they
     already named the new client ("make the same for Stripe"), use that
     client for the test-fill in step 4, so onboarding ends with their deck.
2. **Nothing attached.** Ask once in this conversation: *"Do you have a
   deck to start from — your template, or one you've already sent a client?
   Attach it. Or I can design a new deck in <brand>'s brand."*
   Attached → step 1. New design → `references/from-scratch.md`.
<!-- /brandfetch:choose-template -->

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

<!-- brandfetch:onboarding -->
## Onboarding: set up your template

Onboarding hands the user a file — a template, or their own copy of this
skill — and never edits this folder.

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

### 6. Hand it over

Ask:

> Your template is ready. How do you want to use it?
> 1. **Make it your own skill** (recommended if you'll make decks often) —
>    I'll package a copy of this skill with your template built in. You
>    install it once, and "make a deck for Stripe" just works.
> 2. **Keep using the Brandfetch skill** — save this template file and
>    attach it whenever you want a deck; I'll fill it.

Either way, return the template file itself, named after the user's company
(`Acme template.pptx`) — it is theirs to keep and share.

**Own skill.** Name it after the user's **own** company, not the deck's
client (`acme-presentations`); ask if you do not know it. Then:

```bash
python3 scripts/package_skill.py template.pptx --name acme-presentations \
    --company "Acme" --out <dir> --zip
```

- **Claude Code:** `--out ~/.claude/skills` installs it for the next
  session; return the zip too, for teammates or claude.ai.
- **claude.ai:** `--out` a writable folder; return the zip. They upload it
  in **Settings → Capabilities → Skills**.

Tell them, once, in plain words:

- Turn off the Brandfetch on-brand-presentations skill once theirs is
  installed — both answer "make a deck".
- Their copy does not receive Brandfetch updates. To pick up a new release,
  onboard again with it and repackage.
- On Team or Enterprise, an admin can give the zip to the whole
  organization.

**Brandfetch skill.** Nothing else to do. Next time: attach the template
and say who the deck is for.
<!-- /brandfetch:onboarding -->

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

**Use the template chosen in *Which path*.** Say which you used.

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

- `references/from-scratch.md` — the new-design path: brand kit in, deck
  out, through the environment's pptx tooling.
- `scripts/instrument_template.py` — onboarding: `--detect` proposes,
  `--apply` writes the template.
- `scripts/package_skill.py` — onboarding: the user's own renamed copy of
  this skill, with their template built in.
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

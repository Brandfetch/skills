# Onboarding: set up your template

Turns a deck the user sent a client into their template, then hands it
over as a file and as their **template skill**. It never edits this skill's
folder. `<skill-dir>` below is this skill's folder, as in `SKILL.md`.

Triggered by "set up my template", "use my deck as the template", or an
uploaded `.pptx` the user sent a client. The deck stays in this conversation
and never goes to Brandfetch — only the client's domain does.

### 1. Check the plumbing quietly

Onboarding needs both halves of the pipeline, and step 3 exercises them
anyway: the `get_brand_data` call for the deck's client tests the MCP, and
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

Call `get_brand_data` for **that** client's domain and save the response verbatim
to `brand.json`. Then:

```bash
python3 <skill-dir>/scripts/instrument_template.py --detect deck.pptx \
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
python3 <skill-dir>/scripts/instrument_template.py --apply deck.pptx mapping.json template.pptx
python3 <skill-dir>/scripts/scan_template.py template.pptx
```

`--apply` turns text spans into tokens and client pictures into dashed slot
shapes where the logo was (padded so the builder's inset lands the next
client's logo at the same size), lifts grouped pictures out of their group,
and deletes the old client's image files from the package. Read its output:
anything under **STILL MENTIONS THE PREVIOUS CLIENT** needs a decision.

Then test-fill with a **different** real brand — ideally one with a
monochrome mark, which exposes theme mistakes a coloured logo hides — run
the build in `SKILL.md` (*Every deck*), render it, and **show the user
both**: the template with its dashed slots, and the test deck.

### 5. Iterate

Go back to step 3 or 4 until the user says the template is final. Rerun
`--apply` from the **original** deck with an updated mapping rather than
instrumenting an instrumented file.

### 6. Hand it over

Don't ask how they want to use it: deliver **both** in the same turn, as
files they can download:

- **the template**, named after the user's company (`Acme template.pptx`):
  theirs to keep, share and attach to any chat;
- **their template skill**, `acme-deck-template.skill`. Once installed,
  "make a deck for Stripe" uses the template without an attachment.

Name the skill after the user's **own** company, not the deck's client
(`acme-deck-template`). If you don't know the company yet, ask together with
the step 5 review, so the handover never waits on a question.

```bash
python3 <skill-dir>/scripts/package_template.py template.pptx \
    --name acme-deck-template --company "Acme" \
    --out <work-dir> --skill-file <outputs>/acme-deck-template.skill
```

It holds the template and a short SKILL.md that points back to this skill:
no scripts, no rules, nothing that goes stale. `--out` is a working folder
for the unpacked skill. Keep it out of the outputs, or the user gets its
loose files as downloads too.

- **claude.ai / Claude Desktop:** write both files to the outputs folder
  (`/mnt/user-data/outputs/`) and present them. The `.skill` file comes with
  a button to save it to their skills. Otherwise they upload it in
  **Settings → Capabilities → Skills**.
- **Claude Code:** pass `--out ~/.claude/skills` so it is installed for the
  next session, and still write the `.skill` file for teammates and
  claude.ai.

Then tell them, briefly:

- They can install the skill or just keep the `.pptx` and attach it
  whenever they want a deck. Both work.
- Keep the Brandfetch plugin installed. The template skill only holds the
  file; the Brandfetch skill builds the deck, so they keep getting its
  updates.
- To change the template, onboard the new deck and package it again under
  the same name (`package_template.py … --replace`), then reinstall.
- On Team or Enterprise, an admin can share the `.skill` file with the
  whole organization, so everyone's decks start from the same template.

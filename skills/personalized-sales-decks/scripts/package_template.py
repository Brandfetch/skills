#!/usr/bin/env python3
"""
Package the user's template as a skill of its own: the "install it as your
template" end of onboarding.

    python3 package_template.py template.pptx --name acme-deck-template --company "Acme"
    python3 package_template.py template.pptx --name acme-deck-template --company "Acme" \
        --out ~/.claude/skills            # Claude Code: installed for the next session
    python3 package_template.py template.pptx --name acme-deck-template --company "Acme" \
        --out work --skill-file /mnt/user-data/outputs/acme-deck-template.skill
                                          # claude.ai: a .skill file the user saves to their skills

The template skill holds data, not logic: the template and a short SKILL.md
that hands every deck to the Brandfetch personalized-sales-decks skill. The
building stays in the plugin, so its fixes and new {bf:*} fields reach every
user's template without repackaging. This skill's folder is only read, never
written.
"""
import argparse
import json
import os
import re
import shutil
import sys
import zipfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = os.path.basename(SKILL_DIR)  # personalized-sales-decks

# Bump when a template built for this version would no longer build on an
# older plugin. SKILL.md's *Which path* names the formats it reads.
TEMPLATE_FORMAT = 1

# The opening of the description is what personalized-sales-decks looks for in
# the skill list (SKILL.md, *Which path*); change both together.
DESCRIPTION = (
    "{company}'s deck template for the Brandfetch {builder} skill. Use it whenever "
    "the user wants a sales, pitch, proposal or QBR deck for a client — \"make a "
    "deck for Stripe\", \"the {company} proposal for Notion\", \"personalize our deck "
    "for this prospect\" — together with {builder}, which fills this template with "
    "the client's logos, colors and company data."
)

SKILL_MD = """---
name: {name}
description: {description}
metadata:
  brandfetch-template-format: {format}
---

# {company} deck template

{company}'s PowerPoint template: `<skill-dir>/assets/template.pptx`. This
skill holds the template only; the Brandfetch **{builder}** skill builds
every deck from it.

When the user wants a deck, load the `{builder}` skill and follow it, with
this file as the template. It is read-only: build from its path, and write
every deck to the working folder, never into this one.

If `{builder}` is not available, tell the user this template needs the
Brandfetch plugin for Claude (https://github.com/Brandfetch/skills) with
the Brandfetch MCP connected, and stop — do not fill the template by hand.

To change the template, onboard the new deck with `{builder}` and package
it again under this name.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("template", help="the instrumented template.pptx from onboarding")
    ap.add_argument("--name", required=True, help="skill name, e.g. acme-deck-template")
    ap.add_argument("--company", required=True, help="the user's own company, e.g. Acme")
    ap.add_argument("--out", default=".", help="folder to create <name>/ in (default: .)")
    ap.add_argument("--skill-file", metavar="PATH",
                    help="also write the skill as one installable .skill file (a zip) at PATH")
    ap.add_argument("--replace", action="store_true",
                    help="replace an existing <out>/<name>/ (a new version of the template)")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.name) or len(a.name) > 64:
        sys.exit("--name must be lowercase letters, digits and hyphens, at most 64 characters")
    if a.name == BUILDER:
        sys.exit(f"--name must differ from '{BUILDER}': that is the Brandfetch skill itself")
    company = " ".join(a.company.split())
    if not company:
        sys.exit("--company must not be empty")
    if a.skill_file and not a.skill_file.endswith(".skill"):
        sys.exit("--skill-file must end in .skill: that is what claude.ai offers to install")
    if not zipfile.is_zipfile(a.template):
        sys.exit(f"{a.template} is not a .pptx")

    out = os.path.expanduser(a.out)
    dest = os.path.join(out, a.name)
    if os.path.exists(dest):
        if not a.replace:
            sys.exit(f"{dest} already exists — pick another --name, or pass --replace")
        if not os.path.isfile(os.path.join(dest, "SKILL.md")):
            sys.exit(f"{dest} exists but is not a skill folder; refusing to replace it")
        shutil.rmtree(dest)

    os.makedirs(os.path.join(dest, "assets"))
    shutil.copyfile(a.template, os.path.join(dest, "assets", "template.pptx"))
    # a JSON string is valid YAML, so quotes or colons in a company name
    # cannot break the frontmatter
    desc = json.dumps(DESCRIPTION.format(company=company, builder=BUILDER), ensure_ascii=False)
    with open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD.format(name=a.name, description=desc, format=TEMPLATE_FORMAT,
                                company=company, builder=BUILDER))
    print(f"skill:  {dest}")

    if a.skill_file:
        zpath = os.path.expanduser(a.skill_file)
        os.makedirs(os.path.dirname(os.path.abspath(zpath)), exist_ok=True)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(dest):
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, out))
        print(f"file:   {zpath}")


if __name__ == "__main__":
    main()

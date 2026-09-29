#!/usr/bin/env python3
"""
Package a copy of this skill with the user's template built in, under the
user's own name — the "make it your own skill" end of onboarding.

    python3 package_skill.py template.pptx --name acme-presentations --company "Acme"
    python3 package_skill.py template.pptx --name acme-presentations --company "Acme" \
        --out ~/.claude/skills            # Claude Code: installed for the next session
    python3 package_skill.py template.pptx --name acme-presentations --company "Acme" \
        --out outputs --zip               # claude.ai: a zip to upload in Skills settings

The copy is renamed so it never competes with the Brandfetch skill for "make
a deck", its description names the company, and its SKILL.md drops the
onboarding and template-choice sections: it always fills its own template.
This skill's folder is only read, never written.
"""
import argparse
import glob
import os
import re
import shutil
import sys
import zipfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# only the skill itself is copied: a deck, a brand.json or a preview left in
# the folder by an earlier run must never ship inside the user's zip
KEEP = ("SKILL.md", "scripts/*.py", "references/*.md")

DESCRIPTION = (
    "Generate a pitch or proposal deck for a client from {company}'s own "
    "PowerPoint template, pulling the client's logos, colors, description, and "
    "firmographics from the Brandfetch MCP. Use this whenever the user wants to build, "
    "generate, personalize, or fill a sales deck, proposal, or pitch — \"make a sales "
    "deck\", \"make a deck for Stripe\", \"generate the Acme proposal\", \"personalize our "
    "deck for this prospect\"."
)

TEMPLATE_SECTION = """## Template

This skill fills {company}'s template, `assets/template.pptx`, for every deck.
A template `.pptx` attached in the conversation overrides it for that deck;
a new design only when the user asks for one (`references/from-scratch.md`).
To change the template, onboard the new deck with the Brandfetch
on-brand-presentations skill and package it again under this name.
"""


def section(text, key, replacement):
    pat = re.compile(r"<!-- brandfetch:%s -->.*?<!-- /brandfetch:%s -->\n?" % (key, key), re.S)
    if not pat.search(text):
        sys.exit(f"SKILL.md has no brandfetch:{key} section — is this the Brandfetch skill?")
    return pat.sub(lambda _: replacement, text)


def rewrite_skill_md(text, name, company):
    text = re.sub(r"^name: .*$", f"name: {name}", text, count=1, flags=re.M)
    desc = DESCRIPTION.format(company=company)
    text = re.sub(r"^description: .*$", lambda _: f"description: {desc}", text, count=1, flags=re.M)
    text = re.sub(r"^# Pitch deck generator$", f"# {company} pitch deck", text, count=1, flags=re.M)
    text = section(text, "choose-template", TEMPLATE_SECTION.format(company=company))
    text = section(text, "onboarding", "")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("template", help="the instrumented template.pptx from onboarding")
    ap.add_argument("--name", required=True, help="skill name, e.g. acme-presentations")
    ap.add_argument("--company", required=True, help="the user's own company, e.g. Acme")
    ap.add_argument("--out", default=".", help="folder to create <name>/ in (default: .)")
    ap.add_argument("--zip", action="store_true", help="also write <out>/<name>.zip")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.name) or len(a.name) > 64:
        sys.exit("--name must be lowercase letters, digits and hyphens, at most 64 characters")
    if a.name == os.path.basename(SKILL_DIR):
        sys.exit(f"--name must differ from '{a.name}', or both skills answer \"make a deck\"")
    if not zipfile.is_zipfile(a.template):
        sys.exit(f"{a.template} is not a .pptx")

    out = os.path.expanduser(a.out)
    dest = os.path.join(out, a.name)
    if os.path.exists(dest):
        sys.exit(f"{dest} already exists — pick another --name, or remove it first")

    for pattern in KEEP:
        for src in sorted(glob.glob(os.path.join(SKILL_DIR, pattern))):
            rel = os.path.relpath(src, SKILL_DIR)
            os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
            shutil.copyfile(src, os.path.join(dest, rel))
    os.makedirs(os.path.join(dest, "assets"), exist_ok=True)
    shutil.copyfile(a.template, os.path.join(dest, "assets", "template.pptx"))
    md = os.path.join(dest, "SKILL.md")
    with open(md, encoding="utf-8") as f:
        text = rewrite_skill_md(f.read(), a.name, a.company)
    with open(md, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"skill:  {dest}")

    if a.zip:
        zpath = os.path.join(out, a.name + ".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(dest):
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, out))
        print(f"zip:    {zpath}")


if __name__ == "__main__":
    main()

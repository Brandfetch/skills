# Contributing

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with `name`, `description` and
   `license: MIT` in the frontmatter. The `description` is what makes Claude
   pick the skill: say what it produces and list the phrasings that should
   trigger it.
2. Keep `SKILL.md` short; put long material in `references/` and code in
   `scripts/`. Bundled files go in `assets/`.
3. Every skill must get its brand data from the Brandfetch MCP tools
   (`get_brand`, `brand_search`, …) and must never invent brand facts.
4. Test locally: `claude --plugin-dir . ` then `/brandfetch:<skill-name>`.
5. Run `claude plugin validate --strict .` — it must print `Validation passed`.
   CI runs the same check, plus a frontmatter check, on every pull request.
6. Add a line to `CHANGELOG.md`.

## Releasing

1. Bump `version` in **both** `.claude-plugin/plugin.json` and the plugin
   entry in `.claude-plugin/marketplace.json`, and add a `CHANGELOG.md` entry.
   Users only receive updates when the version changes.
2. `claude plugin validate --strict .`
3. Commit, tag `vX.Y.Z`, push tag and `main`.

The community and official directories pin the plugin to a commit SHA and
re-sync automatically from `main`; no resubmission is needed for updates.

## Plugin name

`brandfetch` is an immutable slug once published. Change `displayName`, never
`name`.

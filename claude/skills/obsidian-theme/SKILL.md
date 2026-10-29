---
name: obsidian-theme
description: Restyle or tweak the repo-owned Obsidian theme "Ayu Ink" in ~/dotfiles/obsidian/ (theme.css, manifest.json), verified by a headless preview against the installed app's own app.css plus a contrast and typography checker, then applied to the open vault. Use for «тема Obsidian», «поправь цвет / шрифт / ширину строки в Obsidian», a screenshot of Obsidian with a complaint, the theme not applying. Not for note content (obsidian-markdown) or vault operations (obsidian-cli).
---

# Obsidian theme (Ayu Ink)

Files: `obsidian/Ayu Ink/theme.css` and `manifest.json` (folder name must equal
the manifest `name`), `obsidian/fixture.html` (static workspace mimic),
`obsidian/preview.py`, `obsidian/check.py`. Design, palette (D5), typography
(D6), measure schema (D3): `plans/obsidian-ayu-ink-theme.md`. `$S` below is the
session scratchpad.

## Facts (Obsidian 1.14)

- The app's CSS lives in `~/Library/Application Support/obsidian/obsidian-X.Y.Z.asar`
  (the `.app` installer is older); `preview.py` extracts `app.css` from it. Look
  up a variable's default in that extracted `app.css`, not in web docs.
- The `obsidian` CLI fails ("installer is out of date") until a current DMG is
  installed: no eval or screenshots through it.
- Obsidian sets `--font-text-size` and the font overrides inline on `body`:
  never set `--font-text-size`, size things as multiples of it.
- app.css overrides some vars on `.mod-macos` (`--tab-radius`,
  `--scrollbar-thumb-bg`), which a `body` rule loses to: colors and shape go in
  `.theme-dark`, typography in `body`.
- Nav item weight goes through `--nav-item-weight`, `-hover`, `-active`: a plain
  `font-weight` rule loses to `.tree-item-self.is-active`.
- Since 1.13 colors mix in OKLCH and the `-rgb` vars are deprecated: set full
  colors (`--color-blue: #59C2FF`); callouts use them.
- The open vault is the one with `"open": true` in
  `~/Library/Application Support/obsidian/obsidian.json`. Its Minimal Settings
  plugin stays on and sets body classes plus `--font-ui-small` inline (harmless);
  the `zoom3` render emulates its base font size and window zoom.

## Loop

1. Edit `theme.css`: no `!important`, no `url()`, colors only under `.theme-dark`
   (light mode keeps Obsidian's defaults).
2. A new text color: compute its contrast with `apca()` / `wcag()` from
   `check.py` against `#0B0E14` first. Floors: body 80, headings 85, links and
   code 75, muted UI 60, faint 35. A change that moves an expectation updates
   `check.py` and the plan's D5/D6 in the same commit.
3. Gate:
   ```bash
   python3 obsidian/preview.py --out "$S/prev" && python3 obsidian/check.py "$S/prev/computed-1440.json" "$S/prev/computed-zoom3.json"
   ```
   Must end with `OK <n> checks`; Read `shot-1440.png` and `shot-zoom3.png`.
   Python edits also: `uvx ruff check obsidian/ && uvx ruff format --check obsidian/ && uvx mypy --strict obsidian/preview.py obsidian/check.py`.
4. Live: the vault's `.obsidian/themes/Ayu Ink` is a link into the repo, so the
   file is live. Whether the running app hot-reloads `theme.css` is unverified:
   confirm with `screencapture -x` (one file per display) before saying it
   applied. Switching a vault to the theme (verified): link it (install.sh
   Obsidian block or `ln -sfn`), `osascript -e 'quit app "Obsidian"'` and wait
   for `pgrep -x Obsidian` to go empty (it rewrites `appearance.json` on quit),
   back up `appearance.json` to `~/.claude/backups/`, `jq '.cssTheme = "Ayu Ink"'`,
   keep the file mode 644, `open -a Obsidian`.
5. Commit by explicit pathspec: `fix(obsidian): ...` / `feat(obsidian): ...`.

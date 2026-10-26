---
name: zen-browser
description: Restyle or tweak Zen Browser (Firefox-based) through the repo-owned theme in ~/dotfiles/zen/ (user.js prefs, chrome/userChrome.css), verified by a headless preview with computed-style checks. Use for "тема / цвет / шрифт в Zen", "кастомизируй zen", "эта штука в Zen мешает", a screenshot of Zen with a complaint, about:config prefs, Zen shortcuts or mods. Not for styling websites.
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Zen Browser theme

Verified on Zen 1.23.4b (Firefox 158), macOS. Design and spike facts:
`~/dotfiles/plans/zen-terminal-theme.md`.

## Layout

- `~/dotfiles/zen/user.js` -> `<profile>/user.js`,
  `~/dotfiles/zen/chrome/userChrome.css` -> `<profile>/chrome/userChrome.css`.
  `<profile>` is `~/Library/Application Support/zen/` + the first `Default=`
  line of `installs.ini`. `install.sh` makes the links (Zen block), or by hand.
- Palette: `--term-*` tokens in `:root` at the top of `userChrome.css` (Ayu,
  taken from Ghostty). Change colors there; no hex anywhere else.
- `zen/preview.py`: headless Zen on a throwaway profile via Marionette, next to
  the running browser. Writes `<out>.png`, `<out>.urlbar.png` (floating URL bar
  open) and `<out>.json` (computed styles per probe name, prefs, user sheets).
- `zen/checks.jq`: expected computed values, `FAIL <name>` per miss.

## Change loop

1. Edit `userChrome.css` / `user.js` (dotfiles rules apply: a value swap goes
   straight to edit, anything larger through `/feature`).
2. `S=$(mktemp -d); uv run ~/dotfiles/zen/preview.py --out "$S/zen.png" && jq -e -r -f ~/dotfiles/zen/checks.jq "$S/zen.json"`,
   then Read both PNGs before saying it looks right.
3. A changed color or size: update its line in `checks.jq` (computed form,
   `rgb(r, g, b)`); a newly styled element without a probe: add one to
   `preview.py` and a check.
4. Apply: the user quits Zen (Cmd+Q) and reopens it. Never quit or kill their
   Zen yourself; never edit `prefs.js`, `zen-*.json`, `*.jsonlz4` while it runs.

## Gotchas

- `userChrome.css` is a user-origin sheet: its `!important` beats Zen's author
  `!important` and inline styles, so specificity only matters inside the file.
- The Space gradient rewrites inline vars on `#zen-browser-background` and
  `#zen-toolbar-background` on every switch. Override
  `--zen-main-browser-background` (also `-old`, `-toolbar`, `-toolbar-old`) on
  those two elements; on `:root` it does not reach them. `--zen-primary-color`
  and `--toolbox-textcolor`: set on `:root, zen-workspace`.
- A symlinked `userContent.css` is ignored on macOS (content process sandbox);
  linked `userChrome.css` and `user.js` work. Web-page styling needs a copied
  file or a pref.
- `font-family` on `:root` misses `panel, menupopup, tooltip, panel-list`.
  macOS context menus and panel popover backgrounds are native: fonts only.
- Deleting a `user.js` line does not reset the pref: write its default (the
  trailing comments in `user.js` list them) or reset it in about:config.
- Prefs worth knowing: `zen.theme.accent-color`, `zen.theme.border-radius`
  (`-1` platform, `0` flat), `zen.theme.content-element-separation` (max 12),
  `zen.widget.macos.window-vibrancy` (restart). No pref turns the gradient off.
- Headless: size the window with `set_window_rect` (`MOZ_HEADLESS_WIDTH` is
  ignored), translucent layers render over white, popups are not in window
  screenshots (probe their computed styles), the open URL bar must be probed in
  the same Marionette session.

## Finding a selector

No Browser Toolbox needed: copy `zen/preview.py` into a mktemp dir, and after
its screenshot run, in chrome context,
`document.elementsFromPoint(x, y).map(e => e.localName + (e.id ? "#" + e.id : "") + "." + [...e.classList].join("."))`
at the pixel taken from the PNG, plus `getComputedStyle` of the hit. Zen's own
rules and pref defaults: sparse clone at the version tag,
`git clone --depth 1 --filter=blob:none --sparse --branch <version> https://github.com/zen-browser/desktop`,
`git sparse-checkout set prefs src/zen` (`prefs/zen/*.yaml`, `src/zen/**/*.css`).
Selectors move between Zen releases: after an update, a red `checks.jq` names
what broke.

## Other layers

- Shortcuts: Settings > Keyboard Shortcuts; `zen-keyboard-shortcuts.json` only
  with Zen closed, change only `key`/`keycode`/`modifiers` of existing entries.
- Zen Mods (`zen-themes.json`, `chrome/zen-themes/<id>/`) and JS (Sine,
  fx-autoconfig) are not used here; JS runs privileged, only with explicit consent.

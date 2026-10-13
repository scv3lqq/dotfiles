# Anki terminal theme add-on

## Goal

Anki 26.9.2 on macOS looks like Ghostty + tmux: Ayu dark palette, JetBrainsMono
Nerd Font, flat surfaces, tmux-style status bar at the bottom of the reviewer.

Non-goals: no changes to `collection.anki2`, no changes to AnkiConnect, no
changes to the user's note types, no new Anki features (scheduling, stats).

## Current behavior

Anki 26.9.2 (`/Applications/Anki.app`, PyQt6 6.11, profile theme `2` = forced
dark) runs stock styling. One add-on installed: AnkiConnect (`2055492159`),
which touches no CSS, so no theme conflict. `addons21` has no ReColor, Onigiri
or background add-on.

Sources of truth for the palette in this repo:

- `ghostty/ghostty/config`: `theme = Ayu`, with explicit `background`,
  `foreground`, `cursor-color` overrides; font `JetBrainsMono Nerd Font` at 15.
- `/Applications/Ghostty.app/Contents/Resources/ghostty/themes/Ayu`: the
  resolved 16-color palette, selection and cursor-text colors.
- `.tmux.conf` + `~/.tmux/plugins/tmux-dotbar/dotbar.tmux`: status bar colors
  (only `@tmux-dotbar-bg` is overridden; the rest are plugin defaults).
- `nvim/lua/plugins/theme.lua`: `ayu-dark`, consistent, used as tiebreaker only.

Only a dark theme is defined, so the same palette is used in both Anki modes.

## Target behavior

### Palette (single source: CSS variables in `web/theme.css`)

| token | value | origin |
| --- | --- | --- |
| `--bg` | `#0B0E14` | ghostty `background` |
| `--fg` | `#BFBDB6` | ghostty `foreground` |
| `--cursor` | `#E6B450` | ghostty `cursor-color` |
| `--cursor-text` | `#0B0E14` | Ayu `cursor-text` |
| `--sel-bg` | `#409FFF` | Ayu `selection-background` |
| `--sel-fg` | `#0B0E14` | Ayu `selection-foreground` |
| `--black` / `--bright-black` | `#11151C` / `#686868` | palette 0 / 8 |
| `--red` / `--bright-red` | `#EA6C73` / `#F07178` | palette 1 / 9 |
| `--green` / `--bright-green` | `#7FD962` / `#AAD94C` | palette 2 / 10 |
| `--yellow` / `--bright-yellow` | `#F9AF4F` / `#FFB454` | palette 3 / 11 |
| `--blue` / `--bright-blue` | `#53BDFA` / `#59C2FF` | palette 4 / 12 |
| `--magenta` / `--bright-magenta` | `#CDA1FA` / `#D2A6FF` | palette 5 / 13 |
| `--cyan` / `--bright-cyan` | `#90E1C6` / `#95E6CB` | palette 6 / 14 |
| `--white` / `--bright-white` | `#C7C7C7` / `#FFFFFF` | palette 7 / 15 |

tmux-dotbar derived tokens:

| token | value | origin |
| --- | --- | --- |
| `--bar-bg` | `#0B0E14` | `@tmux-dotbar-bg` |
| `--bar-fg` | `#475266` | dotbar `fg` (inactive window) |
| `--bar-fg-current` | `#BFBDB6` | dotbar `fg_current` |
| `--bar-fg-session` | `#565B66` | dotbar `fg_session` |
| `--bar-accent` | `#95E6CB` | dotbar `fg_prefix` |
| `--bar-zoom` | `#39BAE6` | dotbar zoom-icon color |
| separator | `" • "` | `window-status-separator` |
| edges | `` / `` | dotbar rounded edge glyphs |

Font: `JetBrainsMono Nerd Font` (installed in `~/Library/Fonts`, Nerd Font, so
powerline glyphs ``/`` are available), base size 15px, configurable.

### Answer buttons

Again `--bright-red`, Hard `--bright-yellow`, Good `--bright-green`,
Easy `--bright-blue`. Flat: 1px border in the accent color, transparent
background, accent text; hover/active inverts to accent background + `--bg`
text. No radius, no shadow, no gradient.

### Reviewer status bar (tmux-style, bottom, above the answer bar)

- Left: `  <deck name>  ` in `--bar-accent` on `--bar-bg`, mirroring
  dotbar's session component (dotbar shows plain ` #S ` when the prefix is not
  pressed; here the deck is always shown, accent-colored).
- Center (`justify: absolute-centre` equivalent): `0:new 12 • 1:learn 3 •
  2:review 45`. Active queue in `--bar-fg-current`, others in `--bar-fg`,
  separator ` • ` in `--bar-fg`. Counts come from `mw.col.sched.counts()`;
  active queue from the current card's queue/type.
- Right: `HH:MM` + date in `--bar-fg-session`, ticking every 20s.

## Relevant files

Read-only (sources of truth, must not change):

- `ghostty/ghostty/config`, `.tmux.conf`, `nvim/lua/plugins/theme.lua`
- `/Applications/Ghostty.app/Contents/Resources/ghostty/themes/Ayu`
- `~/.tmux/plugins/tmux-dotbar/dotbar.tmux`

New (all under `anki/`, nothing else in the repo is touched):

- `anki/terminal_theme/__init__.py` - hook registration, web exports, config.
- `anki/terminal_theme/manifest.json` - package name/version.
- `anki/terminal_theme/config.json` - user toggles.
- `anki/terminal_theme/config.md` - text shown in Tools > Add-ons > Config.
- `anki/terminal_theme/web/theme.css` - palette + all screen styling.
- `anki/terminal_theme/web/statusbar.js` - status bar DOM + clock + counts.
- `anki/terminal_theme/web/qt.qss` - optional native-window stylesheet.
- `anki/terminal_theme/README.md` - structure, how to repalette.
- `anki/cards/cards.css`, `anki/cards/front.html`, `anki/cards/back.html`,
  `anki/cards/README.md` - card template deliverable, AnkiDroid-safe.

## Constraints

- `aqt.gui_hooks` only. No monkey-patching of Anki internals. Hooks confirmed
  present in this build: `webview_will_set_content`,
  `card_review_webview_did_init`, `reviewer_did_show_question`,
  `reviewer_did_show_answer`, `state_did_change`, `theme_did_change`,
  `deck_browser_did_render`, `overview_did_refresh`.
- CSS/JS served via `mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js)")`
  and appended to `web_content.css` / `web_content.js` as
  `/_addons/<pkg>/web/...`. No inline `<style>` blobs.
- Palette defined once, in `:root` of `theme.css`. `statusbar.js` reads
  `var(--...)` only; no hardcoded hex in JS.
- Never write into `collection.anki2`, `prefs21.db`, or `addons21/2055492159`.
- Repo layout: source stays in `anki/terminal_theme/`; `addons21` gets a
  symlink. `install.sh` and the Stow packages are not modified in this task
  (the symlink is created once, manually, after confirmation).
- `anki/cards/` files are given as text to paste; note types are not modified.
- Do not commit unrelated dirty files (`CLAUDE.md`, `ghostty/ghostty/config`,
  `install.sh`, `topgrade/`, `zsh/.zprofile`, other `plans/*.md`).

## Implementation steps

- **T0** (implementer): create `anki/terminal_theme/` skeleton:
  `manifest.json`, `config.json`, `config.md`, empty `web/`. Config keys:
  `status_bar` (bool, true), `blinking_cursor` (bool, true), `font_size`
  (int, 15), `font_family` (str, "JetBrainsMono Nerd Font"), `qt_styling`
  (bool, false). Gate: `jq empty` on both JSON files.
- **T1** (implementer): `web/theme.css` - `:root` palette block, reset
  (no radius/shadow/gradient), font stack, then sections: top toolbar, deck
  browser, deck overview, reviewer card area, bottom answer bar, answer
  buttons. Handles `.nightMode`/`.night_mode` and plain body alike.
- **T2** (implementer): `web/statusbar.js` - builds the bar into the reviewer
  bottom webview, exposes `window.terminalTheme.update({deck, counts, active})`,
  runs the clock. No network, no polling of Anki state from JS.
- **T3** (implementer): `anki/terminal_theme/__init__.py` - config read,
  `setWebExports`, `webview_will_set_content` dispatch by context class
  (`TopToolbar`, `DeckBrowser`, `Overview`, `Reviewer`, `ReviewerBottomBar`),
  CSS variable overrides for `font_size`/`font_family`/`blinking_cursor`
  injected as a small `head` style, and reviewer hooks pushing deck name +
  `mw.col.sched.counts()` + active queue into `statusbar.js`.
  Gate: `python3 -m py_compile`.
- **T4** (implementer): optional QSS - `web/qt.qss` + `main_window_did_init`
  applying `mw.app.setStyleSheet` only when `qt_styling` is true.
- **T5** (implementer): `anki/cards/cards.css` + `front.html` + `back.html`:
  `❯ ` prompt before the question, blinking block cursor, answer rendered
  as command output. Guards for `.nightMode`, `.night_mode` and AnkiDroid
  (no add-on, no CSS variables from the add-on: `cards.css` carries its own
  `:root` copy of the palette). `anki/cards/README.md` says where to paste.
- **T6** (orchestrator): `anki/terminal_theme/README.md`.
- **T7** (orchestrator, needs confirmation): symlink
  `~/Library/Application Support/Anki2/addons21/terminal_theme` ->
  `~/dotfiles/anki/terminal_theme`.
- **T8** (orchestrator, needs confirmation the first time): restart Anki,
  `screencapture -x`, inspect, fix, repeat.

## Tests / verification

- `python3 -m py_compile anki/terminal_theme/__init__.py`
- `find anki -name '*.json' -print0 | xargs -0 -n1 jq empty`
- `osascript -e 'quit app "Anki"'` then `open -a Anki`, then
  `screencapture -x /tmp/.../anki.png` and visual review of deck browser,
  overview and reviewer.
- Anki's own error console (Tools > Debug Console) must stay clean.

## Edge cases

- macOS only in practice (Anki path, `screencapture`); nothing in this task
  runs on Linux, `install.sh` is untouched, so Linux is unaffected.
- Font missing on another machine: CSS falls back to
  `JetBrainsMono Nerd Font, JetBrains Mono, Menlo, monospace`; powerline edge
  glyphs degrade to a blank box, so the status bar keeps its background and
  loses only the rounded caps.
- Anki theme switched to light: `theme_did_change` re-applies; the single dark
  palette is used either way, as only a dark Ghostty theme exists.
- Reviewer opened with an empty deck or from the browser preview: counts hook
  guards on `mw.col` and `mw.reviewer.card` being present.
- AnkiDroid: cards work with no add-on; status bar and toolbar styling are
  desktop-only by design.
- Anki update: hooks are public API, so a version bump should not break it;
  worst case the web export path changes and CSS silently stops loading.

## Rollback / migration notes

- Remove the symlink in `addons21` and restart Anki. Nothing else in `$HOME`
  is modified, no Anki data is written.
- Card templates are opt-in: the user clones a note type and pastes; reverting
  means switching the note back to the original type.
- The repo change is one commit touching only `anki/` and this plan file.

## Acceptance criteria

- [ ] `~/Library/Application Support/Anki2/addons21/terminal_theme` is a
      symlink into this repo, and Anki lists "Terminal Theme" as enabled.
- [ ] Toolbar, deck browser, overview and reviewer use `#0B0E14` background,
      `#BFBDB6` text and JetBrainsMono Nerd Font, with no rounded corners,
      shadows or gradients anywhere.
- [ ] Answer buttons are flat and colored Again/Hard/Good/Easy per the table.
- [ ] The reviewer shows a tmux-style bar: deck on the left, `0:new N •
      1:learn N • 2:review N` centered with the active queue highlighted,
      `HH:MM` and date on the right, in dotbar colors.
- [ ] Tools > Add-ons > Config exposes status bar, blinking cursor, font size
      and Qt styling; each toggle visibly takes effect after a restart.
- [ ] `anki/cards/` renders the prompt, cursor and output style both in Anki
      and, by inspection of the CSS guards, on AnkiDroid.
- [ ] AnkiConnect still works; no file outside `anki/` and `addons21/
      terminal_theme` was written.

## Notes for reviewer

Risk areas: context dispatch in `webview_will_set_content` (class names, not
`isinstance` on private types), the bottom-bar injection timing (the bottom
webview is re-rendered on every answer, so the bar must be rebuilt idempotently),
and CSS specificity against Anki's own stylesheets (prefer targeting Anki's
existing ids/classes over `!important` walls). Expected diff: all-new files
under `anki/`, plus this plan; zero edits to existing repo files.

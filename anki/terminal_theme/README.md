# Terminal Theme (Anki add-on)

Makes Anki look like this machine's terminal: Ghostty with `theme = Ayu` (dark)
and a tmux status bar in the style of `tmux-dotbar`.

Targets Anki 26.9.2 on macOS. Styling goes through `aqt.gui_hooks` and webview
CSS/JS injection only, so no Anki internals are patched.

## Structure

```
anki/terminal_theme/
├── __init__.py        hook registration, config, web exports, status updates
├── manifest.json      add-on package name
├── config.json        user-editable toggles (Tools > Add-ons > Config)
├── config.md          the help text shown next to that config
└── web/
    ├── theme.css      the palette and all screen styling
    ├── statusbar.js   tmux-style bar in the reviewer
    └── qt.qss         optional native-window stylesheet
```

`anki/cards/` next to this folder holds the card templates; they are a separate
deliverable and need no add-on.

### What each hook does

| hook | purpose |
| --- | --- |
| `webview_will_set_content` | appends `theme.css` (and `statusbar.js` in the reviewer) to toolbar, deck browser, overview, reviewer and their bottom bars |
| `reviewer_did_show_question` / `_answer` | pushes deck name, `sched.counts()` and the active queue into the status bar |
| `main_window_did_init` / `theme_did_change` | applies `qt.qss` when `qt_styling` is on |

Contexts are matched by class name (`STYLED_CONTEXTS` in `__init__.py`), so a
renamed private Anki class degrades to "no styling" rather than a crash.

## Install

The source lives in this repo and is symlinked into Anki:

```sh
ln -s ~/dotfiles/anki/terminal_theme \
  ~/Library/Application\ Support/Anki2/addons21/terminal_theme
```

Restart Anki. Edits to the files here are live after the next restart.

To remove: delete the symlink and restart. Nothing else in `$HOME` is touched
and no Anki data is written.

## Changing the palette

Everything is in the `:root` block at the top of `web/theme.css`:

- `--tt-*` tokens are the Ghostty colours (background, foreground, cursor,
  selection, the 16-colour palette).
- `--tt-bar-*` tokens are the tmux-dotbar colours.
- `--tt-again` / `--tt-hard` / `--tt-good` / `--tt-easy` are the answer buttons.
- The second `:root` block remaps Anki's own design tokens (`--canvas`, `--fg`,
  `--state-new`, `--border-radius`, ...) onto those, which is what recolours
  widgets this add-on has no rule for.

Two places intentionally duplicate the palette, because they cannot read CSS
custom properties:

- `QSS_TOKENS` in `__init__.py`, used to fill `web/qt.qss`.
- The `:root` block in `../cards/cards.css`, so cards work on AnkiDroid.

Update those when the palette changes.

## Config

Tools > Add-ons > Terminal Theme > Config. Restart Anki after editing.

| key | default | effect |
| --- | --- | --- |
| `status_bar` | `true` | tmux bar at the bottom of the reviewer |
| `font_family` | `JetBrainsMono Nerd Font` | primary font |
| `font_size` | `15` | base size in px |
| `qt_styling` | `false` | also restyle Browse / Add / Preferences |

`font_family` and `font_size` are injected as CSS variable
overrides into each webview's `<head>`, so they win over `theme.css` defaults.

## Status bar

Mirrors `tmux-dotbar` with `status-justify absolute-centre`:

```
 deck             0:new 12 • 1:learn 3 • 2:review 45            14:32 • 2026-09-21
```

- Left: the current deck in the dotbar session style (powerline caps
  `` / ``, `#95E6CB` on `#0B0E14`).
- Centre: one entry per queue; the queue the current card came from is
  `#BFBDB6`, the others `#475266`, separator ` • ` exactly as
  `window-status-separator`.
- Right: clock and date in `#565B66`, refreshed every 20s.

The powerline caps need a Nerd Font. Without one they render as blank boxes and
only the rounded ends are lost.

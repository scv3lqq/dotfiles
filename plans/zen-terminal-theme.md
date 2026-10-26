# Zen Browser terminal theme

## Goal

Zen Browser on macOS looks like the Ghostty + tmux + starship setup of this
repo: Ayu dark palette, JetBrainsMono Nerd Font, a flat terminal background
instead of the Space gradient, the selected tab marked like a cursor, a muted
shell prompt glyph in the URL bar. Prefs and CSS live in `zen/`, `install.sh`
links them into the active Zen profile, and a headless preview script renders
the theme and checks its computed styles without touching the running browser.

## Current behavior

Zen 1.23.4b (Firefox 158.0.1) runs with stock styling: the active profile has
no `user.js`, no `chrome/userChrome.css`, no Zen Mods (`zen-themes.json` is
`{}`), `zen.view.window.scheme` is already `0` (dark). Nothing about Zen is in
the repo; `README.md` lists Zen under "Install by hand (macOS)".

## Spike findings (Zen 1.23.4b, tag `1.23.4b` = `541ee55` of zen-browser/desktop)

- `userChrome.css` is a user-origin sheet: its `!important` beats Zen's author
  `!important` and inline styles, so specificity only matters between rules of
  this file.
- The Space gradient writes inline custom properties on `#zen-browser-background`
  and `#zen-toolbar-background` (`ZenGradientGenerator.mjs:60-66, 1591-1607,
  1754-1761`) on every Space switch; overriding them on `:root` does not reach
  those elements. Overriding them on the two elements themselves holds across
  Space switches (verified). The grain layer is `.zen-browser-grain`.
- `--zen-primary-color` and `--toolbox-textcolor` are written on
  `documentElement` and on each `zen-workspace` (`ZenSpace.mjs:390-406`).
- Tab corners come from `vertical-tabs.css:392` (`border-radius:
  var(--border-radius-medium) !important`, 14px); the selected tab background
  from `--tab-background-color-selected` set on `zen-workspace`.
- URL bar: the background is `#urlbar > .urlbar-background`; open state
  `#urlbar[breakout-extend]`; result rows `#urlbar-results .urlbarView-row`,
  the selected one forces `color: white !important` on all descendants
  (`zen-omnibox.css:659-664`).
- `font-family` on `:root` reaches tabs, URL bar, result rows, toolbar button
  labels; `panel`, `menupopup`, `tooltip`, `panel-list` use system fonts and
  need their own selector. macOS context menus are native (not styleable).
- The web page frame shadow is on `.browserSidebarContainer`
  (`zen-browser-container.css:11-16`); `browser[type="content"]` paints
  `rgb(32, 32, 32)` behind about:blank and during loads.
- A symlinked `userChrome.css` and a symlinked `user.js` work. A symlinked
  `userContent.css` is NOT applied on macOS (the content process sandbox does
  not follow a link out of the profile), hence no `userContent.css`.
- `zen.theme.border-radius = 0` sets `--zen-border-radius: 0px`
  (`zenThemeModifier.js:112-147`; `-1` is the platform default).
- Headless Zen with Marionette (`--headless --marionette
  -remote-allow-system-access --no-remote --profile <tmp>`, `marionette.port=0`,
  real port in `<profile>/MarionetteActivePort`) runs next to the user's Zen,
  reads chrome computed styles and screenshots the chrome window. Run time
  5-8 s. `MOZ_HEADLESS_WIDTH/HEIGHT` do not size the window: use
  `set_window_rect`. Popups (panels, menus) are not in window screenshots.

## Acceptance criteria

Run from the repo root; `S=$(mktemp -d)` first.

1. Files: `test -f zen/user.js && test -f zen/chrome/userChrome.css && test -f zen/preview.py && test -f zen/checks.jq && test ! -e zen/chrome/userContent.css` exits 0.
2. Preview: `uv run zen/preview.py --out "$S/zen.png"` exits 0 and writes
   `$S/zen.png`, `$S/zen.urlbar.png`, `$S/zen.json`;
   `test -s "$S/zen.png" && test -s "$S/zen.urlbar.png"` exits 0.
3. Theme: `jq -e -r -f zen/checks.jq "$S/zen.json"` exits 0 (prints no
   `FAIL` line, last line `true`).
4. Mutation sanity (the checks really read the CSS): a copy of `zen/` without
   the CSS fails them. `mkdir "$S/z" && cp zen/preview.py zen/user.js "$S/z/" && uv run "$S/z/preview.py" --out "$S/m.png"`,
   then `jq -e -r -f zen/checks.jq "$S/m.json"` exits non-zero and prints
   `FAIL userchrome_loaded`.
5. Install fixture (below) prints no `FAIL` line and exits 0.
6. `bash -n install.sh && /bin/bash -n install.sh` exits 0.
7. Python gates (below) exit 0.
8. Docs: `grep -F 'zen/preview.py' README.md CLAUDE.md` matches in both;
   `grep -F 'zen/user.js' README.md` matches;
   `test "$(wc -l < CLAUDE.md)" -le 199`.
9. No em dash and no home path in new or changed files:
   `! LC_ALL=C grep -n $'\xe2\x80\x94' zen/user.js zen/chrome/userChrome.css zen/preview.py zen/checks.jq install.sh README.md CLAUDE.md plans/zen-terminal-theme.md`
   and `! grep -rnF "$HOME" zen plans/zen-terminal-theme.md` exit 0.
10. The user's running Zen is untouched: in `$S/zen.json`,
    `.meta.foreign_zen_pids_before == .meta.foreign_zen_pids_after` and
    `.meta.own_pid_gone == true` (also asserted inside `zen/checks.jq`).

Branch diff file set (`git diff main...HEAD --stat`): `plans/zen-terminal-theme.md`,
`zen/user.js`, `zen/chrome/userChrome.css`, `zen/preview.py`, `zen/checks.jq`,
`install.sh`, `README.md`, `CLAUDE.md`. Nothing else.

## Gates

Full gates (orchestrator, phase 4):

```bash
S=$(mktemp -d)
bash -n install.sh && /bin/bash -n install.sh
uvx ruff check zen/preview.py && uvx ruff format --check zen/preview.py
uv run --no-project -q --with mypy --with marionette_driver==3.7.1 mypy --strict zen/preview.py
uv run zen/preview.py --out "$S/zen.png" && jq -e -r -f zen/checks.jq "$S/zen.json"
# then the install fixture block below
```

### Install fixture

Runs the Zen block of `install.sh` against throwaway `HOME`s only.

```bash
set -u
repo=$(git rev-parse --show-toplevel)
blk=$(awk '/^# Zen Browser: /{f=1} /^# Personal-data guard/{f=0} f' "$repo/install.sh")
[ -n "$blk" ] || { echo "FAIL block-found"; exit 1; }
printf '%s\n' "$blk" | grep -q 'move it aside first' || { echo "FAIL block-complete"; exit 1; }
run() { HOME="$1" DOTFILES="$repo" OS="$2" /bin/bash -c "$blk" 2>&1; }
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
T=$(mktemp -d)

h="$T/a"; mkdir -p "$h"; out=$(run "$h" Darwin)
check a-msg '[[ "$out" == *"Skipping Zen theme: no Zen profile found"* ]]'
check a-untouched '[ ! -e "$h/Library" ]'

h="$T/b"; z="$h/Library/Application Support/zen"; p="$z/Profiles/ab12cd34.Default (release)"
mkdir -p "$p"
printf '[6ED35B3CA1B5D3AF]\nDefault=Profiles/ab12cd34.Default (release)\nLocked=1\n' > "$z/installs.ini"
out=$(run "$h" Darwin); out2=$(run "$h" Darwin)
check b-userjs '[ "$(readlink "$p/user.js")" = "$repo/zen/user.js" ]'
check b-chrome '[ "$(readlink "$p/chrome/userChrome.css")" = "$repo/zen/chrome/userChrome.css" ]'
check b-no-content '[ ! -e "$p/chrome/userContent.css" ]'
check b-rerun '[[ "$out2" == *"Linking Zen Browser prefs and theme"* && "$out2" != *Skipping* ]]'

h="$T/c"; z="$h/Library/Application Support/zen"; p="$z/Profiles/x.default"
mkdir -p "$p"; printf 'Default=Profiles/x.default\n' > "$z/installs.ini"; echo mine > "$p/user.js"
out=$(run "$h" Darwin)
check c-kept '[ ! -L "$p/user.js" ] && [ "$(cat "$p/user.js")" = mine ]'
check c-msg '[[ "$out" == *"user.js: a regular file, move it aside first"* ]]'
check c-chrome '[ -L "$p/chrome/userChrome.css" ]'

h="$T/d"; z="$h/Library/Application Support/zen"; mkdir -p "$z"
printf 'Default=Profiles/gone.default\n' > "$z/installs.ini"
out=$(run "$h" Darwin)
check d-msg '[[ "$out" == *"Skipping Zen theme: no Zen profile found"* ]]'
check d-no-dir '[ ! -e "$z/Profiles" ]'

h="$T/e"; z="$h/Library/Application Support/zen"; p="$h/elsewhere/prof"
mkdir -p "$z" "$p"; printf 'Default=%s\n' "$p" > "$z/installs.ini"
out=$(run "$h" Darwin)
check e-absolute '[ "$(readlink "$p/user.js")" = "$repo/zen/user.js" ]'

h="$T/f"; mkdir -p "$h"; out=$(run "$h" Linux)
check f-linux-silent '[ -z "$out" ] && [ ! -e "$h/Library" ]'

rm -rf "$T"
exit $fail
```

## Shared definitions

### File layout

| repo path | linked to (macOS) |
| --- | --- |
| `zen/user.js` | `<profile>/user.js` |
| `zen/chrome/userChrome.css` | `<profile>/chrome/userChrome.css` |
| `zen/preview.py` | not linked (dev tool) |
| `zen/checks.jq` | not linked (dev tool) |

`<profile>`: `~/Library/Application Support/zen/` + the value of the first
`Default=` line of `~/Library/Application Support/zen/installs.ini` (relative
to that directory unless it starts with `/`). No profile id ever appears in
the repo.

### Palette (custom properties on `:root` in `zen/chrome/userChrome.css`)

The only place hex colors appear in the CSS. Computed forms are what
`zen/checks.jq` compares against.

| token | value | computed | origin |
| --- | --- | --- | --- |
| `--term-bg` | `#0B0E14` | `rgb(11, 14, 20)` | Ghostty `background`, tmux bar |
| `--term-panel` | `#0F131A` | `rgb(15, 19, 26)` | Ayu dark panel background |
| `--term-line` | `#131721` | `rgb(19, 23, 33)` | Ayu dark current-line highlight |
| `--term-border` | `#6C738033` | `rgba(108, 115, 128, 0.2)` | Ayu indent guide |
| `--term-border-active` | `#6C738080` | `rgba(108, 115, 128, 0.5)` | Ayu active indent guide |
| `--term-fg` | `#BFBDB6` | `rgb(191, 189, 182)` | Ayu foreground |
| `--term-fg-bright` | `#E8E6DD` | `rgb(232, 230, 221)` | Ghostty `foreground` override |
| `--term-fg-dim` | `#8A8986` | `rgb(138, 137, 134)` | 70% foreground over background |
| `--term-muted` | `#565B66` | `rgb(86, 91, 102)` | starship prompt symbol, tmux-dotbar session |
| `--term-accent` | `#E6B450` | `rgb(230, 180, 80)` | Ghostty `cursor-color` |
| `--term-red` | `#F07178` | `rgb(240, 113, 120)` | starship error symbol (palette 9) |
| `--term-selection` | `#D2A6FF4D` | `rgba(210, 166, 255, 0.3)` | Ayu lilac (Ghostty palette 12 override), 30% |
| `--term-shadow` | `rgba(0, 0, 0, 0.5)` | | floating URL bar drop shadow |
| `--term-font` | `"JetBrainsMono Nerd Font", "JetBrains Mono", Menlo, monospace` | | Ghostty `font-family` |
| `--term-font-size` | `12px` | | |
| `--term-radius` | `0px` | | flat, like tmux panes |

### Prefs (`zen/user.js`)

| pref | value | Zen default |
| --- | --- | --- |
| `toolkit.legacyUserProfileCustomizations.stylesheets` | `true` | `false` |
| `zen.view.window.scheme` | `0` | `2` |
| `zen.theme.accent-color` | `"#E6B450"` | `"AccentColor"` |
| `zen.theme.border-radius` | `0` | `-1` |
| `zen.theme.content-element-separation` | `6` | `8` |
| `zen.widget.macos.window-vibrancy` | `false` | `true` |
| `zen.theme.essentials-favicon-bg` | `false` | `true` |

### Preview JSON (`<out>` with suffix `.json`, written by `zen/preview.py`)

```
{
  "meta": {"zen_version": str, "size": [int, int], "startup_s": float,
           "total_s": float, "exit_code": int | null, "own_pid_gone": bool,
           "foreign_zen_pids_before": [int], "foreign_zen_pids_after": [int]},
  "prefs": {"<pref name>": bool | int | str | null},
  "user_sheets": [str],
  "chrome": {"<probe name>": {"found": bool, "props": {"<css prop>": str}}},
  "urlbar": {"<probe name>": {"found": bool, "props": {"<css prop>": str}}},
  "screenshots": [str],
  "error": str
}
```

`error` is present only on failure. `prefs` reports every pref of the table
above. `user_sheets` lists the hrefs of loaded sheets ending in
`/chrome/userChrome.css` or `/chrome/userContent.css`. `props` values are
`getComputedStyle(el, pseudo).getPropertyValue(prop)` with whitespace runs
collapsed to one space and trimmed; `found: false` gives `props: {}`.

### Probes

`chrome` probes (read after the tab set is built, URL bar closed):

| name | selector | pseudo | props |
| --- | --- | --- | --- |
| `root` | `:root` | | `--zen-primary-color`, `--toolbox-textcolor`, `font-family`, `color-scheme` |
| `browser_bg` | `#zen-browser-background` | | `--zen-main-browser-background` |
| `toolbar_bg` | `#zen-toolbar-background` | | `--zen-main-browser-background-toolbar` |
| `grain` | `.zen-browser-grain` | | `display` |
| `urlbar_bg` | `#urlbar > .urlbar-background` | | `background-color`, `border-radius`, `box-shadow` |
| `urlbar_input` | `#urlbar-input` | | `color`, `caret-color`, `font-family`, `font-size` |
| `urlbar_prompt` | `#urlbar .urlbar-input-container` | `::before` | `content`, `color` |
| `tab_selected_bg` | `zen-workspace[active] .tabbrowser-tab[selected]:not([zen-essential]) .tab-background` | | `background-color`, `border-radius`, `box-shadow` |
| `tab_selected_label` | `zen-workspace[active] .tabbrowser-tab[selected]:not([zen-essential]) .tab-label` | | `color`, `font-family`, `font-size` |
| `tab_label` | `zen-workspace[active] .tabbrowser-tab:not([selected], [zen-essential], [pinned], [multiselected]) .tab-label` | | `color` |
| `tab_close` | `zen-workspace[active] .tabbrowser-tab[selected] .tab-close-button` | | `color` |
| `essential_bg` | `.tabbrowser-tab[zen-essential]:not([selected]) .tab-background` | | `background-color`, `border-radius` |
| `content_frame` | `.browserSidebarContainer.deck-selected` | | `box-shadow`, `border-radius` |
| `content_browser` | `.browserSidebarContainer.deck-selected browser[type="content"]` | | `background-color` |
| `space_name` | `.zen-current-workspace-indicator-name` | | `color`, `font-weight` |
| `sidebar_button` | `#zen-sidebar-foot-buttons > toolbarbutton.toolbarbutton-1` | | `color` |
| `panel_font` | `panel` | | `font-family` |
| `menupopup_font` | `menupopup` | | `font-family` |

`urlbar` probes (read while the floating URL bar is open with `about:` typed):

| name | selector | pseudo | props |
| --- | --- | --- | --- |
| `urlbar_open_bg` | `#urlbar[breakout-extend] > .urlbar-background` | | `background-color`, `border-radius`, `box-shadow` |
| `urlbar_open_input` | `#urlbar[breakout-extend] #urlbar-input` | | `font-size` |
| `row_selected` | `.urlbarView-row[selected]` | | `background-color`, `box-shadow`, `border-radius` |
| `row_selected_title` | `.urlbarView-row[selected] .urlbarView-title` | | `color` |

## Tasks

Waves: 1 = T1, T4, T5, T6 (parallel); 2 = T3; 3 = T2. Commit each wave
by explicit pathspec before the next.

### T1: `zen/user.js` (verbatim)

New file, exactly this content:

```js
// Zen Browser prefs: the terminal look of zen/chrome/userChrome.css.
// install.sh links this file into the active profile (macOS); Zen reads it on
// every start. Deleting a line does not reset a pref: set the default (in the
// trailing comment) or reset it in about:config.

// Load chrome/userChrome.css (default false)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Dark UI regardless of the system appearance (default 2: follow the system)
user_pref("zen.view.window.scheme", 0);
// Ghostty cursor color; the Space gradient no longer tints the UI (default "AccentColor")
user_pref("zen.theme.accent-color", "#E6B450");
// Flat corners like tmux panes (default -1: platform radius)
user_pref("zen.theme.border-radius", 0);
// Gap around the web page, px (default 8)
user_pref("zen.theme.content-element-separation", 6);
// Opaque window like Ghostty, no desktop showing through (default true)
user_pref("zen.widget.macos.window-vibrancy", false);
// Essentials on the panel color instead of a favicon tint (default true)
user_pref("zen.theme.essentials-favicon-bg", false);
```

Task gate: `node --check zen/user.js` if `node` is on PATH (it is: install.sh
installs it), plus AC 9 for this file. Done: file matches the block byte for
byte.

### T2: `zen/chrome/userChrome.css`

New file. Implementer model: sonnet. Depends on T1 and T3 (its gate runs the
preview). Write the rules below in this order (later rules win ties between
rules of equal specificity). Every declaration except the palette and the
prompt `::before` block ends in `!important`. Keep the comments short and about
why, as below.

1. Header comment (plain text, no em dash):
   - "Zen Browser terminal look: Ayu dark palette and JetBrainsMono, like
     Ghostty + tmux + starship in this repo. Needs
     toolkit.legacyUserProfileCustomizations.stylesheets (zen/user.js)."
   - "A user sheet: its !important beats Zen's author !important and inline
     styles. Selectors checked against Zen 1.23.4b; after a Zen update run
     zen/preview.py and zen/checks.jq, then inspect misses with the Browser
     Toolbox."
2. `:root { ... }` with every palette token of Shared definitions, exact values.
3. Fonts:
   `:root, panel, menupopup, tooltip, panel-list { font-family: var(--term-font) !important; }`
4. Background, comment "The Space gradient writes these inline on every switch":
   ```css
   #zen-browser-background,
   #zen-toolbar-background {
     --zen-main-browser-background: var(--term-bg) !important;
     --zen-main-browser-background-old: var(--term-bg) !important;
     --zen-main-browser-background-toolbar: var(--term-bg) !important;
     --zen-main-browser-background-toolbar-old: var(--term-bg) !important;
   }
   .zen-browser-grain { display: none !important; }
   :root,
   zen-workspace {
     --zen-primary-color: var(--term-accent) !important;
     --toolbox-textcolor: var(--term-fg) !important;
   }
   ```
5. Web page frame: `.browserSidebarContainer` gets
   `box-shadow: 0 0 0 1px var(--term-border) !important;` and
   `border-radius: var(--term-radius) !important;`.
   `#tabbrowser-tabpanels browser[type="content"]` gets
   `background-color: var(--term-bg) !important;` (comment: "about:blank and
   page loads show this").
6. Tabs (all on `.tabbrowser-tab`, no `#tabbrowser-tabs` prefix: Essentials
   live outside it):
   - `.tabbrowser-tab .tab-background`: `border-radius: var(--term-radius)`,
     `background-color: transparent`, `box-shadow: none`.
   - `.tabbrowser-tab:hover .tab-background`: `background-color: var(--term-line)`.
   - `.tabbrowser-tab:is([selected], [multiselected]) .tab-background`:
     `background-color: var(--term-line)`.
   - `.tabbrowser-tab[selected]:not([zen-essential]) .tab-background`:
     `box-shadow: inset 2px 0 0 var(--term-accent)`; comment "the cursor".
   - `:root[zen-right-side="true"] .tabbrowser-tab[selected]:not([zen-essential]) .tab-background`:
     `box-shadow: inset -2px 0 0 var(--term-accent)`.
   - `.tabbrowser-tab[multiselected]:not([selected]) .tab-background`:
     `box-shadow: inset 0 0 0 1px var(--term-border-active)`.
   - `.tabbrowser-tab .tab-label`: `color: var(--term-fg-dim)`,
     `font-size: var(--term-font-size)`, `font-weight: 500` (comment: "Medium,
     as in Ghostty: Regular reads thin on the dark background").
   - `.tabbrowser-tab:hover .tab-label`: `color: var(--term-fg)`.
   - `.tabbrowser-tab[selected] .tab-label`: `color: var(--term-fg-bright)`.
   - `.tabbrowser-tab .tab-close-button`: `color: var(--term-muted)`.
   - `.tabbrowser-tab .tab-close-button:hover`: `color: var(--term-red)`,
     `background-color: transparent`.
7. Essentials (after the tab rules):
   - `.tabbrowser-tab[zen-essential] .tab-background`:
     `background-color: var(--term-panel)`, `border-radius: var(--term-radius)`,
     `box-shadow: inset 0 0 0 1px var(--term-border)`.
   - `.tabbrowser-tab[zen-essential]:hover .tab-background`:
     `background-color: var(--term-line)`.
   - `.tabbrowser-tab[zen-essential][selected] .tab-background`:
     `background-color: var(--term-line)`,
     `box-shadow: inset 0 -2px 0 var(--term-accent)`.
8. Sidebar chrome:
   - `.pinned-tabs-container-separator, .pinned-tabs-container-separator > *`:
     `--zen-pinned-separator-color: var(--term-border)`.
   - `zen-workspace > arrowscrollbox::part(scrollbox)`:
     `scrollbar-color: var(--term-muted) transparent`.
   - `#tabs-newtab-button`: `color: var(--term-fg-dim)`; `#tabs-newtab-button:hover`:
     `color: var(--term-fg)`.
   - `.zen-current-workspace-indicator-name`: `color: var(--term-fg)`,
     `font-weight: 700` (comment: "bold like the starship directory").
   - `#zen-sidebar-top-buttons toolbarbutton, #zen-sidebar-foot-buttons toolbarbutton`:
     `color: var(--term-fg-dim)`; same selectors with `:hover`: `color: var(--term-fg)`.
9. URL bar:
   - `#urlbar > .urlbar-background`: `background-color: var(--term-panel)`,
     `border-radius: var(--term-radius)`,
     `box-shadow: inset 0 0 0 1px var(--term-border)`, `outline: none`.
   - `#urlbar[breakout-extend] > .urlbar-background`:
     `box-shadow: 0 0 0 1px var(--term-border-active), 0 12px 32px var(--term-shadow)`.
   - `#urlbar-input`: `color: var(--term-fg)`, `caret-color: var(--term-accent)`,
     `font-size: var(--term-font-size)`, `font-weight: 500`.
   - `#urlbar[breakout-extend] #urlbar-input`: `color: var(--term-fg-bright)`,
     `font-size: 14px`.
   - `#urlbar-input::selection`: `background-color: var(--term-selection)`,
     `color: var(--term-fg-bright)`.
   - Prompt, comment "starship's success symbol":
     ```css
     #urlbar .urlbar-input-container::before {
       content: "\279C";
       color: var(--term-muted);
       font-weight: 700;
       align-self: center;
       padding-inline: 6px 2px;
     }
     ```
     If the screenshot shows the glyph misplaced (not left of the site/identity
     icon, or clipped), adjust only `padding-inline`/`align-self`/`order` in
     this block; the probe values (`content`, `color`) must stay.
   - Placeholder slot (added during T2 after the first preview: while the URL
     bar floats, Zen's `#urlbar-container` keeps a rounded grey fill in the
     sidebar): `#urlbar-container:has(> #urlbar[breakout-extend])`:
     `background-color: var(--term-panel)`, `border-radius: var(--term-radius)`,
     `box-shadow: inset 0 0 0 1px var(--term-border)`.
10. URL bar results:
    - `#urlbar-results .urlbarView-row`: `border-radius: var(--term-radius)`,
      `color: var(--term-fg)`.
    - `#urlbar-results .urlbarView-row:hover`: `background-color: var(--term-line)`.
    - `#urlbar-results .urlbarView-row:not([selected]) :is(.urlbarView-url, .urlbarView-action)`:
      `color: var(--term-fg-dim)`.
    - `#urlbar-results .urlbarView-row[selected]`:
      `background-color: var(--term-line)`,
      `box-shadow: inset 2px 0 0 var(--term-accent)`.
    - `#urlbar-results .urlbarView-row[selected] *`: `color: var(--term-fg-bright)`.
11. Toast: `#zen-toast-container .zen-toast`: `background: var(--term-panel)`,
    `color: var(--term-fg)`, `border-radius: var(--term-radius)`,
    `box-shadow: 0 0 0 1px var(--term-border-active)`.

Must not: add rules for other elements, `@import`, `@-moz-document`, a
`userContent.css`, hex colors outside the palette block.

Task gates (S = a scratch dir, never inside the repo):
`uv run zen/preview.py --out "$S/zen.png"`, then
`jq -e -r -f zen/checks.jq "$S/zen.json"` (T6 lands in wave 1). Look at both
PNGs (Read them): the sidebar is flat `#0B0E14`, text is monospace, the
selected tab shows the yellow left bar, the URL bar shows the `➜` glyph
before the site icon. Done: the jq gate prints only `true` and the PNGs show
the points above.

### T3: `zen/preview.py`

New file. Implementer model: sonnet. Depends on T1 (its gate reads the prefs).
A reference spike script is handed over in the dispatch prompt; port its
launch, readiness, tab-building, probing, screenshot and shutdown logic, with
the changes below.

- PEP 723 header so `uv run zen/preview.py` works with no project:
  ```python
  # /// script
  # requires-python = ">=3.11"
  # dependencies = ["marionette_driver==3.7.1"]
  # ///
  ```
- Module docstring: "Render the Zen theme in zen/ headless and dump computed
  styles", one paragraph on what it does and that it never touches a running
  Zen or a real profile.
- CLI (argparse): `--out PATH` (required, PNG of the chrome window),
  `--width INT` (default 1440), `--height INT` (default 900),
  `--zen PATH` (default `/Applications/Zen.app/Contents/MacOS/zen`),
  `--timeout FLOAT` (default 60.0, startup and script timeout in seconds),
  `--keep-profile` (flag, keep the temp profile for debugging). Nothing else.
- Source dir: `Path(__file__).resolve().parent` (the repo's `zen/`). Into a
  fresh `tempfile.mkdtemp(prefix="zen-preview-")` profile, symlink
  `user.js` -> `<src>/user.js` and `chrome/userChrome.css` ->
  `<src>/chrome/userChrome.css`, each only if the source file exists.
- `prefs.js` in the temp profile: the spike's harness prefs plus
  `marionette.port = 0` (user.js is read after prefs.js and wins).
- Launch exactly: `[zen, "--headless", "--marionette",
  "-remote-allow-system-access", "--no-remote", "--profile", str(profile)]`,
  env adds `MOZ_HEADLESS=1`, `MOZ_CRASHREPORTER_DISABLE=1`;
  `start_new_session=True`; stdout+stderr to `<profile>.log` next to the
  profile dir (deleted with it unless `--keep-profile`).
- Port: poll `<profile>/MarionetteActivePort` until a TCP connect succeeds or
  `--timeout` passes (raise `TimeoutError("marionette port did not open")`;
  if the process exits first raise `RuntimeError(f"zen exited early with code {rc}")`).
- After the session starts: chrome context, wait for readiness (spike
  `WAIT_READY_JS`), `set_window_rect(width=..., height=...)`, build the rich
  tab set of the spike (`about:blank`, a data: "Plain tab", `about:robots`;
  one essential, one pinned, one folder, a multiselected tab; the last opened
  normal tab selected), wait 1 s.
- Probes: the `chrome` and `urlbar` tables of Shared definitions, as tuples of
  a frozen dataclass `Probe(name: str, selector: str, props: tuple[str, ...],
  pseudo: str | None = None)`. Output keyed by probe name (JSON shape of
  Shared definitions); `user_sheets` from `InspectorUtils.getAllStyleSheets`
  filtered as defined there.
- Prefs: report exactly the prefs of the Prefs table (read with
  `Services.prefs` by type, `null` when unset).
- Screenshots: chrome window to `--out`; then open the floating URL bar with
  `about:` typed (spike `OPEN_URLBAR_JS`, same Marionette session), read the
  `urlbar` probes, screenshot to `<out stem>.urlbar.png` beside `--out`, close
  the URL bar. `screenshots` lists both paths.
- No userContent/content probes, no `--link`, `--probe`, `--probes`,
  `--simple`, `--tab`, `--pref` options.
- Shutdown in `finally`: Marionette quit (`eAttemptQuit`), wait 20 s, then
  terminate, then kill: only the PID this script started. Record
  `foreign_zen_pids_before/after` (`pgrep -x zen` minus own PID),
  `own_pid_gone`, `exit_code`, `total_s`. Remove the temp profile unless
  `--keep-profile`. Always write the JSON (`out.with_suffix(".json")`).
- Exit code: 0 on success; on any exception put `"<Type>: <message>"` into
  `error`, print it to stderr, exit 1. Print a one-line summary to stdout:
  `zen <version>: <out> (<total_s> s)`.
- Python rules: type hints everywhere, `mypy --strict` clean, no module-level
  mutable state (constants are tuples, frozen dataclasses or
  `types.MappingProxyType`, annotated `Final`), no `Any` without a comment
  saying why (the Marionette client is untyped), structured data in
  dataclasses where it is not the JSON payload itself. The import line:
  `from marionette_driver.marionette import Marionette  # type: ignore[import-untyped]`
  with a comment that the package ships no type information. Keep the
  `SyntaxWarning` filter with its reason (marionette_driver has invalid escape
  sequences).

Task gates: `uvx ruff format zen/preview.py` then
`uvx ruff check zen/preview.py && uvx ruff format --check zen/preview.py`,
`uv run --no-project -q --with mypy --with marionette_driver==3.7.1 mypy --strict zen/preview.py`,
and a run: `uv run zen/preview.py --out "$S/zen.png"` exits 0 with
`jq -e '(.error | not) and .meta.own_pid_gone and .prefs["toolkit.legacyUserProfileCustomizations.stylesheets"] == true and (.chrome | length) == 18 and (.urlbar | length) == 4 and (.screenshots | length) == 2' "$S/zen.json"`
(no `userChrome.css` yet: probes report Zen defaults, that is fine). Done:
gates green.

### T4: `install.sh`

Insert a new section between the end of the Claude Code section (the `fi`
closing its `if [[ "$OS" == "Darwin" ]]` block, around line 442) and the
`Personal-data guard` header. Anchor: insert immediately before these lines
(Edit `old_string`):

```
# =============================================================================
# Personal-data guard for this repo
# =============================================================================
```

New text (keep the blank line after it):

```sh
# =============================================================================
# Zen Browser: prefs and UI theme from zen/
# =============================================================================
# The profile exists only after Zen's first start; installs.ini names the one
# in use. userContent.css stays out: the content process sandbox does not
# follow a link that points outside the profile.
if [[ "$OS" == "Darwin" ]]; then
  zen_root="$HOME/Library/Application Support/zen"
  zen_profile=""
  if [[ -f "$zen_root/installs.ini" ]]; then
    zen_profile="$(awk '/^Default=/ { sub(/^Default=/, ""); print; exit }' "$zen_root/installs.ini")"
  fi
  if [[ -n "$zen_profile" && "$zen_profile" != /* ]]; then
    zen_profile="$zen_root/$zen_profile"
  fi
  if [[ -z "$zen_profile" || ! -d "$zen_profile" ]]; then
    echo "Skipping Zen theme: no Zen profile found, start Zen once and rerun"
  else
    echo "Linking Zen Browser prefs and theme..."
    mkdir -p "$zen_profile/chrome"
    for f in user.js chrome/userChrome.css; do
      dst="$zen_profile/$f"
      if [[ -e "$dst" && ! -L "$dst" ]]; then
        echo "Skipping $dst: a regular file, move it aside first"
        continue
      fi
      ln -sf "$DOTFILES/zen/$f" "$dst"
    done
  fi
fi

```

Must not change anything else in `install.sh` (package lists, Stow, Claude
section). Bash 3.2 compatible (`.claude/rules/shell-scripts.md`).
Task gates: `bash -n install.sh && /bin/bash -n install.sh`, the install
fixture block (Gates). Done: both green, `git diff --stat install.sh` shows
only insertions.

### T5: `README.md` and `CLAUDE.md`

Docs, one task (under 15 lines). Exact edits:

README.md:
1. Layout table, insert after the row starting
   ``| `anki/terminal_theme/` |``:
   ``| `zen/user.js`, `zen/chrome/userChrome.css` | Zen profile | macOS only; terminal look in the Ayu palette, linked into the profile named by `installs.ini`; check it headless with `zen/preview.py` + `zen/checks.jq` |``
2. "Before you start: existing configs" list, insert after the bullet that
   starts "- macOS: `~/.claude/CLAUDE.md` and `~/.claude/settings.json` become
   links too;" (after its second line):
   ```
   - macOS: in the Zen profile named by
     `~/Library/Application Support/zen/installs.ini`, `user.js` and
     `chrome/userChrome.css` become links; a regular file there is skipped
     with a message. Without a profile (Zen never started) the step is skipped.
   ```
3. "Install by hand (macOS)" table: the Zen row's Purpose cell becomes
   ``Browser; start it once before `install.sh` so the theme in `zen/` gets linked``.
4. "Verifying config changes" code block, append after the `aerospace` line:
   ```
   uv run zen/preview.py --out /tmp/zen.png && jq -e -r -f zen/checks.jq /tmp/zen.json # Zen theme, headless
   ```

CLAUDE.md (must end at 199 lines or fewer; it has 199 now):
1. Repository map, insert after the two-line `anki/` bullet (ends "edits and
   checks: `anki-addon` skill."):
   ```
   - `zen/`: Zen prefs + userChrome.css (macOS); `zen/preview.py` + `zen/checks.jq` check them.
   ```
2. "Documentation gaps": replace the two bullets
   "- No documented reload/validation for Karabiner, Starship, or Yazi." and
   "- No documented lazy.nvim lockfile update workflow." with one bullet:
   ```
   - No documented reload/validation for Karabiner, Starship, Yazi, or lazy.nvim lock updates.
   ```
   (merged only to stay under the 200-line limit, no meaning change).

Task gates: AC 8 commands, `test "$(wc -l < CLAUDE.md)" -le 199`. Done: gates
green, no other lines changed.

### T6: `zen/checks.jq` (verbatim)

New file, exactly this content. Run as `jq -e -r -f zen/checks.jq <json>`:
prints `FAIL <name>` per failing check, last line `true` or `false` (the exit
status).

```jq
# Theme checks for the JSON written by zen/preview.py.
# Usage: jq -e -r -f zen/checks.jq out.json  (prints FAIL lines, exit 0 = all pass)
def c: .chrome;
def u: .urlbar;
def has_font: contains("JetBrainsMono Nerd Font");
[
  ["no_error", (.error == null)],
  ["own_pid_gone", (.meta.own_pid_gone == true)],
  ["user_zen_untouched", (.meta.foreign_zen_pids_before == .meta.foreign_zen_pids_after)],
  ["userchrome_loaded", ((.user_sheets // []) | any(endswith("/chrome/userChrome.css")))],
  ["pref_stylesheets", (.prefs["toolkit.legacyUserProfileCustomizations.stylesheets"] == true)],
  ["pref_scheme", (.prefs["zen.view.window.scheme"] == 0)],
  ["pref_accent", (.prefs["zen.theme.accent-color"] == "#E6B450")],
  ["pref_radius", (.prefs["zen.theme.border-radius"] == 0)],
  ["pref_separation", (.prefs["zen.theme.content-element-separation"] == 6)],
  ["pref_vibrancy", (.prefs["zen.widget.macos.window-vibrancy"] == false)],
  ["pref_essentials_bg", (.prefs["zen.theme.essentials-favicon-bg"] == false)],
  ["primary_color", ((c.root.props["--zen-primary-color"] // "" | ascii_downcase) == "#e6b450")],
  ["root_font", (c.root.props["font-family"] // "" | has_font)],
  ["browser_bg", ((c.browser_bg.props["--zen-main-browser-background"] // "" | ascii_downcase) == "#0b0e14")],
  ["toolbar_bg", ((c.toolbar_bg.props["--zen-main-browser-background-toolbar"] // "" | ascii_downcase) == "#0b0e14")],
  ["no_grain", (c.grain.props.display == "none")],
  ["urlbar_bg", (c.urlbar_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["urlbar_radius", (c.urlbar_bg.props["border-radius"] == "0px")],
  ["urlbar_caret", (c.urlbar_input.props["caret-color"] == "rgb(230, 180, 80)")],
  ["urlbar_font_size", (c.urlbar_input.props["font-size"] == "12px")],
  ["urlbar_prompt", (c.urlbar_prompt.props.content == "\"➜\"")],
  ["urlbar_prompt_color", (c.urlbar_prompt.props.color == "rgb(86, 91, 102)")],
  ["tab_selected_bg", (c.tab_selected_bg.props["background-color"] == "rgb(19, 23, 33)")],
  ["tab_selected_radius", (c.tab_selected_bg.props["border-radius"] == "0px")],
  ["tab_cursor", (c.tab_selected_bg.props["box-shadow"] // "" | test("rgb\\(230, 180, 80\\) 2px 0px 0px 0px inset"))],
  ["tab_selected_label", (c.tab_selected_label.props.color == "rgb(232, 230, 221)")],
  ["tab_font", (c.tab_selected_label.props["font-family"] // "" | has_font)],
  ["tab_font_size", (c.tab_selected_label.props["font-size"] == "12px")],
  ["tab_label_dim", (c.tab_label.props.color == "rgb(138, 137, 134)")],
  ["tab_close", (c.tab_close.props.color == "rgb(86, 91, 102)")],
  ["essential_bg", (c.essential_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["content_frame", (c.content_frame.props["box-shadow"] == "rgba(108, 115, 128, 0.2) 0px 0px 0px 1px")],
  ["content_browser_bg", (c.content_browser.props["background-color"] == "rgb(11, 14, 20)")],
  ["space_name", (c.space_name.props.color == "rgb(191, 189, 182)")],
  ["sidebar_button", (c.sidebar_button.props.color == "rgb(138, 137, 134)")],
  ["panel_font", (c.panel_font.props["font-family"] // "" | has_font)],
  ["menupopup_font", (c.menupopup_font.props["font-family"] // "" | has_font)],
  ["urlbar_open_bg", (u.urlbar_open_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["urlbar_open_font_size", (u.urlbar_open_input.props["font-size"] == "14px")],
  ["row_selected_bg", (u.row_selected.props["background-color"] == "rgb(19, 23, 33)")],
  ["row_selected_title", (u.row_selected_title.props.color == "rgb(232, 230, 221)")]
]
| (.[] | select(.[1] != true) | "FAIL " + .[0]), all(.[1] == true)
```

Task gate: `echo '{}' | jq -r -f zen/checks.jq` runs without a jq error
(prints FAIL lines and `false`: there is no preview JSON yet). Done: file
matches the block byte for byte and the gate shows no jq error.

## Seams

| producer | consumer | contract |
| --- | --- | --- |
| T1 | T3, T6 | Prefs table (names, values) |
| T3 | T2, T6 | Preview JSON shape and probe names/selectors/props |
| T2 | T6 | Palette computed values, probe expectations |
| T1, T2 | T4 | File layout (`zen/user.js`, `zen/chrome/userChrome.css`) |
| T3, T6, T4 | T5 | Commands `uv run zen/preview.py --out ...`, `jq -e -r -f zen/checks.jq ...`; link behavior and messages |

## Edge cases

- macOS vs Linux: the install block runs only on Darwin; Linux prints
  nothing (fixture case f). `zen/preview.py` is macOS-only by its default
  binary path; `--zen` overrides it.
- Zen not installed or never started: no `installs.ini` or a missing profile
  dir, the block prints the skip line and creates nothing (cases a, d).
- A user's own `user.js` or `userChrome.css`: kept, skip line (case c).
- Profile path with spaces and parentheses, absolute path (cases b, e).
- Zen running during install: links are fine, Zen reads them on next start.
- Preview while the user's Zen runs: separate process, `--no-remote`, own temp
  profile, Marionette port 0; foreign PIDs recorded before and after.
- Dirty worktree: other sessions share the checkout; commit by explicit
  pathspec only.
- First run of `uv run zen/preview.py`: uv downloads `marionette_driver` once.

## Live apply (orchestrator, after PASS and merge)

Not part of any task. Links the real profile the same way the install block
does, without running `install.sh`; the user restarts Zen afterwards.

```sh
zen_root="$HOME/Library/Application Support/zen"
p="$zen_root/$(awk '/^Default=/ { sub(/^Default=/, ""); print; exit }' "$zen_root/installs.ini")"
mkdir -p "$p/chrome"
[ -e "$p/user.js" ] || ln -s "$HOME/dotfiles/zen/user.js" "$p/user.js"
[ -e "$p/chrome/userChrome.css" ] || ln -s "$HOME/dotfiles/zen/chrome/userChrome.css" "$p/chrome/userChrome.css"
```

## Not doing

- No `userContent.css` (symlink not applied by the content sandbox; about:home
  and about:newtab keep Zen's dark page, rarely seen with
  `zen.urlbar.replace-newtab`).
- No Zen Mod, no Sine/fx-autoconfig, no JavaScript.
- No styling of native macOS context menus or the native popover backgrounds
  of panels (fonts only).
- No change to tab heights, sidebar width, keyboard shortcuts, compact mode,
  Glance, folders' own colors, media controls.
- No change to the user's Space settings or `zen-sessions.jsonlz4`; the Space
  gradient is only painted over.
- No Zen cask in `install.sh` package lists; `everything.md` is not updated.
- No `browser.display.background_color.dark` (no visible effect in Zen).

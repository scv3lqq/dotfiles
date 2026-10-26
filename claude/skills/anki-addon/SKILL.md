---
name: anki-addon
description: Develop, debug, restyle or tweak a desktop Anki add-on (aqt.gui_hooks, webview CSS/JS injection, setWebExports, config.json, Qt QSS) or Anki card templates/styling. Use for "тема для Anki", "аддон Anki", restyling the reviewer/deck browser/toolbar, card front/back templates, anything under addons21 or dotfiles/anki/. Also for any small change to the theme already installed: "убери мигающий курсор", "поменяй цвет/шрифт/статус-бар", "эта штука в Anki мешает", a screenshot of the Anki UI with a complaint. Not for creating cards: that is the `anki` skill.
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Anki add-on development

The user's Anki add-on source lives in `~/dotfiles/anki/`, symlinked into
`~/Library/Application Support/Anki2/addons21/<name>`. Card templates that must
also work on AnkiDroid live in `~/dotfiles/anki/cards/`.

Everything below was verified against Anki 26.9.2 (PyQt6 6.11) on macOS.
Re-verify with `scripts/probe.sh` when the version differs.

## Probe first, never guess

`bash ~/.claude/skills/anki-addon/scripts/probe.sh <subcommand>`

| subcommand | answers |
| --- | --- |
| `version` | Anki version, add-ons installed, profile theme (0 system / 1 light / 2 dark) |
| `hooks <regex>` | which `gui_hooks` names exist in this build |
| `syms <module> <regex>` | any identifier inside a bundled `aqt/*.pyc` or `_aqt/hooks.pyc` |
| `css <name>` | the screen-specific tail of a bundled stylesheet (`webview`, `reviewer`, `reviewer-bottom`, `deckbrowser`, `overview`, `toolbar`) |
| `check <pkg>` | is the add-on loaded: fetches its web exports off Anki's media server |
| `restart` | quit + reopen Anki |

The app ships only `.pyc`, so identifiers are read out of the byte stream with a
regex. That is enough to confirm a hook, a class name or a CSS class exists.

## Known map for 26.9.x

**Hooks that matter** (all public, all present):
`webview_will_set_content`, `card_review_webview_did_init`,
`reviewer_did_show_question`, `reviewer_did_show_answer`,
`reviewer_did_answer_card`, `state_did_change`, `theme_did_change`,
`main_window_did_init`, `deck_browser_did_render`, `overview_did_refresh`,
`webview_did_receive_js_message`.

**`webview_will_set_content` context classes** (match on `type(context).__name__`,
never import the private class): `TopToolbar`, `BottomBar`, `DeckBrowser`,
`DeckBrowserBottomBar`, `Overview`, `OverviewBottomBar`, `Reviewer`,
`ReviewerBottomBar`. `WebContent` has `.head`, `.body`, `.css`, `.js`.

**Web exports**: `mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js)")`,
then append `/_addons/{mw.addonManager.addonFromModule(__name__)}/web/x.css` to
`web_content.css`. Config-driven values go into `web_content.head` as an inline
`<style>` of CSS variables, which wins over the exported file.

**The big lever: Anki's own design tokens.** `_aqt/data/web/css/webview.css`
defines them on `:root` and `:root.night-mode`. Remapping them recolours every
widget you wrote no rule for. Your block must repeat both selectors to beat the
`(0,2,0)` specificity, and add-on CSS is appended last so it wins on ties:

```css
:root, :root.night-mode {
  --fg: ...; --canvas: ...; --canvas-elevated: ...; --canvas-inset: ...;
  --border: ...; --border-subtle: ...; --border-focus: ...; --focus-color: ...;
  --button-bg: ...; --button-gradient-start: ...; --button-primary-bg: ...;
  --state-new: ...; --state-learn: ...; --state-review: ...; --flag-1..7: ...;
  --highlight-bg: ...; --selected-bg: ...; --scrollbar-bg: ...;
  --border-radius: 0; --border-radius-medium: 0; --border-radius-large: 0;
  --shadow: transparent; --blur: 0px; --font-size: ...;
}
```

**DOM per screen** (from the bundled templates, stable across recent versions):

- Top toolbar: `.header > .left-tray | .toolbar | .right-tray`, items `a.hitem`.
- Bottom bars: `<center id=outer><table id=header>` for the generic one;
  the reviewer's is `#outer > #innertable > td.stat | td#middle | td.stat`.
- Deck browser: `tr.deck` (`.current` for the selected row), `td.decktd`,
  `a.deck`, `th.count`, `td.optscol`, `a.collapse`, `img.gears`, `#studiedToday`,
  `.callout`.
- Overview: `h3`, `.descfont.descmid.description`, `#study`, `.smallLink`.
- Counts everywhere: `.new-count`, `.learn-count`, `.review-count`,
  `.zero-count`, `.bury-count`.
- Reviewer card area: `#qa`, `#_mark`, `#_flag`, `hr#answer`, `input#typeans`,
  `.typeGood/.typeBad/.typeMissed`.
- Answer buttons: `#middle button[data-ease="1".."4"]`, default one is
  `#defease`; before answering there is `#ansbut` with `span.stattxt`.
- Base CSS sets `* { box-sizing: content-box }` and `body { margin: 2em }`.

**Reviewer state from Python**: `mw.col.sched.counts()` → `(new, learn, review)`;
active queue from `mw.reviewer.card.queue` (`0` new, `1`/`3` learn, `2` review,
`4` preview); deck via `mw.col.decks.current()["name"]`.

**Fixed overlays** belong in the reviewer's main webview
(`position: fixed; bottom: 0`, plus `padding-bottom` on `body`). The bottom bar
webview has a height Anki controls; do not grow it.

## Install and verify

```sh
ln -s ~/dotfiles/anki/<pkg> ~/Library/Application\ Support/Anki2/addons21/<pkg>
osascript -e 'quit app "Anki"'; open -a Anki
```

`screencapture -x` needs Screen Recording permission for the terminal and
usually fails here with `could not create image from display`. Say so and ask
for screenshots rather than retrying. Verify what you can without pixels:

- `probe.sh check <pkg>` → HTTP 200 on the exported CSS/JS proves the module
  imported cleanly, because `setWebExports` only runs on a successful import.
- AnkiConnect on `:8765` (`{"action":"version","version":6}`) proves the GUI is
  responsive; `~/Library/Application Support/Anki2/crash.log` must stay empty.
- `python3 -m py_compile`, `node --check`, `jq empty`, CSS brace balance.

## Tweaking an installed theme

Grep `~/dotfiles/anki/` for the visible token (class name, keyframe, config key)
and edit there; the plan under `~/dotfiles/plans/` is history, not a spec. Then
`probe.sh restart` + `probe.sh check <pkg>` instead of telling the user to
restart. Removing a feature: drop its DOM node, its CSS rule, its keyframes and
its config key in one pass, and leave palette tokens alone (`--tt-cursor` is the
Ayu cursor colour, used by focus outlines too).

`config.json` is only the default. The live user config is
`addons21/<pkg>/meta.json`, written on first config edit and merged over the
defaults, so a key deleted from `config.json` survives there and a changed
default is ignored. Deleting the code path is what actually removes a feature;
check `meta.json` when a config change has no effect.

## Conventions

- `aqt.gui_hooks` only, no monkey-patching, so the add-on survives updates.
- One palette source. Two places cannot read CSS variables and must duplicate
  it deliberately, with a comment saying so: the QSS token table in
  `__init__.py` and `cards/cards.css` (AnkiDroid has no add-on).
- Cards: guard both `.nightMode` (desktop) and `.night_mode` (AnkiDroid), and
  set a background on `html, body` as well as `.card`.
- Never write `collection.anki2`, `prefs21.db`, or another add-on's folder.
- `__pycache__/` appears inside the add-on folder, which is inside the repo.
  Keep it in `.gitignore`.

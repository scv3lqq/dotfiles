# Obsidian theme "Ayu Ink"

## Current behavior

The open vault (`$VAULT`, value given in dispatch prompts) uses the community
Minimal theme with the Minimal Settings and Style Settings plugins, base font
size 10 and window zoom level 3 (factor 1.728). Nothing Obsidian-related lives in
this repo. Ghostty, Zen, Neovim, tmux and Anki all share one Ayu dark look:
flat `#0B0E14`, text `#BFBDB6`/`#E8E6DD`, cursor yellow `#E6B450` as the only
accent, lilac selection, JetBrainsMono Nerd Font, square corners.

## Goal

A repo-owned Obsidian theme `Ayu Ink` that matches the terminal and browser
(Ayu palette, flat surfaces, mono UI chrome, yellow as the only accent) and takes
from Vercel (hairline borders, mono for UI and metadata), Linear (layered
near-black surfaces, quiet text hierarchy, tight heading tracking) and Stripe
(contrast measured, not guessed). Body text readability wins every conflict:
sans body text, APCA Lc 80+ for body, 65-75 characters per line, line height 1.65.
A headless preview renders the theme against the installed app's own `app.css`
and a checker proves contrast and typography. `install.sh` links the theme into
local vaults; the open vault switches to it.

Placeholders: `$S` = session scratchpad, `$SPIKE` = `$S/obsidian-spike` (spike
output: `fixture.html`, `app.css`, `vars.txt`), `$VAULT` = the open vault. Their
values come with each dispatch prompt; never write them into a repo file.

## Acceptance criteria

Base result (main before this branch) in brackets.

1. `python3 obsidian/preview.py --out "$S/ac"` exits 0 and prints 4 paths;
   `python3 obsidian/check.py "$S/ac/computed-1440.json" "$S/ac/computed-zoom3.json"`
   exits 0, last line starts with `OK `. [base: no such file]
2. The validator Reads `$S/ac/shot-1440.png` and `$S/ac/shot-zoom3.png`: flat
   dark `#0B0E14` UI, sans body text, mono sidebar/tab/status bar, yellow only on
   the active file marker, link underlines and checkbox, no purple anywhere, no
   region that looks unstyled. [base: no such file]
3. `jq -r '.name + " " + .version' "obsidian/Ayu Ink/manifest.json"` prints
   `Ayu Ink 1.0.0`. [base: no such file]
4. `grep -c '!important' "obsidian/Ayu Ink/theme.css"` prints `0`;
   `grep -c 'font-text-size:' "obsidian/Ayu Ink/theme.css"` prints `0` (the
   user's font size is never overridden). [base: no such file]
5. `bash -n install.sh` exits 0, and the T5 block check (T5 gates) prints `True`
   and `ordered`. [base: bash -n exits 0; block check prints False]
6. `grep -cF '`zen/`, `obsidian/`: macOS themes' CLAUDE.md` prints `1` and
   `wc -l < CLAUDE.md` prints `200`. [base: 0 and 200]
7. Live: `readlink "$VAULT/.obsidian/themes/Ayu Ink"` prints
   `$HOME/dotfiles/obsidian/Ayu Ink` (expanded), `jq -r .cssTheme
   "$VAULT/.obsidian/appearance.json"` prints `Ayu Ink`, and the T7 report has a
   screenshot verdict. [base: no link, `Minimal`]
8. `uvx ruff check obsidian/ && uvx ruff format --check obsidian/ && uvx mypy --strict obsidian/preview.py obsidian/check.py`
   exits 0. [base: no such files]
9. `git diff -U0 main...HEAD | python3 -c 'import sys; print(sum(chr(0x2014) in l for l in sys.stdin if l.startswith("+")))'`
   prints `0`. [base: 0]
10. `git diff main...HEAD | grep -c '/Use[r]s/'` prints `0`. [base: 0]

## Gates

```bash
bash -n install.sh
jq empty "obsidian/Ayu Ink/manifest.json"
uvx ruff check obsidian/ && uvx ruff format --check obsidian/
uvx mypy --strict obsidian/preview.py obsidian/check.py
python3 obsidian/preview.py --out "$S/gate" && python3 obsidian/check.py "$S/gate/computed-1440.json" "$S/gate/computed-zoom3.json"
```

## Edge cases

- macOS vs Linux: the install.sh block runs on Darwin only; `preview.py` defaults
  to macOS paths (asar, Chrome) and takes overrides.
- Missing tools: no `obsidian.json` or no `jq` makes install.sh print a skip
  line; no Chrome or no asar makes `preview.py` exit 2 with a message.
- Dirty worktree: the untracked `telegram/` dir belongs to another session and is
  never staged; every commit uses explicit pathspecs.
- First run: Obsidian never started means no `obsidian.json` (skip line); a vault
  without `.obsidian/` is skipped; a real directory at the link target is skipped.
- iCloud vaults (`$HOME/Library/Mobile Documents/...`) are skipped: a synced link
  points nowhere on the phone.
- User font size: the theme never sets `--font-text-size`; line width is a
  multiple of it, so base 10 and base 16 both get ~70 characters per line.
- Minimal Settings stays enabled in the vault and still sets body classes and
  `--font-ui-small:13px` inline: the zoom3 render emulates it.

## Shared definitions

### D1. Paths

- Theme dir: `obsidian/Ayu Ink/` with `manifest.json` and `theme.css` (folder
  name must equal manifest `name`).
- Fixture: `obsidian/fixture.html`. Preview: `obsidian/preview.py`. Checker:
  `obsidian/check.py`.

### D2. Fixture query params (T2 produces, T3 uses)

- `css=<file>`: theme stylesheet href, default `theme.css` (a missing file is fine).
- `base=<n>`: base font size in px, default 16, emulated exactly as the spike
  fixture does (inline `--font-text-size` on body, html font-size).
- `plugins=minimal-settings`: emulate the Minimal Settings side effects (the
  spike's former vault-specific branch: body classes + inline CSS vars).
- `measure=1`: after load, write the D3 JSON with `JSON.stringify` as the text of
  `<pre id="out">`.
- The page links `app.css` and the theme relatively (same dir).

### D3. Measure JSON (T2 produces, T4 consumes)

```json
{"meta": {"base": 16, "viewport": [1440, 1600], "plugins": ""},
 "el": {"p": {"family": "...", "size": 16.0, "lineHeight": 26.4, "weight": 400,
              "letterSpacing": 0.0, "maxWidth": null, "color": [218, 216, 208, 1.0],
              "bg": [11, 14, 20], "decoration": [218, 216, 208, 1.0], "boxShadow": "none"}}}
```

- `family`: computed `font-family` string as is. `size`, `lineHeight`,
  `letterSpacing`, `maxWidth`: px floats (`lineHeight` `normal` -> null,
  `letterSpacing` `normal` -> 0, `maxWidth` `none` -> null). `weight`: int.
- `color`, `decoration` (`text-decoration-color`): `[r, g, b, a]`, r/g/b ints,
  a float 0..1, read through a 1x1 canvas (`fillStyle = value`, `fillRect`,
  `getImageData`) so `oklch()`/`color-mix()` values come out as sRGB.
- `bg`: effective opaque background `[r, g, b]`: walk from the element up through
  its ancestors collecting `background-color` (canvas-normalized), stop at the
  first with alpha >= 0.999 (none: `[255, 255, 255]`), then composite the
  collected translucent layers over it from the outermost inward
  (`c = a*layer + (1-a)*c`), round to ints.
- `boxShadow`: computed `box-shadow` string.
- A key whose selector matches nothing is left out (the checker reports it).

Keys and selectors (`document.querySelector`, first match):

| key | selector |
|---|---|
| body | `body` |
| root | `.workspace-split.mod-root` |
| sizer | `.markdown-preview-sizer` |
| p | `.markdown-preview-sizer > div > p` |
| h1 / h2 / h3 / h4 | `.markdown-preview-view h1` (h2, h3, h4 alike) |
| strong | `.markdown-preview-sizer > div > p strong` |
| link | `.markdown-preview-view a.internal-link:not(.is-unresolved)` |
| unresolved | `.markdown-preview-view a.internal-link.is-unresolved` |
| external | `.markdown-preview-view a.external-link` |
| tag | `.markdown-preview-view a.tag` |
| codeInline | `.markdown-preview-sizer > div > p code` |
| codeBlock | `.markdown-preview-view pre code` |
| tokKeyword / tokString / tokFunction / tokComment / tokNumber / tokOperator / tokPunct | `.markdown-preview-view pre .token.keyword` (`.string`, `.function`, `.comment`, `.number`, `.operator`, `.punctuation`) |
| blockquote | `.markdown-preview-view blockquote p` |
| calloutTitle | `.markdown-preview-view .callout .callout-title-inner` |
| calloutContent | `.markdown-preview-view .callout .callout-content p` |
| th / td | `.markdown-preview-view th` / `.markdown-preview-view td` |
| cmSizer | `.markdown-source-view .cm-sizer` |
| cmLine | `.markdown-source-view .cm-line:not(.HyperMD-header)` |
| cmH1 | `.markdown-source-view .cm-line.HyperMD-header-1` |
| nav | `.nav-file-title:not(.is-active)` |
| navActive | `.nav-file-title.is-active` |
| tab | `.workspace-tab-header.is-active .workspace-tab-header-inner-title` |
| status | `.status-bar-item` |

### D4. Renders (T3 produces, T4 and the validator consume)

| name | base | window | device scale | plugins |
|---|---|---|---|---|
| `1440` | 16 | 1440x1600 | 1 | none |
| `zoom3` | 10 | 713x503 | 1.728 | `minimal-settings` |

Outputs in `--out`: `shot-<name>.png`, `computed-<name>.json`.

### D5. Palette (T1 writes it, T4 encodes its expectations)

| token | value | APCA Lc on `#0B0E14` (WCAG) |
|---|---|---|
| `--ayu-bg` | `#0B0E14` | |
| `--ayu-panel` | `#0F131A` | |
| `--ayu-hover` | `#131721` | |
| `--ayu-border` | `#6C738033` | |
| `--ayu-border-strong` | `#6C738080` | |
| `--ayu-heading` | `#E8E6DD` | -91.2 (15.5) |
| `--ayu-text` | `#DAD8D0` | -82.5 (13.5) |
| `--ayu-muted` | `#BFBDB6` | -66.5 (10.3) |
| `--ayu-faint` | `#8A8986` | about -39 (5.1) |
| `--ayu-accent` | `#E6B450` | -65.9 (10.1) |
| `--ayu-accent-hover` | `#FFB454` | -70.3 (11.0) |
| `--ayu-selection` | `#D2A6FF4D` | |

Code colors: comment `#8B929C` (-42.6 on panel), keyword `#FF8F40` (-57.2),
operator `#F29668` (-57.4), string `#AAD94C`, function `#FFB454`, property
`#59C2FF`, value `#D2A6FF`, tag `#39BAE6`, important `#F07178`.

### D6. Typography expectations (T1 writes them, T4 checks them)

F = measured `p.size`.

- Body font stack (`--font-text-theme`): `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Segoe UI", system-ui, sans-serif`.
- Mono stack (`--font-interface-theme` and `--font-monospace-theme`): `"JetBrainsMono Nerd Font", "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace`.
- `--line-height-normal: 1.65`; `--file-line-width: calc(var(--font-text-size) * 36)`.
- Headings: sizes 1.75 / 1.4 / 1.2 / 1.05 / 1 / 0.875 em, weight 600 all,
  line heights 1.2 / 1.25 / 1.3 / 1.4 / 1.5 / 1.5, letter spacing
  -0.022 / -0.018 / -0.012 / -0.006 / 0 / 0 em.
- `--code-size: 0.875em`. UI weight 500 on nav items, tab titles, status bar.

## Tasks

Wave 1: T1-T5 in parallel (disjoint files). Then main adds the CLAUDE.md line
(T6, micro), runs Gates, commits per task. Then T7 (live), then review.

### T1. Theme files (model: sonnet)

Files: `obsidian/Ayu Ink/manifest.json`, `obsidian/Ayu Ink/theme.css` (new).

`manifest.json` verbatim:

```json
{
  "name": "Ayu Ink",
  "version": "1.0.0",
  "minAppVersion": "1.6.0",
  "author": "scv3lqq"
}
```

`theme.css`: plain CSS, no `!important`, no `@import`, no `url()`, no
`@settings` block. Variable names are Obsidian 1.14.5 core names (all verified in
`$SPIKE/vars.txt`). Three parts, in this order, each opened by one short comment
line naming the part (e.g. `/* Typography */`):

1. `body { ... }` typography (applies to both modes):
   - `--font-text-theme`, `--font-interface-theme`, `--font-monospace-theme`: D6 stacks.
   - `--line-height-normal: 1.65;` `--file-line-width: calc(var(--font-text-size) * 36);`
   - `--h1-size: 1.75em;` `--h2-size: 1.4em;` `--h3-size: 1.2em;` `--h4-size: 1.05em;` `--h5-size: 1em;` `--h6-size: 0.875em;`
   - `--h1-weight` .. `--h6-weight`: `600`.
   - `--h1-line-height: 1.2;` `--h2-line-height: 1.25;` `--h3-line-height: 1.3;` `--h4-line-height: 1.4;` `--h5-line-height: 1.5;` `--h6-line-height: 1.5;`
   - `--h1-letter-spacing: -0.022em;` `--h2-letter-spacing: -0.018em;` `--h3-letter-spacing: -0.012em;` `--h4-letter-spacing: -0.006em;` `--h5-letter-spacing: 0em;` `--h6-letter-spacing: 0em;`
   - `--code-size: 0.875em;` `--code-border-width: 1px;` `--tag-border-width: 1px;`
   - `--link-decoration-thickness: 1px;` `--link-unresolved-opacity: 1;` `--link-unresolved-decoration-style: dashed;`
   - Never `--font-text-size`, `--font-ui-*`, `--p-spacing`, `--heading-spacing`.
2. `.theme-dark { ... }` colors and shape. A class selector on purpose: app.css
   overrides some of these on `.mod-macos` (e.g. `--tab-radius`,
   `--scrollbar-thumb-bg`), which a `body` rule would lose to.
   - D5 palette tokens `--ayu-*` with their values.
   - Accent: `--accent-h: 40;` `--accent-s: 75%;` `--accent-l: 61%;` `--color-accent: var(--ayu-accent);` `--color-accent-1: var(--ayu-accent-hover);` `--color-accent-2: var(--ayu-accent-hover);`
   - Surfaces: `--background-primary: var(--ayu-bg);` `--background-primary-alt: var(--ayu-panel);` `--background-secondary: var(--ayu-bg);` `--background-secondary-alt: var(--ayu-panel);` `--background-modifier-border: var(--ayu-border);` `--background-modifier-border-hover: var(--ayu-border-strong);` `--background-modifier-border-focus: var(--ayu-border-strong);` `--background-modifier-hover: var(--ayu-hover);` `--background-modifier-active-hover: var(--ayu-hover);` `--divider-color: var(--ayu-border);`
   - Text: `--text-normal: var(--ayu-text);` `--text-muted: var(--ayu-muted);` `--text-faint: var(--ayu-faint);` `--text-accent: var(--ayu-accent);` `--text-accent-hover: var(--ayu-accent-hover);` `--text-on-accent: var(--ayu-bg);` `--text-selection: var(--ayu-selection);` `--interactive-accent: var(--ayu-accent);` `--interactive-accent-hover: var(--ayu-accent-hover);` `--caret-color: var(--ayu-accent);`
   - Named colors: `--color-red: #F07178;` `--color-orange: #FF8F40;` `--color-yellow: #E6B450;` `--color-green: #AAD94C;` `--color-cyan: #95E6CB;` `--color-blue: #59C2FF;` `--color-purple: #D2A6FF;` `--color-pink: #F29668;`
   - Code: `--code-background: var(--ayu-panel);` `--code-normal: var(--ayu-text);` `--code-comment: #8B929C;` `--code-function: #FFB454;` `--code-important: #F07178;` `--code-keyword: #FF8F40;` `--code-operator: #F29668;` `--code-property: #59C2FF;` `--code-punctuation: var(--ayu-muted);` `--code-string: #AAD94C;` `--code-tag: #39BAE6;` `--code-value: #D2A6FF;` `--code-radius: 4px;`
   - Headings and emphasis: `--h1-color` .. `--h5-color: var(--ayu-heading);` `--h6-color: var(--ayu-muted);` `--bold-color: var(--ayu-heading);` `--heading-formatting: var(--ayu-faint);`
   - Links: `--link-color: var(--ayu-text);` `--link-color-hover: var(--ayu-accent);` `--link-external-color: var(--ayu-text);` `--link-external-color-hover: var(--ayu-accent);` `--link-unresolved-color: var(--ayu-muted);`
   - Tags: `--tag-color: var(--ayu-muted);` `--tag-color-hover: var(--ayu-text);` `--tag-background: var(--ayu-hover);` `--tag-background-hover: var(--ayu-hover);` `--tag-border-color: var(--ayu-border);` `--tag-border-color-hover: var(--ayu-border-strong);` `--tag-radius: 4px;`
   - Blocks: `--blockquote-border-color: var(--ayu-border-strong);` `--callout-radius: 4px;` `--table-header-background: var(--ayu-panel);` `--table-header-color: var(--ayu-heading);` `--table-border-color: var(--ayu-border);` `--hr-color: var(--ayu-border);`
   - Lists and checkboxes: `--list-marker-color: var(--ayu-faint);` `--list-marker-color-hover: var(--ayu-muted);` `--list-marker-color-collapsed: var(--ayu-accent);` `--checkbox-color: var(--ayu-accent);` `--checkbox-color-hover: var(--ayu-accent-hover);` `--checkbox-marker-color: var(--ayu-bg);` `--checkbox-border-color: var(--ayu-faint);` `--checkbox-border-color-hover: var(--ayu-muted);`
   - Navigation: `--nav-item-color: var(--ayu-muted);` `--nav-item-color-hover: var(--ayu-text);` `--nav-item-color-active: var(--ayu-heading);` `--nav-item-color-selected: var(--ayu-heading);` `--nav-item-color-highlighted: var(--ayu-accent);` `--nav-item-background-hover: var(--ayu-hover);` `--nav-item-background-active: var(--ayu-hover);` `--nav-item-background-selected: color-mix(in srgb, var(--ayu-accent) 12%, transparent);`
   - Chrome: `--titlebar-background: var(--ayu-bg);` `--titlebar-background-focused: var(--ayu-bg);` `--ribbon-background: var(--ayu-bg);` `--ribbon-background-collapsed: var(--ayu-bg);` `--tab-container-background: var(--ayu-bg);` `--tab-background-active: var(--ayu-bg);` `--tab-outline-color: var(--ayu-border);` `--tab-text-color-active: var(--ayu-muted);` `--tab-text-color-focused-active-current: var(--ayu-heading);` `--tab-radius: 0;` `--tab-radius-active: 0;` `--status-bar-background: var(--ayu-bg);` `--status-bar-text-color: var(--ayu-faint);` `--status-bar-border-color: var(--ayu-border);` `--scrollbar-bg: transparent;` `--scrollbar-thumb-bg: var(--ayu-border);` `--scrollbar-active-thumb-bg: var(--ayu-border-strong);`
   - Shape: `--radius-s: 0;` `--radius-m: 0;` `--radius-l: 0;` (square chrome like Zen; code, callouts and tags keep 4px above).
3. Rules:
   ```css
   .nav-file-title,
   .nav-folder-title,
   .workspace-tab-header-inner-title,
   .view-header-title,
   .status-bar {
     font-weight: 500;
   }

   .theme-dark .nav-file-title.is-active {
     box-shadow: inset 2px 0 0 var(--ayu-accent);
   }

   .markdown-rendered a.tag,
   .cm-s-obsidian span.cm-hashtag {
     font-family: var(--font-monospace);
   }

   .theme-dark .markdown-rendered a.internal-link,
   .theme-dark .markdown-rendered a.external-link,
   .theme-dark .cm-s-obsidian span.cm-hmd-internal-link,
   .theme-dark .cm-s-obsidian span.cm-url {
     text-decoration-color: color-mix(in srgb, var(--ayu-accent) 60%, transparent);
     text-underline-offset: 0.2em;
   }

   .theme-dark .markdown-rendered a.internal-link.is-unresolved {
     text-decoration-color: var(--ayu-faint);
   }
   ```
   Every class in these selectors must occur in `$SPIKE/app.css`
   (`grep -c 'cm-hmd-internal-link' "$SPIKE/app.css"` etc.); if one does not,
   stop and report BLOCKED with the class name.

Must not: set colors outside `.theme-dark` (light mode keeps Obsidian's
defaults), touch any other file.

Task gates:

```bash
jq empty "obsidian/Ayu Ink/manifest.json"
test "$(grep -c '!important' "obsidian/Ayu Ink/theme.css")" = 0
test "$(grep -c 'font-text-size:' "obsidian/Ayu Ink/theme.css")" = 0
mkdir -p "$S/t1" && cp "$SPIKE/fixture.html" "$SPIKE/app.css" "$S/t1/" && cp "obsidian/Ayu Ink/theme.css" "$S/t1/theme.css"
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$C" --headless=new --disable-gpu --hide-scrollbars --no-first-run --user-data-dir="$S/t1/.chrome" --allow-file-access-from-files --window-size=1440,1600 --virtual-time-budget=3000 --screenshot="$S/t1/shot.png" "file://$S/t1/fixture.html"
"$C" --headless=new --disable-gpu --no-first-run --user-data-dir="$S/t1/.chrome" --allow-file-access-from-files --window-size=1440,900 --virtual-time-budget=3000 --dump-dom "file://$S/t1/fixture.html?measure=1" 2>/dev/null > "$S/t1/dom.html"
```

Read `$S/t1/shot.png` and the measured values in `$S/t1/dom.html` (`pre#out`,
spike format): reading `p` line height 1.65 x size, sizer max-width 576px, h1
28px weight 600, background `#0B0E14`, nav item in JetBrainsMono.

Done: both files exist, gates pass, the screenshot shows the Ayu look.

### T2. Fixture (model: sonnet)

File: `obsidian/fixture.html` (new), based on `$SPIKE/fixture.html` (290 lines,
classes verified against app.css and app.js; read it first, do not edit it).

Changes against the spike file:

- Replace the vault-specific param and branch with `plugins=minimal-settings`
  (D2), same emulated effects. No vault name, person name, path or host anywhere
  in the file.
- All visible text is English; sidebar files and folders get generic names
  (e.g. `Inbox`, `Projects`, `Reading notes`, `Kafka delivery semantics`).
- Every D3 key must match an element. Make sure of: a first top-level paragraph
  (`.markdown-preview-sizer > div > p`) that holds `strong`, inline `code`, an
  internal link, an unresolved link, an external link and a tag; a `.status-bar`
  with two `.status-bar-item` (`312 words`, `1,984 characters`); a Go code block
  with all seven token classes; the first non-header `.cm-line` with plain text.
  Any class you add must occur in `$SPIKE/app.css`.
- Replace the spike's measure code with D3 (keys, selectors, canvas color
  normalization, effective background, null/0 rules) and D2 meta
  (`viewport: [innerWidth, innerHeight]`, `base` as number, `plugins` string or
  `""`).
- Keep the relative `app.css` link and the `css` param (D2).

Must not: load remote resources, touch other files.

Task gates:

```bash
mkdir -p "$S/t2" && cp obsidian/fixture.html "$SPIKE/app.css" "$S/t2/"
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$C" --headless=new --disable-gpu --no-first-run --user-data-dir="$S/t2/.chrome" --allow-file-access-from-files --window-size=1440,1600 --virtual-time-budget=3000 --dump-dom "file://$S/t2/fixture.html?measure=1&base=10&plugins=minimal-settings" 2>/dev/null > "$S/t2/dom.html"
python3 -I -c 'import sys,re,html,json; d=json.loads(html.unescape(re.search(r"<pre id=\"out\">(.*?)</pre>",open(sys.argv[1]).read(),re.S).group(1))); keys="body root sizer p h1 h2 h3 h4 strong link unresolved external tag codeInline codeBlock tokKeyword tokString tokFunction tokComment tokNumber tokOperator tokPunct blockquote calloutTitle calloutContent th td cmSizer cmLine cmH1 nav navActive tab status".split(); miss=[k for k in keys if k not in d["el"]]; print("missing", miss, "base", d["meta"]["base"], "p", d["el"]["p"])' "$S/t2/dom.html"
```

Expected: `missing []`, `base 10`, `p` with `size` 10.0 and 4-int-ish color list.
Also screenshot it once (`--screenshot`) and Read the PNG: it must look like the
spike's Obsidian rendering.

Done: gates as expected, no personal strings (`grep -ciE 'vault=|/Use[r]s/' obsidian/fixture.html` prints 0).

### T3. Preview script (model: sonnet)

File: `obsidian/preview.py` (new). Python 3.11 stdlib only, typed for
`mypy --strict`. Mirror the structure of `zen/preview.py` (argparse, `main() -> int`,
`raise SystemExit(main())`), but no Marionette: plain headless Chrome.

CLI: `python3 obsidian/preview.py --out DIR [--asar PATH] [--theme PATH] [--fixture PATH] [--chrome PATH]`.

- `--theme` default `Path(__file__).parent / "Ayu Ink" / "theme.css"`,
  `--fixture` default `Path(__file__).parent / "fixture.html"`, `--chrome`
  default `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- asar: if `--asar` is not given, pick the highest `obsidian-X.Y.Z.asar` (numeric
  version compare) in `~/Library/Application Support/obsidian/`, else
  `/Applications/Obsidian.app/Contents/Resources/obsidian.asar`. Read `app.css`
  from it with this reader:
  ```python
  def asar_read(asar: Path, inner: str) -> bytes:
      with asar.open("rb") as f:
          _, hsize = struct.unpack("<II", f.read(8))
          hdr = f.read(hsize)
          jlen = struct.unpack("<I", hdr[4:8])[0]
          node = json.loads(hdr[8 : 8 + jlen])
          for part in inner.strip("/").split("/"):
              node = node["files"][part]
          if node.get("unpacked"):
              return Path(f"{asar}.unpacked", inner).read_bytes()
          f.seek(8 + hsize + int(node["offset"]))
          return f.read(node["size"])
  ```
  (`int(node["offset"])`: asar stores the offset as a string.) Type the JSON
  walk honestly (a `cast` or `isinstance` checks, no bare `Any`).
- Setup: `mkdir -p` the out dir, write `app.css` into it, copy the fixture as
  `fixture.html` and the theme as `theme.css` into it.
- For each D4 render, in order `1440`, `zoom3`: query
  `base=<b>&css=theme.css` plus `&plugins=minimal-settings` when set. Run Chrome
  twice with a fresh `tempfile.TemporaryDirectory()` as `--user-data-dir`, flags
  `--headless=new --disable-gpu --hide-scrollbars --no-first-run --allow-file-access-from-files --virtual-time-budget=3000 --window-size=W,H --force-device-scale-factor=<scale>`:
  1. `--screenshot=<out>/shot-<name>.png file://<out>/fixture.html?<query>`
  2. `--dump-dom file://<out>/fixture.html?<query>&measure=1`, take stdout,
     regex `<pre id="out">(.*?)</pre>` (DOTALL), `html.unescape`, `json.loads`,
     write `<out>/computed-<name>.json` with `json.dumps(data, indent=1)`.
  `subprocess.run(..., capture_output=True, text=True, timeout=90)`.
- Print every written PNG and JSON path, one per line, in creation order.
- Exit 2 with one stderr line for setup errors: `preview: Chrome not found: <path> (pass --chrome)`,
  `preview: no Obsidian asar found (pass --asar)`, `preview: missing <path>` for
  theme or fixture. Exit 1 with `preview: chrome failed for <name>: <first stderr line or "no output">`
  when Chrome exits non-zero, the PNG is missing, or `pre#out` is absent.

Task gates (the repo fixture may not exist yet: use the spike's):

```bash
uvx ruff check obsidian/preview.py && uvx ruff format --check obsidian/preview.py
uvx mypy --strict obsidian/preview.py
python3 obsidian/preview.py --out "$S/t3" --fixture "$SPIKE/fixture.html" --theme "$SPIKE/app.css"
python3 obsidian/preview.py --out "$S/t3x" --chrome /nonexistent; test $? = 2
```

The third command must print 4 paths and exit 0 (`--theme` points at any CSS
file just to exercise the copy). Read `$S/t3/shot-zoom3.png` once.

Done: gates pass.

### T4. Checker (model: sonnet)

File: `obsidian/check.py` (new). Python 3.11 stdlib only, `mypy --strict`, same
CLI style as T3.

CLI: `python3 obsidian/check.py FILE...` (D3 JSON files). Exit 2 with
`check: <reason>` on no args, unreadable file or malformed JSON (name the key).
Parse each `el` entry into a frozen dataclass `Measure(family: str, size: float,
line_height: float | None, weight: int, letter_spacing: float, max_width: float | None,
color: tuple[float, float, float, float], bg: tuple[int, int, int],
decoration: tuple[float, float, float, float], box_shadow: str)`.

Contrast math (verified: `#888888` on `#ffffff` gives 63.1, reverse -68.5):

```python
def _y(rgb: tuple[float, float, float]) -> float:
    r, g, b = (c / 255 for c in rgb)
    y = 0.2126729 * r**2.4 + 0.7151522 * g**2.4 + 0.0721750 * b**2.4
    return y + (0.022 - y) ** 1.414 if y < 0.022 else y

def apca(text: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    yt, yb = _y(text), _y(bg)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:
        s = (yb**0.56 - yt**0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (yb**0.65 - yt**0.62) * 1.14
    return 0.0 if s > -0.1 else (s + 0.027) * 100

def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def wcag(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((0.2126 * _lin(x[0]) + 0.7152 * _lin(x[1]) + 0.0722 * _lin(x[2]) for x in (a, b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
```

Text color for contrast: `color` composited over the element's own `bg`
(`a*c + (1-a)*bg`). Distance: Euclidean in RGB.

Checks, once per run: APCA self-test (`#888888` on `#ffffff` 63.1 +-0.1, `#ffffff`
on `#888888` -68.5 +-0.1). Per file, with F = `p.size`, base = `meta.base`:

1. Every D3 key present (one check per key).
2. `root.bg == (11, 14, 20)`.
3. `p.size == base` (+-0.01).
4. `line_height / size == 1.65` (+-0.01) for `p`, `cmLine`.
5. `family` contains `SF Pro Text`: `p`, `cmLine`, `h1`.
6. `family` contains `JetBrainsMono Nerd Font`: `nav`, `tab`, `status`, `codeInline`, `codeBlock`, `tag`.
7. `max_width == 36 * F` (+-1): `sizer`, `cmSizer`.
8. `size / F` (+-0.01): `h1` 1.75, `h2` 1.4, `h3` 1.2, `h4` 1.05, `cmH1` 1.75, `codeInline` 0.875, `codeBlock` 0.875.
9. `weight == 600`: `h1`..`h4`; `weight == 500`: `nav`.
10. `letter_spacing / size` (+-0.001): `h1` -0.022, `h2` -0.018.
11. `abs(apca)` minimum: `p`, `cmLine` 80; `h1` `h2` `h3` `h4` `strong` `navActive` 85;
    `link` `external` `codeInline` `codeBlock` `blockquote` `td` `th` `calloutContent` 75;
    `nav` `tag` `unresolved` `tab` 60; `calloutTitle` 45; `tokKeyword` `tokString`
    `tokFunction` `tokNumber` `tokOperator` `tokPunct` 55; `tokComment` 40; `status` 35.
    Maximum: `p` 95.
12. `wcag >= 4.5` for every key in 11; `p` also `>= 12`.
13. `navActive.box_shadow` contains `rgb(230, 180, 80)` and `inset`.
14. `link.decoration` composited over `link.bg` within 12 of `(142, 114, 56)`.
15. For every key: `color` and `decoration` (composited) and `bg` farther than 12
    from `(138, 92, 245)` (Obsidian's default accent leaking through).

Output: each failure on its own line
`FAIL <file name> <key>.<what>: got <value rounded to 3>, want <rule>`; then, if
none failed, `OK <n> checks` (n = number of individual assertions) and exit 0;
else `<k> of <n> checks failed` and exit 1.

Task gates:

```bash
uvx ruff check obsidian/check.py && uvx ruff format --check obsidian/check.py
uvx mypy --strict obsidian/check.py
python3 obsidian/check.py; test $? = 2
```

Plus: write `$S/t4/pass.json` by hand per D3 with every key and values that
satisfy 1-15 (F = 16), run the checker on it (expect `OK`, exit 0), then a copy
with `p.color` = `[191, 189, 182, 1.0]` (expect a `FAIL ... p.apca` line, exit 1).

Done: gates pass, both sample runs behave as stated.

### T5. install.sh link block (model: haiku)

File: `install.sh`. Insert the block below verbatim right after the `fi` that
closes the Zen Browser section (the last line before the
`# Personal-data guard for this repo` banner's opening `# ====` line), with one
empty line before and after, exactly like the sections around it.

```sh T5-block
# =============================================================================
# Obsidian: Ayu Ink theme from obsidian/
# =============================================================================
# obsidian.json lists the vaults. iCloud vaults are skipped: a synced link
# points nowhere on the other devices.
if [[ "$OS" == "Darwin" ]]; then
  obsidian_json="$HOME/Library/Application Support/obsidian/obsidian.json"
  if [[ ! -f "$obsidian_json" ]] || ! command -v jq >/dev/null 2>&1; then
    echo "Skipping Obsidian theme: no obsidian.json or jq, start Obsidian once and rerun"
  else
    echo "Linking Obsidian theme into local vaults..."
    while IFS= read -r vault; do
      [[ -d "$vault/.obsidian" ]] || continue
      case "$vault" in
        "$HOME/Library/Mobile Documents/"*)
          echo "Skipping $vault: iCloud vault"
          continue
          ;;
      esac
      dst="$vault/.obsidian/themes/Ayu Ink"
      if [[ -e "$dst" && ! -L "$dst" ]]; then
        echo "Skipping $dst: a regular directory, move it aside first"
        continue
      fi
      mkdir -p "$vault/.obsidian/themes"
      ln -sfn "$DOTFILES/obsidian/Ayu Ink" "$dst"
    done < <(jq -r '.vaults[].path' "$obsidian_json")
  fi
fi
```

Task gates:

```bash
bash -n install.sh
awk '/^```sh T5-block$/{f=1;next} /^```$/{f=0} f' plans/obsidian-ayu-ink-theme.md > "$S/t5.txt"
python3 -I -c 'import sys; print(open(sys.argv[1]).read() in open("install.sh").read())' "$S/t5.txt"
python3 -I -c 'import sys; t=open("install.sh").read(); z=t.index("# Zen Browser: prefs"); o=t.index("# Obsidian: Ayu Ink theme"); p=t.index("# Personal-data guard"); print("ordered" if z < o < p else "misplaced")'
```

Expected: exit 0, `True`, `ordered`. Never run install.sh.

### T6. CLAUDE.md map line (main, micro)

Replace the line
`- `zen/`: Zen prefs + userChrome.css (macOS); `zen/preview.py` + `zen/checks.jq` check them.`
with
`- `zen/`, `obsidian/`: macOS themes, checked by their `preview.py` + `check*`.`
(file stays at 200 lines). Gate: criterion 6.

### T7. Live apply (general-purpose agent, after the wave is committed)

Outside git. `$VAULT` given in the prompt. Steps:

```sh
dst="$VAULT/.obsidian/themes/Ayu Ink"
if [ -e "$dst" ] && [ ! -L "$dst" ]; then echo "real dir at target, stop"; exit 1; fi
mkdir -p "$VAULT/.obsidian/themes" ~/.claude/backups
ln -sfn "$HOME/dotfiles/obsidian/Ayu Ink" "$dst"
cp "$VAULT/.obsidian/appearance.json" ~/.claude/backups/obsidian-appearance.json.$(date +%Y%m%d%H%M%S)
osascript -e 'quit app "Obsidian"'
```

Wait until `pgrep -x Obsidian` prints nothing (at most 30 s; Monitor tool or a
polling loop, no bare `sleep`). Quitting first matters: Obsidian rewrites
`appearance.json` from memory on quit. Then:

```sh
tmp="$(mktemp)"
jq '.cssTheme = "Ayu Ink"' "$VAULT/.obsidian/appearance.json" > "$tmp" && mv "$tmp" "$VAULT/.obsidian/appearance.json"
open -a Obsidian
```

After ~10 s: `jq -r .cssTheme` still `Ayu Ink`; `screencapture -x` one file per
display into `$S/live-*.png`, Read them, verdict: theme visible (flat
`#0B0E14`, sans body, mono sidebar) or `Cannot verify` if Obsidian is not on any
captured display (no retries, no window juggling).

Must not: change any other key in `appearance.json`, touch plugins, the Minimal
theme folder, other vaults, or the repo.

## Seams

| producer | consumer | contract |
|---|---|---|
| T2 | T3 | D2 params, `pre#out` |
| T2 | T4 | D3 schema and keys |
| T1 | T4 | D5 values, D6 expectations |
| T3 | T4, validator | D4 file names |
| T1 | T3, T5, T7 | D1 theme dir |

## Not doing

- A light palette: light mode keeps Obsidian's default colors with this theme's
  typography.
- Style Settings `@settings` options, publishing to the community directory.
- Installing fonts (Geist, Inter): body uses the system SF Pro, UI and code use
  the installed JetBrainsMono Nerd Font.
- Changing the vault's font size (10) or window zoom (3); disabling Minimal,
  Minimal Settings or Style Settings; deleting the Minimal theme.
- Activating the theme in other vaults (install.sh only links it).
- README.md, everything.md, a Claude skill for Obsidian theming.

# Claude Code color theme (Ayu lilac accents)

## Goal

A custom Claude Code theme kept in this repo: the built-in `dark-ansi` preset
(colors come from the Ghostty Ayu palette) with its blue accents recolored to
Ayu lilac. Blue today: inline code and paths in replies (`settings.json`),
dialog borders, picker and autocomplete highlight, memory and `CLAUDE.md`
indicators.

Current behavior: `~/.claude/settings.json` has `"theme": "dark-ansi"`; there
is no `~/.claude/themes/`. Sessions started earlier still run the old `dark`
preset (inline code as `38;5;153`).

Facts (verified on Claude Code 2.1.310):

- Docs: https://code.claude.com/docs/en/terminal-config#create-a-custom-theme
  (file `~/.claude/themes/<slug>.json` with `name`, `base`, `overrides`;
  selected as `custom:<slug>`; values `ansi:<name>` among others; unknown
  tokens are ignored silently) and settings-reference `theme` (settings files
  win over the legacy `~/.claude.json` value).
- Inline code is painted with the `permission` token: the binary contains
  `case"codespan":{let u=Qn("permission",t)(e.text)`.
- `dark-ansi` blue tokens: `permission`, `permissionShimmer`, `suggestion`,
  `remember` (`ansi:blueBright`). Taken accents: `warning` yellowBright,
  `success` greenBright, `error` and `claude` redBright, `planMode`
  cyanBright, `autoAccept`/`bashBorder`/`merged` magentaBright.
- Inside tmux Claude Code renders at most 256 colors, even with
  `COLORTERM=truecolor`, so hex values would be quantized; `ansi:` names map
  to the exact Ghostty Ayu palette (`magenta` = `#cda1fa`,
  `magentaBright` = `#d2a6ff`).

Decision (user): Ayu lilac for the blue accents.

## Acceptance criteria

1. `jq -c . claude/themes/ayu.json` prints exactly
   `{"name":"Ayu","base":"dark-ansi","overrides":{"permission":"ansi:magenta","permissionShimmer":"ansi:magentaBright","suggestion":"ansi:magenta","remember":"ansi:magenta"}}`.
2. Every override key is a token of the installed `dark-ansi` preset: the
   "Token check" snippet (Shared definitions) prints `ok`.
3. `bash -n install.sh` exits 0; `grep -cF 'ln -sf "$DOTFILES/claude/themes/ayu.json" ~/.claude/themes/ayu.json' install.sh`
   prints `1`; `grep -cF "jq '.theme = \"custom:ayu\"'" install.sh` prints `1`.
4. `grep -cF 'overwritten (Claude Code status line and color theme).' README.md` prints `1`;
   `grep -cF '~/.claude/themes/ayu.json; do' README.md` prints `1`;
   `grep -cF 'status line and the color theme, wires the Claude Code Stop hook' README.md`
   prints `1`; `grep -cF 'agents, the status line and the color theme, and sets up' README.md`
   prints `1`.
5. `grep -cF 'claude/themes/ayu.json`: linked into' CLAUDE.md` prints `1`;
   `wc -l < CLAUDE.md` prints a number not above `199`.
6. Live (after T4): `readlink ~/.claude/themes/ayu.json` prints
   `$HOME/dotfiles/claude/themes/ayu.json` (expanded);
   `jq -r .theme ~/.claude/settings.json` prints `custom:ayu`.
7. Live: `diff <(jq -S 'del(.theme)' <backup>) <(jq -S 'del(.theme)' ~/.claude/settings.json)`
   prints nothing (backup path in the dispatch prompt).
8. `git diff main...HEAD --stat` lists exactly `CLAUDE.md`, `README.md`,
   `claude/themes/ayu.json`, `install.sh`, `plans/claude-theme.md`.

## Gates

- `jq empty claude/themes/ayu.json`
- the Token check snippet
- `bash -n install.sh`
- `git diff --check main...HEAD`

## Shared definitions

### Theme file `claude/themes/ayu.json`

Exact content (2-space indent, trailing newline):

```json
{
  "name": "Ayu",
  "base": "dark-ansi",
  "overrides": {
    "permission": "ansi:magenta",
    "permissionShimmer": "ansi:magentaBright",
    "suggestion": "ansi:magenta",
    "remember": "ansi:magenta"
  }
}
```

Slug `ayu`, settings value `"theme": "custom:ayu"`, live link
`~/.claude/themes/ayu.json` -> `$DOTFILES/claude/themes/ayu.json`.

### Token check

Run from the repo root; prints `ok` or the unknown keys:

```bash
python3 -I - "$(readlink -f "$(command -v claude)")" claude/themes/ayu.json <<'PY'
import json, re, sys
data = open(sys.argv[1], 'rb').read()
i = data.find(b'permission:"ansi:blueBright"')
s = data.rfind(b'{', 0, i); e = data.find(b'}', i)
keys = set(re.findall(r'([A-Za-z_]+):"', data[s + 1:e].decode('latin1')))
bad = sorted(set(json.load(open(sys.argv[2]))['overrides']) - keys)
print('ok' if i >= 0 and not bad else f'unknown: {bad}')
PY
```

## Tasks

### T1: `claude/themes/ayu.json` (new file)

Scope: create the file with the exact content of Shared definitions "Theme
file". Nothing else.

Task gates: criterion 1, criterion 2 (Token check prints `ok`).

Commit: `feat(claude): add ayu color theme` with pathspec
`claude/themes/ayu.json`.

### T2: `install.sh` (link the theme, select it)

Scope: one insert. Anchor (verified, end of the "Claude Code status line"
block, lines 389-391):

```
  jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
    "$settings" > "$tmp" && mv "$tmp" "$settings"
fi
```

Insert right after the `fi`, before the existing blank line and the
`# Claude Code notifications (macOS)` banner:

```bash

# Color theme: dark-ansi with the blue accents in Ayu lilac
echo "Linking Claude Code color theme..."
mkdir -p ~/.claude/themes
ln -sf "$DOTFILES/claude/themes/ayu.json" ~/.claude/themes/ayu.json
if ! jq -e '.theme == "custom:ayu"' "$settings" >/dev/null; then
  tmp="$(mktemp)"
  jq '.theme = "custom:ayu"' "$settings" > "$tmp" && mv "$tmp" "$settings"
fi
```

`$settings` is set and the file exists at that point (status line block).
Must not change anything else.

Task gates: `bash -n install.sh`; criterion 3.

Commit: `feat(install): link and select the claude theme` with pathspec
`install.sh`.

### T3: `README.md` and `CLAUDE.md`

Scope: four `README.md` edits and one `CLAUDE.md` edit, each old text
verified to occur once. Apply verbatim.

README edit 1, old:

```
- `~/.claude/statusline.sh` is replaced by a link and the `statusLine` key in
  `~/.claude/settings.json` is overwritten (Claude Code status line).
```

new:

```
- `~/.claude/statusline.sh` and `~/.claude/themes/ayu.json` are replaced by
  links, and the `statusLine` and `theme` keys in `~/.claude/settings.json` are
  overwritten (Claude Code status line and color theme).
```

README edit 2, old:

```
  ~/.claude/agents/skill-dry-run.md ~/.claude/statusline.sh; do
```

new:

```
  ~/.claude/agents/skill-dry-run.md ~/.claude/statusline.sh \
  ~/.claude/themes/ayu.json; do
```

README edit 3, old:

```
default shell to zsh, links the Claude Code `/feature` skill, its agents and
the status line, wires the Claude Code Stop hook, and sets up commit signing
for this repo when `~/.ssh/id_ed25519.pub` exists.
```

new:

```
default shell to zsh, links the Claude Code `/feature` skill, its agents, the
status line and the color theme, wires the Claude Code Stop hook, and sets up
commit signing for this repo when `~/.ssh/id_ed25519.pub` exists.
```

README edit 4, old:

```
no password prompt from `chsh`), links the Claude Code `/feature` skill, its
agents and the status line, and sets up commit signing when
`~/.ssh/id_ed25519.pub` exists.
```

new:

```
no password prompt from `chsh`), links the Claude Code `/feature` skill, its
agents, the status line and the color theme, and sets up commit signing when
`~/.ssh/id_ed25519.pub` exists.
```

CLAUDE.md edit (line count stays 199), old:

```
- `claude/hooks/`: `notify.sh` (Stop hook, macOS alert), `pane-state.sh` (turn
  state for the picker); `claude/statusline.sh`: the status line. `install.sh`
  links them into `~/.claude/` and wires settings.json; see `plans/claude-*.md`.
```

new:

```
- `claude/hooks/` (`notify.sh` Stop alert, `pane-state.sh` picker state),
  `claude/statusline.sh`, `claude/themes/ayu.json`: linked into `~/.claude/` by
  `install.sh`, which also wires settings.json; see `plans/claude-*.md`.
```

Task gates: criteria 4 and 5.

Commit: `docs: mention the claude color theme` with pathspec
`README.md CLAUDE.md`.

### T4: live apply (no repo files), after T1 and T2 are committed

Run verbatim:

```bash
mkdir -p ~/.claude/themes
ln -sf "$HOME/dotfiles/claude/themes/ayu.json" ~/.claude/themes/ayu.json
tmp="$(mktemp)"
jq '.theme = "custom:ayu"' ~/.claude/settings.json > "$tmp" && mv "$tmp" ~/.claude/settings.json
```

Must not: touch other keys, repo files, or run `install.sh`.

Task gates: criteria 6 and 7.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 | T2, T4 | Theme file: path, slug `ayu`, value `custom:ayu` |
| T1 | T3 | Docs name the file path only |

## Edge cases

- macOS and Linux: the block sits outside the OS branch; `ansi:` colors follow
  whatever palette the terminal has.
- `~/.claude/themes/` missing at session start: Claude Code reads the theme
  only after a restart (docs); running sessions keep their colors until then.
- Edits to the theme in the repo reach `~/.claude/themes/` through a file
  link, which the directory watcher may not notice: restart to apply.
- First install: `settings.json` exists by then (status line block creates it).

## Not doing

- Other tokens (text, inactive, diff colors, spinner, subagent colors).
- Ghostty palette changes, `COLORTERM`/tmux color-depth changes.
- A theme for light terminals.

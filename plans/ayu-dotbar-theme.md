# Ayu dark look: Ghostty + tmux-dotbar + robbyrussell prompt + neovim-ayu

## Goal

Make the terminal look like the tmux-dotbar preview
(https://github.com/vaaleyard/tmux-dotbar): ayu dark everywhere, minimal
centered status bar, one-line robbyrussell-style prompt, identical background
`#0B0E14` in Ghostty, the tmux status bar and Neovim.

Non-goals: keybindings, font, shell logic, tmux behavior options, pane border /
message / copy-mode colors, yazi/bat/fzf themes, `install.sh`, `README.md`.

Palette (neovim-ayu dark), use only these:

| role          | hex       |
|---------------|-----------|
| background    | `#0B0E14` |
| foreground    | `#BFBDB6` |
| accent/cursor | `#E6B450` |
| green         | `#AAD94C` |
| cyan          | `#95E6CB` |
| blue          | `#59C2FF` |
| red           | `#F07178` |
| yellow        | `#FFB454` |
| UI grey       | `#565B66` |
| dark grey     | `#475266` |

## Current behavior

- Shell is zsh (`bindkey -e`); starship starts via `eval "$(starship init zsh)"`
  at `zsh/.zshrc:104`. `~/.config/starship.toml` and `~/.tmux.conf` are direct
  symlinks into the repo; `~/.config/ghostty` is a Stow link; `~/.config/nvim/*`
  are Stow links. Edits are live.
- Ghostty 1.3.1: hand-written "Alabaster Dark" block (`background = #000000`,
  16 explicit `palette =` lines), padding 2/2, block cursor without color, no
  `shell-integration-features`.
- tmux 3.7c: TPM already installed and bootstrapped by `install.sh`. Theme is
  `egel/tmux-gruvbox` plus a post-TPM block (`.tmux.conf:68-73`) forcing a
  black status bar. RGB is declared via `terminal-overrides ",xterm-256color:RGB"`
  only, which does not match Ghostty's `TERM=xterm-ghostty`.
- Starship 1.24.2: no top-level `format`; ~45 per-language `format` overrides;
  uncommitted edits disable `cmd_duration`, `docker_context`, `package`,
  `python` (from `plans/starship-prompt-cleanup.md`).
- Neovim 0.12.5: `ellisonleao/gruvbox.nvim` with `transparent_mode = true`
  (Normal has no bg), lualine `theme = "gruvbox"`. `termguicolors` is set in
  `nvim/init.lua:28`.

Verified facts (sources: local `ghostty +list-themes`, the theme file in
`Ghostty.app/Contents/Resources/ghostty/themes/Ayu`, `dotbar.tmux` and
`lua/ayu/colors.lua` from the upstream GitHub repos):

- Ghostty dark theme name is exactly `Ayu` (others: `Ayu Light`, `Ayu Mirage`).
  It already sets bg `#0b0e14`, fg `#bfbdb6`, cursor `#e6b450`.
- tmux-dotbar defaults: bg `#0B0E14`, fg `#475266`, current `#BFBDB6`, session
  `#565B66`, prefix `#95E6CB`, separator ` • `, `absolute-centre`, rounded
  prefix pill. It sets `status-style`, `status-left/right`,
  `window-status-style`, `window-status-format`,
  `window-status-current-format`, `window-status-separator`.
- neovim-ayu dark: `colors.bg = '#0B0E14'`.
- The starship config below was rendered against a temp `STARSHIP_CONFIG`:
  dirty repo `➜  dotfiles git:(main) ✗ `, clean repo without `✗`, home `➜  ~ `,
  non-repo `➜  tmp `, failed status gives bold `#F07178` arrow;
  `custom.git_dirty` costs ~15ms.

## Target behavior

### Ghostty (`ghostty/ghostty/config`)

- Replace the whole "Theme" section (heading comment, `background`,
  `foreground`, all 16 `palette =` lines) with:

  ```
  # =============================================================================
  # Theme: Ayu dark
  # =============================================================================
  theme = Ayu
  # Explicit so the terminal bg matches the tmux status bar 1:1
  background = #0B0E14
  foreground = #BFBDB6
  ```

  The `palette =` lines must go: user keys override the theme, so keeping them
  would leave Alabaster ANSI colors under the Ayu theme.
- Cursor section becomes:

  ```
  cursor-style = block
  cursor-style-blink = false
  cursor-color = #E6B450
  # Without this Ghostty switches the cursor to a bar at the prompt
  shell-integration-features = no-cursor
  ```

- `window-padding-x = 12`, `window-padding-y = 8`.
- Untouched: font (including the uncommitted `font-size = 15`), titlebar,
  `window-save-state`, `macos-option-as-alt`, mouse, `copy-on-select`.

### tmux (`.tmux.conf`)

- Terminal block:

  ```
  set -g default-terminal "tmux-256color"
  set -as terminal-features ",xterm-ghostty:RGB"
  set -as terminal-features ",xterm-256color:RGB"
  ```

  This replaces the `terminal-overrides ",xterm-256color:RGB"` line (same
  purpose, modern option). Keep `allow-passthrough`, `extended-keys` and the
  `xterm*:extkeys` line as they are (uncommitted, not ours).
- Plugins: drop `egel/tmux-gruvbox` and `set -g @tmux-gruvbox 'dark'`, add
  `vaaleyard/tmux-dotbar`. Exact resulting block:

  ```
  # Plugins
  set -g @plugin 'tmux-plugins/tpm'
  set -g @plugin 'christoomey/vim-tmux-navigator'
  set -g @plugin 'tmux-plugins/tmux-sessionist'
  set -g @plugin 'vaaleyard/tmux-dotbar'
  # continuum hooks autosave into status-right: must load after the theme
  set -g @plugin 'tmux-plugins/tmux-resurrect'
  set -g @plugin 'tmux-plugins/tmux-continuum'

  set -g @tmux-dotbar-bg "#0B0E14"
  set -g @resurrect-capture-pane-contents 'on'
  set -g @continuum-restore 'off'

  run '~/.tmux/plugins/tpm/tpm'
  ```

  Order matters: TPM sources plugins in `@plugin` order. dotbar overwrites
  `status-right`, while `continuum.tmux` prepends
  `#(.../continuum_save.sh)` to `status-right` for autosave (verified in
  upstream `continuum.tmux`, `add_resurrect_save_interpolation`). dotbar
  after continuum would silently kill autosave. `tmux-sessionist` only binds
  keys, so moving it above dotbar changes nothing. No other
  `@tmux-dotbar-*` options.
- Delete the post-TPM "Force black status bar" block (`.tmux.conf:68-73`): it
  runs after the plugins and would override dotbar. Nothing may follow the
  `run ... tpm` line.
- `base-index 1`, `pane-base-index 1`, `renumber-windows on` already exist:
  leave as is.
- TPM bootstrap already lives in `install.sh`; do not add auto-install logic
  to `.tmux.conf`.

### Starship (`starship.toml`)

Replace the whole file with:

```toml
"$schema" = 'https://starship.rs/config-schema.json'

add_newline = false
command_timeout = 2000

format = '$character$directory$git_branch${custom.git_dirty}'

[character]
format = '$symbol  '
success_symbol = '[➜](bold #AAD94C)'
error_symbol = '[➜](bold #F07178)'

[directory]
format = '[$path]($style) '
style = 'bold #95E6CB'
truncation_length = 1
truncate_to_repo = false

[git_branch]
format = '[git:\(](bold #59C2FF)[$branch](bold #F07178)[\)](bold #59C2FF) '

# Single robbyrussell-style dirty mark instead of the git_status symbol set
[custom.git_dirty]
when = 'test -n "$(git status --porcelain --ignore-submodules=dirty 2>/dev/null | head -n1)"'
require_repo = true
shell = ['sh']
symbol = '✗'
style = '#FFB454'
format = '[$symbol]($style) '
```

The explicit `format` renders only these four modules, so every per-language
section and the `disabled = true` edits from `starship-prompt-cleanup` become
dead config and are removed. `command_timeout = 2000` stays (commit `1f186e6`).

### Neovim

- `nvim/lua/plugins/theme.lua`: replace the gruvbox spec with

  ```lua
  return {
      "Shatur/neovim-ayu",
      priority = 1000,
      config = function()
          require("ayu").setup({ mirage = false })
          vim.cmd.colorscheme("ayu-dark")
      end,
  }
  ```

  Behavior change on purpose: Normal stops being transparent and becomes
  `#0B0E14`.
- `nvim/lua/plugins/ui.lua:7`: `theme = "gruvbox"` -> `theme = "ayu"` (lualine
  theme shipped by neovim-ayu). Nothing else in `ui.lua`.
- `nvim/lazy-lock.json`: lazy.nvim rewrites it on next start. Never hand-edit.

## Relevant files

- `ghostty/ghostty/config`: edit (theme, cursor, padding).
- `.tmux.conf`: edit (terminal features, plugin swap, remove post-TPM block).
- `starship.toml`: full rewrite.
- `nvim/lua/plugins/theme.lua`: full rewrite (25 lines).
- `nvim/lua/plugins/ui.lua`: one-line edit.
- `nvim/lazy-lock.json`: generated, changed only by lazy.nvim.
- `zsh/.zshrc`, `install.sh`, `nvim/init.lua`: read-only.

## Constraints

- No keybinding, prefix, font, mouse, vi-mode, resurrect/continuum changes.
- Pending uncommitted edits in `.tmux.conf` (passthrough/extkeys),
  `ghostty/ghostty/config` (`font-size = 15`) and `starship.toml`
  (starship-prompt-cleanup) are committed first as a baseline (T0), so the
  theme diff is clean and revertable on its own.
- Never stage or commit: `nvim/lazy-lock.json`, `nvim/lua/plugins/lsp.lua`,
  `nvim/lua/plugins/treesitter.lua` (unrelated pending work) or any untracked
  file (`AGENTS.md`, `CLAUDE.md`, `plans/`, `notes/*`, `plan.md`,
  `everything.md`, `nvim/lua/plugins/markdown-preview.lua`). They must stay
  exactly as they are in the worktree.
- Commits: explicit pathspec only (`git add -- <files>`,
  `git commit -- <files>`), never `-A`/`-u`/`-a`. Unsigned (`gpg.format` is
  not configured). Conventional Commits, no agent attribution.
- No em dash in any new comment, heading or commit message.
- Do not run `install.sh`, `stow`, `brew`, `git stash/reset/clean/checkout`.

## Implementation steps

### T0: baseline commit (orchestrator, before any edit)

No file edits. Commit the pending changes of exactly three files:

```
git add -- .tmux.conf ghostty/ghostty/config starship.toml
git commit -m "chore: trim starship modules, bump ghostty font, add tmux extkeys" \
  -- .tmux.conf ghostty/ghostty/config starship.toml
```

Gate: `git status --short` still lists `nvim/lazy-lock.json`,
`nvim/lua/plugins/lsp.lua`, `nvim/lua/plugins/treesitter.lua` as ` M` and all
untracked files as `??`; the three committed files are gone from the list.

### T1: apply the ayu dark theme (implementer)

Scope, edit only these five files:

1. `ghostty/ghostty/config`: padding, cursor block, theme block.
2. `.tmux.conf`: terminal block, plugin block (exact text above), remove the
   post-TPM block.
3. `starship.toml`: full rewrite with the exact content above.
4. `nvim/lua/plugins/theme.lua`: full rewrite with the exact content above.
5. `nvim/lua/plugins/ui.lua`: line 7 only.

Gates: every non user-run command from "Tests / verification". No commit, no
tmux/Ghostty/nvim reload: the orchestrator reviews the diff first.

### T2: review and theme commit (orchestrator)

Review `git diff -- <five files>` against this plan, then:

```
git add -- .tmux.conf ghostty/ghostty/config starship.toml \
  nvim/lua/plugins/theme.lua nvim/lua/plugins/ui.lua
git commit -m "feat: switch terminal look to ayu dark with tmux-dotbar" \
  -- .tmux.conf ghostty/ghostty/config starship.toml \
  nvim/lua/plugins/theme.lua nvim/lua/plugins/ui.lua
```

`nvim/lazy-lock.json` is left out on purpose: it already carries unrelated
pending plugin updates, and lazy.nvim adds the `neovim-ayu` entry only on the
next nvim start.

## Tests / verification

- `ghostty +validate-config` exits 0.
- `ghostty +show-config | grep -E '^(theme|background|foreground|cursor-color|shell-integration-features|window-padding)'`.
- `grep -c '^palette' ghostty/ghostty/config` prints 0.
- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p`.
- `starship prompt --path ~/dotfiles --logical-path ~/dotfiles --status 0`
  and the same with `--status 1`; `starship timings`.
- `grep -n "@plugin" .tmux.conf` shows the order tpm, vim-tmux-navigator,
  tmux-sessionist, tmux-dotbar, tmux-resurrect, tmux-continuum, and
  `tail -n1 .tmux.conf` is the `run '~/.tmux/plugins/tpm/tpm'` line.
- User-run (mutates live state): `tmux source-file ~/.tmux.conf`, `prefix + I`,
  then `tmux show -g status-style` -> `bg=#0B0E14,fg=#475266`,
  `tmux show -s terminal-features | grep RGB`, and
  `tmux show -g status-right | grep -c continuum_save` -> 1 (autosave hook
  survived the theme).
- After the first nvim start installs the plugin:
  `nvim --headless "+lua io.write(string.format('#%06X', vim.api.nvim_get_hl(0, {name='Normal'}).bg))" +qa`
  must print `#0B0E14`.

## Edge cases

- Running tmux server keeps options set by gruvbox and the removed block
  (`status-left-style`, `status-right-style`, `window-status-current-style`,
  pane border, message and mode styles). Agreed apply path: `prefix + I`,
  `prefix + Ctrl-s` (resurrect save, `continuum-restore` is off), then
  `tmux kill-server` and restore with `prefix + Ctrl-r`.
- `~/.tmux/plugins/tmux-gruvbox` stays on disk until `prefix + alt + u`.
- Re-sourcing appends duplicate `terminal-features` entries: harmless.
- Linux servers: `xterm-ghostty:RGB` is inert there; `starship.toml` and
  `.tmux.conf` stay OS-neutral. Ghostty is macOS-only already.
- `custom.git_dirty` runs `git status --porcelain` per prompt: fine here
  (~15ms), bounded by `command_timeout` in huge repos.
- Detached HEAD shows `git:(HEAD)` (robbyrussell shows a short sha).
- First nvim start needs network to clone neovim-ayu; until then lazy reports
  the missing colorscheme once.

## Apply (user-run, after T2)

- Ghostty: reload config (`cmd + shift + ,`), then open a new tab/window:
  `shell-integration-features = no-cursor` only affects newly started shells.
- tmux: `prefix + I` -> `prefix + Ctrl-s` -> `tmux kill-server` -> start
  `tmux` -> `prefix + Ctrl-r`. Check:
  `tmux show -g status-right | grep -c continuum_save` returns 1.
- Shell: `exec zsh` (starship re-reads its config on every prompt anyway).
- nvim: first start installs neovim-ayu and rewrites `nvim/lazy-lock.json`;
  commit the lock separately afterwards. That commit will also carry the
  plugin updates already pending in the lock today.
- Eyeball: identical `#0B0E14` background in the terminal, the tmux status
  bar and nvim, no seam at the bottom.

## Rollback / migration notes

The T0 baseline commit makes the theme a single revertable commit:
`git revert <theme-commit>` (or, before T2,
`git restore -- <the five files>`, safe because T0 left them clean). Then
reload Ghostty config, `tmux source-file ~/.tmux.conf`, restart the shell,
`:Lazy clean` to drop neovim-ayu.

## Acceptance criteria

- [ ] Ghostty: bg `#0B0E14`, steady amber block cursor at the zsh prompt,
      padding 12/8, font unchanged.
- [ ] tmux: session name dim grey bottom-left, cyan rounded pill while prefix
      is held, windows centered with ` • `, active window light, no color seam
      between status bar and terminal.
- [ ] Prompt: `➜  dotfiles git:(main) ✗ ` on one line, no blank line before
      it, red arrow after a failed command, no `✗` in a clean repo.
- [ ] nvim: `ayu-dark`, Normal bg exactly `#0B0E14`, lualine in ayu colors.
- [ ] tmux: `status-right` still contains `continuum_save.sh` after reload.
- [ ] History: baseline commit (3 files) then theme commit (5 files);
      `lazy-lock.json`, `lsp.lua`, `treesitter.lua` and untracked files are
      still uncommitted and byte-identical to before.

## Notes for reviewer

- Expected theme diff (on top of T0): Ghostty about -22/+10, tmux about
  -10/+6, starship about -145/+25, theme.lua full swap, ui.lua 1 line.
- Risk areas: leftover `palette =` lines in Ghostty; plugin order (dotbar
  must precede resurrect/continuum); anything left after the TPM `run` line
  in `.tmux.conf`; stray files staged into either commit.

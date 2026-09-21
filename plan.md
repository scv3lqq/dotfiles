# Dark background + smaller font + verify starship preset

## Goal

Switch Ghostty to a pure-black background, shrink its font to 14, and force the
tmux status bar to render on a pure-black background. Confirm that
`starship.toml` already matches the upstream `no-empty-icons` preset (no
changes required there).

## Context

- Personal dotfiles repo. Configs are symlinked into `$HOME` / `~/.config`, so
  edits take effect on next reload of the affected tool.
- Terminal is Ghostty; multiplexer is tmux with `egel/tmux-gruvbox` (dark).
- Current Ghostty theme is Alabaster Dark (`background = #0E1415`,
  `palette = 0=#0E1415`). User wants a fully black background.
- `font-size = 20` is too large for the user's setup; target is `14`.
- `starship.toml` was inspected against
  `https://starship.rs/presets/toml/no-empty-icons.toml`. Bodies are
  byte-identical except for one extra line at the top of the local file:
  `command_timeout = 2000` (from commit `1f186e6`, kept to suppress Go
  slowness warnings). The preset is therefore already applied — do not touch
  `starship.toml`.
- `egel/tmux-gruvbox` sets `status-style` (and related window-status styles)
  during tpm initialization. Any `set -g status-style ...` placed **before**
  `run '~/.tmux/plugins/tpm/tpm'` is overwritten by the plugin. Overrides must
  live **after** that `run` line.

## Relevant files

- `ghostty/ghostty/config`
- `.tmux.conf`
- `starship.toml` — read-only, verification target.

## Constraints

- Do not modify `starship.toml`.
- Do not change Stow package layout, install.sh, or any other tool config.
- Keep existing Ghostty palette entries 1..15 untouched; only `palette = 0`
  changes alongside `background`.
- Do not remove the `egel/tmux-gruvbox` plugin or change `@tmux-gruvbox`
  setting — only override status-bar styles after tpm runs.
- Preserve all existing keybindings, plugin list, and unrelated options in
  `.tmux.conf`.
- No comments explaining *what* the change does — only *why* if non-obvious
  (the tmux override block needs a one-line `# why` note about tpm ordering).
- English in code/comments; conventional commits if a commit is requested
  (none requested as part of this handoff — leave the worktree dirty).

## Implementation steps

1. **`ghostty/ghostty/config`** — three line edits, no reordering:
   - `font-size = 20` → `font-size = 14`
   - `background = #0E1415` → `background = #000000`
   - `palette = 0=#0E1415` → `palette = 0=#000000`

2. **`.tmux.conf`** — append a new block at the very end of the file, **after**
   the existing `run '~/.tmux/plugins/tpm/tpm'` line. Add exactly:

   ```tmux

   # Force black status bar (must come after tpm: egel/tmux-gruvbox sets these on init)
   set -g status-style 'bg=#000000,fg=#ebdbb2'
   set -g status-left-style 'bg=#000000'
   set -g status-right-style 'bg=#000000'
   set -g window-status-style 'bg=#000000'
   set -g window-status-current-style 'bg=#000000,fg=#fabd2f'
   ```

   The foreground colors (`#ebdbb2`, `#fabd2f`) are the gruvbox light/yellow
   accents — kept so window/session names stay readable on black.

3. **`starship.toml`** — verify only, no edits. Layout note: line 1 is
   `"$schema" = '...'`, line 2 is blank, line 3 is `command_timeout = 2000`,
   line 4 is blank, line 5 starts `[buf]`. The upstream preset has no
   `command_timeout` line, so a raw diff against upstream will always differ
   by exactly that line plus its trailing blank. Strip both before comparing:

   ```sh
   diff \
     <(sed '/^command_timeout = /{N;d;}' starship.toml) \
     <(curl -fsSL https://starship.rs/presets/toml/no-empty-icons.toml)
   ```

   The `sed '/^command_timeout = /{N;d;}'` removes the `command_timeout` line
   together with the immediately following blank line, leaving exactly the
   upstream-equivalent content.

   - Empty diff → preset confirmed, proceed with steps 1 and 2.
   - Non-empty diff → stop and report; do not auto-sync `starship.toml`.

## Tests / verification

Run from repo root:

- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty` —
  unrelated, sanity only.
- Manual:
  - Quit and relaunch Ghostty; confirm background is pure black and font is
    smaller.
  - In a tmux session: `tmux source-file ~/.tmux.conf` (or `prefix + r`);
    confirm the status bar background is black, window/session names remain
    legible.
- `git diff -- ghostty/ghostty/config .tmux.conf` — review that nothing
  outside the listed lines changed.
- `git status` — `starship.toml` must NOT appear as modified.

## Edge cases

- **tpm not installed yet** (fresh machine): the `run` line silently no-ops,
  so the new `set -g status-*` lines still apply directly. No special-casing
  needed.
- **`palette = 0=#000000` collisions**: any program that prints text colored
  ANSI-black on the default background will become invisible. Acceptable —
  user accepted this trade-off explicitly.
- **Other tmux themes in the future**: if the user swaps `egel/tmux-gruvbox`
  for another theme, this override block will continue to force black and may
  clash. Out of scope for this task; flag in the PR/handoff notes only.
- **Ghostty `window-padding` / titlebar**: not touched. Black background
  shows through padding naturally.

## Acceptance criteria

- `ghostty/ghostty/config` shows exactly three changed lines vs. `HEAD`:
  `font-size`, `background`, `palette = 0`.
- `.tmux.conf` shows exactly the appended block from step 2 vs. `HEAD`; no
  other lines changed.
- `starship.toml` is unmodified (`git status` clean for it).
- Ghostty visually renders pure-black background at font size 14.
- tmux status bar renders on `#000000` background with readable text.

## Notes for reviewer

- Verify the override block sits **after** the `run '~/.tmux/plugins/tpm/tpm'`
  line — placement matters here, this is the whole point of the change.
- Confirm no edits leaked into `starship.toml`, `nvim/`, `aerospace/`,
  `karabiner/`, `yazi/`, `zsh/`, or `install.sh`.
- Do not commit; leave the changes in the worktree for the user to review and
  commit themselves.

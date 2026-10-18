# tmux-session-tree-picker

## Goal

`prefix + s` opens a session tree instead of a flat list of every window:
sessions collapsed by default, `→` expands a session, `Enter` opens the first
window of a session (or the focused window), Ayu dark colors instead of the
default fzf grey.

Non-goals:

- No change to the status bar, window auto-rename or any other binding.
- `everything.md` (lags the configs by design, lines 258-259) is not updated.
- No `install.sh` change: the script is referenced in place.

## Current behavior

`.tmux.conf:49-53`: `bind s display-popup -E` (default 50%x50%, tmux border,
default grey popup style) runs `tmux list-windows -a` into fzf with default
colors and default layout (input at the bottom). Every window of every session
is one line `session:index window_name`; Claude windows show as `2.1.296`
(the Claude binary's process name is its version). Preview: `capture-pane` of
the line's target. `Enter` switches to that window, `Ctrl-d` kills the line's
whole session. The grey left column in the screenshot is fzf's default gutter.

Pre-check (2026-10-19): tmux 3.8, fzf 0.74.5 (Homebrew), bash 5.3 in PATH
(`/bin/bash` 3.2), BWK awk 20200816. Linux servers get distro fzf
(Ubuntu 24.04: 0.44, Debian 12: 0.38, see `zsh/.zshrc:81`). Pane title is the
hostname for shells/nvim and `✳ <task title>` for Claude.

## Target behavior

Mockup (tree mode, query empty; colors in brackets):

```
╭──────────────────────────────────────╮╭ preview ───────────────────────╮
│ ❯ search sessions and windows   7/7  ││ (capture-pane of the target,   │
╰──────────────────────────────────────╯│  trailing blank lines trimmed, │
╭ sessions ────────────────────────────╮│  scrolled to the bottom)       │
│▌▸ dotfiles            4 windows  ●   ││                                │
│ ▸ matcher-service-go  1 window       ││                                │
│ ▾ p-castAI            2 windows      ││                                │
│     ├─ 1  󰚩 claude         Excalidraw and system design skills setup  │
│     └─ 2  󰚩 claude         Claude Code                                 │
│ ▸ p-obsidian          4 windows      ││                                │
╰──────────────────────────────────────╯│                                │
 ↵ open  → expand  ← collapse  ^d kill   esc close                      │
```

- Session line: chevron `▸`/`▾` [#565B66], name padded to the longest
  [#59C2FF; current session #E6B450 bold], `N window(s)` [#475266], `●`
  [#AAD94C] on the current session.
- Window line: tree guide `├─`/`└─` [#475266], index [#565B66], icon by
  `pane_current_command` (Claude `󰚩` #FFB454, nvim/vim `` #AAD94C,
  zsh/bash/sh/fish `` #95E6CB, other `` #BFBDB6), name (a `X.Y.Z` name
  shows as `claude`, renamed windows keep their name), then the pane title
  without its leading `✳ `/spinner glyph, or `~`-shortened
  `pane_current_path` when the title is the hostname [#565B66].
- Search mode (query non-empty): every session and every window, window lines
  prefixed `<session> ›` instead of the tree guide, so `card nvim` finds
  windows across collapsed sessions. Clearing the query returns to the tree
  with the previous expand state.
- Keys:
  - `Enter`: session line: select its lowest-index window (`$id:^`) and
    switch to the session; window line: select that window and switch.
  - `→` / `←` (query empty): expand / collapse the session under the cursor;
    `←` on a window line collapses its session and the cursor lands on the
    session line. With a query they move the query cursor as before.
  - `Ctrl-d`: session line kills the session (as now); window line kills only
    that window (was: the whole session). The list reloads in place.
  - `Esc`/`Ctrl-c`: close.
- Cursor starts on the current session. Sessions stay in tmux order (by name).
- fzf look: `--style full:rounded`, `--layout reverse`, list/preview labels,
  footer with the key hints, `--gutter ' '` (removes the grey column),
  `--highlight-line`, colors: `bg #0B0E14, bg+ #122133, fg #BFBDB6,
  fg+ #E6E1CF, hl/hl+ #E6B450, border #475266, label #E6B450,
  prompt #59C2FF, pointer #E6B450, info/footer #565B66, ghost #475266,
  spinner #95E6CB, scrollbar #475266, gutter #0B0E14`.
- Popup: `-B` (fzf draws the borders), `-w 85% -h 80%`. Preview
  `right,55%,follow`, below the list when the popup is under 100 columns.
- Fallback: when fzf is missing or older than 0.71 (`--id-nth`), `prefix + s`
  is tmux's own `choose-tree -Zs`, which has the same collapsed tree, `→`/`←`
  and `Enter` (it opens the session's last active window, not the first).

## Relevant files

- `tmux/session-picker.sh` (new, executable, bash 3.2 compatible): the picker.
- `.tmux.conf` (edit): replace lines 49-53 with the version-gated binding.
- `README.md` (edit): row at line 379 describes the new picker.
- `zsh/.zshrc`, `install.sh` (read-only).

## Constraints

- Prefix, every other binding, plugins, hooks, layout-repair block unchanged.
- Script path `~/dotfiles/tmux/session-picker.sh` (installer already requires
  the checkout there); no new symlink.
- macOS and Linux both read `.tmux.conf`: the gate must keep Linux working
  with old or absent fzf.
- No module-level state outside a per-run `mktemp -d` dir removed on exit.

## Implementation steps

T1 (orchestrator, Claude edits directly after OK): `tmux/session-picker.sh`,
`.tmux.conf`, `README.md`.

`tmux/session-picker.sh` subcommands (fzf calls the script by `$0`):

- `--supported`: exit 0 when `fzf --version` is >= 0.71, else 1.
- (no args): create `PICKER_STATE=$(mktemp -d)`, `export`, `trap` cleanup,
  compute the current session's position, run `list | fzf ...` with:
  `--ansi --delimiter '\t' --with-nth 3.. --id-nth 1`,
  `load:pos(N)+unbind(load)`,
  `right:transform($0 right {1} {2})`, `left:transform($0 left {1} {2})`,
  `change:reload-sync($0 list)`,
  `ctrl-d:execute-silent($0 kill {1} {2})+track-current+reload-sync($0 list)`,
  `enter:become($0 open {1} {2})`, `--preview '$0 preview {1} {2}'`.
- `list`: one `tmux list-windows -a -F` call (tab-separated: session_id,
  window_id, session_name, session_windows, window_index, window_name,
  pane_current_command, pane title or empty when it equals `#{host}`,
  `~`-shortened path), piped to `LC_ALL=C awk` that prints
  `<session_id>\t<window_id or empty>\t<colored display>`. Tree mode when
  `$FZF_QUERY` is empty (windows only for ids in `$PICKER_STATE/expanded`),
  flat mode otherwise. Glyphs written as octal escapes in awk strings.
  Current session id from `tmux display-message -p '#{session_id}'`.
- `right` / `left`: with `$FZF_QUERY` set print `forward-char` /
  `backward-char`; else add / remove the session id in the state file and
  print `track-current+reload-sync(<self> list)`. Window lines share the
  session's id in field 1, so tracking lands on the session line after a
  collapse.
- `preview`: `capture-pane -ep -t <window_id or session_id:^>`, trailing
  blank lines dropped.
- `open`: no-op on empty id; `select-window -t <target> \; switch-client
  -t <session_id>`.
- `kill`: `kill-window -t <window_id>` or `kill-session -t <session_id>`.

`.tmux.conf`:

```
# Sessions: collapsed session tree in an fzf popup (tmux/session-picker.sh);
# tmux's own tree where fzf is missing or older than 0.71
if-shell '~/dotfiles/tmux/session-picker.sh --supported' \
  'bind s display-popup -B -E -w 85% -h 80% "~/dotfiles/tmux/session-picker.sh"' \
  'bind s choose-tree -Zs'
```

`README.md:379`: `| prefix + s | Session tree popup (fzf): → expand, ← collapse, Enter opens the first window, Ctrl+d kills the session or window; tmux choose-tree when fzf < 0.71 |`.

## Tests / verification

1. `bash -n tmux/session-picker.sh`
2. `tmux source-file ~/.tmux.conf`, then `tmux list-keys -T prefix s` shows
   the `display-popup` binding.
3. Isolated server (`tmux -L pickertest -f /dev/null`, 3 sessions, picker in
   a window, keys via `send-keys`, screen via `capture-pane -ep`):
   initial cursor on the current session; `Right` expands with the cursor kept;
   `Down` + `Left` collapses and lands on the session; typing `be` shows the
   flat list with the top match focused; `BSpace` back to the tree;
   `Ctrl-d` on a window line kills only that window; `Enter` on a session line
   selects window `^` (check with `display -p -t '$id' '#{window_index}'`).
4. Gate: `PATH` without fzf -> `--supported` exits 1.
5. Manual: `prefix + s` in the live server, eyeball colors, `●` on the session
   the popup was opened from.

## Edge cases

- Linux with distro fzf (< 0.71) or no fzf: `choose-tree -Zs`.
- Session or window names with spaces: ids carry identity, names are display
  only; non-ASCII session names misalign the padding (byte widths under
  `LC_ALL=C`), cosmetic.
- Killing the session the client is on: client detaches
  (`detach-on-destroy on`), same as today.
- Killing the last window of a session: the session goes away, tracking finds
  nothing, cursor stays at the same index.
- Popup opened with no other sessions: one session line, still works.

## Rollback / migration notes

Live via the `~/.tmux.conf` symlink after `tmux source-file`. Revert:
`git revert <commit>` and `tmux source-file ~/.tmux.conf`; the old binding
returns, the deleted script is unused.

## Acceptance criteria

- [ ] `prefix + s` shows only sessions, all collapsed, cursor on the current one.
- [ ] `→` shows that session's windows under it; `←` hides them.
- [ ] `Enter` on a session opens its lowest-index window; on a window opens it.
- [ ] Typing a query searches windows of collapsed sessions too.
- [ ] Ayu colors, no grey gutter/background; Claude windows read `claude` +
      task title.
- [ ] With fzf < 0.71 or absent, `prefix + s` is `choose-tree -Zs`.
- [ ] `bash -n` and `tmux source-file` clean; only the three listed files change.

## Notes for reviewer

- Risk: `tmux display-message` inside a popup resolves the most recently
  active client; check `●` with two attached clients.
- Risk: `change:reload-sync` runs on every keystroke (one `list-windows`,
  ~10 ms); fine for tens of windows.
- Behavior change: `Ctrl-d` on a window line kills the window, not the session.
- Expected diff: new script ~130 lines, `.tmux.conf` -5/+5, README one row.

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

## Workflow sections

Amendments to the design above, found while prototyping (they win over the
design text):

- The `change` bind is `untrack-current+reload-sync(<self> list)`: a query
  typed after `→`/`←` then focuses the top match, not the tracked item.
- The README row keeps the table's backtick style (exact text in T2).

### Gates

Run from `~/dotfiles`.

1. `bash -n tmux/session-picker.sh && /bin/bash -n tmux/session-picker.sh`
   (Homebrew bash and macOS bash 3.2) exits 0.
2. `test -x tmux/session-picker.sh` exits 0.
3. `tmux/session-picker.sh --supported; echo $?` prints `0` (fzf 0.74.5).
4. `env PATH=/usr/bin:/bin tmux/session-picker.sh --supported; echo $?`
   prints `1` (no fzf on that PATH; runs under `/bin/bash` 3.2).
5. `tmux source-file ~/.tmux.conf && tmux list-keys -T prefix s` exits 0 and
   prints a line containing `display-popup -B -E -w 85% -h 80%`.
6. `LC_ALL=C grep -c "$(printf '\342\200\224')" tmux/session-picker.sh .tmux.conf README.md`
   prints `:0` for every file (no em dash).
7. Behavior on an isolated tmux server (never the user's server). Setup:

   ```bash
   t() { tmux -L pickertest -f /dev/null "$@"; }
   keys() { for k in "$@"; do t send-keys -t alpha:9 "$k"; sleep 0.4; done; sleep 0.6; t capture-pane -ep -t alpha:9; }
   t kill-server 2>/dev/null
   t new-session -d -s alpha -x 170 -y 30; t new-window -t alpha
   t new-session -d -s beta -x 170 -y 30; t new-window -t beta; t new-window -t beta
   t new-session -d -s gamma -x 170 -y 30
   t new-window -t alpha:9 "$HOME/dotfiles/tmux/session-picker.sh; sleep 60"
   sleep 1.5
   ```

   The cursor row is the one whose `capture-pane -ep` output contains
   `48;2;18;33;51` (the `bg+` color). Run in order, each on the previous state:

   - a. `keys` (no args): rows `▸ alpha … 3 windows  ●`, `▸ beta`, `▸ gamma`;
     no `├─`; cursor on alpha.
   - b. `keys Down Right`: `▾ beta` followed by `├─ 0`, `├─ 1`, `└─ 2`; cursor
     on beta.
   - c. `keys Down Down Left`: beta collapsed (`▸ beta`, no `├─`); cursor on
     beta.
   - d. `keys 2`: the only list row is `beta › 2`, cursor on it; then
     `keys BSpace`: the three collapsed session rows again.
   - e. `keys Down Right Down Down C-d`: `t list-windows -t beta -F '#{window_index}'`
     prints `0` and `2`; the picker shows `beta   2 windows` with the cursor on
     beta.
   - f. `t select-window -t beta:2; keys Enter`: `t display -p -t beta '#{window_index}'`
     prints `0`; the picker pane shows `no current client` (expected: the test
     server has no attached client, `select-window` already ran).
   - Cleanup: `t kill-server`.

### Shared definitions

- Script path used by `.tmux.conf`: `~/dotfiles/tmux/session-picker.sh`.
- `tmux/session-picker.sh --supported`: exit 0 when `fzf --version` is
  >= 0.71, else 1 (also 1 when fzf is absent).

### Tasks

T1 and T2 touch different files and run in parallel.

#### T1: `tmux/session-picker.sh` (new)

Create `tmux/session-picker.sh` (new directory `tmux/`) with exactly the
content below, then `chmod 755`. The file is bash 3.2 compatible (no
associative arrays, no `mapfile`, no `${var,,}`). Nerd Font glyphs in the awk
program are octal escapes (`\363\260\232\251` Claude, `\356\230\253` nvim,
`\356\236\225` shell, `\357\213\220` other) and must stay escapes; the other
non-ASCII characters (`▸ ▾ ├ ─ └ › ● ❯ ▌ ↵ → ←`) are literal. Do not edit any
other file.

Task gates: Gates 1, 2, 3, 4, 6 (this file only), 7.
Definition of done: the file matches the reference byte for byte (report any
deviation a gate forced, with the gate output), mode 755, task gates green.

```bash
#!/usr/bin/env bash
# Session tree for `prefix + s`: sessions collapsed, right/left expand and
# collapse, Enter opens a session's first window or the focused window.
# List lines are "<session_id>\t<window_id>\t<display>"; window lines carry
# their session's id in field 1, so --id-nth tracking lands on the session
# line after a collapse.
set -u

self=$0

supported() {
  local v major minor
  v=$(fzf --version 2>/dev/null) || return 1
  v=${v%% *}
  major=${v%%.*}
  minor=${v#*.}
  minor=${minor%%.*}
  case "$major$minor" in '' | *[!0-9]*) return 1 ;; esac
  # 0.71 added --id-nth
  [ "$major" -gt 0 ] || [ "$minor" -ge 71 ]
}

list() {
  local expanded
  expanded=$(tr '\n' ' ' <"$PICKER_STATE/expanded")
  tmux list-windows -a -F "$(printf '%s\t' '#{session_id}' '#{window_id}' \
    '#{session_name}' '#{session_windows}' '#{window_index}' '#{window_name}' \
    '#{pane_current_command}' '#{?#{==:#{pane_title},#{host}},,#{pane_title}}' \
    '#{pane_current_path}')" |
    LC_ALL=C awk -F '\t' -v cur="$PICKER_CURRENT" -v expd=" $expanded " \
      -v search="${FZF_QUERY:+1}" -v home="$HOME" '
      BEGIN {
        grey = "86;91;102"; dim = "71;82;102"; blue = "89;194;255"
        accent = "230;180;80"; green = "170;217;76"; yellow = "255;180;84"
        cyan = "149;230;203"; fg = "191;189;182"
        version = "^[0-9]+\\.[0-9]+\\.[0-9]+$"
      }
      function c(rgb, s) { return "\033[38;2;" rgb "m" s "\033[0m" }
      {
        n++; sid[n] = $1; wid[n] = $2; sname[n] = $3; swin[n] = $4
        widx[n] = $5; wname[n] = $6; cmd[n] = $7; title[n] = $8; path[n] = $9
        if (length($3) > width) width = length($3)
      }
      END {
        for (i = 1; i <= n; i++) {
          if (sid[i] != prev) {
            prev = sid[i]
            open = search || index(expd, " " sid[i] " ")
            name = sprintf("%-" width "s", sname[i])
            name = sid[i] == cur ? "\033[1m" c(accent, name) : c(blue, name)
            count = swin[i] (swin[i] == 1 ? " window" : " windows")
            mark = sid[i] == cur ? "  " c(green, "●") : ""
            printf "%s\t\t%s %s  %s%s\n", sid[i], c(grey, open ? "▾" : "▸"), name, c(dim, count), mark
          }
          if (!open) continue
          if (cmd[i] ~ version || cmd[i] == "claude") icon = c(yellow, "\363\260\232\251")
          else if (cmd[i] ~ /^n?vim$/) icon = c(green, "\356\230\253")
          else if (cmd[i] ~ /^(zsh|bash|sh|fish)$/) icon = c(cyan, "\356\236\225")
          else icon = c(fg, "\357\213\220")
          wn = wname[i] ~ version ? "claude" : wname[i]
          # Claude prefixes its title with a 3-byte glyph: idle mark or spinner
          t = title[i]
          if (substr(t, 1, 1) == "\342" && substr(t, 4, 1) == " ") t = substr(t, 5)
          p = path[i]
          if (p == home || index(p, home "/") == 1) p = "~" substr(p, length(home) + 1)
          info = t != "" ? t : p
          if (search) lead = c(dim, sname[i] " ›")
          else lead = c(dim, (i == n || sid[i + 1] != sid[i]) ? "  └─" : "  ├─")
          printf "%s\t%s\t%s %s  %s %-14s %s\n", sid[i], wid[i], lead, c(grey, widx[i]), icon, wn, c(grey, info)
        }
      }'
}

toggle() {
  if [ -n "${FZF_QUERY:-}" ]; then
    if [ "$1" = right ]; then echo forward-char; else echo backward-char; fi
    return
  fi
  [ -n "$2" ] || return 0
  grep -vxF -- "$2" "$PICKER_STATE/expanded" >"$PICKER_STATE/next"
  [ "$1" = right ] && echo "$2" >>"$PICKER_STATE/next"
  mv "$PICKER_STATE/next" "$PICKER_STATE/expanded"
  echo "track-current+reload-sync($self list)"
}

preview() {
  tmux capture-pane -ep -t "${2:-$1:^}" |
    awk '{ l[NR] = $0; s = $0; gsub(/\033\[[0-9;:]*[A-Za-z]/, "", s); if (s ~ /[^ \t]/) last = NR }
      END { for (i = 1; i <= last; i++) print l[i] }'
}

open_target() {
  [ -n "$1" ] || return 0
  tmux select-window -t "${2:-$1:^}" \; switch-client -t "$1"
}

kill_target() {
  [ -n "$1" ] || return 0
  if [ -n "$2" ]; then tmux kill-window -t "$2"; else tmux kill-session -t "$1"; fi
}

main() {
  local lines pos
  PICKER_STATE=$(mktemp -d) || exit 1
  PICKER_CURRENT=$(tmux display-message -p '#{session_id}')
  export PICKER_STATE PICKER_CURRENT
  trap 'rm -rf "$PICKER_STATE"' EXIT
  : >"$PICKER_STATE/expanded"
  lines=$(list)
  pos=$(printf '%s\n' "$lines" | awk -F '\t' -v cur="$PICKER_CURRENT" '$1 == cur { print NR; exit }')
  printf '%s\n' "$lines" | fzf --ansi --delimiter '\t' --with-nth 3.. --id-nth 1 \
    --layout reverse --style full:rounded --info inline-right --highlight-line \
    --prompt '❯ ' --pointer '▌' --gutter ' ' \
    --ghost 'search sessions and windows' \
    --list-label ' sessions ' --preview-label ' preview ' \
    --footer '↵ open   → expand   ← collapse   ^d kill   esc close' \
    --color 'bg:#0B0E14,bg+:#122133,fg:#BFBDB6,fg+:#E6E1CF,hl:#E6B450,hl+:#E6B450' \
    --color 'border:#475266,label:#E6B450,prompt:#59C2FF,pointer:#E6B450,query:#BFBDB6' \
    --color 'info:#565B66,footer:#565B66,ghost:#475266,spinner:#95E6CB' \
    --color 'scrollbar:#475266,gutter:#0B0E14,preview-bg:#0B0E14' \
    --preview "$self preview {1} {2}" \
    --preview-window 'right,55%,follow,<100(down,45%,follow)' \
    --bind "load:pos(${pos:-1})+unbind(load)" \
    --bind "right:transform($self right {1} {2})" \
    --bind "left:transform($self left {1} {2})" \
    --bind "change:untrack-current+reload-sync($self list)" \
    --bind "ctrl-d:execute-silent($self kill {1} {2})+track-current+reload-sync($self list)" \
    --bind "enter:become($self open {1} {2})"
}

case "${1:-}" in
  --supported) supported ;;
  list) list ;;
  right | left) toggle "$1" "${2:-}" ;;
  preview) preview "$2" "${3:-}" ;;
  open) open_target "$2" "${3:-}" ;;
  kill) kill_target "$2" "${3:-}" ;;
  *) main ;;
esac
```

#### T2: `.tmux.conf` binding and `README.md` row

`.tmux.conf`: replace lines 49-53 (the comment `# Sessions: fzf popup with
terminal preview and ctrl-d to delete session` and the 4-line
`bind s display-popup -E "tmux list-windows ...` command that ends with
`| cut -d' ' -f1 | xargs tmux switch-client -t"`) with exactly:

```
# Sessions: collapsed session tree in an fzf popup (tmux/session-picker.sh);
# tmux's own tree where fzf is missing or older than 0.71
if-shell '~/dotfiles/tmux/session-picker.sh --supported' \
  'bind s display-popup -B -E -w 85% -h 80% "~/dotfiles/tmux/session-picker.sh"' \
  'bind s choose-tree -Zs'
```

Everything else in `.tmux.conf` stays byte-identical (blank line after the
block, the layout-repair block, plugins).

`README.md` line 379: replace the row
``| `prefix` + `s` | Session/window switcher popup (fzf, `Ctrl+d` kills a session) |``
with exactly:

``| `prefix` + `s` | Session tree popup (fzf): `→` expand, `←` collapse, `Enter` opens the session's first window or the focused window, `Ctrl+d` kills the session or window; tmux `choose-tree` when fzf < 0.71 |``

No other README change.

Task gates: Gate 5 (if T1 is not committed yet, `prefix s` resolves to
`choose-tree -Zs`; then check that line instead and say so), Gate 6 for
`.tmux.conf` and `README.md`.
Definition of done: `git diff --stat` shows only these two files, `.tmux.conf`
-5/+5, `README.md` -1/+1.

### Not doing

- `everything.md`, `install.sh`, status bar, window auto-rename, styling of
  `choose-tree` for the fallback, any other binding.
- No `shellcheck` gate (not installed).

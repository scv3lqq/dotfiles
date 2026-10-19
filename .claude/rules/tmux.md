---
paths:
  - ".tmux.conf"
  - "tmux/**"
---

# tmux config gotchas

- Test hooks, aliases and layouts on a throwaway server first, never on the
  live one: `T=(tmux -L t -f <conf>); $T new-session -d -s a -x 50 -y 20;
  ...; $T kill-server`. Zsh: keep the command in an array, not a string.
- Before adding a hook or alias check occupied slots: `tmux show-hooks -g`,
  `tmux show -g command-alias`. Plugins set unindexed hooks and
  `@resurrect-hook-*` (tmux-assistant-resurrect), so use indexed slots:
  `set-hook -g <name>[10]`, `command-alias[100]`.
- `resize-window` / `resize-pane -x/-y` do not expand formats ("width
  invalid"): wrap in `run-shell "tmux resize-window -t #{window_id} ..."`.
- `resize-window` pins `window-size` to `manual` on that window; follow it
  with `set -wu window-size`.
- Inspect sizes with `tmux list-panes -a -F '#{window_width}x#{window_height}
  #{pane_width}x#{pane_height} #{window_layout}'`; the layout string carries
  its own size, which is the ground truth after a resurrect restore.
- Gates on a binding compare `tmux list-keys -T <table> <key>` output, not
  the conf text: tmux normalizes flags (`display-popup -BE -h "80%"`).
- fzf popups (`tmux/session-picker.sh`): proven fzf behavior and the test
  harness design live in `plans/claude-activity-picker.md` (spike findings);
  read them before a spike. Never a tracked reload (it drops keys).
- A copied `/bin/bash` (fake `pane_current_command`) is SIGKILLed on macOS
  until `codesign -s - -f <copy>`.

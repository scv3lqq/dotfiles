---
name: tmux-cleanup
description: Close idle tmux panes to free resources: "почисти tmux", "закрой старые/неактивные панели", "закрой панели, активные больше N ч назад", too many Claude sessions open. Measures real Claude pane activity from transcripts (window_activity is always fresh for Claude panes), lists what goes, kills after one confirm, keeps a resume list.
argument-hint: "[hours, default 1]"
allowed-tools: Bash(python3:*)
---

# tmux-cleanup

Scope is the whole tmux server unless the user names a session.

1. List: `python3 ~/.claude/skills/tmux-cleanup/panes.py --hours <N>`.
   Rows marked KILL/keep, then counts, sessions that close whole, unsaved
   editors, panes with unknown activity. Quote these numbers as printed;
   never count rows by eye.
2. One AskUserQuestion: the counts, whole sessions, any `UNSAVED?` editor
   or Claude pane sitting on a dialog; options all / named sessions only.
   Skip the ask if the user already named the exact scope.
3. Kill: `python3 ~/.claude/skills/tmux-cleanup/panes.py --hours <N> --kill
   <scratchpad>/killed-panes.tsv` (recomputes, so recent activity is spared).
   Exit 1 means a failed kill or a Claude process still alive: report it.
4. Report: killed count, what stays (`tmux list-panes -a`), the TSV path;
   a session comes back with `cd <cwd> && claude --resume <sessionId>`.

Activity signals (why the script exists):
- Claude pane: max of the last `user`/`assistant`/`system` timestamp in
  `~/.claude/projects/*/<sessionId>.jsonl` and `statusUpdatedAt`; pane pid
  tree maps to `~/.claude/sessions/<pid>.json` for `sessionId`. Transcript
  mtime lies: metadata lines get appended to idle sessions.
- Other panes: `window_activity`.
- The current pane (`$TMUX_PANE`) is never killed.

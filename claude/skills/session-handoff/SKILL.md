---
name: session-handoff
description: Run a task in a fresh interactive Claude Code session instead of this one ("сделай в новой сессии", "в отдельной сессии claude code", "запусти другой сессией"), also several in parallel (one worktree each). Writes a self-contained prompt, opens it in a new tmux window, waits for the result in the background, then reviews and merges it here.
---

# Hand a task to a new Claude Code session

1. Decide the change here: research, exact edits, checks, commit/push. The new session
   sees only its prompt plus the CLAUDE.md files and memory it loads itself, so the prompt
   carries anchors and verbatim text, preflight checks (branch, clean target files, line
   counts), verification commands and the exact commit/push commands. Say the user already
   approved it, so it does not stop to ask. No em dash in the prompt; a check that needs
   one uses `chr(0x2014)`. A `/feature` run: the prompt's first line is `/feature <task>`
   (that skill is user-invoke only) and names the exact branch to create.
   Last step of every prompt: write `PASS <short sha> <its scratchpad dir>` (step 5
   reruns its scratch gate scripts from there) or `FAIL <reason>` to
   `<scratchpad>/<slug>.status` via a tmp file plus `mv` (an interactive session never
   closes its pane). Slug: letters, digits, `-`, `_`, not all digits.
2. Write the prompt to `<scratchpad>/<slug>-prompt.md`.
   Several sessions on one repo: one worktree each, never a shared tree. A repo whose
   CLAUDE.md forbids worktrees (dotfiles): one session at a time in the checkout, its
   preflight runs that CLAUDE.md's free-checkout wait and checks the branch before commits.
   `git worktree add --detach <repo>-worktrees/<slug> <base>` (the session creates its
   branch); copy the gitignored files it needs (`CLAUDE.md`, `.claude/settings.local.json`);
   in-project venv: symlink `.venv`, never install there, and before launch prove imports
   resolve to the worktree (coverage paths stay relative) with a baseline gate run.
   Each prompt gets an ownership split (files/functions it may touch, new tests in new
   files) so the later merge stays small.
3. Launch (needs `$TMUX`; outside tmux, give the user the command instead):
   `tmux new-window -d -n <slug> -c <repo> "zsh ~/.claude/skills/session-handoff/launch.zsh <prompt-file> <slug> <mode>"`
   `<mode>` is `bypassPermissions` only when this session runs in bypass mode, else `manual`.
   Before launch `rm -f <scratchpad>/<slug>.status*`; after it confirm
   `tmux capture-pane -p -t ':=<slug>'` works.
4. Tell the user the window name. Start ONE background Bash call (`run_in_background`):
   `zsh ~/.claude/skills/session-handoff/watch.zsh <slug> <scratchpad>/<slug>.status [cap-hours]`
   Cap 0.5 for direct edits, 4 (default) for a `/feature` cycle. It keeps the Mac awake,
   prints one line and exits; several sessions: one watch each, review the first, restart
   the rest. It presses Enter itself on the usage-limit "Press enter to continue" footer
   (once, logged to `<status-file>.log`), never answers a trust or permission dialog.
   Per exit line, act; restart the watch after PROMPT, IDLE, STALL and TIMEOUT only
   (STATUS and WINDOW GONE are terminal):

   | Line | Main does |
   |---|---|
   | `STATUS ...` | step 5 |
   | `WINDOW GONE` | no status: read the repo state, report |
   | `TIMEOUT` | `tmux capture-pane -p -t ':=<slug>'`; still working or usage-limit wait: restart |
   | `PROMPT trust` | read the pane, confirm the folder is the one main launched, then `send-keys -t ':=<slug>'` Down, Enter |
   | `PROMPT permission` | the dialog truncates long commands: read the full pending command from the newest transcripts in `~/.claude/projects/<dashed-cwd>/`; approve only if every target is provably confined (literal path, session scratchpad), else answer No and tell the user |
   | `IDLE api-error` | `tmux send-keys -t ':=<slug>' -l 'continue'`, then `tmux send-keys -t ':=<slug>' Enter` |
   | `STALL` | 30 min without pane change: `tmux capture-pane -p -t ':=<slug>'`, decide |
   | `CAPTURE FAILED` | duplicate window name or tmux error: check `tmux list-windows`, fix, restart |
5. On the notification: check the result against the spec (`git show --stat`, the diff,
   rerun the gates yourself) and report; the session's own report is on its screen.
   Combining branches: merge in a fresh worktree on the target branch, rerun the gates
   after resolving conflicts. The final report names the branch, the worktree it is
   checked out in (blocks `git switch` there), and the exact
   `git -C <repo> push -u origin <branch>`.

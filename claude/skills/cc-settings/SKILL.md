---
name: cc-settings
description: Edit ~/.claude/settings.json or .claude/settings.local.json, and Claude Code's look (status line script, custom themes and colors, which footer element can be hidden). Covers hooks (Stop, Notification, PreToolUse, PostToolUse, SessionStart, PreCompact...), permission allow/deny rules and their startup warnings ("⚠ Allow rule ..."), env vars, statusLine, skillOverrides, model/effort keys, plugins (`enabledPlugins`, marketplaces). Use for "when X happens run Y", "allow <command> without prompting", "add a hook", "set env var", hook not firing, desktop notifications from Claude Code ("лишние уведомления", built-in channel vs Stop hook), "включи плагин везде / он не применяется", a plugin's skills not showing up, «статуслайн», «тема / цвета Claude Code», «убери X внизу». Compact replacement for the bundled update-config skill, which dumps the full settings JSON schema.
---

# Editing Claude Code settings

Scope: `~/.claude/settings.json` (personal, all projects) > `.claude/settings.json` (team, committed) > `.claude/settings.local.json` (personal per-project, gitignored). Later overrides earlier.

## Procedure

1. `cat` the target file. Never rewrite wholesale: merge.
2. Apply the change with one call:

```bash
~/.claude/bin/settings-edit.sh ~/.claude/settings.json '<jq filter>'
```
It backs up to `~/.claude/backups/` (never inside a repo), applies the filter, validates,
restores the backup if the result is not valid JSON, and prints the resulting diff. Read that
diff: it is the proof that nothing else moved. Broken JSON silently disables every setting in
the file, so never hand-write one.
On macOS `~/.claude/settings.json` is a link into `~/dotfiles/claude/settings.json`: the script
writes through it, while `jq ... > tmp && mv tmp` onto the link would replace it with a regular
file. A settings change is a dotfiles commit.

3. Dedup before appending: `[.hooks.Stop[].hooks[]?.command] | any(test("myscript"))`.
4. Changes to a file that already existed at session start are hot-reloaded; a newly created settings file is not. Hooks added to an existing settings.json apply to running sessions within seconds (verified 2026-10-19 with new UserPromptSubmit/PreToolUse entries); no restart needed.

## Hook shape

```json
{"hooks": {"Stop": [{"matcher": "", "hooks": [
  {"type": "command", "command": "~/.claude/hooks/x.sh", "timeout": 10,
   "statusMessage": "...", "async": true, "if": "Bash(git *)"}]}]}}
```
- `matcher` on tool events (`PreToolUse`, `PostToolUse`, `PermissionRequest`) is a regex over tool names (`Write|Edit`); on `Notification` over `notification_type` (`permission_prompt` ~6 s after a dialog, `idle_prompt` 60 s after Stop, `elicitation_dialog`). Omit elsewhere.
- Events: `PreToolUse PostToolUse PostToolUseFailure Notification UserPromptSubmit Stop StopFailure SubagentStop SessionStart SessionEnd PreCompact PostCompact PermissionRequest TaskCompleted ConfigChange`. `StopFailure` replaces `Stop` on an API error.
- No event at all for Esc mid-turn, a denied permission, or Esc on a question: turn-state trackers go stale (workaround in `~/dotfiles/claude/hooks/pane-state.sh` + `tmux/session-picker.sh`). `PermissionRequest` fires as the dialog shows; AskUserQuestion runs PreToolUse, PermissionRequest, PostToolUse.
- Types: `command` (shell, gets hook JSON on stdin), `prompt`, `agent`, `http`, `mcp_tool`. `prompt`/`agent` only on tool events.
- Hook stdin JSON: `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `tool_name`, `tool_input`, `tool_response`, `message` + `notification_type` (Notification), `agent_id` (events from subagents; `StopFailure` fires for them too), `background_tasks` (Stop: in-flight `{id,type,status,...}`, type `shell|subagent|monitor|workflow`, `[]` when none; absent on StopFailure), `source` (SessionStart: `startup|resume|clear|compact`), `reason` (SessionEnd). Fields not listed: search the binary `~/.local/share/claude/versions/<ver>` with python3 `re` over bytes (ugrep chokes). Env: `TMUX_PANE`, `CLAUDE_CODE_ENTRYPOINT`. Parse with `jq -r`, never unquoted `xargs`.
- `Stop` fires at every main-turn end: also when the turn ends waiting on background agents/workflows/shells (each `<task-notification>` starts a new turn) and in headless `claude -p` (env `CLAUDE_CODE_ENTRYPOINT` is not `cli`). "Only when fully done" logic: `~/dotfiles/claude/hooks/notify.sh`.
- A command hook must exit 0 and print nothing unless it means to: stdout is surfaced, exit 2 blocks. Control the session with JSON on stdout: `{"systemMessage":..., "continue":false, "stopReason":..., "suppressOutput":true, "hookSpecificOutput":{"hookEventName":..., "permissionDecision":"allow|deny|ask", "additionalContext":...}}`.
- Test before wiring: `echo '{"hook_event_name":"Stop","cwd":"'$PWD'"}' | ~/.claude/hooks/x.sh; echo $?`.

## Plugins

- `/plugin install x@market` writes `"x@market": true` into `enabledPlugins` of the CWD's
  `.claude/settings.local.json` only, and pins `scope: "local"` + `projectPath` in
  `~/.claude/plugins/installed_plugins.json`. In another project the plugin looks installed
  but its skills never load. Diagnose with:
  `jq '.plugins' ~/.claude/plugins/installed_plugins.json` and
  `grep -rn '<name>@' ~/.claude/settings.json */.claude/settings*.json`.
- Make it global: `settings-edit.sh ~/.claude/settings.json '.enabledPlugins["x@market"] = true'`.
- Plugin skills load at session start; `/reload-plugins` does not add them to the running
  session's skill list. Say so.

## Look: status line, theme, footer

- Docs as raw markdown: `curl -sL https://code.claude.com/docs/en/<page>.md -o <scratchpad>/<page>.md`, then grep (`statusline`, `terminal-config` for themes; `settings-reference` is ~500 KB, never firecrawl it).
- Inside tmux Claude Code draws at most 256 colors, even with `COLORTERM=truecolor`, and quantizes hex naively (`#565B66` came out as `38;5;102`, `#878787`). Status line script: emit `38;5;N` or basic ANSI codes (bash 3.2 pitfalls: dotfiles rule `shell-scripts.md`). Theme overrides: `ansi:<name>` (exact terminal palette) or `ansi256(n)`, not hex.
- Custom theme: `~/.claude/themes/<slug>.json` (`name`, `base`, `overrides`), selected by `"theme": "custom:<slug>"`. Unknown token names are ignored silently: check them against the preset object in the binary (python3 `re` around `permission:"ansi:blueBright"` finds `dark-ansi`). Inline code and paths in replies use `permission` of the base preset only: the markdown renderer resolves the theme by name (`I2`, built-ins only), so overrides never reach it (2.1.310); recolor it through the terminal palette (Ghostty `palette = 12=` for `dark-ansi`). A themes dir created after session start needs a restart.
- Footer: the permission-mode indicator has no hide key; a status line renders above the footer badges and replaces none of them.
- Check what a session really draws: `tmux capture-pane -ep -t "$TMUX_PANE" | grep -a -o $'\e\\[[0-9;]*m' | sort | uniq -c`. "X is the wrong color": first grep this pane's own scrollback (`-S -300 | grep -a -n <text> | cat -v`) for the code next to that text, it answers most cases. Input box and `@`/`/` dropdowns: isolated instance `env -u TMUX tmux -L test -f /dev/null new-session -d -s t -x 160 -y 40 -c <repo> "claude --model claude-haiku-5-5 --settings '{\"disableAllHooks\": true}'"` (no Stop alert), `send-keys -l '<text>'`, a dropdown row is highlighted only after `Down`; for a sent message wait until the capture shows `● ` in the same script, then `kill-server`.
- "Text too dim / not white": reply body has no SGR (terminal default fg: Ghostty `foreground`), secondary text is `2;37` (palette 7 at Ghostty `faint-opacity`), the user message bar is `userMessageBackground` (`dark-ansi`: blackBright, `#686868` under Ayu; override with `ansi256(n)`). The `text` token only colors bullets and labels. Match a reference screenshot by sampling pixels: `uv run --no-project --with pillow python3 -I -` (no PIL in system python).
- Live setup: `~/dotfiles/claude/statusline.sh`, `~/dotfiles/claude/themes/ayu.json`, linked by `install.sh` (plans `claude-statusline.md`, `claude-theme.md`).

## Other keys

- `permissions.allow|deny|ask`: `"Bash(git *)"` (prefix wildcard), `"Read"`, `"Edit(src/**)"`. Path rules use `Edit(...)` for every writing tool, `Read(...)` for reads.
- Bash rule `*` anywhere matches any text, options included (warning "allows any option at its *"); a shell glob the command types literally takes `\*`, `\\*` in JSON (`cp dir/\\*.so dst/`). Trailing `:*` is a prefix; mid-rule `:*` is a plain wildcard.
- A settings warning's exact semantics: slice the binary around its text, `python3 -c 'import sys; d=open(sys.argv[1],"rb").read(); i=d.find(sys.argv[2].encode()); print(d[max(0,i-300):i+300].decode("utf-8","replace"))' "$(readlink -f "$(command -v claude)")" '<text>'` (0.2 s). `strings | grep -n` dumps 100+ KB minified lines; bounded `grep -o '.{0,150}x'` hangs or hits ugrep's complexity limit.
- `env`: `{"VAR": "value"}` (strings only).
- `skillOverrides`: `{"<skill>": "on|name-only|user-invocable-only|off"}` trims noisy bundled skills.
- `preferredNotifChannel` (`auto|iterm2|terminal_bell|iterm2_with_bell|kitty|ghostty|notifications_disabled`): the effective value is in `~/.claude.json` (global config, `/config` → Notifications); the same key in settings.json did not override it. `claude config set` is gone: change it via `/config` or `jq` on `~/.claude.json`, then restart sessions (running ones rewrite the file from memory).
- `statusLine`, `model`, `effortLevel`, `modelSettings.<model>.effortLevel`, `cleanupPeriodDays`, `attribution.commit|pr`.
- Simple display keys (`editorMode`, `verbose`, `model`, `language`): point at `/config` instead of editing. `theme`: see Look below.
- Full schema only when a key is not listed above: `/update-config`.

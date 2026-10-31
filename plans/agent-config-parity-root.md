# Agent Config Parity Root

Base: `034acd6`. Apply and check with the canonical prose helper.

**E1.** (lines 1-9)

```md E1-old
# Claude role

Claude Code (PLANNER/REVIEWER) is the thinking partner; a separate agent (the
implementer) writes the code. Roles are configuration: change a name below and
the workflow is unchanged.

- PLANNER / REVIEWER: Claude Code, Opus 5.5 (`opus` in settings), xhigh effort.
- IMPLEMENTER: Claude Sonnet 5.5 (`claude-sonnet-5-5`), max effort; may also be Codex,
  which reads this file through the `AGENTS.md` symlink.
```

```md E1-new
# Agent roles

The main agent plans and coordinates; scoped implementers write code and
independent reviewers check it. Roles are workflow responsibilities, independent
of a particular product or model. Runtime configuration owns model selection.
```

**E2.** (lines 19-20)

```md E2-old
- Never write code in the main session beyond a micro task (global `CLAUDE.md`):
  agents implement and review (`/feature`).
```

```md E2-new
- Delegate implementation and review beyond a micro task: at most two short
  calls on known targets or an edit of at most three already-decided lines.
```

**E3.** (lines 35-35)

```md E3-old
No database, migrations, service/API or CI. `just check` validates shell and Codex setup.
```

```md E3-new
No database, migrations, service/API or CI. `just check` validates shell and agent setup.
```

**E4.** (lines 50-51)

```md E4-old
  `tmux/session-picker.sh` (fzf popup; design in `plans/tmux-session-tree-picker.md`
  and `plans/claude-activity-picker.md`).
```

```md E4-new
  `tmux/session-picker.sh` (fzf popup; design in `plans/tmux-session-tree-picker.md`).
```

**E5.** (lines 59-64)

```md E5-old
- `claude/`: the global `~/.claude` config, linked by `install.sh` (skills as
  dir links; `CLAUDE.md`, `settings.json` on macOS only). Personal facts live in
  `~/.claude/private/`, never linked; `.githooks/pre-commit` refuses staged
  lines matching its `denylist`. Design: `plans/claude-*.md`.
- `codex/`: native agents, guidance, skill adapters, Ayu theme and isolated setup checks.
- `plans/`: PLANNER's implementation plans (`<task-name>.md`).
```

```md E5-new
- Agent configuration directories hold global guidance, native roles, skills,
  themes and setup checks; concrete installation paths are documented in `README.md`.
  Private facts stay outside the repository; `.githooks/pre-commit` checks staged
  lines against the configured private denylist.
- `plans/`: implementation plans (`<task-name>.md`).
```

**E6.** (lines 67-67)

```md E6-old
- `AGENTS.md`: symlink to this file for Codex; edit `CLAUDE.md`.
```

```md E6-new
- `AGENTS.md`: the canonical regular instruction file; edit this file.
  Compatibility instruction filenames link to it.
```

**E7.** (lines 70-70)

```md E7-old
- `.claude/skills/`: project skills `setup-dotfiles`, `docs-sync`, `readme-screenshots`.
```

```md E7-new
- Project skills: `setup-dotfiles`, `docs-sync`, `readme-screenshots`.
```

**E8.** (lines 101-114)

```md E8-old
Every non-trivial task runs this cycle, `/feature` typed or not (follow
`claude/skills/feature/SKILL.md`), with no OK wait. Overrides here:

- Plan: the command's sections plus Edge cases (macOS vs Linux, missing tools,
  dirty worktree, first run); edits under ~15 lines total make one task.
- Its agents write and review the code, in their own report formats.
- Branch: `git switch -c feat/<slug>` here, no worktree: gates read live paths.
- Shared checkout: before `git switch -c` run `.claude/bin/wait-free-checkout.sh` in
  the background (exit 0: clean `main`, no other busy Claude pane); a direct commit
  needs no open `feat/*` branch and is chained after a branch == `main` check.
- `~/.claude/` targets outside `claude/` (third-party skills) are outside
  git: back them up to `~/.claude/backups/<name>.<ts>` before dispatch, gate on
  `diff` against the backup. A dirty `claude/settings.json` alone (Claude Code
  writes `/model` through the link) is committed first: `chore(claude): sync settings`.
```

```md E8-new
Every non-trivial task runs the installed `feature` workflow, explicitly invoked
or not, with no OK wait. Use its available runtime adapter. Overrides here:

- Plan: the skill's sections plus Edge cases (macOS vs Linux, missing tools,
  dirty worktree, first run); edits under ~15 lines total make one task.
- Its agents implement and independently review, using their report formats.
- Branch: `git switch -c feat/<slug>` here, no worktree: gates read live paths.
- Shared checkout: before `git switch -c` run `bin/wait-free-checkout.sh` in
  the background (exit 0: clean `main`, no other busy pane reported by the
  configured activity integration). A direct commit needs no open `feat/*`
  branch and is chained after a branch == `main` check.
- Third-party targets outside git: back them up to the existing private backup
  directory before dispatch and gate on `diff` against the backup.
  A lone tracked settings change from an interactive client is committed first
  with a scoped `chore` commit before task changes.
```

**E9.** (lines 188-188)

```md E9-old
- Write backups of live configs to `~/.claude/backups/`, never inside the repo.
```

```md E9-new
- Back up live configs outside the repo using their existing private backup convention.
```

**E10.** (lines 199-199)

```md E10-old
no duplication with `README.md`; under 200 lines (`AGENTS.md` is a link to it).
```

```md E10-new
no duplication with `README.md`; keep the canonical `AGENTS.md` under 200 lines.
```

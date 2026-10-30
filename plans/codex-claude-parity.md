# Codex parity with Claude Code

## Goal

Configure the existing local Codex installation with the same personal workflow,
four missing custom agent roles, 22 personal skills, and Ayu colors. Preserve
existing Codex integrations, model selection, permissions, third-party skills,
and the existing go-code-reviewer. Keep installation reproducible from dotfiles.

Current behavior: Claude uses custom:ayu, four workflow agents and 22 repo-backed
skills. Codex has only the matching go-code-reviewer, generic global guidance,
and no selected CLI syntax theme. Project .agents/ is untracked user content.

## Sources and verified baseline

- Official manual fetched 2026-10-31: https://learn.chatgpt.com/docs/agent-configuration/subagents
  (standalone ~/.codex/agents/*.toml; name, description, developer_instructions).
- https://learn.chatgpt.com/docs/build-skills (name and description required;
  ~/.agents/skills supports directory symlinks).
- https://learn.chatgpt.com/docs/cli-customization (tui.theme and .tmTheme files;
  syntax highlighting only).
- https://learn.chatgpt.com/docs/reference/settings (desktop appearance uses UI).
- Base commit: 9e75c74. No tracked changes; unrelated untracked .agents/ stays out.
- `just check` on base fails: no justfile exists. T0 establishes the existing
  syntax gates before the plan commit; this is verification infrastructure.
- `codex --version`: 0.166.0. `--strict-config features list` is unsupported;
  do not use that command as a gate.
- Checkout guard completed with real tmux access before creating the branch.

## Shared definitions

- Branch: feat/codex-claude-parity. Repo directory: codex/.
- New roles: implementer, plan-reviewer, acceptance-validator, skill-dry-run.
  Native TOML files retain source descriptions and behavioral/report contracts.
  Model is inherited; effort respectively max, max, xhigh, high.
- Theme: ayu-claude; bg #0B0E14, fg #E8E6DD, lilac #CDA1FA,
  bright lilac #D2A6FF, selection #303030, caret #E6B450.
- Skills: all current directories under claude/skills; use codex/skills/<name>
  when an adapter exists (feature and retro), otherwise link Claude source.
  Destinations: ~/.agents/skills/<name>, ~/.codex/agents/<name>.toml,
  ~/.codex/themes/ayu-claude.tmTheme, and ~/.codex/AGENTS.md.
  Linux retains current installer exclusion for mac-* names.
- No modification of the Claude source files or private identity data.
- Setup entry point: `python3 codex/setup.py [--home PATH] [--apply]`.
  Default prints a bounded preview without writes. --apply links owned files,
  backs up replaced live config/guidance under <home>/.claude/backups/codex-<timestamp>,
  and updates only tui.theme in config.toml. Python 3.11+ (stdlib tomllib).
  Existing conflicting skill/agent/theme destinations are preserved and reported;
  missing links or already correct links succeed. Existing AGENTS.md is backed
  up before replacement by the repo guidance link. Preserve unknown config keys,
  comments and formatting; never serialize or print full user config.
  Handle existing [tui], missing [tui], existing theme, and missing config.
  A duplicate/invalid TOML config must fail before any live writes. Use atomic
  config replacement. Repeated application makes no changes or new backup.
  Backup directories are mode 0700 and backed-up regular files mode 0600;
  atomic config replacement preserves the existing mode (new file: 0600).
  Unsupported valid TOML encodings of tui (inline table or dotted keys outside
  a literal [tui] section) fail before writes with a clear diagnostic. Never
  guess a text rewrite that might change another table. Include fixture cases.
- Global guidance carries existing Codex planning/TDD/clean-code/git rules plus
  Claude response, language, stack, and orchestration preferences. Do not copy
  personal identity imports, account names, machine data, or Claude hook claims.
  Map Claude tool vocabulary to available Codex tools, cap parallel waves to
  runtime slots, explicitly read applicable .claude/rules (no auto-injection),
  preserve actual Claude paths for tools whose subject is Claude.
- feature adapter reads the canonical claude/skills/feature/SKILL.md with explicit
  Codex overrides: native role names, available tool names, inherited models,
  applicable rules read explicitly, bounded parallelism, remain active through
  completion; project instructions win. User arguments are prompt text, not
  literal $ARGUMENTS. Existing project overrides continue to apply.
  Claude-only vault-index/skill-note-sync prerequisites do not apply to Codex
  adapters; do not write to a vault. Claude model-tier retry directives do not
  apply: report unavailable models, use inherited supported configuration, and
  resume/redispatch only when runtime/tool guidance permits it.
- retro adapter applies session evidence to Codex AGENTS, skills and native
  agent files, maximum five demonstrated changes; no permission weakening.
- No active-session model override is needed to implement these configs.

## Acceptance criteria

1. Four role files parse as TOML with required fields and the efforts above;
   their instructions preserve scoped implementation and independent review.
2. Both adapter skills have valid name/description and resolve required source
   resources. Native skill discovery sees all 22 personal names after apply.
3. Theme parses as plist with the specified base palette; native Codex selects
   the custom syntax theme. Desktop colors are applied through public UI when
   the requested surface includes desktop, with a visual check. Current desktop
   access is explicitly blocked by Computer Use for com.openai.codex; record
   that concrete limitation and remaining color values, without bypassing it.
4. Setup fixture tests prove dry-run has no effects, first-run success,
   idempotence, backup before replacement, conflicting entries preserved,
   existing config semantics unchanged except tui.theme, invalid config no
   writes, private backup/file modes, unsupported TOML shapes fail before writes,
   and Linux mac-* filtering.
5. Live links resolve to repo sources; config selects ayu-claude, model and
   unrelated settings match the backup; existing third-party entries remain.
6. install.sh calls the setup helper in the Claude/Codex integration area;
   it skips with a clear message if Python 3.11+ is missing. Never run the full
   installer as a test or for live application in this task.
7. README documents setup, changed paths, backup, model inheritance, desktop
   distinction and restart. CLAUDE.md remains under 200 lines.
8. `just check` and `git diff --check` pass. Commit only task-owned files;
   preserve unrelated .agents/. Final acceptance precedes merge and push.

## Gates

- `just check`: installer and zsh syntax plus Codex fixtures/config validation.
- `git diff --check`.
- Native loader smoke check: app-server config/skills listing or isolated CLI
  TUI, without a model request. Verified methods: `codex app-server
  --strict-config --print-startup-config`, `codex debug prompt-input` (assert
  role names because malformed roles can silently disappear), app-server
  config/read and skills/list. Never print the complete live config/prompt.
- Live read-only verification after separately approved home-directory writes.

## Tasks

### T0: verification entry point

Owned file: justfile. Add check recipe executing `/bin/bash -n install.sh` and
`zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh`. No full installer execution.
Task gates: `just check`. Later T3 adds Codex verification to this same file.

### T1: native guidance, roles, theme and skill adapters

Owned files: codex/AGENTS.md, codex/agents/*.toml, codex/themes/ayu-claude.tmTheme,
codex/skills/feature/SKILL.md, codex/skills/retro/SKILL.md.
Read claude/CLAUDE.md, four claude/agents sources, feature and retro sources.
Follow Shared definitions. Preserve report formats. Replace false statements
about tool restrictions, hook enforcement or missing conversation with accurate
Codex instructions; native roles are instruction constrained, parent sandbox
is inherited. Validator references ~/.codex/agents/plan-reviewer.toml.
No unsupported Claude model IDs. Do not create public copies of private files.
Theme adds conventional Ayu scopes for comments, keywords, strings, numbers,
functions and inline code using the existing terminal palette.
Task gates: parse every TOML and plist with Python stdlib; verify both skill
frontmatters and local source references. Definition of done: criteria 1-3
file properties (native/live verification belongs to final validation).

### T2: safe setup and behavior fixtures

Owned files: codex/setup.py and codex/test_setup.py.
Write fixture tests first, run red, then implement Shared definitions. Use
unittest and tempfile, isolated synthetic home paths; no live writes in tests.
No network/packages, no broad exception swallowing. Files outside the named
destinations never change. Default root resolves from setup.py's repository.
Each case in criterion 4 has literal expectations (theme ayu-claude; preserved
model fixture-model, approval_policy on-request; conflicting skill bytes remain
user-owned; invalid config yields nonzero and no links/backup).
Named mutation: remove tui.theme update; tests must fail on the literal theme.
Second mutation: replace an existing conflicting skill; preservation test fails.
Reviewer performs mutations only in scratch copies.
Task gates: `python3 -B -m unittest discover -s codex -p 'test_*.py'`.
Definition of done: criteria 4 and helper behavior, with red/green evidence.

### T3: installer and concise repository documentation

Depends on T0-T2. Owned files: install.sh, justfile, README.md, CLAUDE.md,
codex/check.py.
Add a clearly bounded Codex setup block after Claude links; guard Python 3.11+
before calling setup.py --apply, no new package installs or other behavior.
Extend just check with T2's unit test command plus TOML/plist/frontmatter
validation in codex/check.py (stdlib only; no live writes or network).
README adds one compact Codex subsection near Claude setup with exact command
`python3 codex/setup.py --apply`, paths and caveats from criterion 7.
CLAUDE.md map adds codex/ in existing map, keeping <200 lines.
For existing prose use plan_edits.py exact old/new workflow before dispatch.
Task gates: `just check`; `git diff --check`; `wc -l CLAUDE.md`.

### T4: live apply and validation

Depends on reviewed T1-T3. Orchestrator runs preview, then scoped home-directory
application with sandbox escalation required for those paths. Apply only the
reviewed setup helper; no install.sh/stow/package commands. Verify links and
config preservation without printing user config or secrets. Desktop settings
use computer-use skill and public UI, if in scope. Native loader verifies
discovery; restarting a running user session is left to the user.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 | T2, T4 | role names, theme slug, source/adapter link precedence |
| T2 | T3, T4 | setup.py CLI, dry-run/apply and backup behavior |
| T0 | T3 | just check recipe extended after fixtures exist |

## Edge cases

macOS/Linux: mac-* filtering; no GUI writes on Linux. Missing Codex binary does
not prevent preparing configs; report native verification unavailable. Missing
Python 3.11+ produces a clear installer skip. Invalid config fails closed.
Dirty/untracked user files and preexisting local skills remain untouched.
Existing live config symlink is resolved before backing up/updating its target;
no link is silently replaced. No secrets enter git, plans or logs.

## Not doing

No MCP/permission/auth changes, plugin reinstall, memory/history migration,
Claude changes, terminal-wide palette changes, statusline/hooks translation,
or promise of identical Codex CLI chrome colors. No broad repo refactoring.

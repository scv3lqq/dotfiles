# Codex README edits

Apply with `claude/skills/feature/plan_edits.py` against base `9e75c74`.

```md E1-old
`install.sh` backs up nothing but the two Claude Code files named below:
```

```md E1-new
`install.sh` backs up the Claude Code and Codex files described below:
```

```md E2-old
`install.sh` is safe to re-run on both systems.
```

```md E2-new
`install.sh` is safe to re-run on both systems.

### Codex

Codex shares the personal Claude skills and has native `implementer`,
`plan-reviewer`, `acceptance-validator`, and `skill-dry-run` agents. The agents
inherit the current Codex model; their reasoning efforts match the source roles.
The `feature` and `retro` skills have Codex adapters. Existing third-party skills
and the Go reviewer are preserved.

The installer configures this when Python 3.11+ is available. To preview just
the Codex changes, run `python3 codex/setup.py`; apply them with
`python3 codex/setup.py --apply`. This links guidance and agents into `~/.codex/`,
skills into `~/.agents/skills/`, and the Ayu syntax theme into `~/.codex/themes/`.
It sets only `tui.theme` in the existing `~/.codex/config.toml`; model, permissions,
authentication and integrations remain unchanged. Conflicting skill, agent and
theme files are preserved and reported. Replaced guidance and configuration are
backed up privately under `~/.claude/backups/codex-<timestamp>/`.

Restart Codex after applying. The CLI theme controls syntax highlighting;
terminal background and text follow Ghostty. For the desktop app, use
Settings > Appearance: dark base, background `#0B0E14`, foreground `#E8E6DD`,
accent `#CDA1FA`, and code font `JetBrainsMono Nerd Font`.

Run `just check` for shell syntax, isolated setup tests, and Codex asset checks.
```

# Agent Config Parity Readme

Base: `034acd6`.

**E1.** (lines 168-188)

```md E1-old
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

```md E1-new
The root `AGENTS.md` is the canonical, provider-neutral instruction file;
`CLAUDE.md` links to it. Global Codex assets live in tracked `codex/`, not a
project-local `.codex/`: the setup helper links them into the user's home.

Codex shares 22 personal skills and has four native roles:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| `implementer` | `gpt-6.1-sol` | `max` |
| `plan-reviewer` | `gpt-6.1-sol` | `max` |
| `acceptance-validator` | `gpt-6-astra` | `xhigh` |
| `skill-dry-run` | `gpt-6-astra` | `high` |

The main model is unchanged. The `feature` and `retro` skills have Codex adapters;
existing third-party skills and the Go reviewer are preserved.
The installer configures these assets when Python 3.11+ is available.
Preview with `python3 codex/setup.py`; apply with `python3 codex/setup.py --apply`.
This links guidance and agents into `~/.codex/`, personal skills into
`~/.agents/skills/`, and the Ayu syntax theme into `~/.codex/themes/`.
Only `tui.theme` is changed in the global config. Conflicting files are reported;
replaced guidance and configuration are backed up privately outside the repo.

Four additional plugin packages provide 37 shared skills: Astronomer Data (34),
0bull, frontend-design and Humanizer (one each). With these plugins installed and
enabled in Claude Code, preview `python3 codex/plugins.py`, then apply:

~~~sh
python3 codex/plugins.py --apply
codex plugin marketplace add "$HOME/.codex/plugin-sources/claude-parity"
codex plugin add astronomer-data@claude-parity
codex plugin add 0bull@claude-parity
codex plugin add frontend-design@claude-parity
codex plugin add humanizer@claude-parity
~~~

The helper preserves full packages, licenses, scripts and MCP configuration.
It adapts the Data hooks and Humanizer skill layout without changing their sources.
It preserves local edits and backs up managed snapshots before updates.
Plugin hook trust remains an explicit runtime review. iPhone control requires
0bull OAuth; some Data workflows also require their documented command-line tools.
Skill discovery alone does not prove those external workflows are ready.

Restart Codex after applying. The CLI theme controls syntax highlighting;
terminal background and text follow Ghostty. For the desktop app, use
Settings > Appearance: dark base, background `#0B0E14`, foreground `#E8E6DD`,
accent `#CDA1FA`, and code font `JetBrainsMono Nerd Font`.

Run `just check` for shell syntax, isolated setup/plugin tests and asset checks.
```

